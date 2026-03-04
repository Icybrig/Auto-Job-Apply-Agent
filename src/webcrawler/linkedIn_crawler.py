import asyncio
import random
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from crawlee import Request
from crawlee.crawlers import BeautifulSoupCrawlingContext

from src.webcrawler.rooter import router
from src.webcrawler.utils import (
    extract_education_level,
    extract_experience_level,
    extract_requirements_snippet,
    normalize_linkedin_contract,
    parse_linkedin_date,
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd"
}

_MAX_BLOCK_RETRIES = 3
_BLOCKED_TITLE_SNIPPETS = ("authwall", "sign in")
_BLOCKED_TEXT_SNIPPETS = ("join now to see", "sign in to view", "authwall")

_JOB_ID_RE = re.compile(r'/jobs/view/(?:[^/]+-)?(\d+)')
_AGO_RE = re.compile(
    r'\d+[\s\xa0]*(?:minute|hour|heure|day|jour|week|semaine|month|mois)s?(?:[\s\xa0]*ago)?',
    re.IGNORECASE,
)


def _is_blocked_page(title: str, context: BeautifulSoupCrawlingContext) -> bool:
    title_lower = (title or "").strip().lower()
    if any(snippet in title_lower for snippet in _BLOCKED_TITLE_SNIPPETS):
        return True
    text_sample = context.soup.get_text(" ", strip=True)[:500].lower()
    return any(snippet in text_sample for snippet in _BLOCKED_TEXT_SNIPPETS)


def clean(text: str | None) -> str:
    if not text:
        return ""
    return text.strip()


def extract_criteria(soup) -> dict:
    """Extract seniority level and employment type from the job criteria list.

    Tries multiple selector variants to handle LinkedIn's changing class names.
    """
    result = {'seniority_level': '', 'employment_type': ''}

    # Primary selector used by the guest API response
    items = soup.select('li.description__job-criteria-item')
    # Fallback: any li whose class contains "criteria"
    if not items:
        items = soup.select('li[class*="criteria"]')

    for item in items:
        # h3 subheader label (e.g. "Seniority level", "Employment type")
        h3 = item.select_one('h3, h3[class*="subheader"]')
        # span with the actual value
        span = item.select_one('span[class*="criteria-text"], span[class*="criteria"]')
        if not h3 or not span:
            continue
        header = clean(h3.get_text()).lower()
        value = clean(span.get_text())
        if any(k in header for k in ('seniority', 'séniorité', 'niveau')):
            result['seniority_level'] = value
        elif any(k in header for k in ('employment', "type d’emploi", 'type de contrat', 'contrat', 'emploi')):
            result['employment_type'] = value

    return result


@router.handler(label="Linkedin_List")
async def linkedin_list_handler(context: BeautifulSoupCrawlingContext) -> None:
    context.log.info(f"Processing list page: {context.request.url}")
    page_title = context.soup.title.string if context.soup.title else ""
    context.log.info(f"Page Title: {page_title}")

    user_data = dict(context.request.user_data or {})

    if _is_blocked_page(page_title, context):
        block_retries = int(user_data.get("block_retries", 0))
        max_block_retries = int(user_data.get("max_block_retries", _MAX_BLOCK_RETRIES))
        if block_retries >= max_block_retries:
            context.log.error(
                "Reached block retry limit (%s) for %s; giving up.",
                max_block_retries,
                context.request.url,
            )
            return
        context.log.warning(
            "Detected anti-bot page (%s). Retrying %s/%s.",
            page_title,
            block_retries + 1,
            max_block_retries,
        )
        await context.add_requests(
            [
                Request.from_url(
                    context.request.url,
                    label="Linkedin_List",
                    user_data={**user_data, "block_retries": block_retries + 1},
                    headers=_HEADERS,
                    always_enqueue=True,
                )
            ]
        )
        return

    seen, unique_urls = set(), []
    for a_tag in context.soup.select('a[href*="/jobs/view/"]'):
        match = _JOB_ID_RE.search(a_tag.get('href', ''))
        if match:
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{match.group(1)}"
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

    context.log.info(f"Found {len(unique_urls)} jobs")

    if not unique_urls:
        context.log.warning("No job URLs found on this page; nothing to enqueue.")
        return

    await context.add_requests(
        [
            Request.from_url(url, label="LinkedIn_Job", headers=_HEADERS)
            for url in unique_urls
        ]
    )

    # Paginate while under max_results
    max_results = int(user_data.get("max_results", 1))
    parsed = urlparse(context.request.url)
    qs = parse_qs(parsed.query)
    current_start = int(qs.get('start', ['0'])[0])
    next_start = current_start + len(unique_urls)

    if next_start < max_results:
        qs['start'] = [str(next_start)]
        next_url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in qs.items()})))
        await context.add_requests(
            [
                Request.from_url(
                    next_url,
                    label="Linkedin_List",
                    user_data={**user_data, "block_retries": 0},
                    headers=_HEADERS,
                )
            ]
        )
        context.log.info(f"Pagination → start={next_start}")


@router.handler("LinkedIn_Job")
async def linkedin_job_handler(context: BeautifulSoupCrawlingContext) -> None:
    await asyncio.sleep(random.uniform(1.0, 2.5))
    url = context.request.url
    soup = context.soup

    status_code = getattr(getattr(context, "http_response", None), "status_code", None)
    if status_code in {403, 404}:
        context.log.warning("Skipping job detail %s due to HTTP %s", url, status_code)
        return

    # --- Core fields via CSS selectors ---
    title_tag = soup.select_one(
        'h2.top-card-layout__title, h1.top-card-layout__title, h1'
    )
    company_tag = soup.select_one(
        'a.topcard__org-name-link, .topcard__flavor a, '
        '.job-details-jobs-unified-top-card__company-name a'
    )
    # Location appears as the first bullet-separated flavour text after company
    location_tag = soup.select_one(
        'span.topcard__flavor--bullet, '
        '.job-details-jobs-unified-top-card__bullet, '
        '.jobs-unified-top-card__bullet'
    )
    _time_text = soup.find(string=_AGO_RE)

    job_title = clean(title_tag.get_text() if title_tag else None)
    company_name = clean(company_tag.get_text() if company_tag else None)
    location = clean(location_tag.get_text() if location_tag else None)
    time_of_posting = parse_linkedin_date(str(_time_text) if _time_text else None)

    context.log.info(
        f"title={job_title!r}  company={company_name!r}  location={location!r}"
    )

    if not job_title:
        context.log.warning("Skipping %s — no job title found", url)
        return

    # --- Criteria (seniority / employment type) ---
    criteria = extract_criteria(soup)
    context.log.info(f"criteria={criteria}")

    # --- Description ---
    desc_tag = soup.select_one('div.show-more-less-html__markup')
    desc_text = desc_tag.get_text(separator='\n') if desc_tag else ''

    await context.push_data(
        {
            "url": url,
            "platform": "LinkedIn",
            "title": job_title,
            "company": company_name,
            "location": location,
            "contract": normalize_linkedin_contract(criteria['employment_type']),
            "salary": None,
            "currency": "EUR",
            "job_desc": desc_text,
            "job_reqs": extract_requirements_snippet(desc_text),
            "exp_level": (
                extract_experience_level(criteria['seniority_level'])
                or extract_experience_level(desc_text)
                or "Not specified"
            ),
            "edu_level": extract_education_level(desc_text) or "Not specified",
            "published_at": time_of_posting,
        }
    )
    context.log.info(f"Saved: {job_title!r}")

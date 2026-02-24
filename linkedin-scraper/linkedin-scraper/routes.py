from crawlee.router import Router
from crawlee import Request
from crawlee.crawlers import BeautifulSoupCrawlingContext
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import asyncio
import random
import re

router = Router[BeautifulSoupCrawlingContext]()

_JOB_ID_RE = re.compile(r'/jobs/view/(?:[^/]+-)?(\d+)')


@router.default_handler
async def default_handler(context: BeautifulSoupCrawlingContext) -> None:
    print(f"[default_handler] URL: {context.request.url}")

    seen, unique_urls = set(), []
    for a_tag in context.soup.select('a[href*="/jobs/view/"]'):
        match = _JOB_ID_RE.search(a_tag.get('href', ''))
        if match:
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{match.group(1)}"
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

    print(f"[default_handler] Found {len(unique_urls)} job detail URLs")
    await context.add_requests(
        [Request.from_url(url, label='job_listing') for url in unique_urls]
    )

    # Paginate: enqueue next page while under max_results and LinkedIn returned results
    if unique_urls:
        max_results = int(context.request.user_data.get('max_results', 100))
        parsed = urlparse(context.request.url)
        qs = parse_qs(parsed.query)
        current_start = int(qs.get('start', ['0'])[0])
        next_start = current_start + len(unique_urls)

        if next_start < max_results:
            qs['start'] = [str(next_start)]
            next_url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in qs.items()})))
            await context.add_requests([
                Request.from_url(next_url, user_data={'max_results': max_results})
            ])
            print(f"[default_handler] Paginating → start={next_start} (max={max_results})")


def clean(text: str | None) -> str:
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text).strip()


def extract_experience_years(text: str) -> str:
    matches = re.findall(
        r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s+(?:of\s+)?(?:experience|work)',
        text, re.IGNORECASE,
    )
    return ', '.join(dict.fromkeys(matches))


def extract_requirements(desc_soup) -> str:
    keywords = ['requirement', 'qualification', 'what you need',
                'what we need', 'must have', 'you have', 'you bring']
    for tag in desc_soup.find_all(['h2', 'h3', 'strong', 'b']):
        if any(k in tag.get_text(strip=True).lower() for k in keywords):
            ul = tag.find_next_sibling('ul')
            if ul:
                return ' | '.join(li.get_text(strip=True) for li in ul.find_all('li'))
    return ''


def extract_criteria(soup) -> dict:
    result = {'seniority_level': '', 'employment_type': ''}
    for item in soup.select('li.description__job-criteria-item'):
        h3 = item.select_one('h3')
        span = item.select_one('span.description__job-criteria-text')
        if not h3 or not span:
            continue
        header = clean(h3.get_text()).lower()
        value = clean(span.get_text())
        if 'seniority' in header:
            result['seniority_level'] = value
        elif 'employment' in header:
            result['employment_type'] = value
    return result


@router.handler('job_listing')
async def listing_handler(context: BeautifulSoupCrawlingContext) -> None:
    await asyncio.sleep(random.uniform(1.0, 2.5))
    print(f"[listing_handler] URL: {context.request.url}")
    soup = context.soup

    title_tag   = soup.select_one('h2.top-card-layout__title, h1.top-card-layout__title, h1')
    company_tag = soup.select_one('a.topcard__org-name-link, .topcard__flavor a, '
                                  '.job-details-jobs-unified-top-card__company-name a')
    time_tag    = soup.select_one('span.posted-time-ago__text, span.topcard__flavor--metadata')

    job_title       = clean(title_tag.get_text()   if title_tag   else None)
    company_name    = clean(company_tag.get_text() if company_tag else None)
    time_of_posting = clean(time_tag.get_text()    if time_tag    else None)

    print(f"[listing_handler] title={job_title!r}  company={company_name!r}")

    if not job_title:
        print("[listing_handler] Skipping — no job title found")
        return

    criteria  = extract_criteria(soup)
    desc_tag  = soup.select_one('div.show-more-less-html__markup')
    desc_text = desc_tag.get_text(separator=' ') if desc_tag else ''

    await context.push_data({
        'title':            job_title,
        'Company name':     company_name,
        'Time of posting':  time_of_posting,
        'url':              context.request.url,
        'seniority_level':  criteria['seniority_level'],
        'employment_type':  criteria['employment_type'],
        'experience_years': extract_experience_years(desc_text),
        'requirements':     extract_requirements(desc_tag) if desc_tag else '',
    })

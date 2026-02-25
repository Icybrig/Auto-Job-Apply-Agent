import json

from crawlee import Request
from crawlee.crawlers import BeautifulSoupCrawlingContext

from src.webcrawler.rooter import router
from src.webcrawler.utils import (
    clean_html,
    extract_education_level,
    extract_experience_level,
    extract_requirements_snippet,
    normalize_date,
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

_MAX_BLOCK_RETRIES = 3
_BLOCKED_TITLE_SNIPPETS = ("just a moment", "connexion | comptes indeed")
_BLOCKED_TEXT_SNIPPETS = ("please verify", "moment...")


def _unique_job_ids(job_tags) -> list[str]:
    seen: set[str] = set()
    job_ids: list[str] = []
    for tag in job_tags:
        if not tag.has_attr("data-jk"):
            continue
        job_id = str(tag["data-jk"]).strip()
        if job_id and job_id not in seen:
            seen.add(job_id)
            job_ids.append(job_id)
    return job_ids


def _is_blocked_page(title: str, context: BeautifulSoupCrawlingContext) -> bool:
    title_lower = (title or "").strip().lower()
    if any(snippet in title_lower for snippet in _BLOCKED_TITLE_SNIPPETS):
        return True

    text_sample = context.soup.get_text(" ", strip=True)[:500].lower()
    return any(snippet in text_sample for snippet in _BLOCKED_TEXT_SNIPPETS)


@router.handler(label="Indeed_List")
async def indeed_list_handler(context: BeautifulSoupCrawlingContext) -> None:
    context.log.info(f"Processing list page: {context.request.url}")
    page_title = context.soup.title.string if context.soup.title else "No Title"
    context.log.info(f"Page Title: {page_title}")
    job_tags = context.soup.select("a[data-jk]")
    job_ids = _unique_job_ids(job_tags)
    context.log.info(f"Found {len(job_ids)} jobs")

    user_data = dict(context.request.user_data or {})

    if _is_blocked_page(page_title, context):
        block_retries = int(user_data.get("block_retries", 0))
        max_block_retries = int(user_data.get("max_block_retries", _MAX_BLOCK_RETRIES))
        if block_retries >= max_block_retries:
            context.log.error(
                "Reached block retry limit (%s) for %s; giving up on this page.",
                max_block_retries,
                context.request.url,
            )
            return

        context.log.warning(
            "Detected anti-bot page (%s). Retrying attempt %s/%s after rotating session.",
            page_title,
            block_retries + 1,
            max_block_retries,
        )

        retry_user_data = {
            **user_data,
            "block_retries": block_retries + 1,
        }

        await context.add_requests(
            [
                Request.from_url(
                    context.request.url,
                    label="Indeed_List",
                    user_data=retry_user_data,
                    headers=_HEADERS,
                    always_enqueue=True,
                )
            ]
        )
        return

    if not job_ids:
        context.log.warning(
            "No job identifiers found on this page; nothing to enqueue from here."
        )
        return

    await context.add_requests(
        [
            Request.from_url(
                f"https://fr.indeed.com/viewjob?jk={jid}",
                label="Indeed_Job",
                headers=_HEADERS,
            )
            for jid in job_ids
        ]
    )


@router.handler("Indeed_Job")
async def indeed_job_handler(context: BeautifulSoupCrawlingContext) -> None:
    url = context.request.url
    soup = context.soup
    job_data = None

    status_code = getattr(getattr(context, "http_response", None), "status_code", None)
    if status_code in {403, 404}:
        context.log.warning("Skipping job detail %s due to HTTP %s", url, status_code)
        return

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            obj = json.loads(script.string or "")
            if isinstance(obj, dict) and obj.get("@type") == "JobPosting":
                job_data = obj
                break
            if isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        job_data = item
                        break
        except:
            continue

    if not job_data:
        context.log.warning("JobPosting schema missing on %s; skipping.", url)
        return

    org = job_data.get("hiringOrganization") or {}
    loc = job_data.get("jobLocation") or {}
    addr = loc.get("address") or {} if isinstance(loc, dict) else {}
    salary = job_data.get("baseSalary") or {}
    sal_val = salary.get("value") or {}

    desc_text = clean_html(job_data.get("description"))
    requirements = extract_requirements_snippet(desc_text)
    published_at = normalize_date(job_data.get("datePosted"))

    await context.push_data(
        {
            "url": url,
            "platform": "Indeed",
            "title": job_data.get("title"),
            "company": org.get("name"),
            "location": addr.get("addressLocality") or addr.get("addressRegion"),
            "contract": job_data.get("employmentType"),
            "salary": sal_val.get("minValue") or sal_val.get("value"),
            "currency": salary.get("currency") or "EUR",
            "job_desc": desc_text,
            "job_reqs": requirements,
            "exp_level": extract_experience_level(desc_text),
            "edu_level": extract_education_level(desc_text),
            "published_at": published_at,
        }
    )

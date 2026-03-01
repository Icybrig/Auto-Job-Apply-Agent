from crawlee.crawlers import PlaywrightCrawlingContext
from playwright.async_api import Response
from src.webcrawler.rooter import router
from crawlee import Request
import re
from src.webcrawler.utils import (
    clean_html,
    normalize_date,
    normalize_education_level,
    normalize_experience_level,
)


@router.handler(label="WTTJ_List")
async def wttj_list_handler(context: PlaywrightCrawlingContext):
    context.log.info(f"processing job lists: {context.request.url}")
    queued_count = 0

    async def extract_url_from_response(response: Response):
        nonlocal queued_count
        if (
            "algolia" in response.url
            and response.status == 200
            and response.request.method == "POST"
        ):
            try:
                data = await response.json()
                hits = data.get("results", [{}])[0].get("hits", [])
                job_requests = [
                    Request.from_url(
                        f"https://www.welcometothejungle.com/fr/companies/"
                        f"{hit['organization']['slug']}/jobs/{hit['slug']}",
                        label="WTTJ_Job",
                    )
                    for hit in hits
                    if hit.get("organization") and hit.get("slug")
                ]
                if job_requests:
                    await context.add_requests(job_requests)
                    queued_count += len(job_requests)
                    context.log.info(
                        f"found {len(job_requests)} jobs from current page"
                    )
            except Exception as e:
                context.log.warning(f"failed to extract jobs from response: {e}")

    context.page.on(event="response", f=extract_url_from_response)
    await context.page.goto(url=context.request.url, wait_until="domcontentloaded")
    await context.page.wait_for_load_state("networkidle")
    await context.page.wait_for_timeout(3000)

    if queued_count == 0:
        hrefs = await context.page.eval_on_selector_all(
            'a[href*="/companies/"][href*="/jobs/"]',
            "els => els.map(e => e.getAttribute('href')).filter(Boolean)",
        )
        normalized = []
        seen = set()
        for href in hrefs:
            if not isinstance(href, str):
                continue
            if "/companies/" not in href or "/jobs/" not in href:
                continue
            full = (
                href
                if href.startswith("http")
                else f"https://www.welcometothejungle.com{href}"
            )
            key = full.split("?")[0].split("#")[0]
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                Request.from_url(
                    key,
                    label="WTTJ_Job",
                )
            )

        if normalized:
            await context.add_requests(normalized)
            context.log.info(f"fallback enqueued {len(normalized)} jobs from DOM links")


@router.handler(label="WTTJ_Job")
async def job_handler(context: PlaywrightCrawlingContext):
    url = context.request.url
    context.log.info(f"Processing job: {url}")
    await context.page.route(
        "**/*",
        lambda route: (
            route.abort()
            if route.request.resource_type
            in ["image", "font", "media", "stylesheet", "other"]
            else route.continue_()
        ),
    )

    try:
        match = re.search(r"companies/([^/]+)/jobs/([^/?#]+)", url)
        if not match:
            raise ValueError(f"Could not parse slugs from URL: {url}")

        org_slug, job_slug = match.groups()
        api_url = f"https://api.welcometothejungle.com/api/v1/organizations/{org_slug}/jobs/{job_slug}"
        context.log.info(f"Fetching API directly: {api_url}")
        await context.page.goto(url, wait_until="commit")
        res_json = await context.page.evaluate(
            f"""
            fetch("{api_url}").then(res => {{
                if (!res.ok) throw new Error("API status " + res.status);
                return res.json();
            }})
        """
        )

        data = res_json.get("job", {})
        if not data:
            raise ValueError("API returned empty job data")
        company = data.get("organization") or {}
        office = data.get("office") or {}
        job_desc = clean_html(data.get("description"))
        job_reqs = clean_html(data.get("profile"))
        publicated_at = normalize_date(data.get("published_at"))
        await context.push_data(
            {
                "url": url,
                "platform": "Welcome to the jungle",
                "title": data.get("name"),
                "company": company.get("name"),
                "location": office.get("city"),
                "contract": data.get("contract_type"),
                "salary": data.get("salary_min"),
                "currency": data.get("salary_currency") or "EUR",
                "exp_level": normalize_experience_level(data.get("experience_level"))
                or "Not specified",
                "edu_level": normalize_education_level(data.get("education_level"))
                or "Not specified",
                "job_desc": job_desc,
                "job_reqs": job_reqs,
                "published_at": publicated_at,
            }
        )
        context.log.info(f"Successfully saved: {data.get('name')}")
    except Exception as e:
        context.log.exception("Failed to process WTTJ job %s: %s", url, e)

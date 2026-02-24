from crawlee.crawlers import PlaywrightCrawlingContext
from playwright.async_api import Response
from src.webcrawler.rooter import router
from crawlee import Request
import re


@router.handler(label="WTTJ_List")
async def wttj_list_handler(context: PlaywrightCrawlingContext):
    context.log.info(f"processing job lists: {context.request.url}")

    async def extract_url_from_response(response: Response):
        if (
            "algolia" in response.url
            and "search_origin=job_search_client" in response.url
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
                    context.log.info(
                        f"found {len(job_requests)} jobs from current page"
                    )
            except Exception as e:
                context.log.warning(f"failed to extract jobs from response: {e}")

    context.page.on(event="response", f=extract_url_from_response)
    await context.page.goto(url=context.request.url, wait_until="domcontentloaded")
    await context.page.wait_for_timeout(2000)


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
        await context.push_data(
            {
                "url": url,
                "title": data.get("name"),
                "company": company.get("name"),
                "location": office.get("city"),
                "contract": data.get("contract_type"),
                "salary": data.get("salary_min"),
                "currency": data.get("salary_currency") or "EUR",
                "exp_level": data.get("experience_level") or "Not specified",
                "edu_level": data.get("education_level") or "Not specified",
                "job_desc": data.get("description"),
                "job_reqs": data.get("profile"),
                "published_at": data.get("published_at"),
            }
        )
        context.log.info(f"Successfully saved: {data.get('name')}")
    except:
        pass

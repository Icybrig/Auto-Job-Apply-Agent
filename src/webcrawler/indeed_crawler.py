import json
import re
from crawlee import Request
from crawlee.crawlers import BeautifulSoupCrawlingContext
from src.webcrawler.rooter import router

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


@router.handler(label="Indeed_List")
async def indeed_list_handler(context: BeautifulSoupCrawlingContext) -> None:
    context.log.info(f"Processing list page: {context.request.url}")
    page_title = context.soup.title.string if context.soup.title else "No Title"
    context.log.info(f"Page Title: {page_title}")
    job_tags = context.soup.select("a[data-jk]")
    job_ids = list({str(tag["data-jk"]) for tag in job_tags if tag.has_attr("data-jk")})
    context.log.info(f"Found {len(job_ids)} jobs")

    if job_ids:
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

        max_results = int(context.request.user_data.get("max_results", 50))
        current_start = 0
        match = re.search(r"start=(\d+)", context.request.url)
        if match:
            current_start = int(match.group(1))
        next_start = current_start + len(job_ids)

        if next_start < max_results:
            base_url = context.request.url
            if "start=" in base_url:
                next_url = re.sub(r"start=\d+", f"start={next_start}", base_url)
            else:
                next_url = f"{base_url}&start={next_start}"

            await context.add_requests(
                [
                    Request.from_url(
                        next_url,
                        label="Indeed_List",
                        user_data={"max_results": max_results},
                        headers=_HEADERS,
                    )
                ]
            )


@router.handler("Indeed_Job")
async def indeed_job_handler(context: BeautifulSoupCrawlingContext) -> None:
    url = context.request.url
    soup = context.soup
    job_data = None

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

    if job_data:
        org = job_data.get("hiringOrganization") or {}
        loc = job_data.get("jobLocation") or {}
        addr = loc.get("address") or {} if isinstance(loc, dict) else {}
        salary = job_data.get("baseSalary") or {}
        sal_val = salary.get("value") or {}

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
                "description": job_data.get("description"),
                "date": job_data.get("datePosted"),
            }
        )
        return

    title_tag = soup.select_one("h1.jobsearch-JobInfoHeader-title")
    company_tag = soup.select_one("[data-company-name='true']")
    desc_tag = soup.select_one("#jobDescriptionText")

    await context.push_data(
        {
            "url": url,
            "platform": "Indeed",
            "title": title_tag.get_text().strip() if title_tag else None,
            "company": company_tag.get_text().strip() if company_tag else None,
            "description": desc_tag.get_text().strip() if desc_tag else None,
        }
    )

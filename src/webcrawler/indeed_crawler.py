import json
import re

from crawlee import Request
from crawlee.crawlers import BeautifulSoupCrawlingContext
from crawlee.router import Router

# Indeed 专属 Router（独立于 WTTJ 的 PlaywrightCrawlingContext router）
indeed_router = Router[BeautifulSoupCrawlingContext]()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


@indeed_router.default_handler
async def indeed_list_handler(context: BeautifulSoupCrawlingContext) -> None:
    context.log.info(f"处理列表页: {context.request.url}")

    job_tags = context.soup.select("a[data-jk]")
    job_ids = list({tag["data-jk"] for tag in job_tags if tag.get("data-jk")})
    context.log.info(f"找到 {len(job_ids)} 个职位")

    if job_ids:
        await context.add_requests([
            Request.from_url(
                f"https://fr.indeed.com/viewjob?jk={jid}",
                label="Indeed_Job",
                headers=_HEADERS,
            )
            for jid in job_ids
        ])

        max_results = int(context.request.user_data.get("max_results", 50))
        current_start = int(
            re.search(r"start=(\d+)", context.request.url).group(1)
            if "start=" in context.request.url
            else 0
        )
        next_start = current_start + len(job_ids)
        if next_start < max_results:
            if "start=" in context.request.url:
                next_url = re.sub(r"start=\d+", f"start={next_start}", context.request.url)
            else:
                next_url = context.request.url + f"&start={next_start}"
            await context.add_requests([
                Request.from_url(
                    next_url,
                    user_data={"max_results": max_results},
                    headers=_HEADERS,
                )
            ])
            context.log.info(f"分页 → start={next_start}")


@indeed_router.handler("Indeed_Job")
async def indeed_job_handler(context: BeautifulSoupCrawlingContext) -> None:
    url = context.request.url
    context.log.info(f"处理详情页: {url}")
    soup = context.soup

    # 策略1：优先解析 JSON-LD 结构化数据（最稳定）
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
        except Exception:
            continue

    if job_data:
        org = job_data.get("hiringOrganization") or {}
        loc = job_data.get("jobLocation") or {}
        addr = loc.get("address") or {} if isinstance(loc, dict) else {}
        salary = job_data.get("baseSalary") or {}
        sal_val = salary.get("value") or {}
        await context.push_data({
            "url": url,
            "title": job_data.get("title"),
            "company": org.get("name"),
            "location": addr.get("addressLocality") or addr.get("addressRegion"),
            "contract": job_data.get("employmentType"),
            "salary": sal_val.get("minValue") or sal_val.get("value"),
            "currency": salary.get("currency") or "EUR",
            "exp_level": job_data.get("experienceRequirements") or "Not specified",
            "edu_level": job_data.get("educationRequirements") or "Not specified",
            "job_desc": job_data.get("description"),
            "job_reqs": None,
            "published_at": job_data.get("datePosted"),
        })
        context.log.info(f"已保存(JSON-LD): {job_data.get('title')!r}")
        return

    # 策略2：DOM 降级解析
    def clean(tag) -> str:
        return re.sub(r"\s+", " ", tag.get_text()).strip() if tag else ""

    title_tag = soup.select_one("h1.jobsearch-JobInfoHeader-title, h1[class*='title']")
    company_tag = soup.select_one("[data-company-name='true'], a[data-tn-element='companyName']")
    location_tag = soup.select_one("[data-testid='job-location']")
    desc_tag = soup.select_one("#jobDescriptionText")

    await context.push_data({
        "url": url,
        "title": clean(title_tag),
        "company": clean(company_tag),
        "location": clean(location_tag),
        "contract": None,
        "salary": None,
        "currency": "EUR",
        "exp_level": "Not specified",
        "edu_level": "Not specified",
        "job_desc": clean(desc_tag),
        "job_reqs": None,
        "published_at": None,
    })
    context.log.info(f"已保存(DOM): {clean(title_tag)!r}")

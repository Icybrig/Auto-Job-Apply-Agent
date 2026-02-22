from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from playwright.async_api import Response
from crawlee.router import Router
from crawlee import Request
from webcrawler.utlils import to_digit

router = Router[PlaywrightCrawlingContext]()


# Processing job list page
@router.default_handler
async def deault_handler(context: PlaywrightCrawlingContext):
    context.log.info(f"processing job lists: {context.request.url}")

    async def extract_url_from_response(response: Response):
        if "algolia" in response.url and response.status == 200:
            data = await response.json()
            hits = data.get("results", [{}])[0].get("hits", [{}])
            job_requests = []
            for hit in hits:
                job_url = f"https://www.welcometothejungle.com/fr/companies/{hit['organization']['slug']}/jobs/{hit['slug']}"
                job_requests.append(Request.from_url(job_url, label="job"))
            if job_requests:
                await context.add_requests(job_requests)
                context.log.info(f"found {len(job_requests)} job from current page")

    context.page.on(event="response", f=extract_url_from_response)
    await context.page.goto(url=context.request.url, timeout=2000, wait_until="load")
    try:
        await context.enqueue_links(
            selector="nav[aria-label='Pagination'] a sc-imZCey bmfsCt",
            label="default",
        )
    except Exception:
        context.log.info("No more pages")


# Processing job post page
@router.handler(label="job")
async def job_handler(context: PlaywrightCrawlingContext):
    context.log.info(f"processing job post page: {context.request.url}")
    await context.page.wait_for_selector(selector="div container")
    title = await context.page.locator(
        "div [data-testid = 'job-metadata-block'] h2"
    ).text_content()
    company = await context.page.locator(
        "div [data-testid = 'job-metadata-block'] a span"
    ).text_content()
    location = (
        await context.page.locator("svg[alt = 'Location']")
        .locator(".. span span")
        .text_content()
    )
    contract = (
        await context.page.locator("svg[alt = 'Contract']").locator("..").text_content()
    )
    remote = (
        await context.page.locator("svg[alt = 'Remote']")
        .locator("..")
        .first.text_content()
    )

    salary = (
        await context.page.locator("svg[alt = 'Salary']")
        .locator("..")
        .locator("..")
        .text_content()
    )
    salary = to_digit(salary)
    experience = (
        await context.page.locator("svg[alt = 'Suitcase']")
        .locator("..")
        .locator("..")
        .text_content()
    )
    education = (
        await context.page.locator("svg[alt = 'EducationLevel']")
        .locator("..")
        .text_content()
    )
    job_desc = await context.page.locator(
        "div[data-testid = 'job-section-description']"
    ).text_content()
    job_reqs = await context.page.locator(
        "div[data-testid = 'job-section-experience']"
    ).text_content()
    await context.push_data(
        {
            "url": context.request.url,
            "title": title,
            "salary": salary,
            "company": company,
            "location": location,
            "contract": contract,
            "remote": remote,
            "salary": salary,
            "experience": experience,
            "education": education,
            "job_desc": job_desc,
            "job_reqs": job_reqs,
        }
    )


async def main():
    crawler = PlaywrightCrawler(
        request_handler=router,
        max_requests_per_crawl=20,
    )
    await crawler.run(
        [
            Request.from_url(
                url="https://www.welcometothejungle.com/en/jobs?query=python",
                label="default",
            )
        ]
    )

from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee import Request
from src.webcrawler.rooter import router


@router.handler(label="Indeed_List")
async def indeed_list_handler(context: PlaywrightCrawlingContext):
    context.log.info(f"processing job lists: {context.request.url}")
    await context.page.goto(
        url=context.request.url, wait_until="domcontentloaded", timeout=60000
    )
    title = await context.page.title()
    context.log.info(f"title: {title}")
    try:
        await context.page.wait_for_selector("a.jcs-JobTitle[data-jk]", timeout=10000)
    except Exception:
        context.log.error("timeout")
    job_locators = await context.page.locator("a[data-jk]").all()
    print(job_locators)
    requests = []
    for job_locator in job_locators:
        job_id = await job_locator.get_attribute("data-jk")
        job_url = f"https://fr.indeed.com/viewjob?jk={job_id}"
        requests.append(Request.from_url(job_url, label="Indeed_Job"))

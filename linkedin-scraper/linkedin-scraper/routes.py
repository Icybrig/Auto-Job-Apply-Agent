from contextlib import suppress, asynccontextmanager
from crawlee.router import Router
from crawlee import Request
from crawlee.crawlers import PlaywrightCrawlingContext
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import re



router = Router[PlaywrightCrawlingContext]()


@router.default_handler
async def default_handler(context: PlaywrightCrawlingContext) -> None:
    """Default request handler."""
    print(f"[default_handler] URL: {context.page.url}")
    print(f"[default_handler] Title: {await context.page.title()}")

    #select all the links for the job posting on the page
    hrefs = await context.page.locator('ul.jobs-search__results-list a').evaluate_all("links => links.map(link => link.href)")

    print(f"[default_handler] Found {len(hrefs)} job links")

    #add all the links to the job listing route
    await context.add_requests(
            [
                Request.from_url(rec, label='job_listing') for rec in hrefs
             ]
        )

  

def clean(text: str | None) -> str:
    """Collapse whitespace/newlines into a single space and strip."""
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text).strip()


@router.handler('job_listing')
async def listing_handler(context: PlaywrightCrawlingContext) -> None:
    """Handler for job listings."""

    # Wait until network is idle — React finishes rendering
    await context.page.wait_for_load_state('networkidle')

    print(f"[listing_handler] URL: {context.page.url}")
    print(f"[listing_handler] Title: {await context.page.title()}")

    # Try multiple selector patterns — LinkedIn changes layouts frequently
    title_locator = context.page.locator(
        'h1.top-card-layout__title, h1.job-title, h1'
    ).first
    company_locator = context.page.locator(
        'a.topcard__org-name-link, .topcard__flavor a, .job-details-jobs-unified-top-card__company-name a'
    ).first
    time_locator = context.page.locator(
        'span.posted-time-ago__text, span.topcard__flavor--metadata'
    ).first

    job_title = clean(await title_locator.text_content())
    company_name = clean(await company_locator.text_content())
    time_of_posting = clean(await time_locator.text_content())

    print(f"[listing_handler] title={job_title!r}  company={company_name!r}")

    # Skip the record entirely if critical data is missing
    if not job_title:
        print("[listing_handler] Skipping — no job title found")
        return

    await context.push_data(
        {
            'title': job_title,
            'Company name': company_name,
            'Time of posting': time_of_posting,
            'url': context.request.loaded_url,
        }
    )









        
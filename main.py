import asyncio
from datetime import timedelta
from crawlee.crawlers import PlaywrightCrawler
from crawlee import Request, ConcurrencySettings
import src.webcrawler.indeed_crawler
import src.webcrawler.wttj_crawler
from src.webcrawler.wttj_crawler import router

concurrency_settings = ConcurrencySettings(max_concurrency=1, desired_concurrency=1)


async def main():
    target_pages = 2
    crawler = PlaywrightCrawler(
        request_handler=router,
        concurrency_settings=concurrency_settings,
        max_requests_per_crawl=30 * target_pages,
        request_handler_timeout=timedelta(seconds=120),
        headless=False,
        browser_launch_options={
            "args": [
                "--disable-blink-features=AutomationControlled",  
                "--no-sandbox",
            ],
        },
      
        browser_type="chromium",
    )

    initial_requests = [
        Request.from_url(
            # url=f"https://www.welcometothejungle.com/fr/jobs?query=python&page={i}",
            # label="WTTJ_List",
            url=f"https://fr.indeed.com/jobs?q=python&l=France&start={10}",
            label="Indeed_List",
        )
        for i in range(1, target_pages + 1)
    ]

    await crawler.run(initial_requests)
    await crawler.export_data("storage/datasets/default/data.csv")
    print("Job data exported to dataset.csv")


if __name__ == "__main__":
    asyncio.run(main())

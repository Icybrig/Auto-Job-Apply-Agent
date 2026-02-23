import asyncio
from datetime import timedelta
from crawlee.crawlers import PlaywrightCrawler
from crawlee import Request

from src.webcrawler.wttj_crawler import router


async def main():
    target_pages = 2
    crawler = PlaywrightCrawler(
        request_handler=router,
        max_requests_per_crawl=30 * target_pages,
        request_handler_timeout=timedelta(seconds=120),
    )

    initial_requests = [
        Request.from_url(
            url=f"https://www.welcometothejungle.com/fr/jobs?query=python&page={i}",
            label="default",
        )
        for i in range(1, target_pages + 1)
    ]

    await crawler.run(initial_requests)
    await crawler.export_data("storage/datasets/default/data.csv")
    print("Job data exported to dataset.csv")


if __name__ == "__main__":
    asyncio.run(main())

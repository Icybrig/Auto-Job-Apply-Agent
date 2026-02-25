import asyncio
from datetime import timedelta
from crawlee.crawlers import PlaywrightCrawler, BeautifulSoupCrawler
from crawlee import Request, ConcurrencySettings
import src.webcrawler.indeed_crawler
import src.webcrawler.wttj_crawler
from src.webcrawler.rooter import router


concurrency_settings = ConcurrencySettings(max_concurrency=1, desired_concurrency=1)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


async def main():
    wttj_crawler = PlaywrightCrawler(
        request_handler=router,
        request_handler_timeout=timedelta(seconds=120),
    )
    indeed_crawler = BeautifulSoupCrawler(
        request_handler=router,
        concurrency_settings=concurrency_settings,
        request_handler_timeout=timedelta(seconds=6000),
        ignore_http_error_status_codes={403, 404},
    )

    initial_requests = [
        Request.from_url(
            url="https://fr.indeed.com/jobs?q=data&l=France&start=0",
            label="Indeed_List",
            headers=_HEADERS,
        )
    ]

    await indeed_crawler.run(initial_requests)
    await indeed_crawler.export_data("storage/datasets/default/data.csv")
    print("Job data exported to dataset.csv")


if __name__ == "__main__":
    asyncio.run(main())

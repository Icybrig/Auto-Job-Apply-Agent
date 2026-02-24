from crawlee.crawlers import BeautifulSoupCrawler
from crawlee import Request, ConcurrencySettings
from .routes import router
import urllib.parse
import os


async def main(title: str, data_name: str, max_results: int = 100) -> None:
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {"keywords": title, "start": "0"}
    encoded_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    crawler = BeautifulSoupCrawler(
        request_handler=router,
        concurrency_settings=ConcurrencySettings(
            max_concurrency=2,
            max_tasks_per_minute=25,
        ),
    )

    initial_request = Request.from_url(encoded_url, user_data={'max_results': max_results})
    await crawler.run([initial_request])

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, f"{data_name}.csv")
    await crawler.export_data(output_file)
    print(f"CSV saved to: {output_file}")

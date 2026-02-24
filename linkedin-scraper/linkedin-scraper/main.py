from crawlee.crawlers import PlaywrightCrawler
from .routes import router
import urllib.parse
import os

# location: str
async def main(title: str, data_name: str) -> None:
    base_url = "https://www.linkedin.com/jobs/search"

    # URL encode the parameters
    params = {
        "keywords": title,
        # "location": location,
        # "trk": "public_jobs_jobs-search-bar_search-submit",
        # "position": "1",
        # "pageNum": "0"
    }
    encoded_params = urllib.parse.urlencode(params)
    encoded_url = f"{base_url}?{encoded_params}"

    # Initialize the crawler with anti-detection settings
    crawler = PlaywrightCrawler(
        request_handler=router,
        headless=False,  # headed mode reduces bot detection probability
        browser_type='chromium',
        browser_launch_options={
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ],
        },
    )

    # Run the crawler with the initial list of URLs
    await crawler.run([encoded_url])

    # Save the data to an absolute path so the file is always findable
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, f"{data_name}.csv")
    await crawler.export_data(output_file)
    print(f"CSV saved to: {output_file}")
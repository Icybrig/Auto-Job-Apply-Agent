from datetime import timedelta
from math import ceil
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from crawlee import ConcurrencySettings, Request
from crawlee.configuration import Configuration
from crawlee.crawlers import BeautifulSoupCrawler, PlaywrightCrawler
from crawlee.storages import RequestQueue

import src.webcrawler.indeed_crawler
import src.webcrawler.wttj_crawler
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


def _run_queue_alias(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def _extract_items(result: Any) -> list[dict[str, Any]]:
    items = getattr(result, "items", None)
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        return [item for item in result["items"] if isinstance(item, dict)]
    return []


def _latest_first(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: item.get("published_at") or "", reverse=True)


async def crawl_indeed_jobs(
    title: str = "data", location: str = "France"
) -> list[dict[str, Any]]:
    request_queue = await RequestQueue.open(alias=_run_queue_alias("indeed"))

    crawler = BeautifulSoupCrawler(
        request_handler=router,
        request_manager=request_queue,
        concurrency_settings=ConcurrencySettings(
            max_concurrency=1, desired_concurrency=1
        ),
        request_handler_timeout=timedelta(seconds=600),
        ignore_http_error_status_codes={403, 404},
    )

    requests: list[Request] = []

    params = {
        "q": title,
        "l": location,
        "start": 0,
        "sort": "date",
    }
    start_url = f"https://fr.indeed.com/jobs?{urlencode(params)}"
    requests.append(
        Request.from_url(
            url=start_url,
            label="Indeed_List",
            headers=_HEADERS,
        )
    )

    await crawler.run(requests)
    data_page = await crawler.get_data()
    items = _extract_items(data_page)
    indeed_items = [
        item for item in items if str(item.get("platform", "")).strip().lower() == "indeed"
    ]
    return _latest_first(indeed_items)


async def crawl_wttj_jobs(
    title: str = "data", location: str | None = None, count: int = 30
) -> list[dict[str, Any]]:
    target_count = max(1, count)
    page_size = 15
    pages = ceil(target_count / page_size)
    search_query = title if not location else f"{title} {location}"

    request_queue = await RequestQueue.open(alias=_run_queue_alias("wttj"))

    crawler = PlaywrightCrawler(
        request_handler=router,
        request_manager=request_queue,
        request_handler_timeout=timedelta(seconds=120),
        browser_launch_options={
            "chromium_sandbox": False,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"],
        },
        concurrency_settings=ConcurrencySettings(
            min_concurrency=1,
            desired_concurrency=1,
            max_concurrency=1,
        ),
        configuration=Configuration(
            disable_browser_sandbox=True,
            max_used_cpu_ratio=1.0,
            max_event_loop_delay=timedelta(milliseconds=500),
        ),
    )

    requests: list[Request] = []
    for page in range(1, pages + 1):
        params = {"query": search_query, "page": page, "sortBy": "mostRecent"}
        start_url = "https://www.welcometothejungle.com/fr/jobs" f"?{urlencode(params)}"
        requests.append(
            Request.from_url(
                url=start_url,
                label="WTTJ_List",
                headers=_HEADERS,
            )
        )

    await crawler.run(requests)
    data_page = await crawler.get_data()
    items = _extract_items(data_page)
    wttj_items = [
        item
        for item in items
        if str(item.get("platform", "")).strip().lower() in {"welcome to the jungle", "wttj"}
    ]
    return _latest_first(wttj_items)[:target_count]

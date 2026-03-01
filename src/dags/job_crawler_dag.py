import json
import os
from datetime import datetime, timedelta
from urllib import parse, request

from airflow.decorators import dag, task

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_CRAWL_TITLE = "data scientist"
DEFAULT_CRAWL_LOCATION = "Paris"
DEFAULT_CRAWL_COUNT = 30


def _runtime_config() -> tuple[str, str, str, int]:
    api_base_url = os.getenv("JOB_API_BASE_URL", DEFAULT_API_BASE_URL).strip()
    crawl_title = os.getenv("CRAWL_TITLE", DEFAULT_CRAWL_TITLE).strip()
    crawl_location = os.getenv("CRAWL_LOCATION", DEFAULT_CRAWL_LOCATION).strip()
    try:
        crawl_count = int(os.getenv("CRAWL_COUNT", str(DEFAULT_CRAWL_COUNT)))
    except ValueError:
        crawl_count = DEFAULT_CRAWL_COUNT
    return api_base_url, crawl_title, crawl_location, max(1, crawl_count)


def _post_json(url: str, payload: dict | None = None) -> list[dict]:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url=url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=1800) as response:
        return json.loads(response.read().decode("utf-8"))


@dag(
    dag_id="job_crawler_pipeline",
    start_date=datetime(2026, 2, 28),
    schedule=timedelta(hours=6),
    catchup=False,
    max_active_runs=1,
    tags=["crawler", "jobs"],
)
def job_crawler_pipeline():
    @task
    def run_indeed_crawler() -> list[dict]:
        api_base_url, crawl_title, crawl_location, crawl_count = _runtime_config()
        qs = parse.urlencode(
            {"title": crawl_title, "location": crawl_location, "count": crawl_count}
        )
        url = f"{api_base_url}/crawler/indeed?{qs}"
        return _post_json(url)

    @task
    def run_wttj_crawler() -> list[dict]:
        api_base_url, crawl_title, crawl_location, crawl_count = _runtime_config()
        qs = parse.urlencode(
            {"title": crawl_title, "location": crawl_location, "count": crawl_count}
        )
        url = f"{api_base_url}/crawler/wttj?{qs}"
        return _post_json(url)

    @task
    def save_indeed(jobs: list[dict]) -> int:
        api_base_url, _, _, _ = _runtime_config()
        if not jobs:
            return 0
        saved_rows = _post_json(f"{api_base_url}/job/bulk", {"jobs": jobs})
        return len(saved_rows)

    @task
    def save_wttj(jobs: list[dict]) -> int:
        api_base_url, _, _, _ = _runtime_config()
        if not jobs:
            return 0
        saved_rows = _post_json(f"{api_base_url}/job/bulk", {"jobs": jobs})
        return len(saved_rows)

    indeed_jobs = run_indeed_crawler()
    wttj_jobs = run_wttj_crawler()

    save_indeed(indeed_jobs)
    save_wttj(wttj_jobs)


job_crawler_pipeline()

from operator import and_
from typing import Optional
from sqlalchemy import or_, and_
from fastapi import FastAPI, Depends, Query
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.app.schema import JobResponse, JobCreate, JobBulkCreate
from src.db.model import Job
from typing import List
from src.webcrawler.service import crawl_indeed_jobs, crawl_wttj_jobs

app = FastAPI(title="Job_API")
job_router = APIRouter(prefix="/job")
crawler_router = APIRouter(prefix="/crawler")


@job_router.post("/", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Job)
        .filter(
            Job.platform == job.platform, Job.url == job.url, Job.title == job.title
        )
        .first()
    )
    if existing:
        return existing

    new_job = Job(**job.model_dump())
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


@job_router.post("/bulk", response_model=List[JobResponse])
def create_jobs(jobs: JobBulkCreate, db: Session = Depends(get_db)):
    results: list[Job] = []

    for job in jobs.jobs:
        existing = (
            db.query(Job)
            .filter(
                Job.platform == job.platform, Job.url == job.url, Job.title == job.title
            )
            .first()
        )
        if existing:
            results.append(existing)
            continue

        row = Job(**job.model_dump())
        db.add(row)
        results.append(row)

    db.commit()
    for row in results:
        db.refresh(row)
    return results


@job_router.get("/", response_model=List[JobResponse])
def get_job(
    title: Optional[str] = None,
    location: Optional[str] = None,
    exp_level: Optional[str] = None,
    contract: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    jobs = query.all()
    conditions = []
    if title:
        conditions.append(Job.title.ilike(f"%{title}%"))
    if location:
        conditions.append(Job.location.ilike(f"%{location}%"))
    if exp_level:
        conditions.append(Job.exp_level == exp_level)
    if contract:
        conditions.append(Job.contract == contract)
    if conditions:
        jobs = query.filter(and_(*conditions)).all()
    return jobs


@crawler_router.post("/indeed", response_model=List[JobCreate])
async def run_indeed_crawler(
    title: str = "data scientist",
    location: str = "Paris",
):
    jobs = await crawl_indeed_jobs(title=title, location=location)
    return [JobCreate(**job) for job in jobs]


@crawler_router.post("/wttj", response_model=List[JobCreate])
async def run_wttj_crawler(
    title: str = "data scientist",
    location: Optional[str] = "Paris",
    count: int = Query(default=30, ge=1, le=300),
):
    jobs = await crawl_wttj_jobs(title=title, location=location, count=count)
    return [JobCreate(**job) for job in jobs]

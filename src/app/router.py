from typing import Optional
from sqlalchemy import or_
from fastapi import FastAPI, Depends
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.app.schema import JobResponse, JobCreate
from src.db.model import Job
from typing import List

app = FastAPI(title="Job_API")
job_router = APIRouter(prefix="/job")


@job_router.post("/", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    new_job = Job(**job.model_dump())
    db.add(new_job)
    db.commit()
    return new_job


@job_router.get("/", response_model=List[JobResponse])
def get_job(
    title: Optional[str] = None,
    location: Optional[str] = None,
    exp_level: Optional[str] = None,
    contract: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Job)
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
        jobs = query.filter(or_(*conditions)).all()
    return jobs

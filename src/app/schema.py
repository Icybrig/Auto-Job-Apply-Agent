from datetime import datetime
from pydantic import BaseModel, ConfigDict
from src.db.model import PlatformType


class JobBase(BaseModel):
    platform: PlatformType
    title: str
    company: str
    location: str
    contract: str
    salary: int
    currency: str
    job_desc: str
    job_reqs: str
    exp_level: str
    edu_level: str
    published_at: str


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

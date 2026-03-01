from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from src.db.model import PlatformType
from typing import Optional


class JobBase(BaseModel):
    url: str
    platform: PlatformType
    title: str
    company: str
    location: Optional[str] = None
    contract: Optional[str] = None
    salary: Optional[int] = None
    currency: Optional[str] = None
    job_desc: Optional[str] = None
    job_reqs: Optional[str] = None
    exp_level: Optional[str] = None
    edu_level: Optional[str] = None
    published_at: Optional[str] = None

    @field_validator("platform", mode="before")
    @classmethod
    def normalize_platform(cls, value):
        if isinstance(value, PlatformType):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"wttj", "welcome to the jungle", "welcometothejungle"}:
            return PlatformType.WTTJ
        if normalized in {"Indeed", "indeed"}:
            return PlatformType.Indeed
        if normalized in {"Linkedin", "linkedin"}:
            return PlatformType.Linkedin
        return value

    @field_validator("salary", mode="before")
    @classmethod
    def normalize_salary(cls, value):
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            return int(value)


class JobCreate(JobBase):
    pass


class JobBulkCreate(BaseModel):
    jobs: list[JobCreate]


class JobResponse(JobBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime

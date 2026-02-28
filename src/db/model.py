from arrow import now
from sqlalchemy import Column, Enum, Text, Integer, String, func, DateTime
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class PlatformType(enum.Enum):
    WTTJ = "Welcome to the jungle"
    Indeed = "Indeed"
    Linkedin = "Linkedin"


class Job(Base):
    __tablename__ = "job"
    id = Column(Integer, primary_key=True, nullable=True, index=True)
    platform = Column(Enum(PlatformType))
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    location = Column(String)
    contract = Column(String)
    salary = Column(Integer)
    currency = Column(String)
    job_desc = Column(Text)
    job_reqs = Column(Text)
    exp_level = Column(String)
    edu_level = Column(String)
    published_at = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

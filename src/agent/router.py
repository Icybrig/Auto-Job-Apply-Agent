from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.db.model import Job
from src.app.schema import GenerateRequest, GenerateResponse
from src.agent.service import generate_cv, generate_letter

agent_router = APIRouter(prefix="/agent")


@agent_router.post("/generate", response_model=GenerateResponse)
def generate_documents(request: GenerateRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")

    job_dict = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "exp_level": job.exp_level,
        "job_desc": job.job_desc,
        "job_reqs": job.job_reqs,
    }
    profile_dict = request.user_profile.model_dump()

    cv = generate_cv(job_dict, profile_dict)
    letter = generate_letter(job_dict, profile_dict)

    return GenerateResponse(cv_markdown=cv, letter_markdown=letter)

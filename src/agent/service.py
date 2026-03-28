import os
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def _call_ollama(prompt: str) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=600,
    )
    response.raise_for_status()
    return response.json()["response"]


def generate_cv(job: dict, profile: dict) -> str:
    gender_note = ""
    if profile.get("gender") == "Femme":
        gender_note = "Use feminine adjective agreement throughout (e.g. motivée, diplômée, expérimentée)."

    prompt = f"""You are an expert CV writer. Write a professional, tailored CV in markdown format.
Use the same language as the job description (French if the job is in French, English if in English).
{gender_note}

Job: {job.get('title')} at {job.get('company')}, {job.get('location')}
Experience required: {job.get('exp_level', 'Not specified')}
Job description:
{job.get('job_desc', 'Not available')}

Requirements:
{job.get('job_reqs', 'Not available')}

Candidate profile:
- Name: {profile['name']}
- Skills: {profile['skills']}
- Work experience: {profile['experience']}
- Projects: {profile['projects']}
- Education: {profile['education']}
- Languages: {profile['languages']}

Generate a complete, well-structured CV in markdown. Include sections for: contact info, skills, work experience, projects, education, and languages."""

    return _call_ollama(prompt)


def generate_letter(job: dict, profile: dict) -> str:
    gender_note = ""
    if profile.get("gender") == "Femme":
        gender_note = "Use feminine form throughout (e.g. motivée, diplômée, expérimentée, enthousiaste)."

    prompt = f"""You are an expert at writing professional motivation letters.
Use the same language as the job description (French if the job is in French, English if in English).
{gender_note}

Job: {job.get('title')} at {job.get('company')}, {job.get('location')}
Requirements:
{job.get('job_reqs', 'Not available')}

Candidate: {profile['name']}
Work experience: {profile['experience']}
Projects: {profile['projects']}
Skills: {profile['skills']}
Education: {profile['education']}

Write a compelling 3-4 paragraph motivation letter. Be specific about why this candidate fits this role.
Do not use generic filler phrases. Address the letter to the hiring team."""

    return _call_ollama(prompt)

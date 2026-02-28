from src.db.model import Base
from src.db.database import engine
from fastapi import FastAPI
from src.app.router import job_router

app = FastAPI()
app.include_router(job_router)
Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {"status": "success", "message": "Job API is active at /job/"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

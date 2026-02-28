from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()
DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()

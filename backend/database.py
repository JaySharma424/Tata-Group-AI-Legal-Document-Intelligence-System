import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
load_dotenv()

# DATABASE_URL from environment variable, with fallback for local development
# Format: postgresql://user:password@host:port/database
# In production (Render), set DATABASE_URL as an environment variable
# Example: postgresql://postgres:password@db-host:5432/tata_ai_legal
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/tata_ai_legal")

# SQLite needs check_same_thread=False for multithreading
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
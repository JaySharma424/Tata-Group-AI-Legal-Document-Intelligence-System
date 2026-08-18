import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# DATABASE_URL from environment variable, with fallback for local development
# Format: postgresql://user:password@host:port/database
# In production, set DATABASE_URL as an environment variable
# Example: postgresql://postgres:password@db-host:5432/tata_ai_legal
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/tata_ai_legal")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
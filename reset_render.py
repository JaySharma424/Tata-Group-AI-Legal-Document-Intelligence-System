from sqlalchemy import create_engine
from backend.database import Base
from backend import models

# 1. Paste your copied External Database URL between the quotes below
EXTERNAL_DB_URL = "postgresql://tata_admin:85HYKR7IdWcHazZ9Y8CT7gHRnZUM2Iaj@dpg-d9s1kp7avr4c73a9h90g-a.singapore-postgres.render.com/tata_legal_db"

# Ensure protocol prefix matches SQLAlchemy requirements
if EXTERNAL_DB_URL.startswith("postgres://"):
    EXTERNAL_DB_URL = EXTERNAL_DB_URL.replace("postgres://", "postgresql://", 1)

print("🔌 Connecting to Render PostgreSQL database...")
engine = create_engine(EXTERNAL_DB_URL)

print("⚠️  Dropping all existing tables...")
Base.metadata.drop_all(bind=engine)

print("✨ Recreating clean database schema...")
Base.metadata.create_all(bind=engine)

print("✅ Success! Your Render PostgreSQL database has been completely reset.")
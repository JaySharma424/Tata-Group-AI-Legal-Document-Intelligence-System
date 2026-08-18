import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.database import get_db
from backend.models import UserModel, SessionModel

# Security Configuration
SECRET_KEY = "tata_enterprise_secure_legal_intelligence_platform_secret_key_2026_safe"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

router = APIRouter()

# Authorized corporate email accounts permitted to hold elevated Admin roles
# Using shared AUTHORIZED_ADMIN_EMAILS from backend.api.v1.admin_auth
from backend.api.v1.admin_auth import AUTHORIZED_ADMIN_EMAILS
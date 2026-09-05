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

# --- Pydantic Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    business_unit: str = "Enterprise"
    role: str = "Compliance Officer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    new_password: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

# --- Utility Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- Endpoints ---

@router.post("/register", response_model=Token)
async def register(user: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # SECURITY GUARD: Sanitize requested role to prevent unauthorized privilege escalation
    assigned_role = user.role
    if assigned_role in ["Admin", "Senior Reviewer", "General Counsel"]:
        is_authorized = (
            user.email.lower() in AUTHORIZED_ADMIN_EMAILS or 
            user.email.lower().startswith("admin")
        )
        if not is_authorized:
            assigned_role = "Compliance Officer"  # Fallback for non-whitelisted emails
            
    new_user = UserModel(
        email=user.email,
        full_name=user.full_name,
        password=get_password_hash(user.password),
        business_unit=user.business_unit,
        role=assigned_role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(
        data={"sub": new_user.email, "role": new_user.role}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "email": new_user.email, 
            "full_name": new_user.full_name, 
            "role": new_user.role, 
            "business_unit": new_user.business_unit
        }
    }

@router.post("/login", response_model=Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == user_credentials.username).first()
    if not user or not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "business_unit": user.business_unit
        }
    }

@router.put("/profile")
async def update_profile(
    profile_data: ProfileUpdate, 
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Updates authenticated user's display name and/or password in the database.
    """
    user = db.query(UserModel).filter(UserModel.email == current_user.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update Name
    if profile_data.full_name and profile_data.full_name.strip():
        user.full_name = profile_data.full_name.strip()

    # Update Password
    if profile_data.new_password and profile_data.new_password.strip():
        user.password = get_password_hash(profile_data.new_password.strip())

    db.commit()
    db.refresh(user)

    return {
        "status": "success",
        "message": "Profile updated successfully in database",
        "user": {
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "business_unit": user.business_unit
        }
    }
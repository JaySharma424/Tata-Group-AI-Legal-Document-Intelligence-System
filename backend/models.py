import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base

# ==================== USER & AUTH MODELS ====================

class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False) # Will store the hashed password
    business_unit = Column(String, nullable=False)
    role = Column(String, nullable=False)
    
    # NEW: Account status and tracking concepts
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # NEW: Relational Mappings 
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogModel", back_populates="user")
    documents_uploaded = relationship("DocumentModel", back_populates="uploader")


class SessionModel(Base):
    """Session model for managing JWT tokens and user logins"""
    __tablename__ = "sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    user = relationship("UserModel", back_populates="sessions")


# ==================== DOCUMENT MODELS ====================

class DocumentModel(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}

    job_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    business_unit = Column(String, nullable=False)
    document_category = Column(String, nullable=False)
    
    document_type = Column(String, default="Unknown")
    counterparty = Column(String, nullable=True)
    jurisdiction = Column(String, nullable=True) 
    confidentiality_level = Column(String, nullable=False, default="Standard")
    review_priority = Column(String, nullable=False, default="Normal")
    
    ocr_confidence = Column(Float, default=100.0)
    pages = Column(Integer, default=1)
    entities_detected = Column(Integer, default=0)
    requires_manual_review = Column(Boolean, default=False)
    
    # 🚀 NEW: RAGAS AI Confidence Metrics
    ragas_faithfulness = Column(Float, nullable=True, default=0.0)
    ragas_answer_relevancy = Column(Float, nullable=True, default=0.0)
    ragas_context_precision = Column(Float, nullable=True, default=0.0)
    ragas_context_recall = Column(Float, nullable=True, default=0.0)
    ragas_answer_correctness = Column(Float, nullable=True, default=0.0)
    
    uploaded_by = Column(String, ForeignKey("users.email", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    uploader = relationship("UserModel", back_populates="documents_uploaded")
    clauses = relationship("ClauseModel", back_populates="document", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogModel", back_populates="document", cascade="all, delete-orphan")


class ClauseModel(Base):
    __tablename__ = "extracted_clauses"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    
    # CONCEPT FIX: Converted to a strict Foreign Key linked to DocumentModel
    job_id = Column(String, ForeignKey("documents.job_id", ondelete="CASCADE"), index=True, nullable=False)
    
    clause_type = Column(String, nullable=False)
    extracted_text = Column(String, nullable=False)
    confidence_score = Column(Float, default=0.0)
    risk_level = Column(String, nullable=False)
    risk_rationale = Column(String, nullable=True)
    involved_party = Column(String, nullable=True)
    
    # Expanded Clause Details (Stage 3 Gap Fix)
    page_reference = Column(String, default="N/A")
    obligation_owner = Column(String, default="N/A")
    recommended_action = Column(String, default="Review")
    
    # CONCEPT FIX: Added Edit Tracking Capabilities
    edited_text = Column(Text, nullable=True)
    edited_at = Column(DateTime, nullable=True)
    edited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # NEW: Relational Mappings
    document = relationship("DocumentModel", back_populates="clauses")
    edited_by_user = relationship("UserModel")


# ==================== AUDIT & REVIEW MODELS ====================

class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    
    # CONCEPT FIX: Converted to strict Foreign Keys linked to DocumentModel and UserModel
    job_id = Column(String, ForeignKey("documents.job_id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, ForeignKey("users.email", ondelete="CASCADE"), nullable=False)
    
    action = Column(String, nullable=False)  # e.g., APPROVED, REJECTED, ESCALATED
    notes = Column(String, nullable=True)
    
    # Enhanced Approval Workflow (Stage 5 Gap Fix)
    reviewer_comment = Column(String, nullable=True)
    escalation_status = Column(Boolean, default=False)
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # NEW: Relational Mappings
    document = relationship("DocumentModel", back_populates="audit_logs")
    user = relationship("UserModel", back_populates="audit_logs")

# ==================== SYSTEM CONFIGURATION ====================

class SystemConfigModel(Base):
    """Stores global system configurations dynamically."""
    __tablename__ = "system_config"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, unique=True, index=True, nullable=False) # e.g., "default"
    
    llm_model = Column(String, default="gemini-3.5-flash")
    embedding_model = Column(String, default="gemini-embedding-001")
    api_key = Column(String, nullable=True) # Securely stores the active key
    
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
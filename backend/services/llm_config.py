import os
from backend.database import SessionLocal
from backend.models import SystemConfigModel

def get_llm_config():
    """Retrieves active LLM configuration from the PostgreSQL database."""
    db = SessionLocal()
    try:
        config = db.query(SystemConfigModel).filter(SystemConfigModel.config_key == "default").first()
        if config:
            return {
                "llm_model": config.llm_model,
                "embedding_model": config.embedding_model,
                "api_key": config.api_key or os.getenv("GEMINI_API_KEY", "")
            }
            
        # Fallback if DB is completely empty
        return {
            "llm_model": "gemini-3.5-flash",
            "embedding_model": "gemini-embedding-001",
            "api_key": os.getenv("GEMINI_API_KEY", "")
        }
    except Exception as e:
        print(f"Database Config Read Error: {e}")
        return {
            "llm_model": "gemini-3.5-flash",
            "embedding_model": "gemini-embedding-001",
            "api_key": os.getenv("GEMINI_API_KEY", "")
        }
    finally:
        db.close()

def update_llm_config(new_key: str = None, llm_model: str = None, embedding_model: str = None):
    """Updates runtime configuration and permanently persists to PostgreSQL."""
    db = SessionLocal()
    try:
        # Check if config exists, if not create it
        config = db.query(SystemConfigModel).filter(SystemConfigModel.config_key == "default").first()
        if not config:
            config = SystemConfigModel(config_key="default")
            db.add(config)
        
        # Update the provided values
        if new_key and new_key.strip():
            config.api_key = new_key.strip()
            os.environ["GEMINI_API_KEY"] = new_key.strip() # Keep env updated for immediate access
            
        if llm_model and llm_model.strip():
            config.llm_model = llm_model.strip()
            
        if embedding_model and embedding_model.strip():
            config.embedding_model = embedding_model.strip()
            
        db.commit()
        db.refresh(config)
        
        return {
            "llm_model": config.llm_model,
            "embedding_model": config.embedding_model,
            "api_key": config.api_key
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
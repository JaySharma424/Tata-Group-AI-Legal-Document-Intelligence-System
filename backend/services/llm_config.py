from backend.database import SessionLocal, engine
from backend.models import SystemConfigModel

def ensure_system_config_table():
    """Ensure SystemConfigModel table exists in PostgreSQL.

    This is called lazily on first use rather than at module import time,
    avoiding issues when the database is not yet initialized.
    """
    try:
        SystemConfigModel.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        # Table may already exist or other transient errors - not critical
        pass

def get_llm_config():
    """
    Retrieves active LLM configuration STRICTLY from the PostgreSQL database.
    Environment variable fallbacks have been removed to ensure Admin Portal supremacy.
    """
    db = SessionLocal()
    try:
        # Ensure table exists before querying
        ensure_system_config_table()

        config = db.query(SystemConfigModel).filter(SystemConfigModel.config_key == "default").first()
        if config:
            return {
                "llm_model": config.llm_model,
                "embedding_model": config.embedding_model,
                "api_key": config.api_key  # 🚀 Removed os.getenv fallback completely
            }

        # Fallback if DB is completely empty (System stays offline without a key)
        return {
            "llm_model": "gemini-3.5-flash",
            "embedding_model": "gemini-embedding-001",
            "api_key": "" # 🚀 Blank by default until Admin configures it
        }
    except Exception as e:
        print(f"Database Config Read Error: {e}")
        return {
            "llm_model": "gemini-3.5-flash",
            "embedding_model": "gemini-embedding-001",
            "api_key": ""
        }
    finally:
        db.close()

def update_llm_config(new_key: str = None, llm_model: str = None, embedding_model: str = None):
    """Updates runtime configuration and permanently persists to PostgreSQL ONLY."""
    db = SessionLocal()
    try:
        # Ensure table exists before updating
        ensure_system_config_table()

        # Check if config exists, if not create it
        config = db.query(SystemConfigModel).filter(SystemConfigModel.config_key == "default").first()
        if not config:
            config = SystemConfigModel(config_key="default")
            db.add(config)

        # Update the provided values
        if new_key and new_key.strip():
            config.api_key = new_key.strip()
            # 🚀 Removed os.environ overwrite to prevent cross-contamination of keys

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

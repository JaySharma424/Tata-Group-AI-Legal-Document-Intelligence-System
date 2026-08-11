import os
import json

CONFIG_FILE_PATH = "./backend/storage/llm_config.json"

DEFAULT_CONFIG = {
    "llm_model": "gemini-3.5-flash",
    "embedding_model": "gemini-embedding-001",
    "api_key": os.getenv("GEMINI_API_KEY", "")
}

def get_llm_config():
    """Retrieves active LLM configuration from persistent storage or env defaults."""
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"Error reading LLM config: {e}")
    return DEFAULT_CONFIG

def update_llm_config(new_key: str = None, llm_model: str = None, embedding_model: str = None):
    """Updates runtime configuration and persists to disk."""
    config = get_llm_config()
    
    if new_key and new_key.strip():
        config["api_key"] = new_key.strip()
        os.environ["GEMINI_API_KEY"] = new_key.strip()
        
    if llm_model and llm_model.strip():
        config["llm_model"] = llm_model.strip()
        
    if embedding_model and embedding_model.strip():
        config["embedding_model"] = embedding_model.strip()
        
    os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
        
    return config
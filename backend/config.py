import os
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

AVATARS_DIR = DATA_DIR / "avatars"
AVATARS_DIR.mkdir(exist_ok=True)

VECTOR_DIR = DATA_DIR / "vector_db"
VECTOR_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "assistant.db"

# Load .env if present
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

class Config:
    PROJECT_NAME = "AI Personal Assistant"
    VERSION = "1.0.0"
    
    # Supported LLM Providers: "openrouter", "gemini", "groq", "openai", "ollama"
    DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "openrouter")
    
    # API Keys (Free options: OpenRouter, Google Gemini, Groq, Ollama)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Ollama settings (Local, free, offline)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

    # Default Models
    DEFAULT_OPENROUTER_MODEL = os.getenv("DEFAULT_OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")
    DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-2.5-flash-lite")
    DEFAULT_GROQ_MODEL = os.getenv("DEFAULT_GROQ_MODEL", "openai/gpt-oss-20b")
    DEFAULT_OPENAI_MODEL = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-4o-mini")

    # Memory Settings
    MAX_SHORT_TERM_MESSAGES = int(os.getenv("MAX_SHORT_TERM_MESSAGES", "20"))
    
    # RAG Settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
    TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "4"))
    
    # Assistant Persona
    ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Aura")
    USER_NAME = os.getenv("USER_NAME", "User")
    
    @classmethod
    def get_active_model(cls, provider: str = None) -> str:
        prov = provider or cls.DEFAULT_PROVIDER
        if prov == "openrouter":
            return cls.DEFAULT_OPENROUTER_MODEL
        elif prov == "gemini":
            return cls.DEFAULT_GEMINI_MODEL
        elif prov == "groq":
            return cls.DEFAULT_GROQ_MODEL
        elif prov == "openai":
            return cls.DEFAULT_OPENAI_MODEL
        elif prov == "ollama":
            return cls.OLLAMA_MODEL
        return "groq/compound-mini"

config = Config()

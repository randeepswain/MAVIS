import os

try:
    from pydantic_settings import BaseSettings
except ImportError:
    class BaseSettings:
        pass

class Settings(BaseSettings):
    PROJECT_NAME: str = "MAVIS — Multi-Agent Voice Intake System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Database
    # Defaults to SQLite+aiosqlite for zero-setup local execution, supports PostgreSQL asyncpg:
    # e.g., postgresql+asyncpg://postgres:postgres@localhost:5432/mavis
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./mavis.db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    USE_IN_MEMORY_REDIS_FALLBACK: bool = True
    SLOT_HOLD_TTL_SECONDS: int = int(os.getenv("SLOT_HOLD_TTL_SECONDS", "180")) # 3 minutes soft-hold
    
    # Security / Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "mavis-ultra-secure-jwt-secret-key-2026-ramaiah")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # LLM / Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    
    # Emergency Call Bridge
    EMERGENCY_DESK_PHONE: str = os.getenv("EMERGENCY_DESK_PHONE", "+91-80-2360-1234")
    EMERGENCY_FALLBACK_1: str = "112"
    EMERGENCY_FALLBACK_2: str = "108"
    
    # Audio & Telephony
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "wss://livekit.mavis.local")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "devkey")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "secret")

settings = Settings()

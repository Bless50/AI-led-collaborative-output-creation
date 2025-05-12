import os
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings
    """
    # API configuration
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "AI-Led Collaborative Report Generator"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # API keys
    ANTHROPIC_API_KEY: str
    TAVILY_API_KEY: Optional[str] = None
    MEM0_API_KEY: str
    
    # No session expiration to prevent data loss
    
    # Validate CORS origins
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Create settings instance
settings = Settings()

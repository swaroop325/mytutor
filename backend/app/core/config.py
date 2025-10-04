from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "myTutor"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173"]

    # AWS Configuration
    AWS_REGION: str = "us-east-1"

    # Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # AgentCore MCP
    MCP_SERVER_URL: Optional[str] = None

    # Amazon DCV
    DCV_SERVER_URL: Optional[str] = None
    DCV_SESSION_ID: Optional[str] = None

    # AgentCore Runtime
    AGENTCORE_URL: str = "http://localhost:8080"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env


settings = Settings()

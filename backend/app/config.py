import os


class Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./ridley.db")
    jwt_secret = os.getenv("JWT_SECRET", "ridley-dev-secret")
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL", "").strip()
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    chroma_path = os.getenv("CHROMA_PATH", "./chroma_data")
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    token_hours = 12
    otp_minutes = 5
    otp_max_attempts = 3
    retrieval_floor = 0.32


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ════════════════════════════════════════════════════════════════
    # Application Configuration
    # ════════════════════════════════════════════════════════════════
    app_name: str = "AntonRX"
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"

    # ════════════════════════════════════════════════════════════════
    # AI Configuration (Claude/Anthropic primary, OpenAI fallback)
    # ════════════════════════════════════════════════════════════════
    anthropic_api_key: Optional[str] = None  # Claude API key (primary)
    claude_model: str = "claude-3-5-sonnet-20241022"
    
    openai_api_key: Optional[str] = None  # OpenAI API key (optional fallback)
    openai_model: str = "gpt-4-turbo"
    openai_embedding_model: str = "text-embedding-3-small"
    ai_extraction_timeout_seconds: int = 60
    ai_cache_enabled: bool = True

    # ════════════════════════════════════════════════════════════════
    # JWT / Authentication
    # ════════════════════════════════════════════════════════════════
    secret_key: Optional[str] = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ════════════════════════════════════════════════════════════════
    # Supabase Configuration (PostgreSQL + Vector DB)
    # ════════════════════════════════════════════════════════════════
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    database_url: Optional[str] = None

    # ════════════════════════════════════════════════════════════════
    # File Upload Security
    # ════════════════════════════════════════════════════════════════
    max_upload_size_mb: int = 10
    allowed_file_types: str = "pdf,html,htm,png,jpg,jpeg"
    file_upload_directory: str = "./uploads"
    enable_virus_scan: bool = False

    # ════════════════════════════════════════════════════════════════
    # Rate Limiting
    # ════════════════════════════════════════════════════════════════
    rate_limit_per_minute: int = 10
    rate_limit_extraction_per_day: int = 100

    # ════════════════════════════════════════════════════════════════
    # Pydantic Configuration
    # ════════════════════════════════════════════════════════════════
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    @property
    def allowed_types_list(self) -> list[str]:
        """Return allowed file extensions as a Python list."""
        return [ext.strip().lower() for ext in self.allowed_file_types.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Return max upload size in bytes."""
        if self.max_upload_size_mb <= 0:
            raise ValueError("max_upload_size_mb must be positive")
        return self.max_upload_size_mb * 1024 * 1024


# ════════════════════════════════════════════════════════════════
# Singleton Pattern - Get Settings
# ════════════════════════════════════════════════════════════════
@lru_cache()
def get_settings() -> Settings:
    """Return singleton instance of Settings."""
    return Settings()


# ════════════════════════════════════════════════════════════════
# Quick Test
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    settings = get_settings()
    print("✓ App Configuration Loaded Successfully")
    print(f"  App Name: {settings.app_name}")
    print(f"  Environment: {settings.environment}")
    print(f"  Claude Model: {settings.claude_model}")
    print(f"  Max Upload Size: {settings.max_upload_size_mb} MB")
    print(f"  Allowed File Types: {settings.allowed_file_types}")
    print(f"  Rate Limit: {settings.rate_limit_per_minute} req/min")
    print("Allowed file types:", settings.allowed_types_list)
    print("Max upload size (bytes):", settings.max_upload_size_bytes)
    print("Supabase URL:", settings.supabase_url)
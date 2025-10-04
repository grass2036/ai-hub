"""
AI Hub Platform Settings
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置设置"""
    
    # =============================================================================
    # Basic App Configuration
    # =============================================================================
    
    app_name: str = "AI Hub Platform"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    
    # API Documentation
    enable_api_docs: bool = Field(default=True, env="ENABLE_API_DOCS")
    
    # =============================================================================
    # AI API Keys
    # =============================================================================
    
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    claude_api_key: Optional[str] = Field(default=None, env="CLAUDE_API_KEY")
    
    # =============================================================================
    # Database Configuration
    # =============================================================================
    
    database_url: str = Field(
        default="sqlite:///./data/ai_hub.db",
        env="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Vector Database (Supabase)
    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(default=None, env="SUPABASE_ANON_KEY")
    
    # =============================================================================
    # Security Configuration
    # =============================================================================
    
    jwt_secret_key: str = Field(default="jwt-dev-secret", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        env="CORS_ORIGINS"
    )
    
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1,0.0.0.0",
        env="ALLOWED_HOSTS"
    )
    
    # =============================================================================
    # AgentFlow Configuration
    # =============================================================================
    
    max_concurrent_agents: int = Field(default=10, env="MAX_CONCURRENT_AGENTS")
    task_timeout: int = Field(default=300, env="TASK_TIMEOUT")  # 5 minutes
    enable_agent_monitoring: bool = Field(default=True, env="ENABLE_AGENT_MONITORING")
    
    # =============================================================================
    # File Upload Configuration
    # =============================================================================
    
    upload_path: str = Field(default="./data/uploads", env="UPLOAD_PATH")
    max_upload_size: int = Field(default=10 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 10MB
    allowed_file_types: str = Field(
        default=".pdf,.docx,.txt,.md,.json",
        env="ALLOWED_FILE_TYPES"
    )
    
    # =============================================================================
    # Performance & Monitoring
    # =============================================================================
    
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    enable_response_cache: bool = Field(default=True, env="ENABLE_RESPONSE_CACHE")
    
    # API Rate Limiting
    rate_limit_requests: int = Field(default=1000, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=3600, env="RATE_LIMIT_PERIOD")  # 1 hour
    
    # =============================================================================
    # Logging Configuration
    # =============================================================================
    
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # =============================================================================
    # Email Configuration (Optional)
    # =============================================================================
    
    smtp_server: Optional[str] = Field(default=None, env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    
    # =============================================================================
    # Development Configuration
    # =============================================================================
    
    reload_on_change: bool = Field(default=True, env="RELOAD_ON_CHANGE")
    show_sql_queries: bool = Field(default=False, env="SHOW_SQL_QUERIES")
    test_database_url: str = Field(default="sqlite:///./data/test_ai_hub.db", env="TEST_DATABASE_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_database_url(self) -> str:
        """获取数据库URL"""
        return self.database_url
    
    def get_redis_url(self) -> str:
        """获取Redis URL"""
        return self.redis_url
    
    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """检查是否为开发环境"""
        return self.environment.lower() == "development"
    
    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的源"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def validate_ai_keys(self) -> dict:
        """验证AI API密钥配置"""
        keys_status = {
            "openrouter": bool(self.openrouter_api_key),
            "gemini": bool(self.gemini_api_key),
            "openai": bool(self.openai_api_key),
            "claude": bool(self.claude_api_key),
        }
        return keys_status


@lru_cache()
def get_settings() -> Settings:
    """获取设置实例（缓存）"""
    return Settings()
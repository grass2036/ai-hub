"""
生产环境配置管理模块
Week 6 Day 4: 生产环境准备和部署配置 - 生产环境配置
实现生产环境配置管理、环境变量管理、部署配置等功能
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import yaml
import json
from datetime import datetime
import secrets
import hashlib
import base64

logger = logging.getLogger(__name__)

class Environment(Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str
    port: int
    name: str
    username: str
    password: str
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    ssl_mode: str = "require"
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

@dataclass
class RedisConfig:
    """Redis配置"""
    host: str
    port: int
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 100
    retry_on_timeout: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    ssl: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    cors_origins: List[str] = field(default_factory=list)
    cors_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 1000
    rate_limit_window: int = 3600
    api_key_header: str = "X-API-Key"
    encryption_key: str = ""

@dataclass
class LoggingConfig:
    """日志配置"""
    level: LogLevel
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5
    enable_console: bool = True
    enable_file: bool = True
    enable_json: bool = False
    enable_structlog: bool = True
    external_services: Dict[str, str] = field(default_factory=dict)

@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = True
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    metrics_path: str = "/metrics"
    jaeger_enabled: bool = True
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    health_check_enabled: bool = True
    health_check_path: str = "/health"
    performance_monitoring: bool = True
    alert_webhook_url: Optional[str] = None

@dataclass
class EmailConfig:
    """邮件配置"""
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool = True
    from_email: str
    from_name: str = "AI Hub Platform"
    support_email: str = "support@aihub.com"

@dataclass
class StorageConfig:
    """存储配置"""
    upload_dir: str = "/app/uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".doc", ".docx"
    ])
    enable_s3: bool = False
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None

@dataclass
class ProductionConfig:
    """生产环境完整配置"""
    environment: Environment
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False

    # 子配置
    database: DatabaseConfig
    redis: RedisConfig
    security: SecurityConfig
    logging: LoggingConfig
    monitoring: MonitoringConfig
    email: Optional[EmailConfig] = None
    storage: StorageConfig

    # 应用配置
    api_version: str = "v1"
    api_prefix: str = "/api"
    docs_enabled: bool = False
    openapi_url: str = "/docs"

    # 性能配置
    enable_compression: bool = True
    compression_level: int = 6
    enable_caching: bool = True
    cache_ttl: int = 300

    # 部署配置
    deployment_id: str = ""
    deployment_time: datetime = field(default_factory=datetime.now)
    git_commit: str = ""
    git_branch: str = ""
    docker_image: str = ""

class ProductionConfigManager:
    """生产环境配置管理器"""

    def __init__(self):
        self.config_dir = Path(__file__).parent.parent / "config"
        self.secrets_dir = Path(__file__).parent.parent / "secrets"
        self.config: Optional[ProductionConfig] = None

    def load_config(self, environment: Environment = Environment.PRODUCTION) -> ProductionConfig:
        """加载配置"""
        try:
            # 加载基础配置
            base_config = self._load_base_config(environment)

            # 加载环境特定配置
            env_config = self._load_environment_config(environment)

            # 加载敏感信息
            secrets_config = self._load_secrets(environment)

            # 合并配置
            config = self._merge_configs(base_config, env_config, secrets_config)

            # 验证配置
            self._validate_config(config)

            self.config = config
            logger.info(f"配置加载完成 - 环境: {environment.value}")
            return config

        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise

    def _load_base_config(self, environment: Environment) -> Dict[str, Any]:
        """加载基础配置"""
        config_file = self.config_dir / f"base_config.yaml"

        if not config_file.exists():
            raise FileNotFoundError(f"基础配置文件不存在: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def _load_environment_config(self, environment: Environment) -> Dict[str, Any]:
        """加载环境特定配置"""
        config_file = self.config_dir / f"{environment.value}_config.yaml"

        if not config_file.exists():
            logger.warning(f"环境配置文件不存在: {config_file}，使用默认配置")
            return {}

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def _load_secrets(self, environment: Environment) -> Dict[str, Any]:
        """加载敏感信息"""
        secrets_config = {}

        # 从环境变量加载
        env_secrets = self._load_from_environment()
        secrets_config.update(env_secrets)

        # 从secrets文件加载（优先级低于环境变量）
        secrets_file = self.secrets_dir / f"{environment.value}_secrets.yaml"
        if secrets_file.exists():
            with open(secrets_file, 'r', encoding='utf-8') as f:
                file_secrets = yaml.safe_load(f)
                for key, value in file_secrets.items():
                    if key not in secrets_config:
                        secrets_config[key] = value

        return secrets_config

    def _load_from_environment(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_config = {}

        # 数据库配置
        if os.getenv("DATABASE_URL"):
            env_config["database_url"] = os.getenv("DATABASE_URL")
        else:
            env_config.update({
                "db_host": os.getenv("DB_HOST", "localhost"),
                "db_port": int(os.getenv("DB_PORT", "5432")),
                "db_name": os.getenv("DB_NAME", "ai_hub_prod"),
                "db_username": os.getenv("DB_USERNAME", "postgres"),
                "db_password": os.getenv("DB_PASSWORD"),
            })

        # Redis配置
        env_config.update({
            "redis_host": os.getenv("REDIS_HOST", "localhost"),
            "redis_port": int(os.getenv("REDIS_PORT", "6379")),
            "redis_password": os.getenv("REDIS_PASSWORD"),
        })

        # 安全配置
        env_config.update({
            "secret_key": os.getenv("SECRET_KEY"),
            "jwt_secret_key": os.getenv("JWT_SECRET_KEY"),
            "encryption_key": os.getenv("ENCRYPTION_KEY"),
        })

        # 邮件配置
        if os.getenv("SMTP_HOST"):
            env_config.update({
                "smtp_host": os.getenv("SMTP_HOST"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_username": os.getenv("SMTP_USERNAME"),
                "smtp_password": os.getenv("SMTP_PASSWORD"),
                "from_email": os.getenv("FROM_EMAIL"),
            })

        # 外部服务配置
        env_config.update({
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
            "gemini_api_key": os.getenv("GEMINI_API_KEY"),
            "alert_webhook_url": os.getenv("ALERT_WEBHOOK_URL"),
        })

        return env_config

    def _merge_configs(self, base_config: Dict, env_config: Dict, secrets_config: Dict) -> ProductionConfig:
        """合并配置"""
        # 创建数据库配置
        db_config = DatabaseConfig(
            host=secrets_config.get("db_host") or env_config.get("db_host") or base_config.get("database", {}).get("host", "localhost"),
            port=secrets_config.get("db_port") or env_config.get("db_port") or base_config.get("database", {}).get("port", 5432),
            name=secrets_config.get("db_name") or env_config.get("db_name") or base_config.get("database", {}).get("name", "ai_hub_prod"),
            username=secrets_config.get("db_username") or env_config.get("db_username") or base_config.get("database", {}).get("username", "postgres"),
            password=secrets_config.get("db_password") or env_config.get("db_password") or base_config.get("database", {}).get("password"),
            **base_config.get("database", {})
        )

        # 创建Redis配置
        redis_config = RedisConfig(
            host=secrets_config.get("redis_host") or env_config.get("redis_host") or base_config.get("redis", {}).get("host", "localhost"),
            port=secrets_config.get("redis_port") or env_config.get("redis_port") or base_config.get("redis", {}).get("port", 6379),
            password=secrets_config.get("redis_password") or env_config.get("redis_password") or base_config.get("redis", {}).get("password"),
            **base_config.get("redis", {})
        )

        # 创建安全配置
        security_config = SecurityConfig(
            secret_key=secrets_config.get("secret_key") or env_config.get("secret_key") or base_config.get("security", {}).get("secret_key"),
            jwt_secret_key=secrets_config.get("jwt_secret_key") or env_config.get("jwt_secret_key") or base_config.get("security", {}).get("jwt_secret_key"),
            encryption_key=secrets_config.get("encryption_key") or env_config.get("encryption_key") or base_config.get("security", {}).get("encryption_key"),
            **base_config.get("security", {})
        )

        # 创建日志配置
        logging_config = LoggingConfig(
            level=LogLevel(base_config.get("logging", {}).get("level", "INFO")),
            log_file=base_config.get("logging", {}).get("log_file"),
            **base_config.get("logging", {})
        )

        # 创建监控配置
        monitoring_config = MonitoringConfig(
            alert_webhook_url=secrets_config.get("alert_webhook_url") or env_config.get("alert_webhook_url"),
            **base_config.get("monitoring", {})
        )

        # 创建邮件配置
        email_config = None
        smtp_host = secrets_config.get("smtp_host") or env_config.get("smtp_host")
        if smtp_host:
            email_config = EmailConfig(
                smtp_host=smtp_host,
                smtp_port=int(secrets_config.get("smtp_port") or env_config.get("smtp_port", 587)),
                smtp_username=secrets_config.get("smtp_username") or env_config.get("smtp_username"),
                smtp_password=secrets_config.get("smtp_password") or env_config.get("smtp_password"),
                from_email=secrets_config.get("from_email") or env_config.get("from_email"),
                **base_config.get("email", {})
            )

        # 创建存储配置
        storage_config = StorageConfig(**base_config.get("storage", {}))

        # 创建完整配置
        return ProductionConfig(
            environment=Environment(base_config.get("environment", "production")),
            debug=base_config.get("debug", False),
            host=base_config.get("host", "0.0.0.0"),
            port=base_config.get("port", 8000),
            workers=base_config.get("workers", 4),
            reload=base_config.get("reload", False),
            database=db_config,
            redis=redis_config,
            security=security_config,
            logging=logging_config,
            monitoring=monitoring_config,
            email=email_config,
            storage=storage_config,
            **base_config.get("application", {})
        )

    def _validate_config(self, config: ProductionConfig):
        """验证配置"""
        # 验证必需字段
        required_fields = [
            ("security.secret_key", "安全密钥"),
            ("security.jwt_secret_key", "JWT密钥"),
            ("database.password", "数据库密码"),
        ]

        for field_path, field_name in required_fields:
            value = self._get_nested_value(config, field_path)
            if not value:
                raise ValueError(f"缺少必需配置: {field_name}")

        # 验证密钥强度
        if len(config.security.secret_key) < 32:
            raise ValueError("安全密钥长度必须至少32个字符")

        if len(config.security.jwt_secret_key) < 32:
            raise ValueError("JWT密钥长度必须至少32个字符")

        # 验证端口
        if not (1 <= config.port <= 65535):
            raise ValueError(f"无效的端口号: {config.port}")

        # 验证CORS配置
        if not config.security.cors_origins and config.environment == Environment.PRODUCTION:
            logger.warning("生产环境建议配置CORS源域名")

    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """获取嵌套对象的值"""
        keys = path.split('.')
        current = obj
        for key in keys:
            if hasattr(current, key):
                current = getattr(current, key)
            elif isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def generate_secrets(self, environment: Environment) -> Dict[str, str]:
        """生成敏感信息"""
        secrets = {
            "secret_key": self._generate_secret_key(64),
            "jwt_secret_key": self._generate_secret_key(64),
            "encryption_key": self._generate_secret_key(32),
            "db_password": self._generate_password(32),
            "redis_password": self._generate_password(32),
        }

        logger.info(f"为环境 {environment.value} 生成敏感信息")
        return secrets

    def _generate_secret_key(self, length: int = 64) -> str:
        """生成密钥"""
        return secrets.token_urlsafe(length)

    def _generate_password(self, length: int = 32) -> str:
        """生成密码"""
        import string
        import random

        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(characters) for _ in range(length))
        return password

    def save_secrets(self, environment: Environment, secrets: Dict[str, str]):
        """保存敏感信息到文件"""
        secrets_file = self.secrets_dir / f"{environment.value}_secrets.yaml"

        # 确保目录存在
        self.secrets_dir.mkdir(exist_ok=True)

        # 设置文件权限（仅所有者可读写）
        os.chmod(self.secrets_dir, 0o700)

        with open(secrets_file, 'w', encoding='utf-8') as f:
            yaml.dump(secrets, f, default_flow_style=False)

        os.chmod(secrets_file, 0o600)
        logger.info(f"敏感信息已保存到: {secrets_file}")

    def get_config(self) -> ProductionConfig:
        """获取当前配置"""
        if self.config is None:
            raise RuntimeError("配置未加载，请先调用 load_config()")
        return self.config

    def get_env_file_content(self, config: ProductionConfig) -> str:
        """生成环境变量文件内容"""
        env_lines = [
            "# AI Hub Platform 生产环境配置",
            f"# 生成时间: {datetime.now().isoformat()}",
            "",
            "# 环境配置",
            f"ENVIRONMENT={config.environment.value}",
            f"DEBUG={str(config.debug).lower()}",
            f"HOST={config.host}",
            f"PORT={config.port}",
            f"WORKERS={config.workers}",
            "",
            "# 数据库配置",
            f"DATABASE_URL=postgresql://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.name}",
            f"DB_HOST={config.database.host}",
            f"DB_PORT={config.database.port}",
            f"DB_NAME={config.database.name}",
            f"DB_USERNAME={config.database.username}",
            "",
            "# Redis配置",
            f"REDIS_HOST={config.redis.host}",
            f"REDIS_PORT={config.redis.port}",
            f"REDIS_PASSWORD={config.redis.password or ''}",
            "",
            "# 安全配置",
            f"SECRET_KEY={config.security.secret_key}",
            f"JWT_SECRET_KEY={config.security.jwt_secret_key}",
            f"ENCRYPTION_KEY={config.security.encryption_key}",
            f"CORS_ORIGINS={','.join(config.security.cors_origins)}",
            "",
            "# 外部服务配置",
            f"OPENROUTER_API_KEY={os.getenv('OPENROUTER_API_KEY', '')}",
            f"GEMINI_API_KEY={os.getenv('GEMINI_API_KEY', '')}",
            f"ALERT_WEBHOOK_URL={config.monitoring.alert_webhook_url or ''}",
            "",
            "# 邮件配置",
            f"SMTP_HOST={config.email.smtp_host if config.email else ''}",
            f"SMTP_PORT={config.email.smtp_port if config.email else ''}",
            f"SMTP_USERNAME={config.email.smtp_username if config.email else ''}",
            f"FROM_EMAIL={config.email.from_email if config.email else ''}",
        ]

        return '\n'.join(env_lines)

    def create_docker_compose_prod(self, config: ProductionConfig) -> str:
        """生成生产环境Docker Compose配置"""
        compose_content = f"""version: '3.8'

services:
  # Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: ai-hub-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
    networks:
      - ai-hub-network
    restart: unless-stopped

  # 后端服务
  backend:
    image: aihub/backend:{config.deployment_id}
    container_name: ai-hub-backend
    environment:
      - ENVIRONMENT={config.environment.value}
      - DATABASE_URL=postgresql://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.name}
      - REDIS_HOST={config.redis.host}
      - REDIS_PORT={config.redis.port}
      - REDIS_PASSWORD={config.redis.password}
      - SECRET_KEY={config.security.secret_key}
      - JWT_SECRET_KEY={config.security.jwt_secret_key}
      - ENCRYPTION_KEY={config.security.encryption_key}
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
      - ./secrets:/app/secrets:ro
    depends_on:
      - postgres
      - redis
    networks:
      - ai-hub-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{config.port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL数据库
  postgres:
    image: postgres:14-alpine
    container_name: ai-hub-postgres
    environment:
      POSTGRES_DB: {config.database.name}
      POSTGRES_USER: {config.database.username}
      POSTGRES_PASSWORD: {config.database.password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgresql/init.sql:/docker-entrypoint-initdb/init.sql:ro
    networks:
      - ai-hub-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {config.database.username} -d {config.database.name}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: ai-hub-redis
    command: redis-server --requirepass {config.redis.password}
    volumes:
      - redis_data:/data
    networks:
      - ai-hub-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    container_name: ai-hub-prometheus
    ports:
      - "{config.monitoring.prometheus_port}:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - ai-hub-network
    restart: unless-stopped

  # Grafana仪表板
  grafana:
    image: grafana/grafana:latest
    container_name: ai-hub-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123456
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    networks:
      - ai-hub-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  grafana_data:

networks:
  ai-hub-network:
    driver: bridge
"""

        return compose_content

# 配置管理器实例
config_manager = ProductionConfigManager()

# 测试函数
def test_production_config():
    """测试生产环境配置"""
    print("🚀 测试生产环境配置...")

    try:
        # 生成测试环境配置
        config = config_manager.load_config(Environment.PRODUCTION)

        print(f"✅ 配置加载成功:")
        print(f"   环境: {config.environment.value}")
        print(f"   数据库: {config.database.host}:{config.database.port}/{config.database.name}")
        print(f"   Redis: {config.redis.host}:{config.redis.port}")
        print(f"   端口: {config.port}")
        print(f"   工作进程: {config.workers}")
        print(f"   日志级别: {config.logging.level.value}")

        # 生成环境变量文件
        env_content = config_manager.get_env_file_content(config)
        print(f"\n📝 环境变量文件内容已生成 (长度: {len(env_content)} 字符)")

        # 生成Docker Compose配置
        compose_content = config_manager.create_docker_compose_prod(config)
        print(f"📦 Docker Compose配置已生成 (长度: {len(compose_content)} 字符)")

        print("\n✅ 生产环境配置测试完成")

    except Exception as e:
        print(f"❌ 配置测试失败: {e}")

if __name__ == "__main__":
    test_production_config()
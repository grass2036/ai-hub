"""
AI Hub Platform - Main Application Entry Point
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.v1.router import api_router
from backend.config.settings import get_settings
from backend.middleware.error_handler import ErrorHandlingMiddleware, PerformanceMiddleware, setup_error_handlers
from backend.middleware.api_key_auth import APIKeyAuthMiddleware
from backend.core.ha.middleware import HAMiddleware, LoadBalancingMiddleware, HealthCheckMiddleware
from backend.core.ha.setup import HAConfig, LoadBalancingConfig, HealthCheckConfig, FailoverConfig, ClusterConfig

# Get settings instance
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="AI Hub Platform",
    description="企业级AI应用平台 - 支持多AI模型集成、RAG系统、智能客服",
    version="1.0.0",
    docs_url="/api/docs" if settings.enable_api_docs else None,
    redoc_url="/api/redoc" if settings.enable_api_docs else None,
    openapi_url="/api/openapi.json" if settings.enable_api_docs else None
)

# High Availability middleware (added first for system-wide monitoring)
if settings.environment == "production":
    # 生产环境启用高可用功能
    ha_config = HAConfig(
        enable_load_balancer=True,
        enable_health_checker=True,
        enable_failover_manager=True,
        enable_cluster_manager=True,
        redis_url=getattr(settings, 'redis_url', 'redis://localhost:6379/1')
    )

    load_balancer_config = LoadBalancingConfig(
        strategy="round_robin",
        health_check_interval=30,
        max_retries=3
    )

    health_check_config = HealthCheckConfig(
        check_type="http_endpoint",
        target="http://localhost:8001/health",
        interval=30,
        timeout=5
    )

    failover_config = FailoverConfig(
        strategy="active_passive",
        detection_timeout=10,
        recovery_check_interval=30
    )

    cluster_config = ClusterConfig(
        node_id=os.getenv("NODE_ID", f"node-{os.getpid()}"),
        discovery_servers=os.getenv("DISCOVERY_SERVERS", "localhost:8001").split(","),
        quorum_size=int(os.getenv("QUORUM_SIZE", "1"))
    )

    app.add_middleware(
        HAMiddleware,
        ha_config=ha_config,
        load_balancer_config=load_balancer_config,
        health_check_config=health_check_config,
        failover_config=failover_config,
        cluster_config=cluster_config
    )

# Performance and error handling middleware
app.add_middleware(PerformanceMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# API Key authentication middleware (added after error handling)
app.add_middleware(APIKeyAuthMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (for uploaded documents, etc.)
os.makedirs("data/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")

# Setup error handlers
setup_error_handlers(app)

# Include API router
app.include_router(api_router, prefix="/api/v1", tags=["api"])


@app.get("/")
async def root():
    """根路径，返回API基本信息"""
    return {
        "name": "AI Hub Platform",
        "version": "1.0.0",
        "description": "企业级AI应用平台",
        "features": [
            "多AI模型集成 (OpenRouter + Gemini)",
            "RAG文档问答系统", 
            "智能客服工作流",
            "企业级管理后台"
        ],
        "docs": "/api/docs" if settings.enable_api_docs else "Disabled",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "debug": settings.debug,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动 AI Hub Platform...")
    print(f"🌐 环境: {settings.environment}")
    print(f"🔧 调试模式: {settings.debug}")
    print(f"📚 API文档: http://localhost:8001/api/docs")
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug and settings.environment == "development",
        log_level="info" if not settings.debug else "debug"
    )
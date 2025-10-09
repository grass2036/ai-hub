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

# Performance and error handling middleware
app.add_middleware(PerformanceMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

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
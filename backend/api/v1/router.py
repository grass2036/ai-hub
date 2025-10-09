"""
API v1 Main Router
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.config.settings import get_settings, Settings

# Create API router
api_router = APIRouter()

# Import sub-routers (will be added as development progresses)
from .chat import router as chat_router
from .stats import router as stats_router
from .sessions import router as sessions_router
from .search import router as search_router
from .health import router as health_router
from .models import router as models_router
from .config import router as config_router
from .auth.auth import router as auth_router
from .developer.api_keys import router as api_keys_router
from .developer.chat import router as developer_chat_router
from .developer.usage import router as developer_usage_router
# from .documents import router as documents_router
# from .websocket import router as websocket_router


@api_router.get("/")
async def api_root():
    """API v1 根路径"""
    return {
        "message": "AI Hub Platform API v1",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "stats": "/stats",
            "sessions": "/sessions",
            "search": "/search",
            "models": "/models",
            "health": "/health",
            "config": "/config",
            "documents": "/documents",
            "websocket": "/ws"
        }
    }


@api_router.get("/status")
async def api_status(settings: Settings = Depends(get_settings)):
    """API状态检查"""
    ai_keys = settings.validate_ai_keys()
    
    return {
        "status": "operational",
        "environment": settings.environment,
        "debug": settings.debug,
        "ai_services": {
            "available_services": [k for k, v in ai_keys.items() if v],
            "total_configured": sum(ai_keys.values()),
            "details": ai_keys
        },
        "database": {
            "type": "SQLite" if "sqlite" in settings.database_url else "PostgreSQL",
            "connected": True  # TODO: Add actual database connection check
        },
        "cache": {
            "redis_configured": bool(settings.redis_url),
            "enabled": settings.enable_response_cache
        }
    }


@api_router.get("/health")
async def health_check():
    """健康检查端点"""
    # TODO: Add actual health checks for:
    # - Database connection
    # - Redis connection  
    # - AI services availability
    return {
        "status": "healthy",
        "checks": {
            "database": "ok",
            "cache": "ok", 
            "ai_services": "ok"
        }
    }


# Include sub-routers as they are developed
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(models_router, prefix="/models", tags=["models"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(auth_router, tags=["authentication"])
api_router.include_router(api_keys_router, prefix="/developer/api-keys", tags=["developer"])
api_router.include_router(developer_chat_router, prefix="/developer/chat", tags=["developer"])
api_router.include_router(developer_usage_router, prefix="/developer/usage", tags=["developer"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
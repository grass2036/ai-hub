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
from .developer.auth import router as developer_auth_router
from .developer.keys import router as api_keys_router
from .developer.chat import router as developer_chat_router
from .developer.usage import router as developer_usage_router
from .developer.batch import router as developer_batch_router
from .organizations import router as organizations_router
from .teams import router as teams_router
from .budgets import router as budgets_router
from .org_api_keys import router as org_api_keys_router
from .payments import router as payments_router
from .audit import router as audit_router
from .permissions import router as permissions_router
from .monitoring import router as monitoring_router
from .monitoring_new import router as monitoring_new_router
from .alerts import router as alerts_router
from .ai_advanced import router as ai_advanced_router
from .operations import router as operations_router
from .tenant import router as tenant_router
from .analytics import router as analytics_router
from .performance import router as performance_router
from .ha import router as ha_router
from .backup import router as backup_router
from .multimodal import router as multimodal_router
from .workflow import router as workflow_router
from .recommendations import router as recommendations_router
from .plugin_market import router as plugin_market_router
from .database_optimization import router as database_optimization_router
from .cache import router as cache_router
from .performance_optimization import router as performance_optimization_router
from .billing import router as billing_router
from backend.api.v2 import v2_router
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
            "organizations": "/organizations",
            "teams": "/teams",
            "budgets": "/budgets",
            "api_keys": "/api-keys",
            "payments": "/payments",
            "audit": "/audit",
            "permissions": "/permissions",
            "monitoring": "/monitoring",
            "monitoring_new": "/monitoring-new",
            "alerts": "/alerts",
            "ai_advanced": "/ai-advanced",
            "operations": "/operations",
            "tenant": "/tenant",
            "analytics": "/analytics",
            "performance": "/performance",
            "performance_optimization": "/performance-optimization",
            "ha": "/ha",
            "backup": "/backup",
            "multimodal": "/multimodal",
            "workflow": "/workflow",
            "database_optimization": "/database-optimization",
            "cache": "/cache",
            "billing": "/billing",
            "swagger": "/swagger",
            "v2": "/v2",
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
api_router.include_router(developer_auth_router, prefix="/developer/auth", tags=["developer"])
api_router.include_router(api_keys_router, prefix="/developer/keys", tags=["developer"])
api_router.include_router(developer_chat_router, prefix="/developer/chat", tags=["developer"])
api_router.include_router(developer_usage_router, prefix="/developer/usage", tags=["developer"])
api_router.include_router(developer_batch_router, prefix="/developer/batch", tags=["developer"])
api_router.include_router(organizations_router, prefix="/organizations", tags=["organizations"])
api_router.include_router(teams_router, prefix="/teams", tags=["teams"])
api_router.include_router(budgets_router, prefix="/budgets", tags=["budgets"])
api_router.include_router(org_api_keys_router, tags=["api_keys"])
api_router.include_router(payments_router, tags=["payments"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(permissions_router, prefix="/permissions", tags=["permissions"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(monitoring_new_router, prefix="/monitoring-new", tags=["monitoring"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(ai_advanced_router, prefix="/ai-advanced", tags=["ai_advanced"])
api_router.include_router(operations_router, prefix="/operations", tags=["operations"])
api_router.include_router(tenant_router, prefix="/tenant", tags=["tenant"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(performance_router, prefix="/performance", tags=["performance"])
api_router.include_router(ha_router, tags=["high-availability"])
api_router.include_router(backup_router, tags=["backup-recovery"])
api_router.include_router(multimodal_router, tags=["multimodal"])
api_router.include_router(workflow_router, tags=["workflow"])
api_router.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(plugin_market_router, prefix="/plugin-market", tags=["plugin_market"])
api_router.include_router(database_optimization_router, tags=["database-optimization"])
api_router.include_router(cache_router, tags=["cache"])
api_router.include_router(performance_optimization_router, tags=["performance-optimization"])
api_router.include_router(billing_router, tags=["billing"])
api_router.include_router(v2_router, tags=["api-v2"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
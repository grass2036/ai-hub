"""
API v2 模块初始化
Week 5 Day 2: 高级API功能 - API版本管理
"""

from fastapi import APIRouter
from .health import router as health_router

# 创建v2路由器
v2_router = APIRouter(prefix="/api/v2", tags=["api-v2"])

# 包含v2子路由
v2_router.include_router(health_router, tags=["health-v2"])

# 导出路由器
__all__ = ["v2_router"]
"""
API Key Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class APIKeyCreateRequest(BaseModel):
    """创建API密钥请求"""
    name: str = Field(min_length=1, max_length=255, description="API密钥名称")
    description: Optional[str] = Field(None, max_length=1000, description="API密钥描述")
    expires_days: Optional[int] = Field(None, gt=0, le=365, description="过期天数(1-365)")


class APIKeyResponse(BaseModel):
    """API密钥响应"""
    id: int
    name: str
    description: Optional[str]
    key: str  # Only returned on creation
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyListItem(BaseModel):
    """API密钥列表项（不包含完整key）"""
    id: int
    name: str
    description: Optional[str]
    key_preview: str  # e.g., "aihub_****abc"
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class QuotaResponse(BaseModel):
    """配额响应"""
    limits: dict
    usage: dict
    reset_times: dict

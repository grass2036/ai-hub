#!/usr/bin/env python3
"""
简化的AI Hub后端服务 - 用于测试前端认证功能
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn
import uuid
import hashlib
import datetime
import json
import os

# 创建FastAPI应用
app = FastAPI(
    title="AI Hub API",
    description="AI Hub - 简化版后端服务",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # 开发环境
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内存数据存储 (生产环境应使用数据库)
users_db = {}
api_keys_db = {}

# Pydantic模型
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime.datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

# 工具函数
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_access_token(data: dict) -> str:
    # 简化的token生成 (生产环境应使用JWT)
    token_data = {
        "sub": data["user_id"],
        "exp": str(datetime.datetime.now() + datetime.timedelta(days=7)),
        "random": str(uuid.uuid4())
    }
    return hashlib.sha256(json.dumps(token_data).encode()).hexdigest()

# API路由
@app.get("/")
async def root():
    return {"message": "AI Hub API - 简化版"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now()}

# 模拟API密钥数据
mock_api_keys = [
    {
        "id": 1,
        "key": "ai-hub-test-key-1234567890abcdef",
        "key_prefix": "ai-hub-test",
        "name": "开发密钥",
        "description": "用于开发和测试的API密钥",
        "rate_limit": 100,
        "total_requests": 25,
        "is_active": True,
        "is_expired": False,
        "created_at": "2024-01-15T10:30:00Z",
        "last_used_at": "2024-01-20T14:22:00Z",
        "expires_at": None
    }
]

# 模拟使用统计数据
mock_usage_stats = {
    "quota_used": 1250,
    "quota_total": 50000,
    "quota_remaining": 48750,
    "quota_percentage": 2.5,
    "plan": "developer",
    "quota_reset_at": "2024-02-01T00:00:00Z",
    "days_until_reset": 12,
    "total_cost": 0.125,
    "requests_today": 45,
    "daily_average": 42
}

@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    # 检查用户是否已存在
    if user_data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 创建新用户
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user_data.password)

    user = User(
        id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        created_at=datetime.datetime.now()
    )

    users_db[user_data.email] = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "password": hashed_password,
        "created_at": datetime.datetime.now()
    }

    # 生成API密钥
    api_key = f"ai-hub-{uuid.uuid4().hex[:24]}"
    api_keys_db[api_key] = {
        "user_id": user_id,
        "name": "Default Key",
        "created_at": datetime.datetime.now()
    }

    # 生成访问token
    access_token = create_access_token({"user_id": user_id})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    # 验证用户
    if user_data.email not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_user = users_db[user_data.email]
    if not verify_password(user_data.password, stored_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = User(
        id=stored_user["id"],
        email=stored_user["email"],
        full_name=stored_user["full_name"],
        created_at=stored_user["created_at"]
    )

    # 生成访问token
    access_token = create_access_token({"user_id": stored_user["id"]})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )

@app.get("/api/v1/auth/me")
async def get_current_user():
    # 简化实现，返回示例用户数据
    return {
        "id": "demo-user-id",
        "email": "demo@example.com",
        "full_name": "Demo User",
        "created_at": datetime.datetime.now(),
        "plan": "developer"
    }

# 开发者API端点
@app.get("/api/v1/developer/api-keys")
async def list_api_keys():
    """获取API密钥列表"""
    return mock_api_keys

@app.post("/api/v1/developer/api-keys")
async def create_api_key(request: dict):
    """创建新API密钥"""
    new_key_id = max([key["id"] for key in mock_api_keys]) + 1 if mock_api_keys else 1
    new_key = f"ai-hub-{uuid.uuid4().hex[:24]}"

    new_key_data = {
        "id": new_key_id,
        "key": new_key,
        "key_prefix": new_key[:16],
        "name": request.get("name", "新密钥"),
        "description": request.get("description", ""),
        "rate_limit": request.get("rate_limit", 100),
        "total_requests": 0,
        "is_active": True,
        "is_expired": False,
        "created_at": datetime.datetime.now().isoformat(),
        "last_used_at": None,
        "expires_at": None
    }

    mock_api_keys.append(new_key_data)
    return new_key_data

@app.delete("/api/v1/developer/api-keys/{key_id}")
async def revoke_api_key(key_id: int):
    """撤销API密钥"""
    for key in mock_api_keys:
        if key["id"] == key_id:
            key["is_active"] = False
            return {"message": "API密钥已撤销"}
    raise HTTPException(status_code=404, detail="API密钥不存在")

@app.get("/api/v1/developer/usage/current")
async def get_current_usage():
    """获取当前使用统计"""
    return mock_usage_stats

@app.get("/api/v1/developer/usage/history")
async def get_usage_history(days: int = 30):
    """获取使用历史"""
    # 生成模拟的历史数据
    history = []
    for i in range(days):
        date = datetime.datetime.now() - datetime.timedelta(days=i)
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "requests": max(0, 40 + int(20 * (1 - i/days))),  # 模拟递减的使用量
            "cost": round(max(0, 0.05 * (1 - i/days)), 3)
        })
    return {"data": history, "total_days": days}

# 聊天相关API (简化版)
@app.post("/api/v1/chat/completions")
async def chat_completions(request: dict):
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(datetime.datetime.now().timestamp()),
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "这是一个简化的响应示例。真实的AI服务需要配置API密钥。"
                },
                "finish_reason": "stop"
            }
        ]
    }

@app.get("/api/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai"
            },
            {
                "id": "gpt-4",
                "object": "model",
                "created": 1687882411,
                "owned_by": "openai"
            }
        ]
    }

if __name__ == "__main__":
    print("🚀 启动AI Hub简化版后端服务...")
    print("📍 服务地址: http://localhost:8002")
    print("📚 API文档: http://localhost:8002/docs")
    print("💡 这是用于测试前端认证功能的简化版服务")

    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
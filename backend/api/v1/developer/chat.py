"""
开发者聊天API (带配额检查)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.ai_service import ai_manager
from backend.core.quota_manager import quota_manager
from backend.middleware.quota_check import check_api_key_and_quota

router = APIRouter(prefix="/developer", tags=["Developer API"])


# ============ Pydantic模型 ============ 

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    model: str = "grok-beta"
    stream: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello, how are you?",
                "model": "grok-beta",
                "stream": True
            }
        }


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    model: str
    tokens_used: int
    cost: float


# ============ API端点 ============ 

@router.post("/chat")
async def developer_chat(
    request: ChatRequest,
    auth_info: dict = Depends(check_api_key_and_quota),
    db: AsyncSession = Depends(get_db)
):
    """
    开发者聊天API

    - 需要API密钥认证
    - 自动检查配额和速率限制
    - 支持流式响应
    """
    user_id = auth_info["user_id"]

    # 获取AI服务
    service = await ai_manager.get_service("openrouter")

    if request.stream:
        # 流式响应
        async def stream_with_quota():
            total_tokens = 0

            async for chunk in service.stream_response(
                prompt=request.message,
                model=request.model
            ):
                yield f"data: {chunk}\n\n"
                # 简单估算: 每个chunk约5个token
                total_tokens += 5

            # 消费配额
            await quota_manager.consume_quota(db, user_id, 1)

            yield f"data: [DONE]\n\n"

        return StreamingResponse(
            stream_with_quota(),
            media_type="text/event-stream"
        )
    else:
        # 普通响应
        response = await service.generate_response(
            prompt=request.message,
            model=request.model
        )

        # 消费配额
        await quota_manager.consume_quota(db, user_id, 1)

        return ChatResponse(
            response=response,
            model=request.model,
            tokens_used=100,  # TODO: 实际计算
            cost=0.001  # TODO: 实际计算
        )
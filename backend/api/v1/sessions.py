"""
Session Management API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from backend.core.ai_service import ai_manager

router = APIRouter()


class SessionResponse(BaseModel):
    """会话响应模型"""
    id: str = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    message_count: int = Field(..., description="消息数量")
    first_message: Optional[str] = Field(default=None, description="首条消息")


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str = Field(..., description="消息ID")
    role: str = Field(..., description="角色")
    content: str = Field(..., description="内容")
    timestamp: str = Field(..., description="时间戳")
    model: Optional[str] = Field(default=None, description="模型")
    images: Optional[List[str]] = Field(default=None, description="图片")
    attachments: Optional[List[str]] = Field(default=None, description="附件")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="使用统计")


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field(default=None, description="会话标题")


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""
    title: str = Field(..., description="新标题")


@router.post("/", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    创建新会话
    """
    try:
        session = await ai_manager.session_manager.create_session(title=request.title)
        return SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
            first_message=session.first_message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100, description="返回数量"),
    search: Optional[str] = Query(default=None, description="搜索关键词")
):
    """
    获取会话列表
    """
    try:
        sessions = await ai_manager.session_manager.list_sessions(limit=limit, search=search)
        return [
            SessionResponse(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at,
                message_count=session.message_count,
                first_message=session.first_message
            )
            for session in sessions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    获取会话信息
    """
    try:
        session = await ai_manager.session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
            first_message=session.first_message
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话失败: {str(e)}")


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(session_id: str, request: UpdateSessionRequest):
    """
    更新会话标题
    """
    try:
        success = await ai_manager.session_manager.update_session_title(session_id, request.title)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        session = await ai_manager.session_manager.get_session(session_id)
        return SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
            first_message=session.first_message
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新会话失败: {str(e)}")


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话
    """
    try:
        success = await ai_manager.session_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {"message": "会话删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="消息数量限制")
):
    """
    获取会话消息
    """
    try:
        messages = await ai_manager.session_manager.get_messages(session_id, limit=limit)
        return [
            MessageResponse(
                id=msg.id,
                role=str(msg.role),
                content=msg.content,
                timestamp=msg.timestamp,
                model=msg.model,
                images=msg.images,
                attachments=msg.attachments,
                usage=msg.usage
            )
            for msg in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取消息失败: {str(e)}")


@router.get("/{session_id}/context")
async def get_session_context(
    session_id: str,
    max_messages: int = Query(default=10, ge=1, le=50, description="最大消息数")
):
    """
    获取会话上下文（用于AI模型）
    """
    try:
        context = await ai_manager.session_manager.get_conversation_context(
            session_id, max_messages=max_messages
        )
        return {
            "session_id": session_id,
            "context": context,
            "message_count": len(context)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取上下文失败: {str(e)}")


@router.get("/stats/summary")
async def get_session_stats():
    """
    获取会话统计信息
    """
    try:
        stats = await ai_manager.session_manager.get_session_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
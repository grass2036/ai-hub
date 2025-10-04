"""
Chat API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
from backend.core.ai_service import ai_manager
from backend.core.cost_tracker import ServiceType
from backend.core.session_manager import MessageRole
from backend.core.web_search import web_search_service
from backend.config.settings import get_settings
import re

router = APIRouter()
settings = get_settings()


def should_search_web(message: str) -> bool:
    """检测用户消息是否需要联网搜索"""
    search_patterns = [
        r'搜索\s*(.+)',
        r'查找\s*(.+)',
        r'最新.*?(?:新闻|消息|信息)',
        r'今天.*?(?:发生|新闻)',
        r'现在.*?(?:情况|状态)',
        r'当前.*?(?:价格|汇率)',
        r'最近.*?(?:发布|更新)',
        r'search\s+(.+)',
        r'find\s+(.+)',
        r'latest\s+(.+)',
        r'current\s+(.+)',
        r'recent\s+(.+)',
        r'what.*?happening',
        r'what.*?news',
    ]
    
    for pattern in search_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return True
    return False


def extract_search_query(message: str) -> str:
    """从用户消息中提取搜索关键词"""
    # 尝试提取搜索关键词
    search_patterns = [
        (r'搜索\s*(.+)', 1),
        (r'查找\s*(.+)', 1), 
        (r'search\s+(.+)', 1),
        (r'find\s+(.+)', 1),
    ]
    
    for pattern, group in search_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(group).strip()
    
    # 如果没有明确的搜索指令，直接使用整个消息作为搜索词
    return message


async def augment_with_search(prompt: str) -> str:
    """使用联网搜索增强提示词"""
    if not should_search_web(prompt):
        return prompt
    
    try:
        # 提取搜索关键词
        search_query = extract_search_query(prompt)
        
        # 执行搜索
        search_results = await web_search_service.search(
            query=search_query,
            num_results=3,
            engine="duckduckgo"
        )
        
        if search_results:
            # 构建增强的提示词
            search_context = "根据以下最新搜索结果回答问题:\n\n"
            for i, result in enumerate(search_results, 1):
                search_context += f"{i}. 标题: {result.title}\n"
                search_context += f"   来源: {result.url}\n"
                search_context += f"   摘要: {result.snippet}\n\n"
            
            enhanced_prompt = f"{search_context}用户问题: {prompt}\n\n请基于上述搜索结果提供准确、及时的回答。如果搜索结果不足以回答问题，请说明并提供你的一般性知识。"
            return enhanced_prompt
        else:
            # 如果搜索失败，添加说明
            fallback_prompt = f"用户问题: {prompt}\n\n注意：尝试联网搜索相关信息但未获取到结果，请基于你的训练数据回答。"
            return fallback_prompt
            
    except Exception as e:
        # 搜索失败时的回退处理
        print(f"Search error: {e}")
        return prompt


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=4000)
    service: str = Field(default="openrouter", description="AI服务名称 (openrouter|gemini)")
    model: str = Field(default="x-ai/grok-beta", description="AI模型名称")
    stream: bool = Field(default=False, description="是否启用流式响应")
    session_id: Optional[str] = Field(default=None, description="会话ID，不提供则创建新会话")
    context: Optional[Dict[str, Any]] = Field(default=None, description="对话上下文")
    temperature: Optional[float] = Field(default=0.7, description="生成温度")
    max_tokens: Optional[int] = Field(default=1000, description="最大生成长度")
    images: Optional[List[str]] = Field(default=None, description="图片Base64数据")
    files: Optional[List[str]] = Field(default=None, description="文件名列表")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str = Field(..., description="AI回复")
    model: str = Field(..., description="使用的AI模型")
    session_id: str = Field(..., description="会话ID")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="使用统计")


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    发送消息到AI服务并获取回复
    """
    try:
        # 获取或创建会话
        session_id = request.session_id
        if not session_id:
            session = await ai_manager.session_manager.create_session()
            session_id = session.id
        
        # 获取AI服务
        service = await ai_manager.get_service(request.service)
        
        # 保存用户消息
        await ai_manager.session_manager.add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=request.message,
            images=request.images,
            attachments=request.files
        )
        
        # 获取对话上下文
        context_messages = await ai_manager.session_manager.get_conversation_context(session_id)
        
        # 构建提示词
        prompt = request.message
        if context_messages:
            # 构建上下文提示词
            context_prompt = "\n".join([
                f"用户: {msg['content']}" if msg['role'] == 'user' else f"助手: {msg['content']}"
                for msg in context_messages[:-1]  # 排除当前消息
            ])
            if context_prompt:
                prompt = f"对话历史:\n{context_prompt}\n\n当前问题: {request.message}"
        
        # 检查是否需要联网搜索并增强提示词
        prompt = await augment_with_search(prompt)
        
        # 生成响应 (传递模型和参数)
        kwargs = {
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        if request.service == "openrouter":
            response = await service.generate_response(prompt, request.model, **kwargs)
        else:
            response = await service.generate_response(prompt)
        
        # 跟踪成本和使用情况
        service_type = ServiceType.OPENROUTER if request.service == "openrouter" else ServiceType.GEMINI
        usage_record = await ai_manager.cost_tracker.track_usage(
            service=service_type,
            model=request.model,
            input_text=prompt,
            output_text=response,
            request_id=f"chat_{session_id}"
        )
        
        # 保存AI回复
        await ai_manager.session_manager.add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=response,
            model=f"{request.service}:{request.model}",
            usage=usage_record.to_dict()
        )
        
        return ChatResponse(
            message=response,
            model=f"{request.service}:{request.model}",
            session_id=session_id,
            usage={
                "prompt_tokens": usage_record.input_tokens,
                "completion_tokens": usage_record.output_tokens,
                "total_tokens": usage_record.total_tokens,
                "estimated_cost_usd": usage_record.estimated_cost_usd
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口
    """
    try:
        # 获取或创建会话
        session_id = request.session_id
        if not session_id:
            session = await ai_manager.session_manager.create_session()
            session_id = session.id
        
        # 获取AI服务
        service = await ai_manager.get_service(request.service)
        
        # 保存用户消息
        await ai_manager.session_manager.add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=request.message,
            images=request.images,
            attachments=request.files
        )
        
        # 获取对话上下文
        context_messages = await ai_manager.session_manager.get_conversation_context(session_id)
        
        # 构建提示词
        prompt = request.message
        if context_messages:
            context_prompt = "\n".join([
                f"用户: {msg['content']}" if msg['role'] == 'user' else f"助手: {msg['content']}"
                for msg in context_messages[:-1]  # 排除当前消息
            ])
            if context_prompt:
                prompt = f"对话历史:\n{context_prompt}\n\n当前问题: {request.message}"
        
        # 检查是否需要联网搜索并增强提示词
        prompt = await augment_with_search(prompt)
        
        async def generate():
            """流式响应生成器"""
            accumulated_response = ""
            try:
                kwargs = {
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens
                }
                
                if request.service == "openrouter":
                    stream_iter = service.stream_response(prompt, request.model, **kwargs)
                else:
                    stream_iter = service.stream_response(prompt)
                    
                async for chunk in stream_iter:
                    accumulated_response += chunk
                    data = {
                        "type": "content",
                        "content": chunk,
                        "model": f"{request.service}:{request.model}"
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                
                # 跟踪成本和使用情况
                service_type = ServiceType.OPENROUTER if request.service == "openrouter" else ServiceType.GEMINI
                usage_record = await ai_manager.cost_tracker.track_usage(
                    service=service_type,
                    model=request.model,
                    input_text=prompt,
                    output_text=accumulated_response,
                    request_id=f"stream_{session_id}"
                )
                
                # 保存AI回复
                await ai_manager.session_manager.add_message(
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=accumulated_response,
                    model=f"{request.service}:{request.model}",
                    usage=usage_record.to_dict()
                )
                
                # 发送会话ID
                session_data = {
                    "type": "session",
                    "session_id": session_id
                }
                yield f"data: {json.dumps(session_data, ensure_ascii=False)}\n\n"
                
                # 发送使用统计
                usage_data = {
                    "type": "usage",
                    "usage": {
                        "prompt_tokens": usage_record.input_tokens,
                        "completion_tokens": usage_record.output_tokens,
                        "total_tokens": usage_record.total_tokens,
                        "estimated_cost_usd": usage_record.estimated_cost_usd
                    }
                }
                yield f"data: {json.dumps(usage_data, ensure_ascii=False)}\n\n"
                
                # 发送结束标志
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                error_data = {
                    "type": "error",
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(service: str = "openrouter"):
    """
    获取可用的AI模型列表
    """
    try:
        models_data = await ai_manager.get_models(service)
        return models_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services")
async def list_services():
    """
    获取可用的AI服务列表
    """
    try:
        services = await ai_manager.list_available_services()
        return services
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def chat_health():
    """
    聊天服务健康检查
    """
    health_results = {}
    
    # 测试OpenRouter服务
    try:
        openrouter_service = await ai_manager.get_service("openrouter")
        openrouter_health = await openrouter_service.health_check()
        health_results["openrouter"] = {
            "status": "healthy" if openrouter_health else "unhealthy",
            "available": openrouter_health
        }
    except Exception as e:
        health_results["openrouter"] = {
            "status": "unhealthy",
            "error": str(e),
            "available": False
        }
    
    # 测试Gemini服务
    try:
        gemini_service = await ai_manager.get_service("gemini")
        test_response = await gemini_service.generate_response("Hello")
        health_results["gemini"] = {
            "status": "healthy",
            "test_response_length": len(test_response),
            "available": True
        }
    except Exception as e:
        health_results["gemini"] = {
            "status": "unhealthy",
            "error": str(e),
            "available": False
        }
    
    overall_healthy = any(result["available"] for result in health_results.values())
    
    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "services": health_results,
        "primary_service": "openrouter",
        "fallback_service": "gemini"
    }
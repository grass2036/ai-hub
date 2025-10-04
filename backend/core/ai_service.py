"""
AI Services Integration Module
"""

import asyncio
from typing import Optional, Dict, Any, AsyncGenerator
import google.generativeai as genai
from fastapi import HTTPException
from backend.config.settings import get_settings
from backend.core.openrouter_service import OpenRouterService
from backend.core.cost_tracker import CostTracker, ServiceType
from backend.core.session_manager import SessionManager

settings = get_settings()


class GeminiService:
    """Google Gemini AI服务集成"""
    
    def __init__(self):
        self.model = None
        self._initialized = False
        
    async def initialize(self):
        """初始化Gemini服务"""
        if self._initialized:
            return
            
        try:
            if not settings.gemini_api_key:
                raise ValueError("Gemini API密钥未配置")
                
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self._initialized = True
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Gemini服务初始化失败: {str(e)}"
            )
    
    async def generate_response(self, prompt: str) -> str:
        """生成AI响应"""
        if not self._initialized:
            await self.initialize()
            
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            return response.text
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"AI响应生成失败: {str(e)}"
            )
    
    async def stream_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """流式生成AI响应"""
        if not self._initialized:
            await self.initialize()
            
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"流式响应生成失败: {str(e)}"
            )


class AIServiceManager:
    """AI服务管理器"""
    
    def __init__(self):
        self.openrouter = OpenRouterService()
        self.gemini = GeminiService()
        self.cost_tracker = CostTracker()
        self.session_manager = SessionManager()
        self._services = {
            "openrouter": self.openrouter,
            "gemini": self.gemini
        }
    
    async def get_service(self, service_name: str = "openrouter"):
        """获取AI服务实例"""
        if service_name not in self._services:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的AI服务: {service_name}"
            )
        
        service = self._services[service_name]
        if not service._initialized:
            await service.initialize()
        
        return service
    
    async def list_available_services(self) -> Dict[str, Any]:
        """列出可用的AI服务"""
        return {
            "services": list(self._services.keys()),
            "default": "openrouter",
            "capabilities": {
                "openrouter": {
                    "text_generation": True,
                    "streaming": True,
                    "multi_model": True,
                    "cost_efficient": True
                },
                "gemini": {
                    "text_generation": True,
                    "streaming": True,
                    "multimodal": True
                }
            }
        }
    
    async def get_models(self, service_name: str = "openrouter") -> Dict[str, Any]:
        """获取指定服务的可用模型"""
        service = await self.get_service(service_name)
        
        if service_name == "openrouter":
            models = await service.get_popular_models()
            return {
                "service": service_name,
                "models": models,
                "total_count": len(models)
            }
        elif service_name == "gemini":
            return {
                "service": service_name,
                "models": [
                    {
                        "id": "gemini-2.5-flash",
                        "name": "Gemini 2.5 Flash",
                        "description": "Fast and efficient model for general tasks",
                        "context_length": 1048576,
                        "pricing": {"prompt": "free", "completion": "free"}
                    }
                ],
                "total_count": 1
            }
        else:
            return {"service": service_name, "models": [], "total_count": 0}


# 全局AI服务管理器实例
ai_manager = AIServiceManager()
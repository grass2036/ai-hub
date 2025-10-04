"""OpenRouter AI service integration."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
import aiohttp
from backend.config.settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

class OpenRouterService:
    """OpenRouter API service implementation."""
    
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = settings.openrouter_api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the service."""
        if self._initialized:
            return
            
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")
            
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3001",
                "X-Title": "AI Hub"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        self._initialized = True
        logger.info("OpenRouter service initialized")
        
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
        self._initialized = False
        
    async def generate_response(self, prompt: str, model: str = "grok-beta", **kwargs) -> str:
        """Generate a response using OpenRouter API."""
        if not self._initialized:
            await self.initialize()
            
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "stream": False
            }
            
            async with self.session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                    raise Exception(f"OpenRouter API error: {response.status}")
                
                data = await response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"Unexpected response format: {data}")
                    raise Exception("Invalid response format from OpenRouter")
                    
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    async def stream_response(self, prompt: str, model: str = "grok-beta", **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming response using OpenRouter API."""
        if not self._initialized:
            await self.initialize()
            
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "stream": True
            }
            
            async with self.session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                    raise Exception(f"OpenRouter API error: {response.status}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            raise
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from OpenRouter."""
        if not self._initialized:
            await self.initialize()
            
        try:
            async with self.session.get(f"{self.base_url}/models") as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter models API error: {response.status} - {error_text}")
                    raise Exception(f"OpenRouter models API error: {response.status}")
                
                data = await response.json()
                
                if "data" in data:
                    # Filter and format models for better usability
                    models = []
                    for model in data["data"]:
                        models.append({
                            "id": model["id"],
                            "name": model.get("name", model["id"]),
                            "description": model.get("description", ""),
                            "context_length": model.get("context_length", 0),
                            "pricing": model.get("pricing", {}),
                            "top_provider": model.get("top_provider", {}),
                            "per_request_limits": model.get("per_request_limits")
                        })
                    return models
                else:
                    logger.error(f"Unexpected models response format: {data}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching models: {str(e)}")
            return []
    
    async def get_popular_models(self) -> List[Dict[str, Any]]:
        """Get a curated list of popular/recommended models."""
        all_models = await self.list_models()
        
        # List of preferred free models (in priority order)
        preferred_free_models = [
            "x-ai/grok-4-fast:free",        # 首选：Grok 4 Fast - 速度快、质量高
            "deepseek/deepseek-chat-v3.1:free",  # DeepSeek V3.1 - 推理能力强
            "nvidia/nemotron-nano-9b-v2:free",   # NVIDIA Nemotron - 平衡性好
            "openai/gpt-oss-120b:free",          # OpenAI开源模型
            "openai/gpt-oss-20b:free"            # OpenAI轻量模型
        ]
        
        # List of popular paid model IDs to prioritize
        popular_model_ids = [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o", 
            "google/gemini-2.0-flash-exp",
            "meta-llama/llama-3.1-405b-instruct",
            "deepseek/deepseek-v3",
            "qwen/qwen-2.5-72b-instruct",
            "mistralai/mistral-large-2407"
        ]
        
        # Add free models
        free_models = [model for model in all_models if 
                      model["id"].endswith(":free") or 
                      (model.get("pricing", {}).get("prompt", "0") == "0" and
                       model.get("pricing", {}).get("completion", "0") == "0")]
        
        # Get popular models
        popular_models = [model for model in all_models if model["id"] in popular_model_ids]
        
        # Combine and deduplicate with intelligent ordering
        result = []
        seen_ids = set()
        
        # 1. Add preferred free models in priority order
        for preferred_id in preferred_free_models:
            model = next((m for m in all_models if m["id"] == preferred_id), None)
            if model and model["id"] not in seen_ids:
                result.append(model)
                seen_ids.add(model["id"])
        
        # 2. Add remaining free models  
        for model in free_models:
            if model["id"] not in seen_ids and len([m for m in result if self._is_free_model(m)]) < 8:
                result.append(model)
                seen_ids.add(model["id"])
        
        # 3. Add popular paid models
        for model in popular_models:
            if model["id"] not in seen_ids and len(result) < 15:
                result.append(model)
                seen_ids.add(model["id"])
                
        return result[:15]  # Limit to 15 total models
    
    def _is_free_model(self, model: Dict[str, Any]) -> bool:
        """Check if a model is free."""
        return (model["id"].endswith(":free") or 
                (model.get("pricing", {}).get("prompt", "0") == "0" and
                 model.get("pricing", {}).get("completion", "0") == "0"))
    
    async def health_check(self) -> bool:
        """Check if the service is healthy."""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Simple health check by getting models
            models = await self.list_models()
            return len(models) > 0
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
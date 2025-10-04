"""
Web Search API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from backend.core.web_search import web_search_service
from backend.core.ai_service import ai_manager

router = APIRouter()


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索关键词")
    num_results: int = Field(default=3, ge=1, le=10, description="返回结果数量")
    engine: str = Field(default="duckduckgo", description="搜索引擎")
    use_ai_summary: bool = Field(default=True, description="是否使用AI总结")


class SearchResponse(BaseModel):
    """搜索响应模型"""
    query: str = Field(..., description="搜索关键词")
    results: List[Dict[str, Any]] = Field(..., description="搜索结果")
    summary: Optional[str] = Field(default=None, description="AI总结")
    timestamp: str = Field(..., description="搜索时间")


@router.post("/", response_model=SearchResponse)
async def web_search(request: SearchRequest):
    """
    执行网络搜索
    """
    try:
        if request.use_ai_summary:
            # 使用AI总结搜索结果
            result = await web_search_service.search_and_summarize(
                query=request.query,
                ai_service=ai_manager.ai_service,
                num_results=request.num_results
            )
            return SearchResponse(**result)
        else:
            # 仅返回搜索结果
            search_results = await web_search_service.search(
                query=request.query,
                num_results=request.num_results,
                engine=request.engine
            )
            
            return SearchResponse(
                query=request.query,
                results=[result.to_dict() for result in search_results],
                summary=None,
                timestamp=search_results[0].timestamp if search_results else ""
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/engines")
async def get_search_engines():
    """
    获取可用的搜索引擎列表
    """
    return {
        "engines": [
            {
                "id": "duckduckgo",
                "name": "DuckDuckGo",
                "description": "隐私友好的搜索引擎，无需API密钥",
                "requires_api_key": False
            },
            {
                "id": "bing",
                "name": "Microsoft Bing",
                "description": "微软搜索引擎，需要API密钥",
                "requires_api_key": True
            },
            {
                "id": "google",
                "name": "Google (自定义搜索)",
                "description": "Google自定义搜索API，需要API密钥",
                "requires_api_key": True
            }
        ]
    }


@router.get("/test")
async def test_search(
    query: str = Query(..., description="测试搜索关键词"),
    engine: str = Query(default="duckduckgo", description="搜索引擎")
):
    """
    测试搜索功能
    """
    try:
        results = await web_search_service.search(
            query=query,
            num_results=3,
            engine=engine
        )
        
        return {
            "status": "success",
            "query": query,
            "engine": engine,
            "results_count": len(results),
            "results": [result.to_dict() for result in results]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "engine": engine,
            "error": str(e)
        }
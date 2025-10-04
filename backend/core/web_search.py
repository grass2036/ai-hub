"""
Web Search Service
支持多种搜索引擎的联网搜索功能
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from urllib.parse import quote_plus
import logging

logger = logging.getLogger(__name__)

class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, source: str = ""):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "timestamp": self.timestamp
        }

class WebSearchService:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    async def search(self, query: str, num_results: int = 5, engine: str = "duckduckgo") -> List[SearchResult]:
        """
        执行网络搜索
        
        Args:
            query: 搜索关键词
            num_results: 返回结果数量
            engine: 搜索引擎 (duckduckgo, bing, google)
        
        Returns:
            SearchResult列表
        """
        try:
            if engine == "duckduckgo":
                return await self._search_duckduckgo(query, num_results)
            elif engine == "bing":
                return await self._search_bing(query, num_results)
            elif engine == "google":
                return await self._search_google_fallback(query, num_results)
            else:
                # 默认使用DuckDuckGo
                return await self._search_duckduckgo(query, num_results)
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    async def _search_duckduckgo(self, query: str, num_results: int) -> List[SearchResult]:
        """使用DuckDuckGo搜索（无需API密钥）"""
        results = []
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # 第一步：获取搜索token
                async with session.get(
                    "https://html.duckduckgo.com/",
                    headers={"User-Agent": self.user_agent}
                ) as response:
                    html = await response.text()
                
                # 第二步：执行搜索
                search_url = f"https://html.duckduckgo.com/html/"
                data = {
                    'q': query,
                    'b': '',
                    'kl': 'wt-wt',
                    'df': ''
                }
                
                async with session.post(
                    search_url,
                    data=data,
                    headers={"User-Agent": self.user_agent}
                ) as response:
                    html = await response.text()
                    results = self._parse_duckduckgo_results(html, num_results)
                    
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        
        return results
    
    def _parse_duckduckgo_results(self, html: str, num_results: int) -> List[SearchResult]:
        """解析DuckDuckGo搜索结果"""
        results = []
        
        # 简单的HTML解析（生产环境建议使用BeautifulSoup）
        import re
        
        # DuckDuckGo has updated their HTML structure, try multiple patterns
        patterns = [
            # Original pattern
            r'<div class="result__body">.*?<a class="result__a" href="(.*?)".*?>(.*?)</a>.*?<a class="result__snippet".*?>(.*?)</a>',
            # Alternative pattern for newer DuckDuckGo
            r'<article.*?data-testid="result".*?<h2.*?<a.*?href="(.*?)".*?>(.*?)</a>.*?<div.*?data-result="snippet".*?>(.*?)</div>',
            # Another pattern for links
            r'<h3.*?result__title.*?<a.*?href="(.*?)".*?>(.*?)</a>.*?<a.*?result__snippet.*?>(.*?)</a>',
        ]
        
        logger.info(f"Parsing DuckDuckGo HTML (length: {len(html)})")
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            logger.info(f"Pattern found {len(matches)} matches")
            
            if matches:
                for i, (url, title, snippet) in enumerate(matches[:num_results]):
                    # 清理HTML标签
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                    
                    # 修复相对URL
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = 'https://duckduckgo.com' + url
                    
                    if title and url and 'duckduckgo.com' not in url:
                        results.append(SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            source="DuckDuckGo"
                        ))
                        logger.info(f"Added result: {title[:50]}...")
                
                if results:
                    break
        
        if not results:
            logger.warning("No search results found, saving HTML for debugging")
            # 保存HTML用于调试
            with open("/tmp/duckduckgo_debug.html", "w", encoding='utf-8') as f:
                f.write(html)
        
        return results
    
    async def _search_bing(self, query: str, num_results: int) -> List[SearchResult]:
        """使用Bing搜索（需要API密钥）"""
        # TODO: 实现Bing搜索API
        # 需要在环境变量中配置 BING_SEARCH_API_KEY
        results = []
        
        try:
            import os
            api_key = os.getenv("BING_SEARCH_API_KEY")
            if not api_key:
                logger.warning("Bing API key not found, falling back to DuckDuckGo")
                return await self._search_duckduckgo(query, num_results)
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                headers = {
                    "Ocp-Apim-Subscription-Key": api_key,
                    "User-Agent": self.user_agent
                }
                
                url = f"https://api.bing.microsoft.com/v7.0/search?q={quote_plus(query)}&count={num_results}"
                
                async with session.get(url, headers=headers) as response:
                    data = await response.json()
                    
                    for item in data.get("webPages", {}).get("value", []):
                        results.append(SearchResult(
                            title=item.get("name", ""),
                            url=item.get("url", ""),
                            snippet=item.get("snippet", ""),
                            source="Bing"
                        ))
                        
        except Exception as e:
            logger.error(f"Bing search error: {e}")
        
        return results
    
    async def _search_google_fallback(self, query: str, num_results: int) -> List[SearchResult]:
        """Google搜索备选方案（使用自定义搜索API）"""
        # TODO: 实现Google自定义搜索API
        # 需要配置 GOOGLE_SEARCH_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID
        
        # 暂时回退到DuckDuckGo
        logger.info("Google search not implemented, using DuckDuckGo fallback")
        return await self._search_duckduckgo(query, num_results)
    
    async def search_and_summarize(self, query: str, ai_service, num_results: int = 3) -> Dict[str, Any]:
        """
        搜索并使用AI总结结果
        
        Args:
            query: 搜索关键词
            ai_service: AI服务实例
            num_results: 搜索结果数量
        
        Returns:
            包含搜索结果和AI总结的字典
        """
        # 执行搜索
        search_results = await self.search(query, num_results)
        
        if not search_results:
            return {
                "query": query,
                "results": [],
                "summary": "抱歉，没有找到相关的搜索结果。"
            }
        
        # 构建用于AI总结的文本
        search_text = f"用户搜索: {query}\n\n搜索结果:\n"
        for i, result in enumerate(search_results, 1):
            search_text += f"{i}. 标题: {result.title}\n"
            search_text += f"   链接: {result.url}\n"
            search_text += f"   摘要: {result.snippet}\n\n"
        
        # 构建提示词
        prompt = f"""请根据以下搜索结果，为用户提供一个准确、有用的回答。

{search_text}

请要求:
1. 基于搜索结果提供准确信息
2. 如果信息不确定，请说明
3. 提供相关的链接供用户参考
4. 回答要简洁明了

用户问题: {query}
"""
        
        try:
            # 使用AI服务生成总结
            summary = await ai_service.generate_response(prompt)
            
            return {
                "query": query,
                "results": [result.to_dict() for result in search_results],
                "summary": summary,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return {
                "query": query,
                "results": [result.to_dict() for result in search_results],
                "summary": "搜索完成，但AI总结暂时不可用。请查看以下搜索结果:",
                "timestamp": datetime.now().isoformat()
            }

# 全局搜索服务实例
web_search_service = WebSearchService()
"""
插件市场API接口
Week 7 Day 4: 生态系统建设

提供插件发布、搜索、评价和管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import json
import shutil
from pathlib import Path

from backend.core.plugin_system.plugin_manager import PluginManager
from backend.core.plugin_system.plugin_interface import PluginMetadata, PluginStatus
from backend.core.logging_service import logging_service

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局插件管理器实例
plugin_manager = PluginManager("data/hub")


# 请求��型
class PluginSearchRequest(BaseModel):
    """插件搜索请求"""
    query: str = Field("", description="搜索关键词")
    category: Optional[str] = Field(None, description="插件分类")
    plugin_type: Optional[str] = Field(None, description="插件类型")
    tags: List[str] = Field(default_factory=list, description="标签过滤")
    sort_by: str = Field("popularity", description="排序方式")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class PluginReviewRequest(BaseModel):
    """插件评价请求"""
    plugin_id: str = Field(..., description="插件ID")
    rating: int = Field(..., ge=1, le=5, description="评分(1-5)")
    title: str = Field(..., description="评价标题")
    content: str = Field(..., description="评价内容")
    pros: List[str] = Field(default_factory=list, description="优点")
    cons: List[str] = Field(default_factory=list, description="缺点")


class PluginReportRequest(BaseModel):
    """插件举报请求"""
    plugin_id: str = Field(..., description="插件ID")
    reason: str = Field(..., description="举报原因")
    description: str = Field(..., description="详细描述")
    category: str = Field(..., description="举报类别")


class PluginStatsRequest(BaseModel):
    """插件统计请求"""
    plugin_id: str = Field(..., description="插件ID")
    period: str = Field("7d", description="统计周期")


# 响应模型
class PluginSearchResponse(BaseModel):
    """插件搜索响应"""
    plugins: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    facets: Dict[str, Any]


class PluginDetailResponse(BaseModel):
    """插件详情响应"""
    plugin: Dict[str, Any]
    versions: List[Dict[str, Any]]
    reviews: List[Dict[str, Any]]
    stats: Dict[str, Any]
    related_plugins: List[Dict[str, Any]]


class PluginUploadResponse(BaseModel):
    """插件上传响应"""
    plugin_id: str
    version: str
    status: str
    message: str
    validation_results: Dict[str, Any]


# 模拟数据存储
class PluginMarketplace:
    """插件市场数据存储"""

    def __init__(self):
        self.plugins_db = Path("data/marketplace/plugins.json")
        self.reviews_db = Path("data/marketplace/reviews.json")
        self.stats_db = Path("data/marketplace/stats.json")
        self.downloads_db = Path("data/marketplace/downloads.json")

        # 创建目录
        self.plugins_db.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据
        self._init_data()

    def _init_data(self):
        """初始化数据"""
        if not self.plugins_db.exists():
            with open(self.plugins_db, 'w') as f:
                json.dump({}, f)

        if not self.reviews_db.exists():
            with open(self.reviews_db, 'w') as f:
                json.dump({}, f)

        if not self.stats_db.exists():
            with open(self.stats_db, 'w') as f:
                json.dump({}, f)

        if not self.downloads_db.exists():
            with open(self.downloads_db, 'w') as f:
                json.dump({}, f)

    def _load_data(self, file_path: Path) -> Dict[str, Any]:
        """加载数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _save_data(self, file_path: Path, data: Dict[str, Any]):
        """保存数据"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_plugins(self) -> Dict[str, Any]:
        """获取所有插件"""
        return self._load_data(self.plugins_db)

    def save_plugin(self, plugin_id: str, plugin_data: Dict[str, Any]):
        """保存插件数据"""
        plugins = self.get_plugins()
        plugins[plugin_id] = plugin_data
        self._save_data(self.plugins_db, plugins)

    def get_reviews(self, plugin_id: str) -> List[Dict[str, Any]]:
        """获取插件评价"""
        reviews = self._load_data(self.reviews_db)
        return reviews.get(plugin_id, [])

    def add_review(self, plugin_id: str, review: Dict[str, Any]):
        """添加插件评价"""
        reviews = self._load_data(self.reviews_db)
        if plugin_id not in reviews:
            reviews[plugin_id] = []
        reviews[plugin_id].append(review)
        self._save_data(self.reviews_db, reviews)

    def get_stats(self, plugin_id: str) -> Dict[str, Any]:
        """获取插件统计"""
        stats = self._load_data(self.stats_db)
        return stats.get(plugin_id, {
            "downloads": 0,
            "installs": 0,
            "ratings": [],
            "daily_downloads": {}
        })

    def update_stats(self, plugin_id: str, stat_updates: Dict[str, Any]):
        """更新插件统计"""
        stats = self._load_data(self.stats_db)
        if plugin_id not in stats:
            stats[plugin_id] = {
                "downloads": 0,
                "installs": 0,
                "ratings": [],
                "daily_downloads": {}
            }

        stats[plugin_id].update(stat_updates)
        self._save_data(self.stats_db, stats)

    def record_download(self, plugin_id: str, user_id: str = "anonymous"):
        """记录下载"""
        downloads = self._load_data(self.downloads_db)
        today = datetime.now().strftime("%Y-%m-%d")

        if plugin_id not in downloads:
            downloads[plugin_id] = {"total": 0, "daily": {}, "users": set()}

        downloads[plugin_id]["total"] += 1
        downloads[plugin_id]["daily"][today] = downloads[plugin_id]["daily"].get(today, 0) + 1
        downloads[plugin_id]["users"].add(user_id)

        self._save_data(self.downloads_db, downloads)

    def search_plugins(self, search_request: PluginSearchRequest) -> PluginSearchResponse:
        """搜索插件"""
        plugins = self.get_plugins()
        results = []

        for plugin_id, plugin_data in plugins.items():
            # 应用过滤条件
            if search_request.query:
                query_lower = search_request.query.lower()
                if (query_lower not in plugin_data.get("name", "").lower() and
                    query_lower not in plugin_data.get("description", "").lower() and
                    not any(query_lower in tag.lower() for tag in plugin_data.get("tags", []))):
                    continue

            if search_request.category and plugin_data.get("category") != search_request.category:
                continue

            if search_request.plugin_type and plugin_data.get("plugin_type") != search_request.plugin_type:
                continue

            if search_request.tags and not any(tag in plugin_data.get("tags", []) for tag in search_request.tags):
                continue

            # 添加统计信息
            stats = self.get_stats(plugin_id)
            plugin_data["stats"] = stats

            results.append(plugin_data)

        # 排序
        if search_request.sort_by == "popularity":
            results.sort(key=lambda x: x.get("stats", {}).get("downloads", 0), reverse=True)
        elif search_request.sort_by == "rating":
            results.sort(key=lambda x: x.get("stats", {}).get("avg_rating", 0), reverse=True)
        elif search_request.sort_by == "created":
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        elif search_request.sort_by == "updated":
            results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        # 分页
        total_count = len(results)
        page = search_request.page
        page_size = search_request.page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = results[start_idx:end_idx]

        # 生成聚合信息
        facets = {
            "categories": {},
            "types": {},
            "tags": {}
        }

        for plugin_id, plugin_data in plugins.items():
            category = plugin_data.get("category", "other")
            plugin_type = plugin_data.get("plugin_type", "utility")

            facets["categories"][category] = facets["categories"].get(category, 0) + 1
            facets["types"][plugin_type] = facets["types"].get(plugin_type, 0) + 1

            for tag in plugin_data.get("tags", []):
                facets["tags"][tag] = facets["tags"].get(tag, 0) + 1

        return PluginSearchResponse(
            plugins=page_results,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
            facets=facets
        )


# 全局插件市场实例
plugin_marketplace = PluginMarketplace()


@router.get("/search", response_model=PluginSearchResponse, summary="搜索插件")
async def search_plugins(search_request: PluginSearchRequest):
    """
    搜索插件市场中的插件

    - **query**: 搜索关键词
    - **category**: 插件分类
    - **plugin_type**: 插件类型
    - **tags**: 标签过滤
    - **sort_by**: 排序方式(popularity, rating, created, updated)
    - **page**: 页码
    - **page_size**: 每页数量
    """
    try:
        result = plugin_marketplace.search_plugins(search_request)

        await logging_service.log_user_behavior(
            user_id="anonymous",
            action="plugin_search",
            resource_type="plugin_market",
            details={
                "query": search_request.query,
                "category": search_request.category,
                "results_count": len(result.plugins)
            }
        )

        return result

    except Exception as e:
        logger.error(f"Failed to search plugins: {e}")
        raise HTTPException(status_code=500, detail="搜索插件失败")


@router.get("/featured", summary="获取推荐插件")
async def get_featured_plugins(limit: int = 10):
    """
    获取推荐插件
    """
    try:
        plugins = plugin_marketplace.get_plugins()

        # 筛选推荐插件（可以根据各种条件）
        featured_plugins = []
        for plugin_id, plugin_data in plugins.items():
            stats = plugin_marketplace.get_stats(plugin_id)

            # 推荐条件：下载量 > 10 或评分 > 4.0
            if (stats.get("downloads", 0) > 10 or
                stats.get("avg_rating", 0) > 4.0):
                plugin_data["stats"] = stats
                featured_plugins.append(plugin_data)

        # 按下载量排序
        featured_plugins.sort(key=lambda x: x.get("stats", {}).get("downloads", 0), reverse=True)

        return {
            "featured_plugins": featured_plugins[:limit],
            "total_count": len(featured_plugins)
        }

    except Exception as e:
        logger.error(f"Failed to get featured plugins: {e}")
        raise HTTPException(status_code=500, detail="获取推荐插件失败")


@router.get("/categories", summary="获取插件分类")
async def get_plugin_categories():
    """
    获取所有插件分类
    """
    try:
        categories = {
            "ai_model": {"name": "AI模型", "description": "各种AI模型插件"},
            "data_processor": {"name": "数据处理", "description": "数据处理和转换插件"},
            "authentication": {"name": "认证授权", "description": "身份认证和授权插件"},
            "notification": {"name": "通知服务", "description": "各种通知服务插件"},
            "analytics": {"name": "数据分析", "description": "数据分析和统计插件"},
            "storage": {"name": "存储服务", "description": "各种存储服务插件"},
            "workflow": {"name": "工作流", "description": "工作流相关插件"},
            "ui_component": {"name": "UI组件", "description": "用户界面组件插件"},
            "integration": {"name": "第三方集成", "description": "第三方服务集成插件"},
            "utility": {"name": "工具类", "description": "各种实用工具插件"}
        }

        return {"categories": categories}

    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail="获取分类失败")


@router.get("/{plugin_id}", response_model=PluginDetailResponse, summary="获取插件详情")
async def get_plugin_detail(plugin_id: str):
    """
    获取插件详细信息
    """
    try:
        plugins = plugin_marketplace.get_plugins()

        if plugin_id not in plugins:
            raise HTTPException(status_code=404, detail="插件不存在")

        plugin_data = plugins[plugin_id]

        # 获取统计信息
        stats = plugin_marketplace.get_stats(plugin_id)

        # 获取评价
        reviews = plugin_marketplace.get_reviews(plugin_id)

        # 获取相关插件
        related_plugins = []
        for related_id, related_data in plugins.items():
            if (related_id != plugin_id and
                related_data.get("category") == plugin_data.get("category") and
                len(related_plugins) < 5):
                related_stats = plugin_marketplace.get_stats(related_id)
                related_data["stats"] = related_stats
                related_plugins.append(related_data)

        return PluginDetailResponse(
            plugin=plugin_data,
            versions=[plugin_data],  # 简化实现，实际应该存储多个版本
            reviews=reviews,
            stats=stats,
            related_plugins=related_plugins
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plugin detail: {e}")
        raise HTTPException(status_code=500, detail="获取插件详情失败")


@router.post("/{plugin_id}/download", summary="下载插件")
async def download_plugin(plugin_id: str, user_id: str = "anonymous"):
    """
    下载插件包
    """
    try:
        plugins = plugin_marketplace.get_plugins()

        if plugin_id not in plugins:
            raise HTTPException(status_code=404, detail="插件不存在")

        # 记录下载
        plugin_marketplace.record_download(plugin_id, user_id)

        # 更新统计
        current_stats = plugin_marketplace.get_stats(plugin_id)
        plugin_marketplace.update_stats(plugin_id, {
            "downloads": current_stats.get("downloads", 0) + 1,
            "last_download": datetime.now().isoformat()
        })

        # 返回下载链接（实际实现中应该生成临时下载链接）
        plugin_data = plugins[plugin_id]

        await logging_service.log_user_behavior(
            user_id=user_id,
            action="plugin_download",
            resource_type="plugin_market",
            details={"plugin_id": plugin_id}
        )

        return {
            "download_url": f"/api/v1/plugin-market/{plugin_id}/package",
            "filename": f"{plugin_id}-{plugin_data.get('version', '1.0.0')}.zip",
            "size": "1024KB",  # 实际应该计算文件大小
            "checksum": "abc123"  # 实际应该计算文件校验和
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download plugin: {e}")
        raise HTTPException(status_code=500, detail="下载插件失败")


@router.get("/{plugin_id}/package", summary="获取插件包")
async def get_plugin_package(plugin_id: str):
    """
    获取插件包文件
    """
    try:
        # 实际实现中应该返回插件包文件
        # 这里简化为返回包信息

        plugins = plugin_marketplace.get_plugins()
        if plugin_id not in plugins:
            raise HTTPException(status_code=404, detail="插件不存在")

        # 这里应该返回实际的文件内容
        # 由于是示例，我们返回错误提示
        raise HTTPException(status_code=501, detail="插件包下载功能待实现")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plugin package: {e}")
        raise HTTPException(status_code=500, detail="获取插件包失败")


@router.post("/{plugin_id}/review", summary="评价插件")
async def review_plugin(plugin_id: str, review_request: PluginReviewReview, user_id: str = "anonymous"):
    """
        plugin_id: str = Field(..., description="插件ID")
        rating: int = Field(..., ge=1, le=5, description="评分(1-5)")
        title: str = Field(..., description="评价标题")
        content: str = Field(..., description="评价内容")
        pros: List[str] = Field(default_factory=list, description="优点")
        cons: List[str] = Field(default_factory=list, description="缺点")
    """
    try:
        plugins = plugin_marketplace.get_plugins()

        if plugin_id not in plugins:
            raise HTTPException(status_code=404, detail="插件不存在")

        # 创建评价
        review = {
            "id": f"review_{datetime.now().timestamp()}",
            "user_id": user_id,
            "rating": review_request.rating,
            "title": review_request.title,
            "content": review_request.content,
            "pros": review_request.pros,
            "cons": review_request.cons,
            "created_at": datetime.now().isoformat(),
            "helpful": 0,
            "verified": user_id != "anonymous"  # 简化的验证逻辑
        }

        # 保存评价
        plugin_marketplace.add_review(plugin_id, review)

        # 更新统计
        current_stats = plugin_marketplace.get_stats(plugin_id)
        ratings = current_stats.get("ratings", [])
        ratings.append(review_request.rating)

        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        plugin_marketplace.update_stats(plugin_id, {
            "ratings": ratings,
            "avg_rating": avg_rating,
            "review_count": len(ratings)
        })

        await logging_service.log_user_behavior(
            user_id=user_id,
            action="plugin_review",
            resource_type="plugin_market",
            details={
                "plugin_id": plugin_id,
                "rating": review_request.rating
            }
        )

        return {
            "success": True,
            "message": "评价提交成功",
            "review_id": review["id"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to review plugin: {e}")
        raise HTTPException(status_code=500, detail="提交评价失败")


@router.get("/{plugin_id}/stats", summary="获取插件统计")
async def get_plugin_stats(plugin_id: str, period: str = "7d"):
    """
    获取插件统计信息
    """
    try:
        plugins = plugin_marketplace.get_plugins()

        if plugin_id not in plugins:
            raise HTTPException(status_code=404, detail="插件不存在")

        stats = plugin_marketplace.get_stats(plugin_id)

        # 根据周期过滤数据
        filtered_stats = {
            "downloads": stats.get("downloads", 0),
            "installs": stats.get("installs", 0),
            "avg_rating": stats.get("avg_rating", 0),
            "review_count": len(stats.get("ratings", [])),
            "period": period
        }

        # 添加周期性下载统计
        if "daily_downloads" in stats:
            filtered_stats["daily_downloads"] = stats["daily_downloads"]

        return filtered_stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plugin stats: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.post("/upload", response_model=PluginUploadResponse, summary="上传插件")
async def upload_plugin(
    background_tasks: BackgroundTasks,
    plugin_file: UploadFile = File(...),
    metadata_file: UploadFile = File(...),
    user_id: str = "anonymous"
):
    """
    上传插件到市场
    """
    try:
        # 验证文件类型
        if not plugin_file.filename.endswith('.zip') and not plugin_file.filename.endswith('.tar.gz'):
            raise HTTPException(status_code=400, detail="插件文件格式不支持")

        if not metadata_file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="元数据文件必须是JSON格式")

        # 读取元数据
        metadata_content = await metadata_file.read()
        try:
            metadata = json.loads(metadata_content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="元数据文件格式错误")

        # 验证必需字段
        required_fields = ["id", "name", "version", "description", "author"]
        for field in required_fields:
            if field not in metadata:
                raise HTTPException(status_code=400, detail=f"缺少必需字段: {field}")

        plugin_id = metadata["id"]

        # 检查插件是否已存在
        plugins = plugin_marketplace.get_plugins()
        if plugin_id in plugins:
            existing_version = plugins[plugin_id].get("version", "0.0.0")
            if metadata["version"] <= existing_version:
                raise HTTPException(status_code=400, detail="插件版本必须高于现有版本")

        # 保存插件文件
        uploads_dir = Path("data/marketplace/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        plugin_filename = f"{plugin_id}-{metadata['version']}.zip"
        plugin_path = uploads_dir / plugin_filename

        with open(plugin_path, "wb") as f:
            shutil.copyfileobj(plugin_file.file, f)

        # 保存插件元数据
        plugin_data = {
            **metadata,
            "uploaded_by": user_id,
            "uploaded_at": datetime.now().isoformat(),
            "file_path": str(plugin_path),
            "file_size": plugin_path.stat().st_size,
            "status": "pending_review"
        }

        plugin_marketplace.save_plugin(plugin_id, plugin_data)

        # 后台任务：验证插件
        background_tasks.add_task(validate_uploaded_plugin, plugin_id, str(plugin_path))

        await logging_service.log_user_behavior(
            user_id=user_id,
            action="plugin_upload",
            resource_type="plugin_market",
            details={
                "plugin_id": plugin_id,
                "version": metadata["version"]
            }
        )

        return PluginUploadResponse(
            plugin_id=plugin_id,
            version=metadata["version"],
            status="pending_review",
            message="插件上传成功，正在审核中",
            validation_results={}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload plugin: {e}")
        raise HTTPException(status_code=500, detail="上传插件失败")


async def validate_uploaded_plugin(plugin_id: str, plugin_path: str):
    """
    验证上传的插件（后台任务）
    """
    try:
        # 这里应该实现插件验证逻辑
        # 包括：安全性检查、功能测试、兼容性验证等

        logger.info(f"Validating plugin {plugin_id}")

        # 模拟验证过程
        await asyncio.sleep(2)

        # 更新插件状态
        plugins = plugin_marketplace.get_plugins()
        if plugin_id in plugins:
            plugins[plugin_id]["status"] = "approved"
            plugins[plugin_id]["validated_at"] = datetime.now().isoformat()
            plugin_marketplace.save_plugin(plugin_id, plugins[plugin_id])

        logger.info(f"Plugin {plugin_id} validation completed")

    except Exception as e:
        logger.error(f"Failed to validate plugin {plugin_id}: {e}")

        # 更新状态为验证失败
        plugins = plugin_marketplace.get_plugins()
        if plugin_id in plugins:
            plugins[plugin_id]["status"] = "validation_failed"
            plugins[plugin_id]["validation_error"] = str(e)
            plugin_marketplace.save_plugin(plugin_id, plugins[plugin_id])


@router.post("/{plugin_id}/report", summary="举报插件")
async def report_plugin(plugin_id: str, report_request: PluginReportRequest, user_id: str = "anonymous"):
    """
    举报插件
    """
    try:
        plugins = plugin_marketplace.get_plugins()

        if plugin_id not in plugins:
            raise HTTPException(status_code=404, detail="插件不存在")

        # 创建举报记录
        report = {
            "id": f"report_{datetime.now().timestamp()}",
            "plugin_id": plugin_id,
            "user_id": user_id,
            "reason": report_request.reason,
            "description": report_request.description,
            "category": report_request.category,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }

        # 保存举报记录（简化实现）
        reports_file = Path("data/marketplace/reports.json")
        reports_file.parent.mkdir(parents=True, exist_ok=True)

        reports = {}
        if reports_file.exists():
            with open(reports_file, 'r') as f:
                reports = json.load(f)

        if "reports" not in reports:
            reports["reports"] = []

        reports["reports"].append(report)

        with open(reports_file, 'w') as f:
            json.dump(reports, f, indent=2)

        await logging_service.log_user_behavior(
            user_id=user_id,
            action="plugin_report",
            resource_type="plugin_market",
            details={
                "plugin_id": plugin_id,
                "reason": report_request.reason
            }
        )

        return {
            "success": True,
            "message": "举报已提交，我们会尽快处理",
            "report_id": report["id"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to report plugin: {e}")
        raise HTTPException(status_code=500, detail="提交举报失败")
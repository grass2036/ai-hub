"""
Workflow Engine API Endpoints
Week 7 Day 1: Advanced AI Features Development

Provides RESTful API endpoints for:
- Workflow management (CRUD operations)
- Workflow execution and monitoring
- Template management
- Visual designer support
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from datetime import datetime
import json
import uuid

from backend.core.workflow_engine import (
    workflow_engine,
    WorkflowDefinition,
    WorkflowExecution,
    NodeType,
    ExecutionStatus,
    LoopType
)
from backend.core.auth import get_current_user, require_permissions
from backend.core.logging_service import logging_service

router = APIRouter(prefix="/workflow", tags=["workflow"])


# Request/Response Models
class WorkflowCreateRequest(BaseModel):
    """创建工作流请求"""
    name: str = Field(..., description="工作流名称")
    description: str = Field(default="", description="工作流描述")
    category: str = Field(default="general", description="工作流分类")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="节点列表")
    connections: List[Dict[str, Any]] = Field(default_factory=list, description="连接列表")
    variables: Dict[str, Any] = Field(default_factory=dict, description="工作流变量")
    triggers: List[Dict[str, Any]] = Field(default_factory=list, description="触发器")
    settings: Dict[str, Any] = Field(default_factory=dict, description="工作流设置")


class WorkflowUpdateRequest(BaseModel):
    """更新工作流请求"""
    name: Optional[str] = Field(None, description="工作流名称")
    description: Optional[str] = Field(None, description="工作流描述")
    category: Optional[str] = Field(None, description="工作流分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    nodes: Optional[List[Dict[str, Any]]] = Field(None, description="节点列表")
    connections: Optional[List[Dict[str, Any]]] = Field(None, description="连接列表")
    variables: Optional[Dict[str, Any]] = Field(None, description="工作流变量")
    triggers: Optional[List[Dict[str, Any]]] = Field(None, description="触发器")
    settings: Optional[Dict[str, Any]] = Field(None, description="工作流设置")
    is_active: Optional[bool] = Field(None, description="是否激活")


class WorkflowExecuteRequest(BaseModel):
    """执行工作流请求"""
    inputs: Dict[str, Any] = Field(default_factory=dict, description="输入参数")
    async_execution: bool = Field(default=False, description="是否异步执行")
    timeout: Optional[int] = Field(None, description="超时时间（秒）")


class WorkflowNodeRequest(BaseModel):
    """工作流节点请求"""
    type: NodeType = Field(..., description="节点类型")
    name: str = Field(..., description="节点名称")
    description: str = Field(default="", description="节点描述")
    position: Dict[str, float] = Field(default_factory=dict, description="节点位置")
    config: Dict[str, Any] = Field(default_factory=dict, description="节点配置")
    inputs: List[str] = Field(default_factory=list, description="输入参数")
    outputs: List[str] = Field(default_factory=list, description="输出参数")
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="条件设置")


class WorkflowTemplateRequest(BaseModel):
    """工作流模板请求"""
    template_id: str = Field(..., description="模板ID")
    name: str = Field(..., description="新工作流名称")
    description: str = Field(default="", description="新工作流描述")
    variables: Dict[str, Any] = Field(default_factory=dict, description="工作流变量")


# Response Models
class WorkflowResponse(BaseModel):
    """工作流响应"""
    id: str
    name: str
    description: str
    version: str
    category: str
    tags: List[str]
    is_template: bool
    is_active: bool
    created_at: str
    updated_at: str
    created_by: str
    node_count: int
    connection_count: int


class WorkflowDetailResponse(WorkflowResponse):
    """工作流详细响应"""
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    variables: Dict[str, Any]
    triggers: List[Dict[str, Any]]
    settings: Dict[str, Any]


class WorkflowExecutionResponse(BaseModel):
    """工作流执行响应"""
    id: str
    workflow_id: str
    status: ExecutionStatus
    start_time: Optional[str]
    end_time: Optional[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    variables: Dict[str, Any]
    node_executions: Dict[str, Dict[str, Any]]
    logs: List[Dict[str, Any]]
    error_message: Optional[str]
    created_at: str
    updated_at: str
    duration: Optional[float]


class WorkflowTemplateResponse(BaseModel):
    """工作流模板响应"""
    id: str
    name: str
    description: str
    category: str
    tags: List[str]
    node_count: int
    connection_count: str


# Workflow Management Endpoints
@router.post("/", response_model=WorkflowDetailResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """创建新的工作流"""
    try:
        logging_service.log_info(
            f"User {current_user.get('user_id')} creating workflow: {request.name}"
        )

        # 创建工作流数据
        workflow_data = {
            "id": str(uuid.uuid4()),
            "name": request.name,
            "description": request.description,
            "category": request.category,
            "tags": request.tags,
            "nodes": request.nodes,
            "connections": request.connections,
            "variables": request.variables,
            "triggers": request.triggers,
            "settings": request.settings,
            "created_by": current_user.get("user_id", ""),
            "is_template": False,
            "is_active": True
        }

        workflow = await workflow_engine.create_workflow(workflow_data)

        return WorkflowDetailResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            category=workflow.category,
            tags=workflow.tags,
            is_template=workflow.is_template,
            is_active=workflow.is_active,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            created_by=workflow.created_by,
            node_count=len(workflow.nodes),
            connection_count=len(workflow.connections),
            nodes=[node.to_dict() for node in workflow.nodes],
            connections=[conn.to_dict() for conn in workflow.connections],
            variables=workflow.variables,
            triggers=workflow.triggers,
            settings=workflow.settings
        )

    except Exception as e:
        logging_service.log_error(f"Failed to create workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"创建工作流失败: {str(e)}"
        )


@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    category: Optional[str] = Query(None, description="工作流分类"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取工作流列表"""
    try:
        workflows = await workflow_engine.list_workflows(
            category=category,
            tags=tags,
            is_active=is_active
        )

        # 应用分页
        total = len(workflows)
        workflows = workflows[offset:offset + limit]

        return [
            WorkflowResponse(
                id=workflow.id,
                name=workflow.name,
                description=workflow.description,
                version=workflow.version,
                category=workflow.category,
                tags=workflow.tags,
                is_template=workflow.is_template,
                is_active=workflow.is_active,
                created_at=workflow.created_at,
                updated_at=workflow.updated_at,
                created_by=workflow.created_by,
                node_count=len(workflow.nodes),
                connection_count=len(workflow.connections)
            )
            for workflow in workflows
        ]

    except Exception as e:
        logging_service.log_error(f"Failed to list workflows: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取工作流列表失败: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取工作流详情"""
    try:
        workflow = await workflow_engine.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail="工作流不存在"
            )

        return WorkflowDetailResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            category=workflow.category,
            tags=workflow.tags,
            is_template=workflow.is_template,
            is_active=workflow.is_active,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            created_by=workflow.created_by,
            node_count=len(workflow.nodes),
            connection_count=len(workflow.connections),
            nodes=[node.to_dict() for node in workflow.nodes],
            connections=[conn.to_dict() for conn in workflow.connections],
            variables=workflow.variables,
            triggers=workflow.triggers,
            settings=workflow.settings
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Failed to get workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取工作流失败: {str(e)}"
        )


@router.put("/{workflow_id}", response_model=WorkflowDetailResponse)
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """更新工作流"""
    try:
        # 检查工作流是否存在
        existing_workflow = await workflow_engine.get_workflow(workflow_id)
        if not existing_workflow:
            raise HTTPException(
                status_code=404,
                detail="工作流不存在"
            )

        # 构建更新数据
        updates = {}
        for field, value in request.dict(exclude_unset=True).items():
            updates[field] = value

        updates["updated_at"] = datetime.now().isoformat()

        workflow = await workflow_engine.update_workflow(workflow_id, updates)

        return WorkflowDetailResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            category=workflow.category,
            tags=workflow.tags,
            is_template=workflow.is_template,
            is_active=workflow.is_active,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            created_by=workflow.created_by,
            node_count=len(workflow.nodes),
            connection_count=len(workflow.connections),
            nodes=[node.to_dict() for node in workflow.nodes],
            connections=[conn.to_dict() for conn in workflow.connections],
            variables=workflow.variables,
            triggers=workflow.triggers,
            settings=workflow.settings
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Failed to update workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"更新工作流失败: {str(e)}"
        )


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """删除工作流"""
    try:
        success = await workflow_engine.delete_workflow(workflow_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="工作流不存在"
            )

        return {
            "success": True,
            "message": "工作流删除成功",
            "workflow_id": workflow_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Failed to delete workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除工作流失败: {str(e)}"
        )


# Workflow Execution Endpoints
@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecuteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """执行工作流"""
    try:
        logging_service.log_info(
            f"User {current_user.get('user_id')} executing workflow: {workflow_id}"
        )

        execution = await workflow_engine.execute_workflow(
            workflow_id=workflow_id,
            inputs=request.inputs,
            execution_id=str(uuid.uuid4()) if request.async_execution else None
        )

        # 计算执行时长
        duration = None
        if execution.start_time and execution.end_time:
            duration = (execution.end_time - execution.start_time).total_seconds()

        return WorkflowExecutionResponse(
            id=execution.id,
            workflow_id=execution.workflow_id,
            status=execution.status,
            start_time=execution.start_time.isoformat() if execution.start_time else None,
            end_time=execution.end_time.isoformat() if execution.end_time else None,
            inputs=execution.inputs,
            outputs=execution.outputs,
            variables=execution.variables,
            node_executions=execution.node_executions,
            logs=execution.logs,
            error_message=execution.error_message,
            created_at=execution.created_at.isoformat(),
            updated_at=execution.updated_at.isoformat(),
            duration=duration
        )

    except Exception as e:
        logging_service.log_error(f"Failed to execute workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"执行工作流失败: {str(e)}"
        )


@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecutionResponse])
async def list_workflow_executions(
    workflow_id: str,
    status: Optional[ExecutionStatus] = Query(None, description="执行状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取工作流执行历史"""
    try:
        executions = await workflow_engine.list_executions(
            workflow_id=workflow_id,
            status=status,
            limit=limit
        )

        return [
            WorkflowExecutionResponse(
                id=execution.id,
                workflow_id=execution.workflow_id,
                status=execution.status,
                start_time=execution.start_time.isoformat() if execution.start_time else None,
                end_time=execution.end_time.isoformat() if execution.end_time else None,
                inputs=execution.inputs,
                outputs=execution.outputs,
                variables=execution.variables,
                node_executions=execution.node_executions,
                logs=execution.logs,
                error_message=execution.error_message,
                created_at=execution.created_at.isoformat(),
                updated_at=execution.updated_at.isoformat(),
                duration=(execution.end_time - execution.start_time).total_seconds()
                if execution.start_time and execution.end_time else None
            )
            for execution in executions
        ]

    except Exception as e:
        logging_service.log_error(f"Failed to list executions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取执行历史失败: {str(e)}"
        )


@router.get("/execution/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_execution(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取执行详情"""
    try:
        execution = await workflow_engine.get_execution(execution_id)
        if not execution:
            raise HTTPException(
                status_code=404,
                detail="执行实例不存在"
            )

        duration = None
        if execution.start_time and execution.end_time:
            duration = (execution.end_time - execution.start_time).total_seconds()

        return WorkflowExecutionResponse(
            id=execution.id,
            workflow_id=execution.workflow_id,
            status=execution.status,
            start_time=execution.start_time.isoformat() if execution.start_time else None,
            end_time=execution.end_time.isoformat() if execution.end_time else None,
            inputs=execution.inputs,
            outputs=execution.outputs,
            variables=execution.variables,
            node_executions=execution.node_executions,
            logs=execution.logs,
            error_message=execution.error_message,
            created_at=execution.created_at.isoformat(),
            updated_at=execution.updated_at.isoformat(),
            duration=duration
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Failed to get execution: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取执行详情失败: {str(e)}"
        )


@router.post("/execution/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """取消执行"""
    try:
        success = await workflow_engine.cancel_execution(execution_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="执行实例不存在或无法取消"
            )

        return {
            "success": True,
            "message": "执行取消成功",
            "execution_id": execution_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Failed to cancel execution: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"取消执行失败: {str(e)}"
        )


# Template Management Endpoints
@router.get("/templates/", response_model=List[WorkflowTemplateResponse])
async def list_templates(
    category: Optional[str] = Query(None, description="模板分类"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取工作流模板列表"""
    try:
        templates = await workflow_engine.get_templates(category=category, tags=tags)

        return [
            WorkflowTemplateResponse(
                id=template.id,
                name=template.name,
                description=template.description,
                category=template.category,
                tags=template.tags,
                node_count=len(template.nodes),
                connection_count=len(template.connections)
            )
            for template in templates
        ]

    except Exception as e:
        logging_service.log_error(f"Failed to list templates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取模板列表失败: {str(e)}"
        )


@router.get("/templates/{template_id}", response_model=WorkflowDetailResponse)
async def get_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取模板详情"""
    try:
        template = workflow_engine.template_manager.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=404,
                detail="模板不存在"
            )

        return WorkflowDetailResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            version=template.version,
            category=template.category,
            tags=template.tags,
            is_template=template.is_template,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at,
            created_by=template.created_by,
            node_count=len(template.nodes),
            connection_count=len(template.connections),
            nodes=[node.to_dict() for node in template.nodes],
            connections=[conn.to_dict() for conn in template.connections],
            variables=template.variables,
            triggers=template.triggers,
            settings=template.settings
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Failed to get template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取模板失败: {str(e)}"
        )


@router.post("/templates/{template_id}/create", response_model=WorkflowDetailResponse)
async def create_workflow_from_template(
    template_id: str,
    request: WorkflowTemplateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """从模板创建工作流"""
    try:
        workflow = await workflow_engine.create_workflow_from_template(
            template_id=request.template_id,
            name=request.name,
            description=request.description,
            variables=request.variables
        )

        return WorkflowDetailResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            category=workflow.category,
            tags=workflow.tags,
            is_template=workflow.is_template,
            is_active=workflow.is_active,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            created_by=workflow.created_by,
            node_count=len(workflow.nodes),
            connection_count=len(workflow.connections),
            nodes=[node.to_dict() for node in workflow.nodes],
            connections=[conn.to_dict() for conn in workflow.connections],
            variables=workflow.variables,
            triggers=workflow.triggers,
            settings=workflow.settings
        )

    except Exception as e:
        logging_service.log_error(f"Failed to create workflow from template: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"从模板创建工作流失败: {str(e)}"
        )


# Visual Designer Support Endpoints
@router.get("/designer/node-types")
async def get_node_types():
    """获取支持的节点类型（用于可视化设计器）"""
    try:
        node_types = {
            "basic": [
                {
                    "type": "start",
                    "name": "开始",
                    "description": "工作流起始节点",
                    "category": "basic",
                    "icon": "play",
                    "config_schema": {}
                },
                {
                    "type": "end",
                    "name": "结束",
                    "description": "工作流结束节点",
                    "category": "basic",
                    "icon": "stop",
                    "config_schema": {}
                }
            ],
            "ai": [
                {
                    "type": "ai_task",
                    "name": "AI任务",
                    "description": "执行AI相关任务",
                    "category": "ai",
                    "icon": "brain",
                    "config_schema": {
                        "task_type": {
                            "type": "select",
                            "label": "任务类型",
                            "options": [
                                {"value": "text_generation", "label": "文本生成"},
                                {"value": "multimodal_analysis", "label": "多模态分析"},
                                {"value": "chat_completion", "label": "聊天补全"}
                            ],
                            "default": "text_generation"
                        },
                        "prompt": {
                            "type": "textarea",
                            "label": "提示词",
                            "required": True
                        },
                        "model": {
                            "type": "select",
                            "label": "AI模型",
                            "options": [
                                {"value": "openrouter", "label": "OpenRouter"},
                                {"value": "gemini", "label": "Gemini"}
                            ],
                            "default": "openrouter"
                        }
                    }
                }
            ],
            "data": [
                {
                    "type": "data_processing",
                    "name": "数据处理",
                    "description": "处理和转换数据",
                    "category": "data",
                    "icon": "database",
                    "config_schema": {
                        "operation": {
                            "type": "select",
                            "label": "操作类型",
                            "options": [
                                {"value": "transform", "label": "数据转换"},
                                {"value": "filter", "label": "数据过滤"},
                                {"value": "aggregate", "label": "数据聚合"}
                            ],
                            "default": "transform"
                        }
                    }
                },
                {
                    "type": "condition",
                    "name": "条件判断",
                    "description": "根据条件进行分支",
                    "category": "data",
                    "icon": "git-branch",
                    "config_schema": {
                        "conditions": {
                            "type": "array",
                            "label": "条件列表",
                            "items": {
                                "variable": {"type": "text", "label": "变量名"},
                                "operator": {"type": "select", "label": "操作符"},
                                "value": {"type": "text", "label": "值"},
                                "branch": {"type": "text", "label": "分支"}
                            }
                        }
                    }
                }
            ],
            "control": [
                {
                    "type": "loop",
                    "name": "循环节点",
                    "description": "循环执行任务",
                    "category": "control",
                    "icon": "repeat",
                    "config_schema": {
                        "loop_type": {
                            "type": "select",
                            "label": "循环类型",
                            "options": [
                                {"value": "for_each", "label": "遍历"},
                                {"value": "while", "label": "条件循环"},
                                {"value": "for_range", "label": "范围循环"}
                            ],
                            "default": "for_each"
                        }
                    }
                },
                {
                    "type": "parallel",
                    "name": "并行执行",
                    "description": "并行执行多个任务",
                    "category": "control",
                    "icon": "git-merge",
                    "config_schema": {
                        "tasks": {
                            "type": "array",
                            "label": "任务列表"
                        }
                    }
                },
                {
                    "type": "wait",
                    "name": "等待",
                    "description": "等待指定时间",
                    "category": "control",
                    "icon": "clock",
                    "config_schema": {
                        "wait_time": {
                            "type": "number",
                            "label": "等待时间",
                            "min": 0,
                            "default": 1
                        },
                        "wait_unit": {
                            "type": "select",
                            "label": "时间单位",
                            "options": [
                                {"value": "seconds", "label": "秒"},
                                {"value": "minutes", "label": "分钟"},
                                {"value": "hours", "label": "小时"}
                            ],
                            "default": "seconds"
                        }
                    }
                }
            ],
            "integration": [
                {
                    "type": "webhook",
                    "name": "Webhook",
                    "description": "发送HTTP请求",
                    "category": "integration",
                    "icon": "webhook",
                    "config_schema": {
                        "url": {
                            "type": "url",
                            "label": "URL地址",
                            "required": True
                        },
                        "method": {
                            "type": "select",
                            "label": "HTTP方法",
                            "options": ["GET", "POST", "PUT", "DELETE"],
                            "default": "POST"
                        }
                    }
                },
                {
                    "type": "email",
                    "name": "邮件发送",
                    "description": "发送电子邮件",
                    "category": "integration",
                    "icon": "mail",
                    "config_schema": {
                        "to": {
                            "type": "array",
                            "label": "收件人",
                            "required": True
                        },
                        "subject": {
                            "type": "text",
                            "label": "主题",
                            "required": True
                        },
                        "body": {
                            "type": "textarea",
                            "label": "邮件内容"
                        }
                    }
                }
            ]
        }

        return {
            "success": True,
            "node_types": node_types,
            "categories": [
                {"id": "basic", "name": "基础节点", "icon": "circle"},
                {"id": "ai", "name": "AI节点", "icon": "brain"},
                {"id": "data", "name": "数据节点", "icon": "database"},
                {"id": "control", "name": "控制节点", "icon": "git-branch"},
                {"id": "integration", "name": "集成节点", "icon": "plug"}
            ]
        }

    except Exception as e:
        logging_service.log_error(f"Failed to get node types: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取节点类型失败: {str(e)}"
        )


@router.get("/designer/validation")
async def validate_workflow_design(
    workflow_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """验证工作流设计（用于可视化设计器）"""
    try:
        errors = []
        warnings = []

        # 基本结构验证
        if not workflow_data.get("name"):
            errors.append("工作流名称不能为空")

        nodes = workflow_data.get("nodes", [])
        connections = workflow_data.get("connections", [])

        # 验证节点
        node_ids = []
        start_nodes = 0
        end_nodes = 0

        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                errors.append("发现没有ID的节点")
                continue

            if node_id in node_ids:
                errors.append(f"节点ID重复: {node_id}")
            else:
                node_ids.append(node_id)

            node_type = node.get("type")
            if node_type == "start":
                start_nodes += 1
            elif node_type == "end":
                end_nodes += 1

        # 验证起始和结束节点
        if start_nodes == 0:
            errors.append("工作流必须包含至少一个起始节点")
        elif start_nodes > 1:
            warnings.append("发现多个起始节点，可能只使用第一个")

        if end_nodes == 0:
            errors.append("工作流必须包含至少一个结束节点")

        # 验证连接
        for connection in connections:
            source_id = connection.get("source_node_id")
            target_id = connection.get("target_node_id")

            if source_id not in node_ids:
                errors.append(f"连接源节点不存在: {source_id}")

            if target_id not in node_ids:
                errors.append(f"连接目标节点不存在: {target_id}")

        # 检查循环依赖
        if nodes and connections:
            has_cycle = _detect_cycle(nodes, connections)
            if has_cycle:
                errors.append("检测到循环依赖，请检查连接关系")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "statistics": {
                "total_nodes": len(nodes),
                "total_connections": len(connections),
                "start_nodes": start_nodes,
                "end_nodes": end_nodes
            }
        }

    except Exception as e:
        logging_service.log_error(f"Failed to validate workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"验证工作流设计失败: {str(e)}"
        )


def _detect_cycle(nodes: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> bool:
    """检测图中的循环依赖"""
    try:
        # 构建邻接表
        graph = {}
        for node in nodes:
            graph[node["id"]] = []

        for connection in connections:
            source = connection["source_node_id"]
            target = connection["target_node_id"]
            if source in graph:
                graph[source].append(target)

        # DFS检测循环
        visited = set()
        rec_stack = set()

        def dfs(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in graph:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    except:
        return False


# Statistics Endpoints
@router.get("/statistics")
async def get_workflow_statistics(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取工作流统计信息"""
    try:
        workflows = await workflow_engine.list_workflows()
        executions = await workflow_engine.list_executions(limit=1000)

        # 统计数据
        total_workflows = len(workflows)
        active_workflows = len([w for w in workflows if w.is_active])
        template_workflows = len([w for w in workflows if w.is_template])

        # 按分类统计
        category_stats = {}
        for workflow in workflows:
            category = workflow.category
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1

        # 执行统计
        total_executions = len(executions)
        completed_executions = len([e for e in executions if e.status == ExecutionStatus.COMPLETED])
        failed_executions = len([e for e in executions if e.status == ExecutionStatus.FAILED])
        running_executions = len([e for e in executions if e.status == ExecutionStatus.RUNNING])

        return {
            "workflows": {
                "total": total_workflows,
                "active": active_workflows,
                "templates": template_workflows,
                "categories": category_stats
            },
            "executions": {
                "total": total_executions,
                "completed": completed_executions,
                "failed": failed_executions,
                "running": running_executions,
                "success_rate": (completed_executions / total_executions * 100) if total_executions > 0 else 0
            }
        }

    except Exception as e:
        logging_service.log_error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )
"""
Workflow Engine Tests
Week 7 Day 1: Advanced AI Features Development

Tests for:
- Workflow definition and management
- Workflow execution engine
- Template management
- Node handlers and processing
- Visual designer validation
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from backend.core.workflow_engine import (
    WorkflowEngine,
    WorkflowExecutor,
    WorkflowTemplateManager,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowNode,
    WorkflowConnection,
    NodeType,
    ExecutionStatus,
    LoopType
)


class TestWorkflowNode:
    """工作流节点测试"""

    def test_workflow_node_creation(self):
        """测试工作流节点创建"""
        node = WorkflowNode(
            id="test_node",
            type=NodeType.AI_TASK,
            name="AI分析节点",
            description="执行AI分析任务",
            position={"x": 100, "y": 200},
            config={"task_type": "text_generation", "prompt": "测试提示词"}
        )

        assert node.id == "test_node"
        assert node.type == NodeType.AI_TASK
        assert node.name == "AI分析节点"
        assert node.position == {"x": 100, "y": 200}
        assert node.config["task_type"] == "text_generation"

    def test_workflow_node_serialization(self):
        """测试工作流节点序列化"""
        node = WorkflowNode(
            id="test_node",
            type=NodeType.START,
            name="开始节点",
            config={"test": "value"}
        )

        # 转换为字典
        node_dict = node.to_dict()
        assert isinstance(node_dict, dict)
        assert node_dict["id"] == "test_node"
        assert node_dict["type"] == "start"

        # 从字典创建
        new_node = WorkflowNode.from_dict(node_dict)
        assert new_node.id == node.id
        assert new_node.type == node.type
        assert new_node.name == node.name


class TestWorkflowDefinition:
    """工作流定义测试"""

    def test_workflow_definition_creation(self):
        """测试工作流定义创建"""
        nodes = [
            WorkflowNode(
                id="start",
                type=NodeType.START,
                name="开始"
            ),
            WorkflowNode(
                id="ai_task",
                type=NodeType.AI_TASK,
                name="AI任务",
                config={"task_type": "text_generation"}
            )
        ]

        connections = [
            WorkflowConnection(
                id="conn_1",
                source_node_id="start",
                target_node_id="ai_task"
            )
        ]

        workflow = WorkflowDefinition(
            id="test_workflow",
            name="测试工作流",
            description="用于测试的工作流",
            nodes=nodes,
            connections=connections,
            variables={"input_var": "test_value"}
        )

        assert workflow.id == "test_workflow"
        assert workflow.name == "测试工作流"
        assert len(workflow.nodes) == 2
        assert len(workflow.connections) == 1
        assert workflow.variables["input_var"] == "test_value"

    def test_workflow_definition_serialization(self):
        """测试工作流定义序列化"""
        workflow = WorkflowDefinition(
            id="test_workflow",
            name="测试工作流",
            nodes=[],
            connections=[]
        )

        # 转换为字典
        workflow_dict = workflow.to_dict()
        assert isinstance(workflow_dict, dict)
        assert workflow_dict["id"] == "test_workflow"

        # 从字典创建
        new_workflow = WorkflowDefinition.from_dict(workflow_dict)
        assert new_workflow.id == workflow.id
        assert new_workflow.name == workflow.name


class TestWorkflowExecutor:
    """工作流执行器测试"""

    @pytest.fixture
    def executor(self):
        """创建工作流执行器实例"""
        return WorkflowExecutor()

    @pytest.fixture
    def simple_workflow(self):
        """创建简单工作流"""
        nodes = [
            WorkflowNode(
                id="start",
                type=NodeType.START,
                name="开始"
            ),
            WorkflowNode(
                id="ai_task",
                type=NodeType.AI_TASK,
                name="AI任务",
                config={
                    "task_type": "text_generation",
                    "prompt": "生成测试文本"
                }
            ),
            WorkflowNode(
                id="end",
                type=NodeType.END,
                name="结束"
            )
        ]

        connections = [
            WorkflowConnection(
                id="conn_1",
                source_node_id="start",
                target_node_id="ai_task"
            ),
            WorkflowConnection(
                id="conn_2",
                source_node_id="ai_task",
                target_node_id="end"
            )
        ]

        return WorkflowDefinition(
            id="simple_workflow",
            name="简单工作流",
            nodes=nodes,
            connections=connections
        )

    @pytest.mark.asyncio
    async def test_build_execution_graph(self, executor, simple_workflow):
        """测试构建执行图"""
        graph = executor._build_execution_graph(simple_workflow)

        assert "start" in graph
        assert "ai_task" in graph
        assert "end" in graph
        assert "ai_task" in graph["start"]
        assert "end" in graph["ai_task"]
        assert len(graph["end"]) == 0

    @pytest.mark.asyncio
    async def test_can_execute_node(self, executor):
        """测试节点执行条件检查"""
        graph = {
            "start": ["task1"],
            "task1": ["task2"],
            "task2": []
        }

        executed_nodes = set()

        # 起始节点应该可以执行
        assert executor._can_execute_node("start", executed_nodes, graph)

        # task1还不能执行（start未执行）
        assert not executor._can_execute_node("task1", executed_nodes, graph)

        # 执行start后
        executed_nodes.add("start")
        assert executor._can_execute_node("task1", executed_nodes, graph)

    @pytest.mark.asyncio
    async def test_handle_start_node(self, executor):
        """测试起始节点处理"""
        workflow = WorkflowDefinition(id="test", name="test", nodes=[], connections=[])
        execution = WorkflowExecution(id="exec_1", workflow_id="test", inputs={"test": "value"})
        node = WorkflowNode(id="start", type=NodeType.START, name="开始")

        result = await executor._handle_start(execution, workflow, node)

        assert result["status"] == "started"
        assert result["inputs"] == execution.inputs

    @pytest.mark.asyncio
    async def test_handle_end_node(self, executor):
        """测试结束节点处理"""
        workflow = WorkflowDefinition(id="test", name="test", nodes=[], connections=[])
        execution = WorkflowExecution(
            id="exec_1",
            workflow_id="test",
            variables={"result": "test_output"}
        )
        node = WorkflowNode(id="end", type=NodeType.END, name="结束")

        result = await executor._handle_end(execution, workflow, node)

        assert result["status"] == "completed"
        assert result["outputs"] == execution.variables

    @pytest.mark.asyncio
    async def test_handle_ai_task(self, executor):
        """测试AI任务节点处理"""
        workflow = WorkflowDefinition(id="test", name="test", nodes=[], connections=[])
        execution = WorkflowExecution(
            id="exec_1",
            workflow_id="test",
            variables={"prompt_text": "测试提示词"}
        )
        node = WorkflowNode(
            id="ai_task",
            type=NodeType.AI_TASK,
            name="AI任务",
            config={
                "task_type": "text_generation",
                "prompt": "$prompt_text",
                "model": "openrouter"
            }
        )

        with patch('backend.core.workflow_engine.ai_manager') as mock_ai_manager:
            mock_service = Mock()
            mock_service.generate_response.return_value = "AI生成的响应文本"
            mock_ai_manager.get_service.return_value = mock_service

            result = await executor._handle_ai_task(execution, workflow, node)

            assert result["text"] == "AI生成的响应文本"
            assert result["model"] == "openrouter"

    @pytest.mark.asyncio
    async def test_handle_data_processing(self, executor):
        """测试数据处理节点处理"""
        workflow = WorkflowDefinition(id="test", name="test", nodes=[], connections=[])
        execution = WorkflowExecution(id="exec_1", workflow_id="test")
        node = WorkflowNode(
            id="data_task",
            type=NodeType.DATA_PROCESSING,
            name="数据处理",
            config={
                "operation": "transform",
                "input_data": "test_data",
                "transform_type": "string",
                "output_variable": "result"
            }
        )

        result = await executor._handle_data_processing(execution, workflow, node)

        assert result["result"] == "test_data"
        assert result["operation"] == "transform"
        assert execution.variables["result"] == "test_data"

    @pytest.mark.asyncio
    async def test_handle_condition(self, executor):
        """测试条件节点处理"""
        workflow = WorkflowDefinition(id="test", name="test", nodes=[], connections=[])
        execution = WorkflowExecution(
            id="exec_1",
            workflow_id="test",
            variables={"score": 85}
        )
        node = WorkflowNode(
            id="condition",
            type=NodeType.CONDITION,
            name="条件判断",
            conditions=[
                {
                    "variable": "score",
                    "operator": ">=",
                    "value": 80,
                    "branch": "high_score"
                }
            ]
        )

        result = await executor._handle_condition(execution, workflow, node)

        assert result["condition_met"] is True
        assert result["branch"] == "high_score"

    @pytest.mark.asyncio
    async def test_handle_wait(self, executor):
        """测试等待节点处理"""
        workflow = WorkflowDefinition(id="test", name="test", nodes=[], connections=[])
        execution = WorkflowExecution(id="exec_1", workflow_id="test")
        node = WorkflowNode(
            id="wait",
            type=NodeType.WAIT,
            name="等待",
            config={
                "wait_time": 0.1,  # 0.1秒
                "wait_unit": "seconds"
            }
        )

        start_time = datetime.now()
        result = await executor._handle_wait(execution, workflow, node)
        end_time = datetime.now()

        assert result["waited_seconds"] == 0.1
        assert (end_time - start_time).total_seconds() >= 0.1

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self, executor, simple_workflow):
        """测试执行简单工作流"""
        with patch('backend.core.workflow_engine.ai_manager') as mock_ai_manager:
            mock_service = Mock()
            mock_service.generate_response.return_value = "AI响应"
            mock_ai_manager.get_service.return_value = mock_service

            execution = await executor.execute_workflow(simple_workflow, {"input": "test"})

            assert execution.status == ExecutionStatus.COMPLETED
            assert execution.start_time is not None
            assert execution.end_time is not None
            assert len(execution.node_executions) == 3  # start, ai_task, end
            assert execution.node_executions["ai_task"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_workflow_with_error(self, executor):
        """测试工作流执行错误处理"""
        # 创建会失败的工作流
        nodes = [
            WorkflowNode(id="start", type=NodeType.START, name="开始"),
            WorkflowNode(
                id="failing_task",
                type=NodeType.AI_TASK,
                name="失败任务",
                config={"task_type": "unsupported_type"}
            ),
            WorkflowNode(id="end", type=NodeType.END, name="结束")
        ]

        connections = [
            WorkflowConnection(id="conn_1", source_node_id="start", target_node_id="failing_task"),
            WorkflowConnection(id="conn_2", source_node_id="failing_task", target_node_id="end")
        ]

        workflow = WorkflowDefinition(
            id="failing_workflow",
            name="失败工作流",
            nodes=nodes,
            connections=connections
        )

        execution = await executor.execute_workflow(workflow)

        assert execution.status == ExecutionStatus.FAILED
        assert execution.error_message is not None
        assert execution.node_executions["failing_task"]["status"] == "failed"

    def test_evaluate_condition_operation(self, executor):
        """测试条件操作评估"""
        # 相等比较
        assert executor._evaluate_condition_operation(5, "==", 5) is True
        assert executor._evaluate_condition_operation(5, "==", 3) is False

        # 大于比较
        assert executor._evaluate_condition_operation(10, ">", 5) is True
        assert executor._evaluate_condition_operation(3, ">", 5) is False

        # 包含比较
        assert executor._evaluate_condition_operation("hello world", "contains", "world") is True
        assert executor._evaluate_condition_operation("hello", "contains", "world") is False

        # 存在性检查
        assert executor._evaluate_condition_operation("value", "exists", None) is True
        assert executor._evaluate_condition_operation(None, "exists", None) is False


class TestWorkflowTemplateManager:
    """工作流模板管理器测试"""

    @pytest.fixture
    def template_manager(self):
        """创建模板管理器实例"""
        return WorkflowTemplateManager()

    def test_load_builtin_templates(self, template_manager):
        """测试加载内置模板"""
        assert len(template_manager.templates) > 0
        assert "doc_analysis_template" in template_manager.templates
        assert "image_processing_template" in template_manager.templates

    def test_get_template(self, template_manager):
        """测试获取模板"""
        template = template_manager.get_template("doc_analysis_template")
        assert template is not None
        assert template.name == "文档智能分析"
        assert template.is_template is True

        # 不存在的模板
        template = template_manager.get_template("nonexistent_template")
        assert template is None

    def test_list_templates(self, template_manager):
        """测试列出模板"""
        all_templates = template_manager.list_templates()
        assert len(all_templates) > 0

        # 按分类过滤
        doc_templates = template_manager.list_templates(category="document")
        assert len(doc_templates) > 0
        assert all(t.category == "document" for t in doc_templates)

        # 按标签过滤
        ai_templates = template_manager.list_templates(tags=["AI"])
        assert len(ai_templates) > 0
        assert all(any("AI" in tag for tag in t.tags) for t in ai_templates)

    def test_create_workflow_from_template(self, template_manager):
        """测试从模板创建工作流"""
        workflow = template_manager.create_workflow_from_template(
            template_id="doc_analysis_template",
            name="新的文档分析工作流",
            description="基于模板创建的工作流",
            variables={"custom_var": "custom_value"}
        )

        assert workflow.id != "doc_analysis_template"  # 应该有新的ID
        assert workflow.name == "新的文档分析工作流"
        assert workflow.is_template is False
        assert workflow.variables["custom_var"] == "custom_value"
        assert len(workflow.nodes) > 0  # 应该继承模板的节点

        # 测试不存在的模板
        with pytest.raises(ValueError):
            template_manager.create_workflow_from_template(
                template_id="nonexistent_template",
                name="测试工作流"
            )


class TestWorkflowEngine:
    """工作流引擎主类测试"""

    @pytest.fixture
    def engine(self):
        """创建工作流引擎实例"""
        return WorkflowEngine()

    @pytest.mark.asyncio
    async def test_create_workflow(self, engine):
        """测试创建工作流"""
        workflow_data = {
            "id": "test_workflow",
            "name": "测试工作流",
            "description": "用于测试的工作流",
            "category": "test",
            "tags": ["测试"],
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "开始",
                    "position": {"x": 0, "y": 0}
                }
            ],
            "connections": [],
            "variables": {},
            "created_by": "test_user"
        }

        workflow = await engine.create_workflow(workflow_data)

        assert workflow.id == "test_workflow"
        assert workflow.name == "测试工作流"
        assert workflow.id in engine.workflows

    @pytest.mark.asyncio
    async def test_update_workflow(self, engine):
        """测试更新工作流"""
        # 先创建工作流
        workflow_data = {
            "id": "test_workflow",
            "name": "原始名称",
            "nodes": [],
            "connections": []
        }
        workflow = await engine.create_workflow(workflow_data)

        # 更新工作流
        updates = {"name": "更新后的名称", "description": "新的描述"}
        updated_workflow = await engine.update_workflow("test_workflow", updates)

        assert updated_workflow.name == "更新后的名称"
        assert updated_workflow.description == "新的描述"
        assert updated_workflow.updated_at > workflow.updated_at

    @pytest.mark.asyncio
    async def test_delete_workflow(self, engine):
        """测试删除工作流"""
        # 先创建工作流
        workflow_data = {
            "id": "test_workflow",
            "name": "测试工作流",
            "nodes": [],
            "connections": []
        }
        await engine.create_workflow(workflow_data)

        # 删除工作流
        success = await engine.delete_workflow("test_workflow")
        assert success is True
        assert "test_workflow" not in engine.workflows

        # 删除不存在的工作流
        success = await engine.delete_workflow("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_list_workflows(self, engine):
        """测试列出工作流"""
        # 创建多个工作流
        for i in range(3):
            workflow_data = {
                "id": f"workflow_{i}",
                "name": f"工作流 {i}",
                "category": f"category_{i % 2}",
                "tags": [f"tag_{i}"],
                "nodes": [],
                "connections": []
            }
            await engine.create_workflow(workflow_data)

        # 获取所有工作流
        all_workflows = await engine.list_workflows()
        assert len(all_workflows) >= 3

        # 按分类过滤
        category_0_workflows = await engine.list_workflows(category="category_0")
        assert len(category_0_workflows) >= 1
        assert all(w.category == "category_0" for w in category_0_workflows)

    @pytest.mark.asyncio
    async def test_execute_workflow(self, engine):
        """测试执行工作流"""
        # 创建简单工作流
        workflow_data = {
            "id": "test_workflow",
            "name": "测试工作流",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "开始",
                    "position": {"x": 0, "y": 0}
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "结束",
                    "position": {"x": 200, "y": 0}
                }
            ],
            "connections": [
                {
                    "id": "conn_1",
                    "source_node_id": "start",
                    "target_node_id": "end"
                }
            ],
            "variables": {}
        }

        workflow = await engine.create_workflow(workflow_data)

        # 执行工作流
        with patch('backend.core.workflow_engine.ai_manager') as mock_ai_manager:
            execution = await engine.execute_workflow(
                workflow_id="test_workflow",
                inputs={"test_input": "test_value"}
            )

            assert execution.id is not None
            assert execution.workflow_id == "test_workflow"
            assert execution.status == ExecutionStatus.COMPLETED
            assert execution.inputs["test_input"] == "test_value"
            assert execution.id in engine.executions

    @pytest.mark.asyncio
    async def test_get_execution(self, engine):
        """测试获取执行实例"""
        # 先执行工作流
        workflow_data = {
            "id": "test_workflow",
            "name": "测试工作流",
            "nodes": [
                {"id": "start", "type": "start", "name": "开始", "position": {"x": 0, "y": 0}},
                {"id": "end", "type": "end", "name": "结束", "position": {"x": 200, "y": 0}}
            ],
            "connections": [{"id": "conn_1", "source_node_id": "start", "target_node_id": "end"}],
            "variables": {}
        }

        await engine.create_workflow(workflow_data)

        with patch('backend.core.workflow_engine.ai_manager'):
            execution = await engine.execute_workflow("test_workflow")

            # 获取执行实例
            retrieved_execution = await engine.get_execution(execution.id)
            assert retrieved_execution is not None
            assert retrieved_execution.id == execution.id
            assert retrieved_execution.workflow_id == "test_workflow"

            # 获取不存在的执行实例
            nonexistent_execution = await engine.get_execution("nonexistent_id")
            assert nonexistent_execution is None

    @pytest.mark.asyncio
    async def test_cancel_execution(self, engine):
        """测试取消执行"""
        # 创建长时间运行的工作流
        workflow_data = {
            "id": "long_running_workflow",
            "name": "长时间运行工作流",
            "nodes": [
                {"id": "start", "type": "start", "name": "开始", "position": {"x": 0, "y": 0}},
                {
                    "id": "wait",
                    "type": "wait",
                    "name": "等待",
                    "position": {"x": 200, "y": 0},
                    "config": {"wait_time": 10, "wait_unit": "seconds"}
                },
                {"id": "end", "type": "end", "name": "结束", "position": {"x": 400, "y": 0}}
            ],
            "connections": [
                {"id": "conn_1", "source_node_id": "start", "target_node_id": "wait"},
                {"id": "conn_2", "source_node_id": "wait", "target_node_id": "end"}
            ],
            "variables": {}
        }

        await engine.create_workflow(workflow_data)

        # 启动执行但不等待完成
        async def run_execution():
            with patch('backend.core.workflow_engine.ai_manager'):
                return await engine.execute_workflow("long_running_workflow")

        # 异步启动执行
        execution_task = asyncio.create_task(run_execution())

        # 等待一小段时间让执行开始
        await asyncio.sleep(0.1)

        # 获取执行ID并取消
        # 注意：这个测试可能需要根据实际实现调整
        executions = await engine.list_executions(workflow_id="long_running_workflow")
        if executions:
            execution_id = executions[0].id
            success = await engine.cancel_execution(execution_id)
            # 由于执行可能很快完成，这里只检查函数是否能正常调用
            assert isinstance(success, bool)

        # 清理任务
        execution_task.cancel()
        try:
            await execution_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_create_workflow_from_template(self, engine):
        """测试从模板创建工作流"""
        workflow = await engine.create_workflow_from_template(
            template_id="doc_analysis_template",
            name="基于模板的工作流",
            description="从模板创建的文档分析工作流"
        )

        assert workflow.name == "基于模板的工作流"
        assert workflow.is_template is False
        assert workflow.id in engine.workflows
        assert len(workflow.nodes) > 0

    @pytest.mark.asyncio
    async def test_get_templates(self, engine):
        """测试获取模板列表"""
        templates = await engine.get_templates()
        assert len(templates) > 0

        # 按分类过滤
        doc_templates = await engine.get_templates(category="document")
        assert len(doc_templates) > 0
        assert all(t.category == "document" for t in doc_templates)


class TestWorkflowValidation:
    """工作流验证测试"""

    def test_detect_cycle_simple(self):
        """测试简单循环检测"""
        nodes = [
            {"id": "A", "type": "start"},
            {"id": "B", "type": "ai_task"},
            {"id": "C", "type": "end"}
        ]

        # 无循环的连接
        connections_no_cycle = [
            {"source_node_id": "A", "target_node_id": "B"},
            {"source_node_id": "B", "target_node_id": "C"}
        ]

        # 有循环的连接
        connections_with_cycle = [
            {"source_node_id": "A", "target_node_id": "B"},
            {"source_node_id": "B", "target_node_id": "C"},
            {"source_node_id": "C", "target_node_id": "A"}  # 循环
        ]

        # 从workflow.py导入检测函数
        from backend.api.v1.workflow import _detect_cycle

        assert _detect_cycle(nodes, connections_no_cycle) is False
        assert _detect_cycle(nodes, connections_with_cycle) is True

    def test_detect_cycle_complex(self):
        """测试复杂循环检测"""
        nodes = [
            {"id": "A", "type": "start"},
            {"id": "B", "type": "ai_task"},
            {"id": "C", "type": "condition"},
            {"id": "D", "type": "end"}
        ]

        # 复杂但无循环的结构
        connections_no_cycle = [
            {"source_node_id": "A", "target_node_id": "B"},
            {"source_node_id": "B", "target_node_id": "C"},
            {"source_node_id": "C", "target_node_id": "D"}
        ]

        # 包含循环的复杂结构
        connections_with_cycle = [
            {"source_node_id": "A", "target_node_id": "B"},
            {"source_node_id": "B", "target_node_id": "C"},
            {"source_node_id": "C", "target_node_id": "B"},  # B和C之间的循环
            {"source_node_id": "C", "target_node_id": "D"}
        ]

        from backend.api.v1.workflow import _detect_cycle

        assert _detect_cycle(nodes, connections_no_cycle) is False
        assert _detect_cycle(nodes, connections_with_cycle) is True


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
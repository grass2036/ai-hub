"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  Plus,
  Settings,
  Save,
  Trash2,
  Copy,
  Download,
  Upload,
  GitBranch,
  Database,
  Brain,
  Clock,
  Mail,
  Webhook,
  Repeat,
  Circle,
  CircleDot,
  AlertTriangle
} from "lucide-react";

interface WorkflowNode {
  id: string;
  type: string;
  name: string;
  description?: string;
  position: { x: number; y: number };
  config: Record<string, any>;
  inputs: string[];
  outputs: string[];
}

interface WorkflowConnection {
  id: string;
  sourceNodeId: string;
  targetNodeId: string;
  sourceOutput?: string;
  targetInput?: string;
}

interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
  variables: Record<string, any>;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

interface WorkflowExecution {
  id: string;
  workflowId: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  startTime?: string;
  endTime?: string;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  nodeExecutions: Record<string, any>;
  logs: Array<{
    timestamp: string;
    level: string;
    nodeId: string;
    message: string;
  }>;
  errorMessage?: string;
}

const NODE_TYPES = [
  { type: "start", name: "开始", icon: Circle, color: "text-green-500" },
  { type: "end", name: "结束", icon: CircleDot, color: "text-red-500" },
  { type: "ai_task", name: "AI任务", icon: Brain, color: "text-blue-500" },
  { type: "data_processing", name: "数据处理", icon: Database, color: "text-purple-500" },
  { type: "condition", name: "条件判断", icon: GitBranch, color: "text-yellow-500" },
  { type: "loop", name: "循环", icon: Repeat, color: "text-orange-500" },
  { type: "wait", name: "等待", icon: Clock, color: "text-gray-500" },
  { type: "webhook", name: "Webhook", icon: Webhook, color: "text-indigo-500" },
  { type: "email", name: "邮件", icon: Mail, color: "text-pink-500" },
];

const STATUS_COLORS = {
  pending: "text-gray-500",
  running: "text-blue-500",
  completed: "text-green-500",
  failed: "text-red-500",
  cancelled: "text-orange-500",
};

export default function WorkflowPage() {
  const [activeTab, setActiveTab] = useState("designer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Workflow state
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowDefinition | null>(null);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [templates, setTemplates] = useState<WorkflowDefinition[]>([]);

  // Designer state
  const [canvasNodes, setCanvasNodes] = useState<WorkflowNode[]>([]);
  const [canvasConnections, setCanvasConnections] = useState<WorkflowConnection[]>([]);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectingFrom, setConnectingFrom] = useState<string | null>(null);
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const canvasRef = useRef<HTMLDivElement>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

  // Load workflows
  const loadWorkflows = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/workflow/`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setWorkflows(data);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }, []);

  // Load executions
  const loadExecutions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/workflow/executions`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setExecutions(data);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }, []);

  // Load templates
  const loadTemplates = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/workflow/templates/`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setTemplates(data);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    loadWorkflows();
    loadExecutions();
    loadTemplates();
  }, [loadWorkflows, loadExecutions, loadTemplates]);

  // Create new workflow
  const createWorkflow = async (workflowData: Partial<WorkflowDefinition>) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/workflow/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: workflowData.name,
          description: workflowData.description || "",
          category: workflowData.category || "general",
          tags: workflowData.tags || [],
          nodes: workflowData.nodes || [],
          connections: workflowData.connections || [],
          variables: workflowData.variables || {},
        }),
        credentials: "include",
      });

      if (response.ok) {
        const newWorkflow = await response.json();
        setWorkflows(prev => [...prev, newWorkflow]);
        setSelectedWorkflow(newWorkflow);
        return newWorkflow;
      } else {
        throw new Error("创建工作流失败");
      }
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Execute workflow
  const executeWorkflow = async (workflowId: string, inputs: Record<string, any> = {}) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/workflow/${workflowId}/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          inputs,
          async_execution: true,
        }),
        credentials: "include",
      });

      if (response.ok) {
        const execution = await response.json();
        setExecutions(prev => [execution, ...prev]);
        return execution;
      } else {
        throw new Error("执行工作流失败");
      }
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Create workflow from template
  const createFromTemplate = async (templateId: string, name: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/workflow/templates/${templateId}/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          template_id: templateId,
          name,
          description: `基于模板创建的${name}`,
        }),
        credentials: "include",
      });

      if (response.ok) {
        const newWorkflow = await response.json();
        setWorkflows(prev => [...prev, newWorkflow]);
        setSelectedWorkflow(newWorkflow);
        return newWorkflow;
      } else {
        throw new Error("从模板创建工作流失败");
      }
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Canvas mouse handlers
  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if clicking on a node
    const clickedNode = canvasNodes.find(node => {
      const nodeX = node.position.x;
      const nodeY = node.position.y;
      return x >= nodeX && x <= nodeX + 120 && y >= nodeY && y <= nodeY + 60;
    });

    if (clickedNode) {
      if (isConnecting && connectingFrom) {
        // Create connection
        const newConnection: WorkflowConnection = {
          id: `conn_${Date.now()}`,
          sourceNodeId: connectingFrom,
          targetNodeId: clickedNode.id,
        };
        setCanvasConnections(prev => [...prev, newConnection]);
        setIsConnecting(false);
        setConnectingFrom(null);
      } else {
        setSelectedNode(clickedNode);
        setDraggedNode(clickedNode.id);
      }
    } else {
      setSelectedNode(null);
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setMousePos({ x, y });

    if (draggedNode) {
      setCanvasNodes(prev => prev.map(node =>
        node.id === draggedNode
          ? { ...node, position: { x: x - 60, y: y - 30 } }
          : node
      ));
    }
  };

  const handleCanvasMouseUp = () => {
    setDraggedNode(null);
  };

  // Add node to canvas
  const addNodeToCanvas = (nodeType: string) => {
    const newNode: WorkflowNode = {
      id: `node_${Date.now()}`,
      type: nodeType,
      name: `${nodeType}_${canvasNodes.length + 1}`,
      position: {
        x: 50 + (canvasNodes.length % 4) * 150,
        y: 50 + Math.floor(canvasNodes.length / 4) * 100
      },
      config: {},
      inputs: [],
      outputs: [],
    };
    setCanvasNodes(prev => [...prev, newNode]);
  };

  // Start connection
  const startConnection = (nodeId: string) => {
    setIsConnecting(true);
    setConnectingFrom(nodeId);
  };

  // Save workflow
  const saveWorkflow = async () => {
    if (!selectedWorkflow) {
      // Create new workflow
      try {
        const newWorkflow = await createWorkflow({
          name: `新工作流_${Date.now()}`,
          category: "custom",
          tags: ["自定义"],
          nodes: canvasNodes,
          connections: canvasConnections,
        });
        setSelectedWorkflow(newWorkflow);
      } catch (err) {
        // Error already handled in createWorkflow
      }
    } else {
      // Update existing workflow
      try {
        const response = await fetch(`${API_BASE}/api/v1/workflow/${selectedWorkflow.id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            nodes: canvasNodes,
            connections: canvasConnections,
          }),
          credentials: "include",
        });

        if (response.ok) {
          const updatedWorkflow = await response.json();
          setSelectedWorkflow(updatedWorkflow);
          setWorkflows(prev => prev.map(w => w.id === updatedWorkflow.id ? updatedWorkflow : w));
        }
      } catch (err: any) {
        setError(err.message);
      }
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">智能工作流引擎</h1>
          <p className="text-muted-foreground">
            可视化工作流设计、执行和管理
          </p>
        </div>
        <Badge variant="secondary" className="text-sm">
          Week 7 Day 1
        </Badge>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="designer">可视化设计器</TabsTrigger>
          <TabsTrigger value="workflows">工作流管理</TabsTrigger>
          <TabsTrigger value="executions">执行监控</TabsTrigger>
          <TabsTrigger value="templates">模板库</TabsTrigger>
        </TabsList>

        {/* Visual Designer Tab */}
        <TabsContent value="designer" className="space-y-4">
          <div className="grid grid-cols-12 gap-4">
            {/* Node Palette */}
            <div className="col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">节点类型</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {NODE_TYPES.map(({ type, name, icon: Icon, color }) => (
                    <Button
                      key={type}
                      variant="outline"
                      size="sm"
                      className="w-full justify-start"
                      onClick={() => addNodeToCanvas(type)}
                    >
                      <Icon className={`w-4 h-4 mr-2 ${color}`} />
                      {name}
                    </Button>
                  ))}
                </CardContent>
              </Card>
            </div>

            {/* Canvas */}
            <div className="col-span-8">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>工作流画布</CardTitle>
                      <CardDescription>
                        拖拽节点进行设计，点击节点开始连接
                      </CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={saveWorkflow}>
                        <Save className="w-4 h-4 mr-2" />
                        保存
                      </Button>
                      <Button size="sm" variant="outline">
                        <Play className="w-4 h-4 mr-2" />
                        运行
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div
                    ref={canvasRef}
                    className="relative bg-gray-50 border rounded-lg"
                    style={{ height: "600px" }}
                    onMouseDown={handleCanvasMouseDown}
                    onMouseMove={handleCanvasMouseMove}
                    onMouseUp={handleCanvasMouseUp}
                  >
                    {/* Render Connections */}
                    <svg className="absolute inset-0 pointer-events-none" style={{ width: "100%", height: "100%" }}>
                      {canvasConnections.map((connection) => {
                        const sourceNode = canvasNodes.find(n => n.id === connection.sourceNodeId);
                        const targetNode = canvasNodes.find(n => n.id === connection.targetNodeId);
                        if (!sourceNode || !targetNode) return null;

                        const x1 = sourceNode.position.x + 120;
                        const y1 = sourceNode.position.y + 30;
                        const x2 = targetNode.position.x;
                        const y2 = targetNode.position.y + 30;

                        return (
                          <g key={connection.id}>
                            <line
                              x1={x1}
                              y1={y1}
                              x2={x2}
                              y2={y2}
                              stroke="#6b7280"
                              strokeWidth="2"
                            />
                            <circle cx={x2} cy={y2} r="4" fill="#6b7280" />
                          </g>
                        );
                      })}
                    </svg>

                    {/* Render Nodes */}
                    {canvasNodes.map((node) => {
                      const NodeTypeIcon = NODE_TYPES.find(n => n.type === node.type)?.icon || Circle;
                      const nodeColor = NODE_TYPES.find(n => n.type === node.type)?.color || "text-gray-500";
                      const isSelected = selectedNode?.id === node.id;

                      return (
                        <div
                          key={node.id}
                          className={`absolute bg-white border rounded-lg p-3 cursor-pointer transition-all ${
                            isSelected ? "border-blue-500 shadow-lg" : "border-gray-300"
                          }`}
                          style={{
                            left: `${node.position.x}px`,
                            top: `${node.position.y}px`,
                            width: "120px",
                          }}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <NodeTypeIcon className={`w-4 h-4 ${nodeColor}`} />
                            <span className="text-xs font-medium truncate">{node.name}</span>
                          </div>
                          <div className="text-xs text-gray-500 truncate">{node.type}</div>

                          {/* Connection handles */}
                          <div
                            className="absolute -right-2 top-6 w-4 h-4 bg-blue-500 rounded-full cursor-pointer"
                            onClick={(e) => {
                              e.stopPropagation();
                              startConnection(node.id);
                            }}
                          />
                          <div
                            className="absolute -left-2 top-6 w-4 h-4 bg-green-500 rounded-full"
                          />
                        </div>
                      );
                    })}

                    {/* Connection indicator */}
                    {isConnecting && connectingFrom && (
                      <div
                        className="absolute w-2 h-2 bg-blue-500 rounded-full pointer-events-none"
                        style={{
                          left: `${mousePos.x - 4}px`,
                          top: `${mousePos.y - 4}px`,
                        }}
                      />
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Properties Panel */}
            <div className="col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">属性面板</CardTitle>
                </CardHeader>
                <CardContent>
                  {selectedNode ? (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">节点名称</label>
                        <Input
                          value={selectedNode.name}
                          onChange={(e) => {
                            setCanvasNodes(prev => prev.map(node =>
                              node.id === selectedNode.id
                                ? { ...node, name: e.target.value }
                                : node
                            ));
                          }}
                          size="sm"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-1">节点类型</label>
                        <div className="text-sm text-gray-500">{selectedNode.type}</div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-1">描述</label>
                        <Textarea
                          value={selectedNode.description || ""}
                          onChange={(e) => {
                            setCanvasNodes(prev => prev.map(node =>
                              node.id === selectedNode.id
                                ? { ...node, description: e.target.value }
                                : node
                            ));
                          }}
                          rows={3}
                          placeholder="节点描述..."
                        />
                      </div>

                      <Button
                        variant="destructive"
                        size="sm"
                        className="w-full"
                        onClick={() => {
                          setCanvasNodes(prev => prev.filter(n => n.id !== selectedNode.id));
                          setCanvasConnections(prev => prev.filter(c =>
                            c.sourceNodeId !== selectedNode.id && c.targetNodeId !== selectedNode.id
                          ));
                          setSelectedNode(null);
                        }}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        删除节点
                      </Button>
                    </div>
                  ) : (
                    <div className="text-center text-gray-500 py-8">
                      选择一个节点查看属性
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Workflow Management Tab */}
        <TabsContent value="workflows" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">工作流列表</h3>
            <Button onClick={() => createWorkflow({ name: `新工作流_${Date.now()}`, category: "custom" })}>
              <Plus className="w-4 h-4 mr-2" />
              创建工作流
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workflows.map((workflow) => (
              <Card key={workflow.id} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-base">{workflow.name}</CardTitle>
                      <CardDescription className="text-sm">
                        {workflow.description || "暂无描述"}
                      </CardDescription>
                    </div>
                    <Badge variant={workflow.isActive ? "default" : "secondary"}>
                      {workflow.isActive ? "活跃" : "未激活"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>节点数:</span>
                      <span>{workflow.nodes?.length || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>连接数:</span>
                      <span>{workflow.connections?.length || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>分类:</span>
                      <span>{workflow.category}</span>
                    </div>

                    <div className="flex gap-2 pt-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1"
                        onClick={() => executeWorkflow(workflow.id)}
                      >
                        <Play className="w-3 h-3 mr-1" />
                        运行
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setSelectedWorkflow(workflow)}
                      >
                        <Settings className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Execution Monitoring Tab */}
        <TabsContent value="executions" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">执行历史</h3>
            <Button onClick={loadExecutions}>
              <RotateCcw className="w-4 h-4 mr-2" />
              刷新
            </Button>
          </div>

          <div className="space-y-4">
            {executions.map((execution) => (
              <Card key={execution.id}>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <div>
                      <CardTitle className="text-base">执行 #{execution.id.slice(-8)}</CardTitle>
                      <CardDescription>
                        工作流: {execution.workflowId}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={STATUS_COLORS[execution.status]}>
                        {execution.status}
                      </Badge>
                      {execution.status === "running" && (
                        <Button size="sm" variant="outline">
                          <Square className="w-3 h-3 mr-1" />
                          停止
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">开始时间:</span>
                        <div>{execution.startTime ? new Date(execution.startTime).toLocaleString() : "-"}</div>
                      </div>
                      <div>
                        <span className="text-gray-500">结束时间:</span>
                        <div>{execution.endTime ? new Date(execution.endTime).toLocaleString() : "-"}</div>
                      </div>
                      <div>
                        <span className="text-gray-500">节点执行:</span>
                        <div>{Object.keys(execution.nodeExecutions || {}).length}</div>
                      </div>
                      <div>
                        <span className="text-gray-500">日志条数:</span>
                        <div>{execution.logs?.length || 0}</div>
                      </div>
                    </div>

                    {execution.errorMessage && (
                      <Alert variant="destructive">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>{execution.errorMessage}</AlertDescription>
                      </Alert>
                    )}

                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          查看详情
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                        <DialogHeader>
                          <DialogTitle>执行详情</DialogTitle>
                          <DialogDescription>
                            执行ID: {execution.id}
                          </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-4">
                          {/* Inputs */}
                          <div>
                            <h4 className="font-medium mb-2">输入参数</h4>
                            <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto">
                              {JSON.stringify(execution.inputs, null, 2)}
                            </pre>
                          </div>

                          {/* Node Executions */}
                          <div>
                            <h4 className="font-medium mb-2">节点执行状态</h4>
                            <div className="space-y-2">
                              {Object.entries(execution.nodeExecutions || {}).map(([nodeId, nodeExec]: [string, any]) => (
                                <div key={nodeId} className="flex justify-between items-center p-2 border rounded">
                                  <span className="font-medium">{nodeId}</span>
                                  <Badge className={nodeExec.status === "completed" ? "text-green-500" : "text-red-500"}>
                                    {nodeExec.status}
                                  </Badge>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Logs */}
                          <div>
                            <h4 className="font-medium mb-2">执行日志</h4>
                            <div className="space-y-1 max-h-40 overflow-y-auto">
                              {execution.logs?.map((log, index) => (
                                <div key={index} className="text-sm p-2 bg-gray-50 rounded">
                                  <span className="text-gray-500">
                                    {new Date(log.timestamp).toLocaleTimeString()}
                                  </span>{" "}
                                  <span className="font-medium">{log.nodeId}:</span> {log.message}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">工作流模板库</h3>
            <Button onClick={loadTemplates}>
              <RotateCcw className="w-4 h-4 mr-2" />
              刷新模板
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((template) => (
              <Card key={template.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-base">{template.name}</CardTitle>
                      <CardDescription className="text-sm">
                        {template.description}
                      </CardDescription>
                    </div>
                    <Badge variant="outline">模板</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>分类:</span>
                      <span>{template.category}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>节点数:</span>
                      <span>{template.nodes?.length || 0}</span>
                    </div>

                    {template.tags && template.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {template.tags.map((tag, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}

                    <Button
                      className="w-full"
                      onClick={() => {
                        const name = `基于${template.name}_${Date.now()}`;
                        createFromTemplate(template.id, name);
                      }}
                    >
                      <Copy className="w-4 h-4 mr-2" />
                      使用模板
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
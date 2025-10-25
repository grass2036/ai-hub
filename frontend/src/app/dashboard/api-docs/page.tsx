"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import {
  Copy,
  Play,
  RotateCcw,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  Image,
  Mic,
  Settings,
  Database,
  Brain,
  Users,
  CreditCard,
  Shield,
  BarChart
} from "lucide-react";

interface ApiEndpoint {
  method: string;
  path: string;
  description: string;
  parameters: Array<{
    name: string;
    type: string;
    required: boolean;
    description: string;
  }>;
  requestBody?: any;
  responses: {
    [code: string]: {
      description: string;
      example?: any;
    };
  };
  category: string;
}

interface TestResult {
  endpoint: string;
  status: "success" | "error" | "pending";
  response?: any;
  error?: string;
  duration?: number;
  timestamp: string;
}

const API_ENDPOINTS: ApiEndpoint[] = [
  // Multi-Modal AI Endpoints
  {
    method: "POST",
    path: "/api/v1/multimodal/vision/analyze",
    description: "分析图像内容",
    category: "多模态AI",
    parameters: [
      {
        name: "image",
        type: "file",
        required: true,
        description: "要分析的图像文件"
      },
      {
        name: "analysis_type",
        type: "string",
        required: false,
        description: "分析类型: general, ocr, object_detection, classification, sentiment, content_moderation"
      },
      {
        name: "prompt",
        type: "string",
        required: false,
        description: "分析提示词"
      }
    ],
    responses: {
      "200": {
        description: "分析成功",
        example: {
          success: true,
          description: "这是一张蓝天白云的风景图片",
          tags: ["天空", "云", "蓝色"],
          confidence: 0.95,
          objects: [{"name": "天空", "confidence": 0.98}],
          processing_time: 2.34
        }
      }
    }
  },
  {
    method: "POST",
    path: "/api/v1/multimodal/speech/transcribe",
    description: "音频转文字",
    category: "多模态AI",
    parameters: [
      {
        name: "audio",
        type: "file",
        required: true,
        description: "要转录的音频文件"
      },
      {
        name: "task_type",
        type: "string",
        required: false,
        description: "任务类型: transcription, translation, dictation, command_recognition"
      },
      {
        name: "language",
        type: "string",
        required: false,
        description: "语言代码: auto, en, zh, ja, ko"
      }
    ],
    responses: {
      "200": {
        description: "转录成功",
        example: {
          success: true,
          text: "这是转录的音频内容",
          confidence: 0.92,
          language: "zh",
          duration: 15.5,
          processing_time: 3.21
        }
      }
    }
  },
  {
    method: "POST",
    path: "/api/v1/multimodal/speech/synthesize",
    description: "文字转语音",
    category: "多模态AI",
    parameters: [
      {
        name: "text",
        type: "string",
        required: true,
        description: "要转换为语音的文本"
      },
      {
        name: "voice",
        type: "string",
        required: false,
        description: "声音类型: alloy, echo, fable, onyx, nova, shimmer"
      },
      {
        name: "language",
        type: "string",
        required: false,
        description: "语言代码"
      }
    ],
    responses: {
      "200": {
        description: "语音合成成功",
        example: "返回音频文件流"
      }
    }
  },
  {
    method: "POST",
    path: "/api/v1/multimodal/document/analyze",
    description: "文档内容分析",
    category: "多模态AI",
    parameters: [
      {
        name: "document",
        type: "file",
        required: true,
        description: "要分析的文档文件"
      },
      {
        name: "query",
        type: "string",
        required: false,
        description: "分析查询"
      }
    ],
    responses: {
      "200": {
        description: "分析成功",
        example: {
          success: true,
          content: "文档内容...",
          summary: "文档摘要...",
          key_points: ["要点1", "要点2"],
          processing_time: 5.67
        }
      }
    }
  },
  {
    method: "POST",
    path: "/api/v1/multimodal/process",
    description: "多模态综合处理",
    category: "多模态AI",
    parameters: [
      {
        name: "image",
        type: "file",
        required: false,
        description: "图像文件"
      },
      {
        name: "audio",
        type: "file",
        required: false,
        description: "音频文件"
      },
      {
        name: "document",
        type: "file",
        required: false,
        description: "文档文件"
      },
      {
        name: "text",
        type: "string",
        required: false,
        description: "文本内容"
      }
    ],
    responses: {
      "200": {
        description: "处理成功",
        example: {
          success: true,
          task: "comprehensive_analysis",
          results: {
            vision: { description: "图像分析结果" },
            audio: { text: "音频转录结果" }
          },
          metadata: { modalities: ["image", "audio"] }
        }
      }
    }
  },

  // Workflow Engine Endpoints
  {
    method: "POST",
    path: "/api/v1/workflow/",
    description: "创建工作流",
    category: "工作流引擎",
    requestBody: {
      name: "string",
      description: "工作流描述",
      category: "string",
      nodes: [],
      connections: []
    },
    responses: {
      "201": {
        description: "工作流创建成功",
        example: {
          id: "workflow_123",
          name: "测试工作流",
          created_at: "2024-01-01T00:00:00Z"
        }
      }
    }
  },
  {
    method: "GET",
    path: "/api/v1/workflow/",
    description: "获取工作流列表",
    category: "工作流引擎",
    responses: {
      "200": {
        description: "获取成功",
        example: [
          {
            id: "workflow_123",
            name: "测试工作流",
            node_count: 5,
            connection_count: 4
          }
        ]
      }
    }
  },
  {
    method: "POST",
    path: "/api/v1/workflow/{id}/execute",
    description: "执行工作流",
    category: "工作流引擎",
    parameters: [
      {
        name: "id",
        type: "path",
        required: true,
        description: "工作流ID"
      }
    ],
    requestBody: {
      inputs: {},
      async_execution: true
    },
    responses: {
      "200": {
        description: "执行开始",
        example: {
          id: "execution_123",
          workflow_id: "workflow_123",
          status: "running"
        }
      }
    }
  },
  {
    method: "GET",
    path: "/api/v1/workflow/templates/",
    description: "获取工作流模板",
    category: "工作流引擎",
    responses: {
      "200": {
        description: "获取成功",
        example: [
          {
            id: "doc_analysis_template",
            name: "文档智能分析",
            category: "document",
            node_count: 4
          }
        ]
      }
    }
  },

  // System Endpoints
  {
    method: "GET",
    path: "/api/v1/multimodal/health",
    description: "多模态服务健康检查",
    category: "系统",
    responses: {
      "200": {
        description: "服务状态",
        example: {
          success: true,
          status: {
            vision: { status: "healthy", initialized: true },
            audio: { status: "healthy", initialized: true },
            document: { status: "healthy", initialized: true },
            overall: "healthy"
          }
        }
      }
    }
  },
  {
    method: "GET",
    path: "/api/v1/multimodal/capabilities",
    description: "获取服务能力信息",
    category: "系统",
    responses: {
      "200": {
        description: "能力信息",
        example: {
          success: true,
          capabilities: {
            vision: {
              supported_formats: [".jpg", ".png", ".gif"],
              analysis_types: ["general", "ocr", "object_detection"]
            }
          }
        }
      }
    }
  }
];

const CATEGORY_ICONS = {
  "多模态AI": Brain,
  "工作流引擎": Settings,
  "系统": Database,
};

export default function ApiDocsPage() {
  const [activeTab, setActiveTab] = useState("endpoints");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [testingEndpoint, setTestingEndpoint] = useState<string | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

  // Filter endpoints by category
  const filteredEndpoints = selectedCategory === "all"
    ? API_ENDPOINTS
    : API_ENDPOINTS.filter(endpoint => endpoint.category === selectedCategory);

  // Get unique categories
  const categories = ["all", ...Array.from(new Set(API_ENDPOINTS.map(e => e.category)))];

  // Test API endpoint
  const testEndpoint = async (endpoint: ApiEndpoint) => {
    setTestingEndpoint(endpoint.path);
    const startTime = Date.now();

    try {
      const response = await fetch(`${API_BASE}${endpoint.path}`, {
        method: endpoint.method,
        credentials: "include",
        // Add appropriate headers and body based on endpoint
      });

      const duration = Date.now() - startTime;
      let result: any;

      try {
        result = await response.json();
      } catch {
        result = await response.text();
      }

      const testResult: TestResult = {
        endpoint: endpoint.path,
        status: response.ok ? "success" : "error",
        response: result,
        duration,
        timestamp: new Date().toISOString(),
      };

      setTestResults(prev => [testResult, ...prev]);
    } catch (error: any) {
      const testResult: TestResult = {
        endpoint: endpoint.path,
        status: "error",
        error: error.message,
        duration: Date.now() - startTime,
        timestamp: new Date().toISOString(),
      };

      setTestResults(prev => [testResult, ...prev]);
    } finally {
      setTestingEndpoint(null);
    }
  };

  // Copy to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  // Generate curl command
  const generateCurl = (endpoint: ApiEndpoint) => {
    let curl = `curl -X ${endpoint.method} \\\n`;
    curl += `  "${API_BASE}${endpoint.path}" \\\n`;
    curl += `  -H "Content-Type: application/json" \\\n`;
    curl += `  -H "Cookie: session=your_session_cookie"`;

    if (endpoint.method !== "GET") {
      curl += ` \\\n  -d '{"key": "value"}'`;
    }

    return curl;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">API 文档与测试</h1>
          <p className="text-muted-foreground">
            完整的API文档、交互式测试和示例代码
          </p>
        </div>
        <Badge variant="secondary" className="text-sm">
          Week 7 Day 1
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="endpoints">API端点</TabsTrigger>
          <TabsTrigger value="testing">交互测试</TabsTrigger>
          <TabsTrigger value="examples">示例代码</TabsTrigger>
          <TabsTrigger value="monitoring">服务监控</TabsTrigger>
        </TabsList>

        {/* API Endpoints Tab */}
        <TabsContent value="endpoints" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">API端点列表</h3>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {categories.map(category => (
                  <SelectItem key={category} value={category}>
                    {category === "all" ? "全部" : category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-4">
            {filteredEndpoints.map((endpoint, index) => {
              const CategoryIcon = CATEGORY_ICONS[endpoint.category] || FileText;
              return (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <CategoryIcon className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={
                                endpoint.method === "GET" ? "secondary" :
                                endpoint.method === "POST" ? "default" :
                                endpoint.method === "PUT" ? "default" :
                                endpoint.method === "DELETE" ? "destructive" : "secondary"
                              }
                            >
                              {endpoint.method}
                            </Badge>
                            <code className="text-sm bg-muted px-2 py-1 rounded">
                              {endpoint.path}
                            </code>
                          </div>
                          <CardDescription className="mt-1">
                            {endpoint.description}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => copyToClipboard(generateCurl(endpoint))}
                        >
                          <Copy className="w-4 h-4 mr-1" />
                          复制
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => testEndpoint(endpoint)}
                          disabled={testingEndpoint === endpoint.path}
                        >
                          {testingEndpoint === endpoint.path ? (
                            <>
                              <RotateCcw className="w-4 h-4 mr-1 animate-spin" />
                              测试中
                            </>
                          ) : (
                            <>
                              <Play className="w-4 h-4 mr-1" />
                              测试
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Accordion type="single" collapsible>
                      <AccordionItem value="details">
                        <AccordionTrigger>查看详情</AccordionTrigger>
                        <AccordionContent className="space-y-4">
                          {/* Parameters */}
                          {endpoint.parameters.length > 0 && (
                            <div>
                              <h4 className="font-medium mb-2">参数</h4>
                              <div className="space-y-2">
                                {endpoint.parameters.map((param, idx) => (
                                  <div key={idx} className="flex justify-between items-center p-2 border rounded">
                                    <div>
                                      <code className="text-sm">{param.name}</code>
                                      <Badge variant="outline" className="ml-2 text-xs">
                                        {param.type}
                                      </Badge>
                                      {param.required && (
                                        <Badge variant="destructive" className="ml-1 text-xs">
                                          必需
                                        </Badge>
                                      )}
                                    </div>
                                    <span className="text-sm text-muted-foreground">
                                      {param.description}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Request Body */}
                          {endpoint.requestBody && (
                            <div>
                              <h4 className="font-medium mb-2">请求体</h4>
                              <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto">
                                {JSON.stringify(endpoint.requestBody, null, 2)}
                              </pre>
                            </div>
                          )}

                          {/* Responses */}
                          <div>
                            <h4 className="font-medium mb-2">响应示例</h4>
                            {Object.entries(endpoint.responses).map(([code, response]) => (
                              <div key={code} className="mb-3">
                                <div className="flex items-center gap-2 mb-1">
                                  <Badge variant={code === "200" ? "default" : "secondary"}>
                                    {code}
                                  </Badge>
                                  <span className="text-sm">{response.description}</span>
                                </div>
                                {response.example && (
                                  <pre className="bg-gray-100 p-3 rounded text-sm overflow-x-auto">
                                    {JSON.stringify(response.example, null, 2)}
                                  </pre>
                                )}
                              </div>
                            ))}
                          </div>

                          {/* Curl Command */}
                          <div>
                            <h4 className="font-medium mb-2">cURL 命令</h4>
                            <pre className="bg-gray-900 text-green-400 p-3 rounded text-sm overflow-x-auto">
                              {generateCurl(endpoint)}
                            </pre>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        {/* Interactive Testing Tab */}
        <TabsContent value="testing" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Test Form */}
            <Card>
              <CardHeader>
                <CardTitle>API测试工具</CardTitle>
                <CardDescription>
                  自定义参数测试API端点
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">选择端点</label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="选择要测试的API端点" />
                    </SelectTrigger>
                    <SelectContent>
                      {API_ENDPOINTS.map((endpoint, index) => (
                        <SelectItem key={index} value={endpoint.path}>
                          {endpoint.method} {endpoint.path}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">请求参数</label>
                  <Textarea
                    placeholder="输入JSON格式的参数..."
                    rows={6}
                    defaultValue='{\n  "key": "value"\n}'
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">请求头</label>
                  <Input
                    placeholder="Authorization: Bearer token"
                    defaultValue="Content-Type: application/json"
                  />
                </div>

                <Button className="w-full">
                  <Play className="w-4 h-4 mr-2" />
                  发送请求
                </Button>
              </CardContent>
            </Card>

            {/* Test Results */}
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>测试结果</CardTitle>
                  <Button variant="outline" size="sm" onClick={() => setTestResults([])}>
                    清空结果
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {testResults.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                      暂无测试结果
                    </div>
                  ) : (
                    testResults.map((result, index) => (
                      <div key={index} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            {result.status === "success" ? (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : (
                              <XCircle className="w-5 h-5 text-red-500" />
                            )}
                            <span className="font-medium">{result.endpoint}</span>
                          </div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            {result.duration && <span>{result.duration}ms</span>}
                            <Clock className="w-4 h-4" />
                            <span>{new Date(result.timestamp).toLocaleTimeString()}</span>
                          </div>
                        </div>

                        {result.status === "success" && result.response && (
                          <div className="mt-2">
                            <pre className="bg-gray-100 p-2 rounded text-xs overflow-x-auto">
                              {typeof result.response === "string"
                                ? result.response
                                : JSON.stringify(result.response, null, 2)
                              }
                            </pre>
                          </div>
                        )}

                        {result.status === "error" && result.error && (
                          <Alert variant="destructive" className="mt-2">
                            <AlertDescription>{result.error}</AlertDescription>
                          </Alert>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Examples Tab */}
        <TabsContent value="examples" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Python Examples */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="w-5 h-5" />
                  Python 示例
                </CardTitle>
                <CardDescription>
                  使用Python调用API的示例代码
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">图像分析示例</h4>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded text-sm overflow-x-auto">
{`import requests

# 分析图像
with open('image.jpg', 'rb') as f:
    files = {'image': f}
    data = {
        'analysis_type': 'general',
        'prompt': '请分析这张图片的内容'
    }

    response = requests.post(
        '${API_BASE}/api/v1/multimodal/vision/analyze',
        files=files,
        data=data
    )

    result = response.json()
    print(f"分析结果: {result['description']}")
    print(f"置信度: {result['confidence']}")`}
                  </pre>
                </div>

                <div>
                  <h4 className="font-medium mb-2">工作流执行示例</h4>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded text-sm overflow-x-auto">
{`import requests

# 执行工作流
workflow_data = {
    'inputs': {'input_text': '测试输入'},
    'async_execution': True
}

response = requests.post(
    f'{API_BASE}/api/v1/workflow/{workflow_id}/execute',
    json=workflow_data
)

execution = response.json()
print(f"执行ID: {execution['id']}")
print(f"状态: {execution['status']}")`}
                  </pre>
                </div>
              </CardContent>
            </Card>

            {/* JavaScript Examples */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  JavaScript 示例
                </CardTitle>
                <CardDescription>
                  使用JavaScript调用API的示例代码
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">语音转录示例</h4>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded text-sm overflow-x-auto">
{`// 语音转录
const formData = new FormData();
formData.append('audio', audioFile);
formData.append('task_type', 'transcription');
formData.append('language', 'zh');

fetch('${API_BASE}/api/v1/multimodal/speech/transcribe', {
  method: 'POST',
  body: formData,
  credentials: 'include'
})
.then(response => response.json())
.then(result => {
  console.log('转录结果:', result.text);
  console.log('置信度:', result.confidence);
})
.catch(error => console.error('错误:', error));`}
                  </pre>
                </div>

                <div>
                  <h4 className="font-medium mb-2">文字转语音示例</h4>
                  <pre className="bg-gray-900 text-green-400 p-4 rounded text-sm overflow-x-auto">
{`// 文字转语音
const formData = new FormData();
formData.append('text', '你好，世界！');
formData.append('voice', 'alloy');

fetch('${API_BASE}/api/v1/multimodal/speech/synthesize', {
  method: 'POST',
  body: formData,
  credentials: 'include'
})
.then(response => response.blob())
.then(blob => {
  const audioUrl = URL.createObjectURL(blob);
  const audio = new Audio(audioUrl);
  audio.play();
});`}
                  </pre>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Monitoring Tab */}
        <TabsContent value="monitoring" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Service Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  服务状态
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span>多模态AI服务</span>
                    <Badge className="bg-green-500">健康</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>工作流引擎</span>
                    <Badge className="bg-green-500">健康</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>数据库连接</span>
                    <Badge className="bg-green-500">正常</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* API Statistics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart className="w-5 h-5" />
                  API统计
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span>今日请求</span>
                    <span className="font-medium">1,234</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>成功率</span>
                    <span className="font-medium text-green-500">98.5%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>平均响应时间</span>
                    <span className="font-medium">245ms</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Resource Usage */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  资源使用
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span>活跃用户</span>
                    <span className="font-medium">156</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>工作流执行</span>
                    <span className="font-medium">42</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span>API密钥</span>
                    <span className="font-medium">89</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Real-time Monitoring */}
          <Card>
            <CardHeader>
              <CardTitle>实时监控</CardTitle>
              <CardDescription>
                服务性能和错误监控
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-3">响应时间趋势</h4>
                  <div className="h-40 bg-gray-100 rounded flex items-center justify-center">
                    <span className="text-muted-foreground">响应时间图表</span>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-3">错误率统计</h4>
                  <div className="h-40 bg-gray-100 rounded flex items-center justify-center">
                    <span className="text-muted-foreground">错误率图表</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
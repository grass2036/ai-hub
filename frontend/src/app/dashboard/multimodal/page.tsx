"use client";

import { useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Upload, Download, Play, Pause, RotateCcw, FileText, Image, Mic, Settings } from "lucide-react";

interface AnalysisResult {
  description: string;
  tags: string[];
  confidence: number;
  objects: Array<{ name: string; confidence: number }>;
  text_content?: string;
  sentiment?: string;
  moderation_flags: string[];
  metadata: any;
  processing_time: number;
}

interface SpeechResult {
  text: string;
  confidence: number;
  language: string;
  duration: number;
  segments: Array<{ start: number; end: number; text: string; confidence: number }>;
  translated_text?: string;
  metadata: any;
  processing_time: number;
}

interface DocumentResult {
  content: string;
  summary: string;
  key_points: string[];
  tables: any[];
  images: any[];
  metadata: any;
  processing_time: number;
}

export default function MultimodalPage() {
  const [activeTab, setActiveTab] = useState("vision");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Vision state
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState("general");
  const [visionPrompt, setVisionPrompt] = useState("请详细分析这张图片的内容");
  const [visionResult, setVisionResult] = useState<AnalysisResult | null>(null);

  // Speech state
  const [selectedAudio, setSelectedAudio] = useState<File | null>(null);
  const [speechTaskType, setSpeechTaskType] = useState("transcription");
  const [speechLanguage, setSpeechLanguage] = useState("auto");
  const [speechResult, setSpeechResult] = useState<SpeechResult | null>(null);

  // TTS state
  const [ttsText, setTtsText] = useState("欢迎使用AI Hub多模态AI服务");
  const [ttsVoice, setTtsVoice] = useState("alloy");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  // Document state
  const [selectedDocument, setSelectedDocument] = useState<File | null>(null);
  const [documentQuery, setDocumentQuery] = useState("请总结这个文档的主要内容");
  const [documentResult, setDocumentResult] = useState<DocumentResult | null>(null);

  // Multi-modal state
  const [multimodalInputs, setMultimodalInputs] = useState({
    image: null as File | null,
    audio: null as File | null,
    document: null as File | null,
    text: ""
  });
  const [multimodalResult, setMultimodalResult] = useState<any>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

  // Image handling
  const handleImageSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  // Vision Analysis
  const analyzeImage = async () => {
    if (!selectedImage) {
      setError("请先选择一张图片");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("image", selectedImage);
      formData.append("analysis_type", analysisType);
      formData.append("prompt", visionPrompt);

      const response = await fetch(`${API_BASE}/api/v1/multimodal/vision/analyze`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setVisionResult(result);
    } catch (err: any) {
      setError(err.message || "图像分析失败");
    } finally {
      setLoading(false);
    }
  };

  // Audio handling
  const handleAudioSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedAudio(file);
    }
  };

  // Speech Transcription
  const transcribeAudio = async () => {
    if (!selectedAudio) {
      setError("请先选择一个音频文件");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("audio", selectedAudio);
      formData.append("task_type", speechTaskType);
      formData.append("language", speechLanguage);

      const response = await fetch(`${API_BASE}/api/v1/multimodal/speech/transcribe`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setSpeechResult(result);
    } catch (err: any) {
      setError(err.message || "音频转录失败");
    } finally {
      setLoading(false);
    }
  };

  // Text to Speech
  const synthesizeSpeech = async () => {
    if (!ttsText.trim()) {
      setError("请输入要合成的文本");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("text", ttsText);
      formData.append("voice", ttsVoice);

      const response = await fetch(`${API_BASE}/api/v1/multimodal/speech/synthesize`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (err: any) {
      setError(err.message || "语音合成失败");
    } finally {
      setLoading(false);
    }
  };

  // Document handling
  const handleDocumentSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedDocument(file);
    }
  };

  // Document Analysis
  const analyzeDocument = async () => {
    if (!selectedDocument) {
      setError("请先选择一个文档");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("document", selectedDocument);
      formData.append("query", documentQuery);

      const response = await fetch(`${API_BASE}/api/v1/multimodal/document/analyze`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setDocumentResult(result);
    } catch (err: any) {
      setError(err.message || "文档分析失败");
    } finally {
      setLoading(false);
    }
  };

  // Multi-modal processing
  const processMultimodal = async () => {
    const hasAnyInput = multimodalInputs.image || multimodalInputs.audio ||
                       multimodalInputs.document || multimodalInputs.text.trim();

    if (!hasAnyInput) {
      setError("请至少提供一种输入内容");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("task", "comprehensive_analysis");

      if (multimodalInputs.image) formData.append("image", multimodalInputs.image);
      if (multimodalInputs.audio) formData.append("audio", multimodalInputs.audio);
      if (multimodalInputs.document) formData.append("document", multimodalInputs.document);
      if (multimodalInputs.text.trim()) formData.append("text", multimodalInputs.text);

      const response = await fetch(`${API_BASE}/api/v1/multimodal/process`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setMultimodalResult(result);
    } catch (err: any) {
      setError(err.message || "多模态处理失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">多模态AI服务</h1>
          <p className="text-muted-foreground">
            图像识别、语音处理、文档理解和多模态集成
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
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="vision" className="flex items-center gap-2">
            <Image className="w-4 h-4" />
            图像分析
          </TabsTrigger>
          <TabsTrigger value="speech" className="flex items-center gap-2">
            <Mic className="w-4 h-4" />
            语音处理
          </TabsTrigger>
          <TabsTrigger value="document" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            文档理解
          </TabsTrigger>
          <TabsTrigger value="multimodal" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            多模态集成
          </TabsTrigger>
          <TabsTrigger value="api" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            API测试
          </TabsTrigger>
        </TabsList>

        {/* Vision Analysis Tab */}
        <TabsContent value="vision" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Input Section */}
            <Card>
              <CardHeader>
                <CardTitle>图像输入</CardTitle>
                <CardDescription>
                  上传图片并选择分析类型
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">选择图片</label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="cursor-pointer"
                  />
                </div>

                {imagePreview && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium">图片预览</label>
                    <img
                      src={imagePreview}
                      alt="Preview"
                      className="w-full h-48 object-cover rounded-lg"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-2">分析类型</label>
                  <Select value={analysisType} onValueChange={setAnalysisType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="general">通用分析</SelectItem>
                      <SelectItem value="ocr">文字识别(OCR)</SelectItem>
                      <SelectItem value="object_detection">物体检测</SelectItem>
                      <SelectItem value="classification">图像分类</SelectItem>
                      <SelectItem value="sentiment">情感分析</SelectItem>
                      <SelectItem value="content_moderation">内容审核</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">分析提示词</label>
                  <Textarea
                    value={visionPrompt}
                    onChange={(e) => setVisionPrompt(e.target.value)}
                    placeholder="请输入分析提示词..."
                    rows={3}
                  />
                </div>

                <Button
                  onClick={analyzeImage}
                  disabled={!selectedImage || loading}
                  className="w-full"
                >
                  {loading ? (
                    <>
                      <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                      分析中...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      开始分析
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Results Section */}
            <Card>
              <CardHeader>
                <CardTitle>分析结果</CardTitle>
                <CardDescription>
                  AI图像分析的结果展示
                </CardDescription>
              </CardHeader>
              <CardContent>
                {visionResult ? (
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium mb-2">描述</h4>
                      <p className="text-sm text-muted-foreground">
                        {visionResult.description}
                      </p>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">置信度</h4>
                      <div className="flex items-center gap-2">
                        <Progress value={visionResult.confidence * 100} className="flex-1" />
                        <span className="text-sm font-medium">
                          {(visionResult.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    {visionResult.tags.length > 0 && (
                      <div>
                        <h4 className="font-medium mb-2">标签</h4>
                        <div className="flex flex-wrap gap-1">
                          {visionResult.tags.map((tag, index) => (
                            <Badge key={index} variant="secondary">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {visionResult.objects.length > 0 && (
                      <div>
                        <h4 className="font-medium mb-2">识别对象</h4>
                        <div className="space-y-1">
                          {visionResult.objects.map((obj, index) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span>{obj.name}</span>
                              <span className="text-muted-foreground">
                                {(obj.confidence * 100).toFixed(1)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {visionResult.text_content && (
                      <div>
                        <h4 className="font-medium mb-2">识别文字</h4>
                        <p className="text-sm text-muted-foreground">
                          {visionResult.text_content}
                        </p>
                      </div>
                    )}

                    <div className="text-xs text-muted-foreground">
                      处理时间: {visionResult.processing_time.toFixed(2)}秒
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    暂无分析结果，请先上传图片并开始分析
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Speech Processing Tab */}
        <TabsContent value="speech" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Speech to Text */}
            <Card>
              <CardHeader>
                <CardTitle>语音转文字</CardTitle>
                <CardDescription>
                  上传音频文件进行转录和翻译
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">选择音频文件</label>
                  <Input
                    type="file"
                    accept="audio/*"
                    onChange={handleAudioSelect}
                    className="cursor-pointer"
                  />
                </div>

                {selectedAudio && (
                  <div className="text-sm text-muted-foreground">
                    已选择: {selectedAudio.name}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-2">任务类型</label>
                  <Select value={speechTaskType} onValueChange={setSpeechTaskType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="transcription">语音转录</SelectItem>
                      <SelectItem value="translation">语音翻译</SelectItem>
                      <SelectItem value="dictation">听写</SelectItem>
                      <SelectItem value="command_recognition">命令识别</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">语言</label>
                  <Select value={speechLanguage} onValueChange={setSpeechLanguage}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">自动检测</SelectItem>
                      <SelectItem value="en">英语</SelectItem>
                      <SelectItem value="zh">中文</SelectItem>
                      <SelectItem value="ja">日语</SelectItem>
                      <SelectItem value="ko">韩语</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  onClick={transcribeAudio}
                  disabled={!selectedAudio || loading}
                  className="w-full"
                >
                  {loading ? (
                    <>
                      <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                      转录中...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      开始转录
                    </>
                  )}
                </Button>

                {speechResult && (
                  <div className="mt-4 p-4 bg-muted rounded-lg">
                    <h4 className="font-medium mb-2">转录结果</h4>
                    <p className="text-sm mb-2">{speechResult.text}</p>
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div>置信度: {(speechResult.confidence * 100).toFixed(1)}%</div>
                      <div>语言: {speechResult.language}</div>
                      <div>时长: {speechResult.duration.toFixed(2)}秒</div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Text to Speech */}
            <Card>
              <CardHeader>
                <CardTitle>文字转语音</CardTitle>
                <CardDescription>
                  输入文本生成语音文件
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">输入文本</label>
                  <Textarea
                    value={ttsText}
                    onChange={(e) => setTtsText(e.target.value)}
                    placeholder="请输入要转换为语音的文本..."
                    rows={4}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">声音选择</label>
                  <Select value={ttsVoice} onValueChange={setTtsVoice}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="alloy">中性声音</SelectItem>
                      <SelectItem value="echo">男性声音</SelectItem>
                      <SelectItem value="fable">故事讲述者</SelectItem>
                      <SelectItem value="onyx">深沉男性</SelectItem>
                      <SelectItem value="nova">女性声音</SelectItem>
                      <SelectItem value="shimmer">轻柔女性</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  onClick={synthesizeSpeech}
                  disabled={!ttsText.trim() || loading}
                  className="w-full"
                >
                  {loading ? (
                    <>
                      <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                      生成中...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      生成语音
                    </>
                  )}
                </Button>

                {audioUrl && (
                  <div className="mt-4">
                    <h4 className="font-medium mb-2">生成的语音</h4>
                    <audio controls className="w-full">
                      <source src={audioUrl} type="audio/mpeg" />
                      您的浏览器不支持音频播放
                    </audio>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={() => {
                        const a = document.createElement('a');
                        a.href = audioUrl;
                        a.download = 'speech.mp3';
                        a.click();
                      }}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      下载音频
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Document Understanding Tab */}
        <TabsContent value="document" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Input Section */}
            <Card>
              <CardHeader>
                <CardTitle>文档输入</CardTitle>
                <CardDescription>
                  上传文档进行智能分析
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">选择文档</label>
                  <Input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls"
                    onChange={handleDocumentSelect}
                    className="cursor-pointer"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    支持: PDF, Word, 文本, CSV, Excel
                  </p>
                </div>

                {selectedDocument && (
                  <div className="text-sm text-muted-foreground">
                    已选择: {selectedDocument.name}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-2">分析查询</label>
                  <Textarea
                    value={documentQuery}
                    onChange={(e) => setDocumentQuery(e.target.value)}
                    placeholder="请输入对文档的分析要求..."
                    rows={3}
                  />
                </div>

                <Button
                  onClick={analyzeDocument}
                  disabled={!selectedDocument || loading}
                  className="w-full"
                >
                  {loading ? (
                    <>
                      <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                      分析中...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      开始分析
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Results Section */}
            <Card>
              <CardHeader>
                <CardTitle>分析结果</CardTitle>
                <CardDescription>
                  文档智能分析的结果
                </CardDescription>
              </CardHeader>
              <CardContent>
                {documentResult ? (
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium mb-2">文档摘要</h4>
                      <p className="text-sm text-muted-foreground">
                        {documentResult.summary}
                      </p>
                    </div>

                    {documentResult.key_points.length > 0 && (
                      <div>
                        <h4 className="font-medium mb-2">关键要点</h4>
                        <ul className="space-y-1">
                          {documentResult.key_points.map((point, index) => (
                            <li key={index} className="text-sm text-muted-foreground">
                              • {point}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="text-xs text-muted-foreground">
                      处理时间: {documentResult.processing_time.toFixed(2)}秒
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    暂无分析结果，请先上传文档并开始分析
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Multi-modal Integration Tab */}
        <TabsContent value="multimodal" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>多模态集成处理</CardTitle>
              <CardDescription>
                同时处理图像、音频、文档和文本内容
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Image Input */}
                <div>
                  <label className="block text-sm font-medium mb-2">图像</label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      setMultimodalInputs(prev => ({ ...prev, image: file || null }));
                    }}
                    className="cursor-pointer"
                  />
                </div>

                {/* Audio Input */}
                <div>
                  <label className="block text-sm font-medium mb-2">音频</label>
                  <Input
                    type="file"
                    accept="audio/*"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      setMultimodalInputs(prev => ({ ...prev, audio: file || null }));
                    }}
                    className="cursor-pointer"
                  />
                </div>

                {/* Document Input */}
                <div>
                  <label className="block text-sm font-medium mb-2">文档</label>
                  <Input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      setMultimodalInputs(prev => ({ ...prev, document: file || null }));
                    }}
                    className="cursor-pointer"
                  />
                </div>

                {/* Text Input */}
                <div>
                  <label className="block text-sm font-medium mb-2">文本</label>
                  <Input
                    value={multimodalInputs.text}
                    onChange={(e) => {
                      setMultimodalInputs(prev => ({ ...prev, text: e.target.value }));
                    }}
                    placeholder="输入文本内容..."
                  />
                </div>
              </div>

              <Button
                onClick={processMultimodal}
                disabled={loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                    处理中...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    开始多模态处理
                  </>
                )}
              </Button>

              {multimodalResult && (
                <div className="mt-6 p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-4">处理结果</h4>
                  <div className="space-y-4">
                    {Object.entries(multimodalResult.results || {}).map(([modality, result]) => (
                      <div key={modality}>
                        <h5 className="font-medium mb-2 capitalize">{modality}</h5>
                        <pre className="text-sm text-muted-foreground whitespace-pre-wrap">
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Testing Tab */}
        <TabsContent value="api" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API测试工具</CardTitle>
              <CardDescription>
                直接测试多模态AI API端点
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Alert>
                  <AlertDescription>
                    API端点已集成到系统中，您可以通过以下方式访问：
                  </AlertDescription>
                </Alert>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2">图像分析</h4>
                    <code className="text-sm bg-muted p-2 rounded block">
                      POST /api/v1/multimodal/vision/analyze
                    </code>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2">语音转录</h4>
                    <code className="text-sm bg-muted p-2 rounded block">
                      POST /api/v1/multimodal/speech/transcribe
                    </code>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2">语音合成</h4>
                    <code className="text-sm bg-muted p-2 rounded block">
                      POST /api/v1/multimodal/speech/synthesize
                    </code>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2">文档分析</h4>
                    <code className="text-sm bg-muted p-2 rounded block">
                      POST /api/v1/multimodal/document/analyze
                    </code>
                  </div>
                </div>

                <div className="mt-4">
                  <h4 className="font-medium mb-2">服务状态检查</h4>
                  <Button
                    onClick={async () => {
                      try {
                        const response = await fetch(`${API_BASE}/api/v1/multimodal/health`);
                        const result = await response.json();
                        alert(JSON.stringify(result, null, 2));
                      } catch (err) {
                        alert(`Health check failed: ${err}`);
                      }
                    }}
                  >
                    检查服务状态
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
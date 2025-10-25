"""
Multi-Modal AI API Endpoints
Week 7 Day 1: Advanced AI Features Development

Provides RESTful API endpoints for:
- Vision analysis (image recognition, OCR, object detection)
- Speech processing (transcription, synthesis)
- Document understanding
- Multi-modal workflow integration
"""

from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncio
import json
import io
from datetime import datetime

from backend.core.multimodal_ai_service import (
    multimodal_ai_service,
    AnalysisType,
    SpeechTaskType,
    ModalityType,
    ImageAnalysisResult,
    SpeechProcessResult,
    DocumentAnalysisResult
)
from backend.core.ai_service import ai_manager
from backend.core.auth import get_current_user, require_permissions
from backend.core.logging_service import logging_service

router = APIRouter(prefix="/multimodal", tags=["multi-modal"])


# Request/Response Models
class ImageAnalysisRequest(BaseModel):
    """图像分析请求"""
    analysis_type: AnalysisType = AnalysisType.GENERAL
    prompt: str = Field(default="请详细分析这张图片的内容", description="分析提示词")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class SpeechProcessRequest(BaseModel):
    """语音处理请求"""
    task_type: SpeechTaskType = SpeechTaskType.TRANSCRIPTION
    language: str = Field(default="auto", description="语言代码，如'en', 'zh', 'auto'")
    translate_to: Optional[str] = Field(default=None, description="翻译目标语言")


class DocumentAnalysisRequest(BaseModel):
    """文档分析请求"""
    query: str = Field(default="请总结这个文档的主要内容", description="分析查询")
    extract_tables: bool = Field(default=True, description="是否提取表格")
    extract_images: bool = Field(default=True, description="是否提取图片")


class MultiModalProcessRequest(BaseModel):
    """多模态处理请求"""
    task: str = Field(default="analyze", description="处理任务类型")
    modalities: List[str] = Field(description="处理的模态类型列表")
    prompt: Optional[str] = Field(default=None, description="通用提示词")


class ImageAnalysisResponse(BaseModel):
    """图像分析响应"""
    success: bool
    description: str
    tags: List[str]
    confidence: float
    objects: List[Dict[str, Any]]
    text_content: Optional[str] = None
    sentiment: Optional[str] = None
    moderation_flags: List[str] = []
    metadata: Dict[str, Any] = {}
    processing_time: float
    created_at: str


class SpeechProcessResponse(BaseModel):
    """语音处理响应"""
    success: bool
    text: str
    confidence: float
    language: str
    duration: float
    segments: List[Dict[str, Any]]
    translated_text: Optional[str] = None
    metadata: Dict[str, Any] = {}
    processing_time: float
    created_at: str


class DocumentAnalysisResponse(BaseModel):
    """文档分析响应"""
    success: bool
    content: str
    summary: str
    key_points: List[str]
    tables: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}
    processing_time: float
    created_at: str


class MultiModalProcessResponse(BaseModel):
    """多模态处理响应"""
    success: bool
    task: str
    results: Dict[str, Any]
    metadata: Dict[str, Any]
    processing_time: float
    created_at: str


# Helper functions
async def process_with_timer(func, *args, **kwargs):
    """带计时器的处理函数"""
    start_time = datetime.now()
    try:
        result = await func(*args, **kwargs)
        processing_time = (datetime.now() - start_time).total_seconds()

        if isinstance(result, dict):
            result["processing_time"] = processing_time
        else:
            result = {"result": result, "processing_time": processing_time}

        return result, True
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        return {"error": str(e), "processing_time": processing_time}, False


# Vision Analysis Endpoints
@router.post("/vision/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
    analysis_type: AnalysisType = Form(AnalysisType.GENERAL),
    prompt: str = Form("请详细分析这张图片的内容"),
    confidence_threshold: float = Form(0.5),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    分析图像内容

    支持的分析类型：
    - general: 通用图像分析
    - ocr: 文字识别
    - object_detection: 物体检测
    - classification: 图像分类
    - sentiment: 情感分析
    - content_moderation: 内容审核
    """
    try:
        # 验证文件类型
        if not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="上传的文件必须是图片格式"
            )

        # 记录分析请求
        logging_service.log_info(
            f"User {current_user.get('user_id')} requested image analysis: {analysis_type.value}"
        )

        # 执行图像分析
        start_time = datetime.now()
        result = await multimodal_ai_service.vision_service.analyze_image(
            image_data=image,
            analysis_type=analysis_type,
            prompt=prompt
        )
        processing_time = (datetime.now() - start_time).total_seconds()

        # 应用置信度阈值过滤
        if result.confidence < confidence_threshold:
            logging_service.log_warning(
                f"Low confidence result: {result.confidence} < {confidence_threshold}"
            )

        # 记录成功分析
        logging_service.log_info(
            f"Image analysis completed successfully in {processing_time:.2f}s"
        )

        return ImageAnalysisResponse(
            success=True,
            description=result.description,
            tags=result.tags,
            confidence=result.confidence,
            objects=result.objects,
            text_content=result.text_content,
            sentiment=result.sentiment,
            moderation_flags=result.moderation_flags,
            metadata=result.metadata,
            processing_time=processing_time,
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Image analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"图像分析失败: {str(e)}"
        )


@router.post("/vision/ocr")
async def extract_text_from_image(
    image: UploadFile = File(...),
    language: str = Form(default="auto"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """从图片中提取文字（OCR）"""
    try:
        prompt = f"请识别并提取图片中的所有文字内容，保持原有的格式和结构。"
        if language != "auto":
            prompt += f"文字语言应该是：{language}"

        result = await multimodal_ai_service.vision_service.analyze_image(
            image_data=image,
            analysis_type=AnalysisType.OCR,
            prompt=prompt
        )

        return {
            "success": True,
            "extracted_text": result.text_content or result.description,
            "confidence": result.confidence,
            "language": language,
            "created_at": datetime.now().isoformat()
        }

    except Exception as e:
        logging_service.log_error(f"OCR extraction failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文字提取失败: {str(e)}"
        )


# Speech Processing Endpoints
@router.post("/speech/transcribe", response_model=SpeechProcessResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    task_type: SpeechTaskType = Form(SpeechTaskType.TRANSCRIPTION),
    language: str = Form(default="auto"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    音频转文字

    支持的任务类型：
    - transcription: 语音转录
    - translation: 语音翻译
    - dictation: 听写
    - command_recognition: 命令识别
    """
    try:
        # 验证文件类型
        if not audio.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=400,
                detail="上传的文件必须是音频格式"
            )

        # 记录转录请求
        logging_service.log_info(
            f"User {current_user.get('user_id')} requested audio transcription: {task_type.value}"
        )

        # 执行音频转录
        start_time = datetime.now()
        result = await multimodal_ai_service.audio_service.transcribe_audio(
            audio_data=audio,
            task_type=task_type,
            language=language
        )
        processing_time = (datetime.now() - start_time).total_seconds()

        # 记录成功转录
        logging_service.log_info(
            f"Audio transcription completed successfully in {processing_time:.2f}s"
        )

        return SpeechProcessResponse(
            success=True,
            text=result.text,
            confidence=result.confidence,
            language=result.language,
            duration=result.duration,
            segments=result.segments,
            translated_text=result.translated_text,
            metadata=result.metadata,
            processing_time=processing_time,
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Audio transcription failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"音频转录失败: {str(e)}"
        )


@router.post("/speech/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice: str = Form(default="alloy"),
    language: str = Form(default="en"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    文字转语音

    支持的声音选项：
    - alloy: 中性声音
    - echo: 男性声音
    - fable: 故事讲述者声音
    - onyx: 深沉男性声音
    - nova: 女性声音
    - shimmer: 轻柔女性声音
    """
    try:
        # 验证文本长度
        if len(text) > 5000:
            raise HTTPException(
                status_code=400,
                detail="文本长度不能超过5000字符"
            )

        # 记录合成请求
        logging_service.log_info(
            f"User {current_user.get('user_id')} requested speech synthesis: {len(text)} characters"
        )

        # 执行语音合成
        start_time = datetime.now()
        audio_bytes = await multimodal_ai_service.audio_service.synthesize_speech(
            text=text,
            voice=voice,
            language=language
        )
        processing_time = (datetime.now() - start_time).total_seconds()

        # 记录成功合成
        logging_service.log_info(
            f"Speech synthesis completed successfully in {processing_time:.2f}s"
        )

        # 返回音频流
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3",
                "X-Processing-Time": f"{processing_time:.2f}s"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Speech synthesis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"语音合成失败: {str(e)}"
        )


# Document Understanding Endpoints
@router.post("/document/analyze", response_model=DocumentAnalysisResponse)
async def understand_document(
    document: UploadFile = File(...),
    query: str = Form(default="请总结这个文档的主要内容"),
    extract_tables: bool = Form(default=True),
    extract_images: bool = Form(default=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    理解文档内容

    支持的文档格式：
    - PDF: .pdf
    - Word: .docx, .doc
    - 文本: .txt
    - 表格: .csv, .xlsx, .xls
    """
    try:
        # 验证文件类型
        allowed_types = ['.pdf', '.docx', '.doc', '.txt', '.csv', '.xlsx', '.xls']
        file_ext = f".{document.filename.split('.')[-1].lower()}"

        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文档格式。支持的格式: {', '.join(allowed_types)}"
            )

        # 记录分析请求
        logging_service.log_info(
            f"User {current_user.get('user_id')} requested document analysis: {document.filename}"
        )

        # 执行文档分析
        start_time = datetime.now()
        result = await multimodal_ai_service.document_service.understand_document(
            document_data=document,
            query=query
        )
        processing_time = (datetime.now() - start_time).total_seconds()

        # 记录成功分析
        logging_service.log_info(
            f"Document analysis completed successfully in {processing_time:.2f}s"
        )

        return DocumentAnalysisResponse(
            success=True,
            content=result.content,
            summary=result.summary,
            key_points=result.key_points,
            tables=result.tables,
            images=result.images,
            metadata=result.metadata,
            processing_time=processing_time,
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Document analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文档分析失败: {str(e)}"
        )


# Multi-Modal Integration Endpoints
@router.post("/process", response_model=MultiModalProcessResponse)
async def process_multimodal(
    task: str = Form(default="analyze"),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    document: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    处理多模态输入

    可以同时处理多种类型的输入：
    - 图像: 图片文件
    - 音频: 音频文件
    - 文档: 文档文件
    - 文本: 纯文本内容
    """
    try:
        # 构建输入数据
        inputs = {}
        modalities = []

        if image:
            inputs["image"] = image
            modalities.append("image")

        if audio:
            inputs["audio"] = audio
            modalities.append("audio")

        if document:
            inputs["document"] = document
            modalities.append("document")

        if text:
            inputs["text"] = text
            modalities.append("text")

        if not modalities:
            raise HTTPException(
                status_code=400,
                detail="至少需要提供一种输入类型"
            )

        # 添加额外参数
        inputs["prompt"] = prompt or "请分析提供的内容"

        # 记录多模态处理请求
        logging_service.log_info(
            f"User {current_user.get('user_id')} requested multimodal processing: {modalities}"
        )

        # 执行多模态处理
        start_time = datetime.now()
        result = await multimodal_ai_service.process_multimodal_input(
            inputs=inputs,
            task=task
        )
        processing_time = (datetime.now() - start_time).total_seconds()

        # 记录处理结果
        if result.get("success"):
            logging_service.log_info(
                f"Multimodal processing completed successfully in {processing_time:.2f}s"
            )
        else:
            logging_service.log_error(
                f"Multimodal processing failed: {result.get('error', 'Unknown error')}"
            )

        return MultiModalProcessResponse(
            success=result.get("success", False),
            task=task,
            results=result.get("results", {}),
            metadata=result.get("metadata", {}),
            processing_time=processing_time,
            created_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logging_service.log_error(f"Multimodal processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"多模态处理失败: {str(e)}"
        )


# Utility Endpoints
@router.get("/capabilities")
async def get_multimodal_capabilities():
    """获取多模态AI服务的能力信息"""
    try:
        capabilities = {
            "vision": {
                "supported_formats": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
                "analysis_types": [t.value for t in AnalysisType],
                "max_file_size": "10MB",
                "features": [
                    "通用图像分析",
                    "OCR文字识别",
                    "物体检测",
                    "图像分类",
                    "情感分析",
                    "内容审核"
                ]
            },
            "speech": {
                "supported_formats": [".mp3", ".wav", ".m4a", ".ogg", ".flac"],
                "task_types": [t.value for t in SpeechTaskType],
                "max_file_size": "25MB",
                "features": [
                    "语音转文字",
                    "语音翻译",
                    "文字转语音",
                    "命令识别"
                ],
                "supported_languages": ["auto", "en", "zh", "ja", "ko", "es", "fr", "de"]
            },
            "document": {
                "supported_formats": [".pdf", ".docx", ".doc", ".txt", ".csv", ".xlsx", ".xls"],
                "max_file_size": "50MB",
                "features": [
                    "文档内容提取",
                    "智能摘要生成",
                    "关键点提取",
                    "表格数据提取",
                    "图片内容分析"
                ]
            },
            "integration": {
                "multimodal_combinations": [
                    "image + text",
                    "audio + text",
                    "document + text",
                    "image + audio + text"
                ],
                "workflow_support": True,
                "batch_processing": True
            }
        }

        return {
            "success": True,
            "capabilities": capabilities,
            "version": "1.0.0",
            "updated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logging_service.log_error(f"Failed to get capabilities: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="获取服务能力信息失败"
        )


@router.get("/health")
async def check_multimodal_health():
    """检查多模态AI服务健康状态"""
    try:
        health_status = {
            "vision": {"status": "healthy", "initialized": multimodal_ai_service.vision_service._initialized},
            "audio": {"status": "healthy", "initialized": multimodal_ai_service.audio_service._initialized},
            "document": {"status": "healthy", "initialized": multimodal_ai_service.document_service._initialized},
            "overall": "healthy"
        }

        # 检查初始化状态
        if not multimodal_ai_service._initialized:
            health_status["overall"] = "initializing"

        return {
            "success": True,
            "status": health_status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logging_service.log_error(f"Health check failed: {str(e)}")
        return {
            "success": False,
            "status": {"overall": "unhealthy", "error": str(e)},
            "timestamp": datetime.now().isoformat()
        }
"""
Multi-Modal AI Services Tests
Week 7 Day 1: Advanced AI Features Development

Tests for:
- Vision analysis (image recognition, OCR, object detection)
- Speech processing (transcription, synthesis)
- Document understanding
- Multi-modal workflow integration
"""

import pytest
import asyncio
import tempfile
import os
import json
from io import BytesIO
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path

from backend.core.multimodal_ai_service import (
    VisionService,
    AudioService,
    DocumentService,
    MultiModalAIService,
    AnalysisType,
    SpeechTaskType,
    ModalityType,
    ImageAnalysisResult,
    SpeechProcessResult,
    DocumentAnalysisResult
)
from backend.config.settings import get_settings


class TestVisionService:
    """视觉服务测试"""

    @pytest.fixture
    def vision_service(self):
        """创建视觉服务实例"""
        return VisionService()

    @pytest.fixture
    def mock_openai_client(self):
        """模拟OpenAI客户端"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "description": "这是一张包含蓝天和白云的风景图片",
            "tags": ["天空", "云", "蓝色", "自然"],
            "confidence": 0.95,
            "objects": [{"name": "天空", "confidence": 0.98}, {"name": "云", "confidence": 0.92}]
        })
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @pytest.fixture
    def sample_image_bytes(self):
        """创建示例图片字节数据"""
        # 创建一个简单的RGB图片
        from PIL import Image
        import numpy as np

        # 100x100的红色图片
        img_array = np.full((100, 100, 3), [255, 0, 0], dtype=np.uint8)
        img = Image.fromarray(img_array)

        # 转换为字节数据
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()

    @pytest.mark.asyncio
    async def test_vision_service_initialization(self, vision_service):
        """测试视觉服务初始化"""
        with patch('backend.core.multimodal_ai_service.openai') as mock_openai:
            mock_client = Mock()
            mock_openai.AsyncClient.return_value = mock_client

            await vision_service.initialize()

            assert vision_service._initialized is True
            assert vision_service.openai_client == mock_client

    @pytest.mark.asyncio
    async def test_vision_service_initialization_failure(self, vision_service):
        """测试视觉服务初始化失败"""
        with patch('backend.core.multimodal_ai_service.openai') as mock_openai:
            mock_openai.AsyncClient.side_effect = Exception("API Key Error")

            with pytest.raises(Exception):
                await vision_service.initialize()

    @pytest.mark.asyncio
    async def test_analyze_image_general(self, vision_service, sample_image_bytes, mock_openai_client):
        """测试通用图像分析"""
        vision_service._initialized = True
        vision_service.openai_client = mock_openai_client

        result = await vision_service.analyze_image(
            image_data=sample_image_bytes,
            analysis_type=AnalysisType.GENERAL,
            prompt="分析这张图片"
        )

        assert isinstance(result, ImageAnalysisResult)
        assert result.description == "这是一张包含蓝天和白云的风景图片"
        assert len(result.tags) > 0
        assert result.confidence == 0.95
        assert len(result.objects) > 0

    @pytest.mark.asyncio
    async def test_analyze_image_ocr(self, vision_service, sample_image_bytes, mock_openai_client):
        """测试OCR图像分析"""
        vision_service._initialized = True
        vision_service.openai_client = mock_openai_client

        # 修改mock响应以返回OCR结果
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "识别到的文字：Hello World"
        vision_service.openai_client.chat.completions.create.return_value = mock_response

        result = await vision_service.analyze_image(
            image_data=sample_image_bytes,
            analysis_type=AnalysisType.OCR,
            prompt="识别图片中的文字"
        )

        assert isinstance(result, ImageAnalysisResult)
        assert result.text_content == "识别到的文字：Hello World"

    @pytest.mark.asyncio
    async def test_process_image_input_bytes(self, vision_service, sample_image_bytes):
        """测试图像字节数据处理"""
        base64_result = await vision_service._process_image_input(sample_image_bytes)
        assert isinstance(base64_result, str)
        assert len(base64_result) > 0

    @pytest.mark.asyncio
    async def test_process_image_input_pil(self, vision_service):
        """测试PIL图像处理"""
        from PIL import Image
        import numpy as np

        img_array = np.full((50, 50, 3), [0, 255, 0], dtype=np.uint8)
        img = Image.fromarray(img_array)

        base64_result = await vision_service._process_image_input(img)
        assert isinstance(base64_result, str)
        assert len(base64_result) > 0

    def test_get_analysis_prompt(self, vision_service):
        """测试分析提示词生成"""
        prompt = vision_service._get_analysis_prompt(
            AnalysisType.GENERAL,
            "自定义提示"
        )
        assert "通用图像分析" in prompt
        assert "自定义提示" in prompt

        ocr_prompt = vision_service._get_analysis_prompt(
            AnalysisType.OCR,
            "识别文字"
        )
        assert "文字识别" in ocr_prompt

    def test_parse_vision_response_json(self, vision_service):
        """测试JSON格式视觉响应解析"""
        json_response = json.dumps({
            "description": "测试描述",
            "tags": ["测试", "图片"],
            "confidence": 0.88,
            "objects": [{"name": "测试对象", "confidence": 0.90}]
        })

        result = vision_service._parse_vision_response(json_response, AnalysisType.GENERAL)

        assert isinstance(result, ImageAnalysisResult)
        assert result.description == "测试描述"
        assert result.tags == ["测试", "图片"]
        assert result.confidence == 0.88

    def test_parse_vision_response_text(self, vision_service):
        """测试纯文本格式视觉响应解析"""
        text_response = "这是一张美丽的风景图片，包含了山脉和湖泊"

        result = vision_service._parse_vision_response(text_response, AnalysisType.GENERAL)

        assert isinstance(result, ImageAnalysisResult)
        assert result.description == text_response
        assert result.confidence == 0.8

    def test_extract_tags(self, vision_service):
        """测试标签提取"""
        text = "图片中有一辆红色的车和一栋建筑，还有一棵树和一个人"
        tags = vision_service._extract_tags(text)

        assert "车" in tags
        assert "建筑" in tags
        assert "树" in tags
        assert "人" in tags


class TestAudioService:
    """音频服务测试"""

    @pytest.fixture
    def audio_service(self):
        """创建音频服务实例"""
        return AudioService()

    @pytest.fixture
    def sample_audio_bytes(self):
        """创建示例音频字节数据"""
        # 创建一个临时的音频文件数据
        audio_data = b"fake_audio_data_for_testing"
        return audio_data

    @pytest.fixture
    def mock_whisper_model(self):
        """模拟Whisper模型"""
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "这是转录的音频内容",
            "language": "zh",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "这是", "avg_logprob": -0.1},
                {"start": 2.0, "end": 4.0, "text": "转录的", "avg_logprob": -0.2},
                {"start": 4.0, "end": 6.0, "text": "音频内容", "avg_logprob": -0.15}
            ]
        }
        return mock_model

    @pytest.mark.asyncio
    async def test_audio_service_initialization(self, audio_service):
        """测试音频服务初始化"""
        with patch('backend.core.multimodal_ai_service.whisper') as mock_whisper, \
             patch('backend.core.multimodal_ai_service.elevenlabs') as mock_elevenlabs:

            mock_whisper.load_model.return_value = Mock()
            mock_elevenlabs.ElevenLabs.return_value = Mock()

            await audio_service.initialize()

            assert audio_service._initialized is True

    @pytest.mark.asyncio
    async def test_transcribe_audio(self, audio_service, sample_audio_bytes, mock_whisper_model):
        """测试音频转录"""
        audio_service._initialized = True
        audio_service.whisper_model = mock_whisper_model

        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_tempfile.return_value.__enter__.return_value.name = "test_audio.mp3"

            result = await audio_service.transcribe_audio(
                audio_data=sample_audio_bytes,
                task_type=SpeechTaskType.TRANSCRIPTION,
                language="zh"
            )

        assert isinstance(result, SpeechProcessResult)
        assert result.text == "这是转录的音频内容"
        assert result.language == "zh"
        assert result.duration > 0
        assert len(result.segments) > 0

    @pytest.mark.asyncio
    async def test_synthesize_speech(self, audio_service):
        """测试语音合成"""
        audio_service._initialized = True
        mock_elevenlabs_client = Mock()
        mock_audio_stream = [b"audio_chunk_1", b"audio_chunk_2"]
        mock_elevenlabs_client.generate.return_value = mock_audio_stream
        audio_service.elevenlabs_client = mock_elevenlabs_client

        result = await audio_service.synthesize_speech(
            text="Hello World",
            voice="alloy",
            language="en"
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_process_audio_input_bytes(self, audio_service, sample_audio_bytes):
        """测试音频字节数据处理"""
        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_tempfile.return_value.__enter__.return_value.name = "test_audio.mp3"

            result = await audio_service._process_audio_input(sample_audio_bytes)
            assert result == "test_audio.mp3"

    @pytest.mark.asyncio
    async def test_process_audio_input_file_path(self, audio_service):
        """测试音频文件路径处理"""
        result = await audio_service._process_audio_input("/path/to/audio.mp3")
        assert result == "/path/to/audio.mp3"

    def test_calculate_overall_confidence(self, audio_service):
        """测试整体置信度计算"""
        segments = [
            {"confidence": 0.9},
            {"confidence": 0.8},
            {"confidence": 0.85}
        ]

        confidence = audio_service._calculate_overall_confidence(segments)
        assert confidence == (0.9 + 0.8 + 0.85) / 3

    def test_calculate_overall_confidence_empty(self, audio_service):
        """测试空段列表的置信度计算"""
        confidence = audio_service._calculate_overall_confidence([])
        assert confidence == 0.0


class TestDocumentService:
    """文档服务测试"""

    @pytest.fixture
    def document_service(self):
        """创建文档服务实例"""
        return DocumentService()

    @pytest.fixture
    def sample_text_content(self):
        """示例文本内容"""
        return """
        AI Hub Platform 是一个企业级AI应用平台。
        它集成了多种AI模型，提供流式响应和成本跟踪。
        本平台采用FastAPI和Next.js构建。
        主要特点包括多模态AI支持、智能工作流引擎和企业级安全。
        """

    @pytest.mark.asyncio
    async def test_document_service_initialization(self, document_service):
        """测试文档服务初始化"""
        with patch('backend.core.multimodal_ai_service.PyPDF2') as mock_pypdf, \
             patch('backend.core.multimodal_ai_service.docx') as mock_docx, \
             patch('backend.core.multimodal_ai_service.pd') as mock_pd:

            await document_service.initialize()
            assert document_service._initialized is True

    @pytest.mark.asyncio
    async def test_understand_text_document(self, document_service, sample_text_content):
        """测试文本文档理解"""
        document_service._initialized = True

        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_tempfile.return_value.__enter__.return_value.name = "test_document.txt"
            mock_tempfile.return_value.__enter__.return_value.write.return_value = None

            with open(mock_tempfile.return_value.__enter__.return_value.name, 'w', encoding='utf-8') as f:
                f.write(sample_text_content)

            result = await document_service.understand_document(
                document_data="test_document.txt",
                query="总结文档内容"
            )

        assert isinstance(result, DocumentAnalysisResult)
        assert "AI Hub Platform" in result.content
        assert len(result.key_points) > 0

    @pytest.mark.asyncio
    async def test_extract_text_content(self, document_service, sample_text_content):
        """测试文本内容提取"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write(sample_text_content)
            tmp_path = tmp.name

        try:
            content = await document_service._extract_text_content(tmp_path)
            assert content == sample_text_content
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_generate_summary(self, document_service):
        """测试摘要生成"""
        long_content = "这是一个很长的文档内容。" * 100
        summary = await document_service._generate_summary(long_content, "总结文档")

        assert len(summary) <= 550  # 500 + "..." + summary info
        assert "..." in summary

    @pytest.mark.asyncio
    async def test_extract_key_points(self, document_service):
        """测试关键点提取"""
        content = """
        第一点：AI Hub平台支持多种AI模型。

        第二点：提供企业级安全保障。

        第三点：具备智能工作流引擎。

        第四点：支持多平台部署。

        第五点：提供完善的API接口。

        第六点：支持多模态AI处理。
        """

        key_points = await document_service._extract_key_points(content)
        assert len(key_points) <= 5  # 最多返回5个关键点
        assert any("AI Hub平台" in point for point in key_points)


class TestMultiModalAIService:
    """多模态AI服务测试"""

    @pytest.fixture
    def multimodal_service(self):
        """创建多模态AI服务实例"""
        return MultiModalAIService()

    @pytest.mark.asyncio
    async def test_multimodal_service_initialization(self, multimodal_service):
        """测试多模态服务初始化"""
        with patch.object(multimodal_service.vision_service, 'initialize') as mock_vision, \
             patch.object(multimodal_service.audio_service, 'initialize') as mock_audio, \
             patch.object(multimodal_service.document_service, 'initialize') as mock_doc:

            await multimodal_service.initialize()

            assert multimodal_service._initialized is True
            mock_vision.assert_called_once()
            mock_audio.assert_called_once()
            mock_doc.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_multimodal_input_image_text(self, multimodal_service):
        """测试图像+文本多模态处理"""
        multimodal_service._initialized = True

        # 模拟视觉服务结果
        mock_vision_result = ImageAnalysisResult(
            description="美丽的风景图片",
            tags=["天空", "云"],
            confidence=0.95,
            objects=[]
        )

        with patch.object(multimodal_service.vision_service, 'analyze_image',
                         return_value=mock_vision_result):

            inputs = {
                "image": b"fake_image_data",
                "text": "请分析这张图片"
            }

            result = await multimodal_service.process_multimodal_input(
                inputs=inputs,
                task="analyze"
            )

        assert result["success"] is True
        assert "vision" in result["results"]
        assert "text" in result["results"]
        assert result["metadata"]["modalities"] == ["image", "text"]

    @pytest.mark.asyncio
    async def test_process_multimodal_input_all_modalities(self, multimodal_service):
        """测试全模态输入处理"""
        multimodal_service._initialized = True

        # 模拟各种服务结果
        mock_vision_result = ImageAnalysisResult(
            description="图片描述",
            tags=["图片"],
            confidence=0.9,
            objects=[]
        )

        mock_audio_result = SpeechProcessResult(
            text="音频转录结果",
            confidence=0.85,
            language="en",
            duration=5.0,
            segments=[]
        )

        mock_doc_result = DocumentAnalysisResult(
            content="文档内容",
            summary="文档摘要",
            key_points=["要点1", "要点2"],
            tables=[],
            images=[],
            metadata={}
        )

        with patch.object(multimodal_service.vision_service, 'analyze_image',
                         return_value=mock_vision_result), \
             patch.object(multimodal_service.audio_service, 'transcribe_audio',
                         return_value=mock_audio_result), \
             patch.object(multimodal_service.document_service, 'understand_document',
                         return_value=mock_doc_result):

            inputs = {
                "image": b"fake_image_data",
                "audio": b"fake_audio_data",
                "document": b"fake_document_data",
                "text": "文本内容"
            }

            result = await multimodal_service.process_multimodal_input(
                inputs=inputs,
                task="comprehensive_analysis"
            )

        assert result["success"] is True
        assert "vision" in result["results"]
        assert "audio" in result["results"]
        assert "document" in result["results"]
        assert "text" in result["results"]
        assert set(result["metadata"]["modalities"]) == {"image", "audio", "document", "text"}

    @pytest.mark.asyncio
    async def test_process_multimodal_input_error_handling(self, multimodal_service):
        """测试多模态处理错误处理"""
        multimodal_service._initialized = True

        with patch.object(multimodal_service.vision_service, 'analyze_image',
                         side_effect=Exception("Service unavailable")):

            inputs = {
                "image": b"fake_image_data"
            }

            result = await multimodal_service.process_multimodal_input(
                inputs=inputs,
                task="analyze"
            )

        assert result["success"] is False
        assert "error" in result
        assert "Service unavailable" in result["error"]


class TestMultiModalIntegration:
    """多模态AI集成测试"""

    @pytest.mark.asyncio
    async def test_vision_audio_workflow(self):
        """测试视觉+音频工作流"""
        # 创建临时图片和音频文件
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as img_file, \
             tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_file:

            # 写入测试数据
            img_file.write(b"fake_image_data")
            audio_file.write(b"fake_audio_data")

            img_path = img_file.name
            audio_path = audio_file.name

        try:
            # 测试多模态工作流
            multimodal_service = MultiModalAIService()
            multimodal_service._initialized = True

            with patch.object(multimodal_service.vision_service, 'analyze_image') as mock_vision, \
                 patch.object(multimodal_service.audio_service, 'transcribe_audio') as mock_audio:

                mock_vision.return_value = ImageAnalysisResult(
                    description="包含文字的图片",
                    tags=["图片", "文字"],
                    confidence=0.9,
                    objects=[],
                    text_content="图片中的文字内容"
                )

                mock_audio.return_value = SpeechProcessResult(
                    text="语音解释了图片的内容",
                    confidence=0.85,
                    language="zh",
                    duration=10.0,
                    segments=[]
                )

                # 模拟工作流：分析图片，然后转录语音解释
                vision_result = await multimodal_service.vision_service.analyze_image(img_path)
                audio_result = await multimodal_service.audio_service.transcribe_audio(audio_path)

                # 验证结果
                assert vision_result.text_content == "图片中的文字内容"
                assert audio_result.text == "语音解释了图片的内容"

        finally:
            # 清理临时文件
            os.unlink(img_path)
            os.unlink(audio_path)

    @pytest.mark.asyncio
    async def test_document_analysis_with_vision(self):
        """测试文档分析结合视觉理解"""
        multimodal_service = MultiModalAIService()
        multimodal_service._initialized = True

        # 模拟包含图片的PDF文档分析
        mock_doc_result = DocumentAnalysisResult(
            content="文档文字内容\n[图片位置1]\n更多文字内容",
            summary="文档包含文字和图片",
            key_points=["文字要点", "图片说明"],
            tables=[],
            images=[{"page": 1, "description": "图表"}],
            metadata={"file_type": ".pdf"}
        )

        with patch.object(multimodal_service.document_service, 'understand_document',
                         return_value=mock_doc_result), \
             patch.object(multimodal_service.vision_service, 'analyze_image') as mock_vision:

            mock_vision.return_value = ImageAnalysisResult(
                description="文档中的图片是一个数据图表",
                tags=["图表", "数据"],
                confidence=0.95,
                objects=[],
                text_content="图表标题：2024年AI发展趋势"
            )

            # 先分析文档
            doc_result = await multimodal_service.document_service.understand_document(
                "test_document.pdf"
            )

            # 然后分析文档中的图片
            if doc_result.images:
                vision_result = await multimodal_service.vision_service.analyze_image(
                    b"fake_image_data",
                    analysis_type=AnalysisType.OCR
                )

            # 验证综合分析结果
            assert doc_result.summary == "文档包含文字和图片"
            assert len(doc_result.images) > 0
            assert vision_result.text_content == "图表标题：2024年AI发展趋势"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
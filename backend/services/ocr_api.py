"""
OCR/AI 통합 API 엔드포인트
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List
from pydantic import BaseModel
import tempfile
import os

from .smart_processor import SmartDocumentProcessor, ProcessingStrategy

router = APIRouter(prefix="/api/v1/ocr", tags=["OCR/AI"])


# Pydantic 모델
class ProcessingRequest(BaseModel):
    strategy: Optional[str] = None  # opensource, gemini, gpt5_nano, gpt5_mini, hybrid, cost_optimized
    prompt: Optional[str] = None


class ProcessingResponse(BaseModel):
    text: str
    tables: List[dict]
    confidence: float
    cost: float
    processing_time: float
    strategy: str
    metadata: dict


class ComplexityAnalysisResponse(BaseModel):
    complexity_score: int
    has_tables: bool
    has_complex_layout: bool
    has_low_confidence: bool
    is_handwritten: bool
    is_multi_language: bool
    recommended_strategy: str
    features: dict


class CostEstimateResponse(BaseModel):
    total_files: int
    total_estimated_cost: float
    estimates: List[dict]
    strategy: str


# 전역 프로세서 (싱글톤)
processor = None


def get_processor() -> SmartDocumentProcessor:
    """프로세서 인스턴스 가져오기"""
    global processor
    if processor is None:
        processor = SmartDocumentProcessor({
            "use_gpu": False  # 프로덕션에서는 GPU 사용 권장
        })
    return processor


@router.post("/process", response_model=ProcessingResponse)
async def process_document(
    file: UploadFile = File(...),
    strategy: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None)
):
    """
    문서 처리 (스마트 OCR/AI)

    Args:
        file: 업로드 파일 (이미지 또는 PDF)
        strategy: 처리 전략 (없으면 자동 선택)
            - opensource: 오픈소스만 (무료)
            - gemini: Gemini 2.5 Flash
            - gpt5_nano: GPT-5 Nano
            - gpt5_mini: GPT-5 Mini
            - hybrid: 하이브리드 (오픈소스 + 검증)
            - cost_optimized: 비용 최적화 (자동)
        prompt: LLM 처리 프롬프트 (선택적)

    Returns:
        ProcessingResponse
    """
    # 전략 변환
    strategy_map = {
        "opensource": ProcessingStrategy.OPENSOURCE_ONLY,
        "gemini": ProcessingStrategy.GEMINI_PRIMARY,
        "gpt5_nano": ProcessingStrategy.GPT5_NANO,
        "gpt5_mini": ProcessingStrategy.GPT5_MINI,
        "hybrid": ProcessingStrategy.HYBRID_VERIFY,
        "cost_optimized": ProcessingStrategy.COST_OPTIMIZED
    }

    processing_strategy = strategy_map.get(strategy) if strategy else None

    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # 문서 처리
        proc = get_processor()
        result = proc.process_document(temp_path, processing_strategy, prompt)

        return ProcessingResponse(
            text=result.text,
            tables=result.tables,
            confidence=result.confidence,
            cost=result.cost,
            processing_time=result.processing_time,
            strategy=result.strategy,
            metadata=result.metadata
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/analyze-complexity", response_model=ComplexityAnalysisResponse)
async def analyze_document_complexity(
    file: UploadFile = File(...)
):
    """
    문서 복잡도 분석

    Args:
        file: 업로드 파일

    Returns:
        ComplexityAnalysisResponse
    """
    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # 복잡도 분석
        proc = get_processor()
        complexity = proc.analyze_complexity(temp_path)

        return ComplexityAnalysisResponse(
            complexity_score=complexity.complexity_score,
            has_tables=complexity.has_tables,
            has_complex_layout=complexity.has_complex_layout,
            has_low_confidence=complexity.has_low_confidence,
            is_handwritten=complexity.is_handwritten,
            is_multi_language=complexity.is_multi_language,
            recommended_strategy=complexity.recommended_strategy.value,
            features=complexity.features
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/engines")
async def list_available_engines():
    """
    사용 가능한 엔진 목록

    Returns:
        OCR 및 LLM 엔진 목록
    """
    from ocr_engines import OCREngineFactory
    from llm_engines import LLMEngineFactory

    return {
        "ocr_engines": OCREngineFactory.list_engines(),
        "llm_engines": LLMEngineFactory.list_engines(),
        "strategies": [s.value for s in ProcessingStrategy]
    }


@router.get("/pricing")
async def get_pricing_info():
    """
    가격 정보

    Returns:
        엔진별 가격 정보
    """
    return {
        "opensource": {
            "cost_per_page": 0.0,
            "engines": ["tesseract", "easyocr", "camelot"]
        },
        "gemini_flash_lite": {
            "input_price_per_million": 0.10,
            "output_price_per_million": 0.40,
            "estimated_cost_per_page": 0.01
        },
        "gemini_flash": {
            "input_price_per_million": 0.075,
            "output_price_per_million": 0.30,
            "estimated_cost_per_page": 0.008
        },
        "gpt5_nano": {
            "input_price_per_million": 0.05,
            "output_price_per_million": 0.40,
            "estimated_cost_per_page": 0.005
        },
        "gpt5_mini": {
            "input_price_per_million": 0.25,
            "output_price_per_million": 2.00,
            "estimated_cost_per_page": 0.03
        },
        "gpt5": {
            "input_price_per_million": 1.25,
            "output_price_per_million": 10.00,
            "estimated_cost_per_page": 0.15
        }
    }

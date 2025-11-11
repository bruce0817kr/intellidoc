"""
OCR 엔진 모듈
다양한 OCR 라이브러리를 통합 관리
"""

from .base import BaseOCREngine, OCRResult, OCREngineFactory
from .tesseract_engine import TesseractEngine
from .easyocr_engine import EasyOCREngine
from .camelot_engine import CamelotEngine

__all__ = [
    "BaseOCREngine",
    "OCRResult",
    "OCREngineFactory",
    "TesseractEngine",
    "EasyOCREngine",
    "CamelotEngine",
]

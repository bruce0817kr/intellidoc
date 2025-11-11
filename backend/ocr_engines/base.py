"""
OCR 엔진 기본 클래스 및 팩토리 패턴
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Type
import time


@dataclass
class OCRResult:
    """OCR 결과 데이터 클래스"""

    text: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    engine: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "engine": self.engine
        }


class BaseOCREngine(ABC):
    """OCR 엔진 기본 클래스"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 엔진별 설정 딕셔너리
        """
        self.config = config or {}
        self.engine_name = self.__class__.__name__

    @abstractmethod
    def extract_text(self, image_path: str, **kwargs) -> OCRResult:
        """
        이미지에서 텍스트 추출

        Args:
            image_path: 이미지 파일 경로
            **kwargs: 추가 옵션

        Returns:
            OCRResult 객체
        """
        pass

    def extract_text_with_timing(self, image_path: str, **kwargs) -> OCRResult:
        """처리 시간 측정과 함께 텍스트 추출"""
        start_time = time.time()
        result = self.extract_text(image_path, **kwargs)
        result.processing_time = time.time() - start_time
        result.engine = self.engine_name
        return result


class OCREngineFactory:
    """OCR 엔진 팩토리 패턴"""

    _engines: Dict[str, Type[BaseOCREngine]] = {}

    @classmethod
    def register(cls, name: str):
        """엔진 등록 데코레이터"""
        def decorator(engine_class: Type[BaseOCREngine]):
            cls._engines[name] = engine_class
            return engine_class
        return decorator

    @classmethod
    def create(cls, name: str, config: Optional[Dict[str, Any]] = None) -> BaseOCREngine:
        """
        엔진 인스턴스 생성

        Args:
            name: 엔진 이름
            config: 엔진 설정

        Returns:
            BaseOCREngine 인스턴스

        Raises:
            ValueError: 등록되지 않은 엔진 이름
        """
        if name not in cls._engines:
            available = ", ".join(cls._engines.keys())
            raise ValueError(f"Unknown engine: {name}. Available: {available}")

        return cls._engines[name](config)

    @classmethod
    def list_engines(cls) -> List[str]:
        """사용 가능한 엔진 목록"""
        return list(cls._engines.keys())

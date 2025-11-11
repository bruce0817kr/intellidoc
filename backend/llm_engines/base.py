"""
LLM 엔진 기본 클래스 및 팩토리 패턴
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Type
import time


@dataclass
class LLMResult:
    """LLM 처리 결과 데이터 클래스"""

    text: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    engine: str = ""
    cost: float = 0.0  # 예상 비용 (USD)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "text": self.text,
            "usage": self.usage,
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "engine": self.engine,
            "cost": self.cost
        }


class BaseLLMEngine(ABC):
    """LLM 엔진 기본 클래스"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 엔진별 설정 딕셔너리
        """
        self.config = config or {}
        self.engine_name = self.__class__.__name__
        self.api_key = config.get("api_key", "") if config else ""

    @abstractmethod
    def process_text(self, text: str, prompt: str, **kwargs) -> LLMResult:
        """
        텍스트 처리

        Args:
            text: 입력 텍스트
            prompt: 처리 지시사항
            **kwargs: 추가 옵션

        Returns:
            LLMResult 객체
        """
        pass

    @abstractmethod
    def process_image(
        self,
        image_paths: List[str],
        prompt: str,
        **kwargs
    ) -> LLMResult:
        """
        이미지 처리 (Vision)

        Args:
            image_paths: 이미지 파일 경로 리스트
            prompt: 처리 지시사항
            **kwargs: 추가 옵션

        Returns:
            LLMResult 객체
        """
        pass

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        비용 계산 (USD)

        Args:
            input_tokens: 입력 토큰 수
            output_tokens: 출력 토큰 수

        Returns:
            비용 (USD)
        """
        input_price = self.config.get("input_price_per_million", 0.0)
        output_price = self.config.get("output_price_per_million", 0.0)

        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return input_cost + output_cost


class LLMEngineFactory:
    """LLM 엔진 팩토리 패턴"""

    _engines: Dict[str, Type[BaseLLMEngine]] = {}

    @classmethod
    def register(cls, name: str):
        """엔진 등록 데코레이터"""
        def decorator(engine_class: Type[BaseLLMEngine]):
            cls._engines[name] = engine_class
            return engine_class
        return decorator

    @classmethod
    def create(
        cls,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseLLMEngine:
        """
        엔진 인스턴스 생성

        Args:
            name: 엔진 이름
            config: 엔진 설정

        Returns:
            BaseLLMEngine 인스턴스

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

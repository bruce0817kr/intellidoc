"""
OCR 엔진 추상화 모듈

주요 기능:
1. OCR 엔진 인터페이스 정의
2. 다양한 OCR 엔진 구현체 지원
3. OCR 결과 표준화
"""

import abc
from typing import Dict, Any, Optional, List, Union
import uuid
import os
from pathlib import Path

from shared.config import settings
from shared.exceptions import OCREngineError


class OCRResult:
    """OCR 결과 클래스"""
    
    def __init__(
        self,
        text: str,
        confidence: float,
        page_number: int = 1,
        bounding_boxes: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        OCR 결과 초기화
        
        Args:
            text: 추출된 텍스트
            confidence: 신뢰도 (0.0 ~ 1.0)
            page_number: 페이지 번호
            bounding_boxes: 텍스트 영역 좌표 목록
            metadata: 추가 메타데이터
        """
        self.text = text
        self.confidence = confidence
        self.page_number = page_number
        self.bounding_boxes = bounding_boxes or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 딕셔너리 형태의 OCR 결과
        """
        return {
            "text": self.text,
            "confidence": self.confidence,
            "page_number": self.page_number,
            "bounding_boxes": self.bounding_boxes,
            "metadata": self.metadata
        }


class BaseOCREngine(abc.ABC):
    """OCR 엔진 기본 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        OCR 엔진 초기화
        
        Args:
            config: 엔진 설정
        """
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abc.abstractmethod
    def process_file(self, file_path: str) -> List[OCRResult]:
        """
        파일 처리
        
        Args:
            file_path: 처리할 파일 경로
            
        Returns:
            List[OCRResult]: OCR 결과 목록
        """
        pass
    
    @abc.abstractmethod
    def process_image(self, image_path: str) -> OCRResult:
        """
        이미지 처리
        
        Args:
            image_path: 처리할 이미지 경로
            
        Returns:
            OCRResult: OCR 결과
        """
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """
        파일 유효성 검사
        
        Args:
            file_path: 검사할 파일 경로
            
        Returns:
            bool: 유효한 파일인 경우 True
            
        Raises:
            OCREngineError: 파일이 유효하지 않은 경우
        """
        if not os.path.exists(file_path):
            raise OCREngineError(message=f"파일이 존재하지 않습니다: {file_path}")
        
        return True
    
    def get_temp_dir(self) -> str:
        """
        임시 디렉토리 경로 조회
        
        Returns:
            str: 임시 디렉토리 경로
        """
        temp_dir = os.path.join(settings.UPLOAD_DIR, "temp", str(uuid.uuid4()))
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    
    def cleanup_temp_dir(self, temp_dir: str) -> None:
        """
        임시 디렉토리 정리
        
        Args:
            temp_dir: 정리할 임시 디렉토리 경로
        """
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


class OCREngineFactory:
    """OCR 엔진 팩토리 클래스"""
    
    _engines: Dict[str, type] = {}
    
    @classmethod
    def register(cls, engine_name: str) -> callable:
        """
        OCR 엔진 등록 데코레이터
        
        Args:
            engine_name: 엔진 이름
            
        Returns:
            callable: 데코레이터 함수
        """
        def decorator(engine_class: type) -> type:
            cls._engines[engine_name] = engine_class
            return engine_class
        return decorator
    
    @classmethod
    def create(cls, engine_name: str, config: Optional[Dict[str, Any]] = None) -> BaseOCREngine:
        """
        OCR 엔진 생성
        
        Args:
            engine_name: 엔진 이름
            config: 엔진 설정
            
        Returns:
            BaseOCREngine: OCR 엔진 인스턴스
            
        Raises:
            OCREngineError: 지원하지 않는 엔진인 경우
        """
        if engine_name not in cls._engines:
            raise OCREngineError(message=f"지원하지 않는 OCR 엔진입니다: {engine_name}")
        
        engine_class = cls._engines[engine_name]
        return engine_class(config)
    
    @classmethod
    def get_available_engines(cls) -> List[str]:
        """
        사용 가능한 OCR 엔진 목록 조회
        
        Returns:
            List[str]: 엔진 이름 목록
        """
        return list(cls._engines.keys())

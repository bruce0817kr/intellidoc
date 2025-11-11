"""
EasyOCR 엔진 (딥러닝 기반, 80+ 언어 지원)
"""

from typing import Dict, Any, Optional, List
from .base import BaseOCREngine, OCRResult, OCREngineFactory


@OCREngineFactory.register("easyocr")
class EasyOCREngine(BaseOCREngine):
    """EasyOCR 엔진 - 딥러닝 기반 OCR"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # EasyOCR 지연 import (선택적 의존성)
        try:
            import easyocr
            self.easyocr = easyocr
        except ImportError:
            raise ImportError(
                "EasyOCR is not installed. "
                "Install it with: pip install easyocr"
            )

        # 설정
        self.languages = config.get("languages", ['en', 'ko']) if config else ['en', 'ko']
        self.use_gpu = config.get("use_gpu", False) if config else False
        self.model_storage = config.get(
            "model_storage_directory",
            './models/easyocr'
        ) if config else './models/easyocr'

        # 리더 초기화 (한 번만)
        self.reader = self.easyocr.Reader(
            self.languages,
            gpu=self.use_gpu,
            model_storage_directory=self.model_storage
        )

    def extract_text(self, image_path: str, **kwargs) -> OCRResult:
        """
        EasyOCR로 텍스트 추출

        Args:
            image_path: 이미지 파일 경로
            **kwargs: detail, paragraph 등 추가 옵션

        Returns:
            OCRResult 객체
        """
        # 옵션
        detail = kwargs.get("detail", 1)  # 0: 텍스트만, 1: bbox + 신뢰도 포함
        paragraph = kwargs.get("paragraph", False)  # 단락으로 묶기

        # 텍스트 추출
        results = self.reader.readtext(
            image_path,
            detail=detail,
            paragraph=paragraph
        )

        # 결과 파싱
        if detail == 0:
            # 텍스트만
            text = " ".join(results)
            confidence = 0.0
            text_blocks = []
        else:
            # bbox, 텍스트, 신뢰도
            text_blocks = []
            full_text = []
            confidences = []

            for bbox, text, conf in results:
                text_blocks.append({
                    "text": text,
                    "confidence": float(conf),
                    "bbox": bbox
                })
                full_text.append(text)
                confidences.append(float(conf))

            text = "\n".join(full_text)
            confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            text=text,
            confidence=confidence,
            metadata={
                "text_blocks": text_blocks,
                "languages": self.languages,
                "gpu_used": self.use_gpu,
                "block_count": len(text_blocks),
                "engine": "easyocr"
            }
        )

    def extract_with_languages(
        self,
        image_path: str,
        languages: List[str]
    ) -> OCRResult:
        """특정 언어로 OCR 수행"""
        # 임시 리더 생성
        temp_reader = self.easyocr.Reader(
            languages,
            gpu=self.use_gpu,
            model_storage_directory=self.model_storage
        )

        results = temp_reader.readtext(image_path, detail=1)

        text_blocks = []
        full_text = []
        confidences = []

        for bbox, text, conf in results:
            text_blocks.append({
                "text": text,
                "confidence": float(conf),
                "bbox": bbox
            })
            full_text.append(text)
            confidences.append(float(conf))

        text = "\n".join(full_text)
        confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            text=text,
            confidence=confidence,
            metadata={
                "text_blocks": text_blocks,
                "languages": languages,
                "block_count": len(text_blocks),
                "engine": "easyocr"
            }
        )

"""
Tesseract OCR 엔진
"""

import pytesseract
from PIL import Image
from typing import Dict, Any, Optional
from .base import BaseOCREngine, OCRResult, OCREngineFactory


@OCREngineFactory.register("tesseract")
class TesseractEngine(BaseOCREngine):
    """Tesseract OCR 엔진 (기본)"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.lang = config.get("lang", "eng+kor") if config else "eng+kor"
        self.psm = config.get("psm", 3) if config else 3  # Page segmentation mode

    def extract_text(self, image_path: str, **kwargs) -> OCRResult:
        """
        Tesseract로 텍스트 추출

        Args:
            image_path: 이미지 파일 경로
            **kwargs: lang, psm 등 추가 옵션

        Returns:
            OCRResult 객체
        """
        # 옵션 병합
        lang = kwargs.get("lang", self.lang)
        psm = kwargs.get("psm", self.psm)

        # 이미지 로드
        image = Image.open(image_path)

        # Tesseract 설정
        config_str = f"--psm {psm}"

        # 텍스트 추출
        text = pytesseract.image_to_string(image, lang=lang, config=config_str)

        # 신뢰도 추출 (단어별 신뢰도의 평균)
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=config_str,
            output_type=pytesseract.Output.DICT
        )

        confidences = [
            float(conf) for conf in data['conf']
            if conf != '-1' and str(conf).replace('.', '').isdigit()
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            text=text.strip(),
            confidence=avg_confidence / 100.0,  # 0-1 범위로 정규화
            metadata={
                "word_count": len(text.split()),
                "lang": lang,
                "psm": psm,
                "engine": "tesseract"
            }
        )

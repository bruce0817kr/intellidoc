"""
OCR 엔진 테스트
"""

import pytest
import os
from ocr_engines import OCREngineFactory, BaseOCREngine


class TestOCREngineFactory:
    """OCR 엔진 팩토리 테스트"""

    def test_list_engines(self):
        """등록된 엔진 목록 확인"""
        engines = OCREngineFactory.list_engines()
        assert "tesseract" in engines
        assert "easyocr" in engines
        assert "camelot" in engines

    def test_create_tesseract_engine(self):
        """Tesseract 엔진 생성"""
        engine = OCREngineFactory.create("tesseract")
        assert isinstance(engine, BaseOCREngine)
        assert engine.engine_name == "TesseractEngine"

    def test_create_unknown_engine(self):
        """존재하지 않는 엔진 생성 시 에러"""
        with pytest.raises(ValueError):
            OCREngineFactory.create("unknown_engine")


class TestTesseractEngine:
    """Tesseract 엔진 테스트"""

    @pytest.fixture
    def engine(self):
        return OCREngineFactory.create("tesseract", {
            "lang": "eng",
            "psm": 6
        })

    def test_engine_initialization(self, engine):
        """엔진 초기화"""
        assert engine.lang == "eng"
        assert engine.psm == 6

    # Note: 실제 이미지 파일이 필요한 테스트는 통합 테스트에서 수행


class TestEasyOCREngine:
    """EasyOCR 엔진 테스트"""

    def test_engine_creation_without_library(self):
        """라이브러리 없이 생성 시 에러 처리"""
        # EasyOCR이 설치되지 않은 환경에서는 ImportError 발생
        try:
            engine = OCREngineFactory.create("easyocr")
            # 설치된 경우
            assert engine is not None
        except ImportError as e:
            # 설치되지 않은 경우
            assert "EasyOCR is not installed" in str(e)


class TestCamelotEngine:
    """Camelot 엔진 테스트"""

    def test_engine_creation_without_library(self):
        """라이브러리 없이 생성 시 에러 처리"""
        try:
            engine = OCREngineFactory.create("camelot")
            assert engine is not None
        except ImportError as e:
            assert "Camelot is not installed" in str(e)

    @pytest.fixture
    def engine(self):
        try:
            return OCREngineFactory.create("camelot", {
                "flavor": "lattice"
            })
        except ImportError:
            pytest.skip("Camelot not installed")

    def test_engine_initialization(self, engine):
        """엔진 초기화"""
        assert engine.flavor == "lattice"

    def test_non_pdf_file_handling(self, engine):
        """PDF가 아닌 파일 처리 시 에러 메시지"""
        result = engine.extract_text("image.jpg")
        assert result.confidence == 0.0
        assert "only supports PDF" in result.metadata.get("error", "")

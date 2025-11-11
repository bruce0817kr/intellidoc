"""
스마트 문서 처리기 테스트
"""

import pytest
from services.smart_processor import (
    SmartDocumentProcessor,
    ProcessingStrategy,
    DocumentComplexity
)


class TestProcessingStrategy:
    """처리 전략 enum 테스트"""

    def test_strategies_exist(self):
        """모든 전략 정의 확인"""
        assert ProcessingStrategy.OPENSOURCE_ONLY
        assert ProcessingStrategy.GEMINI_PRIMARY
        assert ProcessingStrategy.GPT5_NANO
        assert ProcessingStrategy.GPT5_MINI
        assert ProcessingStrategy.HYBRID_VERIFY
        assert ProcessingStrategy.COST_OPTIMIZED


class TestSmartDocumentProcessor:
    """스마트 문서 처리기 테스트"""

    @pytest.fixture
    def processor(self):
        """프로세서 인스턴스"""
        return SmartDocumentProcessor({
            "use_gpu": False
        })

    def test_processor_initialization(self, processor):
        """프로세서 초기화"""
        assert processor.tesseract is not None
        # EasyOCR과 Camelot은 설치 여부에 따라 None일 수 있음

    def test_recommend_strategy_simple(self, processor):
        """단순 문서 전략 추천"""
        strategy = processor._recommend_strategy(20, {})
        assert strategy == ProcessingStrategy.OPENSOURCE_ONLY

    def test_recommend_strategy_medium(self, processor):
        """중간 복잡도 전략 추천"""
        strategy = processor._recommend_strategy(40, {})
        assert strategy == ProcessingStrategy.HYBRID_VERIFY

    def test_recommend_strategy_complex(self, processor):
        """복잡 문서 전략 추천"""
        strategy = processor._recommend_strategy(60, {})
        assert strategy == ProcessingStrategy.GEMINI_PRIMARY

    def test_recommend_strategy_very_complex(self, processor):
        """매우 복잡 문서 전략 추천"""
        strategy = processor._recommend_strategy(80, {})
        assert strategy == ProcessingStrategy.GPT5_MINI

    def test_cost_estimate(self, processor):
        """비용 예측"""
        # 가상의 파일 경로 (실제 파일 없이 테스트)
        # Note: 실제 테스트는 통합 테스트에서 수행
        pass


class TestDocumentComplexity:
    """문서 복잡도 데이터 클래스 테스트"""

    def test_complexity_creation(self):
        """복잡도 객체 생성"""
        complexity = DocumentComplexity(
            complexity_score=50,
            has_tables=True,
            has_complex_layout=False,
            has_low_confidence=False,
            is_handwritten=False,
            is_multi_language=True,
            recommended_strategy=ProcessingStrategy.GEMINI_PRIMARY,
            features={"word_count": 500}
        )

        assert complexity.complexity_score == 50
        assert complexity.has_tables is True
        assert complexity.recommended_strategy == ProcessingStrategy.GEMINI_PRIMARY

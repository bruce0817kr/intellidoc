"""
LLM 엔진 테스트
"""

import pytest
import os
from llm_engines import LLMEngineFactory, BaseLLMEngine


class TestLLMEngineFactory:
    """LLM 엔진 팩토리 테스트"""

    def test_list_engines(self):
        """등록된 엔진 목록 확인"""
        engines = LLMEngineFactory.list_engines()
        assert "gemini_flash" in engines or "gemini_flash_lite" in engines
        assert "gpt5_nano" in engines or "gpt5_mini" in engines or "gpt5" in engines

    def test_create_engine_without_api_key(self):
        """API 키 없이 엔진 생성 시 에러"""
        # 환경 변수 백업
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            del os.environ["GEMINI_API_KEY"]

        with pytest.raises(ValueError):
            LLMEngineFactory.create("gemini_flash")

        # 환경 변수 복원
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key


class TestGeminiEngine:
    """Gemini 엔진 테스트"""

    @pytest.fixture
    def engine(self):
        # API 키가 있을 때만 테스트
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not set")

        return LLMEngineFactory.create("gemini_flash_lite", {
            "api_key": api_key,
            "model": "gemini-2.5-flash-lite"
        })

    def test_engine_initialization(self, engine):
        """엔진 초기화"""
        assert engine.model_name == "gemini-2.5-flash-lite"
        assert engine.config["input_price_per_million"] == 0.10
        assert engine.config["output_price_per_million"] == 0.40

    def test_cost_calculation(self, engine):
        """비용 계산"""
        # 1,000 입력 토큰, 500 출력 토큰
        cost = engine.calculate_cost(1000, 500)
        expected = (1000 / 1_000_000) * 0.10 + (500 / 1_000_000) * 0.40
        assert abs(cost - expected) < 0.0001


class TestOpenAIEngine:
    """OpenAI GPT-5 엔진 테스트"""

    @pytest.fixture
    def engine_nano(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")

        return LLMEngineFactory.create("gpt5_nano", {
            "api_key": api_key,
            "model": "gpt-5-nano"
        })

    @pytest.fixture
    def engine_mini(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")

        return LLMEngineFactory.create("gpt5_mini", {
            "api_key": api_key,
            "model": "gpt-5-mini"
        })

    def test_nano_pricing(self, engine_nano):
        """Nano 가격 확인"""
        assert engine_nano.config["input_price_per_million"] == 0.05
        assert engine_nano.config["output_price_per_million"] == 0.40

    def test_mini_pricing(self, engine_mini):
        """Mini 가격 확인"""
        assert engine_mini.config["input_price_per_million"] == 0.25
        assert engine_mini.config["output_price_per_million"] == 2.00

    def test_cost_calculation_nano(self, engine_nano):
        """Nano 비용 계산"""
        cost = engine_nano.calculate_cost(10000, 1000)
        expected = (10000 / 1_000_000) * 0.05 + (1000 / 1_000_000) * 0.40
        assert abs(cost - expected) < 0.0001

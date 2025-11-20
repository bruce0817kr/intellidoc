"""
스마트 문서 처리기
복잡도 분석 및 최적 엔진 선택
"""

import os
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

# import 경로 처리
try:
    # 패키지로 설치된 경우
    from ocr_engines import OCREngineFactory, OCRResult
    from llm_engines import LLMEngineFactory, LLMResult
except ImportError:
    # 직접 실행하는 경우
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from ocr_engines import OCREngineFactory, OCRResult
    from llm_engines import LLMEngineFactory, LLMResult


class ProcessingStrategy(Enum):
    """처리 전략"""
    OPENSOURCE_ONLY = "opensource"  # 오픈소스만 (무료)
    GEMINI_PRIMARY = "gemini"  # Gemini 우선
    GPT5_NANO = "gpt5_nano"  # GPT-5 Nano
    GPT5_MINI = "gpt5_mini"  # GPT-5 Mini
    HYBRID_VERIFY = "hybrid"  # 하이브리드 (오픈소스 + 검증)
    COST_OPTIMIZED = "cost_optimized"  # 비용 최적화 (자동 선택)


@dataclass
class DocumentComplexity:
    """문서 복잡도 분석 결과"""
    complexity_score: int  # 0-100
    has_tables: bool
    has_complex_layout: bool
    has_low_confidence: bool
    is_handwritten: bool
    is_multi_language: bool
    recommended_strategy: ProcessingStrategy
    features: Dict[str, Any]


@dataclass
class ProcessingResult:
    """문서 처리 결과"""
    text: str
    tables: List[Dict[str, Any]]
    confidence: float
    cost: float
    processing_time: float
    strategy: str
    metadata: Dict[str, Any]


class SmartDocumentProcessor:
    """
    스마트 문서 처리기
    복잡도에 따라 최적의 OCR/LLM 엔진 자동 선택
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 설정 딕셔너리
                - gemini_api_key: Gemini API 키
                - openai_api_key: OpenAI API 키
                - default_strategy: 기본 전략
        """
        self.config = config or {}

        # OCR 엔진 초기화
        self.tesseract = OCREngineFactory.create("tesseract")

        try:
            self.easyocr = OCREngineFactory.create("easyocr", {
                "use_gpu": self.config.get("use_gpu", False)
            })
        except ImportError:
            self.easyocr = None

        try:
            self.camelot = OCREngineFactory.create("camelot")
        except ImportError:
            self.camelot = None

        # LLM 엔진 초기화 (선택적)
        self.gemini = None
        self.gpt5_nano = None
        self.gpt5_mini = None

        # Gemini 초기화
        gemini_key = self.config.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                self.gemini = LLMEngineFactory.create("gemini_flash_lite", {
                    "api_key": gemini_key,
                    "model": "gemini-2.5-flash-lite"
                })
            except Exception as e:
                print(f"Gemini initialization failed: {e}")

        # OpenAI 초기화
        openai_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                self.gpt5_nano = LLMEngineFactory.create("gpt5_nano", {
                    "api_key": openai_key,
                    "model": "gpt-5-nano"
                })
                self.gpt5_mini = LLMEngineFactory.create("gpt5_mini", {
                    "api_key": openai_key,
                    "model": "gpt-5-mini"
                })
            except Exception as e:
                print(f"OpenAI initialization failed: {e}")

    def analyze_complexity(self, file_path: str) -> DocumentComplexity:
        """
        문서 복잡도 분석

        Args:
            file_path: 파일 경로

        Returns:
            DocumentComplexity 객체
        """
        # 빠른 OCR로 초기 분석 (Tesseract)
        quick_result = self.tesseract.extract_text_with_timing(file_path)

        complexity_score = 0
        features = {
            "has_tables": False,
            "has_complex_layout": False,
            "has_low_confidence": False,
            "is_handwritten": False,
            "is_multi_language": False,
            "word_count": len(quick_result.text.split())
        }

        # 1. 표 감지 (PDF인 경우 Camelot 사용)
        if file_path.endswith('.pdf') and self.camelot:
            try:
                camelot_result = self.camelot.extract_text(file_path, pages="1")
                if camelot_result.metadata.get("table_count", 0) > 0:
                    features["has_tables"] = True
                    complexity_score += 30
            except:
                pass

        # 2. 신뢰도 확인
        if quick_result.confidence < 0.8:
            features["has_low_confidence"] = True
            complexity_score += 25

        # 3. 복잡한 레이아웃 감지 (단어 수가 많으면 복잡)
        if features["word_count"] > 500:
            features["has_complex_layout"] = True
            complexity_score += 20

        # 4. 다국어 감지 (한글 + 영어 혼합)
        text = quick_result.text
        has_korean = any('\uac00' <= char <= '\ud7a3' for char in text)
        has_english = any('a' <= char.lower() <= 'z' for char in text)
        if has_korean and has_english:
            features["is_multi_language"] = True
            complexity_score += 15

        # 5. 손글씨 감지 (휴리스틱: 매우 낮은 신뢰도 + 짧은 텍스트)
        if quick_result.confidence < 0.5 and features["word_count"] < 100:
            features["is_handwritten"] = True
            complexity_score += 40

        # 전략 추천
        recommended_strategy = self._recommend_strategy(complexity_score, features)

        return DocumentComplexity(
            complexity_score=min(complexity_score, 100),
            has_tables=features["has_tables"],
            has_complex_layout=features["has_complex_layout"],
            has_low_confidence=features["has_low_confidence"],
            is_handwritten=features["is_handwritten"],
            is_multi_language=features["is_multi_language"],
            recommended_strategy=recommended_strategy,
            features=features
        )

    def _recommend_strategy(
        self,
        complexity_score: int,
        features: Dict[str, bool]
    ) -> ProcessingStrategy:
        """
        복잡도 기반 전략 추천

        Args:
            complexity_score: 복잡도 점수 (0-100)
            features: 특성 딕셔너리

        Returns:
            추천 ProcessingStrategy
        """
        # 우선순위: 비용 최적화
        if complexity_score < 30:
            # 단순 문서 -> 오픈소스만
            return ProcessingStrategy.OPENSOURCE_ONLY

        elif complexity_score < 50:
            # 중간 복잡도 -> 하이브리드 (오픈소스 + Gemini 검증)
            return ProcessingStrategy.HYBRID_VERIFY

        elif complexity_score < 70:
            # 복잡 문서 -> Gemini (표, 레이아웃 우수)
            return ProcessingStrategy.GEMINI_PRIMARY

        else:
            # 매우 복잡 또는 손글씨 -> GPT-5 Mini
            return ProcessingStrategy.GPT5_MINI

    def process_document(
        self,
        file_path: str,
        strategy: Optional[ProcessingStrategy] = None,
        prompt: Optional[str] = None
    ) -> ProcessingResult:
        """
        문서 처리 (스마트 엔진 선택)

        Args:
            file_path: 파일 경로
            strategy: 처리 전략 (None이면 자동 선택)
            prompt: LLM 처리 프롬프트 (선택적)

        Returns:
            ProcessingResult 객체
        """
        import time
        start_time = time.time()

        # 1. 복잡도 분석 (전략이 지정되지 않은 경우)
        if strategy is None:
            complexity = self.analyze_complexity(file_path)
            strategy = complexity.recommended_strategy
        else:
            complexity = None

        # 2. 전략별 처리
        if strategy == ProcessingStrategy.OPENSOURCE_ONLY:
            result = self._process_opensource(file_path)

        elif strategy == ProcessingStrategy.GEMINI_PRIMARY:
            result = self._process_gemini(file_path, prompt)

        elif strategy == ProcessingStrategy.GPT5_NANO:
            result = self._process_gpt5(file_path, "gpt-5-nano", prompt)

        elif strategy == ProcessingStrategy.GPT5_MINI:
            result = self._process_gpt5(file_path, "gpt-5-mini", prompt)

        elif strategy == ProcessingStrategy.HYBRID_VERIFY:
            result = self._process_hybrid(file_path, prompt)

        elif strategy == ProcessingStrategy.COST_OPTIMIZED:
            result = self._process_cost_optimized(file_path, complexity, prompt)

        else:
            result = self._process_opensource(file_path)

        result.processing_time = time.time() - start_time
        result.strategy = strategy.value

        return result

    def _process_opensource(self, file_path: str) -> ProcessingResult:
        """오픈소스 엔진으로 처리 (비용: $0)"""

        # EasyOCR 우선 (더 정확), 없으면 Tesseract
        if self.easyocr:
            ocr_result = self.easyocr.extract_text_with_timing(file_path)
        else:
            ocr_result = self.tesseract.extract_text_with_timing(file_path)

        # 표 추출 (PDF인 경우)
        tables = []
        if file_path.endswith('.pdf') and self.camelot:
            try:
                camelot_result = self.camelot.extract_tables_from_pdf(file_path)
                tables = camelot_result.metadata.get("tables", [])
            except:
                pass

        return ProcessingResult(
            text=ocr_result.text,
            tables=tables,
            confidence=ocr_result.confidence,
            cost=0.0,
            processing_time=ocr_result.processing_time,
            strategy="opensource_only",
            metadata={
                "engine": ocr_result.engine,
                "word_count": len(ocr_result.text.split())
            }
        )

    def _process_gemini(
        self,
        file_path: str,
        prompt: Optional[str] = None
    ) -> ProcessingResult:
        """Gemini로 처리"""

        if not self.gemini:
            # Gemini 없으면 오픈소스로 폴백
            return self._process_opensource(file_path)

        # 기본 프롬프트
        if prompt is None:
            prompt = "Extract all text and tables from this document. Preserve the structure."

        # PDF인 경우 PDF 처리, 아니면 이미지 처리
        if file_path.endswith('.pdf'):
            llm_result = self.gemini.process_pdf(file_path, prompt)
        else:
            llm_result = self.gemini.process_image([file_path], prompt)

        # 표 파싱 시도
        tables = []
        # TODO: LLM 결과에서 표 추출 로직

        return ProcessingResult(
            text=llm_result.text,
            tables=tables,
            confidence=0.95,  # Gemini의 높은 신뢰도
            cost=llm_result.cost,
            processing_time=llm_result.processing_time,
            strategy="gemini_primary",
            metadata={
                "engine": "gemini",
                "usage": llm_result.usage
            }
        )

    def _process_gpt5(
        self,
        file_path: str,
        model: str,
        prompt: Optional[str] = None
    ) -> ProcessingResult:
        """GPT-5로 처리"""

        engine = self.gpt5_nano if model == "gpt-5-nano" else self.gpt5_mini

        if not engine:
            # GPT 없으면 오픈소스로 폴백
            return self._process_opensource(file_path)

        # 기본 프롬프트
        if prompt is None:
            prompt = "Extract all text and structured information from this document."

        # 이미지 처리
        llm_result = engine.process_image([file_path], prompt)

        return ProcessingResult(
            text=llm_result.text,
            tables=[],
            confidence=0.93,  # GPT의 높은 신뢰도
            cost=llm_result.cost,
            processing_time=llm_result.processing_time,
            strategy=f"gpt5_{model.split('-')[-1]}",
            metadata={
                "engine": model,
                "usage": llm_result.usage
            }
        )

    def _process_hybrid(
        self,
        file_path: str,
        prompt: Optional[str] = None
    ) -> ProcessingResult:
        """하이브리드 처리 (오픈소스 + Gemini 검증)"""

        # 1단계: 오픈소스 처리
        opensource_result = self._process_opensource(file_path)

        # 2단계: 신뢰도가 낮으면 Gemini로 검증
        if opensource_result.confidence < 0.85:
            if self.gemini:
                gemini_result = self._process_gemini(file_path, prompt)
                gemini_result.strategy = "hybrid_gemini_verified"
                gemini_result.metadata["fallback_from"] = "opensource"
                return gemini_result

        # 신뢰도 충분하면 오픈소스 결과 사용
        opensource_result.strategy = "hybrid_opensource_sufficient"
        return opensource_result

    def _process_cost_optimized(
        self,
        file_path: str,
        complexity: Optional[DocumentComplexity],
        prompt: Optional[str] = None
    ) -> ProcessingResult:
        """비용 최적화 처리 (자동 선택)"""

        # 복잡도 분석이 없으면 수행
        if complexity is None:
            complexity = self.analyze_complexity(file_path)

        # 표 + 복잡한 레이아웃 -> Gemini
        if complexity.has_tables and complexity.has_complex_layout:
            return self._process_gemini(file_path, prompt)

        # 손글씨 또는 매우 복잡 -> GPT-5 Mini
        elif complexity.is_handwritten or complexity.complexity_score > 70:
            return self._process_gpt5(file_path, "gpt-5-mini", prompt)

        # 단순 문서 -> 오픈소스
        elif complexity.complexity_score < 30:
            return self._process_opensource(file_path)

        # 중간 복잡도 -> 하이브리드
        else:
            return self._process_hybrid(file_path, prompt)

    def batch_process(
        self,
        file_paths: List[str],
        strategy: Optional[ProcessingStrategy] = None
    ) -> List[ProcessingResult]:
        """
        배치 처리

        Args:
            file_paths: 파일 경로 리스트
            strategy: 처리 전략 (None이면 파일마다 자동 선택)

        Returns:
            ProcessingResult 리스트
        """
        results = []

        for file_path in file_paths:
            try:
                result = self.process_document(file_path, strategy)
                results.append(result)
            except Exception as e:
                # 에러 처리
                results.append(ProcessingResult(
                    text="",
                    tables=[],
                    confidence=0.0,
                    cost=0.0,
                    processing_time=0.0,
                    strategy="error",
                    metadata={"error": str(e), "file": file_path}
                ))

        return results

    def get_cost_estimate(
        self,
        file_paths: List[str],
        strategy: ProcessingStrategy
    ) -> Dict[str, Any]:
        """
        비용 예측

        Args:
            file_paths: 파일 경로 리스트
            strategy: 처리 전략

        Returns:
            비용 예측 정보
        """
        total_cost = 0.0
        estimates = []

        for file_path in file_paths:
            # 복잡도 분석
            complexity = self.analyze_complexity(file_path)

            # 전략별 예상 비용
            if strategy == ProcessingStrategy.OPENSOURCE_ONLY:
                cost = 0.0
            elif strategy == ProcessingStrategy.GEMINI_PRIMARY:
                # Gemini Flash-Lite 기준: ~$0.01/페이지
                cost = 0.01
            elif strategy == ProcessingStrategy.GPT5_NANO:
                # GPT-5 Nano 기준: ~$0.005/페이지
                cost = 0.005
            elif strategy == ProcessingStrategy.GPT5_MINI:
                # GPT-5 Mini 기준: ~$0.03/페이지
                cost = 0.03
            else:
                cost = 0.0

            estimates.append({
                "file": file_path,
                "complexity_score": complexity.complexity_score,
                "estimated_cost": cost
            })

            total_cost += cost

        return {
            "total_files": len(file_paths),
            "total_estimated_cost": total_cost,
            "estimates": estimates,
            "strategy": strategy.value
        }

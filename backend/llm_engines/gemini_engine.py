"""
Gemini 2.5 Flash 엔진
"""

import os
import json
import base64
import time
from typing import Dict, Any, Optional, List
from .base import BaseLLMEngine, LLMResult, LLMEngineFactory


@LLMEngineFactory.register("gemini_flash")
@LLMEngineFactory.register("gemini_flash_lite")
class GeminiFlashEngine(BaseLLMEngine):
    """
    Gemini 2.5 Flash 엔진
    - 최대 1,500페이지 단일 처리
    - 비용 효율성 최상위
    - 멀티모달 문서 이해
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Google Generative AI import
        try:
            import google.generativeai as genai
            self.genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai is not installed. "
                "Install it with: pip install google-generativeai"
            )

        # API 키 설정
        api_key = self.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in config or environment")

        self.genai.configure(api_key=api_key)

        # 모델 선택
        model_name = config.get("model", "gemini-2.5-flash") if config else "gemini-2.5-flash"
        self.model = self.genai.GenerativeModel(model_name)
        self.model_name = model_name

        # 가격 설정 (per 1M tokens)
        if "lite" in model_name:
            # Flash-Lite: $0.10 입력 / $0.40 출력
            self.config["input_price_per_million"] = 0.10
            self.config["output_price_per_million"] = 0.40
        else:
            # Flash: $0.075 입력 / $0.30 출력
            self.config["input_price_per_million"] = 0.075
            self.config["output_price_per_million"] = 0.30

    def process_text(self, text: str, prompt: str, **kwargs) -> LLMResult:
        """
        텍스트 처리

        Args:
            text: 입력 텍스트
            prompt: 처리 지시사항
            **kwargs: temperature 등 추가 옵션

        Returns:
            LLMResult 객체
        """
        start_time = time.time()

        # 프롬프트 구성
        full_prompt = f"{prompt}\n\n{text}"

        # 생성 설정
        generation_config = {
            "temperature": kwargs.get("temperature", 0.3),
            "top_p": kwargs.get("top_p", 0.95),
            "top_k": kwargs.get("top_k", 40),
            "max_output_tokens": kwargs.get("max_output_tokens", 8192),
        }

        # API 호출
        response = self.model.generate_content(
            full_prompt,
            generation_config=generation_config
        )

        # 토큰 사용량
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count,
            "output_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count
        }

        # 비용 계산
        cost = self.calculate_cost(usage["input_tokens"], usage["output_tokens"])

        return LLMResult(
            text=response.text,
            usage=usage,
            metadata={
                "model": self.model_name,
                "prompt_length": len(text)
            },
            processing_time=time.time() - start_time,
            engine=self.engine_name,
            cost=cost
        )

    def process_image(
        self,
        image_paths: List[str],
        prompt: str,
        **kwargs
    ) -> LLMResult:
        """
        이미지 처리 (Vision)

        Args:
            image_paths: 이미지 파일 경로 리스트 (최대 1,500개)
            prompt: 처리 지시사항
            **kwargs: temperature 등 추가 옵션

        Returns:
            LLMResult 객체
        """
        start_time = time.time()

        # 이미지 로드
        from PIL import Image
        images = [Image.open(path) for path in image_paths]

        # 프롬프트와 이미지 결합
        content = [prompt] + images

        # 생성 설정
        generation_config = {
            "temperature": kwargs.get("temperature", 0.3),
            "top_p": kwargs.get("top_p", 0.95),
            "top_k": kwargs.get("top_k", 40),
            "max_output_tokens": kwargs.get("max_output_tokens", 8192),
        }

        # API 호출
        response = self.model.generate_content(
            content,
            generation_config=generation_config
        )

        # 토큰 사용량
        usage = {
            "input_tokens": response.usage_metadata.prompt_token_count,
            "output_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count
        }

        # 비용 계산
        cost = self.calculate_cost(usage["input_tokens"], usage["output_tokens"])

        return LLMResult(
            text=response.text,
            usage=usage,
            metadata={
                "model": self.model_name,
                "image_count": len(image_paths)
            },
            processing_time=time.time() - start_time,
            engine=self.engine_name,
            cost=cost
        )

    def extract_structured_data(
        self,
        image_paths: List[str],
        schema: Dict[str, Any]
    ) -> LLMResult:
        """
        구조화 데이터 추출 (계약서, 청구서 등)

        Args:
            image_paths: 이미지 파일 경로 리스트
            schema: 추출할 데이터 스키마

        Returns:
            LLMResult 객체 (JSON 형식)
        """
        prompt = f"""
Extract the following information from the document:

Schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

Return the result as a valid JSON matching the schema.
If a field is not found, use null.
Ensure the output is valid JSON format.
"""

        result = self.process_image(image_paths, prompt)

        # JSON 파싱 시도
        try:
            # JSON 블록 추출 (```json ... ``` 형식 처리)
            text = result.text.strip()
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()

            parsed_data = json.loads(text)
            result.metadata["parsed_data"] = parsed_data
            result.metadata["parsing_success"] = True
        except json.JSONDecodeError as e:
            result.metadata["parsing_success"] = False
            result.metadata["parsing_error"] = str(e)

        return result

    def process_pdf(
        self,
        pdf_path: str,
        prompt: str,
        max_pages: int = 1500
    ) -> LLMResult:
        """
        PDF 파일 처리 (최대 1,500페이지)

        Args:
            pdf_path: PDF 파일 경로
            prompt: 처리 지시사항
            max_pages: 최대 페이지 수

        Returns:
            LLMResult 객체
        """
        from pdf2image import convert_from_path
        import tempfile
        import os

        # PDF를 이미지로 변환
        images = convert_from_path(
            pdf_path,
            first_page=1,
            last_page=min(max_pages, 1500)
        )

        # 임시 파일로 저장
        temp_dir = tempfile.mkdtemp()
        image_paths = []

        try:
            for i, img in enumerate(images):
                temp_path = os.path.join(temp_dir, f"page_{i+1}.jpg")
                img.save(temp_path, 'JPEG', quality=85)
                image_paths.append(temp_path)

            # Gemini로 처리
            result = self.process_image(image_paths, prompt)
            result.metadata["pdf_pages"] = len(images)

            return result

        finally:
            # 임시 파일 삭제
            for path in image_paths:
                if os.path.exists(path):
                    os.remove(path)
            os.rmdir(temp_dir)

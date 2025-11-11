"""
OpenAI GPT-5 엔진 (Nano, Mini, Standard)
"""

import os
import json
import base64
import time
from typing import Dict, Any, Optional, List
from .base import BaseLLMEngine, LLMResult, LLMEngineFactory


@LLMEngineFactory.register("gpt5_nano")
@LLMEngineFactory.register("gpt5_mini")
@LLMEngineFactory.register("gpt5")
class OpenAIGPT5Engine(BaseLLMEngine):
    """
    OpenAI GPT-5 엔진
    - gpt-5-nano: $0.05 입력/$0.40 출력 per 1M (최저가)
    - gpt-5-mini: $0.25 입력/$2 출력 per 1M
    - gpt-5: $1.25 입력/$10 출력 per 1M
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # OpenAI import
        try:
            from openai import OpenAI
            self.OpenAI = OpenAI
        except ImportError:
            raise ImportError(
                "openai is not installed. "
                "Install it with: pip install openai"
            )

        # API 키 설정
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in config or environment")

        self.client = self.OpenAI(api_key=api_key)

        # 모델 선택
        model_name = config.get("model", "gpt-5-nano") if config else "gpt-5-nano"
        self.model = model_name

        # 가격 설정 (per 1M tokens)
        pricing = {
            "gpt-5-nano": (0.05, 0.40),
            "gpt-5-mini": (0.25, 2.00),
            "gpt-5": (1.25, 10.00)
        }

        if model_name in pricing:
            self.config["input_price_per_million"] = pricing[model_name][0]
            self.config["output_price_per_million"] = pricing[model_name][1]
        else:
            # 기본값
            self.config["input_price_per_million"] = 0.05
            self.config["output_price_per_million"] = 0.40

    def process_text(self, text: str, prompt: str, **kwargs) -> LLMResult:
        """
        텍스트 처리

        Args:
            text: 입력 텍스트
            prompt: 처리 지시사항
            **kwargs: temperature, response_format 등 추가 옵션

        Returns:
            LLMResult 객체
        """
        start_time = time.time()

        # 메시지 구성
        messages = [
            {"role": "system", "content": "You are a document analysis expert."},
            {"role": "user", "content": f"{prompt}\n\n{text}"}
        ]

        # API 호출 설정
        api_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        # JSON 모드 (선택적)
        if kwargs.get("response_format") == "json":
            api_kwargs["response_format"] = {"type": "json_object"}

        # API 호출
        response = self.client.chat.completions.create(**api_kwargs)

        # 토큰 사용량
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        # 비용 계산
        cost = self.calculate_cost(usage["input_tokens"], usage["output_tokens"])

        return LLMResult(
            text=response.choices[0].message.content,
            usage=usage,
            metadata={
                "model": self.model,
                "finish_reason": response.choices[0].finish_reason
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
            image_paths: 이미지 파일 경로 리스트
            prompt: 처리 지시사항
            **kwargs: temperature 등 추가 옵션

        Returns:
            LLMResult 객체
        """
        start_time = time.time()

        # 이미지를 base64로 인코딩
        image_contents = []
        for image_path in image_paths:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}",
                        "detail": kwargs.get("detail", "auto")  # low, high, auto
                    }
                })

        # 메시지 구성
        content = [{"type": "text", "text": prompt}] + image_contents

        messages = [
            {"role": "user", "content": content}
        ]

        # API 호출
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.3),
            max_tokens=kwargs.get("max_tokens", 4096),
        )

        # 토큰 사용량
        usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        # 비용 계산
        cost = self.calculate_cost(usage["input_tokens"], usage["output_tokens"])

        return LLMResult(
            text=response.choices[0].message.content,
            usage=usage,
            metadata={
                "model": self.model,
                "image_count": len(image_paths)
            },
            processing_time=time.time() - start_time,
            engine=self.engine_name,
            cost=cost
        )

    def extract_structured_json(
        self,
        text: str,
        schema: Dict[str, Any]
    ) -> LLMResult:
        """
        JSON 형식으로 구조화 데이터 추출

        Args:
            text: 입력 텍스트
            schema: 추출할 데이터 스키마

        Returns:
            LLMResult 객체 (JSON 파싱 포함)
        """
        prompt = f"""
Extract information according to the schema and return valid JSON only.

Schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

Document:
{text}
"""

        result = self.process_text(
            "",
            prompt,
            response_format="json"
        )

        # JSON 파싱
        try:
            parsed_data = json.loads(result.text)
            result.metadata["parsed_data"] = parsed_data
            result.metadata["parsing_success"] = True
        except json.JSONDecodeError as e:
            result.metadata["parsing_success"] = False
            result.metadata["parsing_error"] = str(e)

        return result

    def analyze_document(
        self,
        text: str,
        task: str = "summarize"
    ) -> LLMResult:
        """
        문서 분석 (요약, 분류, 개체 추출, 감정 분석)

        Args:
            text: 문서 텍스트
            task: 분석 작업 (summarize, classify, extract_entities, sentiment)

        Returns:
            LLMResult 객체
        """
        prompts = {
            "summarize": "다음 문서를 3-5문장으로 요약하세요:",
            "classify": "다음 문서의 유형을 분류하세요 (계약서, 청구서, 보고서, 이메일, 기타):",
            "extract_entities": """다음 문서에서 중요 정보를 추출하세요:
- 인물 (이름, 직책)
- 조직 (회사명, 부서)
- 날짜 (계약일, 만료일 등)
- 금액 (계약금, 총액 등)
- 위치 (주소, 장소)

JSON 형식으로 반환하세요.""",
            "sentiment": "다음 문서의 감정을 분석하세요 (긍정, 부정, 중립):"
        }

        prompt = prompts.get(task, task)

        # JSON 형식이 필요한 경우
        response_format = "json" if task == "extract_entities" else None

        return self.process_text(
            text,
            prompt,
            response_format=response_format
        )

"""
OpenAI LLM 엔진 구현 모듈

주요 기능:
1. OpenAI API 연동
2. 다양한 모델 지원 (GPT-3.5, GPT-4 등)
3. 토큰 사용량 추적
"""

import os
import json
import time
from typing import Dict, Any, Optional, List, Union
import requests

from shared.logger import log_info, log_error
from shared.exceptions import LLMAPIError
from llm_processors.base import BaseLLMEngine, LLMResult, LLMEngineFactory


@LLMEngineFactory.register("openai")
class OpenAIEngine(BaseLLMEngine):
    """OpenAI LLM 엔진 구현 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        OpenAI 엔진 초기화
        
        Args:
            config: 엔진 설정
        """
        super().__init__(config)
        
        # 기본 설정
        self.api_key = self.config.get("api_key")
        self.default_model = self.config.get("model", "gpt-3.5-turbo")
        self.api_base = self.config.get("api_base", "https://api.openai.com/v1")
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)
        
        # API 키 검증
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            raise LLMAPIError(
                message="OpenAI API 키가 설정되지 않았습니다.",
                details={"engine": "openai"}
            )
    
    def generate(self, prompt: str, **kwargs) -> LLMResult:
        """
        텍스트 생성
        
        Args:
            prompt: 프롬프트 텍스트
            **kwargs: 추가 파라미터
            
        Returns:
            LLMResult: LLM 결과
            
        Raises:
            LLMAPIError: API 호출 중 오류 발생 시
        """
        # 파라미터 설정
        model = kwargs.get("model", self.default_model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        top_p = kwargs.get("top_p", 1.0)
        frequency_penalty = kwargs.get("frequency_penalty", 0.0)
        presence_penalty = kwargs.get("presence_penalty", 0.0)
        
        # API 요청 데이터
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 모델에 따라 요청 형식 변경
        if "gpt" in model.lower():
            # Chat Completion API
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty
            }
            endpoint = f"{self.api_base}/chat/completions"
        else:
            # Completion API (레거시)
            data = {
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty
            }
            endpoint = f"{self.api_base}/completions"
        
        # API 호출
        for attempt in range(self.max_retries):
            try:
                response = requests.post(endpoint, headers=headers, json=data, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                
                # 응답 파싱
                if "gpt" in model.lower():
                    # Chat Completion API 응답
                    text = result["choices"][0]["message"]["content"]
                else:
                    # Completion API 응답
                    text = result["choices"][0]["text"]
                
                # 토큰 사용량
                tokens = {
                    "prompt_tokens": result["usage"]["prompt_tokens"],
                    "completion_tokens": result["usage"]["completion_tokens"],
                    "total_tokens": result["usage"]["total_tokens"]
                }
                
                # 메타데이터
                metadata = {
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "finish_reason": result["choices"][0].get("finish_reason")
                }
                
                return LLMResult(
                    text=text,
                    model=model,
                    tokens=tokens,
                    metadata=metadata
                )
            
            except requests.exceptions.RequestException as e:
                log_error(f"OpenAI API 호출 실패 (시도 {attempt+1}/{self.max_retries}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # 지수 백오프
                else:
                    raise LLMAPIError(
                        message=f"OpenAI API 호출 실패: {str(e)}",
                        details={"model": model, "error": str(e)}
                    )
    
    def get_available_models(self) -> List[str]:
        """
        사용 가능한 모델 목록 조회
        
        Returns:
            List[str]: 모델 이름 목록
            
        Raises:
            LLMAPIError: API 호출 중 오류 발생 시
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.get(f"{self.api_base}/models", headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            models = [model["id"] for model in result["data"]]
            
            # GPT 모델 필터링
            gpt_models = [model for model in models if "gpt" in model.lower()]
            
            return gpt_models
        
        except requests.exceptions.RequestException as e:
            log_error(f"OpenAI 모델 목록 조회 실패: {str(e)}")
            raise LLMAPIError(
                message=f"OpenAI 모델 목록 조회 실패: {str(e)}",
                details={"error": str(e)}
            )

"""
로컬 LLM 엔진 구현 모듈 (Ollama)

주요 기능:
1. Ollama API 연동
2. 로컬 LLM 모델 지원 (Llama, Mistral 등)
3. 경량화된 추론 제공
"""

import os
import json
import time
from typing import Dict, Any, Optional, List, Union
import requests

from shared.logger import log_info, log_error
from shared.exceptions import LLMAPIError
from llm_processors.base import BaseLLMEngine, LLMResult, LLMEngineFactory


@LLMEngineFactory.register("ollama")
class OllamaEngine(BaseLLMEngine):
    """Ollama LLM 엔진 구현 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Ollama 엔진 초기화
        
        Args:
            config: 엔진 설정
        """
        super().__init__(config)
        
        # 기본 설정
        self.api_base = self.config.get("api_base", "http://localhost:11434/api")
        self.default_model = self.config.get("model", "llama2")
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)
        
        # 연결 테스트
        self._test_connection()
    
    def _test_connection(self) -> None:
        """
        Ollama 연결 테스트
        
        Raises:
            LLMAPIError: 연결 실패 시
        """
        try:
            response = requests.get(f"{self.api_base}/tags", timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            log_error(f"Ollama 연결 테스트 실패: {str(e)}")
            raise LLMAPIError(
                message="Ollama 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.",
                details={"api_base": self.api_base, "error": str(e)}
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
        top_p = kwargs.get("top_p", 0.9)
        
        # API 요청 데이터
        data = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": top_p,
            "stream": False
        }
        
        # API 호출
        for attempt in range(self.max_retries):
            try:
                response = requests.post(f"{self.api_base}/generate", json=data, timeout=120)
                response.raise_for_status()
                
                result = response.json()
                
                # 응답 파싱
                text = result.get("response", "")
                
                # 토큰 사용량 (Ollama는 제한적인 정보 제공)
                tokens = {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                }
                
                # 메타데이터
                metadata = {
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                return LLMResult(
                    text=text,
                    model=model,
                    tokens=tokens,
                    metadata=metadata
                )
            
            except requests.exceptions.RequestException as e:
                log_error(f"Ollama API 호출 실패 (시도 {attempt+1}/{self.max_retries}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # 지수 백오프
                else:
                    raise LLMAPIError(
                        message=f"Ollama API 호출 실패: {str(e)}",
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
        try:
            response = requests.get(f"{self.api_base}/tags", timeout=30)
            response.raise_for_status()
            
            result = response.json()
            models = [model["name"] for model in result.get("models", [])]
            
            return models
        
        except requests.exceptions.RequestException as e:
            log_error(f"Ollama 모델 목록 조회 실패: {str(e)}")
            raise LLMAPIError(
                message=f"Ollama 모델 목록 조회 실패: {str(e)}",
                details={"error": str(e)}
            )

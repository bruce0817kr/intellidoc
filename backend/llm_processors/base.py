"""
LLM 엔진 추상화 모듈

주요 기능:
1. LLM 엔진 인터페이스 정의
2. 다양한 LLM 엔진 구현체 지원
3. 프롬프트 관리 및 결과 표준화
"""

import abc
from typing import Dict, Any, Optional, List, Union
import uuid
import os
import json
from pathlib import Path

from shared.config import settings
from shared.exceptions import LLMAPIError


class LLMResult:
    """LLM 결과 클래스"""
    
    def __init__(
        self,
        text: str,
        model: str,
        tokens: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        LLM 결과 초기화
        
        Args:
            text: 생성된 텍스트
            model: 사용된 모델명
            tokens: 토큰 사용량 정보
            metadata: 추가 메타데이터
        """
        self.text = text
        self.model = model
        self.tokens = tokens or {}
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 딕셔너리 형태의 LLM 결과
        """
        return {
            "text": self.text,
            "model": self.model,
            "tokens": self.tokens,
            "metadata": self.metadata
        }


class BaseLLMEngine(abc.ABC):
    """LLM 엔진 기본 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        LLM 엔진 초기화
        
        Args:
            config: 엔진 설정
        """
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abc.abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResult:
        """
        텍스트 생성
        
        Args:
            prompt: 프롬프트 텍스트
            **kwargs: 추가 파라미터
            
        Returns:
            LLMResult: LLM 결과
        """
        pass
    
    @abc.abstractmethod
    def get_available_models(self) -> List[str]:
        """
        사용 가능한 모델 목록 조회
        
        Returns:
            List[str]: 모델 이름 목록
        """
        pass
    
    def format_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """
        프롬프트 템플릿 포맷팅
        
        Args:
            template: 프롬프트 템플릿
            variables: 변수 딕셔너리
            
        Returns:
            str: 포맷팅된 프롬프트
        """
        try:
            return template.format(**variables)
        except KeyError as e:
            raise LLMAPIError(
                message=f"프롬프트 템플릿 포맷팅 실패: 누락된 변수 {e}",
                details={"template": template, "variables": variables}
            )
    
    def validate_api_key(self) -> bool:
        """
        API 키 유효성 검사
        
        Returns:
            bool: 유효한 API 키인 경우 True
            
        Raises:
            LLMAPIError: API 키가 유효하지 않은 경우
        """
        api_key = self.config.get("api_key")
        if not api_key:
            raise LLMAPIError(
                message="API 키가 설정되지 않았습니다.",
                details={"engine": self.name}
            )
        
        return True


class LLMEngineFactory:
    """LLM 엔진 팩토리 클래스"""
    
    _engines: Dict[str, type] = {}
    
    @classmethod
    def register(cls, engine_name: str) -> callable:
        """
        LLM 엔진 등록 데코레이터
        
        Args:
            engine_name: 엔진 이름
            
        Returns:
            callable: 데코레이터 함수
        """
        def decorator(engine_class: type) -> type:
            cls._engines[engine_name] = engine_class
            return engine_class
        return decorator
    
    @classmethod
    def create(cls, engine_name: str, config: Optional[Dict[str, Any]] = None) -> BaseLLMEngine:
        """
        LLM 엔진 생성
        
        Args:
            engine_name: 엔진 이름
            config: 엔진 설정
            
        Returns:
            BaseLLMEngine: LLM 엔진 인스턴스
            
        Raises:
            LLMAPIError: 지원하지 않는 엔진인 경우
        """
        if engine_name not in cls._engines:
            raise LLMAPIError(message=f"지원하지 않는 LLM 엔진입니다: {engine_name}")
        
        engine_class = cls._engines[engine_name]
        return engine_class(config)
    
    @classmethod
    def get_available_engines(cls) -> List[str]:
        """
        사용 가능한 LLM 엔진 목록 조회
        
        Returns:
            List[str]: 엔진 이름 목록
        """
        return list(cls._engines.keys())


class PromptTemplate:
    """프롬프트 템플릿 클래스"""
    
    def __init__(
        self,
        template: str,
        variables: List[str],
        name: Optional[str] = None,
        description: Optional[str] = None
    ):
        """
        프롬프트 템플릿 초기화
        
        Args:
            template: 프롬프트 템플릿 문자열
            variables: 변수 이름 목록
            name: 템플릿 이름
            description: 템플릿 설명
        """
        self.template = template
        self.variables = variables
        self.name = name or "unnamed_template"
        self.description = description or ""
    
    def format(self, **kwargs) -> str:
        """
        프롬프트 템플릿 포맷팅
        
        Args:
            **kwargs: 변수 값
            
        Returns:
            str: 포맷팅된 프롬프트
            
        Raises:
            LLMAPIError: 필수 변수가 누락된 경우
        """
        # 필수 변수 확인
        missing_vars = [var for var in self.variables if var not in kwargs]
        if missing_vars:
            raise LLMAPIError(
                message=f"프롬프트 템플릿 포맷팅 실패: 누락된 변수 {missing_vars}",
                details={"template": self.name, "missing_variables": missing_vars}
            )
        
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise LLMAPIError(
                message=f"프롬프트 템플릿 포맷팅 실패: 변수 오류 {e}",
                details={"template": self.name}
            )
        except Exception as e:
            raise LLMAPIError(
                message=f"프롬프트 템플릿 포맷팅 실패: {str(e)}",
                details={"template": self.name}
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        딕셔너리로 변환
        
        Returns:
            Dict[str, Any]: 딕셔너리 형태의 템플릿
        """
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "variables": self.variables
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """
        딕셔너리에서 템플릿 생성
        
        Args:
            data: 템플릿 데이터
            
        Returns:
            PromptTemplate: 생성된 템플릿
        """
        return cls(
            template=data["template"],
            variables=data["variables"],
            name=data.get("name"),
            description=data.get("description")
        )


class PromptManager:
    """프롬프트 관리 클래스"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        프롬프트 관리자 초기화
        
        Args:
            templates_dir: 템플릿 디렉토리 경로
        """
        self.templates_dir = templates_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates"
        )
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """템플릿 로드"""
        os.makedirs(self.templates_dir, exist_ok=True)
        
        for file_path in Path(self.templates_dir).glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                template = PromptTemplate.from_dict(data)
                self.templates[template.name] = template
            except Exception as e:
                print(f"템플릿 로드 실패: {file_path}, 오류: {str(e)}")
    
    def get_template(self, name: str) -> PromptTemplate:
        """
        템플릿 조회
        
        Args:
            name: 템플릿 이름
            
        Returns:
            PromptTemplate: 템플릿
            
        Raises:
            LLMAPIError: 템플릿을 찾을 수 없는 경우
        """
        if name not in self.templates:
            raise LLMAPIError(
                message=f"프롬프트 템플릿을 찾을 수 없습니다: {name}",
                details={"available_templates": list(self.templates.keys())}
            )
        
        return self.templates[name]
    
    def add_template(self, template: PromptTemplate) -> None:
        """
        템플릿 추가
        
        Args:
            template: 추가할 템플릿
        """
        self.templates[template.name] = template
        
        # 파일로 저장
        os.makedirs(self.templates_dir, exist_ok=True)
        file_path = os.path.join(self.templates_dir, f"{template.name}.json")
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
    
    def remove_template(self, name: str) -> None:
        """
        템플릿 삭제
        
        Args:
            name: 삭제할 템플릿 이름
            
        Raises:
            LLMAPIError: 템플릿을 찾을 수 없는 경우
        """
        if name not in self.templates:
            raise LLMAPIError(
                message=f"프롬프트 템플릿을 찾을 수 없습니다: {name}",
                details={"available_templates": list(self.templates.keys())}
            )
        
        del self.templates[name]
        
        # 파일 삭제
        file_path = os.path.join(self.templates_dir, f"{name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
    
    def get_all_templates(self) -> Dict[str, PromptTemplate]:
        """
        모든 템플릿 조회
        
        Returns:
            Dict[str, PromptTemplate]: 템플릿 딕셔너리
        """
        return self.templates

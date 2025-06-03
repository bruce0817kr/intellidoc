"""
Mistral OCR API 엔진 구현 모듈

주요 기능:
1. Mistral OCR API 연동
2. 이미지/문서 텍스트 추출
3. 구조화된 데이터 추출
"""

import os
import base64
import tempfile
from typing import Dict, Any, Optional, List
import requests
from PIL import Image
import pdf2image

from shared.logger import log_info, log_error
from shared.exceptions import OCREngineError
from ocr_engines.base import BaseOCREngine, OCRResult, OCREngineFactory


@OCREngineFactory.register("mistral_ocr")
class MistralOCREngine(BaseOCREngine):
    """Mistral OCR API 엔진 구현 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Mistral OCR 엔진 초기화
        
        Args:
            config: 엔진 설정
        """
        super().__init__(config)
        
        # API 설정
        self.api_key = self.config.get("api_key") or os.getenv("MISTRAL_API_KEY")
        self.api_url = self.config.get("api_url", "https://api.mistral.ai/v1/chat/completions")
        self.model = self.config.get("model", "pixtral-12b-2409")
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.temperature = self.config.get("temperature", 0.1)
        
        # API 키 확인
        if not self.api_key:
            raise OCREngineError(
                message="Mistral API 키가 설정되지 않았습니다. MISTRAL_API_KEY 환경변수를 설정하거나 config에 api_key를 포함하세요."
            )
        
        # HTTP 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        # 요청 설정
        self.timeout = self.config.get("timeout", 60)
        self.max_retries = self.config.get("max_retries", 3)
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        이미지를 base64로 인코딩
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            str: base64 인코딩된 이미지 데이터
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            log_error(f"이미지 base64 인코딩 실패: {str(e)}")
            raise OCREngineError(
                message=f"이미지 인코딩 중 오류가 발생했습니다: {str(e)}",
                details={"image_path": image_path}
            )
    
    def _get_image_mime_type(self, image_path: str) -> str:
        """
        이미지 MIME 타입 추출
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            str: MIME 타입
        """
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff'
        }
        return mime_types.get(ext, 'image/jpeg')
    
    def _call_mistral_api(self, base64_image: str, mime_type: str) -> Dict[str, Any]:
        """
        Mistral API 호출
        
        Args:
            base64_image: base64 인코딩된 이미지
            mime_type: 이미지 MIME 타입
            
        Returns:
            Dict[str, Any]: API 응답
        """
        # 시스템 프롬프트 - OCR 작업 지시
        system_prompt = """
        당신은 고정밀 OCR 전문가입니다. 주어진 이미지에서 텍스트를 추출하고 다음 JSON 형식으로 결과를 반환하세요:

        {
            "extracted_text": "추출된 전체 텍스트",
            "confidence": 0.95,
            "structured_data": {
                "title": "문서 제목",
                "content": "주요 내용",
                "dates": ["2024-01-01"],
                "amounts": [{"currency": "KRW", "value": 100000}],
                "names": ["홍길동"],
                "addresses": ["서울시 강남구"],
                "phones": ["010-1234-5678"],
                "emails": ["test@example.com"]
            },
            "layout": {
                "text_blocks": [
                    {
                        "text": "텍스트 블록",
                        "x": 100,
                        "y": 200,
                        "width": 300,
                        "height": 50,
                        "confidence": 0.98
                    }
                ]
            }
        }

        다음 규칙을 따르세요:
        1. 모든 텍스트를 정확하게 추출하세요
        2. 한글, 영어, 숫자를 모두 인식하세요
        3. 날짜, 금액, 이름, 주소, 전화번호, 이메일 등을 구조화하세요
        4. 신뢰도는 0.0~1.0 범위로 설정하세요
        5. JSON 형식을 정확히 지켜주세요
        """
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "이 이미지에서 텍스트를 추출하고 구조화해주세요."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        for attempt in range(self.max_retries):
            try:
                log_info(f"Mistral OCR API 호출 시도 {attempt + 1}/{self.max_retries}")
                
                response = self.session.post(
                    self.api_url,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit - 잠시 대기 후 재시도
                    import time
                    wait_time = 2 ** attempt
                    log_info(f"Rate limit 도달, {wait_time}초 대기 후 재시도")
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.Timeout:
                log_error(f"API 호출 타임아웃 (시도 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise OCREngineError(
                        message="Mistral API 호출 시간이 초과되었습니다.",
                        details={"timeout": self.timeout}
                    )
            except requests.exceptions.RequestException as e:
                log_error(f"API 호출 실패: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise OCREngineError(
                        message=f"Mistral API 호출 중 오류가 발생했습니다: {str(e)}",
                        details={"error": str(e)}
                    )
        
        raise OCREngineError(message="모든 재시도 횟수를 초과했습니다.")
    
    def _parse_api_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 응답 파싱
        
        Args:
            response: API 응답
            
        Returns:
            Dict[str, Any]: 파싱된 OCR 결과
        """
        try:
            # 응답에서 content 추출
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # JSON 파싱
            import json
            
            # JSON 블록 추출 (```json으로 둘러싸인 경우)
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                json_str = content[start:end].strip()
            else:
                json_str = content.strip()
            
            # JSON 파싱 시도
            try:
                parsed_result = json.loads(json_str)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값 반환
                log_error(f"JSON 파싱 실패, 원본 텍스트 사용: {content[:200]}...")
                parsed_result = {
                    "extracted_text": content,
                    "confidence": 0.8,
                    "structured_data": {},
                    "layout": {"text_blocks": []}
                }
            
            return parsed_result
            
        except Exception as e:
            log_error(f"API 응답 파싱 실패: {str(e)}")
            raise OCREngineError(
                message=f"API 응답 파싱 중 오류가 발생했습니다: {str(e)}",
                details={"response": str(response)[:500]}
            )
    
    def process_image(self, image_path: str) -> OCRResult:
        """
        이미지 처리
        
        Args:
            image_path: 처리할 이미지 경로
            
        Returns:
            OCRResult: OCR 결과
        """
        self.validate_file(image_path)
        
        try:
            log_info(f"Mistral OCR 이미지 처리 시작: {image_path}")
            
            # 이미지 인코딩
            base64_image = self._encode_image_to_base64(image_path)
            mime_type = self._get_image_mime_type(image_path)
            
            # API 호출
            response = self._call_mistral_api(base64_image, mime_type)
            
            # 응답 파싱
            parsed_result = self._parse_api_response(response)
            
            # OCRResult 생성
            text = parsed_result.get("extracted_text", "")
            confidence = parsed_result.get("confidence", 0.0)
            layout = parsed_result.get("layout", {})
            
            # 바운딩 박스 추출
            bounding_boxes = []
            for block in layout.get("text_blocks", []):
                bounding_boxes.append({
                    "text": block.get("text", ""),
                    "confidence": block.get("confidence", confidence),
                    "x": block.get("x", 0),
                    "y": block.get("y", 0),
                    "width": block.get("width", 0),
                    "height": block.get("height", 0)
                })
            
            log_info(f"Mistral OCR 처리 완료: 신뢰도 {confidence:.2f}")
            
            return OCRResult(
                text=text,
                confidence=confidence,
                page_number=1,
                bounding_boxes=bounding_boxes,
                metadata={
                    "engine": "mistral_ocr",
                    "model": self.model,
                    "structured_data": parsed_result.get("structured_data", {}),
                    "api_response": response.get("usage", {})
                }
            )
            
        except Exception as e:
            log_error(f"Mistral OCR 이미지 처리 실패: {str(e)}", exc_info=True)
            if isinstance(e, OCREngineError):
                raise e
            else:
                raise OCREngineError(
                    message=f"이미지 OCR 처리 중 오류가 발생했습니다: {str(e)}",
                    details={"image_path": image_path}
                )
    
    def _convert_pdf_to_images(self, pdf_path: str, temp_dir: str) -> List[str]:
        """
        PDF를 이미지로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            temp_dir: 임시 디렉토리 경로
            
        Returns:
            List[str]: 이미지 파일 경로 목록
        """
        try:
            # PDF를 이미지로 변환
            dpi = self.config.get("dpi", 300)
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=dpi,
                output_folder=temp_dir,
                fmt="png"
            )
            
            # 이미지 파일 경로 목록 생성
            image_paths = []
            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f"page_{i+1}.png")
                image.save(image_path, "PNG")
                image_paths.append(image_path)
            
            return image_paths
            
        except Exception as e:
            log_error(f"PDF 이미지 변환 실패: {str(e)}", exc_info=True)
            raise OCREngineError(
                message=f"PDF를 이미지로 변환하는 중 오류가 발생했습니다: {str(e)}",
                details={"pdf_path": pdf_path}
            )
    
    def process_file(self, file_path: str) -> List[OCRResult]:
        """
        파일 처리
        
        Args:
            file_path: 처리할 파일 경로
            
        Returns:
            List[OCRResult]: OCR 결과 목록
        """
        self.validate_file(file_path)
        
        # 파일 확장자 확인
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 임시 디렉토리 생성
        temp_dir = self.get_temp_dir()
        
        try:
            # PDF 파일 처리
            if file_ext == '.pdf':
                # PDF를 이미지로 변환
                image_paths = self._convert_pdf_to_images(file_path, temp_dir)
                
                # 각 이미지 처리
                results = []
                for i, image_path in enumerate(image_paths):
                    result = self.process_image(image_path)
                    result.page_number = i + 1
                    results.append(result)
                
                return results
            
            # 이미지 파일 처리
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']:
                result = self.process_image(file_path)
                return [result]
            
            # 지원하지 않는 파일 형식
            else:
                raise OCREngineError(
                    message=f"지원하지 않는 파일 형식입니다: {file_ext}",
                    details={"file_path": file_path}
                )
        
        finally:
            # 임시 디렉토리 정리
            self.cleanup_temp_dir(temp_dir)

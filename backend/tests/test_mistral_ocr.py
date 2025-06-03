"""
Mistral OCR 엔진 테스트 모듈

주요 테스트:
1. Mistral OCR 엔진 초기화
2. 이미지 처리 테스트
3. PDF 처리 테스트
4. API 호출 테스트
5. 오류 처리 테스트
"""

import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json
import requests
import base64
import tempfile
from datetime import datetime

# 테스트 대상 모듈 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 테스트 대상 모듈 임포트
from ocr_engines.mistral_ocr import MistralOCREngine
from ocr_engines.base import OCRResult
from shared.exceptions import OCREngineError


class TestMistralOCREngine(unittest.TestCase):
    """Mistral OCR 엔진 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        # 기본 설정
        self.config = {
            "api_key": "test-mistral-api-key",
            "api_url": "https://api.mistral.ai/v1/chat/completions",
            "model": "pixtral-12b-2409",
            "max_tokens": 4096,
            "temperature": 0.1,
            "timeout": 60,
            "max_retries": 3
        }
        
        # 환경 변수 모의 설정
        self.env_patcher = patch.dict(os.environ, {
            'MISTRAL_API_KEY': 'test-mistral-api-key'
        })
        self.env_patcher.start()
        
        # 모의 API 응답
        self.mock_api_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "extracted_text": "테스트 문서 내용입니다.",
                            "confidence": 0.95,
                            "structured_data": {
                                "title": "테스트 문서",
                                "content": "주요 내용",
                                "dates": ["2024-01-01"],
                                "amounts": [{"currency": "KRW", "value": 100000}]
                            },
                            "layout": {
                                "text_blocks": [
                                    {
                                        "text": "테스트 문서",
                                        "x": 100,
                                        "y": 50,
                                        "width": 200,
                                        "height": 30,
                                        "confidence": 0.98
                                    }
                                ]
                            }
                        })
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300
            }
        }

    def tearDown(self):
        """테스트 정리"""
        self.env_patcher.stop()

    def test_init_with_config(self):
        """설정을 통한 엔진 초기화 테스트"""
        engine = MistralOCREngine(self.config)
        
        self.assertEqual(engine.api_key, "test-mistral-api-key")
        self.assertEqual(engine.model, "pixtral-12b-2409")
        self.assertEqual(engine.max_tokens, 4096)
        self.assertEqual(engine.temperature, 0.1)

    def test_init_with_env_var(self):
        """환경변수를 통한 엔진 초기화 테스트"""
        engine = MistralOCREngine()
        
        self.assertEqual(engine.api_key, "test-mistral-api-key")
        self.assertIsNotNone(engine.session)

    def test_init_without_api_key(self):
        """API 키 없이 초기화 시 오류 테스트"""
        # 환경변수 제거
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(OCREngineError) as context:
                MistralOCREngine()
            
            self.assertIn("API 키가 설정되지 않았습니다", str(context.exception))

    @patch('ocr_engines.mistral_ocr.Image.open')
    def test_encode_image_to_base64(self, mock_image_open):
        """이미지 base64 인코딩 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 모의 이미지 데이터
        test_image_data = b"fake_image_data"
        
        with patch('builtins.open', mock_open(read_data=test_image_data)):
            result = engine._encode_image_to_base64("test_image.jpg")
            
            expected = base64.b64encode(test_image_data).decode('utf-8')
            self.assertEqual(result, expected)

    def test_get_image_mime_type(self):
        """이미지 MIME 타입 확인 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 다양한 이미지 형식 테스트
        test_cases = [
            ("test.jpg", "image/jpeg"),
            ("test.jpeg", "image/jpeg"),
            ("test.png", "image/png"),
            ("test.tiff", "image/tiff"),
            ("test.bmp", "image/bmp"),
            ("test.gif", "image/gif")
        ]
        
        for filename, expected_mime in test_cases:
            with self.subTest(filename=filename):
                result = engine._get_image_mime_type(filename)
                self.assertEqual(result, expected_mime)

    @patch('requests.Session.post')
    def test_call_mistral_api_success(self, mock_post):
        """Mistral API 호출 성공 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 모의 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_api_response
        mock_post.return_value = mock_response
        
        # API 호출
        base64_image = "test_base64_image"
        mime_type = "image/jpeg"
        result = engine._call_mistral_api(base64_image, mime_type)
        
        # 검증
        self.assertEqual(result, self.mock_api_response)
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_call_mistral_api_rate_limit(self, mock_post):
        """API Rate Limit 처리 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 첫 번째 호출은 429 (Rate Limit), 두 번째는 성공
        responses = [
            MagicMock(status_code=429),
            MagicMock(status_code=200)
        ]
        responses[1].json.return_value = self.mock_api_response
        mock_post.side_effect = responses
        
        with patch('time.sleep'):  # sleep 모의
            result = engine._call_mistral_api("test_image", "image/jpeg")
            
        self.assertEqual(result, self.mock_api_response)
        self.assertEqual(mock_post.call_count, 2)

    @patch('requests.Session.post')
    def test_call_mistral_api_timeout(self, mock_post):
        """API 타임아웃 처리 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 타임아웃 예외 발생
        mock_post.side_effect = [
            requests.exceptions.Timeout("Request timeout"),
            requests.exceptions.Timeout("Request timeout"),
            requests.exceptions.Timeout("Request timeout")
        ]
        
        with self.assertRaises(OCREngineError) as context:
            engine._call_mistral_api("test_image", "image/jpeg")
        
        self.assertIn("시간이 초과되었습니다", str(context.exception))

    def test_parse_api_response_success(self):
        """API 응답 파싱 성공 테스트"""
        engine = MistralOCREngine(self.config)
        
        result = engine._parse_api_response(self.mock_api_response)
        
        self.assertEqual(result["extracted_text"], "테스트 문서 내용입니다.")
        self.assertEqual(result["confidence"], 0.95)
        self.assertIn("structured_data", result)
        self.assertIn("layout", result)

    def test_parse_api_response_json_block(self):
        """JSON 블록이 포함된 응답 파싱 테스트"""
        engine = MistralOCREngine(self.config)
        
        # JSON 블록으로 둘러싸인 응답
        json_content = {
            "extracted_text": "블록 테스트",
            "confidence": 0.9
        }
        
        response_with_json_block = {
            "choices": [
                {
                    "message": {
                        "content": f"```json\n{json.dumps(json_content)}\n```"
                    }
                }
            ]
        }
        
        result = engine._parse_api_response(response_with_json_block)
        
        self.assertEqual(result["extracted_text"], "블록 테스트")
        self.assertEqual(result["confidence"], 0.9)

    def test_parse_api_response_invalid_json(self):
        """잘못된 JSON 응답 파싱 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 잘못된 JSON 응답
        invalid_response = {
            "choices": [
                {
                    "message": {
                        "content": "이것은 유효하지 않은 JSON입니다 { invalid }"
                    }
                }
            ]
        }
        
        result = engine._parse_api_response(invalid_response)
        
        # 기본값 반환 확인
        self.assertIn("extracted_text", result)
        self.assertEqual(result["confidence"], 0.8)

    @patch('ocr_engines.mistral_ocr.MistralOCREngine._call_mistral_api')
    @patch('ocr_engines.mistral_ocr.MistralOCREngine._encode_image_to_base64')
    @patch('ocr_engines.mistral_ocr.MistralOCREngine._get_image_mime_type')
    @patch('ocr_engines.mistral_ocr.MistralOCREngine.validate_file')
    def test_process_image_success(self, mock_validate, mock_mime, mock_encode, mock_api):
        """이미지 처리 성공 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 모의 반환값 설정
        mock_encode.return_value = "test_base64"
        mock_mime.return_value = "image/jpeg"
        mock_api.return_value = self.mock_api_response
        
        # 이미지 처리
        result = engine.process_image("test_image.jpg")
        
        # 검증
        self.assertIsInstance(result, OCRResult)
        self.assertEqual(result.text, "테스트 문서 내용입니다.")
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.page_number, 1)
        self.assertIn("engine", result.metadata)

    @patch('pdf2image.convert_from_path')
    @patch('ocr_engines.mistral_ocr.MistralOCREngine.process_image')
    @patch('ocr_engines.mistral_ocr.MistralOCREngine.validate_file')
    def test_process_pdf_file(self, mock_validate, mock_process_image, mock_convert):
        """PDF 파일 처리 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 모의 PDF 이미지 생성
        mock_images = [MagicMock(), MagicMock()]
        mock_convert.return_value = mock_images
        
        # 모의 OCR 결과 생성
        mock_ocr_result = OCRResult(
            text="PDF 페이지 내용",
            confidence=0.9,
            page_number=1,
            bounding_boxes=[],
            metadata={}
        )
        mock_process_image.return_value = mock_ocr_result
        
        with patch('tempfile.mkdtemp') as mock_temp, \
             patch('os.path.join') as mock_join, \
             patch('shutil.rmtree') as mock_rmtree:
            
            mock_temp.return_value = "/tmp/test"
            mock_join.side_effect = lambda *args: "/".join(args)
            
            # PDF 처리
            results = engine.process_file("test.pdf")
            
            # 검증
            self.assertEqual(len(results), 2)  # 2페이지
            self.assertEqual(mock_process_image.call_count, 2)
            mock_rmtree.assert_called_once()

    @patch('ocr_engines.mistral_ocr.MistralOCREngine.process_image')
    @patch('ocr_engines.mistral_ocr.MistralOCREngine.validate_file')
    def test_process_image_file(self, mock_validate, mock_process_image):
        """이미지 파일 처리 테스트"""
        engine = MistralOCREngine(self.config)
        
        # 모의 OCR 결과 생성
        mock_ocr_result = OCRResult(
            text="이미지 내용",
            confidence=0.95,
            page_number=1,
            bounding_boxes=[],
            metadata={}
        )
        mock_process_image.return_value = mock_ocr_result
        
        # 이미지 파일 처리
        results = engine.process_file("test.jpg")
        
        # 검증
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text, "이미지 내용")
        mock_process_image.assert_called_once_with("test.jpg")

    @patch('ocr_engines.mistral_ocr.MistralOCREngine.validate_file')
    def test_process_unsupported_file(self, mock_validate):
        """지원하지 않는 파일 형식 테스트"""
        engine = MistralOCREngine(self.config)
        
        with self.assertRaises(OCREngineError) as context:
            engine.process_file("test.txt")
        
        self.assertIn("지원하지 않는 파일 형식", str(context.exception))

    @patch('pdf2image.convert_from_path')
    @patch('ocr_engines.mistral_ocr.MistralOCREngine.validate_file')
    def test_convert_pdf_to_images_error(self, mock_validate, mock_convert):
        """PDF 이미지 변환 오류 테스트"""
        engine = MistralOCREngine(self.config)
        
        # PDF 변환 오류 발생
        mock_convert.side_effect = Exception("PDF conversion failed")
        
        with patch('tempfile.mkdtemp'):
            with self.assertRaises(OCREngineError) as context:
                engine._convert_pdf_to_images("test.pdf", "/tmp/test")
            
            self.assertIn("PDF를 이미지로 변환하는 중 오류", str(context.exception))


if __name__ == '__main__':
    unittest.main()

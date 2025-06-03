import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import uuid
from datetime import datetime

# 테스트 대상 모듈 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 테스트 대상 모듈 임포트
from shared.models import Document, User, ExtractedData, ProcessingJob
from shared.constants import DocumentStatus, JobStatus
from shared.exceptions import ResourceNotFoundError, OCREngineError
from ocr_engines.service import OCRService
from file_manager.service import FileManager


class TestOCRService(unittest.TestCase):
    """OCR 서비스 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        # 모의 데이터베이스 세션 생성
        self.mock_db = MagicMock()
        
        # 모의 OCR 엔진 생성
        self.mock_ocr_engine = MagicMock()
        # OCRResult 객체들의 리스트를 반환하도록 수정
        self.mock_ocr_engine.process_file.return_value = [
            MagicMock(
                page_number=1,
                text='테스트 문서 내용',
                confidence=0.95,
                bounding_boxes=[]
            )
        ]
        
        # OCR 서비스 생성
        self.ocr_service = OCRService()
        # OCR 엔진과 후처리기를 모의로 교체
        self.ocr_service.engine = self.mock_ocr_engine
        self.ocr_service.postprocessor = MagicMock()
        self.ocr_service.postprocessor.process.return_value = {
            "text": "테스트 문서 내용",
            "structured_data": {},
            "page_count": 1,
            "confidence": 0.95
        }
        
        # 테스트 문서 ID
        self.test_document_id = uuid.uuid4()
        
        # 모의 문서 생성
        self.mock_document = MagicMock(spec=Document)
        self.mock_document.id = self.test_document_id
        self.mock_document.file_path = '/path/to/test/document.pdf'
        self.mock_document.status = 'PENDING'
        self.mock_document.page_count = 1
        
        # 모의 작업 생성
        self.mock_job = MagicMock(spec=ProcessingJob)
        self.mock_job.id = uuid.uuid4()
        self.mock_job.document_id = self.test_document_id
        self.mock_job.job_type = 'ocr'
        self.mock_job.status = 'PENDING'
        
        # 모의 파일 관리자 생성
        self.mock_file_manager = MagicMock()
        self.mock_file_manager.get_document_file_path.return_value = '/path/to/test/document.pdf'
        self.mock_file_manager.get_document_images.return_value = ['/path/to/test/page1.png', '/path/to/test/page2.png']

    def test_process_document_success(self):
        """문서 OCR 처리 성공 테스트"""
        # DB 쿼리 모킹 설정
        document_query = MagicMock()
        
        def mock_query_side_effect(model):
            if model == Document:
                return document_query
            return MagicMock()
        
        self.mock_db.query.side_effect = mock_query_side_effect
        document_query.filter.return_value.first.return_value = self.mock_document
        
        # 테스트 실행
        result = self.ocr_service.process_document(
            db=self.mock_db,
            document_id=self.test_document_id
        )
        
        # 검증
        self.assertEqual(result['document_id'], str(self.test_document_id))
        self.assertEqual(result['status'], 'success')
        self.assertTrue('job_id' in result)
        
        # 문서 상태 업데이트 확인
        self.assertEqual(self.mock_document.status, DocumentStatus.COMPLETED)
        
        # OCR 엔진 호출 확인
        self.mock_ocr_engine.process_file.assert_called()
        
        # 추출 데이터 저장 확인
        self.mock_db.add.assert_called()
        self.mock_db.commit.assert_called()

    def test_process_document_not_found(self):
        """존재하지 않는 문서 처리 테스트"""
        # DB 쿼리 모킹 - 문서를 찾을 수 없도록 설정
        document_query = MagicMock()
        
        def mock_query_side_effect(model):
            if model == Document:
                return document_query
            return MagicMock()
        
        self.mock_db.query.side_effect = mock_query_side_effect
        document_query.filter.return_value.first.return_value = None
        
        # 예외 발생 확인
        with self.assertRaises(ResourceNotFoundError):
            self.ocr_service.process_document(
                db=self.mock_db,
                document_id=self.test_document_id
            )

    def test_process_document_ocr_error(self):
        """OCR 처리 오류 테스트"""
        # DB 쿼리 모킹 설정
        document_query = MagicMock()
        
        def mock_query_side_effect(model):
            if model == Document:
                return document_query
            return MagicMock()
        
        self.mock_db.query.side_effect = mock_query_side_effect
        document_query.filter.return_value.first.return_value = self.mock_document
        
        # OCR 엔진 오류 설정
        self.mock_ocr_engine.process_file.side_effect = Exception("OCR 처리 중 오류 발생")
        
        # 예외 발생 확인
        with self.assertRaises(OCREngineError):
            self.ocr_service.process_document(
                db=self.mock_db,
                document_id=self.test_document_id
            )
        
        # 문서 상태 업데이트 확인
        self.assertEqual(self.mock_document.status, DocumentStatus.FAILED)
        
        # 오류 메시지 저장 확인
        self.mock_db.commit.assert_called()

    def test_get_document_ocr_results(self):
        """OCR 결과 조회 테스트"""
        # 모의 추출 데이터 생성
        mock_extracted_data = [
            MagicMock(spec=ExtractedData, field_name='full_text', field_value='테스트 문서 내용', confidence_score=0.95),
            MagicMock(spec=ExtractedData, field_name='title', field_value='테스트 문서', confidence_score=0.98)
        ]
        
        # DB 쿼리 체인 모킹 - 문서 조회와 추출 데이터 조회를 분리
        document_query = MagicMock()
        extracted_data_query = MagicMock()
        
        def mock_query_side_effect(model):
            if model == Document:
                return document_query
            elif model == ExtractedData:
                return extracted_data_query
            return MagicMock()
        
        self.mock_db.query.side_effect = mock_query_side_effect
        document_query.filter.return_value.first.return_value = self.mock_document
        extracted_data_query.filter.return_value.all.return_value = mock_extracted_data
        
        # 테스트 실행
        result = self.ocr_service.get_document_ocr_results(
            db=self.mock_db,
            document_id=self.test_document_id
        )
        
        # 검증
        self.assertEqual(result['document_id'], str(self.test_document_id))
        self.assertEqual(result['status'], 'processed')
        self.assertTrue('text' in result)
        self.assertEqual(result['text'], '테스트 문서 내용')

    def test_get_document_ocr_results_not_found(self):
        """존재하지 않는 문서의 OCR 결과 조회 테스트"""
        # DB 쿼리 체인 모킹 - 문서를 찾을 수 없도록 설정
        document_query = MagicMock()
        
        def mock_query_side_effect(model):
            if model == Document:
                return document_query
            return MagicMock()
        
        self.mock_db.query.side_effect = mock_query_side_effect
        document_query.filter.return_value.first.return_value = None
        
        # 예외 발생 확인
        with self.assertRaises(ResourceNotFoundError):
            self.ocr_service.get_document_ocr_results(
                db=self.mock_db,
                document_id=self.test_document_id
            )

    def test_get_document_ocr_results_no_data(self):
        """OCR 결과가 없는 문서 조회 테스트"""
        # DB 쿼리 체인 모킹 - 추출 데이터가 없도록 설정
        document_query = MagicMock()
        extracted_data_query = MagicMock()
        
        def mock_query_side_effect(model):
            if model == Document:
                return document_query
            elif model == ExtractedData:
                return extracted_data_query
            return MagicMock()
        
        self.mock_db.query.side_effect = mock_query_side_effect
        document_query.filter.return_value.first.return_value = self.mock_document
        extracted_data_query.filter.return_value.all.return_value = []
        
        # 테스트 실행
        result = self.ocr_service.get_document_ocr_results(
            db=self.mock_db,
            document_id=self.test_document_id
        )
        
        # 검증
        self.assertEqual(result['document_id'], str(self.test_document_id))
        self.assertEqual(result['status'], 'not_processed')
        self.assertTrue('message' in result)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import uuid
from datetime import datetime

# 테스트 대상 모듈 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 테스트 대상 모듈 임포트
from shared.models import Document, User, ExtractedData
from shared.exceptions import ResourceNotFoundError, ExportError
from export.service import ExportService


class TestExportService(unittest.TestCase):
    """내보내기 서비스 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        # 모의 데이터베이스 세션 생성
        self.mock_db = MagicMock()
        
        # 내보내기 서비스 생성
        self.export_service = ExportService()
        
        # 테스트 문서 ID
        self.test_document_id = uuid.uuid4()
        
        # 모의 문서 생성
        self.mock_document = MagicMock(spec=Document)
        self.mock_document.id = self.test_document_id
        self.mock_document.original_filename = "test_document.pdf"
        self.mock_document.status = 'COMPLETED'
        
        # 모의 쿼리 설정
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_document
        
        # 모의 추출 데이터 생성
        self.mock_extracted_data = [
            MagicMock(spec=ExtractedData, field_name='full_text', field_value='테스트 문서 내용', confidence_score=0.95),
            MagicMock(spec=ExtractedData, field_name='title', field_value='테스트 문서', confidence_score=0.98),
            MagicMock(spec=ExtractedData, field_name='date', field_value='2025-06-01', confidence_score=0.92),
            MagicMock(spec=ExtractedData, field_name='amount', field_value='100,000원', confidence_score=0.90)
        ]
        
        # 추출 데이터 쿼리 설정
        self.mock_db.query.return_value.filter.return_value.all.return_value = self.mock_extracted_data

    def test_export_to_excel(self):
        """Excel 내보내기 테스트"""
        # 테스트 실행
        result = self.export_service.export_to_excel(
            db=self.mock_db,
            document_id=self.test_document_id
        )
        
        # 검증 (파일 경로 반환 확인)
        self.assertTrue(isinstance(result, str))
        self.assertTrue(len(result) > 0)

    def test_export_to_csv(self):
        """CSV 내보내기 테스트"""
        # 테스트 실행
        result = self.export_service.export_to_csv(
            db=self.mock_db,
            document_id=self.test_document_id
        )
        
        # 검증 (파일 경로 반환 확인)
        self.assertTrue(isinstance(result, str))
        self.assertTrue(len(result) > 0)
        
        # CSV 내용 확인 (파일에서 직접 읽음)
        with open(result, 'r', encoding='utf-8') as f:
            csv_content = f.read()
            # 헤더 확인
            self.assertTrue('field,value' in csv_content)
            # 데이터 확인 (쉼표 문제로 인해 부분 문자열 검사)
            self.assertTrue('title,테스트 문서' in csv_content)
            self.assertTrue('date,2025-06-01' in csv_content)
            self.assertTrue('amount,"100,000원"' in csv_content)

    def test_export_to_pdf(self):
        """PDF 내보내기 테스트"""
        # PDF 생성 함수 모킹
        with patch('export.service.generate_pdf', return_value=b'PDF_CONTENT'):
            # 테스트 실행
            result = self.export_service.export_to_pdf(
                db=self.mock_db,
                document_id=self.test_document_id
            )
            
            # 검증 (파일 경로 반환 확인)
            self.assertTrue(isinstance(result, str))
            self.assertTrue(len(result) > 0)
            
            # PDF 내용 확인 (파일에서 직접 읽음)
            with open(result, 'rb') as f:
                pdf_content = f.read()
                self.assertEqual(pdf_content, b'PDF_CONTENT')

    def test_export_document_not_found(self):
        """존재하지 않는 문서 내보내기 테스트"""
        # 문서를 찾을 수 없도록 설정
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # 예외 발생 확인
        with self.assertRaises(ResourceNotFoundError):
            self.export_service.export_to_excel(
                db=self.mock_db,
                document_id=self.test_document_id
            )

    def test_export_document_not_completed(self):
        """처리되지 않은 문서 내보내기 테스트"""
        # 문서 상태를 처리 중으로 설정
        self.mock_document.status = 'PROCESSING'
        
        # 예외 발생 확인
        with self.assertRaises(ExportError):
            self.export_service.export_to_excel(
                db=self.mock_db,
                document_id=self.test_document_id
            )

    def test_export_no_extracted_data(self):
        """추출 데이터가 없는 문서 내보내기 테스트"""
        # 추출 데이터가 없도록 설정
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # 예외 발생 확인
        with self.assertRaises(ExportError):
            self.export_service.export_to_excel(
                db=self.mock_db,
                document_id=self.test_document_id
            )

    def test_get_export_formats(self):
        """지원되는 내보내기 형식 조회 테스트"""
        # 테스트 실행
        formats = self.export_service.get_export_formats()
        
        # 검증
        self.assertTrue(isinstance(formats, list))
        self.assertTrue('excel' in formats)
        self.assertTrue('csv' in formats)
        self.assertTrue('pdf' in formats)


if __name__ == '__main__':
    unittest.main()

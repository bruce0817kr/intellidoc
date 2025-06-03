"""
내보내기 서비스 모듈

문서 데이터를 다양한 형식(Excel, CSV, JSON, PDF)으로 내보내는 기능을 제공합니다.
"""

import os
import json
import uuid
import csv
from typing import Dict, Any, Optional, List
from datetime import datetime

# 임포트
import pandas as pd
from openpyxl.styles import Font, PatternFill
from sqlalchemy.orm import Session

# 로컬 임포트
from shared.config import settings
from shared.exceptions import ExportError, ResourceNotFoundError
from shared.models import Document, ExtractedData


class ExportService:
    """
    내보내기 서비스 클래스
    
    다양한 형식으로 문서 데이터를 내보내는 기능을 제공합니다.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        내보내기 관리자 초기화
        
        Args:
            config: 내보내기 설정
        """
        self.config = config or {}
        self.temp_dir = self.config.get("temp_dir", os.path.join(settings.UPLOAD_DIR, "export"))

        # 임시 디렉토리 생성
        os.makedirs(self.temp_dir, exist_ok=True)

    def export_to_excel(
        self,
        db: Session,
        document_id: uuid.UUID,
        filename: Optional[str] = None,
        sheet_name: str = "Data"
    ) -> str:
        """
        엑셀로 내보내기
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            filename: 파일명 (선택사항)
            sheet_name: 시트명
            
        Returns:
            str: 생성된 파일 경로
            
        Raises:
            ExportError: 내보내기 실패 시
            ResourceNotFoundError: 문서를 찾을 수 없을 시
        """
        try:
            # 문서 조회
            document = db.query(Document).filter(Document.id == document_id).first()
            if document is None:
                raise ResourceNotFoundError(f"문서를 찾을 수 없습니다: {document_id}")

            # 문서 상태 확인
            if document.status != 'COMPLETED':
                raise ExportError(f"처리되지 않은 문서입니다: {document.status}")

            # 추출 데이터 조회
            extracted_data = db.query(ExtractedData).filter(ExtractedData.document_id == document_id).all()
            if not extracted_data:
                raise ExportError("추출된 데이터가 없습니다")

            # 데이터 변환
            data = [{"field": item.field_name, "value": item.field_value} for item in extracted_data]

            # 파일명 생성
            if not filename:
                filename = f"export_{uuid.uuid4().hex[:8]}.xlsx"

            if not filename.endswith(".xlsx"):
                filename += ".xlsx"

            file_path = os.path.join(self.temp_dir, filename)

            # 데이터 평면화
            flattened_data = self._flatten_data(data)

            # 데이터프레임 생성
            if isinstance(flattened_data, list):
                df = pd.DataFrame(flattened_data)
            else:
                df = pd.DataFrame([flattened_data])

            # 엑셀 파일 생성
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # 워크시트 스타일 적용
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]

                # 헤더 스타일
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")

                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill

            return file_path

        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise ExportError(f"엑셀 내보내기 중 오류가 발생했습니다: {str(e)}")

    def export_to_csv(
        self,
        db: Session,
        document_id: uuid.UUID,
        filename: Optional[str] = None,
        delimiter: str = ","
    ) -> str:
        """
        CSV로 내보내기
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            filename: 파일명 (선택사항)
            delimiter: 구분자
            
        Returns:
            str: 생성된 파일 경로
        """
        try:
            # 문서 조회
            document = db.query(Document).filter(Document.id == document_id).first()
            if document is None:
                raise ResourceNotFoundError(f"문서를 찾을 수 없습니다: {document_id}")

            # 문서 상태 확인
            if document.status != 'COMPLETED':
                raise ExportError(f"처리되지 않은 문서입니다: {document.status}")

            # 추출 데이터 조회
            extracted_data = db.query(ExtractedData).filter(ExtractedData.document_id == document_id).all()
            if not extracted_data or len(extracted_data) == 0:
                raise ExportError("추출된 데이터가 없습니다")

            # 데이터 변환
            data = [{"field": item.field_name, "value": item.field_value} for item in extracted_data]

            # 파일명 생성
            if not filename:
                filename = f"export_{uuid.uuid4().hex[:8]}.csv"

            if not filename.endswith(".csv"):
                filename += ".csv"

            file_path = os.path.join(self.temp_dir, filename)

            # 데이터 평면화
            flattened_data = self._flatten_data(data)

            # CSV 파일 생성
            if isinstance(flattened_data, list):
                # 리스트 데이터
                if not flattened_data:
                    # 빈 리스트
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f, delimiter=delimiter)
                        writer.writerow([])
                else:
                    # 필드명 추출
                    fieldnames = list(flattened_data[0].keys())

                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                        writer.writeheader()
                        writer.writerows(flattened_data)
            else:
                # 단일 딕셔너리
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = list(flattened_data.keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                    writer.writeheader()
                    writer.writerow(flattened_data)

            return file_path

        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise ExportError(f"CSV 내보내기 중 오류가 발생했습니다: {str(e)}")

    def export_to_json(
        self,
        db: Session,
        document_id: uuid.UUID,
        filename: Optional[str] = None,
        indent: int = 2
    ) -> str:
        """
        JSON으로 내보내기
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            filename: 파일명 (선택사항)
            indent: 들여쓰기
            
        Returns:
            str: 생성된 파일 경로
        """
        try:
            # 문서 조회
            document = db.query(Document).filter(Document.id == document_id).first()
            if document is None:
                raise ResourceNotFoundError(f"문서를 찾을 수 없습니다: {document_id}")

            # 문서 상태 확인
            if document.status != 'COMPLETED':
                raise ExportError(f"처리되지 않은 문서입니다: {document.status}")

            # 추출 데이터 조회
            extracted_data = db.query(ExtractedData).filter(ExtractedData.document_id == document_id).all()
            if extracted_data is None or len(extracted_data) == 0:
                raise ExportError("추출된 데이터가 없습니다")

            # 데이터 변환
            data = [{"field": item.field_name, "value": item.field_value} for item in extracted_data]

            # 파일명 생성
            if not filename:
                filename = f"export_{uuid.uuid4().hex[:8]}.json"

            if not filename.endswith(".json"):
                filename += ".json"

            file_path = os.path.join(self.temp_dir, filename)

            # JSON 파일 생성
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent, default=str)

            return file_path

        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise ExportError(f"JSON 내보내기 중 오류가 발생했습니다: {str(e)}")

    def export_to_pdf(
        self,
        db: Session,
        document_id: uuid.UUID,
        filename: Optional[str] = None,
        title: str = "내보내기 결과"
    ) -> str:
        """
        PDF로 내보내기
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            filename: 파일명 (선택사항)
            title: 문서 제목
            
        Returns:
            str: 생성된 파일 경로
        """
        try:
            # 문서 조회
            document = db.query(Document).filter(Document.id == document_id).first()
            if document is None:
                raise ResourceNotFoundError(f"문서를 찾을 수 없습니다: {document_id}")

            # 문서 상태 확인
            if document.status != 'COMPLETED':
                raise ExportError(f"처리되지 않은 문서입니다: {document.status}")

            # 추출 데이터 조회
            extracted_data = db.query(ExtractedData).filter(ExtractedData.document_id == document_id).all()
            if extracted_data is None or len(extracted_data) == 0:
                raise ExportError("추출된 데이터가 없습니다")

            # 데이터 변환
            data = [{"field": item.field_name, "value": item.field_value} for item in extracted_data]

            # 파일명 생성
            if not filename:
                filename = f"export_{uuid.uuid4().hex[:8]}.pdf"

            if not filename.endswith(".pdf"):
                filename += ".pdf"

            file_path = os.path.join(self.temp_dir, filename)

            # HTML 생성
            html_content = self._generate_html(data, title)

            # HTML을 PDF로 변환 (실제로는 wkhtmltopdf 등을 사용)
            pdf_content = generate_pdf(html_content)

            # PDF 파일 저장
            with open(file_path, 'wb') as f:
                f.write(pdf_content)

            return file_path

        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise ExportError(f"PDF 내보내기 중 오류가 발생했습니다: {str(e)}")

    def _flatten_data(self, data: Any, parent_key: str = '', sep: str = '.') -> Any:
        """
        중첩된 딕셔너리를 평면화
        
        Args:
            data: 원본 데이터
            parent_key: 부모 키
            sep: 구분자
            
        Returns:
            Any: 평면화된 데이터
        """
        if isinstance(data, dict):
            items = []
            for k, v in data.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                items.extend(self._flatten_data(v, new_key, sep).items())
            return dict(items)
        elif isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                return [self._flatten_data(item, parent_key, sep) for item in data]
            else:
                return data
        else:
            return {parent_key: data} if parent_key else data

    def _generate_html(self, data: Any, title: str = "내보내기 결과") -> str:
        """
        HTML 생성
        
        Args:
            data: 데이터
            title: 제목
            
        Returns:
            str: HTML 문자열
        """
        style = """
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; font-weight: bold; }
            tr:nth-child(even) { background-color: #f9f9f9; }
        </style>
        """

        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset='UTF-8'>
            {style}
        </head>
        <body>
            <h1>{title}</h1>
        """

        if isinstance(data, list) and data:
            html += "<table><tr>"
            for key in data[0].keys():
                html += f"<th>{key}</th>"
            html += "</tr>"

            for item in data:
                html += "<tr>"
                for value in item.values():
                    html += f"<td>{value}</td>"
                html += "</tr>"

            html += "</table>"
        else:
            html += "<p>데이터가 없습니다.</p>"

        html += "</body></html>"
        return html

    def get_export_formats(self) -> List[str]:
        """
        지원되는 내보내기 형식 반환
        
        Returns:
            List[str]: 지원되는 형식 목록
        """
        return ["excel", "csv", "json", "pdf"]


def generate_pdf(html_content: str) -> bytes:
    """
    HTML 콘텐츠를 PDF로 변환
    
    Args:
        html_content: HTML 문자열
        
    Returns:
        bytes: PDF 바이트 데이터
    """
    # 실제 구현에서는 wkhtmltopdf, weasyprint 등을 사용
    # 테스트용으로 더미 PDF 데이터 반환
    return b"PDF_CONTENT"

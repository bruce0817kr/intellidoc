"""
Camelot 엔진 (PDF 표 추출 전문)
"""

from typing import Dict, Any, Optional, List
import pandas as pd
from .base import BaseOCREngine, OCRResult, OCREngineFactory


@OCREngineFactory.register("camelot")
class CamelotEngine(BaseOCREngine):
    """Camelot - PDF 표 추출 전문 엔진"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Camelot 지연 import
        try:
            import camelot
            self.camelot = camelot
        except ImportError:
            raise ImportError(
                "Camelot is not installed. "
                "Install it with: pip install camelot-py[cv]"
            )

        # 설정
        self.flavor = config.get("flavor", "lattice") if config else "lattice"
        # lattice: 선 기반 표 (대부분의 PDF)
        # stream: 공백 기반 표 (선이 없는 표)

    def extract_text(self, image_path: str, **kwargs) -> OCRResult:
        """
        PDF에서 표 추출 (이미지는 지원 안함)

        Args:
            image_path: PDF 파일 경로
            **kwargs: pages, flavor 등 추가 옵션

        Returns:
            OCRResult 객체
        """
        if not image_path.endswith('.pdf'):
            return OCRResult(
                text="",
                confidence=0.0,
                metadata={
                    "error": "Camelot only supports PDF files",
                    "engine": "camelot"
                }
            )

        return self.extract_tables_from_pdf(image_path, **kwargs)

    def extract_tables_from_pdf(
        self,
        pdf_path: str,
        pages: str = "all",
        **kwargs
    ) -> OCRResult:
        """
        PDF에서 표 추출

        Args:
            pdf_path: PDF 파일 경로
            pages: 페이지 범위 (예: "1", "1-3", "all")
            **kwargs: flavor 등 추가 옵션

        Returns:
            OCRResult 객체
        """
        flavor = kwargs.get("flavor", self.flavor)

        try:
            # 표 추출
            tables = self.camelot.read_pdf(
                pdf_path,
                pages=pages,
                flavor=flavor,
                strip_text='\n'
            )

            # 결과 파싱
            table_data = []
            all_text = []

            for i, table in enumerate(tables):
                df = table.df

                # 표 메타데이터
                table_info = {
                    "table_number": i + 1,
                    "page": table.page,
                    "accuracy": float(table.accuracy),
                    "whitespace": float(table.whitespace),
                    "rows": len(df),
                    "cols": len(df.columns),
                    "data": df.to_dict('records'),
                    "csv": df.to_csv(index=False),
                    "html": df.to_html(index=False),
                    "markdown": df.to_markdown(index=False)
                }

                table_data.append(table_info)

                # 텍스트 추출
                all_text.append(f"\n=== Table {i + 1} (Page {table.page}) ===\n")
                all_text.append(df.to_string(index=False))
                all_text.append("\n")

            # 평균 정확도
            avg_accuracy = sum(t["accuracy"] for t in table_data) / len(table_data) if table_data else 0.0

            return OCRResult(
                text="\n".join(all_text),
                confidence=avg_accuracy / 100.0,  # 0-1 범위로 정규화
                metadata={
                    "tables": table_data,
                    "table_count": len(table_data),
                    "flavor": flavor,
                    "pages": pages,
                    "engine": "camelot"
                }
            )

        except Exception as e:
            return OCRResult(
                text="",
                confidence=0.0,
                metadata={
                    "error": str(e),
                    "engine": "camelot"
                }
            )

    def export_tables(
        self,
        pdf_path: str,
        output_dir: str,
        formats: List[str] = None,
        pages: str = "all"
    ) -> Dict[str, Any]:
        """
        표를 다양한 형식으로 내보내기

        Args:
            pdf_path: PDF 파일 경로
            output_dir: 출력 디렉토리
            formats: 내보낼 형식 리스트 (csv, excel, html, json)
            pages: 페이지 범위

        Returns:
            내보낸 파일 경로 딕셔너리
        """
        if formats is None:
            formats = ["csv", "excel", "html"]

        tables = self.camelot.read_pdf(pdf_path, pages=pages, flavor=self.flavor)

        exported_files = {}

        for fmt in formats:
            if fmt == "csv":
                output_path = f"{output_dir}/tables.csv"
                tables.export(output_path, f='csv')
                exported_files["csv"] = output_path

            elif fmt == "excel":
                output_path = f"{output_dir}/tables.xlsx"
                tables.export(output_path, f='excel')
                exported_files["excel"] = output_path

            elif fmt == "html":
                output_path = f"{output_dir}/tables.html"
                tables.export(output_path, f='html')
                exported_files["html"] = output_path

            elif fmt == "json":
                output_path = f"{output_dir}/tables.json"
                tables.export(output_path, f='json')
                exported_files["json"] = output_path

        return {
            "exported_files": exported_files,
            "table_count": len(tables),
            "formats": formats
        }

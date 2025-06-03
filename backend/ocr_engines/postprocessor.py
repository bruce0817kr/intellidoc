"""
OCR 결과 후처리 모듈

주요 기능:
1. 텍스트 정규화
2. 레이아웃 분석
3. 구조화된 데이터 추출
"""

import re
import json
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy as np

from shared.logger import log_info, log_error
from shared.constants import KoreanConstants
from ocr_engines.base import OCRResult


class OCRPostProcessor:
    """OCR 결과 후처리 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        후처리기 초기화
        
        Args:
            config: 후처리 설정
        """
        self.config = config or {}
    
    def process(self, ocr_results: List[OCRResult]) -> Dict[str, Any]:
        """
        OCR 결과 후처리
        
        Args:
            ocr_results: OCR 결과 목록
            
        Returns:
            Dict[str, Any]: 후처리된 결과
        """
        # 결과 병합
        merged_text = self.merge_results(ocr_results)
        
        # 텍스트 정규화
        normalized_text = self.normalize_text(merged_text)
        
        # 구조화된 데이터 추출
        structured_data = self.extract_structured_data(normalized_text, ocr_results)
        
        # 결과 반환
        return {
            "text": normalized_text,
            "structured_data": structured_data,
            "page_count": len(ocr_results),
            "confidence": self._calculate_avg_confidence(ocr_results)
        }
    
    def merge_results(self, ocr_results: List[OCRResult]) -> str:
        """
        OCR 결과 병합
        
        Args:
            ocr_results: OCR 결과 목록
            
        Returns:
            str: 병합된 텍스트
        """
        merged_text = ""
        
        for result in ocr_results:
            # 페이지 구분자 추가
            if merged_text:
                merged_text += f"\n\n--- 페이지 {result.page_number} ---\n\n"
            else:
                merged_text += f"--- 페이지 {result.page_number} ---\n\n"
            
            merged_text += result.text
        
        return merged_text
    
    def normalize_text(self, text: str) -> str:
        """
        텍스트 정규화
        
        Args:
            text: 원본 텍스트
            
        Returns:
            str: 정규화된 텍스트
        """
        # 공백 정규화
        normalized = re.sub(r'\s+', ' ', text)
        
        # 줄바꿈 정규화
        normalized = re.sub(r'(?<!\n)\n(?!\n)', ' ', normalized)
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        
        # 특수문자 정규화
        normalized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', normalized)
        
        # 한글 특화 정규화
        if self.config.get("korean_normalize", True):
            # 한글 자모 결합
            normalized = self._normalize_korean_jamo(normalized)
            
            # 한글 날짜 형식 정규화
            normalized = self._normalize_korean_dates(normalized)
            
            # 한글 숫자 정규화
            normalized = self._normalize_korean_numbers(normalized)
        
        return normalized
    
    def _normalize_korean_jamo(self, text: str) -> str:
        """
        한글 자모 결합 정규화
        
        Args:
            text: 원본 텍스트
            
        Returns:
            str: 정규화된 텍스트
        """
        # 초성+중성+종성 결합 (실제 구현은 더 복잡함)
        # 여기서는 간단한 예시만 제공
        return text
    
    def _normalize_korean_dates(self, text: str) -> str:
        """
        한글 날짜 형식 정규화
        
        Args:
            text: 원본 텍스트
            
        Returns:
            str: 정규화된 텍스트
        """
        # 날짜 패턴 정규화
        # 예: "2025 년 6 월 1 일" -> "2025년 6월 1일"
        text = re.sub(r'(\d+)\s*년\s*(\d+)\s*월\s*(\d+)\s*일', r'\1년 \2월 \3일', text)
        
        return text
    
    def _normalize_korean_numbers(self, text: str) -> str:
        """
        한글 숫자 정규화
        
        Args:
            text: 원본 텍스트
            
        Returns:
            str: 정규화된 텍스트
        """
        # 숫자 사이 공백 제거
        # 예: "1 2 3 4" -> "1234"
        text = re.sub(r'(?<=\d)\s+(?=\d)', '', text)
        
        return text
    
    def extract_structured_data(self, text: str, ocr_results: List[OCRResult]) -> Dict[str, Any]:
        """
        구조화된 데이터 추출
        
        Args:
            text: 정규화된 텍스트
            ocr_results: OCR 결과 목록
            
        Returns:
            Dict[str, Any]: 구조화된 데이터
        """
        structured_data = {}
        
        # 개인정보 추출
        personal_info = self.extract_personal_info(text)
        if personal_info:
            structured_data["personal_info"] = personal_info
        
        # 날짜 추출
        dates = self.extract_dates(text)
        if dates:
            structured_data["dates"] = dates
        
        # 금액 추출
        amounts = self.extract_amounts(text)
        if amounts:
            structured_data["amounts"] = amounts
        
        # 표 추출 (바운딩 박스 기반)
        tables = self.extract_tables(ocr_results)
        if tables:
            structured_data["tables"] = tables
        
        return structured_data
    
    def extract_personal_info(self, text: str) -> Dict[str, Any]:
        """
        개인정보 추출
        
        Args:
            text: 정규화된 텍스트
            
        Returns:
            Dict[str, Any]: 추출된 개인정보
        """
        personal_info = {}
        
        # 이름 추출 (한국어 이름 패턴)
        name_match = re.search(r'이\s*름\s*[:\s]\s*([가-힣]{2,5})', text)
        if name_match:
            personal_info["name"] = name_match.group(1).strip()
        
        # 전화번호 추출
        phone_matches = re.finditer(KoreanConstants.PHONE_PATTERN, text)
        phones = [match.group(0) for match in phone_matches]
        if phones:
            personal_info["phones"] = phones
        
        # 이메일 추출
        email_matches = re.finditer(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        emails = [match.group(0) for match in email_matches]
        if emails:
            personal_info["emails"] = emails
        
        # 주소 추출 (한국 주소 패턴)
        address_match = re.search(r'주\s*소\s*[:\s]\s*([가-힣0-9\s,-]+[동로길]\s*[0-9-]+)', text)
        if address_match:
            personal_info["address"] = address_match.group(1).strip()
        
        return personal_info
    
    def extract_dates(self, text: str) -> List[str]:
        """
        날짜 추출
        
        Args:
            text: 정규화된 텍스트
            
        Returns:
            List[str]: 추출된 날짜 목록
        """
        dates = []
        
        # 한국어 날짜 형식 (YYYY년 MM월 DD일)
        kr_date_matches = re.finditer(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일', text)
        for match in kr_date_matches:
            year, month, day = match.groups()
            dates.append(f"{year}년 {month}월 {day}일")
        
        # ISO 날짜 형식 (YYYY-MM-DD)
        iso_date_matches = re.finditer(r'(\d{4})-(\d{2})-(\d{2})', text)
        for match in iso_date_matches:
            dates.append(match.group(0))
        
        # 슬래시 날짜 형식 (YYYY/MM/DD)
        slash_date_matches = re.finditer(r'(\d{4})/(\d{2})/(\d{2})', text)
        for match in slash_date_matches:
            dates.append(match.group(0))
        
        return dates
    
    def extract_amounts(self, text: str) -> List[Dict[str, Any]]:
        """
        금액 추출
        
        Args:
            text: 정규화된 텍스트
            
        Returns:
            List[Dict[str, Any]]: 추출된 금액 목록
        """
        amounts = []
        
        # 원화 금액 (숫자 + '원')
        krw_matches = re.finditer(r'([\d,]+)\s*원', text)
        for match in krw_matches:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = int(amount_str)
                amounts.append({
                    "value": amount,
                    "currency": "KRW",
                    "text": match.group(0)
                })
            except ValueError:
                pass
        
        # 달러 금액 ('$' + 숫자)
        usd_matches = re.finditer(r'\$\s*([\d,.]+)', text)
        for match in usd_matches:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                amounts.append({
                    "value": amount,
                    "currency": "USD",
                    "text": match.group(0)
                })
            except ValueError:
                pass
        
        return amounts
    
    def extract_tables(self, ocr_results: List[OCRResult]) -> List[Dict[str, Any]]:
        """
        표 추출
        
        Args:
            ocr_results: OCR 결과 목록
            
        Returns:
            List[Dict[str, Any]]: 추출된 표 목록
        """
        tables = []
        
        # 바운딩 박스 기반 표 추출 (간단한 구현)
        for page_num, result in enumerate(ocr_results, 1):
            if not result.bounding_boxes:
                continue
            
            # 표 후보 영역 식별
            table_candidates = self._identify_table_regions(result.bounding_boxes)
            
            for i, table_region in enumerate(table_candidates):
                table_data = self._extract_table_data(table_region)
                if table_data:
                    tables.append({
                        "page": page_num,
                        "table_id": f"table_{page_num}_{i+1}",
                        "data": table_data
                    })
        
        return tables
    
    def _identify_table_regions(self, bounding_boxes: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        표 영역 식별
        
        Args:
            bounding_boxes: 바운딩 박스 목록
            
        Returns:
            List[List[Dict[str, Any]]]: 표 영역 목록
        """
        # 실제 구현에서는 더 복잡한 알고리즘 필요
        # 여기서는 간단한 예시만 제공
        return [bounding_boxes]
    
    def _extract_table_data(self, table_region: List[Dict[str, Any]]) -> List[List[str]]:
        """
        표 데이터 추출
        
        Args:
            table_region: 표 영역
            
        Returns:
            List[List[str]]: 표 데이터
        """
        # 실제 구현에서는 더 복잡한 알고리즘 필요
        # 여기서는 간단한 예시만 제공
        return []
    
    def _calculate_avg_confidence(self, ocr_results: List[OCRResult]) -> float:
        """
        평균 신뢰도 계산
        
        Args:
            ocr_results: OCR 결과 목록
            
        Returns:
            float: 평균 신뢰도
        """
        if not ocr_results:
            return 0.0
        
        total_confidence = sum(result.confidence for result in ocr_results)
        return total_confidence / len(ocr_results)

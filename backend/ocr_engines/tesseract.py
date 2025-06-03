"""
Tesseract OCR 엔진 구현 모듈

주요 기능:
1. Tesseract OCR 엔진 래핑
2. 이미지 전처리
3. PDF 파일 처리
"""

import os
import tempfile
import subprocess
from typing import Dict, Any, Optional, List, Tuple
import pytesseract
from PIL import Image
import pdf2image
import numpy as np

from shared.logger import log_info, log_error
from shared.exceptions import OCREngineError
from ocr_engines.base import BaseOCREngine, OCRResult, OCREngineFactory


@OCREngineFactory.register("tesseract")
class TesseractOCREngine(BaseOCREngine):
    """Tesseract OCR 엔진 구현 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Tesseract OCR 엔진 초기화
        
        Args:
            config: 엔진 설정
        """
        super().__init__(config)
        
        # 기본 설정
        self.lang = self.config.get("lang", "kor+eng")
        self.dpi = self.config.get("dpi", 300)
        self.psm = self.config.get("psm", 3)  # 3: 자동 페이지 분할 및 방향 감지
        self.oem = self.config.get("oem", 3)  # 3: 기본 + LSTM OCR 엔진
        
        # Tesseract 경로 설정
        self.tesseract_path = self.config.get("tesseract_path")
        if self.tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        
        # Tesseract 설치 확인
        self._check_tesseract_installed()
    
    def _check_tesseract_installed(self) -> None:
        """
        Tesseract 설치 확인
        
        Raises:
            OCREngineError: Tesseract가 설치되지 않은 경우
        """
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            log_error(f"Tesseract OCR 설치 확인 실패: {str(e)}")
            raise OCREngineError(
                message="Tesseract OCR이 설치되지 않았거나 경로가 올바르지 않습니다.",
                details={"error": str(e)}
            )
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        이미지 전처리
        
        Args:
            image: 원본 이미지
            
        Returns:
            Image.Image: 전처리된 이미지
        """
        # 그레이스케일 변환
        if image.mode != 'L':
            image = image.convert('L')
        
        # 이미지 향상 (선택적)
        if self.config.get("enhance_image", True):
            # 대비 향상
            import cv2
            img_array = np.array(image)
            img_array = cv2.equalizeHist(img_array)
            
            # 노이즈 제거
            img_array = cv2.fastNlMeansDenoising(img_array, None, 10, 7, 21)
            
            # PIL 이미지로 변환
            image = Image.fromarray(img_array)
        
        return image
    
    def _get_tesseract_config(self) -> str:
        """
        Tesseract 설정 문자열 생성
        
        Returns:
            str: Tesseract 설정 문자열
        """
        config = f"--psm {self.psm} --oem {self.oem}"
        
        # 추가 설정
        if self.config.get("tessdata_dir"):
            config += f" --tessdata-dir {self.config['tessdata_dir']}"
        
        return config
    
    def process_image(self, image_path: str) -> OCRResult:
        """
        이미지 처리
        
        Args:
            image_path: 처리할 이미지 경로
            
        Returns:
            OCRResult: OCR 결과
            
        Raises:
            OCREngineError: 처리 중 오류 발생 시
        """
        self.validate_file(image_path)
        
        try:
            # 이미지 로드
            image = Image.open(image_path)
            
            # 이미지 전처리
            processed_image = self._preprocess_image(image)
            
            # OCR 수행
            config = self._get_tesseract_config()
            ocr_data = pytesseract.image_to_data(
                processed_image, 
                lang=self.lang,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # 텍스트 추출
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.lang,
                config=config
            )
            
            # 신뢰도 계산 (단어 신뢰도의 평균)
            confidences = [float(conf) / 100.0 for conf in ocr_data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # 바운딩 박스 추출
            bounding_boxes = []
            for i in range(len(ocr_data['text'])):
                if ocr_data['text'][i].strip() and ocr_data['conf'][i] != '-1':
                    bounding_boxes.append({
                        'text': ocr_data['text'][i],
                        'confidence': float(ocr_data['conf'][i]) / 100.0,
                        'x': ocr_data['left'][i],
                        'y': ocr_data['top'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i],
                        'block_num': ocr_data['block_num'][i],
                        'par_num': ocr_data['par_num'][i],
                        'line_num': ocr_data['line_num'][i],
                        'word_num': ocr_data['word_num'][i]
                    })
            
            # OCR 결과 생성
            return OCRResult(
                text=text,
                confidence=avg_confidence,
                page_number=1,
                bounding_boxes=bounding_boxes,
                metadata={
                    "engine": "tesseract",
                    "lang": self.lang,
                    "psm": self.psm,
                    "oem": self.oem
                }
            )
        
        except Exception as e:
            log_error(f"이미지 OCR 처리 실패: {str(e)}", exc_info=True)
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
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=self.dpi,
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
            
        Raises:
            OCREngineError: 처리 중 오류 발생 시
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

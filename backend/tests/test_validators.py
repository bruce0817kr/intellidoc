"""
validators.py 테스트 모듈

주요 테스트:
- 파일 확장자 검증
- MIME 타입 검증
- 파일 시그니처 감지
- 비밀번호 강도 검증
"""

import pytest
from shared.validators import (
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
    detect_mime_type_from_content,
    validate_password_strength,
    validate_email,
    validate_api_key_format,
)
from shared.exceptions import ValidationError


class TestFileValidation:
    """파일 검증 테스트"""

    def test_validate_file_extension_valid(self):
        """유효한 파일 확장자 테스트"""
        assert validate_file_extension("document.pdf") == True
        assert validate_file_extension("image.png") == True
        assert validate_file_extension("spreadsheet.xlsx") == True

    def test_validate_file_extension_invalid(self):
        """유효하지 않은 파일 확장자 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_file_extension("malware.exe")
        assert "지원하지 않는 파일 형식" in exc_info.value.message

    def test_validate_file_size_valid(self):
        """유효한 파일 크기 테스트"""
        assert validate_file_size(1024 * 1024) == True  # 1MB
        assert validate_file_size(50 * 1024 * 1024) == True  # 50MB

    def test_validate_file_size_too_large(self):
        """파일 크기 초과 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_file_size(200 * 1024 * 1024)  # 200MB
        assert "파일 크기가 너무 큽니다" in exc_info.value.message


class TestMimeTypeValidation:
    """MIME 타입 검증 테스트"""

    def test_detect_pdf_signature(self):
        """PDF 파일 시그니처 감지 테스트"""
        pdf_content = b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n'
        mime_type = detect_mime_type_from_content(pdf_content, "test.pdf")
        assert mime_type == "application/pdf"

    def test_detect_png_signature(self):
        """PNG 파일 시그니처 감지 테스트"""
        png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        mime_type = detect_mime_type_from_content(png_content, "test.png")
        assert mime_type == "image/png"

    def test_detect_jpeg_signature(self):
        """JPEG 파일 시그니처 감지 테스트"""
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        mime_type = detect_mime_type_from_content(jpeg_content, "test.jpg")
        assert mime_type == "image/jpeg"

    def test_validate_mime_type_match(self):
        """MIME 타입 일치 테스트"""
        pdf_content = b'%PDF-1.4'
        assert validate_mime_type(pdf_content, "document.pdf", "application/pdf") == True

    def test_validate_mime_type_mismatch(self):
        """MIME 타입 불일치 테스트 (확장자 위장)"""
        png_content = b'\x89PNG\r\n\x1a\n'
        with pytest.raises(ValidationError) as exc_info:
            validate_mime_type(png_content, "fake.pdf")
        assert "파일 확장자와 실제 파일 내용이 일치하지 않습니다" in exc_info.value.message


class TestPasswordValidation:
    """비밀번호 검증 테스트"""

    def test_password_too_short(self):
        """비밀번호 길이 부족 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_password_strength("Pass1!")
        assert "최소 8자 이상" in exc_info.value.message

    def test_password_no_uppercase(self):
        """대문자 없음 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_password_strength("password123!")
        assert "대문자" in exc_info.value.message

    def test_password_no_lowercase(self):
        """소문자 없음 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_password_strength("PASSWORD123!")
        assert "소문자" in exc_info.value.message

    def test_password_no_number(self):
        """숫자 없음 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_password_strength("Password!")
        assert "숫자" in exc_info.value.message

    def test_password_no_special_char(self):
        """특수문자 없음 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_password_strength("Password123")
        assert "특수문자" in exc_info.value.message

    def test_password_valid(self):
        """유효한 비밀번호 테스트"""
        assert validate_password_strength("SecurePass123!") == True
        assert validate_password_strength("MyP@ssw0rd") == True


class TestEmailValidation:
    """이메일 검증 테스트"""

    def test_email_valid(self):
        """유효한 이메일 테스트"""
        assert validate_email("user@example.com") == True
        assert validate_email("john.doe@company.co.kr") == True

    def test_email_invalid(self):
        """유효하지 않은 이메일 테스트"""
        with pytest.raises(ValidationError):
            validate_email("invalid-email")

        with pytest.raises(ValidationError):
            validate_email("@example.com")

        with pytest.raises(ValidationError):
            validate_email("user@")


class TestAPIKeyValidation:
    """API 키 검증 테스트"""

    def test_api_key_too_short(self):
        """API 키 길이 부족 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_api_key_format("short")
        assert "최소 16자 이상" in exc_info.value.message

    def test_api_key_invalid_characters(self):
        """API 키 유효하지 않은 문자 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            validate_api_key_format("invalid@key#with$special%chars")
        assert "영문자, 숫자, 밑줄, 하이픈, 점만" in exc_info.value.message

    def test_api_key_valid(self):
        """유효한 API 키 테스트"""
        assert validate_api_key_format("valid-api-key-1234567890") == True
        assert validate_api_key_format("API_KEY_123456789012345") == True

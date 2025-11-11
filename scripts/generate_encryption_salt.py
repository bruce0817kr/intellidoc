#!/usr/bin/env python3
"""
암호화 솔트 생성 스크립트

안전한 랜덤 암호화 솔트를 생성합니다.
이 솔트는 .env 파일의 ENCRYPTION_SALT 환경변수에 설정해야 합니다.

사용법:
    python scripts/generate_encryption_salt.py
"""

import os
import secrets
import string

def generate_salt(length: int = 64) -> str:
    """
    안전한 랜덤 솔트 생성

    Args:
        length: 솔트 길이 (기본 64자)

    Returns:
        생성된 솔트 문자열
    """
    # 대소문자, 숫자, 특수문자 포함
    alphabet = string.ascii_letters + string.digits + string.punctuation
    salt = ''.join(secrets.choice(alphabet) for _ in range(length))
    return salt

def main():
    """메인 함수"""
    print("=" * 70)
    print("IntelliDoc 암호화 솔트 생성기")
    print("=" * 70)
    print()

    # 솔트 생성
    salt = generate_salt()

    print("✅ 새로운 암호화 솔트가 생성되었습니다:")
    print()
    print(f"ENCRYPTION_SALT={salt}")
    print()
    print("=" * 70)
    print("설정 방법:")
    print("=" * 70)
    print()
    print("1. .env 파일을 열고 다음 줄을 추가/수정하세요:")
    print(f"   ENCRYPTION_SALT={salt}")
    print()
    print("2. 또는 환경변수로 설정하세요:")
    print(f"   export ENCRYPTION_SALT='{salt}'")
    print()
    print("⚠️  주의사항:")
    print("   - 이 솔트는 안전한 곳에 보관하세요")
    print("   - 프로덕션 환경에서는 반드시 고유한 값을 사용하세요")
    print("   - 솔트 변경 시 기존 암호화된 데이터는 복호화할 수 없습니다")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()

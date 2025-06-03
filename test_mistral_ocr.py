"""
Mistral OCR 단독 테스트 스크립트

사용법:
python test_mistral_ocr.py [이미지_파일_경로]

예시:
python test_mistral_ocr.py test_image.jpg
python test_mistral_ocr.py test_document.pdf
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Optional

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from ocr_engines.mistral_ocr import MistralOCREngine
    from shared.exceptions import OCREngineError
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print("backend 디렉토리가 올바른지 확인하세요.")
    sys.exit(1)


def print_colored(message: str, color: str = "white"):
    """색상 출력 (Windows 호환)"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    
    if os.name == 'nt':  # Windows
        print(message)  # Windows에서는 기본 출력
    else:
        print(f"{colors.get(color, colors['white'])}{message}{colors['reset']}")


def test_mistral_ocr_engine():
    """Mistral OCR 엔진 기본 테스트"""
    print_colored("🔍 Mistral OCR 엔진 기본 테스트 시작...", "cyan")
    
    try:
        # 환경변수 확인
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            print_colored("❌ MISTRAL_API_KEY 환경변수가 설정되지 않았습니다.", "red")
            print_colored("💡 .env 파일에 MISTRAL_API_KEY를 설정하세요.", "yellow")
            return False
        
        print_colored(f"✅ API 키 확인 완료 (길이: {len(api_key)})", "green")
        
        # 엔진 초기화
        config = {
            "api_key": api_key,
            "model": "pixtral-12b-2409",
            "max_tokens": 2048,
            "temperature": 0.1,
            "timeout": 30,
            "max_retries": 2
        }
        
        engine = MistralOCREngine(config)
        print_colored("✅ Mistral OCR 엔진 초기화 완료", "green")
        
        # 설정 확인
        print_colored("📋 엔진 설정:", "blue")
        print(f"  - 모델: {engine.model}")
        print(f"  - 최대 토큰: {engine.max_tokens}")
        print(f"  - 온도: {engine.temperature}")
        print(f"  - 타임아웃: {engine.timeout}초")
        print(f"  - 최대 재시도: {engine.max_retries}회")
        
        return True
        
    except Exception as e:
        print_colored(f"❌ 엔진 테스트 실패: {str(e)}", "red")
        return False


def test_image_processing(image_path: str):
    """이미지 처리 테스트"""
    print_colored(f"🖼️  이미지 처리 테스트: {image_path}", "cyan")
    
    if not os.path.exists(image_path):
        print_colored(f"❌ 파일을 찾을 수 없습니다: {image_path}", "red")
        return False
    
    try:
        # 엔진 초기화
        api_key = os.getenv("MISTRAL_API_KEY")
        engine = MistralOCREngine({"api_key": api_key})
        
        print_colored(f"📂 파일 크기: {os.path.getsize(image_path)} bytes", "blue")
        
        # 파일 확장자 확인
        file_ext = os.path.splitext(image_path)[1].lower()
        print_colored(f"📄 파일 형식: {file_ext}", "blue")
        
        # 처리 시작
        start_time = datetime.now()
        print_colored("⏳ OCR 처리 시작...", "yellow")
        
        if file_ext == '.pdf':
            results = engine.process_file(image_path)
            print_colored(f"✅ PDF 처리 완료 (페이지 수: {len(results)})", "green")
            
            for i, result in enumerate(results):
                print_colored(f"\n📄 페이지 {i+1}:", "blue")
                print_colored(f"📝 추출된 텍스트 ({len(result.text)} 글자):", "blue")
                print(f"   {result.text[:200]}{'...' if len(result.text) > 200 else ''}")
                print_colored(f"🎯 신뢰도: {result.confidence:.2f}", "blue")
                
                if result.metadata.get("structured_data"):
                    print_colored("📊 구조화된 데이터:", "blue")
                    structured = result.metadata["structured_data"]
                    for key, value in structured.items():
                        if value:
                            print(f"   {key}: {value}")
                
        else:
            result = engine.process_image(image_path)
            print_colored("✅ 이미지 처리 완료", "green")
            
            print_colored(f"\n📝 추출된 텍스트 ({len(result.text)} 글자):", "blue")
            print(f"   {result.text[:300]}{'...' if len(result.text) > 300 else ''}")
            
            print_colored(f"\n🎯 신뢰도: {result.confidence:.2f}", "blue")
            
            # 구조화된 데이터 출력
            if result.metadata.get("structured_data"):
                print_colored("\n📊 구조화된 데이터:", "blue")
                structured = result.metadata["structured_data"]
                for key, value in structured.items():
                    if value:
                        if isinstance(value, list) and len(value) > 0:
                            print(f"   {key}: {value}")
                        elif not isinstance(value, list) and value:
                            print(f"   {key}: {value}")
            
            # 바운딩 박스 정보
            if result.bounding_boxes:
                print_colored(f"\n📐 텍스트 블록 수: {len(result.bounding_boxes)}", "blue")
                for i, bbox in enumerate(result.bounding_boxes[:3]):  # 처음 3개만 표시
                    print(f"   블록 {i+1}: \"{bbox['text'][:50]}...\" (신뢰도: {bbox['confidence']:.2f})")
        
        # 처리 시간 계산
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        print_colored(f"\n⏱️  처리 시간: {processing_time:.2f}초", "green")
        
        return True
        
    except OCREngineError as e:
        print_colored(f"❌ OCR 처리 오류: {str(e)}", "red")
        if hasattr(e, 'details') and e.details:
            print_colored(f"💬 세부사항: {e.details}", "yellow")
        return False
    except Exception as e:
        print_colored(f"❌ 예상치 못한 오류: {str(e)}", "red")
        import traceback
        print_colored(f"🔍 스택 트레이스:", "yellow")
        traceback.print_exc()
        return False


def test_api_connectivity():
    """Mistral API 연결 테스트"""
    print_colored("🌐 Mistral API 연결 테스트...", "cyan")
    
    try:
        import requests
        
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            print_colored("❌ API 키가 설정되지 않았습니다.", "red")
            return False
        
        # 간단한 텍스트 완성 요청으로 API 연결 확인
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "pixtral-12b-2409",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user",
                    "content": "Hello, can you respond with 'API connection successful'?"
                }
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        print_colored("📡 API 요청 전송 중...", "yellow")
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print_colored("✅ API 연결 성공", "green")
            
            result = response.json()
            if result.get("choices"):
                content = result["choices"][0]["message"]["content"]
                print_colored(f"💬 응답: {content}", "blue")
            
            # 사용량 정보
            if result.get("usage"):
                usage = result["usage"]
                print_colored(f"📊 토큰 사용량: {usage.get('total_tokens', 'N/A')}", "blue")
            
            return True
        else:
            print_colored(f"❌ API 요청 실패: {response.status_code}", "red")
            print_colored(f"💬 응답: {response.text}", "yellow")
            return False
            
    except requests.exceptions.Timeout:
        print_colored("❌ API 요청 시간 초과", "red")
        return False
    except requests.exceptions.ConnectionError:
        print_colored("❌ API 연결 실패 (네트워크 문제)", "red")
        return False
    except Exception as e:
        print_colored(f"❌ API 테스트 오류: {str(e)}", "red")
        return False


def main():
    """메인 테스트 함수"""
    parser = argparse.ArgumentParser(description="Mistral OCR 테스트 스크립트")
    parser.add_argument("image_path", nargs="?", help="테스트할 이미지 파일 경로")
    parser.add_argument("--api-only", action="store_true", help="API 연결 테스트만 실행")
    parser.add_argument("--no-api-test", action="store_true", help="API 연결 테스트 스킵")
    
    args = parser.parse_args()
    
    print_colored("🚀 Mistral OCR 테스트 시작", "cyan")
    print_colored(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "blue")
    print()
    
    # 환경변수 로드 (.env 파일이 있는 경우)
    env_file = ".env"
    if os.path.exists(env_file):
        print_colored(f"📄 환경변수 파일 로드: {env_file}", "blue")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    success_count = 0
    total_tests = 0
    
    # API 연결 테스트
    if not args.no_api_test:
        total_tests += 1
        if test_api_connectivity():
            success_count += 1
        print()
    
    if args.api_only:
        # API 테스트만 실행
        print_colored("🎯 API 연결 테스트만 실행했습니다.", "blue")
    else:
        # 기본 엔진 테스트
        total_tests += 1
        if test_mistral_ocr_engine():
            success_count += 1
        print()
        
        # 이미지 처리 테스트
        if args.image_path:
            total_tests += 1
            if test_image_processing(args.image_path):
                success_count += 1
        else:
            print_colored("💡 이미지 파일 경로를 제공하면 실제 OCR 테스트를 수행합니다.", "yellow")
            print_colored("   예시: python test_mistral_ocr.py test_image.jpg", "yellow")
    
    # 결과 요약
    print()
    print_colored("=" * 50, "blue")
    print_colored(f"🏁 테스트 완료: {success_count}/{total_tests} 성공", "cyan")
    
    if success_count == total_tests:
        print_colored("🎉 모든 테스트가 통과했습니다!", "green")
        return 0
    else:
        print_colored(f"⚠️  {total_tests - success_count}개 테스트가 실패했습니다.", "yellow")
        return 1


if __name__ == "__main__":
    sys.exit(main())

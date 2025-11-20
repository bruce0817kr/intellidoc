#!/bin/bash
# IntelliDoc 설정 및 테스트 스크립트

echo "============================================"
echo "🚀 IntelliDoc 설정 시작"
echo "============================================"

# 1. 가상환경 확인
if [ -z "$VIRTUAL_ENV" ]; then
    echo ""
    echo "⚠️  가상환경이 활성화되지 않았습니다."
    echo "   다음 명령어로 활성화하세요:"
    echo "   python -m venv venv && source venv/bin/activate"
    echo ""
fi

# 2. 의존성 설치
echo ""
echo "📦 의존성 설치 중..."
pip install -r requirements.in --quiet

# 3. 문법 체크
echo ""
echo "🔍 문법 체크 중..."
python -m py_compile ocr_engines/base.py
python -m py_compile llm_engines/base.py
python -m py_compile services/smart_processor.py

if [ $? -eq 0 ]; then
    echo "   ✓ 문법 체크 통과"
else
    echo "   ✗ 문법 오류 발견"
    exit 1
fi

# 4. Import 테스트
echo ""
echo "📥 Import 테스트 중..."

python << 'PYTHON'
import sys

# OCR 엔진 테스트
try:
    from ocr_engines.base import OCREngineFactory, OCRResult
    print("   ✓ OCR base 모듈 OK")
except ImportError as e:
    print(f"   ✗ OCR base 모듈 실패: {e}")
    sys.exit(1)

# LLM 엔진 테스트
try:
    from llm_engines.base import LLMEngineFactory, LLMResult
    print("   ✓ LLM base 모듈 OK")
except ImportError as e:
    print(f"   ✗ LLM base 모듈 실패: {e}")
    sys.exit(1)

# 스마트 프로세서 테스트
try:
    from services.smart_processor import SmartDocumentProcessor, ProcessingStrategy
    print("   ✓ SmartDocumentProcessor OK")
except ImportError as e:
    print(f"   ✗ SmartDocumentProcessor 실패: {e}")
    sys.exit(1)

print("\n✅ 모든 import 테스트 통과!")
PYTHON

# 5. API 키 확인
echo ""
echo "🔑 API 키 확인..."

if [ -n "$GEMINI_API_KEY" ]; then
    echo "   ✓ GEMINI_API_KEY 설정됨"
else
    echo "   ⚠️  GEMINI_API_KEY 미설정 (유료 API 사용 불가)"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo "   ✓ OPENAI_API_KEY 설정됨"
else
    echo "   ⚠️  OPENAI_API_KEY 미설정 (유료 API 사용 불가)"
fi

# 6. 테스트 실행
echo ""
echo "🧪 테스트 실행 중..."
pytest tests/test_smart_processor.py -v --tb=short 2>/dev/null

# 7. 완료
echo ""
echo "============================================"
echo "✅ IntelliDoc 설정 완료!"
echo "============================================"
echo ""
echo "📌 사용 방법:"
echo ""
echo "1. API 키 설정 (유료 API 사용 시):"
echo "   export GEMINI_API_KEY='your_key'"
echo "   export OPENAI_API_KEY='your_key'"
echo ""
echo "2. Python에서 사용:"
echo "   from services.smart_processor import SmartDocumentProcessor"
echo "   processor = SmartDocumentProcessor()"
echo "   result = processor.process_document('document.pdf')"
echo ""
echo "3. API 서버 시작:"
echo "   uvicorn web_api.main:app --reload"
echo ""

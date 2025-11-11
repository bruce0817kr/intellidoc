# IntelliDoc OCR/AI 통합 구현 가이드

## 📦 구현 완료 내용

### Phase 1-5 모두 완료 ✅

---

## 🏗️ 아키텍처

```
backend/
├── ocr_engines/           # OCR 엔진 모듈
│   ├── base.py           # 기본 클래스 및 팩토리
│   ├── tesseract_engine.py    # Tesseract OCR
│   ├── easyocr_engine.py      # EasyOCR (딥러닝)
│   └── camelot_engine.py      # Camelot (PDF 표 추출)
│
├── llm_engines/          # LLM 엔진 모듈
│   ├── base.py           # 기본 클래스 및 팩토리
│   ├── gemini_engine.py       # Gemini 2.5 Flash/Lite
│   └── openai_engine.py       # GPT-5 Nano/Mini/Standard
│
├── services/             # 비즈니스 로직
│   ├── smart_processor.py     # 스마트 문서 처리기
│   └── ocr_api.py             # API 엔드포인트
│
└── tests/                # 테스트
    ├── test_ocr_engines.py
    ├── test_llm_engines.py
    └── test_smart_processor.py
```

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 백엔드 디렉토리로 이동
cd backend

# 의존성 컴파일 및 설치
pip-compile requirements.in
pip install -r requirements.txt
```

### 2. API 키 설정

```bash
# .env 파일 생성
cat > .env << 'ENV'
# Gemini API 키
GEMINI_API_KEY=your_gemini_api_key_here

# OpenAI API 키
OPENAI_API_KEY=your_openai_api_key_here
ENV

# 환경 변수 로드
export $(cat .env | xargs)
```

### 3. 테스트 실행

```bash
# 모든 테스트
pytest tests/

# 특정 테스트
pytest tests/test_ocr_engines.py -v
pytest tests/test_llm_engines.py -v
pytest tests/test_smart_processor.py -v
```

---

## 💻 사용 예제

### 1. OCR 엔진 직접 사용

```python
from ocr_engines import OCREngineFactory

# Tesseract OCR
tesseract = OCREngineFactory.create("tesseract", {
    "lang": "eng+kor",
    "psm": 3
})

result = tesseract.extract_text_with_timing("document.jpg")
print(f"Text: {result.text}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Time: {result.processing_time:.2f}s")

# EasyOCR (딥러닝)
easyocr = OCREngineFactory.create("easyocr", {
    "languages": ['en', 'ko'],
    "use_gpu": True
})

result = easyocr.extract_text("complex_document.jpg")
print(f"Blocks: {len(result.metadata['text_blocks'])}")

# Camelot (PDF 표 추출)
camelot = OCREngineFactory.create("camelot", {
    "flavor": "lattice"
})

result = camelot.extract_tables_from_pdf("tables.pdf", pages="all")
print(f"Found {result.metadata['table_count']} tables")
for table in result.metadata['tables']:
    print(f"Table {table['table_number']}: {table['rows']}x{table['cols']}")
    print(table['markdown'])
```

### 2. LLM 엔진 직접 사용

```python
import os
from llm_engines import LLMEngineFactory

# Gemini 2.5 Flash-Lite (가장 저렴)
gemini = LLMEngineFactory.create("gemini_flash_lite", {
    "api_key": os.getenv("GEMINI_API_KEY"),
    "model": "gemini-2.5-flash-lite"
})

# 이미지에서 텍스트 추출
result = gemini.process_image(
    ["document1.jpg", "document2.jpg"],
    prompt="Extract all text and tables from these documents."
)

print(f"Extracted text: {result.text}")
print(f"Cost: ${result.cost:.6f}")
print(f"Tokens: {result.usage['total_tokens']}")

# PDF 처리 (최대 1,500페이지)
result = gemini.process_pdf(
    "contract.pdf",
    prompt="Extract key information: parties, dates, amounts, terms.",
    max_pages=50
)

# 구조화 데이터 추출
schema = {
    "contract_number": "string",
    "parties": ["string"],
    "start_date": "date",
    "end_date": "date",
    "total_amount": "number"
}

result = gemini.extract_structured_data(
    ["contract_page1.jpg", "contract_page2.jpg"],
    schema=schema
)

if result.metadata["parsing_success"]:
    data = result.metadata["parsed_data"]
    print(f"Contract: {data}")

# GPT-5 Nano (최저가)
gpt5_nano = LLMEngineFactory.create("gpt5_nano", {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "model": "gpt-5-nano"
})

# 문서 요약
result = gpt5_nano.analyze_document(
    document_text,
    task="summarize"
)

print(f"Summary: {result.text}")
print(f"Cost: ${result.cost:.6f}")

# 개체 추출 (JSON 모드)
result = gpt5_nano.analyze_document(
    document_text,
    task="extract_entities"
)

entities = result.metadata["parsed_data"]
print(f"People: {entities.get('people', [])}")
print(f"Organizations: {entities.get('organizations', [])}")
print(f"Dates: {entities.get('dates', [])}")
print(f"Amounts: {entities.get('amounts', [])}")

# GPT-5 Mini (고급 분석)
gpt5_mini = LLMEngineFactory.create("gpt5_mini", {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "model": "gpt-5-mini"
})

# 이미지 분석
result = gpt5_mini.process_image(
    ["chart.jpg"],
    prompt="Analyze this chart and describe the trends."
)

print(result.text)
```

### 3. 스마트 문서 처리기 사용 (권장)

```python
from services.smart_processor import (
    SmartDocumentProcessor,
    ProcessingStrategy
)

# 프로세서 초기화
processor = SmartDocumentProcessor({
    "use_gpu": False,  # GPU 사용 (EasyOCR)
    "gemini_api_key": os.getenv("GEMINI_API_KEY"),
    "openai_api_key": os.getenv("OPENAI_API_KEY")
})

# 자동 전략 선택 (비용 최적화)
result = processor.process_document("document.pdf")

print(f"Strategy: {result.strategy}")
print(f"Text length: {len(result.text)} chars")
print(f"Tables: {len(result.tables)}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Cost: ${result.cost:.6f}")
print(f"Time: {result.processing_time:.2f}s")

# 복잡도 분석
complexity = processor.analyze_complexity("document.pdf")

print(f"Complexity score: {complexity.complexity_score}/100")
print(f"Has tables: {complexity.has_tables}")
print(f"Complex layout: {complexity.has_complex_layout}")
print(f"Low confidence: {complexity.has_low_confidence}")
print(f"Handwritten: {complexity.is_handwritten}")
print(f"Multi-language: {complexity.is_multi_language}")
print(f"Recommended: {complexity.recommended_strategy.value}")

# 특정 전략 사용
result = processor.process_document(
    "contract.pdf",
    strategy=ProcessingStrategy.GEMINI_PRIMARY,
    prompt="Extract contract terms and key dates."
)

# 배치 처리
files = [
    "document1.pdf",
    "document2.pdf",
    "document3.jpg",
    "document4.pdf"
]

results = processor.batch_process(files)

total_cost = sum(r.cost for r in results)
print(f"Processed {len(results)} files")
print(f"Total cost: ${total_cost:.4f}")

for i, result in enumerate(results):
    print(f"\nFile {i+1}: {result.strategy}")
    print(f"  Confidence: {result.confidence:.2%}")
    print(f"  Cost: ${result.cost:.6f}")
    print(f"  Time: {result.processing_time:.2f}s")

# 비용 예측
estimate = processor.get_cost_estimate(
    files,
    strategy=ProcessingStrategy.GEMINI_PRIMARY
)

print(f"\nCost Estimate:")
print(f"Total files: {estimate['total_files']}")
print(f"Estimated cost: ${estimate['total_estimated_cost']:.4f}")
```

---

## 🌐 API 사용

### FastAPI 엔드포인트 통합

```python
# backend/web_api/main.py에 추가

from fastapi import FastAPI
from services.ocr_api import router as ocr_router

app = FastAPI()

# OCR/AI 라우터 등록
app.include_router(ocr_router)

# 서버 실행
# uvicorn web_api.main:app --reload
```

### API 호출 예제

```bash
# 1. 문서 처리 (자동 전략)
curl -X POST "http://localhost:8000/api/v1/ocr/process" \
  -F "file=@document.pdf"

# 2. 문서 처리 (Gemini 전략)
curl -X POST "http://localhost:8000/api/v1/ocr/process" \
  -F "file=@document.pdf" \
  -F "strategy=gemini" \
  -F "prompt=Extract all tables and convert to JSON"

# 3. 복잡도 분석
curl -X POST "http://localhost:8000/api/v1/ocr/analyze-complexity" \
  -F "file=@document.pdf"

# 4. 사용 가능한 엔진 목록
curl "http://localhost:8000/api/v1/ocr/engines"

# 5. 가격 정보
curl "http://localhost:8000/api/v1/ocr/pricing"
```

### Python에서 API 호출

```python
import requests

# 문서 처리
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/ocr/process",
        files={"file": f},
        data={
            "strategy": "cost_optimized",
            "prompt": "Summarize this document in 3 sentences."
        }
    )

result = response.json()
print(f"Text: {result['text']}")
print(f"Cost: ${result['cost']:.6f}")
print(f"Strategy: {result['strategy']}")

# 복잡도 분석
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/ocr/analyze-complexity",
        files={"file": f}
    )

complexity = response.json()
print(f"Complexity: {complexity['complexity_score']}/100")
print(f"Recommended: {complexity['recommended_strategy']}")
```

---

## 💰 비용 최적화 전략

### 전략별 비용 (페이지당)

| 전략 | 비용/페이지 | 정확도 | 속도 | 사용 시나리오 |
|------|-----------|--------|------|--------------|
| **OPENSOURCE_ONLY** | $0 | 88-94% | 1-2초 | 단순 텍스트 문서 |
| **HYBRID_VERIFY** | $0-0.01 | 94-96% | 2-4초 | 중간 복잡도 문서 |
| **GEMINI_PRIMARY** | $0.008-0.01 | 96-98% | 3-4초 | 표, 복잡한 레이아웃 |
| **GPT5_NANO** | $0.005 | 93-95% | 3-4초 | 고급 텍스트 분석 |
| **GPT5_MINI** | $0.03 | 95-97% | 4-5초 | 계약서 분석, 손글씨 |

### 자동 전략 선택 로직

```
복잡도 점수 계산:
├── 표 포함: +30점
├── 낮은 신뢰도 (<0.8): +25점
├── 복잡한 레이아웃 (>500 단어): +20점
├── 손글씨 감지: +40점
└── 다국어: +15점

전략 선택:
├── 0-30점 → OPENSOURCE_ONLY ($0)
├── 31-50점 → HYBRID_VERIFY ($0-0.01)
├── 51-70점 → GEMINI_PRIMARY ($0.01)
└── 71-100점 → GPT5_MINI ($0.03)
```

### 월간 비용 예측

```python
# 월간 1,000건 처리 시나리오

# 시나리오 1: 모두 오픈소스 (단순 문서)
# 1,000건 × $0 = $0

# 시나리오 2: 하이브리드 (80% 오픈소스, 20% Gemini)
# 800건 × $0 + 200건 × $0.01 = $2

# 시나리오 3: Gemini 위주 (복잡 문서)
# 1,000건 × $0.01 = $10

# 시나리오 4: GPT-5 Mini (고급 분석)
# 1,000건 × $0.03 = $30

# 기존 GPT-4 Vision 사용 시
# 1,000건 × $0.15 = $150

# 절감액: $120-$150 (80-100%)
```

---

## 🔧 환경별 설정

### 개발 환경

```python
config = {
    "use_gpu": False,  # GPU 없음
    "gemini_api_key": os.getenv("GEMINI_API_KEY"),
    "openai_api_key": os.getenv("OPENAI_API_KEY")
}

processor = SmartDocumentProcessor(config)
```

### 프로덕션 환경 (GPU 있음)

```python
config = {
    "use_gpu": True,  # GPU 사용 (EasyOCR 가속)
    "gemini_api_key": os.getenv("GEMINI_API_KEY"),
    "openai_api_key": os.getenv("OPENAI_API_KEY")
}

processor = SmartDocumentProcessor(config)
```

### 오픈소스만 사용 (API 키 없음)

```python
config = {
    "use_gpu": False
}

processor = SmartDocumentProcessor(config)

# 자동으로 오픈소스 전략만 사용
result = processor.process_document("document.pdf")
# 항상 strategy="opensource_only"
```

---

## 📊 모니터링 및 로깅

### 비용 추적

```python
from datetime import datetime
import json

class CostTracker:
    def __init__(self):
        self.costs = []

    def track(self, result):
        self.costs.append({
            "timestamp": datetime.now().isoformat(),
            "strategy": result.strategy,
            "cost": result.cost,
            "processing_time": result.processing_time,
            "confidence": result.confidence
        })

    def get_daily_report(self):
        total_cost = sum(c["cost"] for c in self.costs)
        total_docs = len(self.costs)

        strategies = {}
        for c in self.costs:
            strategy = c["strategy"]
            if strategy not in strategies:
                strategies[strategy] = {"count": 0, "cost": 0.0}
            strategies[strategy]["count"] += 1
            strategies[strategy]["cost"] += c["cost"]

        return {
            "total_documents": total_docs,
            "total_cost": total_cost,
            "avg_cost_per_doc": total_cost / total_docs if total_docs > 0 else 0,
            "strategies": strategies
        }

# 사용
tracker = CostTracker()

for file_path in document_files:
    result = processor.process_document(file_path)
    tracker.track(result)

report = tracker.get_daily_report()
print(json.dumps(report, indent=2))

# 출력 예시:
# {
#   "total_documents": 100,
#   "total_cost": 0.85,
#   "avg_cost_per_doc": 0.0085,
#   "strategies": {
#     "opensource_only": {"count": 60, "cost": 0.0},
#     "gemini_primary": {"count": 30, "cost": 0.30},
#     "gpt5_nano": {"count": 10, "cost": 0.05}
#   }
# }
```

---

## 🚦 에러 처리

### 재시도 로직

```python
import time

def process_with_retry(
    processor,
    file_path,
    max_retries=3,
    backoff=2
):
    """재시도 로직이 있는 문서 처리"""

    for attempt in range(max_retries):
        try:
            result = processor.process_document(file_path)
            return result

        except Exception as e:
            if attempt == max_retries - 1:
                # 마지막 재시도 실패
                raise

            wait_time = backoff ** attempt
            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {wait_time}s...")
            time.sleep(wait_time)

# 사용
try:
    result = process_with_retry(processor, "document.pdf")
    print(f"Success: {result.strategy}")
except Exception as e:
    print(f"Failed after retries: {e}")
```

### Fallback 전략

```python
def process_with_fallback(processor, file_path):
    """Fallback 전략이 있는 문서 처리"""

    strategies = [
        ProcessingStrategy.COST_OPTIMIZED,
        ProcessingStrategy.GEMINI_PRIMARY,
        ProcessingStrategy.OPENSOURCE_ONLY
    ]

    last_error = None

    for strategy in strategies:
        try:
            result = processor.process_document(file_path, strategy)
            return result
        except Exception as e:
            last_error = e
            print(f"Strategy {strategy.value} failed: {e}")
            continue

    # 모든 전략 실패
    raise Exception(f"All strategies failed. Last error: {last_error}")
```

---

## 📈 성능 최적화

### 배치 처리 최적화

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_process_parallel(
    processor,
    file_paths,
    max_workers=4
):
    """병렬 배치 처리"""

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 작업 제출
        future_to_file = {
            executor.submit(processor.process_document, file_path): file_path
            for file_path in file_paths
        }

        # 결과 수집
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                print(f"✓ {file_path}: {result.strategy}")
            except Exception as e:
                print(f"✗ {file_path}: {e}")

    return results

# 사용
results = batch_process_parallel(
    processor,
    document_files,
    max_workers=4
)

print(f"Processed {len(results)}/{len(document_files)} files")
```

---

## 🎯 다음 단계

### 프로덕션 배포 체크리스트

- [ ] API 키 환경 변수 설정 (`GEMINI_API_KEY`, `OPENAI_API_KEY`)
- [ ] GPU 인스턴스 설정 (EasyOCR 가속)
- [ ] Redis 캐싱 통합
- [ ] 비용 모니터링 대시보드 설정
- [ ] 로그 수집 및 분석 (Prometheus + Grafana)
- [ ] API 엔드포인트 보안 (인증, rate limiting)
- [ ] 에러 알림 설정
- [ ] 문서 스토리지 최적화
- [ ] 부하 테스트

### 추가 기능 개발

- [ ] 테이블 추출 고도화 (CSV, Excel 내보내기)
- [ ] 문서 분류 모델 추가
- [ ] 핸드라이팅 전문 OCR (TrOCR)
- [ ] LayoutLMv3 통합 (문서 이해)
- [ ] 웹 UI 대시보드
- [ ] 배치 처리 스케줄러
- [ ] A/B 테스트 프레임워크

---

## 📚 참고 자료

### API 문서

- [Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [EasyOCR GitHub](https://github.com/JaidedAI/EasyOCR)
- [Camelot Docs](https://camelot-py.readthedocs.io/)

### 관련 문서

- `OPTIMIZED_OCR_AI_STRATEGY_2025.md` - 전략 및 분석
- `OCR_AI_ENHANCEMENT_PROPOSAL.md` - 초기 제안서
- `FINAL_COMPREHENSIVE_REPORT.md` - Phase 0-4 보고서

---

**작성일:** 2025-11-11  
**버전:** 1.0  
**상태:** ✅ 모든 Phase 구현 완료

# IntelliDoc MongoDB 연동 및 확장성 진단 가이드

## 목차
1. [소개](#1-소개)
2. [MongoDB 연동 방안](#2-mongodb-연동-방안)
3. [데이터 매핑 및 변환](#3-데이터-매핑-및-변환)
4. [보안 및 트랜잭션 처리](#4-보안-및-트랜잭션-처리)
5. [성능 및 장애 대응](#5-성능-및-장애-대응)
6. [IntelliDoc 확장성 진단](#6-intellidoc-확장성-진단)
7. [확장성 개선 권고](#7-확장성-개선-권고)
8. [커스터마이징 및 추가 개발](#8-커스터마이징-및-추가-개발)

## 1. 소개

이 문서는 IntelliDoc 시스템에서 추출된 기업 데이터를 외부 평가 시스템(MongoDB 기반)과 연동하는 방법과 IntelliDoc 시스템 자체의 확장성에 대한 진단 결과를 제공합니다. IntelliDoc은 모듈식 아키텍처를 기반으로 설계되어 외부 시스템과의 연동 및 확장이 용이합니다.

## 2. MongoDB 연동 방안

IntelliDoc에서 처리된 데이터를 평가 시스템의 MongoDB에 연동하는 방법은 크게 세 가지가 있습니다. 각 방법은 장단점이 있으므로, 평가 시스템의 요구사항, 실시간성, 개발 리소스 등을 고려하여 적절한 방식을 선택해야 합니다.

### 2.1 방법 1: IntelliDoc API 활용 (권장)

**개요:** 평가 시스템에서 IntelliDoc API를 주기적으로 호출하여 처리 완료된 문서의 데이터를 가져와 MongoDB에 저장하는 방식입니다.

**장점:**
- IntelliDoc 시스템의 변경 없이 연동 가능합니다.
- 평가 시스템이 데이터 동기화 시점과 로직을 제어할 수 있습니다.
- REST API 표준을 따르므로 구현이 비교적 용이합니다.

**단점:**
- 실시간 동기화가 어렵습니다 (주기적 폴링 필요).
- API 호출량에 따라 비용이 발생할 수 있습니다 (외부 API 사용 시).
- 평가 시스템 측에서 API 호출 및 데이터 처리 로직 개발이 필요합니다.

**구현 단계:**
1.  **API 키 발급**: IntelliDoc 관리자 인터페이스에서 API 키를 발급받습니다.
2.  **처리 완료 문서 조회**: 평가 시스템에서 `/documents` API를 주기적으로 호출하여 `status=COMPLETED`인 문서를 조회합니다.
3.  **데이터 조회**: 처리 완료된 문서 ID를 사용하여 `/documents/{document_id}/ocr/result`, `/documents/{document_id}/llm/result`, `/documents/{document_id}/template_result` API를 호출하여 필요한 데이터를 가져옵니다.
4.  **데이터 변환 및 저장**: 가져온 데이터를 평가 시스템의 MongoDB 스키마에 맞게 변환하여 저장합니다.
5.  **상태 업데이트**: 데이터 동기화가 완료된 문서는 IntelliDoc에서 별도 상태(예: `SYNCED`)로 업데이트하거나, 평가 시스템 내부적으로 동기화 상태를 관리합니다.

**예제 코드 (Python):**
```python
import requests
import time
from pymongo import MongoClient

INTELLIDOC_API_URL = "https://api.intellidoc.com/v1"
API_KEY = "your_intellidoc_api_key"
MONGO_URI = "mongodb://your_mongo_user:your_mongo_password@your_mongo_host:27017/"
MONGO_DB = "evaluation_system_db"
MONGO_COLLECTION = "company_data"

headers = {"X-API-Key": API_KEY}

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
collection = db[MONGO_COLLECTION]

def get_completed_documents(last_sync_time):
    params = {
        "status": "COMPLETED",
        "updated_since": last_sync_time, # 예시: 특정 시간 이후 업데이트된 문서만 조회
        "limit": 100
    }
    response = requests.get(f"{INTELLIDOC_API_URL}/documents", headers=headers, params=params)
    response.raise_for_status()
    return response.json()["data"]["items"]

def get_document_data(doc_id):
    data = {}
    try:
        # OCR 결과
        ocr_res = requests.get(f"{INTELLIDOC_API_URL}/documents/{doc_id}/ocr/result", headers=headers)
        ocr_res.raise_for_status()
        data["ocr"] = ocr_res.json()["data"]
        
        # LLM 결과
        llm_res = requests.get(f"{INTELLIDOC_API_URL}/documents/{doc_id}/llm/result", headers=headers)
        if llm_res.status_code == 200:
             data["llm"] = llm_res.json()["data"]
             
        # 템플릿 결과 (필요시)
        # template_res = requests.get(f"{INTELLIDOC_API_URL}/documents/{doc_id}/template_result", headers=headers)
        # if template_res.status_code == 200:
        #     data["template"] = template_res.json()["data"]
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {doc_id}: {e}")
        return None
    return data

def transform_data(intellidoc_data):
    # IntelliDoc 데이터를 평가 시스템 MongoDB 스키마에 맞게 변환
    # 예시: 기업명, 재무 정보, 주요 키워드 등을 추출하여 매핑
    transformed = {
        "source_document_id": intellidoc_data["ocr"]["document_id"],
        "company_name": None, # LLM 결과 등에서 추출
        "financial_data": {},
        "keywords": [],
        "raw_text": "".join([page["text"] for page in intellidoc_data["ocr"]["pages"]]),
        "processed_at": intellidoc_data["ocr"].get("completed_at")
    }
    # ... 상세 변환 로직 구현 ...
    return transformed

def sync_data():
    last_sync_time = get_last_sync_time() # 마지막 동기화 시간 조회 로직
    documents = get_completed_documents(last_sync_time)
    
    for doc in documents:
        doc_id = doc["id"]
        print(f"Processing document: {doc_id}")
        intellidoc_data = get_document_data(doc_id)
        
        if intellidoc_data:
            transformed_data = transform_data(intellidoc_data)
            try:
                collection.update_one(
                    {"source_document_id": doc_id},
                    {"$set": transformed_data},
                    upsert=True
                )
                print(f"Successfully synced document: {doc_id}")
                # 동기화 완료 상태 업데이트 (IntelliDoc API 또는 내부 DB)
            except Exception as e:
                print(f"Error saving data for {doc_id} to MongoDB: {e}")
                
    update_last_sync_time() # 현재 시간으로 마지막 동기화 시간 업데이트

# 주기적으로 sync_data() 함수 실행 (예: cron, Celery Beat)
# sync_data()
```

### 2.2 방법 2: IntelliDoc 웹훅 활용

**개요:** IntelliDoc에서 문서 처리가 완료될 때마다 설정된 웹훅 URL로 이벤트 알림을 보내고, 평가 시스템은 이 알림을 받아 해당 문서 데이터를 API로 조회하여 MongoDB에 저장하는 방식입니다.

**장점:**
- 실시간 또는 준실시간 데이터 동기화가 가능합니다.
- 주기적인 폴링이 필요 없어 리소스 효율적입니다.
- 이벤트 기반 아키텍처로 시스템 간 결합도를 낮출 수 있습니다.

**단점:**
- 평가 시스템 측에서 웹훅 엔드포인트 개발 및 관리가 필요합니다.
- 웹훅 실패 시 재시도 및 오류 처리 로직이 필요합니다.
- 초기 설정(웹훅 등록)이 필요합니다.

**구현 단계:**
1.  **웹훅 엔드포인트 개발**: 평가 시스템에 IntelliDoc 이벤트를 수신할 HTTP 엔드포인트를 개발합니다. (API 문서의 웹훅 서명 검증 로직 포함)
2.  **웹훅 등록**: IntelliDoc API(`/webhooks`)를 사용하여 개발된 엔드포인트 URL과 수신할 이벤트(`ocr.completed`, `llm.completed` 등)를 등록합니다.
3.  **이벤트 수신 및 처리**: 웹훅 엔드포인트에서 이벤트 알림을 받으면, 알림에 포함된 `document_id`를 사용하여 IntelliDoc API로 상세 데이터를 조회합니다.
4.  **데이터 변환 및 저장**: 조회한 데이터를 평가 시스템 MongoDB 스키마에 맞게 변환하여 저장합니다.
5.  **응답**: 웹훅 요청에 대해 성공(HTTP 200 OK) 응답을 보내야 합니다. 실패 시 IntelliDoc은 일정 횟수 재시도합니다.

**예제 코드 (Python Flask 웹훅 엔드포인트):**
```python
from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import json
from pymongo import MongoClient

app = Flask(__name__)

INTELLIDOC_API_URL = "https://api.intellidoc.com/v1"
API_KEY = "your_intellidoc_api_key"
WEBHOOK_SECRET = "your_webhook_secret"
MONGO_URI = "mongodb://your_mongo_user:your_mongo_password@your_mongo_host:27017/"
MONGO_DB = "evaluation_system_db"
MONGO_COLLECTION = "company_data"

headers = {"X-API-Key": API_KEY}

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
collection = db[MONGO_COLLECTION]

def verify_signature(payload, signature):
    mac = hmac.new(WEBHOOK_SECRET.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)

def get_document_data(doc_id):
    # ... (API 활용 방식의 get_document_data 함수와 동일)
    pass

def transform_data(intellidoc_data):
    # ... (API 활용 방식의 transform_data 함수와 동일)
    pass

@app.route("/intellidoc-webhook", methods=["POST"])
def handle_webhook():
    signature = request.headers.get("X-IntelliDoc-Signature")
    payload = request.get_data()
    
    if not signature or not verify_signature(payload, signature):
        return jsonify({"error": "Invalid signature"}), 401
        
    event_data = json.loads(payload)
    event_type = event_data.get("event")
    data = event_data.get("data")
    
    print(f"Received webhook event: {event_type}")
    
    if event_type in ["ocr.completed", "llm.completed"] and data:
        doc_id = data.get("document_id")
        if doc_id:
            print(f"Processing document from webhook: {doc_id}")
            intellidoc_data = get_document_data(doc_id)
            if intellidoc_data:
                transformed_data = transform_data(intellidoc_data)
                try:
                    collection.update_one(
                        {"source_document_id": doc_id},
                        {"$set": transformed_data},
                        upsert=True
                    )
                    print(f"Successfully synced document via webhook: {doc_id}")
                except Exception as e:
                    print(f"Error saving data for {doc_id} to MongoDB: {e}")
                    # 실패 시 재처리 큐에 넣는 등의 로직 추가 가능
                    return jsonify({"error": "Failed to process data"}), 500
            else:
                 print(f"Failed to fetch data for document: {doc_id}")
                 return jsonify({"error": "Failed to fetch document data"}), 500
        else:
            print("Webhook data missing document_id")
            
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(port=5001)
```

### 2.3 방법 3: IntelliDoc 백엔드 직접 수정 (비권장)

**개요:** IntelliDoc 백엔드 코드(예: Celery 태스크)를 직접 수정하여, 문서 처리가 완료되는 시점에 평가 시스템의 MongoDB에 데이터를 직접 저장하는 방식입니다.

**장점:**
- 완전한 실시간 동기화가 가능합니다.
- 별도의 외부 API 호출이나 웹훅 엔드포인트가 필요 없습니다.

**단점:**
- IntelliDoc 시스템의 코드를 직접 수정해야 하므로, 향후 IntelliDoc 업데이트 시 충돌이 발생하거나 유지보수가 어려워질 수 있습니다.
- IntelliDoc과 평가 시스템 간의 결합도가 높아집니다.
- IntelliDoc 백엔드 환경에 MongoDB 클라이언트 라이브러리 설치 및 연결 설정이 필요합니다.
- 오류 처리 및 트랜잭션 관리가 더 복잡해질 수 있습니다.

**구현 단계:**
1.  **MongoDB 라이브러리 설치**: IntelliDoc 백엔드 환경(`backend/requirements.txt`)에 `pymongo` 라이브러리를 추가하고 설치합니다.
2.  **MongoDB 연결 설정**: IntelliDoc 설정 파일(`backend/shared/config.py`) 또는 환경 변수에 MongoDB 연결 정보를 추가합니다.
3.  **Celery 태스크 수정**: 문서 처리 완료 관련 Celery 태스크(`backend/celery_app/tasks.py`의 `process_ocr_result`, `process_llm_result` 등) 내부에 MongoDB 저장 로직을 추가합니다.
4.  **데이터 변환 로직 추가**: IntelliDoc 내부 데이터 구조를 평가 시스템 스키마에 맞게 변환하는 로직을 구현합니다.
5.  **오류 처리**: MongoDB 저장 실패 시 로깅 및 재시도 로직을 구현합니다.

**결론:** 특별한 이유가 없는 한, **방법 1(API 활용)** 또는 **방법 2(웹훅 활용)**를 사용하는 것이 시스템 간 결합도를 낮추고 유지보수성을 높이는 데 유리합니다. 실시간성이 중요하다면 웹훅 방식, 평가 시스템에서 동기화 제어가 필요하다면 API 방식을 추천합니다.

## 3. 데이터 매핑 및 변환

IntelliDoc에서 추출된 데이터(OCR 텍스트, LLM 분석 결과, 템플릿 필드)를 평가 시스템의 MongoDB 스키마에 맞게 매핑하고 변환하는 과정이 필요합니다.

### 3.1 매핑 전략 수립
- **필드 식별**: 평가 시스템에서 필요한 데이터 필드(예: 기업명, 사업자등록번호, 재무제표 항목, 주요 계약 조건 등)를 명확히 정의합니다.
- **소스 식별**: 각 필드에 해당하는 데이터를 IntelliDoc의 어떤 결과(OCR 텍스트, LLM 추출 정보, 템플릿 필드)에서 가져올지 결정합니다.
- **변환 규칙 정의**: 데이터 형식 변환(예: 날짜 형식 통일, 숫자 형식 변환, 텍스트 정규화), 단위 변환, 코드 매핑 등의 규칙을 정의합니다.

### 3.2 변환 로직 구현
- 위에서 선택한 연동 방식(API, 웹훅, 직접 수정)에 따라 적절한 위치에 변환 로직을 구현합니다.
- Python의 딕셔너리, 정규식, 날짜/시간 라이브러리 등을 활용하여 데이터를 가공합니다.
- 복잡한 변환 로직은 별도의 함수나 클래스로 모듈화하여 관리하는 것이 좋습니다.

**예시 (Python):**
```python
def transform_intellidoc_to_evaluation(intellidoc_data):
    eval_data = {}
    eval_data["source_doc_id"] = intellidoc_data.get("document_id")
    
    # 기업명 추출 (LLM 결과 활용)
    company_name = find_value_in_llm_result(intellidoc_data.get("llm"), "extract_info", "company_name")
    eval_data["company_name"] = company_name
    
    # 재무 정보 추출 (템플릿 또는 LLM 결과 활용)
    financials = {}
    sales = find_value_in_llm_result(intellidoc_data.get("llm"), "extract_info", "sales")
    if sales:
        financials["sales"] = parse_currency(sales)
    # ... 기타 재무 항목 ...
    eval_data["financial_data"] = financials
    
    # 날짜 형식 변환
    doc_date = find_value_in_llm_result(intellidoc_data.get("llm"), "extract_info", "document_date")
    if doc_date:
        eval_data["document_date"] = format_date(doc_date, "%Y-%m-%d")
        
    # 원본 텍스트
    if intellidoc_data.get("ocr"): 
        eval_data["raw_text"] = "\n".join([p.get("text", "") for p in intellidoc_data["ocr"].get("pages", [])])
        
    return eval_data

# Helper 함수들 (find_value_in_llm_result, parse_currency, format_date 등) 구현 필요
```

## 4. 보안 및 트랜잭션 처리

### 4.1 보안 고려사항
- **API 키/시크릿 관리**: IntelliDoc API 키 및 웹훅 시크릿은 안전하게 보관하고, 환경 변수나 시크릿 관리 도구를 통해 관리합니다.
- **HTTPS 통신**: IntelliDoc API 및 웹훅 엔드포인트는 모두 HTTPS를 사용해야 합니다.
- **웹훅 서명 검증**: 수신된 웹훅 요청의 서명을 반드시 검증하여 요청의 무결성과 출처를 확인합니다.
- **데이터 접근 제어**: MongoDB 접근 권한을 최소화하고, 필요한 서비스 계정만 접근하도록 설정합니다.
- **민감 정보 처리**: 연동 과정에서 민감 정보(개인정보, 기업 기밀 등)가 포함될 경우, 마스킹 또는 암호화 등의 보호 조치를 적용합니다.

### 4.2 트랜잭션 및 데이터 일관성
- **멱등성**: API 호출이나 웹훅 처리가 여러 번 발생하더라도 결과가 동일하도록 멱등성을 보장하는 것이 중요합니다. MongoDB의 `update_one` 또는 `find_one_and_update`와 `upsert=True` 옵션을 활용할 수 있습니다.
- **오류 처리 및 재시도**: API 호출 실패나 웹훅 처리 중 오류 발생 시, 로깅과 함께 적절한 재시도 메커니즘(예: 지수 백오프)을 구현합니다.
- **상태 관리**: IntelliDoc 문서의 동기화 상태를 명확히 관리하여 중복 처리나 누락을 방지합니다. (예: IntelliDoc 문서 메타데이터에 `sync_status` 필드 추가 또는 평가 시스템 DB에 동기화 로그 저장)
- **분산 트랜잭션 (필요시)**: IntelliDoc 상태 변경과 MongoDB 저장을 원자적으로 처리해야 하는 복잡한 시나리오에서는 분산 트랜잭션 패턴(예: Saga 패턴)을 고려할 수 있으나, 구현 복잡도가 높습니다. 대부분의 경우 멱등성과 재시도로 충분합니다.

## 5. 성능 및 장애 대응

### 5.1 성능 최적화
- **비동기 처리**: 웹훅 엔드포인트에서는 요청을 빠르게 수신하고 실제 데이터 처리 로직은 백그라운드 작업(예: Celery, RQ)으로 넘겨 응답 시간을 단축합니다.
- **배치 처리**: API 폴링 방식의 경우, 여러 문서를 한 번에 처리하는 배치 로직을 구현하여 API 호출 횟수를 줄입니다.
- **MongoDB 최적화**: 평가 시스템 MongoDB의 쓰기 성능을 고려하여 적절한 인덱스를 생성하고, 필요한 경우 샤딩(Sharding)을 검토합니다.
- **IntelliDoc API 제한**: IntelliDoc API의 요청 한도(Rate Limit)를 확인하고, 초과하지 않도록 호출 빈도를 조절합니다.

### 5.2 장애 대응
- **로깅 및 모니터링**: 연동 과정의 각 단계에서 상세한 로그를 기록하고, 오류 발생 시 알림(예: Sentry, Slack)을 설정합니다.
- **재시도 메커니즘**: 일시적인 네트워크 오류나 API 오류 발생 시 자동으로 재시도하는 로직을 구현합니다.
- **데드 레터 큐 (Dead Letter Queue)**: 반복적인 실패로 처리가 불가능한 메시지나 이벤트는 별도의 큐에 저장하여 수동으로 분석 및 처리할 수 있도록 합니다.
- **회복 전략**: 연동 시스템 장애 발생 시, 동기화되지 못한 데이터를 추후 일괄 처리할 수 있는 방안을 마련합니다.

## 6. IntelliDoc 확장성 진단

IntelliDoc 시스템은 확장성을 고려하여 설계되었으며, 주요 특징은 다음과 같습니다:

### 6.1 강점
- **모듈식 아키텍처**: 각 기능(API 게이트웨이, 문서 처리, OCR, LLM 등)이 분리되어 있어 개별적인 확장이 용이합니다.
- **비동기 처리**: Celery를 사용하여 시간이 오래 걸리는 작업을 비동기적으로 처리하므로, API 응답 시간에 영향을 주지 않고 작업량을 늘릴 수 있습니다.
- **수평 확장**: 백엔드 API 서버와 Celery 워커는 상태를 가지지 않으므로(Stateless), 필요에 따라 인스턴스 수를 늘려 수평 확장이 가능합니다.
- **데이터베이스/캐시 확장성**: PostgreSQL과 Redis는 자체적으로 복제(Replication), 샤딩(Sharding), 클러스터링 등 다양한 확장 기능을 지원합니다.
- **엔진 추상화**: OCR 및 LLM 엔진이 추상화되어 있어, 성능 요구사항에 따라 더 강력한 엔진(예: 클라우드 기반 API)으로 쉽게 교체하거나 로드 밸런싱을 통해 여러 엔진을 동시에 사용할 수 있습니다.
- **컨테이너 기반**: Docker를 사용하여 배포되므로, Kubernetes와 같은 컨테이너 오케스트레이션 도구를 통해 손쉽게 확장 및 관리가 가능합니다.

### 6.2 잠재적 병목 지점 및 고려사항
- **데이터베이스 성능**: 문서 메타데이터 및 처리 결과가 증가함에 따라 데이터베이스 쿼리 성능이 저하될 수 있습니다. 정기적인 인덱스 최적화 및 느린 쿼리 분석이 필요합니다.
- **스토리지 용량 및 I/O**: 업로드된 원본 문서 및 처리 결과 파일이 저장되는 스토리지의 용량과 I/O 성능이 병목이 될 수 있습니다. 클라우드 스토리지(S3 등) 사용 또는 고성능 스토리지 도입을 고려해야 합니다.
- **Celery 워커 처리량**: 동시에 처리해야 하는 문서 수가 많아지면 Celery 워커의 처리량이 한계에 도달할 수 있습니다. 워커 수를 늘리거나, 더 성능 좋은 인스턴스를 사용해야 합니다.
- **Redis 성능**: 메시지 큐 및 캐시로 사용되는 Redis의 메모리 및 네트워크 대역폭이 병목이 될 수 있습니다. Redis 클러스터링 또는 더 큰 인스턴스 사용을 고려해야 합니다.
- **외부 API 의존성**: Google Vision, OpenAI 등 외부 API를 사용하는 경우, 해당 API의 요청 한도(Rate Limit) 및 응답 시간이 전체 성능에 영향을 줄 수 있습니다.
- **네트워크 대역폭**: 대용량 파일 업로드/다운로드 및 내부 서비스 간 통신량이 많아지면 네트워크 대역폭이 병목이 될 수 있습니다.

## 7. 확장성 개선 권고

IntelliDoc 시스템의 확장성을 더욱 향상시키기 위한 권고 사항입니다:

- **데이터베이스 읽기 복제 (Read Replica)**: 읽기 작업이 많은 경우, PostgreSQL 읽기 복제본을 구성하여 읽기 부하를 분산시킵니다.
- **데이터베이스 샤딩 (Sharding)**: 데이터 양이 매우 커질 경우, Citus와 같은 확장 기능을 사용하여 PostgreSQL을 샤딩하는 것을 고려합니다.
- **클라우드 스토리지 활용**: 문서 저장을 위해 로컬 볼륨 대신 AWS S3, Google Cloud Storage 등 확장성이 뛰어난 클라우드 스토리지를 사용합니다.
- **Celery 워커 최적화**: 작업 유형에 따라 별도의 큐와 워커 풀을 구성하고(예: OCR용 큐, LLM용 큐), 워커의 동시성(Concurrency) 설정을 튜닝합니다.
- **Redis 클러스터링**: Redis 부하가 높을 경우, Redis 클러스터를 구성하여 성능과 가용성을 높입니다.
- **API 게이트웨이 최적화**: API 요청량이 많아지면 FastAPI 인스턴스 수를 늘리고, 필요시 Nginx 등 리버스 프록시를 사용하여 로드 밸런싱 및 캐싱을 강화합니다.
- **마이크로서비스 분리 강화**: 특정 기능(예: 템플릿 처리, 사용자 관리)의 부하가 매우 높아지면, 해당 기능을 별도의 마이크로서비스로 완전히 분리하는 것을 고려합니다.
- **성능 모니터링 강화**: 각 컴포넌트의 성능 지표(응답 시간, 처리량, 오류율 등)를 상세히 모니터링하고, 병목 지점을 조기에 식별하여 대응합니다.

## 8. 커스터마이징 및 추가 개발

IntelliDoc은 확장성을 고려하여 설계되었으므로, 특정 요구사항에 맞게 커스터마이징하거나 추가 기능을 개발할 수 있습니다.

- **커스텀 OCR/LLM 엔진 추가**: 개발자 가이드의 지침에 따라 새로운 엔진 구현체를 추가합니다.
- **커스텀 데이터 추출 로직**: 특정 문서 유형이나 정보 추출 요구사항에 맞춰 데이터 처리 모듈(`data_processor`) 또는 Celery 태스크를 수정하거나 확장합니다.
- **커스텀 내보내기 형식**: 내보내기 모듈(`export`)에 새로운 형식 지원 로직을 추가합니다.
- **외부 시스템 연동 모듈**: 특정 외부 시스템(예: ERP, CRM)과의 연동을 위한 별도 모듈을 개발하고 API 또는 웹훅을 통해 통합합니다.
- **프론트엔드 UI/UX 개선**: 특정 사용자 그룹이나 워크플로우에 맞춰 프론트엔드 컴포넌트 및 페이지를 수정하거나 추가합니다.

추가 개발 시에는 개발자 가이드의 코드 구조 및 기여 가이드라인을 따르는 것이 좋습니다.

---

이 가이드에 대한 문의사항이나 추가 지원이 필요한 경우, 프로젝트 관리자에게 문의하거나 이슈 트래커에 등록해 주세요.

© 2025 IntelliDoc. All rights reserved.

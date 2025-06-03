# IntelliDoc API 문서

## 목차
1. [소개](#1-소개)
2. [인증](#2-인증)
3. [API 엔드포인트](#3-api-엔드포인트)
4. [오류 처리](#4-오류-처리)
5. [사용 예제](#5-사용-예제)
6. [웹훅](#6-웹훅)
7. [제한 사항](#7-제한-사항)
8. [확장성 고려사항](#8-확장성-고려사항)

## 1. 소개

IntelliDoc API는 OCR과 LLM을 활용한 문서 처리 기능을 외부 시스템에서 활용할 수 있도록 RESTful 인터페이스를 제공합니다. 이 문서는 API의 사용 방법, 엔드포인트, 요청/응답 형식, 오류 처리 등에 대한 정보를 제공합니다.

### 1.1 기본 URL
```
https://api.intellidoc.com/v1
```

### 1.2 응답 형식
모든 API 응답은 JSON 형식으로 제공됩니다. 기본 응답 구조는 다음과 같습니다:

성공 응답:
```json
{
  "status": "success",
  "data": { ... }
}
```

오류 응답:
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "오류 메시지",
    "details": { ... }
  }
}
```

## 2. 인증

### 2.1 API 키 인증
모든 API 요청은 API 키를 통한 인증이 필요합니다. API 키는 HTTP 요청 헤더에 포함되어야 합니다:

```
X-API-Key: your_api_key_here
```

### 2.2 API 키 생성
API 키는 IntelliDoc 웹 인터페이스의 '관리자 설정' > 'API 관리' 메뉴에서 생성할 수 있습니다. 생성된 API 키는 안전하게 보관해야 하며, 노출되었을 경우 즉시 재발급해야 합니다.

### 2.3 JWT 인증 (선택적)
일부 고급 기능이나 사용자 특정 작업의 경우 JWT 토큰 기반 인증을 사용할 수 있습니다:

```
Authorization: Bearer your_jwt_token_here
```

JWT 토큰은 `/auth/login` 엔드포인트를 통해 획득할 수 있습니다.

## 3. API 엔드포인트

### 3.1 인증 API

#### 3.1.1 로그인
```
POST /auth/login
```

**요청 본문:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "access_token": "jwt_access_token",
    "refresh_token": "jwt_refresh_token",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "user_id",
      "username": "username",
      "email": "email@example.com",
      "roles": ["user"]
    }
  }
}
```

#### 3.1.2 토큰 갱신
```
POST /auth/refresh
```

**요청 헤더:**
```
Authorization: Bearer your_refresh_token_here
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "access_token": "new_jwt_access_token",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

### 3.2 문서 API

#### 3.2.1 문서 목록 조회
```
GET /documents
```

**쿼리 파라미터:**
- `page`: 페이지 번호 (기본값: 1)
- `limit`: 페이지당 항목 수 (기본값: 20, 최대: 100)
- `status`: 문서 상태 필터 (예: PENDING, PROCESSING, COMPLETED, ERROR)
- `sort`: 정렬 기준 (예: created_at, -created_at)
- `search`: 검색어

**응답:**
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "document_id",
        "original_filename": "example.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "status": "COMPLETED",
        "created_at": "2025-06-01T12:00:00Z",
        "updated_at": "2025-06-01T12:05:30Z",
        "page_count": 5,
        "thumbnail_url": "https://api.intellidoc.com/thumbnails/document_id.jpg"
      },
      ...
    ],
    "pagination": {
      "total": 45,
      "page": 1,
      "limit": 20,
      "pages": 3
    }
  }
}
```

#### 3.2.2 문서 상세 조회
```
GET /documents/{document_id}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "id": "document_id",
    "original_filename": "example.pdf",
    "file_size": 1024000,
    "mime_type": "application/pdf",
    "status": "COMPLETED",
    "created_at": "2025-06-01T12:00:00Z",
    "updated_at": "2025-06-01T12:05:30Z",
    "page_count": 5,
    "thumbnail_url": "https://api.intellidoc.com/thumbnails/document_id.jpg",
    "ocr_status": "COMPLETED",
    "ocr_engine": "tesseract",
    "ocr_completed_at": "2025-06-01T12:03:45Z",
    "llm_status": "COMPLETED",
    "llm_engine": "openai",
    "llm_completed_at": "2025-06-01T12:05:30Z",
    "metadata": {
      "author": "John Doe",
      "created_date": "2025-05-15",
      "document_type": "invoice"
    }
  }
}
```

#### 3.2.3 문서 업로드
```
POST /documents/upload
```

**요청 헤더:**
```
Content-Type: multipart/form-data
```

**요청 본문:**
- `file`: 업로드할 파일 (필수)
- `metadata`: 문서 메타데이터 (선택, JSON 문자열)

**응답:**
```json
{
  "status": "success",
  "data": {
    "id": "document_id",
    "original_filename": "example.pdf",
    "file_size": 1024000,
    "mime_type": "application/pdf",
    "status": "PENDING",
    "created_at": "2025-06-01T12:00:00Z",
    "updated_at": "2025-06-01T12:00:00Z"
  }
}
```

#### 3.2.4 문서 삭제
```
DELETE /documents/{document_id}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "message": "문서가 성공적으로 삭제되었습니다."
  }
}
```

### 3.3 OCR API

#### 3.3.1 OCR 처리 시작
```
POST /documents/{document_id}/ocr
```

**요청 본문:**
```json
{
  "engine": "tesseract",  // 선택 사항: tesseract, google_vision, aws_textract
  "options": {
    "language": "kor+eng",  // 언어 설정 (Tesseract 엔진용)
    "enhance_image": true,  // 이미지 향상 처리 여부
    "deskew": true          // 기울기 보정 여부
  }
}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "job_id": "ocr_job_id",
    "document_id": "document_id",
    "status": "PROCESSING",
    "engine": "tesseract",
    "created_at": "2025-06-01T12:01:00Z",
    "estimated_completion_time": "2025-06-01T12:03:00Z"
  }
}
```

#### 3.3.2 OCR 처리 상태 조회
```
GET /documents/{document_id}/ocr/status
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "job_id": "ocr_job_id",
    "document_id": "document_id",
    "status": "PROCESSING",  // PENDING, PROCESSING, COMPLETED, ERROR
    "progress": 60,  // 진행률 (0-100)
    "engine": "tesseract",
    "created_at": "2025-06-01T12:01:00Z",
    "updated_at": "2025-06-01T12:02:30Z",
    "estimated_completion_time": "2025-06-01T12:03:00Z",
    "error": null  // 오류 발생 시 오류 정보
  }
}
```

#### 3.3.3 OCR 결과 조회
```
GET /documents/{document_id}/ocr/result
```

**쿼리 파라미터:**
- `page`: 특정 페이지만 조회 (선택 사항)
- `format`: 결과 형식 (text, json, hocr, 기본값: json)

**응답:**
```json
{
  "status": "success",
  "data": {
    "document_id": "document_id",
    "page_count": 5,
    "engine": "tesseract",
    "completed_at": "2025-06-01T12:03:45Z",
    "pages": [
      {
        "page_number": 1,
        "text": "전체 추출 텍스트...",
        "confidence": 0.95,
        "width": 595,
        "height": 842,
        "elements": [
          {
            "type": "text",
            "text": "텍스트 블록",
            "confidence": 0.98,
            "bounding_box": {
              "x": 100,
              "y": 200,
              "width": 300,
              "height": 50
            }
          },
          // 추가 텍스트 요소...
        ]
      },
      // 추가 페이지...
    ]
  }
}
```

### 3.4 LLM API

#### 3.4.1 LLM 처리 시작
```
POST /documents/{document_id}/llm
```

**요청 본문:**
```json
{
  "engine": "openai",  // 선택 사항: openai, ollama
  "model": "gpt-4",    // 엔진별 사용 가능한 모델
  "tasks": [
    {
      "type": "summarize",  // 요약
      "options": {
        "max_length": 500,
        "format": "bullet"  // bullet, paragraph
      }
    },
    {
      "type": "extract_info",  // 정보 추출
      "options": {
        "fields": ["date", "amount", "sender", "recipient"]
      }
    },
    {
      "type": "classify",  // 문서 분류
      "options": {
        "categories": ["invoice", "contract", "receipt", "report"]
      }
    }
  ]
}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "job_id": "llm_job_id",
    "document_id": "document_id",
    "status": "PROCESSING",
    "engine": "openai",
    "model": "gpt-4",
    "created_at": "2025-06-01T12:04:00Z",
    "estimated_completion_time": "2025-06-01T12:05:30Z"
  }
}
```

#### 3.4.2 LLM 처리 상태 조회
```
GET /documents/{document_id}/llm/status
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "job_id": "llm_job_id",
    "document_id": "document_id",
    "status": "COMPLETED",  // PENDING, PROCESSING, COMPLETED, ERROR
    "progress": 100,  // 진행률 (0-100)
    "engine": "openai",
    "model": "gpt-4",
    "created_at": "2025-06-01T12:04:00Z",
    "updated_at": "2025-06-01T12:05:30Z",
    "completed_at": "2025-06-01T12:05:30Z",
    "error": null  // 오류 발생 시 오류 정보
  }
}
```

#### 3.4.3 LLM 결과 조회
```
GET /documents/{document_id}/llm/result
```

**쿼리 파라미터:**
- `task`: 특정 작업 결과만 조회 (선택 사항)

**응답:**
```json
{
  "status": "success",
  "data": {
    "document_id": "document_id",
    "engine": "openai",
    "model": "gpt-4",
    "completed_at": "2025-06-01T12:05:30Z",
    "results": [
      {
        "task": "summarize",
        "result": {
          "summary": "이 문서는 2025년 5월 15일 ABC 회사와 XYZ 회사 간의 서비스 계약서입니다. 계약 금액은 1,000,000원이며, 계약 기간은 2025년 6월 1일부터 2025년 12월 31일까지입니다. 주요 서비스 내용은 소프트웨어 개발 및 유지보수이며, 월간 보고서 제출이 요구됩니다."
        }
      },
      {
        "task": "extract_info",
        "result": {
          "fields": {
            "date": "2025-05-15",
            "amount": "1,000,000원",
            "sender": "ABC 회사",
            "recipient": "XYZ 회사"
          },
          "confidence_scores": {
            "date": 0.98,
            "amount": 0.95,
            "sender": 0.97,
            "recipient": 0.96
          }
        }
      },
      {
        "task": "classify",
        "result": {
          "category": "contract",
          "confidence": 0.92,
          "all_categories": {
            "contract": 0.92,
            "invoice": 0.05,
            "receipt": 0.02,
            "report": 0.01
          }
        }
      }
    ]
  }
}
```

### 3.5 데이터 내보내기 API

#### 3.5.1 데이터 내보내기
```
GET /documents/{document_id}/export
```

**쿼리 파라미터:**
- `format`: 내보내기 형식 (excel, csv, pdf, json, 기본값: json)
- `include_ocr`: OCR 결과 포함 여부 (true/false, 기본값: true)
- `include_llm`: LLM 결과 포함 여부 (true/false, 기본값: true)
- `include_metadata`: 메타데이터 포함 여부 (true/false, 기본값: true)

**응답:**
- `format=json`인 경우 JSON 응답
- 다른 형식의 경우 파일 다운로드 (Content-Disposition 헤더 포함)

### 3.6 템플릿 API

#### 3.6.1 템플릿 목록 조회
```
GET /templates
```

**쿼리 파라미터:**
- `page`: 페이지 번호 (기본값: 1)
- `limit`: 페이지당 항목 수 (기본값: 20, 최대: 100)

**응답:**
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": "template_id",
        "name": "영수증 템플릿",
        "description": "일반 영수증 정보 추출용 템플릿",
        "document_type": "receipt",
        "created_at": "2025-05-01T10:00:00Z",
        "updated_at": "2025-05-10T15:30:00Z",
        "field_count": 8
      },
      ...
    ],
    "pagination": {
      "total": 15,
      "page": 1,
      "limit": 20,
      "pages": 1
    }
  }
}
```

#### 3.6.2 템플릿 상세 조회
```
GET /templates/{template_id}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "id": "template_id",
    "name": "영수증 템플릿",
    "description": "일반 영수증 정보 추출용 템플릿",
    "document_type": "receipt",
    "created_at": "2025-05-01T10:00:00Z",
    "updated_at": "2025-05-10T15:30:00Z",
    "fields": [
      {
        "id": "field_id",
        "name": "date",
        "display_name": "날짜",
        "type": "date",
        "required": true,
        "extraction_rule": {
          "type": "regex",
          "pattern": "\\d{4}[-/]\\d{2}[-/]\\d{2}"
        }
      },
      {
        "id": "field_id",
        "name": "amount",
        "display_name": "금액",
        "type": "number",
        "required": true,
        "extraction_rule": {
          "type": "keyword_based",
          "keywords": ["합계", "총액", "Total"],
          "pattern": "[\\d,]+원"
        }
      },
      ...
    ]
  }
}
```

#### 3.6.3 템플릿 생성
```
POST /templates
```

**요청 본문:**
```json
{
  "name": "계약서 템플릿",
  "description": "표준 계약서 정보 추출용 템플릿",
  "document_type": "contract",
  "fields": [
    {
      "name": "contract_date",
      "display_name": "계약일",
      "type": "date",
      "required": true,
      "extraction_rule": {
        "type": "regex",
        "pattern": "\\d{4}[-/]\\d{2}[-/]\\d{2}"
      }
    },
    {
      "name": "contract_amount",
      "display_name": "계약금액",
      "type": "number",
      "required": true,
      "extraction_rule": {
        "type": "keyword_based",
        "keywords": ["계약금액", "금액", "Amount"],
        "pattern": "[\\d,]+원"
      }
    },
    ...
  ]
}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "id": "new_template_id",
    "name": "계약서 템플릿",
    "description": "표준 계약서 정보 추출용 템플릿",
    "document_type": "contract",
    "created_at": "2025-06-01T13:00:00Z",
    "updated_at": "2025-06-01T13:00:00Z",
    "fields": [
      ...
    ]
  }
}
```

#### 3.6.4 템플릿 적용
```
POST /documents/{document_id}/apply_template
```

**요청 본문:**
```json
{
  "template_id": "template_id"
}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "job_id": "template_job_id",
    "document_id": "document_id",
    "template_id": "template_id",
    "status": "PROCESSING",
    "created_at": "2025-06-01T13:30:00Z",
    "estimated_completion_time": "2025-06-01T13:31:00Z"
  }
}
```

#### 3.6.5 템플릿 적용 결과 조회
```
GET /documents/{document_id}/template_result
```

**쿼리 파라미터:**
- `template_id`: 특정 템플릿 결과만 조회 (선택 사항)

**응답:**
```json
{
  "status": "success",
  "data": {
    "document_id": "document_id",
    "template_id": "template_id",
    "template_name": "영수증 템플릿",
    "completed_at": "2025-06-01T13:31:00Z",
    "fields": {
      "date": {
        "value": "2025-05-15",
        "confidence": 0.98,
        "bounding_box": {
          "x": 120,
          "y": 85,
          "width": 80,
          "height": 20
        }
      },
      "amount": {
        "value": "1,000,000원",
        "confidence": 0.95,
        "bounding_box": {
          "x": 350,
          "y": 420,
          "width": 100,
          "height": 25
        }
      },
      ...
    }
  }
}
```

### 3.7 배치 처리 API

#### 3.7.1 배치 업로드
```
POST /batch/upload
```

**요청 헤더:**
```
Content-Type: multipart/form-data
```

**요청 본문:**
- `files[]`: 업로드할 파일들 (여러 파일 가능)
- `name`: 배치 이름 (선택 사항)
- `metadata`: 배치 메타데이터 (선택, JSON 문자열)

**응답:**
```json
{
  "status": "success",
  "data": {
    "batch_id": "batch_id",
    "name": "2025년 6월 영수증",
    "document_count": 5,
    "status": "PENDING",
    "created_at": "2025-06-01T14:00:00Z",
    "updated_at": "2025-06-01T14:00:00Z",
    "documents": [
      {
        "id": "document_id_1",
        "original_filename": "receipt1.pdf",
        "status": "PENDING"
      },
      ...
    ]
  }
}
```

#### 3.7.2 배치 처리 시작
```
POST /batch/{batch_id}/process
```

**요청 본문:**
```json
{
  "ocr": {
    "enabled": true,
    "engine": "tesseract",
    "options": {
      "language": "kor+eng",
      "enhance_image": true
    }
  },
  "llm": {
    "enabled": true,
    "engine": "openai",
    "model": "gpt-4",
    "tasks": [
      {
        "type": "summarize",
        "options": { "max_length": 500 }
      },
      {
        "type": "extract_info",
        "options": { "fields": ["date", "amount"] }
      }
    ]
  },
  "template": {
    "enabled": true,
    "template_id": "template_id"
  },
  "priority": "normal"  // high, normal, low
}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "batch_id": "batch_id",
    "status": "PROCESSING",
    "created_at": "2025-06-01T14:00:00Z",
    "updated_at": "2025-06-01T14:01:00Z",
    "estimated_completion_time": "2025-06-01T14:10:00Z"
  }
}
```

#### 3.7.3 배치 상태 조회
```
GET /batch/{batch_id}/status
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "batch_id": "batch_id",
    "name": "2025년 6월 영수증",
    "status": "PROCESSING",  // PENDING, PROCESSING, COMPLETED, ERROR
    "progress": 60,  // 진행률 (0-100)
    "document_count": 5,
    "completed_count": 3,
    "error_count": 0,
    "created_at": "2025-06-01T14:00:00Z",
    "updated_at": "2025-06-01T14:05:00Z",
    "estimated_completion_time": "2025-06-01T14:10:00Z",
    "documents": [
      {
        "id": "document_id_1",
        "original_filename": "receipt1.pdf",
        "status": "COMPLETED",
        "ocr_status": "COMPLETED",
        "llm_status": "COMPLETED",
        "template_status": "COMPLETED"
      },
      ...
    ]
  }
}
```

#### 3.7.4 배치 결과 내보내기
```
GET /batch/{batch_id}/export
```

**쿼리 파라미터:**
- `format`: 내보내기 형식 (excel, csv, pdf, json, zip, 기본값: json)
- `include_ocr`: OCR 결과 포함 여부 (true/false, 기본값: true)
- `include_llm`: LLM 결과 포함 여부 (true/false, 기본값: true)
- `include_template`: 템플릿 결과 포함 여부 (true/false, 기본값: true)

**응답:**
- `format=json`인 경우 JSON 응답
- 다른 형식의 경우 파일 다운로드 (Content-Disposition 헤더 포함)

## 4. 오류 처리

### 4.1 오류 코드
IntelliDoc API는 다음과 같은 오류 코드를 사용합니다:

| 코드 | HTTP 상태 코드 | 설명 |
|------|--------------|------|
| `AUTH_INVALID_CREDENTIALS` | 401 | 잘못된 인증 정보 |
| `AUTH_EXPIRED_TOKEN` | 401 | 만료된 토큰 |
| `AUTH_INSUFFICIENT_PERMISSIONS` | 403 | 권한 부족 |
| `RESOURCE_NOT_FOUND` | 404 | 요청한 리소스를 찾을 수 없음 |
| `VALIDATION_ERROR` | 400 | 요청 데이터 유효성 검사 실패 |
| `FILE_TOO_LARGE` | 400 | 파일 크기 초과 |
| `UNSUPPORTED_FILE_TYPE` | 400 | 지원되지 않는 파일 형식 |
| `OCR_ENGINE_ERROR` | 500 | OCR 엔진 오류 |
| `LLM_ENGINE_ERROR` | 500 | LLM 엔진 오류 |
| `TEMPLATE_ERROR` | 500 | 템플릿 처리 오류 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 한도 초과 |
| `INTERNAL_SERVER_ERROR` | 500 | 서버 내부 오류 |

### 4.2 오류 응답 예시
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 데이터 유효성 검사 실패",
    "details": {
      "field": "engine",
      "reason": "지원되지 않는 엔진 유형입니다. 'tesseract', 'google_vision', 'aws_textract' 중 하나를 사용하세요."
    }
  }
}
```

## 5. 사용 예제

### 5.1 Python 예제

#### 5.1.1 문서 업로드 및 OCR 처리
```python
import requests
import time
import json

API_BASE_URL = "https://api.intellidoc.com/v1"
API_KEY = "your_api_key_here"

headers = {
    "X-API-Key": API_KEY
}

# 문서 업로드
def upload_document(file_path):
    url = f"{API_BASE_URL}/documents/upload"
    files = {"file": open(file_path, "rb")}
    
    response = requests.post(url, headers=headers, files=files)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"업로드 오류: {response.text}")
        return None

# OCR 처리 시작
def start_ocr(document_id):
    url = f"{API_BASE_URL}/documents/{document_id}/ocr"
    payload = {
        "engine": "tesseract",
        "options": {
            "language": "kor+eng",
            "enhance_image": True
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"OCR 시작 오류: {response.text}")
        return None

# OCR 상태 확인
def check_ocr_status(document_id):
    url = f"{API_BASE_URL}/documents/{document_id}/ocr/status"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"상태 확인 오류: {response.text}")
        return None

# OCR 결과 가져오기
def get_ocr_result(document_id):
    url = f"{API_BASE_URL}/documents/{document_id}/ocr/result"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"결과 조회 오류: {response.text}")
        return None

# 메인 실행 함수
def main():
    # 문서 업로드
    document = upload_document("example.pdf")
    if not document:
        return
    
    document_id = document["id"]
    print(f"문서 업로드 완료: {document_id}")
    
    # OCR 처리 시작
    ocr_job = start_ocr(document_id)
    if not ocr_job:
        return
    
    print(f"OCR 처리 시작: {ocr_job['job_id']}")
    
    # OCR 처리 완료 대기
    while True:
        status = check_ocr_status(document_id)
        if not status:
            return
        
        print(f"OCR 처리 상태: {status['status']}, 진행률: {status['progress']}%")
        
        if status["status"] == "COMPLETED":
            break
        elif status["status"] == "ERROR":
            print(f"OCR 처리 오류: {status['error']}")
            return
        
        time.sleep(5)
    
    # OCR 결과 가져오기
    result = get_ocr_result(document_id)
    if not result:
        return
    
    print(f"OCR 처리 완료: {len(result['pages'])} 페이지")
    
    # 결과 저장
    with open("ocr_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("결과가 ocr_result.json 파일에 저장되었습니다.")

if __name__ == "__main__":
    main()
```

#### 5.1.2 LLM 처리 및 결과 내보내기
```python
import requests
import time
import json

API_BASE_URL = "https://api.intellidoc.com/v1"
API_KEY = "your_api_key_here"

headers = {
    "X-API-Key": API_KEY
}

# LLM 처리 시작
def start_llm(document_id):
    url = f"{API_BASE_URL}/documents/{document_id}/llm"
    payload = {
        "engine": "openai",
        "model": "gpt-4",
        "tasks": [
            {
                "type": "summarize",
                "options": {
                    "max_length": 500,
                    "format": "bullet"
                }
            },
            {
                "type": "extract_info",
                "options": {
                    "fields": ["date", "amount", "sender", "recipient"]
                }
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"LLM 시작 오류: {response.text}")
        return None

# LLM 상태 확인
def check_llm_status(document_id):
    url = f"{API_BASE_URL}/documents/{document_id}/llm/status"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"상태 확인 오류: {response.text}")
        return None

# LLM 결과 가져오기
def get_llm_result(document_id):
    url = f"{API_BASE_URL}/documents/{document_id}/llm/result"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"결과 조회 오류: {response.text}")
        return None

# 결과 내보내기
def export_document(document_id, format="excel"):
    url = f"{API_BASE_URL}/documents/{document_id}/export"
    params = {
        "format": format,
        "include_ocr": "true",
        "include_llm": "true",
        "include_metadata": "true"
    }
    
    response = requests.get(url, headers=headers, params=params, stream=True)
    if response.status_code == 200:
        filename = f"document_{document_id}.{format}"
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return filename
    else:
        print(f"내보내기 오류: {response.text}")
        return None

# 메인 실행 함수
def main(document_id):
    # LLM 처리 시작
    llm_job = start_llm(document_id)
    if not llm_job:
        return
    
    print(f"LLM 처리 시작: {llm_job['job_id']}")
    
    # LLM 처리 완료 대기
    while True:
        status = check_llm_status(document_id)
        if not status:
            return
        
        print(f"LLM 처리 상태: {status['status']}, 진행률: {status['progress']}%")
        
        if status["status"] == "COMPLETED":
            break
        elif status["status"] == "ERROR":
            print(f"LLM 처리 오류: {status['error']}")
            return
        
        time.sleep(5)
    
    # LLM 결과 가져오기
    result = get_llm_result(document_id)
    if not result:
        return
    
    print(f"LLM 처리 완료: {len(result['results'])} 작업")
    
    # 결과 저장
    with open("llm_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("결과가 llm_result.json 파일에 저장되었습니다.")
    
    # 결과 내보내기
    formats = ["excel", "csv", "pdf"]
    for format in formats:
        filename = export_document(document_id, format)
        if filename:
            print(f"{format.upper()} 형식으로 내보내기 완료: {filename}")

if __name__ == "__main__":
    document_id = "your_document_id_here"
    main(document_id)
```

### 5.2 Node.js 예제

#### 5.2.1 문서 업로드 및 OCR 처리
```javascript
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

const API_BASE_URL = 'https://api.intellidoc.com/v1';
const API_KEY = 'your_api_key_here';

const headers = {
  'X-API-Key': API_KEY
};

// 문서 업로드
async function uploadDocument(filePath) {
  try {
    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    
    const response = await axios.post(`${API_BASE_URL}/documents/upload`, form, {
      headers: {
        ...headers,
        ...form.getHeaders()
      }
    });
    
    return response.data.data;
  } catch (error) {
    console.error('업로드 오류:', error.response?.data || error.message);
    return null;
  }
}

// OCR 처리 시작
async function startOcr(documentId) {
  try {
    const payload = {
      engine: 'tesseract',
      options: {
        language: 'kor+eng',
        enhance_image: true
      }
    };
    
    const response = await axios.post(`${API_BASE_URL}/documents/${documentId}/ocr`, payload, { headers });
    return response.data.data;
  } catch (error) {
    console.error('OCR 시작 오류:', error.response?.data || error.message);
    return null;
  }
}

// OCR 상태 확인
async function checkOcrStatus(documentId) {
  try {
    const response = await axios.get(`${API_BASE_URL}/documents/${documentId}/ocr/status`, { headers });
    return response.data.data;
  } catch (error) {
    console.error('상태 확인 오류:', error.response?.data || error.message);
    return null;
  }
}

// OCR 결과 가져오기
async function getOcrResult(documentId) {
  try {
    const response = await axios.get(`${API_BASE_URL}/documents/${documentId}/ocr/result`, { headers });
    return response.data.data;
  } catch (error) {
    console.error('결과 조회 오류:', error.response?.data || error.message);
    return null;
  }
}

// 지연 함수
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// 메인 실행 함수
async function main() {
  // 문서 업로드
  const document = await uploadDocument('example.pdf');
  if (!document) return;
  
  const documentId = document.id;
  console.log(`문서 업로드 완료: ${documentId}`);
  
  // OCR 처리 시작
  const ocrJob = await startOcr(documentId);
  if (!ocrJob) return;
  
  console.log(`OCR 처리 시작: ${ocrJob.job_id}`);
  
  // OCR 처리 완료 대기
  while (true) {
    const status = await checkOcrStatus(documentId);
    if (!status) return;
    
    console.log(`OCR 처리 상태: ${status.status}, 진행률: ${status.progress}%`);
    
    if (status.status === 'COMPLETED') {
      break;
    } else if (status.status === 'ERROR') {
      console.error(`OCR 처리 오류: ${status.error}`);
      return;
    }
    
    await delay(5000);
  }
  
  // OCR 결과 가져오기
  const result = await getOcrResult(documentId);
  if (!result) return;
  
  console.log(`OCR 처리 완료: ${result.pages.length} 페이지`);
  
  // 결과 저장
  fs.writeFileSync('ocr_result.json', JSON.stringify(result, null, 2), 'utf8');
  console.log('결과가 ocr_result.json 파일에 저장되었습니다.');
}

main().catch(console.error);
```

## 6. 웹훅

IntelliDoc API는 비동기 작업의 상태 변경을 실시간으로 알리기 위한 웹훅 기능을 제공합니다.

### 6.1 웹훅 등록
```
POST /webhooks
```

**요청 본문:**
```json
{
  "url": "https://your-server.com/webhook-endpoint",
  "events": ["document.created", "ocr.completed", "llm.completed", "template.completed"],
  "secret": "your_webhook_secret"
}
```

**응답:**
```json
{
  "status": "success",
  "data": {
    "id": "webhook_id",
    "url": "https://your-server.com/webhook-endpoint",
    "events": ["document.created", "ocr.completed", "llm.completed", "template.completed"],
    "created_at": "2025-06-01T15:00:00Z",
    "updated_at": "2025-06-01T15:00:00Z"
  }
}
```

### 6.2 웹훅 이벤트 형식
웹훅 이벤트는 다음과 같은 형식으로 전송됩니다:

```json
{
  "event": "ocr.completed",
  "timestamp": "2025-06-01T12:03:45Z",
  "data": {
    "document_id": "document_id",
    "job_id": "ocr_job_id",
    "status": "COMPLETED",
    "engine": "tesseract",
    "completed_at": "2025-06-01T12:03:45Z"
  }
}
```

### 6.3 웹훅 서명 검증
웹훅 요청의 무결성을 검증하기 위해 `X-IntelliDoc-Signature` 헤더가 포함됩니다. 이 서명은 요청 본문과 등록 시 제공한 시크릿을 사용하여 생성됩니다.

**서명 검증 예제 (Node.js):**
```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
  const hmac = crypto.createHmac('sha256', secret);
  const digest = hmac.update(JSON.stringify(payload)).digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(digest),
    Buffer.from(signature)
  );
}

// Express 미들웨어 예제
app.post('/webhook-endpoint', (req, res) => {
  const signature = req.headers['x-intellidoc-signature'];
  const isValid = verifyWebhookSignature(req.body, signature, 'your_webhook_secret');
  
  if (!isValid) {
    return res.status(401).send('Invalid signature');
  }
  
  // 웹훅 처리 로직
  console.log('웹훅 이벤트 수신:', req.body.event);
  console.log('데이터:', req.body.data);
  
  res.status(200).send('OK');
});
```

## 7. 제한 사항

### 7.1 요청 한도
- API 키당 분당 최대 요청 수: 60 (기본 플랜)
- 동시 처리 가능한 문서 수: 10 (기본 플랜)
- 최대 파일 크기: 100MB
- 배치 업로드 시 최대 파일 수: 50

### 7.2 지원 형식
- 이미지: JPG, PNG, TIFF, BMP, GIF
- 문서: PDF, DOCX, XLSX, PPTX
- 압축 파일: ZIP (배치 업로드 시)

### 7.3 OCR 엔진별 제한 사항
- Tesseract: 최대 해상도 4000x4000, 최대 50페이지
- Google Vision API: 최대 파일 크기 20MB, 최대 5페이지
- AWS Textract: 최대 파일 크기 10MB, PDF의 경우 최대 3000페이지

### 7.4 LLM 엔진별 제한 사항
- OpenAI: 최대 입력 토큰 수 8,000 (GPT-3.5) 또는 32,000 (GPT-4)
- Ollama: 모델에 따라 다름, 일반적으로 2,000~8,000 토큰

## 8. 확장성 고려사항

### 8.1 MongoDB 연동
IntelliDoc API는 MongoDB와의 연동을 위한 확장 포인트를 제공합니다:

#### 8.1.1 데이터 내보내기 MongoDB 형식
```
GET /documents/{document_id}/export?format=mongodb
```

이 엔드포인트는 MongoDB에 직접 삽입할 수 있는 BSON 호환 JSON 형식으로 데이터를 내보냅니다.

#### 8.1.2 MongoDB 웹훅 통합
웹훅을 사용하여 처리 완료 이벤트를 수신하고, MongoDB에 자동으로 데이터를 저장할 수 있습니다:

```javascript
const { MongoClient } = require('mongodb');
const express = require('express');
const app = express();
app.use(express.json());

const mongoClient = new MongoClient('mongodb://localhost:27017');
let db;

async function connectToMongo() {
  await mongoClient.connect();
  db = mongoClient.db('your_evaluation_system');
  console.log('MongoDB에 연결되었습니다.');
}

connectToMongo().catch(console.error);

app.post('/webhook-endpoint', async (req, res) => {
  try {
    const event = req.body.event;
    const data = req.body.data;
    
    if (event === 'ocr.completed' || event === 'llm.completed') {
      const documentId = data.document_id;
      
      // 문서 데이터 가져오기
      const documentResponse = await axios.get(
        `${API_BASE_URL}/documents/${documentId}`,
        { headers }
      );
      
      // OCR 결과 가져오기
      const ocrResponse = await axios.get(
        `${API_BASE_URL}/documents/${documentId}/ocr/result`,
        { headers }
      );
      
      // LLM 결과 가져오기 (있는 경우)
      let llmResult = null;
      if (event === 'llm.completed') {
        const llmResponse = await axios.get(
          `${API_BASE_URL}/documents/${documentId}/llm/result`,
          { headers }
        );
        llmResult = llmResponse.data.data;
      }
      
      // MongoDB에 저장
      const document = documentResponse.data.data;
      const ocrResult = ocrResponse.data.data;
      
      await db.collection('documents').updateOne(
        { external_id: documentId },
        {
          $set: {
            external_id: documentId,
            filename: document.original_filename,
            status: document.status,
            created_at: new Date(document.created_at),
            updated_at: new Date(document.updated_at),
            ocr_result: ocrResult,
            llm_result: llmResult,
            metadata: document.metadata || {}
          }
        },
        { upsert: true }
      );
      
      console.log(`문서 ${documentId} 데이터가 MongoDB에 저장되었습니다.`);
    }
    
    res.status(200).send('OK');
  } catch (error) {
    console.error('웹훅 처리 오류:', error);
    res.status(500).send('Internal Server Error');
  }
});

app.listen(3000, () => {
  console.log('웹훅 서버가 포트 3000에서 실행 중입니다.');
});
```

### 8.2 확장 API 엔드포인트
IntelliDoc API는 다음과 같은 확장 API 엔드포인트를 제공합니다:

#### 8.2.1 커스텀 분석 파이프라인
```
POST /documents/{document_id}/custom_pipeline
```

**요청 본문:**
```json
{
  "steps": [
    {
      "type": "ocr",
      "engine": "tesseract",
      "options": { ... }
    },
    {
      "type": "llm",
      "engine": "openai",
      "tasks": [ ... ]
    },
    {
      "type": "template",
      "template_id": "template_id"
    },
    {
      "type": "custom_script",
      "script_id": "script_id",
      "parameters": { ... }
    }
  ],
  "output_format": "json",
  "callback_url": "https://your-server.com/callback"
}
```

#### 8.2.2 외부 시스템 연동
```
POST /integrations/connect
```

**요청 본문:**
```json
{
  "type": "mongodb",
  "connection_string": "mongodb://username:password@host:port/database",
  "collection": "documents",
  "mapping": {
    "document_id": "external_id",
    "original_filename": "filename",
    "ocr_result.pages": "pages",
    "llm_result.results[0].result.summary": "summary"
  },
  "events": ["ocr.completed", "llm.completed"]
}
```

### 8.3 확장성 설계 원칙
IntelliDoc API는 다음과 같은 확장성 설계 원칙을 따릅니다:

1. **모듈화된 아키텍처**: 각 기능(OCR, LLM, 템플릿 등)이 독립적으로 확장 가능
2. **버전 관리**: API 버전 관리를 통한 하위 호환성 유지
3. **표준 인터페이스**: RESTful API 설계 원칙 준수
4. **비동기 처리**: 장시간 실행 작업의 비동기 처리 및 상태 추적
5. **이벤트 기반 통합**: 웹훅을 통한 이벤트 기반 통합
6. **확장 포인트**: 커스텀 스크립트, 외부 시스템 연동 등 확장 포인트 제공
7. **데이터 포맷 유연성**: 다양한 데이터 형식(JSON, CSV, Excel, PDF 등) 지원

---

이 API 문서에 대한 문의사항이나 추가 지원이 필요한 경우, 관리자에게 문의하거나 api-support@intellidoc.com으로 이메일을 보내주세요.

© 2025 IntelliDoc. All rights reserved.

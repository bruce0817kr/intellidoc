# IntelliDoc API 사용 가이드

이 문서는 IntelliDoc API의 사용 방법을 설명합니다.

## 목차
- [개요](#개요)
- [인증](#인증)
- [API 엔드포인트](#api-엔드포인트)
  - [인증 API](#인증-api)
  - [문서 관리 API](#문서-관리-api)
- [에러 처리](#에러-처리)
- [보안 고려사항](#보안-고려사항)
- [예제 코드](#예제-코드)

---

## 개요

IntelliDoc은 AI 기반 문서 처리 시스템으로 다음과 같은 기능을 제공합니다:

- **문서 업로드 및 관리**: PDF, DOCX, 이미지 등 다양한 형식 지원
- **OCR 처리**: Tesseract, EasyOCR, PaddleOCR 등 다양한 엔진 지원
- **LLM 기반 분석**: OpenAI GPT, Claude, Gemini를 활용한 데이터 추출
- **데이터 내보내기**: JSON, CSV, Excel, PDF 형식으로 내보내기

### Base URL
```
http://localhost:8000/api/v1
```

### 대화형 API 문서
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 인증

IntelliDoc API는 **JWT 토큰 기반 인증**을 사용하며, 토큰은 **HttpOnly 쿠키**에 저장됩니다.

### 인증 흐름

1. **로그인**: `/api/v1/auth/login`으로 사용자 인증
2. **자동 토큰 저장**: 서버가 HttpOnly 쿠키에 토큰 저장
3. **자동 인증**: 브라우저가 모든 요청에 쿠키 자동 포함
4. **토큰 갱신**: 만료 시 `/api/v1/auth/refresh`로 자동 갱신

### 보안 특징

- **HttpOnly 쿠키**: XSS 공격으로부터 보호
- **SameSite=Lax**: CSRF 공격 방지
- **Secure 플래그**: HTTPS에서만 전송 (프로덕션)
- **토큰 만료**: Access Token 15분, Refresh Token 7일

---

## API 엔드포인트

### 인증 API

#### 1. 로그인 (POST `/auth/login`)

사용자 인증을 수행하고 JWT 토큰을 발급합니다.

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=SecurePassword123!" \
  -c cookies.txt
```

**응답 (200 OK):**
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "관리자",
    "department": "IT",
    "roles": ["admin"],
    "permissions": ["document:read", "document:write", "document:delete"],
    "created_at": "2025-01-01T00:00:00Z"
  },
  "token_type": "bearer",
  "message": "로그인 성공"
}
```

**에러 응답 (401 Unauthorized):**
```json
{
  "error": "인증 오류",
  "detail": "사용자 이름 또는 비밀번호가 올바르지 않습니다.",
  "code": "INVALID_CREDENTIALS"
}
```

#### 2. 현재 사용자 정보 조회 (GET `/auth/me`)

현재 인증된 사용자의 정보를 조회합니다.

**요청:**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -b cookies.txt
```

**응답 (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "관리자",
  "department": "IT",
  "roles": ["admin", "user"],
  "permissions": ["document:read", "document:write", "document:delete"],
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### 3. 토큰 갱신 (POST `/auth/refresh`)

만료된 Access Token을 갱신합니다.

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -b cookies.txt \
  -c cookies.txt
```

**응답 (200 OK):**
```json
{
  "token_type": "bearer",
  "message": "토큰 갱신 성공"
}
```

#### 4. 로그아웃 (POST `/auth/logout`)

현재 사용자를 로그아웃하고 토큰을 무효화합니다.

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -b cookies.txt
```

**응답:** 204 No Content

---

### 문서 관리 API

#### 1. 문서 업로드 (POST `/documents/`)

새로운 문서를 업로드합니다.

**요청:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/" \
  -b cookies.txt \
  -F "file=@/path/to/document.pdf" \
  -F "auto_process=true"
```

**지원 파일 형식:**
- **문서**: PDF, DOCX, DOC, TXT, RTF
- **이미지**: PNG, JPEG, JPG, TIFF, BMP, GIF, WEBP
- **스프레드시트**: XLSX, XLS, CSV

**응답 (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "sample_document.pdf",
  "file_type": "pdf",
  "file_size": 2048000,
  "status": "UPLOADED",
  "upload_date": "2025-01-01T12:00:00Z",
  "auto_process": true
}
```

**에러 응답 (400 Bad Request):**
```json
{
  "error": "검증 오류",
  "detail": "지원하지 않는 파일 형식입니다.",
  "code": "UNSUPPORTED_FILE_TYPE"
}
```

#### 2. 문서 목록 조회 (GET `/documents/`)

현재 사용자가 업로드한 문서 목록을 조회합니다.

**요청:**
```bash
# 기본 조회 (최신 100개)
curl -X GET "http://localhost:8000/api/v1/documents/" \
  -b cookies.txt

# 페이지네이션
curl -X GET "http://localhost:8000/api/v1/documents/?skip=0&limit=20" \
  -b cookies.txt

# 상태 필터링
curl -X GET "http://localhost:8000/api/v1/documents/?status=PROCESSED" \
  -b cookies.txt
```

**쿼리 파라미터:**
- `skip` (선택): 건너뛸 개수 (기본값: 0)
- `limit` (선택): 최대 개수 (기본값: 100, 최대: 1000)
- `status` (선택): 문서 상태 (`UPLOADED`, `PROCESSING`, `PROCESSED`, `FAILED`)

**응답 (200 OK):**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "sample_document.pdf",
    "file_type": "pdf",
    "file_size": 2048000,
    "status": "PROCESSED",
    "upload_date": "2025-01-01T12:00:00Z",
    "processed_date": "2025-01-01T12:05:00Z"
  },
  {
    "id": "456e7890-e89b-12d3-a456-426614174111",
    "filename": "invoice.png",
    "file_type": "png",
    "file_size": 512000,
    "status": "PROCESSING",
    "upload_date": "2025-01-01T12:10:00Z",
    "processed_date": null
  }
]
```

#### 3. 문서 상세 조회 (GET `/documents/{document_id}`)

특정 문서의 상세 정보를 조회합니다.

**요청:**
```bash
curl -X GET "http://localhost:8000/api/v1/documents/123e4567-e89b-12d3-a456-426614174000" \
  -b cookies.txt
```

**응답 (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "sample_document.pdf",
  "file_type": "pdf",
  "file_size": 2048000,
  "mime_type": "application/pdf",
  "status": "PROCESSED",
  "upload_date": "2025-01-01T12:00:00Z",
  "processed_date": "2025-01-01T12:05:00Z",
  "page_count": 10,
  "metadata": {
    "author": "John Doe",
    "title": "Sample Document",
    "created": "2025-01-01"
  },
  "jobs": [
    {
      "id": "456e7890-e89b-12d3-a456-426614174111",
      "job_type": "OCR",
      "status": "COMPLETED",
      "created_at": "2025-01-01T12:00:00Z",
      "started_at": "2025-01-01T12:00:30Z",
      "completed_at": "2025-01-01T12:02:00Z",
      "error_message": null
    },
    {
      "id": "789e0123-e89b-12d3-a456-426614174222",
      "job_type": "LLM_ANALYSIS",
      "status": "COMPLETED",
      "created_at": "2025-01-01T12:02:00Z",
      "started_at": "2025-01-01T12:02:10Z",
      "completed_at": "2025-01-01T12:05:00Z",
      "error_message": null
    }
  ]
}
```

**에러 응답 (404 Not Found):**
```json
{
  "error": "리소스 없음",
  "detail": "문서를 찾을 수 없습니다.",
  "code": "RESOURCE_NOT_FOUND"
}
```

#### 4. 문서 다운로드 (GET `/documents/{document_id}/download`)

문서 파일을 다운로드합니다.

**요청:**
```bash
curl -X GET "http://localhost:8000/api/v1/documents/123e4567-e89b-12d3-a456-426614174000/download" \
  -b cookies.txt \
  -o downloaded_document.pdf
```

**응답:** 파일 스트림 (200 OK)

#### 5. 문서 삭제 (DELETE `/documents/{document_id}`)

문서를 삭제합니다 (복구 불가).

**요청:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/123e4567-e89b-12d3-a456-426614174000" \
  -b cookies.txt
```

**응답:** 204 No Content

**에러 응답 (403 Forbidden):**
```json
{
  "error": "권한 없음",
  "detail": "이 문서에 대한 접근 권한이 없습니다.",
  "code": "FORBIDDEN"
}
```

---

## 에러 처리

### HTTP 상태 코드

| 코드 | 의미 | 설명 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 201 | Created | 리소스 생성 성공 |
| 204 | No Content | 요청 성공 (응답 본문 없음) |
| 400 | Bad Request | 잘못된 요청 (검증 오류 등) |
| 401 | Unauthorized | 인증 실패 또는 토큰 만료 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 500 | Internal Server Error | 서버 내부 오류 |

### 에러 응답 형식

```json
{
  "error": "에러 타입",
  "detail": "에러 상세 메시지",
  "code": "ERROR_CODE"
}
```

### 일반적인 에러 코드

- `INVALID_CREDENTIALS`: 잘못된 사용자 이름 또는 비밀번호
- `TOKEN_EXPIRED`: 토큰 만료
- `INVALID_TOKEN`: 유효하지 않은 토큰
- `UNSUPPORTED_FILE_TYPE`: 지원하지 않는 파일 형식
- `FILE_SIZE_EXCEEDED`: 파일 크기 초과 (최대 50MB)
- `MIME_TYPE_MISMATCH`: 파일 시그니처와 확장자 불일치
- `RESOURCE_NOT_FOUND`: 리소스를 찾을 수 없음
- `FORBIDDEN`: 접근 권한 없음
- `WEAK_PASSWORD`: 비밀번호 강도 부족

---

## 보안 고려사항

### 1. HttpOnly 쿠키 사용

- **JavaScript 접근 불가**: XSS 공격으로부터 토큰 보호
- **자동 전송**: 브라우저가 자동으로 쿠키 포함
- **HTTPS 필수**: 프로덕션 환경에서는 Secure 플래그 활성화

### 2. CSRF 보호

- **SameSite=Lax**: 크로스 사이트 요청 제한
- **안전한 메서드**: GET은 허용, POST/PUT/DELETE는 Same-Site만

### 3. 파일 검증

- **MIME 타입 검증**: 파일 시그니처 기반 검증
- **확장자 검증**: 선언된 확장자와 실제 형식 일치 확인
- **크기 제한**: 최대 50MB

### 4. 비밀번호 정책

- **최소 8자**
- **대문자 1개 이상**
- **소문자 1개 이상**
- **숫자 1개 이상**
- **특수문자 1개 이상**

### 5. 환경 변수 검증

- **프로덕션 환경**: 기본값 사용 금지
- **SECRET_KEY**: 최소 32자
- **ENCRYPTION_SALT**: 최소 32자
- **DEBUG**: 프로덕션에서 비활성화

---

## 예제 코드

### Python (requests)

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# 세션 생성 (쿠키 자동 관리)
session = requests.Session()

# 1. 로그인
response = session.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": "admin",
        "password": "SecurePassword123!"
    }
)
print("로그인:", response.json())

# 2. 현재 사용자 정보 조회
response = session.get(f"{BASE_URL}/auth/me")
print("사용자 정보:", response.json())

# 3. 문서 업로드
with open("document.pdf", "rb") as f:
    response = session.post(
        f"{BASE_URL}/documents/",
        files={"file": f},
        data={"auto_process": "true"}
    )
print("업로드:", response.json())
document_id = response.json()["id"]

# 4. 문서 목록 조회
response = session.get(f"{BASE_URL}/documents/")
print("문서 목록:", response.json())

# 5. 문서 상세 조회
response = session.get(f"{BASE_URL}/documents/{document_id}")
print("문서 상세:", response.json())

# 6. 문서 다운로드
response = session.get(f"{BASE_URL}/documents/{document_id}/download")
with open("downloaded.pdf", "wb") as f:
    f.write(response.content)

# 7. 로그아웃
response = session.post(f"{BASE_URL}/auth/logout")
print("로그아웃 완료")
```

### JavaScript (Axios)

```javascript
const axios = require('axios');

// Base URL 및 쿠키 설정
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  withCredentials: true  // 쿠키 자동 포함
});

async function main() {
  try {
    // 1. 로그인
    const loginResponse = await api.post('/auth/login',
      new URLSearchParams({
        username: 'admin',
        password: 'SecurePassword123!'
      })
    );
    console.log('로그인:', loginResponse.data);

    // 2. 현재 사용자 정보 조회
    const userResponse = await api.get('/auth/me');
    console.log('사용자 정보:', userResponse.data);

    // 3. 문서 업로드
    const FormData = require('form-data');
    const fs = require('fs');
    const formData = new FormData();
    formData.append('file', fs.createReadStream('document.pdf'));
    formData.append('auto_process', 'true');

    const uploadResponse = await api.post('/documents/', formData, {
      headers: formData.getHeaders()
    });
    console.log('업로드:', uploadResponse.data);
    const documentId = uploadResponse.data.id;

    // 4. 문서 목록 조회
    const listResponse = await api.get('/documents/');
    console.log('문서 목록:', listResponse.data);

    // 5. 문서 상세 조회
    const detailResponse = await api.get(`/documents/${documentId}`);
    console.log('문서 상세:', detailResponse.data);

    // 6. 문서 다운로드
    const downloadResponse = await api.get(`/documents/${documentId}/download`, {
      responseType: 'arraybuffer'
    });
    fs.writeFileSync('downloaded.pdf', downloadResponse.data);

    // 7. 로그아웃
    await api.post('/auth/logout');
    console.log('로그아웃 완료');

  } catch (error) {
    console.error('에러:', error.response?.data || error.message);
  }
}

main();
```

### cURL 스크립트

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"
COOKIES="cookies.txt"

# 1. 로그인
echo "=== 로그인 ==="
curl -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=SecurePassword123!" \
  -c ${COOKIES} | jq .

# 2. 현재 사용자 정보 조회
echo -e "\n=== 사용자 정보 조회 ==="
curl -X GET "${BASE_URL}/auth/me" \
  -b ${COOKIES} | jq .

# 3. 문서 업로드
echo -e "\n=== 문서 업로드 ==="
DOCUMENT_ID=$(curl -X POST "${BASE_URL}/documents/" \
  -b ${COOKIES} \
  -F "file=@document.pdf" \
  -F "auto_process=true" | jq -r '.id')
echo "Document ID: ${DOCUMENT_ID}"

# 4. 문서 목록 조회
echo -e "\n=== 문서 목록 조회 ==="
curl -X GET "${BASE_URL}/documents/" \
  -b ${COOKIES} | jq .

# 5. 문서 상세 조회
echo -e "\n=== 문서 상세 조회 ==="
curl -X GET "${BASE_URL}/documents/${DOCUMENT_ID}" \
  -b ${COOKIES} | jq .

# 6. 문서 다운로드
echo -e "\n=== 문서 다운로드 ==="
curl -X GET "${BASE_URL}/documents/${DOCUMENT_ID}/download" \
  -b ${COOKIES} \
  -o "downloaded.pdf"

# 7. 로그아웃
echo -e "\n=== 로그아웃 ==="
curl -X POST "${BASE_URL}/auth/logout" \
  -b ${COOKIES}

echo -e "\n완료!"
```

---

## 추가 리소스

- **OpenAPI 스펙 다운로드**: http://localhost:8000/openapi.json
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **GitHub 저장소**: https://github.com/yourusername/intellidoc

---

## 라이선스

MIT License - 자세한 내용은 LICENSE 파일 참조

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-11-11

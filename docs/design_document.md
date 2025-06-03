# IntelliDoc 프로젝트 설계서

## 프로젝트 개요
- **프로젝트명:** IntelliDoc (사내 지능형 문서 처리 시스템)
- **목적:** 한국어 문서 OCR + AI 분석을 통한 데이터 추출 및 엑셀 출력
- **특징:** 플러그인 방식 API 확장, 지속적 학습, 완전한 감사 추적

## 핵심 요구사항
1. 다중 파일 업로드 및 배치 처리
2. OCR/LLM API 동적 추가 기능
3. 한국어 특화 처리
4. 모든 작업 로그 및 감사 추적
5. 지속적 학습 및 성능 개선
6. 엑셀/CSV 내보내기
7. 사내 전용 보안

---

# 모듈별 상세 설계

## 1. 공통 모듈 (shared)

### 1.1 설정 관리 모듈
```python
# shared/config.py
"""
환경변수 및 설정 관리
- DATABASE_URL, REDIS_URL 등 환경변수 로드
- API 키 암호화 저장/로드 기능
- 동적 설정 업데이트 지원
"""

# shared/constants.py
"""
시스템 상수 정의
- 파일 형식, 상태 코드, 에러 메시지
- API 엔드포인트 상수
- 권한 레벨 정의
"""

# shared/exceptions.py
"""
커스텀 예외 클래스
- DocumentProcessingError
- OCREngineError
- LLMAPIError
- AuthenticationError
"""
```

### 1.2 데이터베이스 모델
```python
# shared/models.py
"""
SQLAlchemy 모델 정의

필수 테이블:
1. users - 사용자 정보
2. documents - 문서 메타데이터
3. extracted_data - 추출된 데이터
4. processing_jobs - 작업 큐
5. audit_logs - 감사 로그
6. feedback - 학습 피드백
7. api_configurations - 동적 API 설정
8. system_settings - 시스템 설정
"""

# shared/database.py
"""
데이터베이스 연결 관리
- 연결 풀 설정
- 트랜잭션 관리
- 마이그레이션 스크립트
"""
```

### 1.3 유틸리티 모듈
```python
# shared/utils.py
"""
공통 유틸리티 함수
- 파일 검증 (크기, 형식)
- UUID 생성
- 날짜/시간 처리
- 암호화/복호화
"""

# shared/validators.py
"""
데이터 검증 함수
- 파일 형식 검증
- API 키 형식 검증
- 사용자 입력 검증
"""

# shared/logger.py
"""
구조화된 로깅 시스템
- JSON 형태 로그 출력
- 사용자별 로그 컨텍스트
- 에러 추적 및 알림
"""
```

---

## 2. 인증 모듈 (auth)

### 2.1 인증 서비스
```python
# auth/service.py
"""
JWT 토큰 기반 인증 시스템

주요 기능:
1. 로그인/로그아웃 처리
2. 토큰 생성 및 검증
3. 리프레시 토큰 관리
4. 비밀번호 해싱 (bcrypt)

구현할 함수:
- authenticate_user(username, password)
- create_access_token(user_data)
- verify_token(token)
- refresh_access_token(refresh_token)
"""

# auth/models.py
"""
사용자 및 권한 모델
- User 모델 (id, username, email, department, role)
- UserSession 모델 (세션 추적)
- Role 모델 (역할 기반 권한)
"""

# auth/dependencies.py
"""
FastAPI 의존성 주입
- get_current_user()
- require_admin()
- require_auditor()
"""
```

### 2.2 권한 관리
```python
# auth/permissions.py
"""
역할 기반 접근 제어 (RBAC)

권한 레벨:
- user: 문서 업로드, 처리, 조회
- admin: 사용자 관리, 시스템 설정
- auditor: 로그 조회, 보고서 생성

구현할 데코레이터:
- @require_permission("document.upload")
- @require_permission("admin.user_management")
"""
```

---

## 3. 파일 관리 모듈 (file_manager)

### 3.1 파일 업로드 처리
```python
# file_manager/upload.py
"""
다중 파일 업로드 처리

주요 기능:
1. 파일 형식 검증 (PDF, 이미지, Word, HWP)
2. 파일 크기 제한 (최대 100MB)
3. 안전한 파일명 생성
4. 스토리지 저장 (로컬/클라우드)
5. 메타데이터 추출

구현할 함수:
- validate_file(file)
- save_file(file, user_id)
- generate_safe_filename(original_name)
- extract_file_metadata(file_path)
"""

# file_manager/storage.py
"""
파일 스토리지 추상화
- 로컬 파일 시스템
- AWS S3 (선택사항)
- 파일 접근 권한 관리
"""
```

### 3.2 파일 처리 큐
```python
# file_manager/queue.py
"""
Celery 기반 비동기 처리

작업 유형:
1. OCR 처리 작업
2. AI 분석 작업
3. 데이터 내보내기 작업

구현할 태스크:
- process_document_ocr.delay(document_id, ocr_engine)
- process_document_ai.delay(document_id, llm_model)
- export_to_excel.delay(document_ids, user_id)
"""
```

---

## 4. OCR 엔진 모듈 (ocr_engines)

### 4.1 OCR 엔진 추상화
```python
# ocr_engines/base.py
"""
OCR 엔진 베이스 클래스

class BaseOCREngine:
    def __init__(self, config):
        pass
    
    def extract_text(self, file_path):
        # 텍스트 추출 로직
        pass
    
    def extract_structured_data(self, file_path):
        # 테이블, 양식 구조 추출
        pass
    
    def get_confidence_score(self):
        # 신뢰도 점수 반환
        pass
"""

# ocr_engines/registry.py
"""
동적 OCR 엔진 등록 시스템

class OCREngineRegistry:
    def register_engine(self, name, engine_class, config):
        # 새 OCR 엔진 등록
        pass
    
    def get_engine(self, name):
        # 등록된 엔진 반환
        pass
    
    def list_engines(self):
        # 사용 가능한 엔진 목록
        pass
"""
```

### 4.2 개별 OCR 엔진 구현
```python
# ocr_engines/tesseract.py
"""
Tesseract OCR 엔진 (무료)
- 한글 언어팩 설정
- 이미지 전처리 (노이즈 제거, 대비 조정)
- 테이블 구조 인식
"""

# ocr_engines/google_vision.py
"""
Google Cloud Vision API
- API 키 관리
- 배치 처리 지원
- 한글 인식 최적화
"""

# ocr_engines/naver_clova.py
"""
Naver Clova OCR API
- 한국어 특화 인식
- 신분증, 명함 등 특수 문서 처리
"""

# ocr_engines/mistral_ocr.py
"""
Mistral OCR API
- API 엔드포인트 설정
- 응답 파싱 로직
- 에러 처리
"""
```

### 4.3 OCR 결과 후처리
```python
# ocr_engines/postprocessor.py
"""
OCR 결과 후처리

주요 기능:
1. 한글 오타 수정
2. 테이블 구조 정리
3. 신뢰도 기반 필터링
4. 텍스트 정규화

구현할 함수:
- correct_korean_typos(text)
- extract_table_structure(text)
- filter_low_confidence_text(results, threshold)
"""
```

---

## 5. LLM 처리 모듈 (llm_processors)

### 5.1 LLM 엔진 추상화
```python
# llm_processors/base.py
"""
LLM 엔진 베이스 클래스

class BaseLLMProcessor:
    def __init__(self, config):
        pass
    
    def analyze_document(self, text, prompt):
        # 문서 분석
        pass
    
    def extract_structured_data(self, text, schema):
        # 구조화된 데이터 추출
        pass
    
    def summarize_document(self, text):
        # 문서 요약
        pass
"""

# llm_processors/registry.py
"""
동적 LLM 엔진 등록 시스템
- 사용자가 새 API 추가 가능
- 설정 검증 및 테스트
"""
```

### 5.2 개별 LLM 엔진 구현
```python
# llm_processors/ollama.py
"""
Ollama 로컬 LLM
- 모델 다운로드 관리
- 한국어 모델 우선 사용
- 리소스 사용량 모니터링
"""

# llm_processors/openai.py
"""
OpenAI API
- GPT-3.5/GPT-4 지원
- 비용 추적
- 속도 제한 관리
"""

# llm_processors/claude.py
"""
Anthropic Claude API
- 긴 문서 처리 특화
- 안전한 프롬프트 처리
"""
```

### 5.3 프롬프트 관리
```python
# llm_processors/prompts.py
"""
프롬프트 템플릿 관리

기본 프롬프트:
1. 문서 분류 프롬프트
2. 데이터 추출 프롬프트 (테이블, 양식)
3. 요약 프롬프트
4. 한국어 특화 프롬프트

동적 프롬프트:
- 사용자 정의 추출 규칙
- 학습 기반 프롬프트 최적화
"""

# llm_processors/prompt_optimizer.py
"""
프롬프트 최적화 시스템
- A/B 테스트
- 성능 메트릭 기반 개선
- 피드백 기반 학습
"""
```

---

## 6. 데이터 처리 모듈 (data_processor)

### 6.1 데이터 추출 및 구조화
```python
# data_processor/extractor.py
"""
추출된 데이터 구조화

주요 기능:
1. OCR + LLM 결과 통합
2. 신뢰도 기반 데이터 검증
3. 중복 제거 및 정규화
4. 한국어 데이터 특화 처리

구현할 함수:
- merge_ocr_llm_results(ocr_data, llm_data)
- validate_extracted_data(data, schema)
- normalize_korean_data(data)
"""

# data_processor/validator.py
"""
데이터 검증 엔진
- 필드별 검증 규칙
- 비즈니스 로직 검증
- 이상치 탐지
"""
```

### 6.2 데이터 변환 및 매핑
```python
# data_processor/transformer.py
"""
데이터 변환 엔진

기능:
1. 다양한 출력 형식 지원
2. 사용자 정의 매핑 규칙
3. 데이터 타입 변환
4. 한국어 주소, 전화번호 등 표준화

구현할 클래스:
- DataTransformer
- MappingRule
- KoreanDataNormalizer
"""
```

---

## 7. 내보내기 모듈 (export)

### 7.1 엑셀 내보내기
```python
# export/excel_exporter.py
"""
Excel 파일 생성

기능:
1. 다중 시트 지원
2. 차트 및 그래프 생성
3. 데이터 검증 규칙 적용
4. 템플릿 기반 출력

라이브러리: openpyxl, xlsxwriter

구현할 함수:
- create_excel_file(data, template)
- add_data_validation(worksheet, rules)
- create_charts(worksheet, data)
"""

# export/csv_exporter.py
"""
CSV 파일 생성
- UTF-8 인코딩 (한글 지원)
- 대용량 데이터 스트리밍
- 구분자 선택 옵션
"""
```

### 7.2 템플릿 관리
```python
# export/template_manager.py
"""
내보내기 템플릿 관리

기능:
1. 사용자 정의 템플릿
2. 부서별 템플릿
3. 템플릿 버전 관리
4. 미리보기 기능

구현할 클래스:
- TemplateManager
- ExcelTemplate
- CSVTemplate
"""
```

---

## 8. 학습 시스템 모듈 (learning)

### 8.1 피드백 수집
```python
# learning/feedback_collector.py
"""
사용자 피드백 수집 시스템

기능:
1. 데이터 수정 내역 추적
2. 정확도 평가 수집
3. 사용자 만족도 조사
4. 자동 품질 평가

구현할 함수:
- collect_correction_feedback(original, corrected, user_id)
- calculate_accuracy_metrics(document_id)
- track_user_interactions(user_id, action, data)
"""

# learning/performance_analyzer.py
"""
성능 분석 엔진
- OCR 엔진별 성능 비교
- LLM 모델별 성능 분석
- 문서 유형별 정확도 통계
"""
```

### 8.2 자동 학습 시스템
```python
# learning/auto_learner.py
"""
자동 학습 및 개선 시스템

기능:
1. 프롬프트 자동 최적화
2. 처리 파이프라인 개선
3. 모델 파라미터 튜닝
4. A/B 테스트 자동화

구현할 클래스:
- AutoLearner
- PromptOptimizer
- PipelineOptimizer
"""
```

---

## 9. 감사 및 로깅 모듈 (audit)

### 9.1 감사 로그 시스템
```python
# audit/logger.py
"""
포괄적 감사 로그 시스템

로그 유형:
1. 사용자 액션 로그
2. 시스템 이벤트 로그
3. 데이터 변경 로그
4. API 호출 로그

구현할 함수:
- log_user_action(user_id, action, resource, details)
- log_data_change(table, old_values, new_values, user_id)
- log_api_call(endpoint, user_id, request_data, response)
"""

# audit/compliance.py
"""
컴플라이언스 검사
- 데이터 보존 정책
- 접근 권한 검증
- 보안 정책 준수 확인
"""
```

### 9.2 보고서 생성
```python
# audit/report_generator.py
"""
감사 보고서 자동 생성

보고서 유형:
1. 사용자 활동 보고서
2. 시스템 성능 보고서
3. 데이터 처리 통계
4. 보안 이벤트 보고서

구현할 함수:
- generate_user_activity_report(start_date, end_date)
- generate_performance_report(period)
- generate_security_report()
"""
```

---

## 10. API 관리 모듈 (api_manager)

### 10.1 동적 API 설정
```python
# api_manager/dynamic_config.py
"""
사용자가 OCR/LLM API를 동적으로 추가할 수 있는 시스템

기능:
1. API 설정 UI
2. API 키 안전 저장
3. 연결 테스트
4. 설정 검증

구현할 클래스:
- APIConfigManager
- APICredentialManager
- APITester

UI 화면:
- API 추가/편집 폼
- 연결 테스트 버튼
- 설정 목록 관리
"""

# api_manager/plugin_system.py
"""
플러그인 시스템

기능:
1. 새 API 플러그인 로드
2. 플러그인 버전 관리
3. 설정 스키마 검증
4. 플러그인 활성화/비활성화

구현할 인터페이스:
- OCRPluginInterface
- LLMPluginInterface
- PluginManager
"""
```

### 10.2 API 모니터링
```python
# api_manager/monitor.py
"""
API 사용량 및 성능 모니터링

기능:
1. API 호출 횟수 추적
2. 응답 시간 모니터링
3. 에러율 추적
4. 비용 추적 (상용 API)

구현할 함수:
- track_api_usage(api_name, endpoint, response_time)
- calculate_api_costs(api_name, usage_count)
- monitor_api_health(api_name)
"""
```

---

## 11. 웹 API 모듈 (web_api)

### 11.1 FastAPI 라우터
```python
# web_api/routers/auth.py
"""
인증 관련 API 엔드포인트
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
PUT  /api/v1/auth/password
"""

# web_api/routers/documents.py
"""
문서 관리 API
POST /api/v1/documents/upload
GET  /api/v1/documents
GET  /api/v1/documents/{id}
DELETE /api/v1/documents/{id}
POST /api/v1/documents/{id}/process
GET  /api/v1/documents/{id}/status
"""

# web_api/routers/admin.py
"""
관리자 API
GET  /api/v1/admin/users
POST /api/v1/admin/users
PUT  /api/v1/admin/users/{id}
GET  /api/v1/admin/logs
GET  /api/v1/admin/stats
PUT  /api/v1/admin/settings
"""

# web_api/routers/api_config.py
"""
API 설정 관리
GET  /api/v1/config/ocr-engines
POST /api/v1/config/ocr-engines
PUT  /api/v1/config/ocr-engines/{id}
DELETE /api/v1/config/ocr-engines/{id}
POST /api/v1/config/ocr-engines/{id}/test
"""
```

### 11.2 미들웨어 및 의존성
```python
# web_api/middleware.py
"""
커스텀 미들웨어
- CORS 설정
- 요청/응답 로깅
- 에러 처리
- 속도 제한
"""

# web_api/dependencies.py
"""
공통 의존성 주입
- 데이터베이스 세션
- 현재 사용자 정보
- 권한 검증
- 페이지네이션
"""
```

---

## 12. 프론트엔드 모듈 (frontend)

### 12.1 React 컴포넌트 구조
```javascript
// src/components/Layout/
- Header.tsx          // 헤더, 네비게이션
- Sidebar.tsx         // 사이드바 메뉴
- Layout.tsx          // 전체 레이아웃

// src/components/Documents/
- DocumentUpload.tsx  // 파일 업로드 (드래그앤드롭)
- DocumentList.tsx    // 문서 목록
- DocumentViewer.tsx  // 문서 뷰어
- ProcessingStatus.tsx // 처리 상태 표시

// src/components/Data/
- DataTable.tsx       // 추출된 데이터 테이블
- DataEditor.tsx      // 데이터 편집
- ExportDialog.tsx    // 내보내기 옵션

// src/components/Admin/
- UserManagement.tsx  // 사용자 관리
- APIConfig.tsx       // API 설정 관리
- SystemLogs.tsx      // 로그 조회
- Dashboard.tsx       // 관리자 대시보드

// src/components/Settings/
- OCRSettings.tsx     // OCR 엔진 설정
- LLMSettings.tsx     // LLM 모델 설정
- APIPlugins.tsx      // API 플러그인 관리
```

### 12.2 상태 관리 (Redux Toolkit)
```javascript
// src/store/slices/
- authSlice.ts        // 인증 상태
- documentsSlice.ts   // 문서 관리 상태
- processingSlice.ts  // 처리 작업 상태
- settingsSlice.ts    // 설정 상태
- uiSlice.ts          // UI 상태 (로딩, 알림 등)

// src/store/api/
- authApi.ts          // 인증 API
- documentsApi.ts     // 문서 API  
- adminApi.ts         // 관리자 API
- configApi.ts        // 설정 API
```

### 12.3 핵심 화면 구현
```javascript
// src/pages/
- Login.tsx           // 로그인 페이지
- Dashboard.tsx       // 메인 대시보드
- DocumentUpload.tsx  // 문서 업로드 페이지
- DocumentProcess.tsx // 문서 처리 페이지
- DataManagement.tsx  // 데이터 관리 페이지
- Settings.tsx        // 설정 페이지
- AdminPanel.tsx      // 관리자 패널

// 각 페이지별 구현 요구사항:
1. 반응형 디자인 (모바일 지원)
2. 실시간 상태 업데이트 (WebSocket)
3. 에러 처리 및 사용자 피드백
4. 로딩 상태 표시
5. 접근성 (WCAG 2.1 준수)
```

---

## 13. 배포 및 인프라 모듈 (deployment)

### 13.1 Docker 설정
```dockerfile
# Dockerfile.backend
# Python FastAPI 백엔드 컨테이너
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Dockerfile.frontend  
# React 프론트엔드 컨테이너
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "start"]

# docker-compose.yml
# 전체 서비스 오케스트레이션
services:
  backend, frontend, postgres, redis, celery
```

### 13.2 설정 관리
```yaml
# config/development.yml
# 개발 환경 설정

# config/production.yml  
# 운영 환경 설정

# config/docker.yml
# Docker 환경 설정
```

---

## 개발 단계별 체크리스트

### Phase 1: 기본 인프라 구축 (Week 1-2)
- [ ] 프로젝트 구조 생성
- [ ] 데이터베이스 설계 및 마이그레이션
- [ ] 인증 시스템 구현
- [ ] 기본 API 엔드포인트 구현
- [ ] Docker 환경 구성

### Phase 2: 파일 처리 시스템 (Week 3-4)
- [ ] 파일 업로드 시스템
- [ ] Celery 작업 큐 설정
- [ ] 기본 OCR 엔진 통합 (Tesseract)
- [ ] 파일 메타데이터 관리
- [ ] 기본 프론트엔드 UI

### Phase 3: AI 처리 시스템 (Week 5-6)
- [ ] LLM API 통합 (Ollama, OpenAI)
- [ ] 프롬프트 시스템 구현
- [ ] 데이터 추출 및 구조화
- [ ] OCR+AI 결과 통합
- [ ] 결과 표시 UI

### Phase 4: 동적 API 시스템 (Week 7-8)
- [ ] API 플러그인 시스템
- [ ] 동적 설정 UI
- [ ] API 테스트 기능
- [ ] Mistral OCR API 플러그인
- [ ] 설정 검증 시스템

### Phase 5: 데이터 내보내기 (Week 9-10)
- [ ] Excel/CSV 내보내기
- [ ] 템플릿 시스템
- [ ] 배치 내보내기
- [ ] 내보내기 이력 관리
- [ ] 내보내기 UI

### Phase 6: 감사 및 로깅 (Week 11-12)
- [ ] 포괄적 감사 로그
- [ ] 로그 검색 및 필터링
- [ ] 보고서 생성 시스템
- [ ] 관리자 대시보드
- [ ] 컴플라이언스 검사

### Phase 7: 학습 시스템 (Week 13-14)
- [ ] 피드백 수집 시스템
- [ ] 성능 분석 엔진
- [ ] 자동 개선 시스템
- [ ] A/B 테스트 프레임워크
- [ ] 학습 결과 UI

### Phase 8: 최적화 및 배포 (Week 15-16)
- [ ] 성능 최적화
- [ ] 보안 강화
- [ ] 부하 테스트
- [ ] 모니터링 시스템
- [ ] 운영 환경 배포

---

## AI 코더를 위한 추가 지침

### 코드 품질 요구사항
1. **타입 힌트:** Python은 모든 함수에 타입 힌트 필수
2. **문서화:** 모든 함수/클래스에 docstring 작성
3. **에러 처리:** try-catch 블록으로 예외 처리
4. **로깅:** 중요한 작업은 구조화된 로그 남기기
5. **테스트:** 각 모듈별 단위 테스트 작성

### 보안 고려사항
1. **입력 검증:** 모든 사용자 입력 검증
2. **SQL 인젝션 방지:** ORM 사용
3. **XSS 방지:** 출력 데이터 이스케이프
4. **API 키 보안:** 환경변수로 관리
5. **접근 제어:** 모든 엔드포인트 권한 검증

### 성능 최적화
1. **데이터베이스:** 인덱스 적절히 설정
2. **캐싱:** Redis 활용한 결과 캐싱
3. **비동기 처리:** 무거운 작업은 Celery로 백그라운드 처리
4. **파일 스트리밍:** 대용량 파일 처리 시 스트리밍 방식
5. **API 최적화:** 불필요한 데이터 전송 최소화

### 한국어 특화 처리
1. **인코딩:** UTF-8 강제 사용
2. **폰트:** 한글 폰트 기본 포함
3. **정규식:** 한국어 패턴 매칭 최적화
4. **주소/전화번호:** 한국 형식 검증 및 정규화
5. **날짜:** 한국어 날짜 형식 파싱

### 모니터링 및 알림
1. **헬스체크:** `/health` 엔드포인트 구현
2. **메트릭:** Prometheus 메트릭 수집
3. **알림:** 에러 발생 시 Slack/이메일 알림
4. **대시보드:** Grafana 모니터링 대시보드
5. **로그 분석:** ELK 스택 구성

---

## 데이터베이스 상세 스키마

### 테이블별 인덱스 설정
```sql
-- 성능 최적화를 위한 인덱스
CREATE INDEX idx_documents_user_upload ON documents(uploaded_by, upload_date);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_extracted_data_document ON extracted_data(document_id);
CREATE INDEX idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_feedback_document_user ON feedback(document_id, user_id);

-- 전문 검색을 위한 인덱스
CREATE INDEX idx_documents_filename_gin ON documents USING gin(to_tsvector('korean', filename));
CREATE INDEX idx_extracted_data_value_gin ON extracted_data USING gin(to_tsvector('korean', field_value));
```

### 파티셔닝 전략
```sql
-- 감사 로그 테이블 월별 파티셔닝
CREATE TABLE audit_logs_2025_01 PARTITION OF audit_logs
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- 문서 테이블 연도별 파티셔닝 (대용량 처리 대비)
CREATE TABLE documents_2025 PARTITION OF documents
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

---

## API 플러그인 개발 가이드

### OCR 플러그인 예시
```python
# plugins/ocr/custom_ocr_plugin.py
"""
커스텀 OCR 플러그인 개발 예시

플러그인 개발자가 새로운 OCR API를 추가할 때 사용
"""

from ocr_engines.base import BaseOCREngine
from typing import Dict, Any, List

class CustomOCRPlugin(BaseOCREngine):
    """
    커스텀 OCR 엔진 플러그인
    
    필수 구현 메서드:
    - extract_text()
    - extract_structured_data()
    - get_confidence_score()
    - validate_config()
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        초기화
        
        Args:
            config: {
                "api_key": "your_api_key",
                "endpoint": "https://api.example.com/ocr",
                "timeout": 30,
                "language": "ko"
            }
        """
        self.config = config
        self.api_key = config.get("api_key")
        self.endpoint = config.get("endpoint")
        self.timeout = config.get("timeout", 30)
        self.language = config.get("language", "ko")
    
    def validate_config(self) -> bool:
        """
        설정 검증
        플러그인 등록 시 호출됨
        """
        required_fields = ["api_key", "endpoint"]
        return all(field in self.config for field in required_fields)
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        텍스트 추출
        
        Returns:
            {
                "text": "추출된 텍스트",
                "confidence": 0.95,
                "language": "ko",
                "processing_time": 1.23
            }
        """
        # 실제 API 호출 로직 구현
        pass
    
    def extract_structured_data(self, file_path: str) -> List[Dict]:
        """
        구조화된 데이터 추출 (테이블, 양식 등)
        
        Returns:
            [
                {
                    "type": "table",
                    "bbox": [x1, y1, x2, y2],
                    "data": [["셀1", "셀2"], ["셀3", "셀4"]],
                    "confidence": 0.92
                }
            ]
        """
        # 구조화된 데이터 추출 로직
        pass
    
    def get_confidence_score(self) -> float:
        """
        마지막 처리 결과의 신뢰도 점수 반환
        """
        return self.last_confidence_score

# 플러그인 메타데이터
PLUGIN_METADATA = {
    "name": "Custom OCR",
    "version": "1.0.0",
    "description": "커스텀 OCR API 플러그인",
    "author": "개발자명",
    "config_schema": {
        "api_key": {"type": "string", "required": True, "description": "API 키"},
        "endpoint": {"type": "string", "required": True, "description": "API 엔드포인트"},
        "timeout": {"type": "integer", "default": 30, "description": "타임아웃 (초)"},
        "language": {"type": "string", "default": "ko", "description": "언어 코드"}
    }
}
```

### LLM 플러그인 예시
```python
# plugins/llm/custom_llm_plugin.py
"""
커스텀 LLM 플러그인 개발 예시
"""

from llm_processors.base import BaseLLMProcessor
from typing import Dict, Any, List

class CustomLLMPlugin(BaseLLMProcessor):
    """
    커스텀 LLM 엔진 플러그인
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name", "default")
        self.max_tokens = config.get("max_tokens", 4000)
    
    def analyze_document(self, text: str, prompt: str) -> Dict[str, Any]:
        """
        문서 분석
        
        Args:
            text: OCR로 추출된 텍스트
            prompt: 분석 지시사항
            
        Returns:
            {
                "analysis": "분석 결과",
                "confidence": 0.89,
                "processing_time": 2.34,
                "token_usage": {"prompt": 1200, "completion": 800}
            }
        """
        # LLM API 호출 로직
        pass
    
    def extract_structured_data(self, text: str, schema: Dict) -> List[Dict]:
        """
        스키마 기반 구조화된 데이터 추출
        
        Args:
            text: 분석할 텍스트
            schema: 추출할 데이터 스키마
            
        Returns:
            추출된 구조화 데이터 리스트
        """
        # 스키마 기반 추출 로직
        pass
```

---

## 보안 체크리스트

### 애플리케이션 보안
- [ ] **입력 검증:** 모든 사용자 입력에 대한 화이트리스트 검증
- [ ] **출력 인코딩:** XSS 방지를 위한 HTML 엔티티 인코딩
- [ ] **SQL 인젝션 방지:** ORM 사용 및 매개변수화된 쿼리
- [ ] **CSRF 보호:** CSRF 토큰 검증
- [ ] **파일 업로드 보안:** 
  - 허용된 확장자만 업로드
  - 파일 크기 제한
  - 악성 파일 스캔
  - 안전한 디렉토리에 저장

### 인증 및 권한
- [ ] **강력한 암호 정책:** 최소 8자, 대소문자/숫자/특수문자 조합
- [ ] **JWT 보안:** 
  - 짧은 만료 시간 (15분)
  - 리프레시 토큰 로테이션
  - 비밀키 주기적 교체
- [ ] **세션 관리:** 
  - 세션 타임아웃 설정
  - 동시 로그인 제한
  - 로그아웃 시 세션 완전 삭제
- [ ] **권한 검증:** 모든 API 엔드포인트에 권한 검사

### 데이터 보안
- [ ] **저장 암호화:** 
  - 데이터베이스 TDE (Transparent Data Encryption)
  - 파일 시스템 암호화
  - API 키 AES-256 암호화
- [ ] **전송 암호화:** HTTPS 강제 사용
- [ ] **개인정보 보호:** 
  - 개인정보 마스킹
  - 데이터 익명화
  - 보존 기간 설정 및 자동 삭제

### 네트워크 보안
- [ ] **방화벽 설정:** 필요한 포트만 개방
- [ ] **VPN 접근:** 사내 네트워크에서만 접근 가능
- [ ] **API 보안:** 
  - Rate Limiting
  - API 키 검증
  - IP 화이트리스트

---

## 성능 최적화 가이드

### 데이터베이스 최적화
```sql
-- 자주 사용되는 쿼리 최적화
EXPLAIN ANALYZE SELECT * FROM documents 
WHERE uploaded_by = ? AND status = 'completed' 
ORDER BY upload_date DESC LIMIT 10;

-- 인덱스 사용률 모니터링
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- 슬로우 쿼리 로그 분석
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 10;
```

### 캐싱 전략
```python
# Redis 캐싱 구현 예시
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration=3600):
    """
    함수 결과 캐싱 데코레이터
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 캐시에서 조회
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # 함수 실행 및 캐시 저장
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            return result
        return wrapper
    return decorator

# 사용 예시
@cache_result(expiration=1800)  # 30분 캐싱
def get_user_documents(user_id):
    # 데이터베이스 조회 로직
    pass
```

### 비동기 처리 최적화
```python
# Celery 태스크 체이닝
from celery import chain, group, chord

# 문서 처리 파이프라인
def process_documents_batch(document_ids):
    """
    여러 문서를 병렬로 처리하는 파이프라인
    """
    # 1단계: OCR 처리 (병렬)
    ocr_jobs = group(
        process_ocr.s(doc_id) for doc_id in document_ids
    )
    
    # 2단계: AI 분석 (병렬)
    ai_jobs = group(
        process_ai.s(doc_id) for doc_id in document_ids
    )
    
    # 3단계: 결과 통합 (순차)
    combine_job = combine_results.s(document_ids)
    
    # 체인 실행
    workflow = chain(ocr_jobs, ai_jobs, combine_job)
    return workflow.apply_async()
```

---

## 테스트 전략

### 단위 테스트
```python
# tests/test_ocr_engines.py
import pytest
from unittest.mock import Mock, patch
from ocr_engines.tesseract import TesseractEngine

class TestTesseractEngine:
    @pytest.fixture
    def engine(self):
        config = {"language": "ko", "confidence_threshold": 0.8}
        return TesseractEngine(config)
    
    def test_extract_text_success(self, engine):
        """정상적인 텍스트 추출 테스트"""
        with patch('pytesseract.image_to_string') as mock_ocr:
            mock_ocr.return_value = "테스트 텍스트"
            
            result = engine.extract_text("test_image.jpg")
            
            assert result["text"] == "테스트 텍스트"
            assert result["confidence"] > 0.8
    
    def test_extract_text_low_confidence(self, engine):
        """낮은 신뢰도 텍스트 처리 테스트"""
        with patch('pytesseract.image_to_data') as mock_data:
            mock_data.return_value = {
                'text': ['테스트', '텍스트'],
                'conf': [30, 40]  # 낮은 신뢰도
            }
            
            result = engine.extract_text("blurry_image.jpg")
            
            assert result["confidence"] < 0.5
            assert "low_confidence" in result["warnings"]

# tests/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestDocumentAPI:
    def test_upload_document_success(self):
        """문서 업로드 성공 테스트"""
        with open("test_document.pdf", "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 201
        assert "document_id" in response.json()
    
    def test_upload_invalid_file_type(self):
        """잘못된 파일 형식 업로드 테스트"""
        with open("test.exe", "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("malware.exe", f, "application/x-executable")},
                headers={"Authorization": "Bearer valid_token"}
            )
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
```

### 통합 테스트
```python
# tests/test_integration.py
import pytest
from tests.helpers import create_test_user, upload_test_document

class TestDocumentProcessingFlow:
    """전체 문서 처리 플로우 통합 테스트"""
    
    @pytest.mark.integration
    def test_complete_document_processing(self):
        """문서 업로드부터 데이터 추출까지 전체 플로우"""
        # 1. 사용자 생성
        user = create_test_user()
        
        # 2. 문서 업로드
        document = upload_test_document(user.id, "sample_invoice.pdf")
        
        # 3. OCR 처리
        ocr_result = process_ocr(document.id, "tesseract")
        assert ocr_result["status"] == "completed"
        
        # 4. AI 분석
        ai_result = process_ai(document.id, "gpt-3.5-turbo")
        assert ai_result["status"] == "completed"
        
        # 5. 데이터 추출 확인
        extracted_data = get_extracted_data(document.id)
        assert len(extracted_data) > 0
        assert "invoice_number" in [item["field_name"] for item in extracted_data]
        
        # 6. 엑셀 내보내기
        excel_file = export_to_excel([document.id])
        assert excel_file.exists()
        assert excel_file.suffix == ".xlsx"
```

### 부하 테스트
```python
# tests/load_test.py
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def upload_document_load_test(session, file_path, token):
    """단일 문서 업로드 부하 테스트"""
    with open(file_path, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field('file', f, filename='test.pdf', content_type='application/pdf')
        
        async with session.post(
            'http://localhost:8000/api/v1/documents/upload',
            data=data,
            headers={'Authorization': f'Bearer {token}'}
        ) as response:
            return await response.json()

async def run_load_test(concurrent_users=50, test_duration=60):
    """부하 테스트 실행"""
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        tasks = []
        
        while time.time() - start_time < test_duration:
            if len(tasks) < concurrent_users:
                task = asyncio.create_task(
                    upload_document_load_test(session, "test_document.pdf", "test_token")
                )
                tasks.append(task)
            
            # 완료된 태스크 제거
            tasks = [task for task in tasks if not task.done()]
            await asyncio.sleep(0.1)
        
        # 남은 태스크 완료 대기
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_load_test())
```

---

## 배포 및 운영 가이드

### Docker Compose 설정
```yaml
# docker-compose.production.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.production
    environment:
      - NODE_ENV=production
      - REACT_APP_API_URL=https://api.intellidoc.company.com

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/intellidoc
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    command: celery -A app.celery worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/intellidoc
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./uploads:/app/uploads

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    command: celery -A app.celery beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/intellidoc
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=intellidoc
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  grafana_data:
```

### 백업 스크립트
```bash
#!/bin/bash
# scripts/backup.sh

# 데이터베이스 백업
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL 백업
docker exec intellidoc_postgres_1 pg_dump -U user intellidoc > $BACKUP_DIR/db_backup_$DATE.sql

# 파일 시스템 백업
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz ./uploads

# 7일 이상된 백업 삭제
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

### 모니터링 설정
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'intellidoc-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

---

## 유지보수 가이드

### 정기 점검 항목
```bash
# scripts/health_check.sh
#!/bin/bash

# 서비스 상태 확인
echo "=== Service Status ==="
docker-compose ps

# 디스크 사용량 확인
echo "=== Disk Usage ==="
df -h

# 데이터베이스 연결 확인
echo "=== Database Connection ==="
docker exec intellidoc_postgres_1 pg_isready -U user

# API 응답 확인
echo "=== API Health Check ==="
curl -f http://localhost:8000/health || echo "API health check failed"

# 로그 에러 확인
echo "=== Recent Errors ==="
docker logs intellidoc_backend_1 --since="1h" | grep ERROR

# 메모리 사용량 확인
echo "=== Memory Usage ==="
docker stats --no-stream

echo "Health check completed: $(date)"
```

### 로그 순환 설정
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  }
}
```

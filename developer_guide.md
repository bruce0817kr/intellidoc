# IntelliDoc 개발자 가이드

## 목차
1. [소개](#1-소개)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [코드 구조](#3-코드-구조)
4. [개발 환경 설정](#4-개발-환경-설정)
5. [주요 모듈 상세](#5-주요-모듈-상세)
6. [테스트 전략](#6-테스트-전략)
7. [배포 및 운영](#7-배포-및-운영)
8. [확장성 및 커스터마이징](#8-확장성-및-커스터마이징)
9. [기여 가이드라인](#9-기여-가이드라인)

## 1. 소개

이 문서는 IntelliDoc 시스템의 개발자를 위한 가이드입니다. 시스템 아키텍처, 코드 구조, 개발 환경 설정, 주요 모듈 구현 방식, 테스트 전략, 배포 및 운영, 확장성 등에 대한 정보를 제공하여 개발자가 시스템을 이해하고 유지보수하며 확장하는 데 도움을 주는 것을 목표로 합니다.

## 2. 시스템 아키텍처

IntelliDoc은 확장성과 유지보수성을 고려한 모듈식 마이크로서비스 아키텍처를 기반으로 설계되었습니다. 주요 구성 요소는 다음과 같습니다:

- **프론트엔드 (React/TypeScript)**: 사용자 인터페이스를 제공하며, API를 통해 백엔드와 통신합니다.
- **백엔드 API 게이트웨이 (FastAPI)**: 모든 클라이언트 요청을 받아 적절한 백엔드 서비스로 라우팅하고, 인증 및 로깅을 처리합니다.
- **문서 처리 서비스 (FastAPI/Celery)**: 문서 업로드, OCR 처리, LLM 처리 등 핵심 비즈니스 로직을 수행합니다. 무거운 작업은 Celery를 통해 비동기적으로 처리됩니다.
- **데이터베이스 (PostgreSQL)**: 사용자 정보, 문서 메타데이터, 추출 데이터, 처리 작업 정보 등을 저장합니다.
- **캐시/메시지 큐 (Redis)**: 자주 사용되는 데이터를 캐싱하고, Celery 작업 큐를 관리합니다.
- **OCR 엔진**: Tesseract, Google Vision API, AWS Textract 등 다양한 OCR 엔진을 지원합니다.
- **LLM 엔진**: OpenAI, Ollama 등 다양한 LLM 엔진을 지원합니다.
- **모니터링 (Prometheus/Grafana)**: 시스템 메트릭을 수집하고 시각화하여 시스템 상태를 모니터링합니다.
- **로깅 (ELK Stack)**: 시스템 로그를 중앙에서 수집하고 분석합니다.

### 2.1 아키텍처 다이어그램

```mermaid
graph TD
    User[사용자] --> FE[프론트엔드 (React)]
    FE --> APIGW[API 게이트웨이 (FastAPI)]
    APIGW --> Auth[인증 서비스]
    APIGW --> DocSvc[문서 처리 서비스 (FastAPI/Celery)]
    DocSvc --> DB[(PostgreSQL)]
    DocSvc --> Cache[(Redis)]
    DocSvc --> OCR[OCR 엔진]
    DocSvc --> LLM[LLM 엔진]
    DocSvc --> MQ[메시지 큐 (Redis/Celery)]
    MQ --> Worker[Celery 워커]
    Worker --> DocSvc
    Worker --> DB
    Worker --> OCR
    Worker --> LLM

    subgraph 모니터링
        APIGW --> Prometheus
        DocSvc --> Prometheus
        DB --> Prometheus
        Cache --> Prometheus
        Prometheus --> Grafana[Grafana 대시보드]
    end

    subgraph 로깅
        APIGW --> ELK[ELK 스택]
        DocSvc --> ELK
    end
```

### 2.2 기술 스택 상세
- **백엔드**: Python 3.9+, FastAPI, SQLAlchemy (ORM), Alembic (DB 마이그레이션), Celery, Pydantic (데이터 검증)
- **프론트엔드**: Node.js 16+, React 18+, TypeScript, Ant Design (UI 라이브러리), Axios (HTTP 클라이언트), Redux Toolkit (상태 관리)
- **데이터베이스**: PostgreSQL 13+
- **캐시/메시지 큐**: Redis 6+
- **OCR**: Tesseract 4+, Google Cloud Vision API, AWS Textract API
- **LLM**: OpenAI API, Ollama
- **컨테이너**: Docker, Docker Compose
- **모니터링**: Prometheus, Grafana
- **로깅**: Elasticsearch, Logstash, Kibana (ELK)

## 3. 코드 구조

프로젝트는 백엔드와 프론트엔드로 나뉘어 있으며, 각 디렉토리 구조는 다음과 같습니다:

### 3.1 백엔드 (`/backend`)
```
backend/
├── alembic/              # 데이터베이스 마이그레이션 스크립트
├── shared/               # 공통 모듈 (설정, 모델, 유틸리티 등)
│   ├── config.py         # 환경 변수 및 설정 관리
│   ├── constants.py      # 시스템 상수 정의
│   ├── database.py       # 데이터베이스 연결 및 세션 관리
│   ├── exceptions.py     # 커스텀 예외 클래스
│   ├── logger.py         # 로깅 설정
│   ├── models.py         # SQLAlchemy 데이터베이스 모델
│   ├── schemas.py        # Pydantic 스키마 (데이터 검증 및 직렬화)
│   └── utils.py          # 공통 유틸리티 함수
├── auth/                 # 인증 및 권한 관리 모듈
│   ├── api.py            # 인증 관련 API 엔드포인트
│   ├── permissions.py    # 권한 검사 로직
│   ├── schemas.py        # 인증 관련 스키마
│   └── service.py        # 인증 비즈니스 로직 (JWT, 비밀번호 처리)
├── file_manager/         # 파일 업로드 및 관리 모듈
│   ├── api.py
│   ├── schemas.py
│   └── service.py
├── ocr_engines/          # OCR 엔진 처리 모듈
│   ├── api.py
│   ├── base.py           # OCR 엔진 추상 클래스
│   ├── google_vision.py  # Google Vision 엔진 구현
│   ├── schemas.py
│   ├── service.py
│   └── tesseract.py      # Tesseract 엔진 구현
├── llm_processors/       # LLM 처리 모듈
│   ├── api.py
│   ├── base.py           # LLM 엔진 추상 클래스
│   ├── ollama_engine.py  # Ollama 엔진 구현
│   ├── openai_engine.py  # OpenAI 엔진 구현
│   ├── prompts.py        # LLM 프롬프트 관리
│   ├── schemas.py
│   └── service.py
├── data_processor/       # 데이터 추출 및 구조화 모듈
│   ├── api.py
│   ├── schemas.py
│   └── service.py
├── export/               # 데이터 내보내기 모듈
│   ├── api.py
│   ├── schemas.py
│   └── service.py
├── web_api/              # FastAPI 애플리케이션 진입점 및 라우터
│   ├── dependencies.py   # API 의존성 주입 (DB 세션, 현재 사용자 등)
│   ├── main.py           # FastAPI 앱 초기화 및 미들웨어 설정
│   └── routers.py        # API 라우터 설정
├── celery_app/           # Celery 애플리케이션 설정
│   ├── __init__.py
│   └── tasks.py          # Celery 비동기 작업 정의
├── tests/                # 단위 테스트 및 통합 테스트
├── .env.example          # 환경 변수 예시 파일
├── docker-compose.yml    # Docker Compose 설정 파일
├── Dockerfile            # 백엔드 Docker 이미지 빌드 파일
└── requirements.txt      # Python 의존성 목록
```

### 3.2 프론트엔드 (`/frontend`)
```
frontend/
├── public/               # 정적 파일 (index.html, 파비콘 등)
├── src/
│   ├── assets/           # 이미지, 폰트 등 정적 에셋
│   ├── components/       # 재사용 가능한 UI 컴포넌트
│   │   ├── common/         # 버튼, 입력 필드 등 공통 컴포넌트
│   │   ├── layout/         # 헤더, 사이드바 등 레이아웃 컴포넌트
│   │   └── specific/       # 특정 페이지용 컴포넌트 (예: DocumentViewer)
│   ├── hooks/            # 커스텀 React 훅
│   ├── lib/              # 유틸리티 함수, API 클라이언트 등
│   ├── pages/            # 각 페이지 컴포넌트
│   ├── store/            # 상태 관리 (Redux Toolkit)
│   │   ├── features/     # 기능별 슬라이스 (예: authSlice, documentSlice)
│   │   └── index.ts      # Redux 스토어 설정
│   ├── styles/           # 전역 스타일 및 테마
│   ├── types/            # TypeScript 타입 정의
│   ├── App.tsx           # 메인 애플리케이션 컴포넌트 및 라우팅
│   └── main.tsx          # 애플리케이션 진입점
├── tests/                # 컴포넌트 및 유틸리티 테스트
├── .env.example          # 프론트엔드 환경 변수 예시
├── Dockerfile            # 프론트엔드 Docker 이미지 빌드 파일 (Nginx 기반)
├── package.json          # Node.js 의존성 및 스크립트
├── tsconfig.json         # TypeScript 설정
└── vite.config.ts        # Vite 빌드 설정
```

## 4. 개발 환경 설정

### 4.1 필수 도구 설치
- Python 3.9+
- Node.js 16+
- Docker 및 Docker Compose
- PostgreSQL 13+
- Redis 6+
- Git

### 4.2 백엔드 설정
1. 저장소 클론:
   ```bash
   git clone https://github.com/yourusername/intellidoc.git
   cd intellidoc/backend
   ```
2. 가상 환경 생성 및 활성화:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate  # Windows
   ```
3. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```
4. 환경 변수 설정:
   ```bash
   cp .env.example .env
   # .env 파일 수정 (데이터베이스 연결 정보, API 키 등)
   ```
5. 데이터베이스 마이그레이션:
   ```bash
   # Docker Compose로 PostgreSQL 실행 권장
   docker-compose up -d postgres redis
   alembic upgrade head
   ```
6. 개발 서버 실행:
   ```bash
   uvicorn web_api.main:app --reload --host 0.0.0.0 --port 8000
   ```
7. Celery 워커 실행 (별도 터미널):
   ```bash
   celery -A celery_app worker --loglevel=info
   ```

### 4.3 프론트엔드 설정
1. 프론트엔드 디렉토리 이동:
   ```bash
   cd ../frontend
   ```
2. 의존성 설치:
   ```bash
   npm install
   ```
3. 환경 변수 설정:
   ```bash
   cp .env.example .env.local
   # .env.local 파일 수정 (백엔드 API URL 등)
   ```
4. 개발 서버 실행:
   ```bash
   npm run dev
   ```

### 4.4 Docker Compose 사용 (권장)
Docker Compose를 사용하면 모든 서비스를 한 번에 실행할 수 있습니다.
```bash
cd intellidoc
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# .env 파일들 수정
docker-compose up --build -d
```

## 5. 주요 모듈 상세

### 5.1 인증 모듈 (`/backend/auth`)
- **JWT 기반 인증**: `access_token`과 `refresh_token` 사용
- **비밀번호 해싱**: `bcrypt` 사용
- **권한 관리**: 역할 기반 접근 제어 (RBAC)
- **FastAPI 의존성 주입**: `get_current_user` 함수를 통해 현재 사용자 정보 제공

### 5.2 문서 처리 서비스 (`/backend/file_manager`, `/backend/ocr_engines`, `/backend/llm_processors`)
- **비동기 처리**: Celery를 사용하여 OCR, LLM 등 시간이 오래 걸리는 작업을 백그라운드에서 처리
- **상태 관리**: 문서 처리 상태(PENDING, PROCESSING, COMPLETED, ERROR)를 데이터베이스에 기록하고 추적
- **엔진 추상화**: 다양한 OCR/LLM 엔진을 쉽게 추가하거나 교체할 수 있도록 추상 클래스(`base.py`) 기반 설계
- **오류 처리**: 각 처리 단계에서 발생할 수 있는 오류를 정의하고 처리 로직 구현

### 5.3 데이터베이스 모듈 (`/backend/shared/models.py`, `/backend/shared/database.py`)
- **ORM**: SQLAlchemy 사용
- **모델 정의**: 각 테이블에 해당하는 Python 클래스 정의
- **마이그레이션**: Alembic을 사용하여 데이터베이스 스키마 변경 관리
- **세션 관리**: FastAPI 의존성 주입을 통해 각 요청마다 독립적인 DB 세션 제공

### 5.4 프론트엔드 상태 관리 (`/frontend/src/store`)
- **Redux Toolkit**: 전역 상태 관리 라이브러리
- **슬라이스**: 기능별로 상태 로직 분리 (예: `authSlice`, `documentSlice`)
- **비동기 로직**: `createAsyncThunk`를 사용하여 API 호출 및 상태 업데이트 처리

## 6. 테스트 전략

### 6.1 백엔드 테스트 (`/backend/tests`)
- **단위 테스트**: `unittest` 또는 `pytest` 사용. 각 서비스 및 유틸리티 함수에 대한 테스트 작성. DB 및 외부 API는 모킹(Mocking) 사용.
- **통합 테스트**: `FastAPI TestClient` 사용. 실제 API 엔드포인트를 호출하여 전체 흐름 테스트. 테스트용 데이터베이스 사용.
- **테스트 실행**: `python -m unittest discover -s tests` 또는 `pytest`

### 6.2 프론트엔드 테스트 (`/frontend/tests`)
- **단위 테스트**: `Vitest` 또는 `Jest` 사용. 컴포넌트, 훅, 유틸리티 함수 테스트.
- **컴포넌트 테스트**: `@testing-library/react` 사용. 사용자 상호작용 시뮬레이션 및 렌더링 결과 검증.
- **E2E 테스트**: `Cypress` 또는 `Playwright` 사용. 실제 브라우저 환경에서 전체 사용자 시나리오 테스트.
- **테스트 실행**: `npm test` 또는 `npm run test:e2e`

### 6.3 CI/CD 파이프라인
- GitHub Actions 또는 Jenkins 등을 사용하여 코드 푸시 시 자동으로 테스트 실행 및 빌드/배포 자동화 구성 권장.

## 7. 배포 및 운영

### 7.1 배포 옵션
- **Docker Compose**: 가장 간편한 배포 방법. `docker-compose.yml` 파일 참조.
- **Kubernetes**: 대규모 환경 또는 고가용성이 필요한 경우 권장.
- **클라우드 플랫폼**: AWS, GCP, Azure 등 클라우드 서비스의 관리형 서비스(컨테이너, 데이터베이스, 캐시 등) 활용.

### 7.2 Docker 이미지 빌드
- 백엔드: `docker build -t intellidoc-backend:latest backend/`
- 프론트엔드: `docker build -t intellidoc-frontend:latest frontend/`

### 7.3 환경 변수 관리
- `.env` 파일을 사용하여 환경별 설정 관리 (데이터베이스 정보, API 키, 시크릿 키 등).
- 운영 환경에서는 환경 변수를 안전하게 관리하는 방법 사용 (예: AWS Secrets Manager, HashiCorp Vault).

### 7.4 모니터링 및 로깅
- **Prometheus/Grafana**: 시스템 메트릭(CPU, 메모리, 요청 수, 응답 시간 등) 모니터링.
- **ELK Stack**: 로그 중앙 수집 및 분석. 오류 추적 및 성능 분석에 활용.
- **헬스 체크**: `/health` 엔드포인트를 통해 서비스 상태 주기적 확인.

### 7.5 데이터베이스 관리
- **백업**: 정기적인 데이터베이스 백업 설정 (예: `pg_dump`).
- **마이그레이션**: `alembic`을 사용하여 스키마 변경 관리.
- **성능 튜닝**: 느린 쿼리 분석 및 인덱스 최적화.

## 8. 확장성 및 커스터마이징

### 8.1 OCR/LLM 엔진 추가
1. `/backend/ocr_engines` 또는 `/backend/llm_processors` 디렉토리에 새로운 엔진 구현 파일 추가.
2. `base.py`의 추상 클래스를 상속받아 필요한 메서드 구현.
3. `service.py` 파일에서 새로운 엔진을 인식하고 사용할 수 있도록 로직 수정.
4. API 및 프론트엔드에서 새로운 엔진 선택 옵션 추가.

### 8.2 데이터베이스 스키마 확장
1. `/backend/shared/models.py` 파일에 새로운 모델 또는 필드 추가.
2. `alembic revision --autogenerate -m "Add new feature"` 명령으로 마이그레이션 스크립트 생성.
3. 생성된 마이그레이션 스크립트 검토 및 수정.
4. `alembic upgrade head` 명령으로 데이터베이스 스키마 업데이트.
5. 관련 서비스 및 API 로직 수정.

### 8.3 외부 시스템 연동 (예: MongoDB)
- **API 활용**: IntelliDoc API를 사용하여 외부 시스템에서 문서 처리 기능을 호출하고 결과를 받아 MongoDB에 저장. (API 문서 참조)
- **웹훅 활용**: IntelliDoc 웹훅을 설정하여 처리 완료 이벤트를 수신하고, 해당 데이터를 MongoDB에 저장. (API 문서 참조)
- **직접 연동 (백엔드 수정)**:
  1. MongoDB 클라이언트 라이브러리 설치 (`pymongo`).
  2. `/backend/shared/database.py` 또는 별도 모듈에 MongoDB 연결 설정 추가.
  3. 데이터 처리 서비스(`data_processor/service.py`) 또는 Celery 태스크(`celery_app/tasks.py`)에서 처리 결과를 MongoDB에 저장하는 로직 추가.
  4. 필요시 관련 API 엔드포인트 수정.

### 8.4 커스텀 처리 로직 추가
- **Celery 태스크**: `/backend/celery_app/tasks.py`에 새로운 비동기 작업 정의.
- **FastAPI 서비스**: 특정 기능을 위한 새로운 서비스 모듈 생성 및 API 라우터 등록.
- **커스텀 스크립트 API**: `/documents/{document_id}/custom_pipeline` API를 활용하여 미리 정의된 커스텀 스크립트 실행.

### 8.5 프론트엔드 커스터마이징
- **테마**: `/frontend/src/styles` 디렉토리에서 스타일 및 테마 수정.
- **UI 컴포넌트**: Ant Design 컴포넌트를 사용하거나, `/frontend/src/components`에 커스텀 컴포넌트 추가.
- **기능 추가**: 새로운 페이지, 상태 관리 슬라이스, API 연동 로직 추가.

## 9. 기여 가이드라인

IntelliDoc 프로젝트에 기여하려면 다음 가이드라인을 따르십시오:

1. **이슈 트래커 확인**: 작업 시작 전 관련 이슈가 있는지 확인하고, 없다면 새로 생성합니다.
2. **브랜치 생성**: `main` 브랜치에서 새로운 기능 또는 버그 수정 브랜치를 생성합니다 (예: `feature/new-feature`, `fix/bug-fix`).
3. **코드 스타일**: 프로젝트의 코드 스타일 가이드(예: Black, Prettier)를 따릅니다.
4. **테스트 작성**: 새로운 기능이나 수정 사항에 대한 단위 테스트 및 통합 테스트를 작성합니다.
5. **문서화**: 코드 주석 및 관련 문서를 업데이트합니다.
6. **Pull Request 생성**: 변경 사항을 푸시하고 `main` 브랜치로 Pull Request를 생성합니다. PR 설명에는 변경 내용과 관련 이슈 번호를 명시합니다.
7. **코드 리뷰**: 최소 1명 이상의 리뷰어에게 코드 리뷰를 요청하고 피드백을 반영합니다.
8. **머지**: 리뷰 승인 후 PR을 `main` 브랜치에 머지합니다.

---

이 개발자 가이드에 대한 문의사항이나 개선 제안이 있다면 프로젝트 관리자에게 연락하거나 이슈 트래커에 등록해 주세요.

© 2025 IntelliDoc. All rights reserved.

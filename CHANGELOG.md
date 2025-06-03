# 변경 로그 (Changelog)

IntelliDoc 프로젝트의 모든 주요 변경사항이 이 파일에 문서화됩니다.

이 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 기반으로 하며,
이 프로젝트는 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)을 준수합니다.

## [Unreleased]

### 추가됨
- 프로젝트 초기 릴리스 준비
- 포괄적인 문서화 (README, CONTRIBUTING, LICENSE)
- GitHub 리포지토리 설정

## [1.0.0] - 2025-06-03

### 추가됨
- **OCR 엔진 지원**
  - Tesseract OCR 통합
  - Mistral OCR 엔진 지원
  - 배치 처리 기능
  - 후처리 및 정제 기능

- **LLM 통합**
  - OpenAI GPT 모델 지원
  - Ollama 로컬 모델 지원
  - 구조화된 데이터 추출
  - 커스텀 프롬프트 템플릿

- **웹 애플리케이션**
  - React + TypeScript 프론트엔드
  - FastAPI 백엔드
  - 실시간 처리 상태 표시
  - 반응형 UI 디자인

- **데이터 내보내기**
  - Excel, CSV, JSON, PDF 형식 지원
  - 사용자 정의 템플릿
  - 실시간 미리보기

- **인증 및 보안**
  - JWT 기반 인증
  - 역할 기반 접근 제어
  - 보안 스캔 도구 통합

- **데이터베이스**
  - PostgreSQL 통합
  - Redis 캐싱
  - SQLAlchemy ORM

- **DevOps**
  - Docker 컨테이너화
  - Docker Compose 설정
  - Nginx 리버스 프록시
  - 자동 배포 스크립트

- **테스팅**
  - 포괄적인 단위 테스트 (64개 테스트)
  - 통합 테스트
  - 성능 테스트
  - 보안 테스트

### 기술 스택
- **Backend**: Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **OCR**: Tesseract, Mistral OCR
- **LLM**: OpenAI API, Ollama
- **DevOps**: Docker, Nginx, GitHub Actions

### 성능
- 문서 처리 속도: 평균 2-5초 (페이지당)
- 동시 사용자 지원: 최대 100명
- 메모리 사용량: 기본 512MB, 확장 가능

### 보안
- 모든 보안 취약점 스캔 통과
- HTTPS 강제 사용
- 파일 업로드 검증
- SQL 인젝션 방지

---

## 범례

- `추가됨`: 새로운 기능
- `변경됨`: 기존 기능의 변경사항
- `지원 중단`: 곧 제거될 기능
- `제거됨`: 이번 버전에서 제거된 기능
- `수정됨`: 버그 수정
- `보안`: 보안 관련 변경사항

# 📄 IntelliDoc

**지능형 문서 처리 및 분석 플랫폼**

IntelliDoc은 OCR, LLM, 그리고 지능형 데이터 추출 기술을 결합하여 문서를 자동으로 처리하고 분석하는 현대적인 웹 애플리케이션입니다.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## 🚀 주요 기능

### 📋 문서 처리
- **다중 OCR 엔진 지원**: Tesseract, Mistral OCR 등 여러 OCR 엔진
- **배치 처리**: 여러 문서를 동시에 처리
- **지원 포맷**: PDF, 이미지 파일 (PNG, JPEG, TIFF)

### 🤖 AI 기반 분석
- **LLM 통합**: OpenAI GPT, Ollama 등 다양한 LLM 지원
- **자동 데이터 추출**: AI를 활용한 구조화된 데이터 추출
- **스마트 후처리**: 추출된 데이터의 자동 검증 및 정제

### 📊 데이터 내보내기
- **다양한 형식**: Excel, CSV, JSON, PDF
- **사용자 정의 템플릿**: 맞춤형 출력 템플릿 지원
- **실시간 미리보기**: 내보내기 전 결과 미리보기

### 🔐 보안 및 인증
- **JWT 인증**: 안전한 사용자 인증 시스템
- **역할 기반 접근 제어**: 관리자, 사용자 등 역할별 권한 관리
- **보안 스캔**: 자동 보안 취약점 검사

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (React +      │◄──►│   (FastAPI +    │◄──►│   (PostgreSQL + │
│    TypeScript)  │    │    Python)      │    │    Redis)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   File Storage  │
                    │   (Local/Cloud) │
                    └─────────────────┘
```

## 🔧 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.13)
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL + Redis
- **OCR**: Tesseract, Mistral OCR
- **LLM**: OpenAI API, Ollama
- **Task Queue**: Celery

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios

### DevOps
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx
- **Testing**: pytest, Jest
- **CI/CD**: GitHub Actions (설정 가능)

## 📦 설치 및 실행

### 필수 요구사항

- **Python 3.13+**
- **Node.js 18+**
- **Docker & Docker Compose**
- **PostgreSQL 13+**
- **Redis 6+**

## 🚀 원클릭 배포

### Windows
```powershell
# PowerShell 실행
.\deploy.ps1

# 또는 배치 파일
.\deploy.bat

# Make 사용 (선택사항)
make deploy
```

### Linux/macOS
```bash
# 실행 권한 부여 후 실행
chmod +x deploy.sh
./deploy.sh

# Make 사용
make deploy
```

## 🐳 Docker를 사용한 설치 (권장)

1. **저장소 클론**
```bash
git clone https://github.com/YOUR_USERNAME/intellidoc.git
cd intellidoc
```

2. **환경 변수 설정**
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 설정을 입력하세요
```

3. **Docker Compose로 실행**
```bash
# 개발 환경
docker-compose -f docker-compose.dev.yml up -d

# 프로덕션 환경
docker-compose up -d
```

4. **애플리케이션 접속**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API 문서: http://localhost:8000/docs

## 🛠️ 로컬 개발 설정

### Backend 설정

1. **가상환경 생성 및 활성화**
```bash
# Windows
.\setup_venv.ps1

# Linux/Mac
./setup_venv.sh
```

2. **의존성 설치**
```bash
cd backend
pip install -r requirements-dev.txt
```

3. **데이터베이스 설정**
```bash
# PostgreSQL 및 Redis가 실행 중이어야 합니다
python -m alembic upgrade head
```

4. **Backend 서버 실행**
```bash
uvicorn web_api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend 설정

1. **의존성 설치**
```bash
cd frontend
npm install
```

2. **개발 서버 실행**
```bash
npm run dev
```

## 🧪 테스트

### Backend 테스트
```bash
cd backend
pytest tests/ -v --cov=.
```

### Frontend 테스트
```bash
cd frontend
npm test
```

### 통합 테스트
```bash
# Windows
.\test_integration.ps1

# Linux/Mac
./test_integration.sh
```

## 📚 사용법

### 1. 문서 업로드
1. 웹 인터페이스에서 "문서 업로드" 클릭
2. PDF 또는 이미지 파일 선택
3. OCR 엔진 및 처리 옵션 선택

### 2. AI 분석 설정
1. 사용할 LLM 모델 선택
2. 추출할 데이터 필드 정의
3. 분석 시작

### 3. 결과 확인 및 내보내기
1. 추출된 데이터 검토
2. 필요시 수동 수정
3. 원하는 형식으로 내보내기

## 🔧 설정

### 환경 변수

```bash
# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost/intellidoc
REDIS_URL=redis://localhost:6379

# API 키
OPENAI_API_KEY=your_openai_api_key
OLLAMA_BASE_URL=http://localhost:11434

# 보안
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# 파일 업로드
MAX_FILE_SIZE=50MB
UPLOAD_DIR=/app/uploads
```

### OCR 엔진 설정

#### Tesseract
```bash
# 추가 언어팩 설치 (선택사항)
sudo apt-get install tesseract-ocr-kor  # 한국어
```

#### Mistral OCR
```bash
# API 키 설정
export MISTRAL_API_KEY=your_mistral_api_key
```

## 🔌 API 문서

자세한 API 문서는 다음에서 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### 주요 엔드포인트

```
POST /api/v1/documents/upload     # 문서 업로드
GET  /api/v1/documents/{id}       # 문서 조회
POST /api/v1/documents/{id}/ocr   # OCR 처리
POST /api/v1/documents/{id}/llm   # LLM 분석
GET  /api/v1/documents/{id}/export # 데이터 내보내기
```

## 🤝 기여하기

프로젝트에 기여해주셔서 감사합니다! 기여 방법:

1. **Fork** 저장소
2. **Feature branch** 생성 (`git checkout -b feature/amazing-feature`)
3. **Commit** 변경사항 (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Pull Request** 생성

자세한 기여 가이드라인은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

## 📋 로드맵

- [ ] **v1.1.0**: 추가 OCR 엔진 지원
- [ ] **v1.2.0**: 실시간 협업 기능
- [ ] **v1.3.0**: 모바일 앱 지원
- [ ] **v2.0.0**: AI 모델 파인튜닝 기능

## 🐛 이슈 및 버그 리포트

이슈가 발견되면 [GitHub Issues](https://github.com/YOUR_USERNAME/intellidoc/issues)에 보고해주세요.

버그 리포트 시 포함할 정보:
- 운영체제 및 버전
- Python/Node.js 버전
- 에러 메시지 및 스택 트레이스
- 재현 단계

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들을 기반으로 합니다:

- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://reactjs.org/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [OpenAI API](https://openai.com/api/)

## 📞 연락처

- **GitHub**: [프로젝트 저장소](https://github.com/YOUR_USERNAME/intellidoc)
- **문서**: [프로젝트 위키](https://github.com/YOUR_USERNAME/intellidoc/wiki)
- **이슈**: [GitHub Issues](https://github.com/YOUR_USERNAME/intellidoc/issues)

---

⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요!
./deploy.sh

# Make 사용
make deploy
```

## 📋 주요 배포 명령어

| 명령어 | 설명 |
|--------|------|
| `make deploy` | 포트 자동 할당 + 서비스 배포 |
| `make deploy-clean` | 완전 정리 후 새로 배포 |
| `make dev` | 개발 모드 배포 |
| `make ports` | 포트 충돌만 해결 |
| `make stop` | 서비스 중지 |
| `make clean` | 완전 정리 |
| `make logs` | 로그 확인 |

## 🔧 포트 충돌 자동 해결

IntelliDoc은 **포트 매니저**를 통해 배포 시 포트 충돌을 자동으로 해결합니다:

- ✅ 사용 중인 포트 자동 감지
- ✅ 사용 가능한 포트로 자동 할당
- ✅ Docker Compose 파일 자동 업데이트
- ✅ 환경 변수 파일 자동 업데이트
- ✅ 기존 컨테이너 자동 정리

### 수동 포트 관리
```bash
# Windows
.\setup_ports.bat

# Linux/macOS
./setup_ports.sh

# Python 직접 실행
python port_manager.py
```

## 🛠️ 개발 환경 설정

### 1. 초기 설정
```bash
# 전체 개발 환경 구성
make setup

# 또는 단계별 설정
make deps     # 의존성 설치
make ports    # 포트 설정
make build    # 이미지 빌드
```

### 2. 개발 서버 실행
```bash
make dev
```

## 📊 서비스 정보 확인

```bash
# 컨테이너 상태
make status

# 서비스 정보 및 포트
make info

# 로그 확인
make logs
make logs-backend  # 백엔드만
make logs-frontend # 프론트엔드만
```

## 🌐 기본 접속 정보

배포 완료 후 다음 URL로 접속할 수 있습니다:

- **웹 애플리케이션**: http://localhost (포트는 자동 할당)
- **API 서버**: http://localhost:8000 (포트는 자동 할당)  
- **API 문서**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (선택사항)

> 실제 포트는 `allocated_ports.json` 파일에서 확인하거나 `make info` 명령으로 확인할 수 있습니다.

## 🏭 프로덕션 배포

```bash
# 프로덕션 환경
make production

# 또는 PowerShell
.\deploy.ps1 -Environment production
```

## 💾 백업 및 복원

```bash
# 데이터 백업
make backup

# 데이터 복원
make restore BACKUP_FILE=backup_20250602_143000.sql
```

## 🐛 문제 해결

### 포트 충돌 문제
```bash
# 포트 재할당
make ports

# 완전 재배포
make deploy-clean
```

### 컨테이너 문제
```bash
# 컨테이너 상태 확인
make status

# 로그 확인
make logs

# 완전 정리 후 재시작
make clean
make deploy
```

### 이미지 문제
```bash
# 이미지 재빌드
make build

# 캐시 없이 빌드
docker-compose build --no-cache
```

## 📁 주요 파일

- `port_manager.py`: 포트 충돌 해결 스크립트
- `deploy.ps1` / `deploy.bat`: Windows 배포 스크립트
- `deploy.sh`: Linux/macOS 배포 스크립트
- `Makefile`: 크로스 플랫폼 명령어 모음
- `allocated_ports.json`: 할당된 포트 정보
- `docker-compose.yml`: 기본 Docker Compose 설정

## 🔐 기본 계정

- **관리자**: admin / admin123

## 📖 추가 문서

- [API 문서](api_documentation.md)
- [개발자 가이드](developer_guide.md)
- [사용자 매뉴얼](user_manual.md)
- [Docker 배포 가이드](docker_deployment_guide.md)

---

## 🆘 지원

문제가 발생했거나 추가 기능이 필요한 경우:

1. 로그 확인: `make logs`
2. 상태 확인: `make status`  
3. 완전 재배포: `make deploy-clean`
4. GitHub Issues에 문의

**Happy Coding! 🎉**

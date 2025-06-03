# IntelliDoc Makefile
# use MCP: context7, Github, Sequential Thinking, Task Manager, Memory Bank

.PHONY: help deploy deploy-clean dev stop clean logs build ports test

# 기본 타겟
help:
	@echo "IntelliDoc 배포 및 관리 명령어"
	@echo "================================="
	@echo "deploy        : 포트 자동 할당 + 서비스 배포"
	@echo "deploy-clean  : 완전 정리 후 새로 배포"
	@echo "dev           : 개발 모드로 배포"
	@echo "ports         : 포트 충돌만 해결"
	@echo "build         : Docker 이미지 빌드"
	@echo "stop          : 서비스 중지"
	@echo "clean         : 컨테이너 및 볼륨 정리"
	@echo "logs          : 서비스 로그 확인"
	@echo "test          : 테스트 실행"

# 원클릭 배포
deploy:
	@echo "🚀 IntelliDoc 원클릭 배포 실행..."
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy Bypass -File deploy.ps1
else
	./deploy.sh
endif

# 완전 정리 후 배포
deploy-clean:
	@echo "🧹 완전 정리 후 새로 배포..."
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy Bypass -File deploy.ps1 -CleanStart
else
	./deploy.sh development --skip-port --clean
endif

# 개발 모드
dev:
	@echo "💻 개발 모드로 배포..."
	$(MAKE) ports
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 포트 충돌만 해결
ports:
	@echo "🔧 포트 충돌 해결 중..."
ifeq ($(OS),Windows_NT)
	setup_ports.bat
else
	./setup_ports.sh
endif

# Docker 이미지 빌드
build:
	@echo "🔨 Docker 이미지 빌드 중..."
	docker build -t intellidoc-backend:latest ./backend/
	docker build -t intellidoc-frontend:latest ./frontend/

# 서비스 중지
stop:
	@echo "⏹️ 서비스 중지 중..."
	docker-compose stop

# 완전 정리
clean:
	@echo "🗑️ 컨테이너 및 볼륨 정리 중..."
	docker-compose down -v
	docker system prune -f

# 로그 확인
logs:
	@echo "📄 서비스 로그 확인..."
	docker-compose logs -f

# 특정 서비스 로그
logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-worker:
	docker-compose logs -f worker

# 컨테이너 상태 확인
status:
	@echo "📊 컨테이너 상태:"
	docker-compose ps

# 테스트 실행
test:
	@echo "🧪 테스트 실행 중..."
	docker-compose exec backend python -m pytest tests/

# 포트 정보 표시
info:
	@echo "📋 IntelliDoc 서비스 정보:"
	@if [ -f "allocated_ports.json" ]; then \
		echo "포트 할당 정보:"; \
		cat allocated_ports.json; \
	else \
		echo "포트 정보 없음. 'make ports' 실행 필요"; \
	fi

# 의존성 설치
deps:
	@echo "📦 개발 의존성 설치 중..."
ifeq ($(OS),Windows_NT)
	pip install -r requirements-dev.txt
else
	pip3 install -r requirements-dev.txt
endif

# 개발 환경 초기 설정
setup:
	@echo "🛠️ 개발 환경 초기 설정..."
	$(MAKE) deps
	$(MAKE) ports
	$(MAKE) build
	@echo "✅ 개발 환경 설정 완료!"

# 프로덕션 배포
production:
	@echo "🏭 프로덕션 배포..."
	$(MAKE) ports
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 백업
backup:
	@echo "💾 데이터 백업 중..."
	docker-compose exec postgres pg_dump -U intellidoc intellidoc > backup_$(shell date +%Y%m%d_%H%M%S).sql

# 복원
restore:
	@echo "🔄 데이터 복원 중..."
	@echo "사용법: make restore BACKUP_FILE=backup_file.sql"
ifdef BACKUP_FILE
	docker-compose exec -T postgres psql -U intellidoc intellidoc < $(BACKUP_FILE)
else
	@echo "❌ BACKUP_FILE 매개변수가 필요합니다."
endif

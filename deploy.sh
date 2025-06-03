#!/bin/bash

# IntelliDoc 원클릭 배포 스크립트 (Linux/macOS)
# use MCP: context7, Github, Sequential Thinking, Task Manager, Memory Bank

set -e  # 오류 발생 시 스크립트 종료

ENVIRONMENT=${1:-development}
SKIP_PORT_CHECK=$2
CLEAN_START=$3

echo "🚀 IntelliDoc 자동 배포 시작"
echo "환경: $ENVIRONMENT"
echo "=================================================="

# 1. 포트 충돌 해결
if [ "$SKIP_PORT_CHECK" != "--skip-port" ]; then
    echo "🔧 1단계: 포트 충돌 해결 중..."
    
    if [ ! -d "venv" ]; then
        echo "Python 가상환경 생성 중..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements-dev.txt -q
    
    python port_manager.py
    if [ $? -ne 0 ]; then
        echo "❌ 포트 매니저 실행 실패!"
        exit 1
    fi
fi

# 2. 기존 컨테이너 정리 (선택적)
if [ "$CLEAN_START" = "--clean" ]; then
    echo "🧹 2단계: 기존 컨테이너 정리 중..."
    docker-compose down -v
fi

# 3. Docker 이미지 빌드 확인
echo "🔨 3단계: Docker 이미지 확인 및 빌드..."
if [ -z "$(docker images -q intellidoc-backend:latest 2>/dev/null)" ]; then
    echo "백엔드 이미지 빌드 중..."
    docker build -t intellidoc-backend:latest ./backend/
fi

if [ -z "$(docker images -q intellidoc-frontend:latest 2>/dev/null)" ]; then
    echo "프론트엔드 이미지 빌드 중..."
    docker build -t intellidoc-frontend:latest ./frontend/
fi

# 4. 서비스 시작
echo "🚀 4단계: 서비스 시작 중..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo "✅ 배포 성공!"
    
    # 포트 정보 표시
    if [ -f "allocated_ports.json" ]; then
        echo ""
        echo "🌐 서비스 접속 정보:"
        if command -v jq >/dev/null 2>&1; then
            FRONTEND_PORT=$(jq -r '.frontend' allocated_ports.json)
            BACKEND_PORT=$(jq -r '.backend' allocated_ports.json)
            echo "웹 애플리케이션: http://localhost:$FRONTEND_PORT"
            echo "API 서버: http://localhost:$BACKEND_PORT"
            echo "API 문서: http://localhost:$BACKEND_PORT/docs"
        else
            echo "자세한 포트 정보는 allocated_ports.json을 확인하세요"
        fi
    fi
    
    echo ""
    echo "📊 컨테이너 상태:"
    docker-compose ps
    
else
    echo "❌ 배포 실패!"
    echo "로그 확인: docker-compose logs"
    exit 1
fi

echo ""
echo "🎉 IntelliDoc 배포 완료!"
echo "문제 발생 시: ./deploy.sh $ENVIRONMENT --skip-port --clean 로 완전 재배포하세요"

# 실행 권한 부여
chmod +x deploy.sh

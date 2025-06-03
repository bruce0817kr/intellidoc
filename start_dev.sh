#!/bin/bash
# IntelliDoc 개발 환경 시작 스크립트 (Linux/macOS)
# 사용법: ./start_dev.sh [-c|--clean] [-r|--rebuild] [-t|--tools]

# 기본 옵션 설정
CLEAN=false
REBUILD=false
TOOLS=false

# 인수 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -r|--rebuild)
            REBUILD=true
            shift
            ;;
        -t|--tools)
            TOOLS=true
            shift
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            echo "사용법: ./start_dev.sh [-c|--clean] [-r|--rebuild] [-t|--tools]"
            exit 1
            ;;
    esac
done

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로고 출력
echo -e "${CYAN}
 _____       _       _ _ _ _____             
|_   _|     | |     | | (_)  __ \            
  | |  _ __ | |_ ___| | |_| |  | | ___   ___ 
  | | | '_ \| __/ _ \ | | | |  | |/ _ \ / __|
 _| |_| | | | ||  __/ | | | |__| | (_) | (__ 
|_____|_| |_|\__\___|_|_|_|_____/ \___/ \___|
                                             
${NC}"

echo -e "${CYAN}ℹ️  IntelliDoc 개발 환경 시작 스크립트${NC}"
echo -e "${CYAN}===========================================${NC}"
echo -e "${CYAN}ℹ️  작업 시간: $(date)${NC}"
echo -e "${CYAN}ℹ️  옵션: Clean=$CLEAN, Rebuild=$REBUILD, Tools=$TOOLS${NC}"
echo -e "${CYAN}===========================================${NC}"

# 오류 발생 시 스크립트 종료
set -e

# Docker 확인
echo -e "${CYAN}ℹ️  Docker 환경 확인 중...${NC}"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${CYAN}ℹ️  Docker 버전: $DOCKER_VERSION${NC}"
else
    echo -e "${RED}❌ Docker가 설치되지 않았습니다.${NC}"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo -e "${CYAN}ℹ️  Docker Compose 버전: $COMPOSE_VERSION${NC}"
else
    echo -e "${RED}❌ Docker Compose가 설치되지 않았습니다.${NC}"
    exit 1
fi

# 포트 매니저 실행
echo -e "${CYAN}ℹ️  포트 매니저 실행 중...${NC}"

if command -v python3 &> /dev/null; then
    python3 port_manager.py || {
        echo -e "${YELLOW}⚠️  포트 매니저 오류: $?${NC}"
        echo -e "${CYAN}ℹ️  포트 충돌이 발생할 수 있습니다.${NC}"
    }
elif command -v python &> /dev/null; then
    python port_manager.py || {
        echo -e "${YELLOW}⚠️  포트 매니저 오류: $?${NC}"
        echo -e "${CYAN}ℹ️  포트 충돌이 발생할 수 있습니다.${NC}"
    }
else
    echo -e "${YELLOW}⚠️  Python이 설치되지 않았습니다. 포트 충돌이 발생할 수 있습니다.${NC}"
fi

# 환경 변수 파일 확인
echo -e "${CYAN}ℹ️  환경 변수 파일 확인 중...${NC}"

if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        echo -e "${YELLOW}⚠️  .env 파일이 없습니다. .env.example을 복사합니다.${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️  .env 파일을 편집하여 실제 API 키를 설정하세요.${NC}"
    else
        echo -e "${YELLOW}⚠️  .env 및 .env.example 파일이 모두 없습니다. 기본 환경 변수를 사용합니다.${NC}"
    fi
else
    echo -e "${GREEN}✅ .env 파일 확인 완료${NC}"
fi

# Clean 옵션 처리
if [[ "$CLEAN" = true ]]; then
    echo -e "${CYAN}ℹ️  기존 컨테이너 정리 중...${NC}"
    
    # 기존 컨테이너 중지 및 삭제
    docker-compose -f docker-compose.dev.yml down --remove-orphans
    
    echo -e "${GREEN}✅ 기존 컨테이너 정리 완료${NC}"
    
    # 기존 볼륨 삭제 (개발용 데이터)
    read -p "개발용 데이터 볼륨도 삭제하시겠습니까? (y/N) " DELETE_VOLUMES
    if [[ "$DELETE_VOLUMES" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⚠️  개발용 볼륨 삭제 중...${NC}"
        
        docker volume rm intellidoc_postgres_dev_data 2>/dev/null || true
        docker volume rm intellidoc_redis_dev_data 2>/dev/null || true
        docker volume rm intellidoc_node_modules_cache 2>/dev/null || true
        
        echo -e "${GREEN}✅ 개발용 볼륨 삭제 완료${NC}"
    fi
fi

# Rebuild 옵션 처리
if [[ "$REBUILD" = true ]]; then
    echo -e "${CYAN}ℹ️  이미지 리빌드 중...${NC}"
    
    # 개발용 이미지 리빌드
    docker-compose -f docker-compose.dev.yml build --no-cache
    
    echo -e "${GREEN}✅ 이미지 리빌드 완료${NC}"
fi

# 개발용 컨테이너 시작
echo -e "${CYAN}ℹ️  개발 환경 컨테이너 시작 중...${NC}"

if [[ "$TOOLS" = true ]]; then
    # 개발 도구 포함
    docker-compose -f docker-compose.dev.yml --profile tools up -d
else
    # 기본 서비스만
    docker-compose -f docker-compose.dev.yml up -d
fi

# 서비스 상태 확인
sleep 5
echo -e "${CYAN}ℹ️  실행 중인 서비스 확인...${NC}"
docker-compose -f docker-compose.dev.yml ps

# 접속 정보 출력
echo -e "${GREEN}\n✅ 개발 환경이 성공적으로 시작되었습니다!${NC}"
echo -e "${CYAN}===========================================${NC}"
echo -e "${CYAN}ℹ️  개발용 URL:${NC}"
echo -e "${CYAN}ℹ️  - 프론트엔드: http://localhost:3001${NC}"
echo -e "${CYAN}ℹ️  - 백엔드 API: http://localhost:8001${NC}"
echo -e "${CYAN}ℹ️  - API 문서: http://localhost:8001/docs${NC}"
echo -e "${CYAN}ℹ️  - 통합 접속: http://localhost:8080${NC}"

if [[ "$TOOLS" = true ]]; then
    echo -e "\n${CYAN}ℹ️  개발 도구:${NC}"
    echo -e "${CYAN}ℹ️  - Adminer (DB 관리): http://localhost:8082${NC}"
    echo -e "${CYAN}ℹ️  - Redis Commander: http://localhost:8083${NC}"
    echo -e "${CYAN}ℹ️  - Flower (Celery 모니터링): http://localhost:5556${NC}"
fi

echo -e "\n${CYAN}ℹ️  서비스 중지 명령어:${NC}"
echo -e "${CYAN}ℹ️  docker-compose -f docker-compose.dev.yml down${NC}"
echo -e "${CYAN}===========================================${NC}"

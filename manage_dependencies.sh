#!/bin/bash
# IntelliDoc 의존성 관리 스크립트 (Linux/macOS)
# 사용법: ./manage_dependencies.sh [--compile] [--sync] [--update] [--dev]

# 기본 옵션 설정
COMPILE=false
SYNC=false
UPDATE=false
DEV=false

# 인수 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --compile)
            COMPILE=true
            shift
            ;;
        --sync)
            SYNC=true
            shift
            ;;
        --update)
            UPDATE=true
            shift
            ;;
        --dev)
            DEV=true
            shift
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            echo "사용법: ./manage_dependencies.sh [--compile] [--sync] [--update] [--dev]"
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

# 가상 환경 활성화 확인
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  가상 환경이 활성화되지 않았습니다.${NC}"
    read -p "가상 환경을 활성화하시겠습니까? (y/N) " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        if [[ -f "./setup_venv.sh" ]]; then
            ./setup_venv.sh setup
            source ./intellidoc_venv/bin/activate
        else
            echo -e "${RED}❌ setup_venv.sh 스크립트를 찾을 수 없습니다.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  가상 환경 없이 진행합니다. 글로벌 환경을 수정할 수 있습니다.${NC}"
    fi
fi

# pip-tools 설치 확인
if ! pip show pip-tools &> /dev/null; then
    echo -e "${CYAN}ℹ️  pip-tools 설치 중...${NC}"
    pip install pip-tools
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ pip-tools 설치 실패${NC}"
        exit 1
    fi
fi

# 인자 기본값 처리
if [[ "$COMPILE" = false && "$SYNC" = false && "$UPDATE" = false ]]; then
    echo -e "${CYAN}ℹ️  기본 동작: Compile + Sync${NC}"
    COMPILE=true
    SYNC=true
fi

# 의존성 컴파일
if [[ "$COMPILE" = true ]]; then
    echo -e "${CYAN}ℹ️  의존성 파일 컴파일 중...${NC}"
    
    # 백엔드 의존성 컴파일
    echo -e "${CYAN}ℹ️  백엔드 의존성 컴파일 중...${NC}"
    pip-compile --verbose --output-file=backend/requirements.txt backend/requirements.in
    
    # 개발용 의존성 컴파일 (Dev 옵션이 활성화된 경우)
    if [[ "$DEV" = true ]]; then
        echo -e "${CYAN}ℹ️  개발용 의존성 컴파일 중...${NC}"
        pip-compile --verbose --output-file=requirements-dev.txt requirements-dev.in
    fi
    
    echo -e "${GREEN}✅ 의존성 컴파일 완료${NC}"
fi

# 의존성 업데이트
if [[ "$UPDATE" = true ]]; then
    echo -e "${CYAN}ℹ️  의존성 파일 업데이트 중...${NC}"
    
    # 백엔드 의존성 업데이트
    echo -e "${CYAN}ℹ️  백엔드 의존성 업데이트 중...${NC}"
    pip-compile --upgrade --output-file=backend/requirements.txt backend/requirements.in
    
    # 개발용 의존성 업데이트 (Dev 옵션이 활성화된 경우)
    if [[ "$DEV" = true ]]; then
        echo -e "${CYAN}ℹ️  개발용 의존성 업데이트 중...${NC}"
        pip-compile --upgrade --output-file=requirements-dev.txt requirements-dev.in
    fi
    
    echo -e "${GREEN}✅ 의존성 업데이트 완료${NC}"
fi

# 의존성 동기화
if [[ "$SYNC" = true ]]; then
    echo -e "${CYAN}ℹ️  의존성 설치/동기화 중...${NC}"
    
    # 백엔드 의존성 동기화
    echo -e "${CYAN}ℹ️  백엔드 의존성 설치 중...${NC}"
    pip-sync backend/requirements.txt
    
    # 개발용 의존성 설치 (Dev 옵션이 활성화된 경우)
    if [[ "$DEV" = true ]]; then
        echo -e "${CYAN}ℹ️  개발용 의존성 설치 중...${NC}"
        pip install -r requirements-dev.txt
    fi
    
    echo -e "${GREEN}✅ 의존성 설치/동기화 완료${NC}"
fi

# 완료 메시지
echo -e "${GREEN}\n✅ 의존성 관리 작업이 완료되었습니다.${NC}"
if [[ "$DEV" = true ]]; then
    echo -e "${CYAN}ℹ️  개발용 의존성이 포함되었습니다.${NC}"
else
    echo -e "${CYAN}ℹ️  기본 의존성만 처리되었습니다. 개발용 의존성을 포함하려면 --dev 옵션을 사용하세요.${NC}"
fi

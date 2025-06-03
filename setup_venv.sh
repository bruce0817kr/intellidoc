#!/bin/bash
# IntelliDoc 가상 환경 설정 스크립트 (Linux/macOS)
# 사용법: ./setup_venv.sh [setup|activate|deactivate|clean|reinstall|status] [--force] [--quiet]

set -e

# 기본 설정
ACTION="${1:-setup}"
FORCE=false
QUIET=false

# 인수 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        setup|activate|deactivate|clean|reinstall|status)
            ACTION="$1"
            shift
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            exit 1
            ;;
    esac
done

# 상수 정의
VENV_NAME="intellidoc_venv"
VENV_PATH="./$VENV_NAME"
REQUIREMENTS_FILE="./backend/requirements.txt"
REQUIREMENTS_DEV_FILE="./requirements-dev.txt"
PYTHON_MIN_VERSION="3.9"

# 색상 출력 함수
print_color() {
    local color=$1
    local message=$2
    if [[ $QUIET == false ]]; then
        case $color in
            "green") echo -e "\033[32m✅ $message\033[0m" ;;
            "cyan") echo -e "\033[36mℹ️  $message\033[0m" ;;
            "yellow") echo -e "\033[33m⚠️  $message\033[0m" ;;
            "red") echo -e "\033[31m❌ $message\033[0m" ;;
            *) echo "$message" ;;
        esac
    fi
}

print_success() {
    print_color "green" "$1"
}

print_info() {
    print_color "cyan" "$1"
}

print_warning() {
    print_color "yellow" "$1"
}

print_error() {
    print_color "red" "$1"
}

# Python 버전 확인 함수
check_python_version() {
    local python_cmd=""
    
    # Python 명령어 찾기
    if command -v python3 &> /dev/null; then
        python_cmd="python3"
    elif command -v python &> /dev/null; then
        python_cmd="python"
    else
        print_error "Python이 설치되지 않았습니다."
        return 1
    fi
    
    # 버전 확인
    local python_version=$($python_cmd -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    print_info "Python 버전: $python_version"
    
    # 최소 버전 확인
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
        return 0
    else
        print_error "Python $PYTHON_MIN_VERSION 이상이 필요합니다. 현재 버전: $python_version"
        return 1
    fi
}

# 가상 환경 존재 확인 함수
check_venv_exists() {
    [[ -d "$VENV_PATH" && -f "$VENV_PATH/bin/activate" ]]
}

# 가상 환경 활성화 상태 확인 함수
check_venv_active() {
    [[ -n "$VIRTUAL_ENV" && "$VIRTUAL_ENV" == *"$VENV_NAME" ]]
}

# 가상 환경 생성 함수
create_virtual_environment() {
    print_info "가상 환경 생성 중: $VENV_NAME"
    
    if check_venv_exists; then
        if [[ $FORCE == true ]]; then
            print_warning "기존 가상 환경을 삭제하고 새로 생성합니다."
            rm -rf "$VENV_PATH"
        else
            print_warning "가상 환경이 이미 존재합니다. --force 옵션을 사용하여 재생성하세요."
            return 1
        fi
    fi
    
    # Python 버전 확인
    if ! check_python_version; then
        return 1
    fi
    
    # 가상 환경 생성
    if command -v python3 &> /dev/null; then
        python3 -m venv "$VENV_PATH"
    else
        python -m venv "$VENV_PATH"
    fi
    
    if ! check_venv_exists; then
        print_error "가상 환경 생성에 실패했습니다."
        return 1
    fi
    
    print_success "가상 환경이 성공적으로 생성되었습니다: $VENV_PATH"
    
    # pip 업그레이드
    print_info "pip 업그레이드 중..."
    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip
    deactivate
    
    return 0
}

# 의존성 설치 함수
install_dependencies() {
    local install_dev=${1:-false}
    
    if ! check_venv_active; then
        print_error "가상 환경이 활성화되지 않았습니다."
        return 1
    fi
    
    # 기본 의존성 설치
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        print_info "기본 의존성 설치 중: $REQUIREMENTS_FILE"
        pip install -r "$REQUIREMENTS_FILE"
    else
        print_warning "requirements.txt 파일을 찾을 수 없습니다: $REQUIREMENTS_FILE"
    fi
    
    # 개발 의존성 설치
    if [[ $install_dev == true && -f "$REQUIREMENTS_DEV_FILE" ]]; then
        print_info "개발 의존성 설치 중: $REQUIREMENTS_DEV_FILE"
        pip install -r "$REQUIREMENTS_DEV_FILE"
    fi
    
    print_success "의존성 설치 완료"
    return 0
}

# 가상 환경 활성화 함수
activate_virtual_environment() {
    if ! check_venv_exists; then
        print_error "가상 환경이 존재하지 않습니다. 먼저 'setup' 명령을 실행하세요."
        return 1
    fi
    
    if check_venv_active; then
        print_info "가상 환경이 이미 활성화되어 있습니다."
        return 0
    fi
    
    print_info "가상 환경 활성화: $VENV_NAME"
    print_info "다음 명령을 실행하세요:"
    print_color "yellow" "  source ./$VENV_NAME/bin/activate"
    
    return 0
}

# 가상 환경 비활성화 함수
deactivate_virtual_environment() {
    if check_venv_active; then
        print_info "가상 환경 비활성화"
        print_info "다음 명령을 실행하세요:"
        print_color "yellow" "  deactivate"
    else
        print_info "가상 환경이 활성화되어 있지 않습니다."
    fi
    
    return 0
}

# 가상 환경 삭제 함수
remove_virtual_environment() {
    if check_venv_exists; then
        if [[ $FORCE == true ]]; then
            response="y"
        else
            read -p "가상 환경을 삭제하시겠습니까? (y/N): " response
        fi
        
        if [[ $response == "y" || $response == "Y" ]]; then
            print_info "가상 환경 삭제 중: $VENV_PATH"
            rm -rf "$VENV_PATH"
            print_success "가상 환경이 삭제되었습니다."
        else
            print_info "가상 환경 삭제가 취소되었습니다."
        fi
    else
        print_info "삭제할 가상 환경이 없습니다."
    fi
    
    return 0
}

# 상태 확인 함수
show_status() {
    print_info "=== IntelliDoc 가상 환경 상태 ==="
    
    # Python 정보
    if check_python_version; then
        print_success "Python 설치됨"
    else
        print_error "Python 설치되지 않음"
    fi
    
    # 가상 환경 정보
    if check_venv_exists; then
        print_success "가상 환경 존재함: $VENV_PATH"
        
        if check_venv_active; then
            print_success "가상 환경 활성화됨"
        else
            print_warning "가상 환경 비활성화됨"
        fi
        
        # 설치된 패키지 정보
        if [[ -f "$VENV_PATH/bin/pip" ]]; then
            local package_count=$("$VENV_PATH/bin/pip" list | wc -l)
            package_count=$((package_count - 2))
            print_info "설치된 패키지 수: $package_count"
        fi
    else
        print_error "가상 환경 존재하지 않음"
    fi
    
    # 의존성 파일 정보
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        print_success "기본 requirements.txt 존재함"
    else
        print_warning "기본 requirements.txt 없음"
    fi
    
    if [[ -f "$REQUIREMENTS_DEV_FILE" ]]; then
        print_success "개발 requirements-dev.txt 존재함"
    else
        print_warning "개발 requirements-dev.txt 없음"
    fi
    
    return 0
}

# 메인 실행 부분
main() {
    print_info "IntelliDoc 가상 환경 관리 스크립트"
    print_info "작업: $ACTION"
    
    case $ACTION in
        "setup")
            if create_virtual_environment; then
                print_info "가상 환경을 활성화하고 의존성을 설치합니다..."
                
                # 가상 환경 활성화하여 의존성 설치
                source "$VENV_PATH/bin/activate"
                install_dependencies true
                deactivate
                
                print_success "가상 환경 설정 완료!"
                print_info "가상 환경을 활성화하려면 다음 명령을 실행하세요:"
                print_color "yellow" "  ./setup_venv.sh activate"
            else
                exit 1
            fi
            ;;
        
        "activate")
            activate_virtual_environment
            ;;
        
        "deactivate")
            deactivate_virtual_environment
            ;;
        
        "clean")
            remove_virtual_environment
            ;;
        
        "reinstall")
            remove_virtual_environment
            if create_virtual_environment; then
                source "$VENV_PATH/bin/activate"
                install_dependencies true
                deactivate
            fi
            ;;
        
        "status")
            show_status
            ;;
        
        *)
            print_error "알 수 없는 작업: $ACTION"
            print_info "사용 가능한 작업: setup, activate, deactivate, clean, reinstall, status"
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"

# IntelliDoc 개발 환경 시작 스크립트 (PowerShell)
# 사용법: .\start_dev.ps1 [-Clean] [-Rebuild] [-Tools]

param(
    [switch]$Clean,      # 기존 컨테이너 및 볼륨 정리
    [switch]$Rebuild,    # 이미지 리빌드
    [switch]$Tools       # 개발 도구 컨테이너 실행
)

# 스크립트 설정
$ErrorActionPreference = "Stop"

# 색상 출력 함수
function Write-ColorOutput($Message, $Color = "White") {
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success($Message) {
    Write-ColorOutput "✅ $Message" "Green"
}

function Write-Info($Message) {
    Write-ColorOutput "ℹ️  $Message" "Cyan"
}

function Write-Warning($Message) {
    Write-ColorOutput "⚠️  $Message" "Yellow"
}

function Write-Error($Message) {
    Write-ColorOutput "❌ $Message" "Red"
}

# 로고 출력
Write-Host "
 _____       _       _ _ _ _____             
|_   _|     | |     | | (_)  __ \            
  | |  _ __ | |_ ___| | |_| |  | | ___   ___ 
  | | | '_ \| __/ _ \ | | | |  | |/ _ \ / __|
 _| |_| | | | ||  __/ | | | |__| | (_) | (__ 
|_____|_| |_|\__\___|_|_|_|_____/ \___/ \___|
                                             
" -ForegroundColor Cyan

Write-Info "IntelliDoc 개발 환경 시작 스크립트"
Write-Info "=========================================="
Write-Info "작업 시간: $(Get-Date)"
Write-Info "옵션: Clean=$Clean, Rebuild=$Rebuild, Tools=$Tools"
Write-Info "=========================================="

try {
    # Docker 확인
    Write-Info "Docker 환경 확인 중..."
    
    try {
        $DockerVersion = docker --version
        Write-Info "Docker 버전: $DockerVersion"
    } catch {
        Write-Error "Docker가 설치되지 않았거나 실행되지 않고 있습니다."
        exit 1
    }
    
    try {
        $ComposeVersion = docker-compose --version
        Write-Info "Docker Compose 버전: $ComposeVersion"
    } catch {
        Write-Error "Docker Compose가 설치되지 않았습니다."
        exit 1
    }
    
    # 포트 매니저 실행
    Write-Info "포트 매니저 실행 중..."
    
    try {
        python port_manager.py
        Write-Success "포트 설정 완료"
    } catch {
        Write-Warning "포트 매니저 오류: $_"
        Write-Info "포트 충돌이 발생할 수 있습니다."
    }
    
    # 환경 변수 파일 확인
    Write-Info "환경 변수 파일 확인 중..."
    
    if (!(Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Write-Warning ".env 파일이 없습니다. .env.example을 복사합니다."
            Copy-Item ".env.example" ".env"
            Write-Warning ".env 파일을 편집하여 실제 API 키를 설정하세요."
        } else {
            Write-Warning ".env 및 .env.example 파일이 모두 없습니다. 기본 환경 변수를 사용합니다."
        }
    } else {
        Write-Success ".env 파일 확인 완료"
    }
    
    # Clean 옵션 처리
    if ($Clean) {
        Write-Info "기존 컨테이너 정리 중..."
        
        # 기존 컨테이너 중지 및 삭제
        docker-compose -f docker-compose.dev.yml down --remove-orphans
        
        Write-Success "기존 컨테이너 정리 완료"
        
        # 기존 볼륨 삭제 (개발용 데이터)
        $DeleteVolumes = Read-Host "개발용 데이터 볼륨도 삭제하시겠습니까? (y/N)"
        if ($DeleteVolumes -eq "y" -or $DeleteVolumes -eq "Y") {
            Write-Warning "개발용 볼륨 삭제 중..."
            
            docker volume rm intellidoc_postgres_dev_data 2>$null
            docker volume rm intellidoc_redis_dev_data 2>$null
            docker volume rm intellidoc_node_modules_cache 2>$null
            
            Write-Success "개발용 볼륨 삭제 완료"
        }
    }
    
    # Rebuild 옵션 처리
    if ($Rebuild) {
        Write-Info "이미지 리빌드 중..."
        
        # 개발용 이미지 리빌드
        docker-compose -f docker-compose.dev.yml build --no-cache
        
        Write-Success "이미지 리빌드 완료"
    }
    
    # 개발용 컨테이너 시작
    Write-Info "개발 환경 컨테이너 시작 중..."
    
    if ($Tools) {
        # 개발 도구 포함
        docker-compose -f docker-compose.dev.yml --profile tools up -d
    } else {
        # 기본 서비스만
        docker-compose -f docker-compose.dev.yml up -d
    }
    
    # 서비스 상태 확인
    Start-Sleep -Seconds 5
    Write-Info "실행 중인 서비스 확인..."
    docker-compose -f docker-compose.dev.yml ps
    
    # 접속 정보 출력
    Write-Success "`n개발 환경이 성공적으로 시작되었습니다!"
    Write-Info "=========================================="
    Write-Info "개발용 URL:"
    Write-Info "- 프론트엔드: http://localhost:3001"
    Write-Info "- 백엔드 API: http://localhost:8001"
    Write-Info "- API 문서: http://localhost:8001/docs"
    Write-Info "- 통합 접속: http://localhost:8080"
    
    if ($Tools) {
        Write-Info "`n개발 도구:"
        Write-Info "- Adminer (DB 관리): http://localhost:8082"
        Write-Info "- Redis Commander: http://localhost:8083"
        Write-Info "- Flower (Celery 모니터링): http://localhost:5556"
    }
    
    Write-Info "`n서비스 중지 명령어:"
    Write-Info "docker-compose -f docker-compose.dev.yml down"
    Write-Info "=========================================="
    
} catch {
    Write-Error "개발 환경 시작 중 오류가 발생했습니다: $_"
    exit 1
}

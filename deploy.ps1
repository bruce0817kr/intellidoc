# IntelliDoc 원클릭 배포 스크립트 (PowerShell)
# use MCP: context7, Github, Sequential Thinking, Task Manager, Memory Bank

param(
    [string]$Environment = "development",
    [switch]$SkipPortCheck = $false,
    [switch]$CleanStart = $false
)

Write-Host "🚀 IntelliDoc 자동 배포 시작" -ForegroundColor Green
Write-Host "환경: $Environment" -ForegroundColor Yellow
Write-Host "=" * 50

# 1. 포트 충돌 해결 (선택적)
if (-not $SkipPortCheck) {
    Write-Host "🔧 1단계: 포트 충돌 해결 중..." -ForegroundColor Cyan
    
    # Python 가상환경 설정
    if (-not (Test-Path "venv")) {
        Write-Host "Python 가상환경 생성 중..."
        python -m venv venv
    }
    
    & "venv\Scripts\activate.ps1"
    pip install -r requirements-dev.txt -q
    
    # 포트 매니저 실행
    python port_manager.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 포트 매니저 실행 실패!" -ForegroundColor Red
        exit 1
    }
}

# 2. 기존 컨테이너 정리 (선택적)
if ($CleanStart) {
    Write-Host "🧹 2단계: 기존 컨테이너 정리 중..." -ForegroundColor Cyan
    docker-compose down -v
}

# 3. Docker 이미지 빌드 (필요 시)
Write-Host "🔨 3단계: Docker 이미지 확인 및 빌드..." -ForegroundColor Cyan
if (-not (docker images -q intellidoc-backend:latest)) {
    Write-Host "백엔드 이미지 빌드 중..."
    docker build -t intellidoc-backend:latest ./backend/
}

if (-not (docker images -q intellidoc-frontend:latest)) {
    Write-Host "프론트엔드 이미지 빌드 중..."
    docker build -t intellidoc-frontend:latest ./frontend/
}

# 4. 서비스 시작
Write-Host "🚀 4단계: 서비스 시작 중..." -ForegroundColor Cyan
docker-compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 배포 성공!" -ForegroundColor Green
    
    # 포트 정보 표시
    if (Test-Path "allocated_ports.json") {
        $ports = Get-Content "allocated_ports.json" | ConvertFrom-Json
        Write-Host "`n🌐 서비스 접속 정보:" -ForegroundColor Yellow
        Write-Host "웹 애플리케이션: http://localhost:$($ports.frontend)"
        Write-Host "API 서버: http://localhost:$($ports.backend)"
        Write-Host "API 문서: http://localhost:$($ports.backend)/docs"
    }
    
    # 서비스 상태 확인
    Write-Host "`n📊 컨테이너 상태:" -ForegroundColor Yellow
    docker-compose ps
    
} else {
    Write-Host "❌ 배포 실패!" -ForegroundColor Red
    Write-Host "로그 확인: docker-compose logs" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n🎉 IntelliDoc 배포 완료!" -ForegroundColor Green
Write-Host "문제 발생 시: deploy.ps1 -CleanStart 로 완전 재배포하세요" -ForegroundColor Gray

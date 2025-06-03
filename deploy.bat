@echo off
REM IntelliDoc 원클릭 배포 스크립트 (Batch)
REM use MCP: context7, Github, Sequential Thinking, Task Manager, Memory Bank

setlocal enabledelayedexpansion

set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="" set ENVIRONMENT=development

set SKIP_PORT_CHECK=%2
set CLEAN_START=%3

echo 🚀 IntelliDoc 자동 배포 시작
echo 환경: %ENVIRONMENT%
echo ==================================================

REM 1. 포트 충돌 해결
if not "%SKIP_PORT_CHECK%"=="--skip-port" (
    echo 🔧 1단계: 포트 충돌 해결 중...
    
    if not exist "venv" (
        echo Python 가상환경 생성 중...
        python -m venv venv
    )
    
    call venv\Scripts\activate
    pip install -r requirements-dev.txt >nul 2>&1
    
    python port_manager.py
    if errorlevel 1 (
        echo ❌ 포트 매니저 실행 실패!
        exit /b 1
    )
)

REM 2. 기존 컨테이너 정리 (선택적)
if "%CLEAN_START%"=="--clean" (
    echo 🧹 2단계: 기존 컨테이너 정리 중...
    docker-compose down -v
)

REM 3. Docker 이미지 빌드 확인
echo 🔨 3단계: Docker 이미지 확인 및 빌드...
for /f %%i in ('docker images -q intellidoc-backend:latest 2^>nul') do set BACKEND_EXISTS=%%i
if "%BACKEND_EXISTS%"=="" (
    echo 백엔드 이미지 빌드 중...
    docker build -t intellidoc-backend:latest ./backend/
)

for /f %%i in ('docker images -q intellidoc-frontend:latest 2^>nul') do set FRONTEND_EXISTS=%%i
if "%FRONTEND_EXISTS%"=="" (
    echo 프론트엔드 이미지 빌드 중...
    docker build -t intellidoc-frontend:latest ./frontend/
)

REM 4. 서비스 시작
echo 🚀 4단계: 서비스 시작 중...
docker-compose up -d

if errorlevel 0 (
    echo ✅ 배포 성공!
    
    REM 포트 정보 표시
    if exist "allocated_ports.json" (
        echo.
        echo 🌐 서비스 접속 정보:
        echo 자세한 포트 정보는 allocated_ports.json을 확인하세요
    )
    
    echo.
    echo 📊 컨테이너 상태:
    docker-compose ps
    
) else (
    echo ❌ 배포 실패!
    echo 로그 확인: docker-compose logs
    exit /b 1
)

echo.
echo 🎉 IntelliDoc 배포 완료!
echo 문제 발생 시: deploy.bat %ENVIRONMENT% --skip-port --clean 로 완전 재배포하세요

pause

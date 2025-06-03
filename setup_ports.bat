@echo off
REM IntelliDoc 포트 매니저 실행 스크립트 (Windows)
REM use MCP: context7, Github, Sequential Thinking, Task Manager, Memory Bank

echo ===============================================
echo  IntelliDoc 포트 자동 할당 및 충돌 해결
echo ===============================================

REM Python 가상환경 확인 및 생성
if not exist "venv" (
    echo 🔧 Python 가상환경 생성 중...
    python -m venv venv
)

REM 가상환경 활성화
echo 🔧 가상환경 활성화 중...
call venv\Scripts\activate

REM 개발 도구 설치
echo 📦 개발 도구 설치 중...
pip install -r requirements-dev.txt

REM 포트 매니저 실행
echo 🚀 포트 매니저 실행 중...
python port_manager.py

echo.
echo ✅ 포트 할당이 완료되었습니다!
echo 이제 'docker-compose up -d' 명령으로 서비스를 시작하세요.

pause

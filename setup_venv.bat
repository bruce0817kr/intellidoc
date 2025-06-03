@echo off
REM IntelliDoc 가상 환경 설정 스크립트 (Windows Batch)
REM 사용법: setup_venv.bat [setup|activate|deactivate|clean|reinstall|status] [/force] [/quiet]

setlocal enabledelayedexpansion

REM 기본 설정
set "ACTION=%~1"
set "FORCE=false"
set "QUIET=false"

REM 기본 액션 설정
if "%ACTION%"=="" set "ACTION=setup"

REM 인수 파싱
:parse_args
if "%~2"=="" goto :args_done
if /i "%~2"=="/force" (
    set "FORCE=true"
    shift /2
    goto :parse_args
)
if /i "%~2"=="/quiet" (
    set "QUIET=true"
    shift /2
    goto :parse_args
)
shift /2
goto :parse_args

:args_done

REM 상수 정의
set "VENV_NAME=intellidoc_venv"
set "VENV_PATH=.\%VENV_NAME%"
set "REQUIREMENTS_FILE=.\backend\requirements.txt"
set "REQUIREMENTS_DEV_FILE=.\requirements-dev.txt"

REM 색상 출력 함수 (간단 버전)
if "%QUIET%"=="false" (
    echo [INFO] IntelliDoc 가상 환경 관리 스크립트
    echo [INFO] 작업: %ACTION%
)

REM Python 버전 확인 함수
:check_python
py --version >nul 2>&1
if %errorlevel%==0 (
    if "%QUIET%"=="false" echo [SUCCESS] Python 설치 확인됨
    goto :python_ok
)

python --version >nul 2>&1
if %errorlevel%==0 (
    if "%QUIET%"=="false" echo [SUCCESS] Python 설치 확인됨
    goto :python_ok
)

echo [ERROR] Python이 설치되지 않았거나 PATH에 없습니다.
exit /b 1

:python_ok

REM 가상 환경 존재 확인
:check_venv_exists
if exist "%VENV_PATH%\Scripts\activate.bat" (
    exit /b 0
) else (
    exit /b 1
)

REM 가상 환경 생성
:create_venv
if "%QUIET%"=="false" echo [INFO] 가상 환경 생성 중: %VENV_NAME%

call :check_venv_exists
if %errorlevel%==0 (
    if "%FORCE%"=="true" (
        if "%QUIET%"=="false" echo [WARNING] 기존 가상 환경을 삭제하고 새로 생성합니다.
        rmdir /s /q "%VENV_PATH%" 2>nul
    ) else (
        echo [WARNING] 가상 환경이 이미 존재합니다. /force 옵션을 사용하여 재생성하세요.
        exit /b 1
    )
)

REM 가상 환경 생성
py -m venv "%VENV_PATH%" 2>nul
if %errorlevel% neq 0 (
    python -m venv "%VENV_PATH%"
    if %errorlevel% neq 0 (
        echo [ERROR] 가상 환경 생성에 실패했습니다.
        exit /b 1
    )
)

call :check_venv_exists
if %errorlevel% neq 0 (
    echo [ERROR] 가상 환경 생성에 실패했습니다.
    exit /b 1
)

if "%QUIET%"=="false" echo [SUCCESS] 가상 환경이 성공적으로 생성되었습니다: %VENV_PATH%

REM pip 업그레이드
if "%QUIET%"=="false" echo [INFO] pip 업그레이드 중...
"%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1

exit /b 0

REM 의존성 설치
:install_deps
set "INSTALL_DEV=%~1"

REM 기본 의존성 설치
if exist "%REQUIREMENTS_FILE%" (
    if "%QUIET%"=="false" echo [INFO] 기본 의존성 설치 중: %REQUIREMENTS_FILE%
    "%VENV_PATH%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS_FILE%"
    if %errorlevel% neq 0 (
        echo [ERROR] 기본 의존성 설치 실패
        exit /b 1
    )
) else (
    echo [WARNING] requirements.txt 파일을 찾을 수 없습니다: %REQUIREMENTS_FILE%
)

REM 개발 의존성 설치
if "%INSTALL_DEV%"=="true" (
    if exist "%REQUIREMENTS_DEV_FILE%" (
        if "%QUIET%"=="false" echo [INFO] 개발 의존성 설치 중: %REQUIREMENTS_DEV_FILE%
        "%VENV_PATH%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS_DEV_FILE%"
        if %errorlevel% neq 0 (
            echo [ERROR] 개발 의존성 설치 실패
            exit /b 1
        )
    )
)

if "%QUIET%"=="false" echo [SUCCESS] 의존성 설치 완료
exit /b 0

REM 상태 확인
:show_status
echo [INFO] === IntelliDoc 가상 환경 상태 ===

call :check_python
if %errorlevel%==0 (
    echo [SUCCESS] Python 설치됨
) else (
    echo [ERROR] Python 설치되지 않음
)

call :check_venv_exists
if %errorlevel%==0 (
    echo [SUCCESS] 가상 환경 존재함: %VENV_PATH%
    
    if defined VIRTUAL_ENV (
        echo [SUCCESS] 가상 환경 활성화됨
    ) else (
        echo [WARNING] 가상 환경 비활성화됨
    )
    
    REM 설치된 패키지 수 확인
    for /f %%i in ('"%VENV_PATH%\Scripts\python.exe" -m pip list 2^>nul ^| find /c /v ""') do set "PACKAGE_COUNT=%%i"
    set /a PACKAGE_COUNT-=2
    echo [INFO] 설치된 패키지 수: !PACKAGE_COUNT!
) else (
    echo [ERROR] 가상 환경 존재하지 않음
)

if exist "%REQUIREMENTS_FILE%" (
    echo [SUCCESS] 기본 requirements.txt 존재함
) else (
    echo [WARNING] 기본 requirements.txt 없음
)

if exist "%REQUIREMENTS_DEV_FILE%" (
    echo [SUCCESS] 개발 requirements-dev.txt 존재함
) else (
    echo [WARNING] 개발 requirements-dev.txt 없음
)

exit /b 0

REM 메인 로직
if /i "%ACTION%"=="setup" (
    call :create_venv
    if %errorlevel%==0 (
        if "%QUIET%"=="false" echo [INFO] 가상 환경을 활성화하고 의존성을 설치합니다...
        call :install_deps true
        if %errorlevel%==0 (
            echo [SUCCESS] 가상 환경 설정 완료!
            echo [INFO] 가상 환경을 활성화하려면 다음 명령을 실행하세요:
            echo   %VENV_PATH%\Scripts\activate.bat
        ) else (
            echo [ERROR] 의존성 설치에 실패했습니다.
            exit /b 1
        )
    ) else (
        exit /b 1
    )
) else if /i "%ACTION%"=="activate" (
    call :check_venv_exists
    if %errorlevel%==0 (
        echo [INFO] 가상 환경 활성화: %VENV_NAME%
        echo [INFO] 다음 명령을 실행하세요:
        echo   %VENV_PATH%\Scripts\activate.bat
    ) else (
        echo [ERROR] 가상 환경이 존재하지 않습니다. 먼저 'setup' 명령을 실행하세요.
        exit /b 1
    )
) else if /i "%ACTION%"=="deactivate" (
    if defined VIRTUAL_ENV (
        echo [INFO] 가상 환경 비활성화
        echo [INFO] 다음 명령을 실행하세요:
        echo   deactivate
    ) else (
        echo [INFO] 가상 환경이 활성화되어 있지 않습니다.
    )
) else if /i "%ACTION%"=="clean" (
    call :check_venv_exists
    if %errorlevel%==0 (
        if "%FORCE%"=="true" (
            set "response=y"
        ) else (
            set /p "response=가상 환경을 삭제하시겠습니까? (y/N): "
        )
        
        if /i "!response!"=="y" (
            echo [INFO] 가상 환경 삭제 중: %VENV_PATH%
            rmdir /s /q "%VENV_PATH%"
            echo [SUCCESS] 가상 환경이 삭제되었습니다.
        ) else (
            echo [INFO] 가상 환경 삭제가 취소되었습니다.
        )
    ) else (
        echo [INFO] 삭제할 가상 환경이 없습니다.
    )
) else if /i "%ACTION%"=="reinstall" (
    rmdir /s /q "%VENV_PATH%" 2>nul
    call :create_venv
    if %errorlevel%==0 (
        call :install_deps true
    )
) else if /i "%ACTION%"=="status" (
    call :show_status
) else (
    echo [ERROR] 알 수 없는 작업: %ACTION%
    echo [INFO] 사용 가능한 작업: setup, activate, deactivate, clean, reinstall, status
    exit /b 1
)

exit /b 0

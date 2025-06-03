# IntelliDoc 가상 환경 설정 스크립트 (PowerShell)
# 사용법: .\setup_venv.ps1 [-Action <setup|activate|deactivate|clean|reinstall>] [-Force]

param(
    [ValidateSet("setup", "activate", "deactivate", "clean", "reinstall", "status")]
    [string]$Action = "setup",
    [switch]$Force,
    [switch]$Quiet
)

# 스크립트 설정
$ErrorActionPreference = "Stop"
$ProgressPreference = if ($Quiet) { "SilentlyContinue" } else { "Continue" }

# 상수 정의
$VENV_NAME = "intellidoc_venv"
$VENV_PATH = ".\$VENV_NAME"
$REQUIREMENTS_FILE = ".\backend\requirements.txt"
$REQUIREMENTS_DEV_FILE = ".\requirements-dev.txt"
$PYTHON_MIN_VERSION = [version]"3.9.0"

# 색상 출력 함수
function Write-ColorOutput($Message, $Color = "White") {
    if (!$Quiet) {
        Write-Host $Message -ForegroundColor $Color
    }
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

# Python 버전 확인 함수
function Test-PythonVersion {
    try {
        $PythonVersion = py -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        if (!$PythonVersion) {
            $PythonVersion = python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        }
        
        if ($PythonVersion) {
            $Version = [version]$PythonVersion
            Write-Info "Python 버전: $PythonVersion"
            
            if ($Version -ge $PYTHON_MIN_VERSION) {
                return $true
            } else {
                Write-Error "Python $PYTHON_MIN_VERSION 이상이 필요합니다. 현재 버전: $PythonVersion"
                return $false
            }
        } else {
            Write-Error "Python이 설치되지 않았거나 PATH에 없습니다."
            return $false
        }
    } catch {
        Write-Error "Python 버전 확인 실패: $($_.Exception.Message)"
        return $false
    }
}

# 가상 환경 존재 확인 함수
function Test-VenvExists {
    return (Test-Path $VENV_PATH) -and (Test-Path "$VENV_PATH\Scripts\activate.ps1")
}

# 가상 환경 활성화 상태 확인 함수
function Test-VenvActive {
    return $env:VIRTUAL_ENV -and $env:VIRTUAL_ENV.EndsWith($VENV_NAME)
}

# 가상 환경 생성 함수
function New-VirtualEnvironment {
    Write-Info "가상 환경 생성 중: $VENV_NAME"
    
    if (Test-VenvExists) {
        if ($Force) {
            Write-Warning "기존 가상 환경을 삭제하고 새로 생성합니다."
            Remove-Item -Path $VENV_PATH -Recurse -Force
        } else {
            Write-Warning "가상 환경이 이미 존재합니다. -Force 옵션을 사용하여 재생성하세요."
            return $false
        }
    }
    
    try {
        # Python 버전 확인
        if (!(Test-PythonVersion)) {
            return $false
        }
        
        # 가상 환경 생성
        py -m venv $VENV_PATH 2>$null
        if (!$?) {
            python -m venv $VENV_PATH
        }
        
        if (!(Test-VenvExists)) {
            Write-Error "가상 환경 생성에 실패했습니다."
            return $false
        }
        
        Write-Success "가상 환경이 성공적으로 생성되었습니다: $VENV_PATH"
        
        # pip 업그레이드
        Write-Info "pip 업그레이드 중..."
        & "$VENV_PATH\Scripts\python.exe" -m pip install --upgrade pip
        
        return $true
        
    } catch {
        Write-Error "가상 환경 생성 실패: $($_.Exception.Message)"
        return $false
    }
}

# 의존성 설치 함수
function Install-Dependencies {
    param([switch]$DevDependencies)
    
    if (!(Test-VenvActive)) {
        Write-Error "가상 환경이 활성화되지 않았습니다."
        return $false
    }
    
    try {
        # 기본 의존성 설치
        if (Test-Path $REQUIREMENTS_FILE) {
            Write-Info "기본 의존성 설치 중: $REQUIREMENTS_FILE"
            & "$VENV_PATH\Scripts\python.exe" -m pip install -r $REQUIREMENTS_FILE
            
            if (!$?) {
                Write-Error "기본 의존성 설치 실패"
                return $false
            }
        } else {
            Write-Warning "requirements.txt 파일을 찾을 수 없습니다: $REQUIREMENTS_FILE"
        }
        
        # 개발 의존성 설치
        if ($DevDependencies -and (Test-Path $REQUIREMENTS_DEV_FILE)) {
            Write-Info "개발 의존성 설치 중: $REQUIREMENTS_DEV_FILE"
            & "$VENV_PATH\Scripts\python.exe" -m pip install -r $REQUIREMENTS_DEV_FILE
            
            if (!$?) {
                Write-Error "개발 의존성 설치 실패"
                return $false
            }
        }
        
        Write-Success "의존성 설치 완료"
        return $true
        
    } catch {
        Write-Error "의존성 설치 실패: $($_.Exception.Message)"
        return $false
    }
}

# 가상 환경 활성화 함수
function Enable-VirtualEnvironment {
    if (!(Test-VenvExists)) {
        Write-Error "가상 환경이 존재하지 않습니다. 먼저 'setup' 명령을 실행하세요."
        return $false
    }
    
    if (Test-VenvActive) {
        Write-Info "가상 환경이 이미 활성화되어 있습니다."
        return $true
    }
    
    Write-Info "가상 환경 활성화: $VENV_NAME"
    Write-Info "다음 명령을 실행하세요:"
    Write-ColorOutput "  . .\$VENV_NAME\Scripts\Activate.ps1" "Yellow"
    Write-Info "또는 CMD에서:"
    Write-ColorOutput "  .\$VENV_NAME\Scripts\activate.bat" "Yellow"
    
    return $true
}

# 가상 환경 비활성화 함수
function Disable-VirtualEnvironment {
    if (Test-VenvActive) {
        Write-Info "가상 환경 비활성화"
        Write-Info "다음 명령을 실행하세요:"
        Write-ColorOutput "  deactivate" "Yellow"
    } else {
        Write-Info "가상 환경이 활성화되어 있지 않습니다."
    }
    
    return $true
}

# 가상 환경 삭제 함수
function Remove-VirtualEnvironment {
    if (Test-VenvExists) {
        if ($Force -or (Read-Host "가상 환경을 삭제하시겠습니까? (y/N)") -eq "y") {
            Write-Info "가상 환경 삭제 중: $VENV_PATH"
            Remove-Item -Path $VENV_PATH -Recurse -Force
            Write-Success "가상 환경이 삭제되었습니다."
        } else {
            Write-Info "가상 환경 삭제가 취소되었습니다."
        }
    } else {
        Write-Info "삭제할 가상 환경이 없습니다."
    }
    
    return $true
}

# 상태 확인 함수
function Show-Status {
    Write-Info "=== IntelliDoc 가상 환경 상태 ==="
    
    # Python 정보
    if (Test-PythonVersion) {
        Write-Success "Python 설치됨"
    } else {
        Write-Error "Python 설치되지 않음"
    }
    
    # 가상 환경 정보
    if (Test-VenvExists) {
        Write-Success "가상 환경 존재함: $VENV_PATH"
        
        if (Test-VenvActive) {
            Write-Success "가상 환경 활성화됨"
        } else {
            Write-Warning "가상 환경 비활성화됨"
        }
        
        # 설치된 패키지 정보
        try {
            $PackageCount = (& "$VENV_PATH\Scripts\python.exe" -m pip list | Measure-Object -Line).Lines - 2
            Write-Info "설치된 패키지 수: $PackageCount"
        } catch {
            Write-Warning "패키지 정보를 가져올 수 없습니다."
        }
    } else {
        Write-Error "가상 환경 존재하지 않음"
    }
    
    # 의존성 파일 정보
    if (Test-Path $REQUIREMENTS_FILE) {
        Write-Success "기본 requirements.txt 존재함"
    } else {
        Write-Warning "기본 requirements.txt 없음"
    }
    
    if (Test-Path $REQUIREMENTS_DEV_FILE) {
        Write-Success "개발 requirements-dev.txt 존재함"
    } else {
        Write-Warning "개발 requirements-dev.txt 없음"
    }
    
    return $true
}

# 메인 실행 부분
try {
    Write-Info "IntelliDoc 가상 환경 관리 스크립트"
    Write-Info "작업: $Action"
    
    switch ($Action) {
        "setup" {
            if (New-VirtualEnvironment) {
                Write-Info "가상 환경을 활성화하고 의존성을 설치합니다..."
                
                # 임시로 가상 환경을 활성화하여 의존성 설치
                $env:VIRTUAL_ENV = (Resolve-Path $VENV_PATH).Path
                $env:PATH = "$VENV_PATH\Scripts;$env:PATH"
                
                if (Install-Dependencies -DevDependencies) {
                    Write-Success "가상 환경 설정 완료!"
                    Write-Info "가상 환경을 활성화하려면 다음 명령을 실행하세요:"
                    Write-ColorOutput "  .\setup_venv.ps1 -Action activate" "Yellow"
                } else {
                    Write-Error "의존성 설치에 실패했습니다."
                    exit 1
                }
            } else {
                exit 1
            }
        }
        
        "activate" {
            Enable-VirtualEnvironment
        }
        
        "deactivate" {
            Disable-VirtualEnvironment
        }
        
        "clean" {
            Remove-VirtualEnvironment
        }
        
        "reinstall" {
            Remove-VirtualEnvironment
            if (New-VirtualEnvironment) {
                $env:VIRTUAL_ENV = (Resolve-Path $VENV_PATH).Path
                $env:PATH = "$VENV_PATH\Scripts;$env:PATH"
                Install-Dependencies -DevDependencies
            }
        }
        
        "status" {
            Show-Status
        }
        
        default {
            Write-Error "알 수 없는 작업: $Action"
            Write-Info "사용 가능한 작업: setup, activate, deactivate, clean, reinstall, status"
            exit 1
        }
    }
    
} catch {
    Write-Error "스크립트 실행 중 오류가 발생했습니다: $($_.Exception.Message)"
    exit 1
}

# IntelliDoc 의존성 관리 스크립트 (PowerShell)
# 사용법: .\\manage_dependencies.ps1 [-Compile] [-Sync] [-Update] [-Dev]

[CmdletBinding()]
param (
    [switch]$Compile,  # 의존성 파일을 컴파일합니다. (기본값: $true, 다른 작업이 지정되지 않은 경우)
    [switch]$Sync,     # 컴파일된 의존성을 가상 환경에 설치/동기화합니다. (기본값: $true, 다른 작업이 지정되지 않은 경우)
    [switch]$Update,   # .in 파일 기준으로 의존성을 최신 버전으로 업데이트하여 컴파일합니다.
    [switch]$Dev       # 개발용 의존성 파일(requirements-dev.in, requirements-dev.txt)을 함께 처리합니다.
)

# 스크립트 시작 부분에 추가하여 현재 작업 디렉토리를 스크립트 위치로 변경
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath
Set-Location $ScriptDirectory

# 색상 출력 함수
function Write-ColorOutput($Message, $Color = "White", $NewLine = $true) {
    if ($NewLine) {
        Write-Host $Message -ForegroundColor $Color
    } else {
        Write-Host $Message -ForegroundColor $Color -NoNewline
    }
}

function Write-Success($Message) { Write-ColorOutput "✅ $Message" "Green" }
function Write-Info($Message) { Write-ColorOutput "ℹ️  $Message" "Cyan" }
function Write-Warning($Message) { Write-ColorOutput "⚠️  $Message" "Yellow" }
function Write-Error($Message) { Write-ColorOutput "❌ $Message" "Red" }

# 가상 환경 경로
$venvPath = ".\\intellidoc_venv"
$venvActivateScript = Join-Path $venvPath "Scripts\\Activate.ps1"

# 가상 환경 활성화 확인 및 시도
if (-not $env:VIRTUAL_ENV) {
    Write-Warning "가상 환경이 활성화되지 않았습니다."
    $answer = Read-Host "가상 환경을 설정하고 활성화하시겠습니까? (y/N)"
    if ($answer -match '^[Yy]$') { # 수정된 부분: 정규식 따옴표 처리 변경
        if (Test-Path ".\\setup_venv.ps1") {
            try {
                Write-Info "setup_venv.ps1 실행하여 가상 환경 설정..."
                & .\\setup_venv.ps1 -Action Setup 
                if (Test-Path $venvActivateScript) {
                    Write-Info "가상 환경 활성화 시도: $venvActivateScript"
                    . $venvActivateScript
                    if ($env:VIRTUAL_ENV) {
                        Write-Success "가상 환경이 활성화되었습니다: $($env:VIRTUAL_ENV)"
                    } else {
                        Write-Error "가상 환경 활성화에 실패했습니다. 스크립트를 수동으로 실행해 주세요: $venvActivateScript"
                        exit 1
                    }
                } else {
                    Write-Error "$venvActivateScript 를 찾을 수 없습니다. 가상 환경 설정이 올바르게 되었는지 확인하세요."
                    exit 1
                }
            } catch {
                Write-Error "setup_venv.ps1 실행 중 오류 발생 또는 가상 환경 활성화 실패: $($_.Exception.Message)"
                exit 1
            }
        } else {
            Write-Error ".\\setup_venv.ps1 스크립트를 찾을 수 없습니다."
            exit 1
        }
    } else {
        Write-Warning "가상 환경 없이 진행합니다. 이 경우 글로벌 Python 환경에 패키지가 설치될 수 있습니다."
    }
} else {
    Write-Success "가상 환경이 이미 활성화되어 있습니다: $($env:VIRTUAL_ENV)"
}

# pip-tools 설치 확인
try {
    $pipToolsInstalled = pip show pip-tools 2>$null
} catch {
    $pipToolsInstalled = $null
}

if (-not $pipToolsInstalled) {
    Write-Info "pip-tools 설치 중..."
    try {
        pip install pip-tools
        Write-Success "pip-tools 설치 완료."
    } catch {
        Write-Error "pip-tools 설치 실패: $($_.Exception.Message)"
        exit 1
    }
}

# 인자 기본값 처리: 아무런 작업 플래그가 없으면 Compile과 Sync를 수행
if (-not ($Compile.IsPresent -or $Sync.IsPresent -or $Update.IsPresent)) {
    Write-Info "명시된 작업이 없어 기본 동작으로 Compile 및 Sync를 수행합니다."
    $Compile = $true
    $Sync = $true
}

# 의존성 파일 경로
$backendReqIn = "backend\\requirements.in"
$backendReqTxt = "backend\\requirements.txt"
$devReqIn = "requirements-dev.in"
$devReqTxt = "requirements-dev.txt"

# 의존성 컴파일
if ($Compile.IsPresent -or $Update.IsPresent) {
    if ($Update.IsPresent) {
        Write-Info "의존성 파일 업데이트 및 컴파일 중 (최신 버전으로)..."
    } else {
        Write-Info "의존성 파일 컴파일 중..."
    }
    
    $compileArgsBase = @("--verbose")
    if ($Update.IsPresent) {
        $compileArgsBase += "--upgrade"
    }

    try {
        # 백엔드 의존성 컴파일
        Write-Info "백엔드 의존성 처리 중 ($backendReqIn -> $backendReqTxt)..."
        $currentBackendArgs = $compileArgsBase + @("--output-file=$backendReqTxt", $backendReqIn)
        pip-compile @currentBackendArgs
        if ($LASTEXITCODE -ne 0) { throw "백엔드 의존성 컴파일 실패" }
        Write-Success "백엔드 의존성 처리 완료."

        # 개발용 의존성 컴파일 (Dev 옵션이 활성화된 경우)
        if ($Dev.IsPresent) {
            Write-Info "개발용 의존성 처리 중 ($devReqIn -> $devReqTxt)..."
            $currentDevArgs = $compileArgsBase + @("--output-file=$devReqTxt", $devReqIn)
            pip-compile @currentDevArgs
            if ($LASTEXITCODE -ne 0) { throw "개발용 의존성 컴파일 실패" }
            Write-Success "개발용 의존성 처리 완료."
        }
        Write-Success "모든 의존성 파일 처리 완료."
    } catch {
        Write-Error "의존성 처리 실패: $($_.Exception.Message)"
        exit 1
    }
}

# 의존성 동기화
if ($Sync.IsPresent) {
    Write-Info "의존성 동기화 중..."
    try {
        if ($Dev.IsPresent -and (Test-Path $devReqTxt)) {
            Write-Info "개발용 의존성 동기화 중 ($devReqTxt)..."
            py -m piptools sync $devReqTxt # pip-sync 대신 py -m piptools sync 사용
            if ($LASTEXITCODE -ne 0) { throw "개발용 의존성 동기화 실패" }
            Write-Success "개발용 의존성 동기화 완료."
        } elseif (Test-Path $backendReqTxt) {
            Write-Info "백엔드 의존성 동기화 중 ($backendReqTxt)..."
            py -m piptools sync $backendReqTxt # pip-sync 대신 py -m piptools sync 사용
            if ($LASTEXITCODE -ne 0) { throw "백엔드 의존성 동기화 실패" }
            Write-Success "백엔드 의존성 동기화 완료."
        } else {
            Write-Warning "동기화할 .txt 파일을 찾을 수 없습니다. 먼저 컴파일을 실행하세요."
        }
        Write-Success "의존성 동기화 작업 완료."
    } catch {
        Write-Error "의존성 동기화 실패: $($_.Exception.Message)"
        exit 1
    }
}

Write-Success "모든 의존성 관리 작업이 완료되었습니다."

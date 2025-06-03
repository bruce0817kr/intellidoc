# IntelliDoc 테스트 실행 스크립트
# 이 스크립트는 IntelliDoc 프로젝트의 다양한 테스트를 실행하고 결과를 보고합니다.
# 기능:
# 1. 환경 검증 (verify_environment.ps1 실행)
# 2. 유닛 테스트 실행 (pytest)
# 3. 코드 품질 검사 (flake8, mypy, black)
# 4. 테스트 커버리지 측정
# 5. 통합 결과 보고

# 스크립트 매개변수
param(
    [switch]$SkipEnvironmentCheck,  # 환경 검증 건너뛰기
    [switch]$UnitTestsOnly,         # 유닛 테스트만 실행
    [switch]$QualityChecksOnly,     # 코드 품질 검사만 실행
    [switch]$Coverage,              # 커버리지 측정 포함
    [switch]$Verbose,               # 상세 출력
    [string]$TestPattern = "*",     # 테스트 패턴 필터
    [switch]$ShowLogs               # 테스트 로그 출력
)

# 색상 출력 함수들
function Write-Success {
    param ([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Error {
    param ([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Warning {
    param ([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Info {
    param ([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Header {
    param ([string]$Message)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host " $Message" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
}

# 실행 결과 추적 변수들
$global:TestResults = @{
    EnvironmentCheck = $null
    UnitTests = $null
    Flake8 = $null
    Mypy = $null
    Black = $null
    Coverage = $null
    TotalErrors = 0
    TotalWarnings = 0
}

# 가상 환경 활성화 함수
function Enable-VirtualEnvironment {
    $venvName = "intellidoc_venv"
    $activateScriptPath = Join-Path $PSScriptRoot "$venvName\Scripts\Activate.ps1"
    
    if (Test-Path $activateScriptPath) {
        try {
            Write-Info "가상 환경 활성화 중: $activateScriptPath"
            . $activateScriptPath
            
            if (-not [string]::IsNullOrEmpty($env:VIRTUAL_ENV)) {
                Write-Success "가상 환경이 활성화되었습니다: $env:VIRTUAL_ENV"
                return $true
            } else {
                Write-Warning "가상 환경 활성화에 실패했을 수 있습니다."
                return $false
            }
        } catch {
            Write-Error "가상 환경 활성화 중 오류: $($_.Exception.Message)"
            return $false
        }
    } else {
        Write-Error "가상 환경 활성화 스크립트를 찾을 수 없습니다: $activateScriptPath"
        return $false
    }
}

# 환경 검증 실행 함수
function Test-Environment {
    Write-Header "환경 검증 실행"
    
    $verifyScriptPath = Join-Path $PSScriptRoot "verify_environment.ps1"
    if (-not (Test-Path $verifyScriptPath)) {
        Write-Error "환경 검증 스크립트를 찾을 수 없습니다: $verifyScriptPath"
        $global:TestResults.EnvironmentCheck = "FAILED"
        $global:TestResults.TotalErrors++
        return $false
    }
    
    try {
        Write-Info "환경 검증 스크립트 실행 중..."
        $output = & $verifyScriptPath 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($Verbose -or $ShowLogs) {
            Write-Host $output
        }
        
        if ($exitCode -eq 0) {
            Write-Success "환경 검증 완료"
            $global:TestResults.EnvironmentCheck = "PASSED"
            return $true
        } else {
            Write-Error "환경 검증 실패 (Exit Code: $exitCode)"
            $global:TestResults.EnvironmentCheck = "FAILED"
            $global:TestResults.TotalErrors++
            return $false
        }
    } catch {
        Write-Error "환경 검증 실행 중 오류: $($_.Exception.Message)"
        $global:TestResults.EnvironmentCheck = "ERROR"
        $global:TestResults.TotalErrors++
        return $false
    }
}

# 유닛 테스트 실행 함수
function Invoke-UnitTests {
    Write-Header "유닛 테스트 실행"
    
    $testArgs = @()
    
    # 테스트 패턴 추가
    if ($TestPattern -ne "*") {
        $testArgs += "-k", $TestPattern
    }
    
    # 상세 출력 설정
    if ($Verbose) {
        $testArgs += "-v"
    }
    
    # 커버리지 설정
    if ($Coverage) {
        $testArgs += "--cov=.", "--cov-report=term-missing", "--cov-report=html:htmlcov"
    }
    
    # 로그 출력 설정
    if ($ShowLogs) {
        $testArgs += "--log-cli-level=INFO"
    }
    
    try {
        Write-Info "pytest 실행 중... 인수: $($testArgs -join ' ')"
        $output = py -m pytest @testArgs 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($Verbose -or $ShowLogs) {
            Write-Host $output
        }
        
        # pytest 결과 분석
        if ($exitCode -eq 0) {
            Write-Success "모든 유닛 테스트 통과"
            $global:TestResults.UnitTests = "PASSED"
            
            # 커버리지 정보 추출 시도
            if ($Coverage) {
                $coverageMatch = $output | Select-String "TOTAL.*(\d+%)"
                if ($coverageMatch) {
                    $coveragePercent = $coverageMatch.Matches[0].Groups[1].Value
                    Write-Info "테스트 커버리지: $coveragePercent"
                    $global:TestResults.Coverage = $coveragePercent
                }
            }
            
            return $true
        } elseif ($exitCode -eq 1) {
            Write-Warning "일부 테스트 실패"
            $global:TestResults.UnitTests = "FAILED"
            $global:TestResults.TotalErrors++
            return $false
        } else {
            Write-Error "테스트 실행 중 오류 (Exit Code: $exitCode)"
            $global:TestResults.UnitTests = "ERROR"
            $global:TestResults.TotalErrors++
            return $false
        }
    } catch {
        Write-Error "유닛 테스트 실행 중 오류: $($_.Exception.Message)"
        $global:TestResults.UnitTests = "ERROR"
        $global:TestResults.TotalErrors++
        return $false
    }
}

# Flake8 코드 품질 검사 함수
function Invoke-Flake8Check {
    Write-Header "Flake8 코드 스타일 검사"
    
    try {
        Write-Info "flake8 실행 중..."
        $output = py -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($Verbose -or $ShowLogs) {
            Write-Host $output
        }
        
        if ($exitCode -eq 0) {
            Write-Success "Flake8 검사 통과"
            $global:TestResults.Flake8 = "PASSED"
            return $true
        } else {
            Write-Warning "Flake8에서 문제 발견"
            $global:TestResults.Flake8 = "FAILED"
            $global:TestResults.TotalWarnings++
            return $false
        }
    } catch {
        Write-Error "Flake8 실행 중 오류: $($_.Exception.Message)"
        $global:TestResults.Flake8 = "ERROR"
        $global:TestResults.TotalErrors++
        return $false
    }
}

# MyPy 타입 검사 함수
function Invoke-MypyCheck {
    Write-Header "MyPy 타입 검사"
    
    try {
        Write-Info "mypy 실행 중..."
        $output = py -m mypy . --ignore-missing-imports 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($Verbose -or $ShowLogs) {
            Write-Host $output
        }
        
        if ($exitCode -eq 0) {
            Write-Success "MyPy 검사 통과"
            $global:TestResults.Mypy = "PASSED"
            return $true
        } else {
            Write-Warning "MyPy에서 타입 문제 발견"
            $global:TestResults.Mypy = "FAILED"
            $global:TestResults.TotalWarnings++
            return $false
        }
    } catch {
        Write-Error "MyPy 실행 중 오류: $($_.Exception.Message)"
        $global:TestResults.Mypy = "ERROR"
        $global:TestResults.TotalErrors++
        return $false
    }
}

# Black 코드 포맷팅 검사 함수
function Invoke-BlackCheck {
    Write-Header "Black 코드 포맷팅 검사"
    
    try {
        Write-Info "black 검사 실행 중..."
        $output = py -m black --check --diff . 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($Verbose -or $ShowLogs) {
            Write-Host $output
        }
        
        if ($exitCode -eq 0) {
            Write-Success "Black 포맷팅 검사 통과"
            $global:TestResults.Black = "PASSED"
            return $true
        } else {
            Write-Warning "Black에서 포맷팅 문제 발견"
            $global:TestResults.Black = "FAILED"
            $global:TestResults.TotalWarnings++
            return $false
        }
    } catch {
        Write-Error "Black 실행 중 오류: $($_.Exception.Message)"
        $global:TestResults.Black = "ERROR"
        $global:TestResults.TotalErrors++
        return $false
    }
}

# 결과 요약 출력 함수
function Show-TestSummary {
    Write-Header "테스트 결과 요약"
    
    Write-Host "환경 검증:      " -NoNewline
    switch ($global:TestResults.EnvironmentCheck) {
        "PASSED" { Write-Host "✅ 통과" -ForegroundColor Green }
        "FAILED" { Write-Host "❌ 실패" -ForegroundColor Red }
        "ERROR"  { Write-Host "💥 오류" -ForegroundColor Red }
        $null    { Write-Host "⏸️ 건너뜀" -ForegroundColor Gray }
    }
    
    Write-Host "유닛 테스트:    " -NoNewline
    switch ($global:TestResults.UnitTests) {
        "PASSED" { Write-Host "✅ 통과" -ForegroundColor Green }
        "FAILED" { Write-Host "❌ 실패" -ForegroundColor Red }
        "ERROR"  { Write-Host "💥 오류" -ForegroundColor Red }
        $null    { Write-Host "⏸️ 건너뜀" -ForegroundColor Gray }
    }
    
    Write-Host "Flake8 검사:   " -NoNewline
    switch ($global:TestResults.Flake8) {
        "PASSED" { Write-Host "✅ 통과" -ForegroundColor Green }
        "FAILED" { Write-Host "⚠️ 경고" -ForegroundColor Yellow }
        "ERROR"  { Write-Host "💥 오류" -ForegroundColor Red }
        $null    { Write-Host "⏸️ 건너뜀" -ForegroundColor Gray }
    }
    
    Write-Host "MyPy 검사:     " -NoNewline
    switch ($global:TestResults.Mypy) {
        "PASSED" { Write-Host "✅ 통과" -ForegroundColor Green }
        "FAILED" { Write-Host "⚠️ 경고" -ForegroundColor Yellow }
        "ERROR"  { Write-Host "💥 오류" -ForegroundColor Red }
        $null    { Write-Host "⏸️ 건너뜀" -ForegroundColor Gray }
    }
    
    Write-Host "Black 검사:    " -NoNewline
    switch ($global:TestResults.Black) {
        "PASSED" { Write-Host "✅ 통과" -ForegroundColor Green }
        "FAILED" { Write-Host "⚠️ 경고" -ForegroundColor Yellow }
        "ERROR"  { Write-Host "💥 오류" -ForegroundColor Red }
        $null    { Write-Host "⏸️ 건너뜀" -ForegroundColor Gray }
    }
    
    if ($global:TestResults.Coverage) {
        Write-Host "테스트 커버리지: $($global:TestResults.Coverage)" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "총 오류: $($global:TestResults.TotalErrors)" -ForegroundColor $(if ($global:TestResults.TotalErrors -eq 0) { "Green" } else { "Red" })
    Write-Host "총 경고: $($global:TestResults.TotalWarnings)" -ForegroundColor $(if ($global:TestResults.TotalWarnings -eq 0) { "Green" } else { "Yellow" })
    
    # 전체 결과 판정
    if ($global:TestResults.TotalErrors -eq 0) {
        Write-Success "🎉 모든 중요한 검사가 통과했습니다!"
        return $true
    } else {
        Write-Error "💥 일부 중요한 검사에서 오류가 발생했습니다."
        return $false
    }
}

# --- 메인 스크립트 실행 ---
Write-Header "IntelliDoc 테스트 실행 스크립트"

# 가상 환경 활성화
Write-Info "가상 환경 활성화 시도 중..."
if (-not (Enable-VirtualEnvironment)) {
    Write-Error "가상 환경을 활성화할 수 없습니다. 스크립트를 종료합니다."
    exit 1
}

$overallSuccess = $true

# 1. 환경 검증 (건너뛰지 않는 경우)
if (-not $SkipEnvironmentCheck) {
    if (-not (Test-Environment)) {
        $overallSuccess = $false
    }
} else {
    Write-Info "환경 검증을 건너뜁니다."
}

# 2. 유닛 테스트 실행 (품질 검사만 하는 경우가 아니라면)
if (-not $QualityChecksOnly) {
    if (-not (Invoke-UnitTests)) {
        $overallSuccess = $false
    }
} else {
    Write-Info "유닛 테스트를 건너뜁니다."
}

# 3. 코드 품질 검사 (유닛 테스트만 하는 경우가 아니라면)
if (-not $UnitTestsOnly) {
    # Flake8 검사
    Invoke-Flake8Check | Out-Null
    
    # MyPy 검사
    Invoke-MypyCheck | Out-Null
    
    # Black 검사
    Invoke-BlackCheck | Out-Null
} else {
    Write-Info "코드 품질 검사를 건너뜁니다."
}

# 결과 요약 출력
$summarySuccess = Show-TestSummary

# 최종 종료 코드 결정
if ($overallSuccess -and $summarySuccess) {
    Write-Success "테스트 실행이 성공적으로 완료되었습니다!"
    exit 0
} else {
    Write-Error "테스트 실행 중 문제가 발생했습니다."
    exit 1
}

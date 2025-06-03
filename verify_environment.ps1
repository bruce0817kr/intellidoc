# IntelliDoc 환경 검증 스크립트
# 이 스크립트는 IntelliDoc 프로젝트의 Python 환경이 올바르게 설정되었는지 확인합니다.
# 1. Python 버전 확인
# 2. 가상 환경 활성화 확인
# 3. pip check를 통한 의존성 호환성 검사
# 4. requirements.txt 및 requirements-dev.txt의 패키지 설치 및 버전 확인

# 색상 출력 함수
function Write-ColorOutput($Message, $Color = "White", $NewLine = $true) {
    if ($NewLine) {
        Write-Host $Message -ForegroundColor $Color
    } else {
        Write-Host $Message -ForegroundColor $Color -NoNewline
    }
}

# Helper function to write success messages
function Write-Success {
    param ([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

# Helper function to write error messages
function Write-Error {
    param ([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Helper function to write warning messages
function Write-Warning {
    param ([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

# Helper function to write info messages
function Write-Info {
    param ([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

# Function to get Python version
function Get-PythonVersion {
    try {
        $rawVersionOutput = (py --version 2>&1 | Out-String).Trim()
        $ansiEscapeRegex = "\x1B\[[0-?]*[ -/]*[@-~]" # ANSI 이스케이프 코드 제거용 정규식
        $versionString = ($rawVersionOutput -replace $ansiEscapeRegex, '').Trim() # ANSI 코드 제거 후 다시 Trim

        # 디버깅 로그
        # Write-Host "[DEBUG Get-PythonVersion] Raw: '$rawVersionOutput' (Length: $($rawVersionOutput.Length))"
        # Write-Host "[DEBUG Get-PythonVersion] Cleaned: '$versionString' (Length: $($versionString.Length))"

        # 정규식 수정: "Python " (대소문자 구분 없음)으로 시작하고, 그 뒤에 버전 번호가 오는 경우
        # 버전 번호는 X.Y.Z 형식이며, 그 뒤에 추가적인 문자열(예: .alpha, +build)이 올 수 있음
        if ($versionString -match '(?i)^Python\s+(\d+\.\d+\.\d+(?:\.\w+)*(?:[+-][\w\.]+)*)') {
            # Write-Host "[DEBUG Get-PythonVersion] Matched 'Python X.Y.Z...' pattern. Version: $($Matches[1])"
            return $Matches[1]
        } 
        # 또는 버전 번호만 있는 경우 (예: "3.13.0")
        elseif ($versionString -match '^(\d+\.\d+\.\d+(?:\.\w+)*(?:[+-][\w\.]+)*)$') {
            # Write-Host "[DEBUG Get-PythonVersion] Matched 'X.Y.Z...' pattern. Version: $($Matches[1])"
            return $Matches[1]
        }
        
        Write-Warning "Python 버전 형식을 인식할 수 없습니다. Cleaned: '$versionString', Raw: '$rawVersionOutput'"
        return "Unknown"
    }
    catch {
        Write-Error "Python 버전을 가져오는 중 오류 발생 (py --version 실행 실패 가능성): $($_.Exception.Message)"
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "py --version exited with code $LASTEXITCODE."
        }
        return "Error"
    }
}

# Function to check if virtual environment is active (basic check)
function Test-VirtualEnvActive {
    # This is a basic check; more robust checks might be needed depending on setup
    $venvPath = $env:VIRTUAL_ENV
    if (-not [string]::IsNullOrEmpty($venvPath)) {
        Write-Info "가상 환경이 활성화된 것으로 보입니다: $venvPath"
        return $true
    }
    else {
        Write-Warning "가상 환경이 활성화되지 않은 것 같습니다."
        return $false
    }
}

# Function to parse a requirements.txt file
function Get-ParsedRequirementsFile {
    param (
        [Parameter(Mandatory=$true)]
        [string]$filePath
    )

    if (-not (Test-Path $filePath)) {
        Write-Error "요구사항 파일을 찾을 수 없습니다: $filePath"
        return @{}
    }

    $requirements = @{}
    $lines = Get-Content $filePath
    # Corrected regex: uses single quotes, refined capture groups for name, extras, and version specifier.
    $regex = '^([\w.\-]+)(?:\[([\w.,\-]+)\])?(?:([!=<>~]=?[\w.*\-]+))?.*$'

    foreach ($line in $lines) {
        $trimmedLine = $line.Trim()
        if ($trimmedLine -eq "" -or $trimmedLine.StartsWith("#") -or $trimmedLine.StartsWith("-r") -or $trimmedLine.StartsWith("-e")) {
            continue
        }

        if ($trimmedLine -match $regex) {
            $name = $Matches[1]
            # $extras = $Matches[2] # Extras are captured but not used in this simplified version
            $version = $Matches[3] # Version specifier, e.g., ==1.0, >=1.2
            if ([string]::IsNullOrEmpty($version)) {
                $version = "any" # Or handle as error, or assume latest
            }
            $requirements[$name] = $version
        }
        else {
            Write-Warning "요구사항 파일에서 다음 라인을 파싱할 수 없습니다: $trimmedLine (파일: $filePath)"
        }
    }
    return $requirements
}

# Function to get currently installed Python packages
function Get-InstalledPackages {
    param()
    try {
        # Ensure pip version check doesn't interfere with JSON output or speed
        $pipOutput = py -m pip list --format=json --disable-pip-version-check
        if ($LASTEXITCODE -ne 0) {
            Write-Error "pip list 실행 중 오류 발생. pip가 정확히 설치되어 있고 PATH에 있는지 확인하세요."
            return $null
        }
        $installedPackages = $pipOutput | ConvertFrom-Json
        $result = @{}
        foreach ($pkg in $installedPackages) {
            $result[$pkg.name] = $pkg.version
        }
        return $result
    }
    catch {
        Write-Error "설치된 패키지 목록을 가져오는 중 오류 발생: $($_.Exception.Message)"
        return $null
    }
}

# Function to normalize package names (PEP 508 normalization)
function Normalize-PackageName {
    param([string]$name)
    # PEP 508: normalize by converting to lowercase and replacing [-_.] with -
    return $name.ToLower() -replace '[-_.]', '-'
}

# Function to test installed packages against a requirements file
function Test-InstalledPackagesAgainstRequirements {
    param (
        [Parameter(Mandatory=$true)]
        [string]$requirementsFilePath,
        [Parameter(Mandatory=$true)]
        [string]$requirementFileType # e.g., "Основной", "Для разработки"
    )

    Write-Info "$requirementFileType 요구사항 파일($requirementsFilePath)을 기준으로 패키지 설치 상태를 확인합니다."
    $requiredPackages = Get-ParsedRequirementsFile -filePath $requirementsFilePath
    if ($null -eq $requiredPackages -or $requiredPackages.Count -eq 0) {
        Write-Warning "$requirementsFilePath 에서 요구사항을 파싱하지 못했거나 파일이 비어있습니다."
        return # Or return a specific status
    }

    $installedPackages = Get-InstalledPackages
    if ($null -eq $installedPackages) {
        Write-Error "설치된 패키지 정보를 가져올 수 없어 검사를 계속할 수 없습니다."
        return # Or return a specific status
    }

    # Create normalized lookup table for installed packages
    $normalizedInstalledPackages = @{}
    foreach ($pkg in $installedPackages.Keys) {
        $normalizedName = Normalize-PackageName $pkg
        $normalizedInstalledPackages[$normalizedName] = @{
            'originalName' = $pkg
            'version' = $installedPackages[$pkg]
        }
    }

    $allMatch = $true
    foreach ($name in $requiredPackages.Keys) {
        $requiredVersionSpec = $requiredPackages[$name]
        $normalizedRequiredName = Normalize-PackageName $name
          if ($normalizedInstalledPackages.ContainsKey($normalizedRequiredName)) {
            $installedInfo = $normalizedInstalledPackages[$normalizedRequiredName]
            $installedVersion = $installedInfo.version
            # This is a simplified check. True version spec comparison (e.g., >=, <=, ~=) is complex.
            # For "any" or if no version spec, just check for presence.
            # If specific version (==), check exact match.
            # For this script, we'll primarily check for presence and exact match if "==" is used.
            if ($requiredVersionSpec -eq "any" -or [string]::IsNullOrEmpty($requiredVersionSpec)) {
                Write-Success "패키지 '$name'이(가) 설치되어 있습니다 (버전: $installedVersion). 요구사항: ($requiredVersionSpec)"
            } elseif ($requiredVersionSpec.StartsWith("==")) {
                $expectedVersion = $requiredVersionSpec.Substring(2)
                if ($installedVersion -eq $expectedVersion) {
                    Write-Success "패키지 '$name'이(가) 올바른 버전 ($installedVersion)으로 설치되어 있습니다."
                } else {
                    Write-Error "패키지 '$name'의 버전 불일치. 설치된 버전: $installedVersion, 요구사항: $requiredVersionSpec"
                    $allMatch = $false
                }
            } else {
                 # For other specifiers like >=, <=, ~=, !=, we're just noting it's installed.
                 # A full library for version comparison would be needed for accuracy here.
                Write-Info "패키지 '$name'이(가) 설치되어 있습니다 (버전: $installedVersion). 요구사항: $requiredVersionSpec. (정확한 버전 범위 검사는 이 스크립트에서 단순화됨)"
            }
        } else {
            Write-Error "필수 패키지 '$name'이(가) 설치되지 않았습니다. (요구사항: $requiredVersionSpec)"
            $allMatch = $false
        }
    }

    if ($allMatch) {
        Write-Success "$requirementFileType 모든 필수 패키지가 요구사항에 맞게 설치된 것으로 보입니다."
    } else {
        Write-Error "$requirementFileType 일부 패키지가 누락되었거나 버전이 일치하지 않습니다."
    }
}

# --- Main Script ---
Write-Host "IntelliDoc 환경 검증 스크립트 시작..."

# Attempt to activate virtual environment
$venvName = "intellidoc_venv" 
$activateScriptPath = Join-Path $PSScriptRoot "$venvName\Scripts\Activate.ps1"

if (Test-Path $activateScriptPath) {
    try {
        Write-Info "가상 환경 활성화를 시도합니다: $activateScriptPath"
        . $activateScriptPath
        Write-Success "가상 환경이 성공적으로 활성화되었거나 이미 활성화 상태일 수 있습니다."
        # Re-check VIRTUAL_ENV after attempting activation
        if (-not [string]::IsNullOrEmpty($env:VIRTUAL_ENV)) {
            Write-Info "활성화된 가상 환경 경로: $env:VIRTUAL_ENV"
        } else {
            Write-Warning "활성화 시도 후에도 VIRTUAL_ENV 환경 변수가 설정되지 않았습니다. 활성화가 부분적으로 실패했을 수 있습니다."
            Write-Warning "매우 중요: 이 경우, 이후의 Python/pip 명령어는 전역(Global) 환경을 사용할 수 있으며, 이는 검증 결과의 정확성에 큰 영향을 미칩니다!"
        }
    } catch {
        Write-Error "가상 환경 활성화 중 오류 발생: $($_.Exception.Message)"
        Write-Warning "스크립트는 계속 진행되지만, Python 환경이 올바르지 않을 수 있습니다."
    }
} else {
    Write-Warning "가상 환경 활성화 스크립트를 찾을 수 없습니다: $activateScriptPath. 전역 Python 환경에서 실행될 수 있습니다."
}


# 1. Python 버전 확인
Write-Info "1. Python 버전 확인 중..."
$pythonVersion = Get-PythonVersion
if ($pythonVersion) {
    Write-Success "Python 버전: $pythonVersion"
    # Add specific version checks if needed, e.g., if ($pythonVersion -notlike "3.10.*") { Write-Error "..." }
} else {
    Write-Error "Python 버전을 확인할 수 없습니다."
}

# 2. 가상 환경 활성화 상태 확인 (after attempting activation)
Write-Info "2. 가상 환경 활성화 상태 확인 중..."
Test-VirtualEnvActive # This will print info/warning

# 3. pip check 실행
Write-Info "3. 'pip check'를 사용하여 설치된 패키지 호환성 검사 중..."
try {
    $pipCheckOutput = py -m pip check 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "'pip check' 실행 결과: 모든 의존성이 호환됩니다."
        if ($pipCheckOutput) { Write-Host $pipCheckOutput -ForegroundColor Gray }
    } else {
        Write-Error "'pip check' 실행 결과: 호환되지 않는 의존성이 발견되었습니다."
        Write-Host $pipCheckOutput # Show output for details
    }
}
catch {
    Write-Error "'pip check' 실행 중 오류 발생: $($_.Exception.Message)"
}

# 4. requirements.txt 및 requirements-dev.txt 패키지 설치 확인
$backendReqPath = Join-Path $PSScriptRoot "backend\\requirements.txt"
$devReqPath = Join-Path $PSScriptRoot "requirements-dev.txt"

Test-InstalledPackagesAgainstRequirements -requirementsFilePath $backendReqPath -requirementFileType "백엔드 기본"
Test-InstalledPackagesAgainstRequirements -requirementsFilePath $devReqPath -requirementFileType "개발"

Write-Host "IntelliDoc 환경 검증 스크립트 완료."

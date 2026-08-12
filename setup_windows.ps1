param(
    [switch]$SkipPlaywright
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Require-Command {
    param(
        [string]$Name,
        [string]$InstallHint
    )
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found. $InstallHint"
    }
}

function Copy-IfMissing {
    param(
        [string]$Source,
        [string]$Destination
    )
    if ((Test-Path $Source) -and -not (Test-Path $Destination)) {
        Copy-Item $Source $Destination
        Write-Host "Created $Destination"
    }
}

function Assert-LastCommand {
    param([string]$Action)
    if ($LASTEXITCODE -ne 0) {
        throw "$Action failed with exit code $LASTEXITCODE."
    }
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Step "Checking prerequisites"
Require-Command "node" "Install Node.js 18 or newer from https://nodejs.org/"
Require-Command "npm" "Install npm with Node.js 18 or newer from https://nodejs.org/"
Require-Command "python" "Install Python 3.10 or newer from https://www.python.org/downloads/"

$NodeVersion = [version]((node --version).TrimStart("v"))
Assert-LastCommand "Checking Node.js version"
if ($NodeVersion.Major -lt 18) {
    throw "Node.js 18 or newer is required. Found $NodeVersion."
}

$PythonVersionRaw = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Assert-LastCommand "Checking Python version"
$PythonVersion = [version]$PythonVersionRaw
if ($PythonVersion.Major -lt 3 -or ($PythonVersion.Major -eq 3 -and $PythonVersion.Minor -lt 10)) {
    throw "Python 3.10 or newer is required. Found $PythonVersion."
}

Write-Host "Node.js $NodeVersion"
Write-Host "Python $PythonVersion"

Write-Step "Creating virtual environment"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
    Assert-LastCommand "Creating virtual environment"
}
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
& $VenvPython -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Virtual environment exists but pip is missing. Repairing with ensurepip..."
    & $VenvPython -m ensurepip --upgrade
    Assert-LastCommand "Repairing virtual environment pip"
}
& $VenvPython -m pip --version *> $null
Assert-LastCommand "Checking virtual environment pip"

Write-Step "Installing Python dependencies"
& $VenvPython -m pip install --upgrade pip
Assert-LastCommand "Upgrading pip"
if (Test-Path "wheels") {
    & $VenvPython -m pip install --no-index --find-links wheels -r requirements.txt
    Assert-LastCommand "Installing root Python dependencies from wheels"
    & $VenvPython -m pip install --no-index --find-links wheels -r apps\gmail-agent\requirements.txt
    Assert-LastCommand "Installing Gmail agent Python dependencies from wheels"
} else {
    & $VenvPython -m pip install -r requirements.txt
    Assert-LastCommand "Installing root Python dependencies"
    & $VenvPython -m pip install -r apps\gmail-agent\requirements.txt
    Assert-LastCommand "Installing Gmail agent Python dependencies"
}

Write-Step "Installing Node dependencies"
npm install
Assert-LastCommand "Installing Node dependencies"

if (-not $SkipPlaywright) {
    Write-Step "Installing Playwright Chromium"
    npx playwright install chromium
    Assert-LastCommand "Installing Node Playwright Chromium"
    & $VenvPython -m playwright install chromium
    Assert-LastCommand "Installing Python Playwright Chromium"
}

Write-Step "Creating local setup files"
Copy-IfMissing "config\profile.example.yml" "config\profile.yml"
Copy-IfMissing "templates\portals.example.yml" "portals.yml"
Copy-IfMissing ".env.example" ".env"
Copy-IfMissing "modes\_profile.template.md" "modes\_profile.md"
Copy-IfMissing "apps\gmail-agent\.env.example" "apps\gmail-agent\.env"

foreach ($Directory in @("data\gmail-agent", "output", "reports\daily", "jds", "batch\logs", "batch\tracker-additions")) {
    if (-not (Test-Path $Directory)) {
        New-Item -ItemType Directory -Path $Directory | Out-Null
    }
}

Write-Step "Validating install"
npm run doctor
if ($LASTEXITCODE -ne 0) {
    Write-Host "Doctor reported setup items that require your private files. Continue with the next steps below."
}
& $VenvPython run.py --help
Assert-LastCommand "Checking run.py help"

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next:"
Write-Host "  1. If you want Gmail scanning, download your Google OAuth credentials file from Google Console and save it as apps\gmail-agent\credentials.json."
Write-Host "  2. For setting up your CV, run the command .\.venv\Scripts\python.exe run.py"

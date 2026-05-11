param(
    [string]$PythonVersion = "3.12",
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

function Get-PythonCommand {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py"
    }

    return $null
}

$pythonCommand = Get-PythonCommand

if (-not $pythonCommand) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python is not installed and winget is unavailable. Install Python manually, then rerun this script."
    }

    Write-Output "Python not found. Installing Python $PythonVersion with winget..."
    winget install --id Python.Python.$PythonVersion -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget failed to install Python $PythonVersion."
    }

    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $pythonCommand = Get-PythonCommand
    if (-not $pythonCommand) {
        throw "Python install completed but python was still not found on PATH. Open a new terminal and rerun the script."
    }
}

Write-Output "Using Python command: $pythonCommand"

if ($pythonCommand -eq "py") {
    & py -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to ensure pip with py."
    }

    & py -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip with py."
    }

    & py -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requirements with py."
    }
}
else {
    & python -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to ensure pip with python."
    }

    & python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip with python."
    }

    & python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requirements with python."
    }
}

Write-Output "Python environment is ready."

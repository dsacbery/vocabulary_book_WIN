Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonBin = Join-Path $ProjectDir '.venv\Scripts\python.exe'
$AppPort = $null
$AppUrl = $null

Set-Location $ProjectDir

function Test-PortOpen {
    param([int]$Port)

    $Client = [System.Net.Sockets.TcpClient]::new()
    try {
        $Connect = $Client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $Connect.AsyncWaitHandle.WaitOne(250, $false)) {
            return $false
        }
        $Client.EndConnect($Connect)
        return $true
    } catch {
        return $false
    } finally {
        $Client.Close()
    }
}

function Test-AppSignature {
    param([string]$Url)

    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 1
        return $Response.Content -like "*Vocabulary*"
    } catch {
        return $false
    }
}

function Find-RunningAppUrl {
    foreach ($Candidate in 5000..5010) {
        $CandidateUrl = "http://127.0.0.1:$Candidate"
        if ((Test-PortOpen -Port $Candidate) -and (Test-AppSignature -Url $CandidateUrl)) {
            return $CandidateUrl
        }
    }
    return $null
}

function Find-AvailablePort {
    foreach ($Candidate in 5000..5010) {
        if (-not (Test-PortOpen -Port $Candidate)) {
            return $Candidate
        }
    }
    return $null
}

function Wait-ForApp {
    param([string]$Url)

    foreach ($Attempt in 1..40) {
        if (Test-AppSignature -Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

Write-Host "Starting Vocabulary Book for Windows..."

$RunningAppUrl = Find-RunningAppUrl
if ($RunningAppUrl) {
    Write-Host "Vocabulary Book is already running. Opening browser..."
    Start-Process $RunningAppUrl
    exit 0
}

$AppPort = Find-AvailablePort
if (-not $AppPort) {
    Write-Host "No available local port found from 5000 through 5010."
    Write-Host "Close another local service, then run this launcher again."
    Read-Host "Press Enter to close this window"
    exit 1
}

$AppUrl = "http://127.0.0.1:$AppPort"

if (-not (Test-Path -LiteralPath $PythonBin)) {
    Write-Host "Virtual environment not found at:"
    Write-Host $PythonBin
    Write-Host ""
    Write-Host "Create it first:"
    Write-Host "py -3 -m venv .venv"
    Write-Host ".\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    Read-Host "Press Enter to close this window"
    exit 1
}

& $PythonBin -c "import flask" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Install dependencies first:"
    Write-Host ".\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    Read-Host "Press Enter to close this window"
    exit 1
}

$env:VOCABULARY_PORT = [string]$AppPort
$Server = Start-Process -FilePath $PythonBin -ArgumentList "app.py" -WorkingDirectory $ProjectDir -WindowStyle Hidden -PassThru

if (Wait-ForApp -Url $AppUrl) {
    Write-Host "Vocabulary Book is ready. Opening browser..."
    Start-Process $AppUrl
    Wait-Process -Id $Server.Id
} else {
    Write-Host "Vocabulary did not become ready at $AppUrl."
    Write-Host "Stopping server process $($Server.Id)."
    Stop-Process -Id $Server.Id -Force -ErrorAction SilentlyContinue
    Read-Host "Press Enter to close this window"
    exit 1
}

# Starts Obscura (backend and website) on Windows.
#   powershell -ExecutionPolicy Bypass -File .\start.ps1

Set-Location $PSScriptRoot

if (-not (Test-Path "backend\.venv\Scripts\python.exe")) {
    Write-Host "Run setup.ps1 first." -ForegroundColor Red
    exit 1
}

$hasKey = Select-String -Path "backend\.env" -Pattern "^GEMINI_API_KEY=(?!put_your_key_here)\S+" -Quiet
if (-not $hasKey) {
    Write-Host "No Gemini key found in backend\.env." -ForegroundColor Yellow
    Write-Host "Privacy checks will work, but sending to the AI will fail until you add one." -ForegroundColor Yellow
}

$backend = "Set-Location '$PSScriptRoot\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backend

$frontend = "Set-Location '$PSScriptRoot\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontend

Write-Host "Waiting for the backend. The first start can take a few minutes..."

$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        Invoke-RestMethod "http://localhost:8000/api/health" -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}

if ($ready) {
    Write-Host "Backend is up. Opening the app." -ForegroundColor Green
    Write-Host "The first privacy check can be slow while the models load."
    Start-Process "http://localhost:5173"
} else {
    Write-Host "The backend did not answer in time. Look at its window for errors." -ForegroundColor Red
}

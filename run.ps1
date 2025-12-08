# Set UTF-8 encoding for Python
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Function to cleanup on exit
function Cleanup {
    Write-Host "`nStopping Flask server..." -ForegroundColor Yellow
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*Kungungalacorgus.stats*"} | Stop-Process -Force
    Write-Host "Flask server stopped." -ForegroundColor Green
}

# Register cleanup function to run on script exit
Register-EngineEvent PowerShell.Exiting -Action { Cleanup } | Out-Null

# Trap Ctrl+C to ensure cleanup
trap {
    Cleanup
    break
}

Write-Host "Starting Flask server..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

try {
    # Run Flask directly - it will terminate when this script is cancelled
    .\.venv\Scripts\python.exe main.py
}
finally {
    Cleanup
}

# Start RLE monitor and GitHub pusher together

Write-Host "Starting RLE Cloud Monitoring Suite..." -ForegroundColor Cyan
Write-Host ""

# Check if GITHUB_TOKEN is set
if (-not $env:GITHUB_TOKEN) {
    Write-Host "ERROR: GITHUB_TOKEN not set!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Set it permanently with:" -ForegroundColor Yellow
    Write-Host '  [System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "your_token_here", "User")' -ForegroundColor White
    Write-Host ""
    Write-Host "Or for this session only:" -ForegroundColor Yellow
    Write-Host '  $env:GITHUB_TOKEN="your_token_here"' -ForegroundColor White
    Write-Host ""
    pause
    exit
}

# Start monitor in background
$monitorJob = Start-Job -ScriptBlock {
    Set-Location "F:\RLE\lab"
    F:\RLE\venv\Scripts\python.exe start_monitor.py --mode cpu --sample-hz 1 --rated-cpu 125 --hwinfo-csv "F:\RLE\sessions\hwinfo\10_30_2025_702pm.CSV"
}

# Wait a bit
Start-Sleep -Seconds 3

# Start GitHub pusher in background
$pusherJob = Start-Job -ScriptBlock {
    Set-Location "F:\RLE\lab\monitoring"
    F:\RLE\venv\Scripts\python.exe push_to_github.py --interval 30
}

Write-Host "Both processes started!" -ForegroundColor Green
Write-Host "- Monitor: Collecting hardware data to CSV" -ForegroundColor Gray
Write-Host "- Pusher: Uploading CSV to GitHub every 30s" -ForegroundColor Gray
Write-Host ""
Write-Host "Jobs running. Access dashboard at:" -ForegroundColor Cyan
Write-Host "  Local:   http://localhost:8501" -ForegroundColor White
Write-Host "  Cloud:   [Your Streamlit Cloud URL]" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all processes" -ForegroundColor Yellow
Write-Host ""

# Keep running and show status
try {
    while ($true) {
        Start-Sleep -Seconds 5
        $monitorStatus = (Get-Job -Id $monitorJob.Id).State
        $pusherStatus = (Get-Job -Id $pusherJob.Id).State
        Write-Host "[Status] Monitor: $monitorStatus | Pusher: $pusherStatus" -ForegroundColor DarkGray
    }
} finally {
    Write-Host ""
    Write-Host "Stopping processes..." -ForegroundColor Yellow
    Stop-Job -Id $monitorJob.Id,$pusherJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $monitorJob.Id,$pusherJob.Id -ErrorAction SilentlyContinue
    Write-Host "Stopped." -ForegroundColor Green
}


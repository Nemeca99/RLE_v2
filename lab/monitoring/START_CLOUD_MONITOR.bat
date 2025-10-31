@echo off
REM Start RLE monitor and GitHub pusher together

echo Starting RLE Cloud Monitoring Suite...
echo.

REM Check if GITHUB_TOKEN is set
if "%GITHUB_TOKEN%"=="" (
    echo ERROR: GITHUB_TOKEN not set!
    echo.
    echo Set it first:
    echo   setx GITHUB_TOKEN "your_token_here"
    echo.
    echo Then restart this script.
    pause
    exit /b 1
)

REM Start monitor in background
start "RLE Monitor" cmd /k "cd /d F:\RLE\lab && ..\venv\Scripts\python.exe start_monitor.py --mode cpu --sample-hz 1 --rated-cpu 125 --hwinfo-csv ^"F:\RLE\sessions\hwinfo\10_30_2025_702pm.CSV^""

REM Wait a bit for monitor to start
timeout /t 3 /nobreak >nul

REM Start GitHub pusher in background
start "RLE GitHub Sync" cmd /k "cd /d F:\RLE\lab\monitoring && ..\..\venv\Scripts\python.exe push_to_github.py --interval 30"

echo.
echo Both processes started!
echo - Monitor: Collecting hardware data to CSV
echo - Pusher: Uploading CSV to GitHub every 30s
echo.
echo Press any key to open Streamlit dashboard...
pause >nul

REM Open browser to Streamlit
start http://localhost:8501

echo.
echo Starting Streamlit dashboard...
streamlit run monitoring\scada_dashboard_live.py


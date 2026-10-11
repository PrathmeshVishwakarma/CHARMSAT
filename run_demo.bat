@echo off
title CHARMSAT - DeltaV IO Signal Sudoku Allocation Engine
cls
echo ==============================================================================
echo   CHARMSAT -- DELTAV IO ALLOCATION ENGINE WITH INDEPENDENT VERIFIER
echo   CODE APEX 3.0 // VIT PUNE // TEAM lost_in_the_shine
echo ==============================================================================
echo.
echo [1/2] Verifying Python Environment...
python -c "import ortools, openpyxl, rapidfuzz, hypothesis, fastapi, uvicorn; print('   Dependencies: OK')"
if %errorlevel% neq 0 (
    echo [!] Installing required Python packages...
    python -m pip install -r backend\requirements.txt
)
echo.
echo [2/2] Launching CHARMSAT Unified Server at http://127.0.0.1:8000 ...
echo.
python run_server.py
pause

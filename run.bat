@echo off
chcp 65001 >nul
title CNC Tool Condition Monitoring - Frontend

echo ============================================
echo   数控机床刀具预测性维护系统
echo ============================================
echo.

echo [1/2] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.9+.
    pause
    exit /b 1
)

echo [2/2] Starting server...
echo.
python app.py
pause
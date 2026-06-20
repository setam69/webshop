@echo off
REM اجرای برنامه از روی کد منبع (بدون ساخت exe)
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PYEXE=py") else (set "PYEXE=python")

%PYEXE% -m pip install -r requirements.txt >nul 2>nul
%PYEXE% run.py
pause

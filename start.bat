@echo off
REM ====== اجرای پلتفرم حسابداری دستمزد روی ویندوز ======
chcp 65001 >nul
cd /d "%~dp0"

REM پیدا کردن پایتون
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYEXE=py"
) else (
    set "PYEXE=python"
)

REM ساخت محیط مجازی در اولین اجرا
if not exist ".venv" (
    echo --- در حال ساخت محیط و نصب پیش‌نیازها (فقط بار اول) ...
    %PYEXE% -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    call ".venv\Scripts\activate.bat"
)

echo --- در حال اجرای برنامه ... مرورگر باز می‌شود.
python run.py
pause

@echo off
REM ============================================================
REM   ساخت فایل اجرایی ویندوز (PersianPayroll.exe)
REM   این فایل را روی ویندوز اجرا کنید (دوبار کلیک).
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PYEXE=py") else (set "PYEXE=python")

echo --- نصب پیش‌نیازها و PyInstaller (ممکن است چند دقیقه طول بکشد) ...
%PYEXE% -m pip install --upgrade pip
%PYEXE% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo نصب پیش‌نیازها ناموفق بود.
    pause
    exit /b 1
)

echo --- در حال ساخت فایل اجرایی ...
%PYEXE% -m PyInstaller --noconfirm PersianPayroll.spec
if errorlevel 1 (
    echo ساخت فایل اجرایی ناموفق بود.
    pause
    exit /b 1
)

echo --- آماده‌سازی پوشه تحویل (README، چک‌لیست، پوشه‌های داده) ...
set "OUT=dist\PersianPayroll"
copy /Y "DIST_README.md" "%OUT%\README.md" >nul
copy /Y "TEST_CHECKLIST.md" "%OUT%\TEST_CHECKLIST.md" >nul
if not exist "%OUT%\instance" mkdir "%OUT%\instance"
if not exist "%OUT%\backups" mkdir "%OUT%\backups"

echo.
echo ============================================================
echo   ساخت با موفقیت انجام شد.
echo   پوشه آماده تحویل:  dist\PersianPayroll
echo   فایل اجرایی:        dist\PersianPayroll\PersianPayroll.exe
echo   برای استفاده، کل پوشه dist\PersianPayroll را کپی کنید.
echo ============================================================
pause

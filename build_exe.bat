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

echo --- پاک‌سازی build های قبلی (build, dist, spec های اضافی) ...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
REM حذف spec های قدیمی که ممکن است از اجرای اشتباه «pyinstaller run.py» ساخته شده باشند
if exist "run.spec" del /q "run.spec"
if exist "desktop.spec" del /q "desktop.spec"

echo --- در حال ساخت فایل اجرایی (فقط از روی PersianPayroll.spec) ...
%PYEXE% -m PyInstaller --clean --noconfirm PersianPayroll.spec
if errorlevel 1 (
    echo ساخت فایل اجرایی ناموفق بود.
    pause
    exit /b 1
)

echo --- بررسی صحت باندل (schema.sql باید موجود باشد) ...
if not exist "dist\PersianPayroll\_internal\payroll\schema.sql" (
    echo خطا: فایل schema.sql در خروجی پیدا نشد. build معتبر نیست.
    pause
    exit /b 1
)
if not exist "dist\PersianPayroll\_internal\templates\base.html" (
    echo خطا: قالب‌ها (templates) در خروجی پیدا نشدند. build معتبر نیست.
    pause
    exit /b 1
)

echo --- آماده‌سازی پوشه تحویل (README و چک‌لیست) ...
set "OUT=dist\PersianPayroll"
copy /Y "DIST_README.md" "%OUT%\README.md" >nul
copy /Y "TEST_CHECKLIST.md" "%OUT%\TEST_CHECKLIST.md" >nul
REM توجه: دیتابیس و بکاپ‌ها داخل پوشه dist ساخته نمی‌شوند.
REM محل ثابت داده‌ها:  %%LOCALAPPDATA%%\PersianPayroll
REM به همین دلیل build/rebuild هرگز دیتابیس کاربر را پاک نمی‌کند.

echo.
echo ============================================================
echo   ساخت با موفقیت انجام شد.
echo   پوشه آماده تحویل:  dist\PersianPayroll
echo   فایل اجرایی:        dist\PersianPayroll\PersianPayroll.exe
echo   برای استفاده، کل پوشه dist\PersianPayroll را کپی کنید.
echo ============================================================
pause

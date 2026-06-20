# -*- mode: python ; coding: utf-8 -*-
"""تنظیمات ساخت فایل اجرایی با PyInstaller (حالت onedir).

اجرا روی ویندوز:
    pyinstaller --noconfirm PersianPayroll.spec
خروجی:
    dist/PersianPayroll/PersianPayroll.exe  (به همراه پوشه _internal)
"""

# منابع فقط‌خواندنی که باید داخل بسته قرار بگیرند
datas = [
    ("templates", "templates"),
    ("static", "static"),
    ("payroll/schema.sql", "payroll"),
]

# ماژول‌هایی که ممکن است به‌صورت پویا بارگذاری شوند و تحلیل ایستا آن‌ها را نبیند
hiddenimports = [
    "openpyxl.cell._writer",
    "payroll.blueprints.dashboard",
    "payroll.blueprints.workers",
    "payroll.blueprints.projects",
    "payroll.blueprints.payments",
    "payroll.blueprints.settlement",
    "payroll.blueprints.expenses",
    "payroll.blueprints.customer",
    "payroll.blueprints.reports",
    "payroll.blueprints.settings",
    "payroll.demo",
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # برنامه از این پکیج‌ها استفاده نمی‌کند؛ کنارگذاشتن آن‌ها بسته را سبک‌تر می‌کند.
    excludes=["cryptography", "tkinter", "pytest", "PIL", "numpy", "pandas"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PersianPayroll",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,          # پنجره برای نمایش خطاها فعلاً باز می‌ماند
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="static/app.ico",  # در صورت داشتن آیکن، این خط را فعال کنید
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PersianPayroll",
)

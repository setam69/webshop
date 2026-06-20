"""مسیریابی سازگار با اجرای معمولی و اجرای بسته‌بندی‌شده با PyInstaller.

دو نوع مسیر داریم:
  * منابع فقط‌خواندنی (templates, static, schema.sql) که داخل بسته exe قرار می‌گیرند.
  * داده‌های ماندگار (دیتابیس، بکاپ‌ها، کلید نشست) که در یک مسیر ثابتِ کاربر و
    خارج از پوشه برنامه ذخیره می‌شوند تا با build/rebuild یا آپدیت exe پاک نشوند.
"""

import os
import sys


APP_NAME = "PersianPayroll"


def is_frozen():
    """آیا برنامه به‌صورت فایل اجرایی PyInstaller اجرا می‌شود؟"""
    return getattr(sys, "frozen", False)


def resource_path(*parts):
    """مسیر یک منبع فقط‌خواندنی بسته‌بندی‌شده (templates/static/schema.sql)."""
    if is_frozen():
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(base, *parts)


def project_root():
    """ریشه پروژه (در اجرای از روی کد منبع)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def exe_dir():
    """پوشه‌ای که فایل اجرایی در آن قرار دارد (برای یافتن دیتابیس‌های قدیمی)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return project_root()


def data_home():
    """پوشه ثابت و امن داده‌های کاربر.

    اولویت‌ها:
      ۱) متغیر محیطی ``PAYROLL_HOME`` (در صورت تنظیم).
      ۲) در حالت exe روی ویندوز: ``%LOCALAPPDATA%\\PersianPayroll``
         و روی سایر سیستم‌ها: ``~/.local/share/PersianPayroll``.
      ۳) در اجرای از روی کد منبع (توسعه): پوشه ``instance`` کنار پروژه
         (تا گردش‌کار فعلی و دیتابیس توسعه دست‌نخورده بماند).

    این پوشه **خارج از پوشه برنامه/dist** است؛ بنابراین build و rebuild هرگز آن
    را پاک نمی‌کند.
    """
    env = os.environ.get("PAYROLL_HOME")
    if env:
        return os.path.abspath(env)
    if is_frozen():
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.join(
                os.path.expanduser("~"), ".local", "share"
            )
        return os.path.join(base, APP_NAME)
    return os.path.join(project_root(), "instance")


# سازگاری با کد قبلی
def app_data_dir():
    return data_home()

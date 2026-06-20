"""مسیریابی سازگار با اجرای معمولی و اجرای بسته‌بندی‌شده با PyInstaller.

دو نوع مسیر داریم:
  * منابع فقط‌خواندنی (templates, static, schema.sql) که داخل بسته exe قرار می‌گیرند.
  * داده‌های ماندگار (دیتابیس، بکاپ‌ها، کلید نشست) که باید کنار فایل اجرایی و
    خارج از بسته ذخیره شوند تا با هر بار اجرا/آپدیت پاک نشوند.
"""

import os
import sys


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


def app_data_dir():
    """پوشه ماندگار کنار فایل اجرایی (در حالت عادی: ریشه پروژه).

    دیتابیس و بکاپ‌ها اینجا ذخیره می‌شوند تا با آپدیت exe پاک نشوند.
    """
    env = os.environ.get("PAYROLL_HOME")
    if env:
        return os.path.abspath(env)
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

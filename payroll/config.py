"""پیکربندی برنامه (Application configuration)."""

import os
import secrets
from datetime import timedelta

from .paths import data_home


# پوشه ثابت و امن داده‌های کاربر (خارج از پوشه برنامه/dist).
#   حالت exe ویندوز:  %LOCALAPPDATA%\PersianPayroll
#   اجرای از کد منبع:  <project>/instance
DATA_HOME = data_home()


def _load_or_create_secret_key():
    """کلید مخفی نشست را از روی دیسک می‌خواند یا یک‌بار می‌سازد و ذخیره می‌کند."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    os.makedirs(DATA_HOME, exist_ok=True)
    key_path = os.path.join(DATA_HOME, "secret_key")
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    key = secrets.token_hex(32)
    with open(key_path, "w", encoding="utf-8") as fh:
        fh.write(key)
    return key


class Config:
    SECRET_KEY = _load_or_create_secret_key()
    # دیتابیس مستقیماً داخل پوشه داده‌ها (نه زیرپوشه instance) قرار می‌گیرد.
    DATABASE = os.environ.get("PAYROLL_DB", os.path.join(DATA_HOME, "payroll.db"))
    BACKUP_DIR = os.path.join(DATA_HOME, "backups")

    # نام و رمز کاربر مدیر پیش‌فرض (فقط در اولین راه‌اندازی ساخته می‌شود)
    DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # سقف عمر کوکی نشست؛ کنترل اصلی خروج، «قفل بیکاری» در auth.py است.
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)


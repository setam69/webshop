"""پیکربندی برنامه (Application configuration)."""

import os
import secrets
from datetime import timedelta


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


def _load_or_create_secret_key():
    """کلید مخفی نشست را از روی دیسک می‌خواند یا یک‌بار می‌سازد و ذخیره می‌کند."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    key_path = os.path.join(INSTANCE_DIR, "secret_key")
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    key = secrets.token_hex(32)
    with open(key_path, "w", encoding="utf-8") as fh:
        fh.write(key)
    return key


class Config:
    SECRET_KEY = _load_or_create_secret_key()
    DATABASE = os.environ.get(
        "PAYROLL_DB", os.path.join(INSTANCE_DIR, "payroll.db")
    )
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")

    # نام و رمز کاربر مدیر پیش‌فرض (فقط در اولین راه‌اندازی ساخته می‌شود)
    DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # سقف عمر کوکی نشست؛ کنترل اصلی خروج، «قفل بیکاری» در auth.py است.
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)

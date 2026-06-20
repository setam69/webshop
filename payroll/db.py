"""لایه دیتابیس SQLite: اتصال، راه‌اندازی و توابع کمکی پرس‌وجو."""

import os
import sqlite3
from datetime import datetime

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    """اتصال دیتابیس مخصوص همین درخواست را برمی‌گرداند (با کش در ``g``)."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """ساختار جداول را ایجاد می‌کند و در صورت نبود، مدیر و تنظیمات پیش‌فرض می‌سازد."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as fh:
        db.executescript(fh.read())
    db.commit()
    _seed_defaults(db)


def _table_columns(db, table):
    return {r["name"] for r in db.execute("PRAGMA table_info(%s)" % table).fetchall()}


def migrate():
    """مهاجرت امن و افزایشی ساختار دیتابیس بدون آسیب به داده‌های قبلی.

    همه گام‌ها idempotent هستند (افزودن ستون فقط در صورت نبود، و جداول با
    ``IF NOT EXISTS``)، بنابراین اجرای مکرر آن بی‌خطر است. ستون‌های جدید روی
    دیتابیس‌های قدیمی با ``ALTER TABLE`` اضافه می‌شوند و داده‌ها دست‌نخورده می‌مانند.
    """
    db = get_db()
    changed = False

    additions = {
        "projects": [
            ("customer_total", "INTEGER NOT NULL DEFAULT 0"),
            ("internal_note", "TEXT"),
        ],
        "workers": [
            ("internal_note", "TEXT"),
        ],
        "payments": [
            ("method", "TEXT"),
        ],
    }
    for table, cols in additions.items():
        existing = _table_columns(db, table)
        for col, decl in cols:
            if col not in existing:
                db.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, decl))
                changed = True

    # برای پروژه‌های قدیمی که هنوز مبلغ قابل دریافت از مشتری ندارند،
    # آن را برابر مبلغ دستمزد قرار بده تا گزارش‌ها معنادار بمانند.
    if changed:
        db.execute(
            "UPDATE projects SET customer_total = labor_amount"
            " WHERE customer_total = 0 AND labor_amount > 0"
        )
    db.commit()
    return changed


def _seed_defaults(db):
    now = datetime.now().isoformat(timespec="seconds")

    # تنظیمات پیش‌فرض
    defaults = {
        "currency": "تومان",
        "shop_name": "مغازه",
        "default_shop_percent": "",  # خالی = خودکار از باقی‌مانده
        "auto_backup_enabled": "1",
        "auto_backup_keep": "30",
        "session_timeout_minutes": "30",
    }
    for key, value in defaults.items():
        db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    # کاربر مدیر پیش‌فرض فقط وقتی هیچ کاربری وجود ندارد
    row = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    if row["c"] == 0:
        username = current_app.config["DEFAULT_ADMIN_USERNAME"]
        password = current_app.config["DEFAULT_ADMIN_PASSWORD"]
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)"
            " VALUES (?, ?, ?, 'admin', 1, ?)",
            (username, generate_password_hash(password), "مدیر سیستم", now),
        )
    db.commit()


def create_backup(prefix="payroll_backup"):
    """یک کپی سالم از دیتابیس SQLite در پوشه backups می‌سازد و مسیر آن را برمی‌گرداند."""
    src = current_app.config["DATABASE"]
    backup_dir = current_app.config["BACKUP_DIR"]
    os.makedirs(backup_dir, exist_ok=True)
    if not os.path.exists(src):
        return None
    fname = "%s_%s.db" % (prefix, datetime.now().strftime("%Y%m%d_%H%M%S"))
    dest = os.path.join(backup_dir, fname)
    if os.path.exists(dest):  # جلوگیری از بازنویسی در همان ثانیه
        return dest
    # استفاده از API رسمی بکاپ SQLite برای کپی یکپارچه حتی هنگام باز بودن دیتابیس
    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dest)
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()
    return dest


def prune_backups(prefix, keep):
    """فقط ``keep`` بکاپ آخر با پیشوند مشخص را نگه می‌دارد و بقیه را حذف می‌کند."""
    backup_dir = current_app.config["BACKUP_DIR"]
    if not os.path.isdir(backup_dir) or keep <= 0:
        return
    files = sorted(
        (f for f in os.listdir(backup_dir)
         if f.startswith(prefix) and f.endswith(".db")),
        reverse=True,
    )
    for stale in files[keep:]:
        try:
            os.remove(os.path.join(backup_dir, stale))
        except OSError:
            pass


def auto_backup():
    """بکاپ خودکار هنگام راه‌اندازی برنامه (پیش از هر تغییر ساختار دیتابیس)."""
    try:
        keep = int(get_setting("auto_backup_keep", "30") or "30")
    except (ValueError, TypeError):
        keep = 30
    if get_setting("auto_backup_enabled", "1") == "0":
        return None
    path = create_backup(prefix="auto_backup")
    prune_backups("auto_backup", keep)
    return path


def get_setting(key, default=None):
    row = get_db().execute(
        "SELECT value FROM settings WHERE key = ?", (key,)
    ).fetchone()
    if row is None or row["value"] is None:
        return default
    return row["value"]


def set_setting(key, value):
    db = get_db()
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    db.commit()


@click.command("init-db")
def init_db_command():
    """دستور خط فرمان: ساخت جداول و داده‌های اولیه."""
    init_db()
    click.echo("دیتابیس راه‌اندازی شد.")


@click.command("migrate")
def migrate_command():
    """دستور خط فرمان: بکاپ خودکار و مهاجرت امن ساختار دیتابیس."""
    auto_backup()
    changed = migrate()
    click.echo("مهاجرت انجام شد." if changed else "ساختار دیتابیس از قبل به‌روز است.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_command)

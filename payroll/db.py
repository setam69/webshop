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


def _seed_defaults(db):
    now = datetime.now().isoformat(timespec="seconds")

    # تنظیمات پیش‌فرض
    defaults = {
        "currency": "تومان",
        "shop_name": "مغازه",
        "default_shop_percent": "",  # خالی = خودکار از باقی‌مانده
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


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

"""تنظیمات: واحد پول، درصد پیش‌فرض، مدیریت کاربران و بکاپ."""

import os
import shutil
from datetime import datetime

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request,
    send_file, url_for
)
from werkzeug.security import generate_password_hash

from ..auth import admin_required, login_required
from ..db import get_db, get_setting, set_setting
from ..utils import parse_percent

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/", methods=("GET", "POST"))
@login_required
def index():
    db = get_db()
    if request.method == "POST":
        currency = (request.form.get("currency") or "تومان").strip() or "تومان"
        shop_name = (request.form.get("shop_name") or "مغازه").strip() or "مغازه"
        shop_percent_raw = request.form.get("default_shop_percent") or ""
        if shop_percent_raw.strip():
            sp = parse_percent(shop_percent_raw)
            if sp is None:
                flash("درصد پیش‌فرض مغازه نامعتبر است.", "error")
                return redirect(url_for("settings.index"))
            set_setting("default_shop_percent", str(sp))
        else:
            set_setting("default_shop_percent", "")
        set_setting("currency", currency)
        set_setting("shop_name", shop_name)
        flash("تنظیمات ذخیره شد.", "success")
        return redirect(url_for("settings.index"))

    users = db.execute(
        "SELECT id, username, full_name, role, is_active, created_at FROM users ORDER BY id"
    ).fetchall()
    backups = _list_backups()
    return render_template(
        "settings/index.html",
        currency=get_setting("currency", "تومان"),
        shop_name=get_setting("shop_name", "مغازه"),
        default_shop_percent=get_setting("default_shop_percent", ""),
        users=users, backups=backups,
    )


# --- مدیریت کاربران ---------------------------------------------------------
@bp.route("/users/new", methods=("POST",))
@admin_required
def user_create():
    db = get_db()
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    full_name = (request.form.get("full_name") or "").strip()
    role = request.form.get("role") if request.form.get("role") in ("admin", "user") else "user"
    if not username or not password:
        flash("نام کاربری و رمز عبور الزامی است.", "error")
        return redirect(url_for("settings.index"))
    exists = db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    if exists:
        flash("این نام کاربری قبلاً وجود دارد.", "error")
        return redirect(url_for("settings.index"))
    db.execute(
        "INSERT INTO users (username, password_hash, full_name, role, is_active, created_at)"
        " VALUES (?, ?, ?, ?, 1, ?)",
        (username, generate_password_hash(password), full_name, role,
         datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    flash("کاربر جدید ساخته شد.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/users/<int:user_id>/password", methods=("POST",))
@admin_required
def user_password(user_id):
    db = get_db()
    password = request.form.get("password") or ""
    if len(password) < 4:
        flash("رمز عبور باید حداقل ۴ نویسه باشد.", "error")
        return redirect(url_for("settings.index"))
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
               (generate_password_hash(password), user_id))
    db.commit()
    flash("رمز عبور تغییر کرد.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/users/<int:user_id>/toggle", methods=("POST",))
@admin_required
def user_toggle(user_id):
    db = get_db()
    if user_id == g.user["id"]:
        flash("نمی‌توانید حساب خودتان را غیرفعال کنید.", "error")
        return redirect(url_for("settings.index"))
    user = db.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        db.execute("UPDATE users SET is_active = ? WHERE id = ?",
                   (0 if user["is_active"] else 1, user_id))
        db.commit()
        flash("وضعیت کاربر تغییر کرد.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/users/<int:user_id>/delete", methods=("POST",))
@admin_required
def user_delete(user_id):
    db = get_db()
    if user_id == g.user["id"]:
        flash("نمی‌توانید حساب خودتان را حذف کنید.", "error")
        return redirect(url_for("settings.index"))
    count = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if count <= 1:
        flash("حداقل یک کاربر باید باقی بماند.", "error")
        return redirect(url_for("settings.index"))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    flash("کاربر حذف شد.", "success")
    return redirect(url_for("settings.index"))


# --- بکاپ -------------------------------------------------------------------
def _list_backups():
    backup_dir = current_app.config["BACKUP_DIR"]
    if not os.path.isdir(backup_dir):
        return []
    items = []
    for name in sorted(os.listdir(backup_dir), reverse=True):
        if name.endswith(".db"):
            path = os.path.join(backup_dir, name)
            items.append({
                "name": name,
                "size": os.path.getsize(path),
                "mtime": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M"),
            })
    return items


@bp.route("/backup", methods=("POST",))
@login_required
def backup_now():
    """یک کپی امن از دیتابیس SQLite می‌سازد."""
    import sqlite3
    src = current_app.config["DATABASE"]
    backup_dir = current_app.config["BACKUP_DIR"]
    os.makedirs(backup_dir, exist_ok=True)
    fname = "payroll_backup_%s.db" % datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_dir, fname)
    # استفاده از API بکاپ SQLite برای کپی سازگار حتی هنگام باز بودن دیتابیس
    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dest)
    with dst_conn:
        src_conn.backup(dst_conn)
    src_conn.close()
    dst_conn.close()
    flash("بکاپ با موفقیت ساخته شد: %s" % fname, "success")
    return redirect(url_for("settings.index"))


@bp.route("/backup/download")
@login_required
def backup_download():
    name = request.args.get("name", "")
    backup_dir = current_app.config["BACKUP_DIR"]
    path = os.path.join(backup_dir, os.path.basename(name))
    if not name or not os.path.isfile(path):
        flash("فایل بکاپ یافت نشد.", "error")
        return redirect(url_for("settings.index"))
    return send_file(path, as_attachment=True, download_name=os.path.basename(name))

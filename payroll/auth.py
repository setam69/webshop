"""احراز هویت: ورود، خروج و دکوریتورهای دسترسی."""

import functools
import time

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash

from .db import get_db, get_setting

bp = Blueprint("auth", __name__)


def _idle_timeout_seconds():
    try:
        minutes = int(get_setting("session_timeout_minutes", "30") or "30")
    except (ValueError, TypeError):
        minutes = 30
    return max(minutes, 1) * 60


@bp.before_app_request
def load_logged_in_user():
    """کاربر فعلی را بارگذاری و قفل بیکاری (auto-logout) را اعمال می‌کند."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return

    # خروج خودکار پس از مدت مشخص بیکاری
    now = time.time()
    last = session.get("last_active", now)
    if now - last > _idle_timeout_seconds():
        session.clear()
        g.user = None
        if request.endpoint not in ("auth.login", "static"):
            flash("به دلیل بیکاری طولانی، از سیستم خارج شدید. دوباره وارد شوید.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return
    session["last_active"] = now

    g.user = get_db().execute(
        "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
    ).fetchone()
    if g.user is None:
        session.clear()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        if g.user["role"] != "admin":
            flash("این بخش فقط برای مدیر در دسترس است.", "error")
            return redirect(url_for("dashboard.index"))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("نام کاربری یا رمز عبور نادرست است.", "error")
        elif not user["is_active"]:
            flash("این حساب غیرفعال است.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["last_active"] = time.time()
            session.permanent = True
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("از حساب خارج شدید.", "success")
    return redirect(url_for("auth.login"))

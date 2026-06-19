"""مدیریت نیروهای نصب."""

from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)

from ..auth import login_required
from ..db import get_db
from ..queries import workers_with_balances
from ..utils import parse_percent

bp = Blueprint("workers", __name__, url_prefix="/workers")


@bp.route("/")
@login_required
def index():
    workers = workers_with_balances()
    return render_template("workers/list.html", workers=workers)


@bp.route("/new", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        data, error = _read_form()
        if error:
            flash(error, "error")
            return render_template("workers/form.html", worker=request.form, mode="new")
        db = get_db()
        db.execute(
            "INSERT INTO workers (name, phone, default_percent, is_active, note, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (data["name"], data["phone"], data["default_percent"],
             data["is_active"], data["note"],
             datetime.now().isoformat(timespec="seconds")),
        )
        db.commit()
        flash("نیرو با موفقیت ثبت شد.", "success")
        return redirect(url_for("workers.index"))
    return render_template("workers/form.html", worker=None, mode="new")


@bp.route("/<int:worker_id>/edit", methods=("GET", "POST"))
@login_required
def edit(worker_id):
    db = get_db()
    worker = db.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
    if worker is None:
        flash("نیرو یافت نشد.", "error")
        return redirect(url_for("workers.index"))
    if request.method == "POST":
        data, error = _read_form()
        if error:
            flash(error, "error")
            return render_template("workers/form.html", worker=request.form, mode="edit")
        db.execute(
            "UPDATE workers SET name=?, phone=?, default_percent=?, is_active=?, note=? WHERE id=?",
            (data["name"], data["phone"], data["default_percent"],
             data["is_active"], data["note"], worker_id),
        )
        db.commit()
        flash("تغییرات ذخیره شد.", "success")
        return redirect(url_for("workers.index"))
    return render_template("workers/form.html", worker=worker, mode="edit")


@bp.route("/<int:worker_id>/delete", methods=("POST",))
@login_required
def delete(worker_id):
    db = get_db()
    used = db.execute(
        "SELECT COUNT(*) AS c FROM project_workers WHERE worker_id = ?", (worker_id,)
    ).fetchone()["c"]
    if used:
        flash(
            "این نیرو در پروژه‌ها استفاده شده است؛ برای حفظ سوابق نمی‌توان حذف کرد. "
            "می‌توانید آن را «غیرفعال» کنید.",
            "error",
        )
        return redirect(url_for("workers.index"))
    db.execute("DELETE FROM workers WHERE id = ?", (worker_id,))
    db.commit()
    flash("نیرو حذف شد.", "success")
    return redirect(url_for("workers.index"))


def _read_form():
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    note = (request.form.get("note") or "").strip()
    is_active = 1 if request.form.get("is_active") else 0
    if not name:
        return None, "نام نیرو الزامی است."
    percent = parse_percent(request.form.get("default_percent") or "0")
    if percent is None:
        return None, "درصد پیش‌فرض باید عددی بین ۰ تا ۱۰۰ باشد."
    return {
        "name": name,
        "phone": phone,
        "note": note,
        "is_active": is_active,
        "default_percent": percent,
    }, None

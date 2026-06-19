"""ثبت و حذف پرداخت‌ها به نیروها."""

from datetime import datetime

from flask import Blueprint, flash, redirect, request, url_for

from ..auth import login_required
from ..db import get_db
from ..jalali import parse_date_input, today_jalali_str
from ..utils import parse_amount

bp = Blueprint("payments", __name__, url_prefix="/payments")


@bp.route("/new", methods=("POST",))
@login_required
def create():
    """ثبت پرداخت دستی به یک نیرو (اختیاری مرتبط با یک پروژه)."""
    db = get_db()
    worker_id = request.form.get("worker_id")
    project_id = request.form.get("project_id") or None
    amount = parse_amount(request.form.get("amount"))
    note = (request.form.get("note") or "").strip()
    date_jalali, date_iso = parse_date_input(
        request.form.get("payment_date") or today_jalali_str()
    )
    back = request.form.get("back") or url_for("dashboard.index")

    if not worker_id:
        flash("نیرو مشخص نشده است.", "error")
        return redirect(back)
    if amount is None or amount <= 0:
        flash("مبلغ پرداخت باید عددی بزرگ‌تر از صفر باشد.", "error")
        return redirect(back)

    db.execute(
        "INSERT INTO payments (worker_id, project_id, amount, payment_date,"
        " payment_date_jalali, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (int(worker_id), int(project_id) if project_id else None, amount,
         date_iso, date_jalali, note,
         datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    flash("پرداخت ثبت شد.", "success")
    return redirect(back)


@bp.route("/<int:payment_id>/delete", methods=("POST",))
@login_required
def delete(payment_id):
    db = get_db()
    db.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    db.commit()
    flash("پرداخت حذف شد.", "success")
    return redirect(request.form.get("back") or url_for("dashboard.index"))

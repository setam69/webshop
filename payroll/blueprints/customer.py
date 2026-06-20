"""دریافت پول از مشتری به‌صورت چند مرحله‌ای."""

from datetime import datetime

from flask import Blueprint, flash, redirect, request, url_for

from ..auth import login_required
from ..db import get_db
from ..jalali import parse_date_input, today_jalali_str
from ..utils import PAYMENT_METHODS, parse_amount

bp = Blueprint("customer", __name__, url_prefix="/customer-payments")


@bp.route("/new", methods=("POST",))
@login_required
def create():
    db = get_db()
    project_id = request.form.get("project_id")
    amount = parse_amount(request.form.get("amount"))
    method = request.form.get("method")
    note = (request.form.get("note") or "").strip()
    date_jalali, date_iso = parse_date_input(
        request.form.get("receive_date") or today_jalali_str()
    )
    back = url_for("projects.detail", project_id=project_id) if project_id else url_for("dashboard.index")

    if not project_id:
        flash("پروژه مشخص نشده است.", "error")
        return redirect(back)
    if amount is None or amount <= 0:
        flash("مبلغ دریافتی باید عددی بزرگ‌تر از صفر باشد.", "error")
        return redirect(back)
    if method not in PAYMENT_METHODS:
        method = None

    db.execute(
        "INSERT INTO customer_payments (project_id, amount, method, receive_date,"
        " receive_date_jalali, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (int(project_id), amount, method, date_iso, date_jalali, note,
         datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    flash("دریافت از مشتری ثبت شد.", "success")
    return redirect(back)


@bp.route("/<int:cp_id>/delete", methods=("POST",))
@login_required
def delete(cp_id):
    db = get_db()
    row = db.execute("SELECT project_id FROM customer_payments WHERE id = ?", (cp_id,)).fetchone()
    db.execute("DELETE FROM customer_payments WHERE id = ?", (cp_id,))
    db.commit()
    flash("دریافت از مشتری حذف شد.", "success")
    if row and row["project_id"]:
        return redirect(url_for("projects.detail", project_id=row["project_id"]))
    return redirect(url_for("dashboard.index"))

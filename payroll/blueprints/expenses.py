"""هزینه‌های جانبی پروژه (بنزین، غذا، ابزار، خرید جنس، ایاب‌وذهاب، سایر)."""

from datetime import datetime

from flask import Blueprint, flash, redirect, request, url_for

from ..auth import login_required
from ..db import get_db
from ..jalali import parse_date_input, today_jalali_str
from ..utils import EXPENSE_CATEGORIES, parse_amount

bp = Blueprint("expenses", __name__, url_prefix="/expenses")


@bp.route("/new", methods=("POST",))
@login_required
def create():
    db = get_db()
    project_id = request.form.get("project_id")
    category = request.form.get("category")
    amount = parse_amount(request.form.get("amount"))
    note = (request.form.get("note") or "").strip()
    date_jalali, date_iso = parse_date_input(
        request.form.get("expense_date") or today_jalali_str()
    )
    back = url_for("projects.detail", project_id=project_id) if project_id else url_for("dashboard.index")

    if not project_id:
        flash("پروژه مشخص نشده است.", "error")
        return redirect(back)
    if category not in EXPENSE_CATEGORIES:
        flash("دسته هزینه نامعتبر است.", "error")
        return redirect(back)
    if amount is None or amount <= 0:
        flash("مبلغ هزینه باید عددی بزرگ‌تر از صفر باشد.", "error")
        return redirect(back)

    db.execute(
        "INSERT INTO expenses (project_id, category, amount, expense_date,"
        " expense_date_jalali, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (int(project_id), category, amount, date_iso, date_jalali, note,
         datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    flash("هزینه ثبت شد.", "success")
    return redirect(back)


@bp.route("/<int:expense_id>/delete", methods=("POST",))
@login_required
def delete(expense_id):
    db = get_db()
    row = db.execute("SELECT project_id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    db.commit()
    flash("هزینه حذف شد.", "success")
    if row and row["project_id"]:
        return redirect(url_for("projects.detail", project_id=row["project_id"]))
    return redirect(url_for("dashboard.index"))

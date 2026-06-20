"""ثبت، ویرایش و حذف پرداخت‌ها به نیروها."""

from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)

from ..auth import login_required
from ..db import get_db
from ..jalali import parse_date_input, today_jalali_str
from ..queries import worker_totals
from ..utils import PAYMENT_METHODS, parse_amount

bp = Blueprint("payments", __name__, url_prefix="/payments")


def _clean_method(value):
    return value if value in PAYMENT_METHODS else None


@bp.route("/new", methods=("POST",))
@login_required
def create():
    """ثبت پرداخت دستی به یک نیرو (اختیاری مرتبط با یک پروژه)."""
    db = get_db()
    worker_id = request.form.get("worker_id")
    project_id = request.form.get("project_id") or None
    amount = parse_amount(request.form.get("amount"))
    method = _clean_method(request.form.get("method"))
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

    # جلوگیری از پرداخت بیشتر از مانده طلب، مگر با تأیید هشدار
    balance = worker_totals(int(worker_id))["balance"]
    if amount > balance and request.form.get("confirm_overpay") != "1":
        flash(
            "مبلغ پرداخت (%s) بیشتر از مانده طلب نیرو (%s) است. برای ثبت، گزینه تأیید را بزنید."
            % ("{:,}".format(amount), "{:,}".format(balance)),
            "error",
        )
        return redirect(back)

    db.execute(
        "INSERT INTO payments (worker_id, project_id, amount, method, payment_date,"
        " payment_date_jalali, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (int(worker_id), int(project_id) if project_id else None, amount, method,
         date_iso, date_jalali, note,
         datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    flash("پرداخت ثبت شد.", "success")
    return redirect(back)


@bp.route("/<int:payment_id>/edit", methods=("GET", "POST"))
@login_required
def edit(payment_id):
    db = get_db()
    payment = db.execute(
        "SELECT p.*, w.name AS worker_name FROM payments p"
        " JOIN workers w ON w.id = p.worker_id WHERE p.id = ?",
        (payment_id,),
    ).fetchone()
    if payment is None:
        flash("پرداخت یافت نشد.", "error")
        return redirect(url_for("dashboard.index"))

    back = request.values.get("back") or url_for(
        "settlement.detail", worker_id=payment["worker_id"]
    )

    if request.method == "POST":
        amount = parse_amount(request.form.get("amount"))
        method = _clean_method(request.form.get("method"))
        note = (request.form.get("note") or "").strip()
        date_jalali, date_iso = parse_date_input(
            request.form.get("payment_date") or today_jalali_str()
        )
        if amount is None or amount <= 0:
            flash("مبلغ پرداخت باید عددی بزرگ‌تر از صفر باشد.", "error")
            return render_template("payments/edit.html", payment=payment, back=back)

        # مانده طلب بدون احتساب همین پرداخت
        balance_excl = worker_totals(payment["worker_id"])["balance"] + payment["amount"]
        if amount > balance_excl and request.form.get("confirm_overpay") != "1":
            flash(
                "مبلغ ویرایش‌شده (%s) بیشتر از مانده طلب (%s) است. برای ثبت، تأیید کنید."
                % ("{:,}".format(amount), "{:,}".format(balance_excl)),
                "error",
            )
            return render_template("payments/edit.html", payment=payment, back=back,
                                   overpay=True)

        db.execute(
            "UPDATE payments SET amount=?, method=?, payment_date=?, payment_date_jalali=?,"
            " note=? WHERE id=?",
            (amount, method, date_iso, date_jalali, note, payment_id),
        )
        db.commit()
        flash("پرداخت ویرایش شد.", "success")
        return redirect(back)

    return render_template("payments/edit.html", payment=payment, back=back)


@bp.route("/<int:payment_id>/delete", methods=("POST",))
@login_required
def delete(payment_id):
    db = get_db()
    db.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    db.commit()
    flash("پرداخت حذف شد.", "success")
    return redirect(request.form.get("back") or url_for("dashboard.index"))

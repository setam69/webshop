"""تسویه حساب نیروها: صفحه طلب/پرداخت هر نیرو."""

from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)

from ..auth import login_required
from ..db import get_db
from ..jalali import today_jalali_str
from ..queries import worker_totals, workers_with_balances

bp = Blueprint("settlement", __name__, url_prefix="/settlement")


@bp.route("/")
@login_required
def index():
    workers = workers_with_balances()
    return render_template("settlement/list.html", workers=workers)


@bp.route("/<int:worker_id>")
@login_required
def detail(worker_id):
    db = get_db()
    worker = db.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
    if worker is None:
        flash("نیرو یافت نشد.", "error")
        return redirect(url_for("settlement.index"))

    projects = db.execute(
        "SELECT pw.percent, pw.share_amount, p.id, p.name, p.status,"
        " p.project_date_jalali, p.labor_amount,"
        " (SELECT COALESCE(SUM(amount), 0) FROM payments"
        "   WHERE worker_id = pw.worker_id AND project_id = p.id) AS paid_on_project"
        " FROM project_workers pw JOIN projects p ON p.id = pw.project_id"
        " WHERE pw.worker_id = ? ORDER BY p.id DESC",
        (worker_id,),
    ).fetchall()

    payments = db.execute(
        "SELECT p.*, pr.name AS project_name FROM payments p"
        " LEFT JOIN projects pr ON pr.id = p.project_id"
        " WHERE p.worker_id = ? ORDER BY p.id DESC",
        (worker_id,),
    ).fetchall()

    totals = worker_totals(worker_id)
    return render_template(
        "settlement/detail.html",
        worker=worker, projects=projects, payments=payments,
        totals=totals, today=today_jalali_str(),
    )


@bp.route("/<int:worker_id>/settle-all", methods=("POST",))
@login_required
def settle_all(worker_id):
    """ثبت یک پرداخت برابر با کل مانده طلب نیرو (تسویه کامل)."""
    db = get_db()
    totals = worker_totals(worker_id)
    balance = totals["balance"]
    if balance <= 0:
        flash("این نیرو مانده طلبی ندارد.", "error")
        return redirect(url_for("settlement.detail", worker_id=worker_id))
    j = today_jalali_str()
    from ..jalali import jalali_to_gregorian_iso
    db.execute(
        "INSERT INTO payments (worker_id, project_id, amount, payment_date,"
        " payment_date_jalali, note, created_at) VALUES (?, NULL, ?, ?, ?, ?, ?)",
        (worker_id, balance, jalali_to_gregorian_iso(j), j,
         "تسویه کامل", datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    flash("تسویه کامل ثبت شد.", "success")
    return redirect(url_for("settlement.detail", worker_id=worker_id))

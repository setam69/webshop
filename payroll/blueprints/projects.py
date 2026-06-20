"""ثبت، ویرایش و جزئیات پروژه‌ها."""

from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)

from ..auth import login_required
from ..db import get_db
from ..jalali import parse_date_input, today_jalali_str
from ..queries import project_financials, project_worker_paid
from ..utils import (
    PAYMENT_METHODS, STATUS_LABELS, parse_amount, parse_percent, worker_share,
)

bp = Blueprint("projects", __name__, url_prefix="/projects")


@bp.route("/")
@login_required
def index():
    status = request.args.get("status") or ""
    q = (request.args.get("q") or "").strip()
    pay = request.args.get("pay") or ""        # فیلتر دریافت از مشتری: unpaid/paid

    # جستجو شامل: نام پروژه، نام مشتری، نام نیرو، تاریخ شمسی، و برچسب وضعیت
    sql = (
        "SELECT p.*, "
        " (SELECT COALESCE(SUM(amount),0) FROM customer_payments WHERE project_id=p.id) AS received "
        "FROM projects p"
    )
    clauses, params = [], []
    if status in STATUS_LABELS:
        clauses.append("p.status = ?")
        params.append(status)
    if q:
        like = "%" + q + "%"
        clauses.append(
            "(p.name LIKE ? OR p.customer_name LIKE ? OR p.project_date_jalali LIKE ?"
            " OR p.id IN (SELECT pw.project_id FROM project_workers pw"
            "   JOIN workers w ON w.id = pw.worker_id WHERE w.name LIKE ?))"
        )
        params.extend([like, like, like, like])
    if pay == "unpaid":   # مشتری هنوز کامل پرداخت نکرده
        clauses.append("p.customer_total > (SELECT COALESCE(SUM(amount),0)"
                       " FROM customer_payments WHERE project_id=p.id)")
    elif pay == "paid":   # مشتری کامل پرداخت کرده
        clauses.append("p.customer_total > 0 AND p.customer_total <= (SELECT COALESCE(SUM(amount),0)"
                       " FROM customer_payments WHERE project_id=p.id)")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY p.id DESC"

    rows = get_db().execute(sql, params).fetchall()
    projects = []
    for r in rows:
        d = dict(r)
        d["customer_balance"] = (d["customer_total"] or 0) - d["received"]
        projects.append(d)
    return render_template(
        "projects/list.html", projects=projects, status=status, q=q, pay=pay
    )


@bp.route("/new", methods=("GET", "POST"))
@login_required
def create():
    db = get_db()
    if request.method == "POST":
        return _save_project(None)
    workers = db.execute(
        "SELECT * FROM workers WHERE is_active = 1 ORDER BY name COLLATE NOCASE"
    ).fetchall()
    f = {"status": "not_started", "project_date": today_jalali_str()}
    return render_template(
        "projects/form.html",
        project=None, mode="new", workers=workers, f=f,
        selected={}, today=today_jalali_str(),
    )


@bp.route("/<int:project_id>/edit", methods=("GET", "POST"))
@login_required
def edit(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        flash("پروژه یافت نشد.", "error")
        return redirect(url_for("projects.index"))
    if request.method == "POST":
        return _save_project(project_id)
    # نیروهای فعال + نیروهایی که قبلاً انتخاب شده‌اند (حتی اگر غیرفعال شده باشند)
    workers = db.execute(
        "SELECT * FROM workers WHERE is_active = 1 OR id IN"
        " (SELECT worker_id FROM project_workers WHERE project_id = ?)"
        " ORDER BY name COLLATE NOCASE",
        (project_id,),
    ).fetchall()
    rows = db.execute(
        "SELECT worker_id, percent FROM project_workers WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    selected = {r["worker_id"]: r["percent"] for r in rows}
    f = {
        "name": project["name"],
        "customer_name": project["customer_name"],
        "address": project["address"],
        "note": project["note"],
        "internal_note": project["internal_note"],
        "status": project["status"],
        "labor_amount": project["labor_amount"],
        "customer_total": project["customer_total"],
        "project_date": project["project_date_jalali"],
    }
    return render_template(
        "projects/form.html",
        project=project, mode="edit", workers=workers, f=f,
        selected=selected, today=today_jalali_str(),
    )


def _save_project(project_id):
    """ذخیره پروژه جدید یا ویرایش‌شده با اعتبارسنجی کامل درصدها و مبالغ."""
    db = get_db()
    name = (request.form.get("name") or "").strip()
    customer_name = (request.form.get("customer_name") or "").strip()
    address = (request.form.get("address") or "").strip()
    note = (request.form.get("note") or "").strip()
    internal_note = (request.form.get("internal_note") or "").strip()
    status = request.form.get("status") or "not_started"
    labor_amount = parse_amount(request.form.get("labor_amount"))
    # مبلغ قابل دریافت از مشتری؛ اگر خالی بماند برابر مبلغ دستمزد در نظر گرفته می‌شود
    customer_total = parse_amount(request.form.get("customer_total"))
    if customer_total is None:
        customer_total = labor_amount if labor_amount is not None else 0
    date_jalali, date_iso = parse_date_input(request.form.get("project_date"))

    # نیروهای انتخاب‌شده و درصدشان
    worker_ids = request.form.getlist("worker_id")
    chosen = []  # (worker_id, percent)
    errors = []
    for wid in worker_ids:
        try:
            wid_int = int(wid)
        except (TypeError, ValueError):
            continue
        percent = parse_percent(request.form.get("percent_%s" % wid))
        if percent is None:
            errors.append("درصد یکی از نیروها نامعتبر است.")
            continue
        chosen.append((wid_int, percent))

    if not name:
        errors.append("نام پروژه الزامی است.")
    if labor_amount is None:
        errors.append("مبلغ کل دستمزد باید عددی معتبر باشد.")
    if status not in STATUS_LABELS:
        status = "not_started"

    total_percent = sum(p for _, p in chosen)
    if total_percent > 100:
        errors.append(
            "مجموع درصد نیروها (%g٪) بیشتر از ۱۰۰٪ است؛ امکان ثبت وجود ندارد." % total_percent
        )

    if errors:
        for e in errors:
            flash(e, "error")
        return _rerender_form(project_id)

    now = datetime.now().isoformat(timespec="seconds")
    if project_id is None:
        cur = db.execute(
            "INSERT INTO projects (name, customer_name, project_date, project_date_jalali,"
            " address, labor_amount, customer_total, note, internal_note, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, customer_name, date_iso, date_jalali, address,
             labor_amount, customer_total, note, internal_note, status, now),
        )
        project_id = cur.lastrowid
    else:
        db.execute(
            "UPDATE projects SET name=?, customer_name=?, project_date=?, project_date_jalali=?,"
            " address=?, labor_amount=?, customer_total=?, note=?, internal_note=?, status=? WHERE id=?",
            (name, customer_name, date_iso, date_jalali, address,
             labor_amount, customer_total, note, internal_note, status, project_id),
        )
        db.execute("DELETE FROM project_workers WHERE project_id = ?", (project_id,))

    for wid_int, percent in chosen:
        db.execute(
            "INSERT INTO project_workers (project_id, worker_id, percent, share_amount)"
            " VALUES (?, ?, ?, ?)",
            (project_id, wid_int, percent, worker_share(labor_amount, percent)),
        )
    db.commit()
    flash("پروژه با موفقیت ذخیره شد.", "success")
    return redirect(url_for("projects.detail", project_id=project_id))


def _rerender_form(project_id):
    db = get_db()
    workers = db.execute(
        "SELECT * FROM workers WHERE is_active = 1 ORDER BY name COLLATE NOCASE"
    ).fetchall()
    selected = {}
    for wid in request.form.getlist("worker_id"):
        try:
            selected[int(wid)] = parse_percent(request.form.get("percent_%s" % wid)) or 0
        except (TypeError, ValueError):
            pass
    mode = "edit" if project_id else "new"
    f = {
        "name": request.form.get("name", ""),
        "customer_name": request.form.get("customer_name", ""),
        "address": request.form.get("address", ""),
        "note": request.form.get("note", ""),
        "internal_note": request.form.get("internal_note", ""),
        "status": request.form.get("status", "not_started"),
        "labor_amount": request.form.get("labor_amount", ""),
        "customer_total": request.form.get("customer_total", ""),
        "project_date": request.form.get("project_date", ""),
    }
    project = {"id": project_id} if project_id else None
    return render_template(
        "projects/form.html",
        project=project, mode=mode, workers=workers, f=f,
        selected=selected, today=today_jalali_str(),
    )


@bp.route("/<int:project_id>")
@login_required
def detail(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        flash("پروژه یافت نشد.", "error")
        return redirect(url_for("projects.index"))
    rows = db.execute(
        "SELECT pw.*, w.name AS worker_name, w.phone AS worker_phone"
        " FROM project_workers pw JOIN workers w ON w.id = pw.worker_id"
        " WHERE pw.project_id = ? ORDER BY w.name COLLATE NOCASE",
        (project_id,),
    ).fetchall()
    workers = []
    total_share = 0
    for r in rows:
        paid = project_worker_paid(project_id, r["worker_id"])
        total_share += r["share_amount"]
        workers.append({
            "worker_id": r["worker_id"],
            "name": r["worker_name"],
            "phone": r["worker_phone"],
            "percent": r["percent"],
            "share_amount": r["share_amount"],
            "paid": paid,
            "balance": r["share_amount"] - paid,
        })
    payments = db.execute(
        "SELECT p.*, w.name AS worker_name FROM payments p"
        " JOIN workers w ON w.id = p.worker_id"
        " WHERE p.project_id = ? ORDER BY p.id DESC",
        (project_id,),
    ).fetchall()
    expenses = db.execute(
        "SELECT * FROM expenses WHERE project_id = ? ORDER BY id DESC", (project_id,)
    ).fetchall()
    customer_payments = db.execute(
        "SELECT * FROM customer_payments WHERE project_id = ? ORDER BY id DESC", (project_id,)
    ).fetchall()
    fin = project_financials(project_id)
    return render_template(
        "projects/detail.html",
        project=project, workers=workers, total_share=fin["workers_share"],
        fin=fin, payments=payments, expenses=expenses,
        customer_payments=customer_payments, today=today_jalali_str(),
    )


@bp.route("/<int:project_id>/print")
@login_required
def print_view(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        flash("پروژه یافت نشد.", "error")
        return redirect(url_for("projects.index"))
    show_notes = request.args.get("notes") == "1"
    rows = db.execute(
        "SELECT pw.*, w.name AS worker_name FROM project_workers pw"
        " JOIN workers w ON w.id = pw.worker_id WHERE pw.project_id = ?"
        " ORDER BY w.name COLLATE NOCASE",
        (project_id,),
    ).fetchall()
    workers = []
    for r in rows:
        paid = project_worker_paid(project_id, r["worker_id"])
        workers.append({
            "name": r["worker_name"], "percent": r["percent"],
            "share_amount": r["share_amount"], "paid": paid,
            "balance": r["share_amount"] - paid,
        })
    expenses = db.execute(
        "SELECT * FROM expenses WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    customer_payments = db.execute(
        "SELECT * FROM customer_payments WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    fin = project_financials(project_id)
    return render_template(
        "projects/print.html",
        project=project, workers=workers, fin=fin, expenses=expenses,
        customer_payments=customer_payments, show_notes=show_notes,
    )


@bp.route("/<int:project_id>/status", methods=("POST",))
@login_required
def set_status(project_id):
    status = request.form.get("status")
    if status in STATUS_LABELS:
        db = get_db()
        db.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))
        db.commit()
        flash("وضعیت پروژه به‌روزرسانی شد.", "success")
    return redirect(url_for("projects.detail", project_id=project_id))


@bp.route("/<int:project_id>/delete", methods=("POST",))
@login_required
def delete(project_id):
    db = get_db()
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    flash("پروژه و اطلاعات مرتبط حذف شد.", "success")
    return redirect(url_for("projects.index"))

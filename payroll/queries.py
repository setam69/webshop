"""پرس‌وجوهای مشترک مالی که در داشبورد، تسویه و گزارش‌ها استفاده می‌شوند."""

from .db import get_db


def worker_totals(worker_id):
    """مجموع سهم، مجموع پرداخت و مانده طلب یک نیرو را برمی‌گرداند."""
    db = get_db()
    share = db.execute(
        "SELECT COALESCE(SUM(share_amount), 0) AS s FROM project_workers WHERE worker_id = ?",
        (worker_id,),
    ).fetchone()["s"]
    paid = db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM payments WHERE worker_id = ?",
        (worker_id,),
    ).fetchone()["s"]
    return {"share": share, "paid": paid, "balance": share - paid}


def project_worker_paid(project_id, worker_id):
    """مبلغ پرداخت‌شده به یک نیرو در یک پروژه خاص."""
    row = get_db().execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM payments"
        " WHERE worker_id = ? AND project_id = ?",
        (worker_id, project_id),
    ).fetchone()
    return row["s"]


def dashboard_stats():
    """آمار کلی برای داشبورد."""
    db = get_db()
    projects_count = db.execute("SELECT COUNT(*) AS c FROM projects").fetchone()["c"]
    total_labor = db.execute(
        "SELECT COALESCE(SUM(labor_amount), 0) AS s FROM projects"
    ).fetchone()["s"]
    total_workers_share = db.execute(
        "SELECT COALESCE(SUM(share_amount), 0) AS s FROM project_workers"
    ).fetchone()["s"]
    total_paid = db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM payments"
    ).fetchone()["s"]
    shop_share = total_labor - total_workers_share
    unsettled_count = db.execute(
        "SELECT COUNT(*) AS c FROM projects WHERE status != 'settled'"
    ).fetchone()["c"]
    return {
        "projects_count": projects_count,
        "total_labor": total_labor,
        "total_workers_share": total_workers_share,
        "shop_share": shop_share,
        "total_paid": total_paid,
        "total_debt": total_workers_share - total_paid,
        "unsettled_count": unsettled_count,
    }


def workers_with_balances(only_active=False, only_debt=False):
    """لیست نیروها همراه با سهم، پرداخت و مانده طلب."""
    db = get_db()
    sql = (
        "SELECT w.*, "
        " COALESCE(s.share, 0) AS total_share, "
        " COALESCE(p.paid, 0) AS total_paid "
        "FROM workers w "
        "LEFT JOIN (SELECT worker_id, SUM(share_amount) AS share FROM project_workers GROUP BY worker_id) s "
        "  ON s.worker_id = w.id "
        "LEFT JOIN (SELECT worker_id, SUM(amount) AS paid FROM payments GROUP BY worker_id) p "
        "  ON p.worker_id = w.id "
    )
    if only_active:
        sql += "WHERE w.is_active = 1 "
    sql += "ORDER BY w.name COLLATE NOCASE"
    rows = []
    for r in db.execute(sql).fetchall():
        d = dict(r)
        d["balance"] = d["total_share"] - d["total_paid"]
        if only_debt and d["balance"] <= 0:
            continue
        rows.append(d)
    return rows

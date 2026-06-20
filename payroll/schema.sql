-- ساختار دیتابیس پلتفرم حسابداری دستمزد
-- همه‌ی مبالغ به «تومان» و به صورت عدد صحیح ذخیره می‌شوند.

PRAGMA foreign_keys = ON;

-- کاربران پنل ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    full_name     TEXT,
    role          TEXT    NOT NULL DEFAULT 'admin',   -- admin | user
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL
);

-- نیروهای نصب ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    phone           TEXT,
    default_percent REAL    NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    note            TEXT,
    internal_note   TEXT,                  -- یادداشت داخلی نیرو
    created_at      TEXT    NOT NULL
);

-- پروژه‌ها -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    customer_name       TEXT,
    project_date        TEXT,                  -- تاریخ میلادی ISO برای مرتب‌سازی/بازه
    project_date_jalali TEXT,                  -- تاریخ شمسی برای نمایش
    address             TEXT,
    labor_amount        INTEGER NOT NULL DEFAULT 0,
    customer_total      INTEGER NOT NULL DEFAULT 0,  -- مبلغ کل قابل دریافت از مشتری
    note                TEXT,
    internal_note       TEXT,                  -- یادداشت داخلی (قابل مخفی‌کردن در چاپ)
    status              TEXT    NOT NULL DEFAULT 'not_started',
    created_at          TEXT    NOT NULL
);

-- اتصال نیرو به پروژه (درصد و سهم همان پروژه) ---------------------------------
CREATE TABLE IF NOT EXISTS project_workers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL,
    worker_id    INTEGER NOT NULL,
    percent      REAL    NOT NULL DEFAULT 0,
    share_amount INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (worker_id)  REFERENCES workers  (id) ON DELETE CASCADE,
    UNIQUE (project_id, worker_id)
);

-- پرداخت‌ها به نیروها --------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id           INTEGER NOT NULL,
    project_id          INTEGER,               -- می‌تواند تهی باشد (تسویه کلی)
    amount              INTEGER NOT NULL,
    method              TEXT,                  -- روش پرداخت: cash/card/transfer/check/other
    payment_date        TEXT,                  -- میلادی ISO
    payment_date_jalali TEXT,                  -- شمسی
    note                TEXT,
    created_at          TEXT    NOT NULL,
    FOREIGN KEY (worker_id)  REFERENCES workers  (id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL
);

-- هزینه‌های جانبی هر پروژه ----------------------------------------------------
CREATE TABLE IF NOT EXISTS expenses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL,
    category            TEXT    NOT NULL,      -- fuel/food/consumable/goods/transport/other
    amount              INTEGER NOT NULL,
    expense_date        TEXT,
    expense_date_jalali TEXT,
    note                TEXT,
    created_at          TEXT    NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- دریافت‌های پول از مشتری (چند مرحله‌ای) --------------------------------------
CREATE TABLE IF NOT EXISTS customer_payments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL,
    amount              INTEGER NOT NULL,
    method              TEXT,
    receive_date        TEXT,
    receive_date_jalali TEXT,
    note                TEXT,
    created_at          TEXT    NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- تنظیمات کلیدی-مقداری -------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_pw_project ON project_workers (project_id);
CREATE INDEX IF NOT EXISTS idx_pw_worker  ON project_workers (worker_id);
CREATE INDEX IF NOT EXISTS idx_pay_worker ON payments (worker_id);
CREATE INDEX IF NOT EXISTS idx_proj_date  ON projects (project_date);
CREATE INDEX IF NOT EXISTS idx_exp_project ON expenses (project_id);
CREATE INDEX IF NOT EXISTS idx_cp_project  ON customer_payments (project_id);

"""اجرای برنامه به‌صورت اپلیکیشن پنجره‌ای ویندوز (Desktop App) با pywebview.

Flask در یک نخ پس‌زمینه اجرا می‌شود و pywebview یک پنجره native ویندوز باز می‌کند
و برنامه را داخل همان پنجره نمایش می‌دهد. **مرورگر سیستم باز نمی‌شود.**

این فایل نقطه‌ورود اصلی فایل اجرایی (PersianPayroll.exe) است.
برای اجرای حالت مرورگری/توسعه از ``run.py`` یا ``run_web.py`` استفاده کنید.
"""

import multiprocessing
import os
import socket
import sys
import threading
import time

from payroll import create_app

WINDOW_TITLE = "حسابداری نیروهای نصب"
HOST = "127.0.0.1"


def _port_is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) != 0


def pick_port(preferred=5000):
    """پورت ترجیحی را اگر آزاد بود برمی‌گرداند، وگرنه یک پورت آزاد از سیستم."""
    if _port_is_free(preferred):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def start_server(app, port):
    """سرور Flask را در یک نخ daemon اجرا می‌کند (با بسته‌شدن پنجره خاتمه می‌یابد)."""
    def _run():
        # بدون reloader و بدون باز کردن مرورگر
        app.run(host=HOST, port=port, debug=False, use_reloader=False, threaded=True)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def wait_until_up(port, timeout=20.0):
    """منتظر بالا آمدن سرور می‌ماند."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) == 0:
                return True
        time.sleep(0.1)
    return False


def main():
    # ساخت اپ → init_db + بکاپ خودکار + مهاجرت امن (دیتابیس قبلی حفظ می‌شود)
    app = create_app()
    port = pick_port(int(os.environ.get("PORT", "5000")))
    start_server(app, port)
    if not wait_until_up(port):
        raise RuntimeError("سرور داخلی برنامه بالا نیامد.")

    import webview  # فقط در حالت دسکتاپ لازم است
    webview.create_window(
        WINDOW_TITLE,
        "http://%s:%d/" % (HOST, port),
        width=1200,
        height=800,
        resizable=True,
    )
    # امکان maximize و تغییر اندازه؛ این فراخوانی تا بسته‌شدن پنجره مسدود می‌ماند
    webview.start()


def _log_error(exc_text):
    """نوشتن خطا در فایلی کنار برنامه تا حتی بدون کنسول قابل بررسی باشد."""
    try:
        from payroll.paths import app_data_dir
        with open(os.path.join(app_data_dir(), "desktop_error.log"), "a",
                  encoding="utf-8") as fh:
            fh.write(exc_text + "\n")
    except Exception:
        pass


def run():
    try:
        main()
    except Exception:
        import traceback
        text = traceback.format_exc()
        _log_error(text)
        # اگر کنسول وجود دارد، خطا را نمایش بده (در حالت پنجره‌ای stderr ممکن است None باشد)
        if getattr(sys, "stderr", None):
            try:
                sys.stderr.write(text)
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # لازم برای سازگاری با PyInstaller
    run()

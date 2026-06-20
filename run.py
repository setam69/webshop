"""اجرای محلی پلتفرم حسابداری دستمزد.

اجرای عادی:   python run.py
اجرای exe:    دوبار کلیک روی PersianPayroll.exe
سپس مرورگر روی نشانی http://127.0.0.1:5000 باز می‌شود.
"""

import multiprocessing
import os
import sys
import threading
import webbrowser

from payroll import create_app

app = create_app()


def _open_browser(host, port):
    try:
        webbrowser.open("http://%s:%d/" % (host, port))
    except Exception:
        pass


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))

    # در اجرای مستقیم (نه فرایند ری‌لود) مرورگر را خودکار باز کن
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true" and not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, _open_browser, args=(host, port)).start()

    print("=" * 56)
    print("  پلتفرم حسابداری دستمزد در حال اجراست")
    print("  نشانی:  http://%s:%d" % (host, port))
    print("  برای بستن برنامه این پنجره را ببندید.")
    print("=" * 56)

    # use_reloader=False تا در حالت exe دو نسخه اجرا نشود
    app.run(host=host, port=port, debug=bool(os.environ.get("DEBUG")),
            use_reloader=False)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # لازم برای سازگاری با PyInstaller
    try:
        main()
    except Exception as exc:  # نمایش خطا و باز نگه‌داشتن پنجره در حالت exe
        import traceback
        traceback.print_exc()
        if getattr(sys, "frozen", False):
            print("\nخطا در اجرای برنامه. متن بالا را بررسی کنید.")
            try:
                input("برای بستن، کلید Enter را بزنید...")
            except EOFError:
                pass
        sys.exit(1)

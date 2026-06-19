"""اجرای محلی پلتفرم حسابداری دستمزد.

اجرا:  python run.py
سپس مرورگر روی نشانی http://127.0.0.1:5000 باز می‌شود.
"""

import os
import threading
import webbrowser

from payroll import create_app

app = create_app()


def _open_browser(host, port):
    webbrowser.open("http://%s:%d/" % (host, port))


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    # در حالت اجرای مستقیم (نه ری‌لود)، مرورگر را خودکار باز کن
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true" and not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, _open_browser, args=(host, port)).start()
    app.run(host=host, port=port, debug=bool(os.environ.get("DEBUG")))

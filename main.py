import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS

DB_PATH = "app.db"

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})


# ============================================================
#  DATABASE KURULUMU
# ============================================================
def init_db():
    """Geliştirme ortamı: her çalıştırmada drafts tablosunu temiz kur."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Eski tabloyu sil
    c.execute("DROP TABLE IF EXISTS drafts")

    # Yeni tabloyu oluştur
    c.execute("""
        CREATE TABLE drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            platforms TEXT,
            schedule_mode TEXT,
            scheduled_at TEXT,
            media_json TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(">> drafts tablosu yeni şemayla oluşturuldu.")


# ============================================================
#  DATABASE YARDIMCI FONKSIYONLAR
# ============================================================
def save_draft(text, platforms, schedule_mode, scheduled_at, media_files):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    platforms_str = ",".join(platforms) if platforms else ""
    media_json = json.dumps(media_files or [])

    c.execute(
        """
        INSERT INTO drafts (text, platforms, schedule_mode, scheduled_at, media_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (text, platforms_str, schedule_mode, scheduled_at, media_json),
    )
    conn.commit()
    conn.close()


def get_all_drafts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, text, platforms, schedule_mode, scheduled_at, media_json, ts
        FROM drafts
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def get_draft_by_id(draft_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, text, platforms, schedule_mode, scheduled_at, media_json, ts
        FROM drafts
        WHERE id = ?
    """, (draft_id,))
    row = c.fetchone()
    conn.close()
    return row


# ============================================================
#  ROUTES
# ============================================================

@app.route("/")
def prepare():
    """Yeni gönderi: boş form."""
    return render_template("prepare.html", draft=None)


@app.route("/multi")
def multi():
    """Multi-Post Beta placeholder sayfası."""
    return render_template("multi.html")


@app.route("/drafts")
def drafts():
    """Tüm taslakları listeleyen sayfa."""
    rows = get_all_drafts()
    drafts_list = []

    for row in rows:
        draft_id, text, platforms_str, schedule_mode, scheduled_at, media_json, ts = row
        platforms = platforms_str.split(",") if platforms_str else []

        try:
            media_files = json.loads(media_json) if media_json else []
        except Exception:
            media_files = []

        drafts_list.append({
            "id": draft_id,
            "text": text or "",
            "platforms": platforms,
            "schedule_mode": schedule_mode or "now",
            "scheduled_at": scheduled_at or "",
            "media_files": media_files,
            "ts": ts,
        })

    return render_template("drafts.html", drafts=drafts_list)


@app.route("/draft/<int:draft_id>")
def edit_draft(draft_id):
    """Belirli bir taslağı düzenleme modunda açar."""
    row = get_draft_by_id(draft_id)
    if not row:
        return redirect(url_for("prepare"))

    draft_id, text, platforms_str, schedule_mode, scheduled_at, media_json, ts = row

    draft = {
        "id": draft_id,
        "text": text or "",
        "platforms": platforms_str.split(",") if platforms_str else [],
        "schedule_mode": schedule_mode or "now",
        "scheduled_at": scheduled_at or "",
        "media_files": json.loads(media_json) if media_json else [],
        "ts": ts,
    }

    return render_template("prepare.html", draft=draft)


@app.route("/api/draft", methods=["POST"])
def save_draft_api():
    """Frontend'in taslak kaydetmesi için JSON API."""
    data = request.json or {}

    text = (data.get("text") or "").strip()
    platforms = data.get("platforms") or []
    if not isinstance(platforms, list):
        platforms = []

    schedule_mode = data.get("schedule_mode") or "now"
    scheduled_at = data.get("scheduled_at") or ""

    media_files = data.get("media_files") or []
    if not isinstance(media_files, list):
        media_files = []

    save_draft(text, platforms, schedule_mode, scheduled_at, media_files)
    return jsonify({"ok": True})


# ============================================================
#  UYGULAMA BAŞLATMA
# ============================================================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)

from __future__ import annotations
from flask import Flask, render_template, request, redirect, url_for, jsonify
from pathlib import Path
import json
import os

# OpenAI client (gerçek yapay zeka için)
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception:
    client = None  # API yoksa endpointler hata mesajı döner

# -------------------------------------------------
# Basit dosya tabanlı depolama
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SCHEDULED_FILE = DATA_DIR / "scheduled_posts.json"
DRAFTS_FILE = DATA_DIR / "draft_posts.json"


def load_json(path: Path) -> list:
    """Verilen dosyadan liste döndür. Yoksa boş liste."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_json(path: Path, data: list) -> None:
    """Listeyi JSON olarak diske yaz."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# -------------------------------------------------
# Flask uygulaması
# -------------------------------------------------
app = Flask(__name__)


# -------------------------------------------------
# ANA SAYFA
# -------------------------------------------------
@app.route("/")
def home():
    """
    Ana sayfa. Şu an index.html'i açıyor.
    İstersen burada direkt prepare sayfasına da yönlendirebiliriz.
    """
    return render_template("index.html")


# -------------------------------------------------
# GÖNDERİ OLUŞTUR (prepare.html)
# -------------------------------------------------
@app.route("/prepare", methods=["GET", "POST"])
@app.route("/create", methods=["GET", "POST"])
def create_post():
    """
    Gönderi oluşturma ekranı.
    GET  -> prepare.html formunu gösterir.
    POST -> formdan gelen veriyi zamanlanmış veya taslak olarak kaydeder.
    """

    if request.method == "POST":
        # Hangi butona basıldığını anlamak için:
        #  - Taslak Olarak Kaydet  -> action = "draft"
        #  - Gönderiyi Oluştur     -> action = "submit"
        action = request.form.get("action", "").strip()

        text = request.form.get("post_text", "").strip()
        hashtags = request.form.get("hashtags", "").strip()
        platforms = request.form.getlist("platforms")           # checkbox listesi
        fmt = request.form.get("format", "normal")              # radio
        schedule_at = request.form.get("schedule_at", "").strip()
        aspect_ratio = request.form.get("aspect_ratio", "").strip()

        # Tek bir ortak obje yapısı
        post_obj = {
            "text": text,
            "hashtags": hashtags,
            "platforms": platforms,
            "format": fmt,
            "schedule_at": schedule_at,
            "aspect_ratio": aspect_ratio,
        }

        # Taslak kaydı
        if action == "draft":
            drafts = load_json(DRAFTS_FILE)
            drafts.append(post_obj)
            save_json(DRAFTS_FILE, drafts)
            return redirect(url_for("drafts"))

        # Varsayılan: zamanlanmış gönderi kaydı
        scheduled = load_json(SCHEDULED_FILE)
        scheduled.append(post_obj)
        save_json(SCHEDULED_FILE, scheduled)
        return redirect(url_for("tasks"))

    # GET isteği: sadece formu göster
    return render_template("prepare.html")


# -------------------------------------------------
# ZAMANLANMIŞ GÖNDERİLER (tasks.html)
# -------------------------------------------------
@app.route("/tasks")
def tasks():
    """
    Zamanlanmış gönderilerin listesi.
    tasks.html içinde 'posts' olarak kullanılıyor.
    """
    scheduled_posts = load_json(SCHEDULED_FILE)
    return render_template("tasks.html", posts=scheduled_posts)


# -------------------------------------------------
# TASLAKLAR / HAZIRLANANLAR (drafts.html)
# -------------------------------------------------
@app.route("/drafts")
def drafts():
    """
    Taslak gönderilerin listesi.
    drafts.html içinde 'posts' olarak kullanılıyor.
    """
    draft_posts = load_json(DRAFTS_FILE)
    return render_template("drafts.html", posts=draft_posts)


# -------------------------------------------------
# DOSYA YÜKLEME ÖRNEK ENDPOINT
# -------------------------------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    """
    İleride medya dosyalarını göstermek için kullanabileceğin endpoint.
    Şimdilik sadece dosya adını döndürüyor ki uygulama patlamasın.
    """
    return f"File: {filename}"


# -------------------------------------------------
# GERÇEK AI ENDPOINT'LERİ
# -------------------------------------------------
def ensure_client():
    if client is None:
        return None, jsonify({"error": "OpenAI client kullanılamıyor. 'openai' paketini kur ve OPENAI_API_KEY tanımla."}), 500
    if not os.environ.get("OPENAI_API_KEY"):
        return None, jsonify({"error": "OPENAI_API_KEY ortam değişkeni tanımlı değil."}), 500
    return client, None, None


@app.route("/api/ai_text", methods=["POST"])
def api_ai_text():
    """
    Gönderi metni için yapay zeka ile yeni bir öneri üretir.
    Body: { "lang": "tr", "base_text": "..." }
    """
    cli, err_resp, status = ensure_client()
    if err_resp:
        return err_resp, status

    data = request.get_json(silent=True) or {}
    lang = data.get("lang", "tr")
    base_text = data.get("base_text", "").strip()
    platforms = data.get("platforms", [])
    tone = data.get("tone", "default")

    # Kullanıcıya görünmeyecek ama modele giden açıklama
    system_msg = (
        "You are an assistant that writes short, social-media-friendly post texts. "
        "Keep it under 2–3 sentences. Return only the text, no explanations."
    )

    # Dil ve ton bilgisi ile prompt
    user_prompt = f"Language code: {lang}\n"
    if platforms:
        user_prompt += f"Target platforms: {', '.join(platforms)}\n"
    if tone != "default":
        user_prompt += f"Tone: {tone}\n"
    if base_text:
        user_prompt += f"Base idea from user: {base_text}\n"
        user_prompt += "Rewrite/extend this idea into a clean, engaging post."
    else:
        user_prompt += "Create a fresh, engaging social media post from scratch."

    try:
        completion = cli.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ],
        )
        suggestion = completion.choices[0].message.content.strip()
        return jsonify({"suggestion": suggestion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai_hashtags", methods=["POST"])
def api_ai_hashtags():
    """
    Hashtag önerisi üretir.
    Body: { "lang": "tr", "base_text": "...", "platforms": ["instagram", ...] }
    """
    cli, err_resp, status = ensure_client()
    if err_resp:
        return err_resp, status

    data = request.get_json(silent=True) or {}
    lang = data.get("lang", "tr")
    base_text = data.get("base_text", "").strip()
    platforms = data.get("platforms", [])

    system_msg = (
        "You are an assistant that generates social media hashtags. "
        "Return 10–20 hashtags, separated by spaces, no explanations, no numbering."
    )

    user_prompt = f"Language code: {lang}\n"
    if platforms:
        user_prompt += f"Target platforms: {', '.join(platforms)}\n"
    if base_text:
        user_prompt += f"Post text: {base_text}\n"
    user_prompt += (
        "Generate relevant, trending but not spammy hashtags for this post. "
        "Output only hashtags, separated by spaces."
    )

    try:
        completion = cli.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ],
        )
        suggestion = completion.choices[0].message.content.strip()
        return jsonify({"suggestion": suggestion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------
# Uygulama giriş noktası
# -------------------------------------------------
if __name__ == "__main__":
    # debug=True: geliştirme aşamasında iyi, prod'da False yapılır
    app.run(debug=True)

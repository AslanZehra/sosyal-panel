# MySocial Panel

MySocial Panel, sosyal medya icerigini tek bir panelden yonetmek icin hazirlanan bir web uygulamasidir.

Su anki hizli launch kapsami:

- Facebook + Instagram
- Simdi Gonder + Tek Sefer planlama
- Kuyruk + Arsiv + Hesap baglama + Worker log takibi

Bu repo su an "tek yonetici paneli" seviyesindedir. Cok kullanicili SaaS yapisi henuz hedef kapsamda degildir.

## Launch'ta hazir olanlar

- Facebook ve Instagram icin gercek publish akisi
- Metin + medya ile gonderi olusturma
- Tek sefer planlama
- Kuyruk, arsiv ve worker log ekranlari
- Meta OAuth ile hesap baglama
- Render uzerinden production deploy

## Teknolojiler

- Backend: Python, Flask
- Frontend: HTML, CSS, JavaScript
- Diger: JSON tabanli veri saklama

## Lokal kurulum

```bash
git clone https://github.com/AslanZehra/sosyal-panel.git
cd sosyal-panel

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

python3 main.py
python3 static/worker.py
```

## Production deploy

En kisa production yolu Render blueprint kullanmaktir:

- `render.yaml` ile web service olustur
- `APP_STORAGE_DIR`, `META_*`, `PUBLIC_BASE_URL` env'lerini gir
- `FLASK_SECRET_KEY` ekle
- Meta callback/domain ayarlarini production domaine tasi
- Detayli adimlar icin [DEPLOY.md](DEPLOY.md)

## Launch disinda biraktiklarimiz

- X, YouTube, TikTok
- Interval/campaign planlama
- Ozel hedef secimi
- Cok kullanicili hesap yonetimi

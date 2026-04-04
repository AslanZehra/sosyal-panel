# Production Deploy (Render)

Bu proje JSON dosyalari (`data/`) ve yuklenen medya (`uploads/`) kullandigi icin
tek servis icinde `web + worker` beraber calistirilir.

## 1) Render'da yeni Web Service olustur
- Repo: `sosyal-panel`
- Runtime: `Python`
- Build Command:
  - `pip install -r requirements.txt`
- Start Command:
  - `bash scripts/start_web_with_worker.sh`

## 2) Persistent disk ekle
- Render service ayarlarinda disk ekle.
- `Mount Path`: `/var/data`
- `Size`: en az `1 GB`

## 3) Environment Variables
- `APP_STORAGE_DIR=/var/data/mysocial`
- `META_APP_ID=...`
- `META_APP_SECRET=...`
- `META_REDIRECT_URI=https://<render-domain>/auth/meta/callback`
- `META_GRAPH_VERSION=v19.0`
- `META_LOGIN_SCOPE=pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish`
- `PUBLIC_BASE_URL=https://<render-domain>`
- `OPENAI_API_KEY=...` (opsiyonel, yoksa fallback calisir)

## 4) Meta panelde redirect guncelle
- Facebook Login > Settings:
  - `Valid OAuth Redirect URI`:
    - `https://<render-domain>/auth/meta/callback`

## 5) Deploy sonrasi hizli test
1. `https://<render-domain>/accounts` ac.
2. `Meta ile Baglan` ile yetkiyi onayla.
3. `Instagram ID Yenile` tikla.
4. `create` ekranindan test gonderisi at.
5. `queue`, `worker-logs`, `archive` ekranlarini kontrol et.

## Notlar
- Free plan uyuyabildigi icin zamanli gonderiler kacabilir.
- Stabil kullanim icin uyumayan (always-on) plan gerekir.

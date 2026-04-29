# Production Deploy (Render)

Bu proje JSON dosyalari (`data/`) ve yuklenen medya (`uploads/`) kullandigi icin
tek servis icinde `web + worker` beraber calistirilir.

## 1) En kisa yol: Blueprint ile kur
- Repo'yu Render'a bagla.
- Root'taki `render.yaml` dosyasini kullanarak service olustur.
- Service tipi `web`, worker ayni servis icinde `scripts/start_web_with_worker.sh` ile ayağa kalkar.

## 2) Alternatif: Elle Web Service olustur
- Repo: `sosyal-panel`
- Runtime: `Python`
- Build Command:
  - `pip install -r requirements.txt`
- Start Command:
  - `bash scripts/start_web_with_worker.sh`

## 3) Persistent disk ekle
- Render service ayarlarinda disk ekle.
- `Mount Path`: `/var/data`
- `Size`: en az `1 GB`

## 4) Environment Variables
- `APP_STORAGE_DIR=/var/data/mysocial`
- `META_APP_ID=...`
- `META_APP_SECRET=...`
- `META_REDIRECT_URI=https://<render-domain>/auth/meta/callback`
- `META_GRAPH_VERSION=v19.0`
- `META_LOGIN_SCOPE=pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish`
- `PUBLIC_BASE_URL=https://<render-domain>`
- `FLASK_SECRET_KEY=uzun-rastgele-bir-deger`
- `OPENAI_API_KEY=...` (opsiyonel, yoksa fallback calisir)

## 5) Meta panelde redirect guncelle
- Facebook Login > Settings:
  - `Valid OAuth Redirect URI`:
    - `https://<render-domain>/auth/meta/callback`
- App Settings > Basic:
  - `App Domains`:
    - `<render-domain>`

## 6) Deploy sonrasi hizli test
1. `https://<render-domain>/accounts` ac.
2. `https://<render-domain>/register` uzerinden ilk kullaniciyi olustur.
3. Giris yaptiktan sonra `Meta ile Baglan` ile yetkiyi onayla.
4. `Instagram ID Yenile` tikla.
5. `create` ekranindan test gonderisi at.
6. `queue`, `worker-logs`, `archive` ekranlarini kontrol et.

## Hizli launch scope
- Ilk yayin icin sadece `Facebook + Instagram` acik tutulmali.
- Ilk yayin icin sadece `Simdi Gonder` ve `Tek Sefer` kullanilmali.
- `X / YouTube / TikTok`, `campaign`, `interval`, ozel hedef secimi ikinci faza birakilmali.

## Yayina cikmadan hemen once
1. Render domain calisiyor mu kontrol et.
2. `META_REDIRECT_URI` ve Meta paneldeki callback birebir ayni mi kontrol et.
3. `/accounts` ekraninda Meta baglantisini tekrar kur.
4. `/create -> /queue -> /archive` zincirini tek test postuyla dogrula.
5. Sorunsuzsa ancak ondan sonra custom domain bagla.

## Notlar
- Free plan uyuyabildigi icin zamanli gonderiler kacabilir.
- Stabil kullanim icin uyumayan (always-on) plan gerekir.

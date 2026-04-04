# Kaldigimiz Yer (2026-03-13 15:45 civari)

## Tamamlananlar
- Meta OAuth akisi calisiyor.
- Facebook login/callback basarili oldu.
- `data/accounts.json` icinde Facebook hesabı bagli durumda:
  - status: connected
  - page_id kayitli
  - page_access_token kayitli
- `pages_found: 1` donen basarili callback goruldu.

## Son gorulen hata ve neden
- Gonderim denemesinde worker hatasi:
  - `publish_error: (#283) Requires pages_read_engagement permission to manage the object`
- Neden:
  - OAuth scope yetersizdi (yalnizca `pages_show_list` ile bagli kalinmisti).

## Bugun yapilan teknik duzeltme
- `main.py` icinde `META_LOGIN_SCOPE` guncellendi:
  - `pages_show_list,pages_read_engagement,pages_manage_posts`
- Flask restart edildi.

## Siradaki tek kritik adim (kullanici tarafi)
1. `/accounts` ac.
2. `Meta ile Baglan` tikla.
3. Facebook ekraninda `Onceki ayarlari duzenle` linkine tikla.
4. Izinlerde sayfa yetkilerini acik birak:
   - pages_show_list
   - pages_read_engagement
   - pages_manage_posts
5. `Tekrar baglan` ile bitir.

## Son test sonucu (2026-03-07 00:32)
- OAuth callback basarili ve token scope dogrulandi:
  - pages_show_list
  - pages_read_engagement
  - pages_manage_posts
- Gercek Facebook post testi basarili:
  - post id: `facebook:1090443410810890_122101754829213708`
  - `data/archive.json` icinde `status: sent` ve `delivered_platforms: [facebook]`

## Otomatik gonderim guclendirme (2026-03-07 01:30)
- `static/worker.py` iyilestirildi:
  - kalici worker log dosyasi: `data/worker.log`
  - retry backoff eklendi: 2/4/8/16/30 dk
  - `needs_auth` retry araligi 15 dk yapildi (log spam azaltildi)
  - item log tekrarlarinda `repeat` sayaci eklendi
  - `last_error` alani queue/archive item'larina eklendi
- Web panelde yeni sayfa:
  - `/worker-logs` (son 300 satir worker log goruntusu)
- Nav'a `Worker Log` menusu eklendi.

## Son durum (2026-03-07 01:57)
- Kuyruk davranisi dogrulandi:
  - Worker kapaliyken `Simdi Gonder` kayitlari `/queue` icinde bekliyor.
  - Worker acilinca kayitlar kuyruktan alinip gonderiliyor.
- Canli test sonucu:
  - Kuyruktaki 2 adet `facebook` gonderisi basariyla gitti.
  - `data/queue.json` tekrar bos (`0`).
  - `data/archive.json` icinde son iki kayit `status: sent`.
  - Worker log kayitlari `data/worker.log` icinde:
    - `item_sent id=0458df...`
    - `item_sent id=823762...`

## Yarin ilk adim
1. Bu stabil durumda devam:
   - `/accounts` bagli kontrolu
   - `/worker-logs` hizli kontrol
2. Sonra yeni asamaya gec:
   - Instagram gercek entegrasyonu (ig_business_id + gercek post akisi)

## Instagram entegrasyon ilerlemesi (2026-03-13)
- `accounts` ekranina yeni buton eklendi:
  - `Instagram ID Yenile` (`/auth/meta/refresh-instagram`)
- Backend eklendi:
  - Facebook Page uzerinden `instagram_business_account` / `connected_instagram_account` cekip `data/accounts.json` gunceller.
- Worker eklendi:
  - Instagram icin gercek Graph API publish akisi:
    - `/{ig_business_id}/media` (image_url + caption)
    - `/{ig_business_id}/media_publish`
  - `PUBLIC_BASE_URL` yoksa `META_REDIRECT_URI` domainiyle medya URL olusturma fallback'i eklendi.
  - Instagram icin gorsel zorunlulugu kontrolu eklendi.

## Mevcut durum
- `Instagram ID Yenile` sonucu:
  - `Bu Facebook sayfasina bagli Instagram Business hesabi bulunamadi.`
- Bu nedenle Instagram halen aktif degil:
  - `instagram.status = not_connected`
  - `instagram.ig_business_id = ""`

## Sonraki net adim
1. Facebook Page'e bir Instagram Professional (Business/Creator) hesabi bagla.
2. Sonra `/accounts` -> `Instagram ID Yenile`.
3. `ig_business_id` dolunca `/create` uzerinden instagram + gorsel ile test gonderisi yap.

## Sonraki test adimlari
1. Terminal 1:
   - `cd /Users/zehraaslan/Desktop/sosyal-panel`
   - `source venv/bin/activate`
   - `python3 main.py`
2. Terminal 2:
   - `ngrok http 5050`
3. Tarayicida:
   - `http://127.0.0.1:5050/accounts` ac
   - Meta baglantisini yeniden onayla (yukaridaki kritik adim)
4. Test:
   - `/create` uzerinden kisa bir Facebook test gonderisi olustur
   - worker loglarinda hata yerine basarili gonderim gor
   - `/archive` sayfasina dustugunu kontrol et

## Sonraki hedef
- Stabilizasyon + otomatik gonderim dogrulama tamamla.
- Ardindan Instagram adimi ve sonra X/YouTube/TikTok entegrasyon sirasina gec.

## Guncel durum (2026-03-13 19:50)
- Instagram baglantisi artik aktif:
  - `instagram.status = connected`
  - `instagram.ig_business_id = 17841443249726766`
- Canli Instagram gonderisi basarili:
  - archive kaydi: `id=f6396f852ac54a8c8768c34495050c10`
  - sonuc: `published: instagram:18096112556514861`
- Canli coklu platform gonderisi basarili (Facebook + Instagram):
  - archive kaydi: `id=f5be40a469894fc7b64cc36bae8bc126`
  - facebook: `1090443410810890_122113641279213708`
  - instagram: `18089785802331322`
- Worker acik oldugunda kuyruktan alip gonderiyor.

## Son yapilan iyilestirme
- `static/worker.py` icinde Instagram publish adimina gecici bekleme/retry eklendi.
- Amaç:
  - `Media ID is not available` benzeri gecici hatalarda ilk denemede daha dayanikli olmak.

## Bir sonraki adim
1. Web app'i production ortamina tasima (domain + SSL + sunucu).
2. Mobil paketleme karari:
   - hizli yol: webview/kaplama (MVP)
   - saglam yol: React Native/Flutter istemci
3. Store oncesi checklist:
   - gizlilik politikasi
   - KVKK/GDPR metinleri
   - crash/log izleme
   - test hesaplari ve test senaryolari

## Kayit noktasi (2026-03-13 20:13)
- Son onaylanan durum:
  - Facebook + Instagram gercek gonderi akisi calisiyor.
  - Queue bos, gonderiler archive'a dusuyor.
- Sonraki oturumda direkt baslanacak is:
  1. Production deploy dosyalari (web + worker)
  2. Canli ortama alma (domain/SSL)

## Deploy hazirligi (2026-03-27)
- Production icin dosyalar eklendi:
  - `Procfile` (`web: bash scripts/start_web_with_worker.sh`)
  - `scripts/start_web_with_worker.sh` (worker + gunicorn beraber)
  - `DEPLOY.md` (Render adimlari)
- Storage path env destekleri eklendi:
  - `APP_STORAGE_DIR` ile `data/` ve `uploads/` production diske tasinabilir.
- `main.py` artik `PORT` env ile aciliyor.

## Yeni ozellikler (2026-03-27)
- Planlama:
  - Yeni mod: `campaign` (gunde N paylasim + tarih araligi).
  - Ornek: `20/gun` secilince otomatik `72 dk` aralik hesaplanir.
- Hedef secimi:
  - `targets` alani eklendi (or: `facebook:page:<id>`, `facebook:group:<id>`, `instagram:self`).
  - Facebook publish, hedef listesine gore sayfa/grup feed'e post atmayi dener.
- Instagram:
  - Medya URL preflight dogrulamasi eklendi (content-type kontrolu).
  - Tekli image + tekli video + coklu medya (carousel) akisi eklendi.
  - Graph API timeout/connection hatalarinda ic retry eklendi.
- Dogruluk:
  - X/YouTube/TikTok icin sahte `simulated sent` kaldirildi.
- Bu platformlarda entegrasyon hazir degilse `needs_auth` doner.

## Guncel kayit (2026-04-03 gecesi)
- Runtime:
  - `main.py` ve `static/worker.py` tekrar canli acildi.
  - Onceki campaign kaydindan gelen "gecmis run'lari tek tek yetistirme" kuyruk sisirmesi tespit edildi.
- Kritik duzeltme:
  - `static/worker.py` icinde `next_run_skip_missed(...)` eklendi.
  - `interval` ve `interval_range` artik kacirilan eski slotlari tek tek kuyruga atmiyor; bir sonraki gecerli zamana zipliyor.
  - Son kontrol: `data/queue.json` uzunlugu `0`, campaign `next_run_at` gelecege atlandi (`2026-04-04T00:48:00`).
- Facebook coklu medya:
  - `publish_facebook` guncellendi.
  - Coklu foto artik album olarak tek post (`attached_media`) gonderebiliyor.
  - Tek video icin `/videos` akisi eklendi.
  - Karisik/coklu video durumda net hata mesaji doner (sessiz bozulma yok).
- Story/UX netlestirme:
  - `templates/prepare.html` + `static/app.js` guncellendi.
  - Story secilince sadece Instagram aktif kalir (diger platform checkbox'lari disable).
  - Boyunca Story'nin Facebook'a normal post gibi gitmesi engellenir.
- Gozlem:
  - Worker logda cok sayida eski `facebook ... fail:network` kaydi var; bunlar gecmis backlog denemeleri.
  - Yeni scheduler mantigi ile tekrar flood beklenmiyor.

## Sonraki adim (bir sonraki oturum)
1. UI'dan canli test:
   - `create`: format `story` sec -> sadece Instagram aktif mi kontrol.
   - Birden fazla foto secip Facebook normal post at -> archive logda `ok:album` beklenir.
2. X medya destegi:
   - su an text-only; media pipeline (upload+attach) eklenecek.
3. YouTube/TikTok:
   - gercek OAuth + publish endpoint entegrasyonlari (simulasyon yok).

## Guncel kayit (2026-04-04 gece)
- Story failure root-cause netlesti:
  - Worker log: `medya URL erişim hatası ... Failed to resolve 'unstamped-nonarguable-aubri.ngrok-free.dev'`
  - Yani queue item'daki medya URL eski/ngrok DNS dusmus domaine bakiyordu.
- Kod iyilestirmeleri:
  - `post_with_retry` artik bos `network:` yerine exception class + detay yaziyor.
  - `try_publish` icinde story guvenlik normalize eklendi:
    - Story item'inda platform listesi otomatik `["instagram"]` olacak sekilde normalize edilir.
    - Story item'inda 1'den fazla medya varsa ilkine dusurulur.
- Runtime:
  - main/worker yeniden baslatildi.
  - Queue su an bos.

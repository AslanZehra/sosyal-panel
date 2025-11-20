# MySocial – Sosyal Medya Gönderi Hazırlama & Taslak Paneli

Bu proje, tek bir panelden Instagram, Facebook, X (Twitter), YouTube ve TikTok için
gönderi hazırlamayı, taslak kaydetmeyi ve planlamayı amaçlayan bir **Flask tabanlı web uygulamasıdır.**

## Özellikler

- ✏️ Tek gönderi hazırlama ekranı
  - Gönderi metni
  - Platform seçimi (Instagram, Facebook, X, YouTube, TikTok)
  - Format seçimi (Normal, Short/Reels, Story)
  - Aspect ratio önerileri (platforma göre)
  - Basit medya dosyası seçimi (şimdilik sadece isimler tutuluyor)
  - Zamanlama (şimdi paylaş / ileri tarih planlama)

- 💾 Taslak sistemi
  - Gönderiyi taslak olarak kaydetme
  - Tüm taslakları listeleme
  - Taslaktan düzenleme ekranına geri dönme
  - Hangi platformlar için hazırlandığını görme

- 🧪 Multi-Post Beta
  - Tek bir “temel metin”den yola çıkarak her platform için ayrı metin üretme
  - Her platform için ayrı textarea ve ipucu metinleri
  - Ortak zamanlama seçeneği
  - Tüm çoklu gönderiyi özetleyen beta önizleme

## Teknolojiler

- Python 3
- Flask
- SQLite (basit yerel veritabanı)
- HTML / Jinja2 template
- Vanilla JavaScript (`app.js`, `multi.js`)
- CSS (dark theme + neon stil)

## Kurulum

```bash
# Projeyi klonla
git clone <REPO_URL> mysocial
cd mysocial

# Sanal ortam oluştur ve aktif et (isteğe bağlı)
python -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Uygulamayı çalıştır
python main.py

# MySocial Panel

MySocial Panel, tek bir arayüz üzerinden birden fazla sosyal medya hesabını yönetmeyi hedefleyen bir web uygulamasıdır.  
Amaç; örneğin Instagram, Facebook, YouTube Shorts vb. platformlar için **tek ekrandan** gönderi planlama, taslak kaydetme ve toplu paylaşım yapabilmektir.

## Özellikler (Planlananlar)

- 📌 Çoklu platform seçimi (Instagram, Facebook, YouTube Shorts vb.)
- 📝 Gönderi taslağı oluşturma (metin + görsel)
- 💾 Taslakları kaydedip daha sonra düzenleyebilme
- ⏰ Geleceğe tarih/saat vererek gönderi planlama
- 🌓 Karanlık tema + neon detaylı modern arayüz
- 📊 Gönderi listesi: Durum (Taslak / Zamanlandı / Paylaşıldı) ve platform etiketleri
- 👥 Birden fazla hesap için altyapı (ileriki versiyonlarda)

## Teknolojiler

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Diğer:** JSON tabanlı basit veri saklama (ileride veritabanına taşınacak)

## Kurulum

Aşağıdaki adımlar macOS üzerinde test edilmiştir.

```bash
# 1. Projeyi klonla
git clone https://github.com/AslanZehra/sosyal-panel.git
cd sosyal-panel

# 2. Sanal ortam oluştur ve aktif et
python3 -m venv venv
source venv/bin/activate

# 3. Gerekli paketleri yükle
pip install -r requirements.txt

# 4. Uygulamayı çalıştır
python main.py

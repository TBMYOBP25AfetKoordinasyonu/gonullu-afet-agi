# Gönüllü Afet Koordinasyon Ağı

Flask tabanlı afet yönetimi ve gönüllü koordinasyon platformu. Afet durumlarında yardım talep edenleri, gönüllüleri ve koordinatörleri bir araya getiren kapsamlı bir web uygulamasıdır.

## 🚀 Özellikler

### 👥 Kullanıcı Rolleri ve Yetkileri

#### 🔥 **Afetzede (Requester)**
- Yardım talebi oluşturma
- Konum belirleme (GPS veya manuel)
- Talep durumu takibi
- Profil yönetimi

#### 🙋‍♂️ **Gönüllü (Volunteer)**
- 50km çapında yakın yardım taleplerini görüntüleme
- Harita üzerinde afet bölgelerini görme
- Yardım teklifinde bulunma ve iptal etme
- Koordinatör olmak için başvuru yapma
- Mesafe bazlı talep sıralaması

#### 👨‍💼 **Koordinatör (Coordinator)**
- Tüm yardım taleplerini görüntüleme ve yönetme
- Gönüllüleri görevlere atama (çoklu seçim)
- Talep durumlarını güncelleme (beklemede, devam ediyor, tamamlandı, iptal)
- İnteraktif harita ile bölgesel görünüm
- Mesafe hesaplamalı gönüllü önerisi

#### 🔐 **Admin**
- Koordinatör başvurularını onaylama/reddetme
- Kullanıcı yönetimi (engelleme/engel kaldırma)
- Rol yükseltmeleri (gönüllü → koordinatör)
- Sistem istatistikleri görüntüleme
- Koordinatör onaylarını geri çekme

### 🗺️ Harita ve Konum Özellikleri

- **Leaflet.js** entegrasyonu ile interaktif haritalar
- Gerçek zamanlı GPS konum alma
- Manuel adres seçimi (il, ilçe, mahalle)
- Afet türüne göre renkli işaretleme
- Mesafe hesaplaması (Haversine formülü)
- Zoom ve filtreleme özellikleri

### 📊 Talep Yönetim Sistemi

- **Durum Takibi**: Beklemede → Devam Ediyor → Tamamlandı
- **Atama Sistemi**: Koordinatör tarafından gönüllü ataması
- **Mesafe Optimizasyonu**: En yakın gönüllü önerisi
- **Çoklu Gönüllü**: Bir talebe birden fazla gönüllü ataması
- **Otomatik Bildirimler**: Durum değişikliklerinde flash mesajları

### 🔄 Kullanıcı Deneyimi

- **Profil Yönetimi**: Kişisel bilgi güncelleme
- **Rol Geçişi**: Gönüllü → Koordinatör başvuru süreci
- **Responsive Tasarım**: Mobil uyumlu arayüz
- **Güvenlik**: Session tabanlı kimlik doğrulama
- **Veritabanı**: SQLite ile veri persistency

## 📱 Sayfa Yapısı

### 🏠 **Ana Sayfa**
- Hızlı yardım talebi ve gönüllü kayıt linkleri
- Kullanıcı giriş/kayıt seçenekleri
- Platform hakkında bilgilendirme

### 🆘 **Yardım Talebi Sayfası**
- Afet türü seçimi
- Otomatik GPS konum alma
- Manuel konum seçimi (il/ilçe/mahalle)
- Ek bilgi ekleme alanı

### 📊 **Dashboard Sayfaları**

#### Gönüllü Paneli
- Yakındaki yardım talepleri (50km)
- Harita görünümü ve filtreleme
- Mesafe bilgisi ile sıralama
- Kabul edilen görevler listesi

#### Koordinatör Paneli
- Tüm yardım taleplerini görüntüleme
- Gönüllü atama sistemi (çoklu seçim)
- Durum güncelleme araçları
- Mesafe bazlı gönüllü önerisi

#### Admin Paneli
- Kullanıcı istatistikleri
- Koordinatör başvuru yönetimi
- Kullanıcı rol yönetimi
- Sistem genel bakış

### 👤 **Profil Sayfası**
- Kişisel bilgi güncelleme
- Talep/görev geçmişi
- Koordinatör başvuru formu
- Durum bildirimleri

## 🛠️ Teknik Altyapı

### Backend
- **Flask** - Python web framework
- **SQLite** - Veritabanı sistemi
- **Werkzeug** - Şifre güvenliği
- **WTForms** - Form doğrulama

### Frontend
- **HTML5/CSS3** - Modern web standartları
- **JavaScript** - İnteraktif özellikler
- **Leaflet.js** - Harita entegrasyonu
- **Font Awesome** - İkon sistemi

### Veritabanı Şeması
- **users** - Kullanıcı bilgileri ve roller
- **help_requests** - Yardım talepleri
- **assignments** - Gönüllü atamaları
- **locations** - Coğrafi konum verileri
- **coordinator_requests** - Koordinatör başvuruları

## 🔧 Kurulum ve Çalıştırma

```bash
# Depoyu klonla
git clone [repository-url]
cd gonullu-afet-agi

# Bağımlılıkları yükle
pip install flask werkzeug wtforms

# Veritabanını oluştur
python -c "import sqlite3; conn = sqlite3.connect('data.db'); conn.executescript(open('schema.sql').read()); conn.close()"

# Uygulamayı başlat
python app.py
```

Uygulama `http://localhost:5000` adresinde çalışacaktır.

## 📈 Sistem Akışı

1. **Kayıt/Giriş** - Kullanıcı rolüne göre hesap oluşturma
2. **Yardım Talebi** - Afetzede tarafından talep oluşturma
3. **Gönüllü Bildirim** - 50km çapında uygun gönüllülere gösterim
4. **Koordinatör Müdahale** - Talep yönetimi ve gönüllü ataması
5. **Görev Tamamlama** - Yardım sürecinin sonlandırılması
6. **Raporlama** - Admin panel üzerinden istatistik takibi

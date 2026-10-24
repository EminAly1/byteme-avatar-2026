# Görev 8 — Android doğrulama raporu

Rapor tarihi: **25 Ekim 2026, Europe/Istanbul**. Başlangıç main `3626c99` (PR #1–#10 normal merge commit’leri geçmişten doğrulandı). Çalışma branch’i feature/android-sales-app. Yalnız android/ kaynak/dokümanları değiştirildi; backend/frontend/ML/database/tests ve ortak checklist değiştirilmedi.

## Sonuç ve test ayrımı

| Kontrol | Gerçek sonuç |
| --- | --- |
| `./gradlew test` | **16 farklı host testi**, debug ve release için **32 çalıştırma; 0 hata, 0 skip** |
| `./gradlew lintDebug` | Başarılı; son XML raporunda **0 lint issue** |
| `./gradlew assembleDebug` | Başarılı, kurulabilir debug APK üretildi |
| `./gradlew assembleDebugAndroidTest` | Başarılı, cihaz test APK’si üretildi |
| API 28 AOSP / x86_64 cihaz koşusu | **3/3 geçti, 0 skip**: gerçek backend/UI satışı + SQLite kalıcılığı + Android Keystore |
| Ek API 28 offline/kalıcılık koşusu | **3/3 geçti, 0 skip**: güçlendirilmiş SQLite onay/anahtar testi, Keystore ve Wi‑Fi/mobil veri kapalı UI taslağı |
| Farklı cihaz test metodu sayısı | **4**; iki koşuda 3+3 çalıştırma, iki kalıcılık/güvenlik testi tekrarlandı |
| Bağımsız APK açılışı ve süreç yeniden başlatma | Keystore’dan bağlantı geri yüklendi, API kataloğu okundu; aynı outbox anahtarları, gövdeler ve durumlar korundu |
| Gerçek ekran incelemesi | 390×844 light; 360×640 mantıksal boyutta dark; form/boşluk/kart/nav ve hata ekranları kontrol edildi |

Host testleri **Robolectric + native SQLite + MockWebServer** kullanır; gerçek Android cihaz veya MySQL testi diye sunulmaz. ComposeSmokeTest 360×640 mantıksal ekranda gerçek Room kaydından form/özet çizimini test eder. API 28 Android Emulator yazılım TCG emülasyonudur; fiziksel cihaz değildir. Gerçek backend testi FastAPI + **MySQL 8.0.46** üzerinde ayrı `avatar_android_demo_test` veritabanıyla çalıştırıldı.

Ham sonuç özetleri: [build.txt](validation/build.txt), [ilk cihaz koşusu](validation/connected-sale.txt), [offline/kalıcılık koşusu](validation/connected-offline.txt), [makine okunabilir sonuçlar](validation/results.json). Ham loglardaki UTC/emülatör saatleri kendi ortam saatleridir; rapor tarihi kullanıcı Türkiye bağlamıdır.

## Doğrulanan senaryolar

- Room ürün/lot/stok/müşteri FK’leri; dosya kapat/aç sonrası taslak, UUID anahtar, gövde ve onay kaydının korunması. App DB’sinde destructive migration yoktur.
- Katalog cursor’larının sonuna kadar okuma; cursor döngüsünde eski önbelleğin korunması. Ürün/lot/konum/müşteri eşleşmesi, kg/paket/adet ayrımı ve Decimal metin doğrulaması.
- Onaydan önce kalıcı key/body; aynı taslağı kuyruğa alırken ikinci key üretmeme; bağlantı kopması ve süreç kesilmesinde aynı bayt gövde ve key ile yeniden gönderim.
- Başarı cevabının gerçek satış/satır/lot/ürün/konum/miktar/fiyat/hareket kimlikleriyle eşleşmesi; onay snapshot’ı ve outbox durumunun Room transaction’ında yazılması.
- Yerel stoktan tahminî düşüm yapılmaması. 409 LOT_BLOCKED/INSUFFICIENT_STOCK, 401, 422 ve 503 ayrı durum/mesajları. Kalıcı çatışmalar kör tekrar edilmez; auth hatası yeniden kullanıcı onayı ister.
- Sahte/uyuşmayan başarı cevabı kesin satış sayılmaz. Başka endpoint’e geçildiğinde eski onaylı istek yeni sunucuya gönderilmez.
- Android Keystore AES-GCM: depolanan SharedPreferences değerinde düz anahtar yok; yeni SecureSettings örneği anahtarı geri açar. Debug loopback HTTP / release HTTPS sınırı host testinde denetlendi.
- Wi‑Fi ve mobil veri gerçekten kapatıldı: önbellekten lot seçildi, formdan taslak kaydedildi; outbox ve onaylı satış sayısı artmadı, stok aynı kaldı. Radyo ayarları finally içinde geri açıldı. Bu test fiziksel telefonda yapılmadı.

401/422/503, yetersiz stok ve belirsiz yanıt durumlarının Android eşlemesi MockWebServer testidir. Gerçek cihaz/backend koşusu özellikle başarılı satış, idempotent tekrar ve recall blokajını kapsar. Gerçek cihazda proxy’nin cevabı düşürdüğü ağ arızası veya zorlanmış backend kesintisi test edilmedi.

## Gerçek Kotlin → FastAPI → MySQL demosu

Mevcut app.demo_cutting, kaynaklar değiştirilmeden kullanıldı. Quantity kesiminin butunda eski demo satışı vardır; mobil uygulama **value kesiminden çıkan satılmamış 6 kg but lotunu** kullandı. But/omuz/sırt/kaburga/kıyma ağırlıkları, referans fiyatlar ve fire sınıfı PDF’de verilmediği için kurgusal demo etiketi korunur.

1. Özel mode 0600 fixture /tmp içinde üretildi, APK’ye veya Gradle argümanına gömülmedi. Debug cihazın uygulamaya özel alanına aktarıldı; sonrasında cihazdan silindi. Hazırlama aracı repository içine gizli fixture yazmayı reddeder; bu sınır ayrıca çalıştırılarak doğrulandı.
2. Gerçek Compose ekranından stok/lot, müşteri, **1 kg** ve **25 EUR/kg** seçilip özet onaylandı.
3. Backend’in gerçek satış/satır/StockMovement UUID’leri Room’a kaydedilip ekranda gösterildi. Sunucu stoğu **6.000000 → 5.000000 kg** oldu.
4. Kotlin API istemcisi kalıcı outbox gövdesini aynı key ile tekrar gönderdi: aynı server satış UUID’si döndü, stok **5.000000** kaldı.
5. Kaynak kuzu lotuna gerçek recall uygulandı. Android’in hâlâ blokesiz eski önbelleğinden yeni istek gönderildi: **409 LOT_BLOCKED**, NEEDS_ACTION, hata/taslak korundu; alternatif lot seçilmedi. Satış veya stok hareketi oluşmadı.
6. Ek gerçek offline testinin ardından uygulama force-stop edilip yeniden açıldı ve APK `install -r` ile güncellendi. SQLite dosyaları süreç duruyorken okundu: önceki **iki key/gövde/durum birebir aynı**, toplam **3 taslak**, bunlardan **1’i outbox’sız offline taslak** olarak kaldı. Eski kesin satış + bloke reddi kaybolmadı. Keystore bağlantısıyla katalog tekrar okunabildi.

Bağımsız SQL sayımı: **2 Sale / 2 SaleLine** (biri önceki backend demo satışı, biri Android satışı), **1 Recall / 6 RecallLot / 16 StockMovement**. Mobil hedef but lotu **5.000000 kg**. Offline test yeni merkezî satış yaratmadı. Gerçek UUID’ler ve APK checksum’ı [results.json](validation/results.json) içindedir; bunlar kurgusal demo kayıtlarıdır, işletme verisi değildir.

## Ekran kanıtları

Son paletle gerçek emülatörden alınmış görüntülerdir; tasarım maketi değildir. Küçük boyutta emülatör fiziksel framebuffer’ı siyah kenarlarla letterbox eder; uygulamanın mantıksal alanı 360×640’tır.

- [Ana ekran, light](validation/home-light.png)
- [Onaylı satış ve gerçek hareket kimliği](validation/demo-confirmed.png)
- [Recall reddi ve offline taslak](validation/demo-blocked.png)
- [Küçük ekran, dark](validation/small-dark.png)

## Başarısız girişimler ve sınırlar

İlk API 35 Google APIs yazılım emülatöründe instrumentation **test keşfinden önce “Process crashed”** ile durdu, 0 test çalıştı. Sistem servislerinde de ANR/native çökme kayıtları vardı; kesin kök neden belirlenmedi. **API 35 cihaz uyumluluğu doğrulanmış sayılmaz.** API 28 AOSP koşuları başarıyla tamamlandı. Fiziksel telefon, KVM/GPU hızlandırmalı emülatör ve farklı üreticiler test edilmedi.

İlk kurulumda SDK manager manifest erişimi, proxy/CA, JRE’de javac olmaması ve salt okunur home nedeniyle sorunlar yaşandı. Resmî arşivler doğrulanarak JDK/SDK kuruldu; TLS doğrulaması kapatılmadı. ADB’nin kullanıcı dizini yazma sorunu geçici tool container’ı ile çözüldü; bu uygulamaya yeni servis eklenmesi değildir. İlk JUnit void dönüşü ve debug network XML lint hataları düzeltildi. Kaynak klasörü değişimindeki eski incremental resource cache’i yeniden üretildi. Son teslim komutları yukarıdaki gibi geçti. Ortamın analytics dizini ve native sembol strip uyarıları test başarısızlığı değildir; son lint raporu temizdir.

Uygulama tek satırlı lot satışı oluşturur; çok satırlı backend geçmişini okuyabilir. Kapalı uygulamada WorkManager/background gönderimi yoktur; gönderim uygulama açıkken ağ dönüşünde veya kullanıcı yenilemesinde yapılır. Release APK/imzalama/dağıtım, gerçek üretim TLS oturumu ve kullanıcı/rol yetkilendirmesi uygulanmadı. Backend’in X-API-Key prototip koruması üretim kimlik sistemi diye sunulmaz. Gerçek cihaz yeniden başlatması veya uninstall sonrası kurtarma test edilmedi; normal süreç yeniden açılışı ve DB dosyası kalıcılığı doğrulandı.

## APK ve entegrasyon devri

APK: `android/app/build/outputs/apk/debug/app-debug.apk` (bu çalışma alanında tam yol `/workspace/byteme-avatar-2026/android/app/build/outputs/apk/debug/app-debug.apk`). Kurulum: `adb install -r <APK yolu>`. APK/build çıktıları Git’e eklenmez; checksum ve boyut sonuç JSON’undadır. Linux/Zorin yönergeleri: [ANDROID_SETUP.md](ANDROID_SETUP.md).

Ortak docs/PROJECT_CHECKLIST.md değiştirilmedi. Entegrasyon sorumlusu **AND-01…AND-06 ve KUZ-05** için API 28’de bu dar prototip kabul kanıtlarını kullanabilir: Kotlin build, Room/Retrofit, kalıcı outbox/safe retry, gerçek lot satışı/StockMovement, recall reddi ve kesim parçasının cihazdan satışı. API 35/fiziksel cihaz doğrulaması, üretim yetkilendirmesi ve bütün yarışmanın birleşik teslimi ayrı kalır. Backend/frontend/ML kaynaklarına veya henüz tamamlanmamış ajan işlerine müdahale edilmedi.

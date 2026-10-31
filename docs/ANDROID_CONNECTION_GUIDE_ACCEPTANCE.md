# Görev 29B — Son Android bağlantı rehberi

31 Ekim 2026 · Kaynak branch: [`feature/android-connection-guide`](https://github.com/EminAly1/byteme-avatar-2026/tree/feature/android-connection-guide).
Başlangıç `origin/main`: `868ae1dfd440c85e683550927d9f833e2afc7342`; PR #47'nin birleşimi Git merge geçmişinden doğrulandı.
[Main hedefli PR / karşılaştırma](https://github.com/EminAly1/byteme-avatar-2026/compare/main...feature/android-connection-guide).

## Kullanıcı akışı

- İlk açılışta **Sunucuya bağlan** ve **Bağlantı yardımı** seçenekleri birlikte görünür. Yardım ayarlardan da açılır; beş sekmeye yeni sekme eklenmez.
- Durum kartı **Bağlı değil / Bağlanıyor / Bağlandı / Hata** gösterir. Kaydedilmiş URL tek başına başarı değildir; durum son gerçek API kontrolüne dayanır. Ağ kaybında/ayar değişiminde eski kontrol geçersizleştirilir.
- **Bağlantıyı kontrol et**, kayıtlı bağlantıyla kimlik doğrulamalı `GET /v1/products?limit=1` isteği gönderir ve beklenen JSON Page şemasını okur. Genel `/health` yanıtı API yetkisi kabul edilmez. HTTP/JSON/ulaşım hatası ve eksik anahtar başarı değildir. Ayarlar değişirse eski sonuç kabul edilmez; hata metni raw yanıt/anahtar içermez.
- Kontrol sadece okur: `drain`, katalog yenileme, satış onayı veya Room yazma çağrısı yapmaz. Mevcut otomatik senkronizasyon ve açıkça onaylanmış satışların gönderim kuralları korunur; bu kontrol ayrı bir satış gönderimi başlatmaz.
- Yardım ekranı bilgisayardaki sunucuyu, USB yetkilendirmeyi, Android 11+ kablosuz ADB bağlantısını, `adb devices` ve `adb reverse tcp:8000 tcp:8000` adımlarını açıklar. Telefon için `http://127.0.0.1:8000/`, emülatör için `10.0.2.2` ayrımı vardır. Birden fazla cihazda `adb -s` ve yeniden bağlanma sonrası tünel kontrolü belirtilir.
- **QR ile APK indirme otomatik sunucu eşleştirmesi değildir.** Yeni eşleştirme protokolü/Android QR tarayıcısı eklenmedi. Standart Android/Android Studio kablosuz ADB yönergeleri kullanılır.
- Yardım composable'ı API anahtarı almaz veya okumaz; gerçek anahtar yalnız mevcut maskeli ayar alanı ve Keystore yolunda kalır. HTTP/LAN sınırları, paket, ikon ve imza ayarları değiştirilmedi.

Kaynaklar: [ConnectionHelp.kt](../android/app/src/main/java/com/byteme/avatar/ui/ConnectionHelp.kt), [ConnectionProbe.kt](../android/app/src/main/java/com/byteme/avatar/network/ConnectionProbe.kt), [AvatarScreen.kt](../android/app/src/main/java/com/byteme/avatar/ui/AvatarScreen.kt), [SalesViewModel.kt](../android/app/src/main/java/com/byteme/avatar/ui/SalesViewModel.kt).

## Gerçek test sonuçları

| Kapı | Sonuç / sınır |
| --- | --- |
| `testDebugUnitTest` | **43 test, 0 failure, 0 error, 0 skip**. Robolectric SDK28, MockWebServer ve native SQLite; fiziksel cihaz/emülatör kabulü değildir. Önceki 34 host testi korundu, 9 test eklendi. |
| `lintDebug`, `lintPreview` | **Başarılı; her raporda 0 issue.** |
| `assemblePreview` | **Başarılı; yeni APK üretildi.** Son birleşik Gradle kapısı 35 saniyede başarılı tamamlandı. |
| Bağlantı fixture testleri | 5 yeni HTTP testi: boş ayar/anahtar, doğru yetkili GET, 401/503/geçersiz 200 yanıtı, ulaşılamayan sunucu/güvenli hata, değişmiş kimlik bilgisi/iptal. |
| UI host kontrolleri | 3 yeni test: ilk açılış seçenekleri/dört durum, kontrol düğmesinin URL'yi başarı saymaması, yardımda USB/kablosuz/reverse ve anahtar alanı bulunmaması. Mevcut maskeleme/placeholder/HTTP politikası testleri geçti. |
| Room/offline koruması | 1 yeni test: başarılı ve 401 bağlantı kontrolü sonrası bağımsız offline taslak, onaylı outbox kaydı, key/body/durum ve stok birebir aynı; yalnız GET var, kesin satış oluşmadı. Mevcut kalıcılık/idempotency/LOT_BLOCKED/sekme/form/PDF testleri de geçti. |
| Gerçek FastAPI sözleşmesi | Ayrı mevcut `*_test` DB üzerinde host'tan salt okunur `GET /v1/products?limit=1`: kayıtlı anahtarla **200 + Page JSON**, anahtarsız **401**. Android → gerçek backend cihaz kabulü değildir. |
| 29A QR akışı / yeni APK | Mevcut Chromium senaryosu **1/1 geçti**: gerçek güncel APK, bağımsız QR decode/aktif URL eşleşmesi, hash eşleşen tek indirme, ikinci indirme reddi, gerçek yeni paylaşım ve süre sonu. 390/768/1440 px kontrolleri de mevcut senaryoda geçti. |
| Paylaşım aracı testleri | Mevcut Python testleri **6/6 geçti**; eski APK yeni canonical build karşısında ayrıca gerçekten reddedildi. Mevcut Starlette/anyio deprecation uyarısı var. |
| Paket/imza/artefakt | `apksigner verify --print-certs` başarılı; mevcut Preview sertifikası aynı. `aapt` paket/sürüm/minSdk kontrolü ve dağıtım kopyasının SHA256 eşitliği doğrulandı. |

Makine okunabilir özet: [results.json](evidence/android-connection-guide/results.json).
Yeni APK ile gerçek web popup'ı: [1440 px ekran](evidence/android-connection-guide/new-apk-qr-masked-1440.png); token gizliliği için **QR ve URL maskeli**. QR kanıtı görüntüden değil bağımsız decoder karşılaştırmasındandır. 29A'nın tarihsel ekranları byte-for-byte korundu. Backend/MySQL/ML/frontend/paylaşım aracı kaynakları değiştirilmedi; iş kaydı silme/yazma yapılmadı.

## Yeni APK

| Alan | Değer |
| --- | --- |
| Build | `android/app/build/outputs/apk/preview/app-preview.apk` |
| Teslim kopyası | `/workspace/artifacts/AVATAR-Preview-connection-guide.apk` |
| Hash dosyası | `/workspace/artifacts/AVATAR-Preview-connection-guide.apk.sha256` |
| Boyut | **17.061.564 bayt** |
| SHA256 | **`0affc5b5ba72650ec33fe96fa23c5fdec87cc83134cb8f9c1b75065a911cfd3e`** |
| Kimlik / sürüm | `com.byteme.avatar.preview` / `0.1.0-preview.2`, versionCode 1; minSdk26, targetSdk35 |
| Sertifika SHA256 | `b9fbe028ac6c63fc1f873fbe446a0693be3f6260d57807f89d75ad6ef0418f9f` — önceki Preview ile aynı |

Sürüm etiketi korunur; yeni build yukarıdaki yeni SHA256 ile ayırt edilir. APK ve raw loglar Git'e eklenmez. Güncel paylaşım komutları/hash [INDIRME.md](INDIRME.md) içindedir. Eski uygulamayı uninstall/`pm clear` etmeyin; sertifika uyuşmazlığında durun. Bu oturumda cihaz kurulumu veya cihaz verisine işlem yapılmadı.

## NOT RUN ve kalan insan kabulü

- **Fiziksel Android telefon: NOT RUN.** Bu SDK/PATH'te `adb` bulunmadı; fiziksel cihaza erişim kurulmadı. USB/kablosuz ADB yönergeleri cihaz üzerinde denenmedi.
- **API28 emülatör instrumentation: NOT RUN. API35: NO ACCEPTANCE / 0 test.** Emülatör kurulmadı/başlatılmadı. Robolectric SDK28 host sonuçları cihaz kabulü sayılmaz.
- **Gerçek Wi-Fi telefon kamerası → QR → APK indirme/kurulum: NOT RUN.** Bulutun özel IPv4 arabiriminde aynı host'tan HTTP aktarımı yapıldı.
- Fiziksel telefonda mevcut Room/outbox/Keystore verileriyle güncelleme ve PDF/native paylaşım kabulü bu görevde denenmedi. Eski veriler silinmedi veya yeniden anahtarlanmadı.

**Sonraki aşama yalnız fiziksel telefon provası ve yarışma videosudur:** güvenilir kanaldan hash'i doğrula → mevcut verileri koruyarak uygun Preview güncellemesini dene → USB/kablosuz ADB reverse → gerçek bağlantı kontrolü → offline taslak/idempotency/PDF akışlarını prova et → yarışma videosunu kaydet. Yeni özellik veya mimari geliştirmesi başlatılmadı. PR incelemesi/merge ekip tarafından yapılmalıdır.

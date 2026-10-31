# AVATAR Android — Görev 24-MINIMAL

Teslim kaydı: **31 Ekim 2026, Europe/Istanbul**. Branch:
`feature/android-release-minimal`; başlangıç `origin/main`:
`d68ff7854dd68583f9d5fecdc4bda942eeda11fa`.
Bu çalışma kaybolan Görev 24 kaynaklarını aramaz; çalışan main üzerine küçük
değişiklikler uygular. Önceki oturumun 28 host/7 cihaz sonucu bu sürümün kanıtı değildir.

## Uygulananlar

- Görünen uygulama adı ve üst çubuk **AVATAR**. Paket `com.byteme.avatar`,
  launcher ikonu, minSdk 26 ve targetSdk 35 korunur.
- Material 3 ana sayfa, stok, satış, bekleyenler, uyarılar ve mevcut ayarlar.
  Beş alt sekme, 48 dp kontroller, 16 dp içerik aralıkları; geçmişe Ana Sayfa'dan erişim.
- Miktarlar `BigDecimal.stripTrailingZeros().toPlainString()` ile gösterilir:
  `20.000000 → 20`, `20.500000 → 20,5`, `0.125000 → 0,125`,
  `0.000001 → 0,000001`. Kayıtlı ve kullanılabilir miktarlar ayrı gösterilir.
  Bloke, geçmiş/geçersiz SKT, boş bakiye veya uygun olmayan konum satışa kapalıdır.
- Retrofit `GET /v1/alerts/summary` ve `GET /v1/alerts`, mevcut `X-API-Key`
  korumasını kullanır. Sunucu sayısı, şiddeti, kaynak ID'si, lot etiketi,
  önerisi ve kanıtları korunur. Filtre/sayfalama, 401/403/503 mesajları ve eski
  değerlendirme etiketi vardır. Sahte uyarı veya push/FCM eklenmedi.
- Uyarılar yalnız bellekte ve ayrı repository/coroutine'dedir; Room/outbox'a
  erişmez. Başarısız GET son başarılı değerlendirmeyi sıfır risk gibi göstermez.
  Endpoint değişimi ve geç gelen eski cevap için generation kontrolü vardır.
- Satış girdileri kökte `rememberSaveable` ile saklanır; sekme değişimi formu
  silmez. Yeni satış açıkça yeni form açar. Geçişlerde odak/klavye kapatılır,
  her ekran kendi kaydırma durumuyla açılır. Offline taslak kesin satış değildir.
- AVATAR ikonlu açılış, gerçek Room ekran durumu hazır olduğunda sona erer.
  Sabit bekleme/yüzde yoktur; sistem animasyon ölçeği sıfırken animasyon kapalıdır.

## Korunan sözleşmeler

`SalesRepository.kt`, `LocalDatabase.kt`, Room şema v1 ve sekiz tablo,
`SecureSettings.kt`, Gradle bağımlılıkları ve ağ güvenliği XML'leri değiştirilmedi.
Frozen key/body, mutex/claim, idempotency, backend UUID doğrulaması, atomik Room
onayı ve endpoint sınırı aynı kalır. Cihazda stok veya maliyet muhasebesi yoktur.
Satış POST'una otomatik HTTP retry eklenmedi. Anahtar maskeli ve mevcut
Keystore AES-GCM yaklaşımıyla tutulur; yeni UI saved state'e anahtar yazmaz.
Üretim HTTPS/debug loopback sınırı değişmedi. Backend, web, ML ve checklist'e dokunulmadı.

## Bu sürümün gerçek kabul kapısı

```sh
./android/gradlew -p android testDebugUnitTest lintDebug assembleDebug
```

JDK 17.0.17, checksum doğrulanmış Gradle 8.10.2, platform/build-tools 35 ile:

| Kontrol | Sonuç |
| --- | --- |
| `testDebugUnitTest` | **23 geçti; 0 hata, 0 atlama** |
| `lintDebug` | **0 bulgu** |
| `assembleDebug` | **Başarılı; APK imzası doğrulandı** |
| API28 cihaz smoke | Hazır emülatör yok; **çalıştırılmadı** |
| API35 | **NO ACCEPTANCE / 0 test**; başlatılmadı |

Mevcut 15 satış repository testi korunur: offline taslak, stok değiştirmeyen
yerel işlemler, onaylı UUID/hareket eşleşmesi, kayıp cevap sonrası aynı key/body,
401/503, LOT_BLOCKED, negatif/yetersiz stok hatası, kalıcılık ve endpoint sınırları.
Compose/Robolectric testi uygulama ekranını açar, AVATAR'ı, mikro stok metnini,
bloke düğmeyi, sekmeler arası miktar/fiyat korumasını ve mevcut onay özetini doğrular.
Üç sunum ve dört MockWebServer uyarı testi de geçti. Bunlar gerçek Android
emülatörü veya canlı MySQL entegrasyonu olarak sunulmaz. Uyarı DTO'ları mevcut
backend sözleşmesine bağlandı; korumalı gerçek HTTP yolları MockWebServer ile
doğrulandı. Bu oturumda gerçek 6→5 kg satış, 30 tablo hash'i ve cihazda canlı
uyarı demosu tekrarlanmadı; bu alanlara yeni kabul verilmedi.

[Makinece okunur test/scope/hash özeti](evidence/android-premium-ux/minimal-results.json).
Raw log, özel fixture, keystore ve APK binary Git'e eklenmez. Uzun ekran
matrisi veya eski SystemUI hata görüntüleri bu sürümün kanıtı olarak kullanılmaz.

## APK ve gerçek sınırlar

- Dosya: `android/app/build/outputs/apk/debug/app-debug.apk`.
- SHA256: `2ffaca1d8931902a61ce6556806be1f96aa899f5578c69817ed74210a025320a`.
- Bu ortamda üretilen debug sertifikası, bulunan eski APK'nın sertifikasıyla
  **farklıdır**. Mevcut cihaz verisini koruyan `install -r` yükseltmesi doğrulanmadı.
  Önceki kurulumun üzerine yükseltmek için özgün imza anahtarıyla build alınmalıdır;
  bunu aşmak için uninstall/`pm clear` veya Room silme yapılmadı ve yapılmamalıdır.
- API28/gerçek cihaz, TalkBack, fiziksel klavye ve görsel emülatör kabulü bekler.
  API35 önceki Package Manager sorunu nedeniyle bu görevde açılmadı.
- PDF/Android belge paylaşımı Görev 25'tir. FCM, RBAC, resmî e-Fatura veya yeni
  muhasebe işlevi yoktur. Main'e merge yapılmaz; bu sürüm PR incelemesine gönderilir.

# Android belge/PDF kabulü — Görev 25

31 Ekim 2026, Europe/Istanbul. Branch: `feature/android-documents-final`.
Başlangıç `4ace298`: PR #41'in main'e merge edildiği Git geçmişi ve
`ce26268` ancestor kontrolüyle doğrulandı. Beş sekme, AVATAR markası, paket
`com.byteme.avatar`, uyarılar ve mevcut satış güvenliği korundu.

## Kaydedilen çalışan aşamalar

1. Temel belge ekranı/not editörü: [`495034a45577505a50831f574a9b26ff9c706cac`](https://github.com/EminAly1/byteme-avatar-2026/commit/495034a45577505a50831f574a9b26ff9c706cac).
   26 test/lint/build geçince, PDF geliştirmesine başlamadan commit ve push yapıldı.
2. Son belge/PDF uygulama kodu: [`c3ba215442544114bf33d0ba1ecad546292f3089`](https://github.com/EminAly1/byteme-avatar-2026/commit/c3ba215442544114bf33d0ba1ecad546292f3089).
   PDF önizleme, kaydetme ve paylaşma 31 test/lint/build sonrasında ayrı commit/push aldı.
   Her iki uzak SHA `git ls-remote` ile doğrulandı. Sonraki kabul raporu commit'i uygulama kodunu değiştirmez.

[GitHub branch](https://github.com/EminAly1/byteme-avatar-2026/tree/feature/android-documents-final) ·
[main hedefli PR karşılaştırması](https://github.com/EminAly1/byteme-avatar-2026/compare/main...feature/android-documents-final?expand=1).
PR oluşturma sonucu teslim raporunda belirtilir; main'e merge yapılmaz.

## Kullanıcı akışı

Ana Sayfa ve onaylı satış kartlarından **Belgeler** açılır; alt menüye altıncı
sekme eklenmez. Kullanıcı onaylı satış ve Proforma/Satış Özeti türünü seçer.
`GET /v1/document-drafts/sales/{sale_id}` mevcut X-API-Key korumasıyla çağrılır.
DTO'lar doğrudan backend `document_api.py`, `document_drafts.py` sözleşmesinden
alındı. Müşteri, fiyat, miktar, lot, iade/iptal tutarları, bağlı sevkiyatlar ve
kaynak durumu salt okunurdur. Müşteri güncel iş ortağı kaydıdır; tarihsel vergi
adresi olarak sunulmaz. İptal/tam iadede güncel ödeme talebi olmadığı gösterilir.

Ayrı editörde yalnız DraftFields allowlist'i değişir: başlık/açıklama, satıcı
beyanı/iletişim, belge tarihi, ödeme/teslimat açıklaması, not, referans ve demo
etiketi. Tarih, uzunluk, satır ve Unicode kontrol karakteri kuralları uygulanır.
Bunlar geçici bellek alanlarıdır; sunucuya taslak arşivi veya satış düzeltmesi
kaydedilmez. Ödeme, vergi/KDV veya tahsilat hesabı yapılmaz.

PDF, `POST /v1/document-drafts/proforma/pdf` üzerinden gerçek sunucu baytlarıdır.
İstek seçili satış ID'si, backend kaynak fingerprint'i, tür ve izinli draft
alanlarından oluşur. 409 kaynak değişiminde eski PDF kullanılmaz; açık kaynak
yenilemesi gerekir. Android PDF üretmez ve kesin satış/stok komutu göndermez.

## PDF, dosya ve URI güvenliği

- `application/pdf` Content-Type, `%PDF-` imzası ve son 1024 baytta `%%EOF`
  kontrol edilir. Eksik/yanlış/truncated veya 20 MiB üzerindeki yanıt reddedilir.
  İndirme streaming/8192 bayt tamponla yapılır; reddedilen dosya silinir.
- PDF yalnız `cacheDir/document-pdfs/` içinde rastgele adla tutulur. Başlık veya
  kullanıcı referansı dosya yolu olmaz. Her üretimde bu modülün eski dosyaları
  temizlenir: en çok 5 dosya, 24 saati geçenler sonraki üretimde kaldırılır.
  Bu geçici önbellek mali belge arşivi değildir. Key/header veya kaynak JSON'u
  PDF dosyasına eklenmez. Source/tür/draft değişince geçersiz PDF bağlantısı kesilir.
- PdfRenderer yalnız seçilen sayfayı açar; descriptor/page/renderer `use` ile
  kapanır. Render IO thread'dedir; mutex aynı anda tek renderer çalıştırır.
  Bitmap boyutu en çok 1000×1500'dür; tüm sayfaların bitmap listesi oluşturulmaz.
  Önceki/Sonraki kontrolleri yükleme sırasında kapalıdır. Parser hatası UI'da ele alınır.
- Kaydetme `ActivityResultContracts.CreateDocument("application/pdf")` ve
  ContentResolver ile kullanıcı seçimi üzerinden yapılır. Genel depolama izni
  yoktur. Başarı yalnız stream kapanınca bildirilir; iptal/hata ayrıdır.
- Paylaşma yalnız bu özel klasör için unexported FileProvider kullanır.
  URI `content://` türündedir; ClipData ve yalnız READ grant vardır. WRITE grant,
  API anahtarı, API URL'si veya header paylaşılmaz. Destekleyen uygulama yoksa
  açıklayıcı mesaj gösterilir. Paylaşım uygulamasını kullanıcı sistem chooser'ında seçer.

## Gerçek minimum kabul sonuçları

```sh
./android/gradlew -p android testDebugUnitTest lintDebug assembleDebug
```

| Kontrol | Sonuç |
| --- | --- |
| Android unit/Robolectric | **31/31 geçti; 0 hata, 0 atlama** |
| Android lintDebug | **0 bulgu** |
| assembleDebug | **Başarılı; APK imzası doğrulandı** |
| PDF API | Kontrollü MockWebServer GET/POST sözleşmesi geçti |
| Geçersiz PDF | Yanlış MIME, yanlış/kısa imza, eksik dosya sonu, aşırı boyut reddedildi |
| URI | FileProvider kapsamı/content URI/ClipData/yalnız READ grant doğrulandı |
| İş kayıtları | Belge okuma + draft edit + PDF sonrası Room stok/satış/taslak/outbox ve frozen key/body aynı |
| API28 cihaz | **Yapılmadı; hazır cihaz yok, emülatör kurulmadı** |
| API35 | **NO ACCEPTANCE / 0 test; başlatılmadı** |

Mevcut 23 testin tamamı korunur. Ek 8 test belge sözleşmesi, readonly kayıtlar,
409 fingerprint koruması, draft allowlist'i, PDF baytları ve URI yetkisini kapsar.
Source GET ve PDF POST dışındaki HTTP komutları belge testinde gönderilmedi.
Bunlar canlı Android/MySQL entegrasyonu veya fiziksel cihaz kabulü değildir.

### Kontrollü PDF kanıtı

`android/app/src/test/resources/document-source.json` ve
`document-draft-fixture.json` tamamen KURGUSAL'dır. Değiştirilmemiş backend
`render_pdf` fonksiyonu bunlarla `document-server-fixture.pdf` üretti; Android
veya mock metniyle uydurulmuş bir PDF değildir. pypdf strict parse: **2 sayfa,
48.595 bayt**. Fixture SHA256:
`26a2af7d1bb6d822a7e87479cfd4dfc1de741308ce15b0158981f002df1bdd61`.
İstemcinin aldığı dosya fixture ile byte-for-byte aynıdır. Üreticide hem
proforma hem sale_summary ayrı render/parse edildi (ikisi de 2 sayfa); kontrollü
kaynak dictionary'sinin hash'i önce/sonra aynıydı. Bu kontrol MySQL ledger hash'i
olarak sunulmaz. Backend/font kaynakları değiştirilmedi.

## Paket ve kalan engeller

- APK: `android/app/build/outputs/apk/debug/app-debug.apk`.
- SHA256: `2de9cc7e309a4d073aea716ef38b790e771513c049eab338144d6bf239bf4b21`.
- Debug sertifikası PR #41 minimal APK ile aynı:
  `b9fbe028ac6c63fc1f873fbe446a0693be3f6260d57807f89d75ad6ef0418f9f`.
  Daha eski kurulumla bilinen imza uyuşmazlığı çözülmüş sayılmaz. Özgün eski imza
  anahtarı son paketlemede kullanılmalıdır. Uninstall, pm clear veya veri silme yapılmadı.
- Fiziksel/API28/API35 PdfRenderer çizimi, OS dosya seçicisi ve üçüncü parti
  paylaşım hedefi bu ortamda test edilmedi. Kontrollü unit sonuçları bunların
  yerine geçmez. Cihazda canlı backend/PDF testi ve veri koruyan yükseltme bekler.
- Room/satış repository/şema, Keystore, frozen key-body ve idempotency kodları
  değişmedi. Backend/web/ML değişikliği, yeni muhasebe, e-Fatura veya belge/satış
  silme özelliği yoktur. API anahtarı, özel env, raw log ve APK Git'e eklenmedi.

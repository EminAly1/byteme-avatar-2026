# ByteMe Android satış uygulaması — Görev 8

Kotlin / Compose Material 3 / MVVM; Room SQLite önbelleği ve kalıcı outbox; Retrofit + OkHttp; Coroutines + Flow. Çalışma branch’i feature/android-sales-app, başlangıç main 3626c99 (PR #1–#10 merge geçmişi doğrulandı). Yalnız android/ değişir.

[Kurulum, sürümler, APK ve demo](ANDROID_SETUP.md) · [Gerçek doğrulama sonuçları](VALIDATION.md).

## Kaynak mimarisi

- `network/AvatarApi.kt`: Gerçek v1 DTO’ları, cursor bitene kadar sayfalama ve döngü kontrolü. GET products/lots/stocks/locations/parties/sales ve sale detail; POST sales. Para ve miktar JSON string’dir.
- `data/LocalDatabase.kt`: sekiz Room tablosu, FK/indeksler, Flow sorguları. Katalog tüm sayfalar başarıyla okunduktan sonra transaction’da yenilenir; kesilen yenileme eski kataloğu silmez. Referans verilen eski kayıtlar inactive tutulur, taslaklar silinmez.
- `data/SalesRepository.kt`: giriş doğrulama, taslak, değişmez onaylı istek, tek sender mutex + DB claim, FIFO gönderilebilir işler, backend cevabı doğrulama ve atomik onay kaydı. SQLite veya UI stok/maliyet muhasebesi yapmaz.
- `security/SecureSettings.kt`: debug loopback/HTTPS adres denetimi, Keystore AES-GCM anahtar saklama. Anahtar kaynak/BuildConfig/APK içine gömülmez. Endpoint, ciphertext ve IV atomik kaydedilir; anahtar loglanmaz.
- `ui/SalesViewModel.kt`: ekran durumu, ağ dönüşünde/manuel senkronizasyon ve kullanıcı onayı. `AvatarScreen.kt`: ana ekran, stok/lot, ürün→lot/konum→müşteri→miktar/fiyat→onay, satış ayrıntısı, taslak/outbox ve bağlantı ayarı. Light/dark tema, küçük ekran için kayan form/dialog, en az Material dokunma alanları, loading/boş/hata durumları.

## Room veri sözleşmesi

| Tablo | Anahtar / ilişki / amaç |
| --- | --- |
| CachedProduct | backend UUID PK; isim, SKU, tür, birim, active |
| CachedLot | UUID PK, productId FK+index; lot kodu, bloke, SKT |
| CachedStock | PK(lotId,locationId); lot/ürün FK, ürün index; sunucunun miktarı/kullanılabilir miktarı, gerçek konum adı/türü |
| CachedCustomer | UUID PK; yalnız customer rolünden alınır; isim/iletişim |
| SaleDraft | UUID PK; stock(lot,location) ve customer FK/index; ürün/lot/konum/müşteri, miktar/fiyat/birim ve bağlı endpoint |
| SaleOutbox | UUID Idempotency-Key PK; draft FK+unique; değişmez JSON gövde, endpoint, durum/deneme/hata |
| ConfirmedSaleSnapshot | gerçek satış UUID PK; nullable unique outbox FK; gerçek backend başlık/ayrıntı JSON’u |
| SyncMetadata | katalog adı PK; endpoint, son başarılı okuma zamanı, satış sonrası stale bayrağı |

İlk DB v1; app/schemas export edilir. Destructive migration yok. Anahtar ve gövde bir kere oluşturulur; DAO durum güncellemeleri bunları değiştirmez. Başarılı cevabın satış/lot/konum/birim/miktar/fiyat ve gerçek UUID’leri beklenen istekle doğrulanır. Confirmed snapshot + outbox durumu Room transaction’ında yazılır. Katalogdan stok düşülmez; backend’den yeni stok okunur. Farklı REST listeleri tek server snapshot’ı değildir; ekrandaki bütün stoklar son okuma olarak etiketlenir, kesin uygunluk POST sırasında backend’de yeniden kontrol edilir.

## Durumlar ve güvenli tekrar

- Sadece SaleDraft: offline kaydedilebilir; sunucuya gönderilmez, kesin satış değildir.
- READY: kullanıcı özeti onayladı; kalıcı key/body oluşturuldu.
- SENDING: CAS claim ile tek gönderici; uygulama yeniden başladığında tamamlanmamış kayıt RETRYABLE olur.
- RETRYABLE: timeout/bağlantı/503 veya doğrulanamayan yanıt. Sonuç belirsiz olabilir, aynı gövde ve anahtarla tekrar edilir.
- AUTH_REQUIRED: 401; anahtar düzeltilip kullanıcı yeniden onaylamadan otomatik gönderilmez.
- NEEDS_ACTION: 409/422 ve diğer kalıcı hatalar; taslak/hata korunur. LOT_BLOCKED veya yetersiz stokta otomatik alternatif lot veya yeni anahtar seçilmez. Düzeltme yeni ve açıkça onaylanmış taslak gerektirir; eski kayıt değişmez.
- CONFIRMED: backend gerçek satış cevabını onayladı. Sunucudan okunan mevcut satışlar da geçmişte görüntülenir; mobil istekle eşleşmedikçe ona ait outbox onaylanmış varsayılmaz.

Gönderilebilir READY/RETRYABLE işler createdAt+key sırasıyla tek göndericide işlenir. Kalıcı çatışmalar otomatik tekrar kuyruğundan çıkar, ayrı incelenmek üzere görünür kalır. Ağ/503/401 sonucu aynı drain turunu durdurur. Gönderim ve katalog yenilemesi serileştirilir; eski bir yerel yenileme satış sonrası stale bayrağını yanlışlıkla silemez. Başka endpoint’e ait bekleyen istek yeni sunucuya gönderilmez. Normal süreç/Activity yeniden açılışında SQLite anahtarları ve taslaklar kalır.

## Kapsam

PDF Kotlin + SQLite + MySQL tutarlı senkronizasyon ister; offline kesin satış veya cihazda maliyet hesabı uygulanmaz. Uygulama tek satırlı lot satışı oluşturur; backend çok satırlı satışlarının ayrıntılarını okuyabilir. Recall oluşturma, sevkiyat kaydı, kesim yürütme ve ML mobil ekranları bu görevde yoktur; mevcut backend’in oluşturduğu parça lotları satılır. Anahtar koruması gerçek kullanıcı/rol kimlik sistemi değildir. Android veritabanı katalog ve outbox’tır; merkezî kayıt MySQL’dir.

Ortak checklist değiştirilmedi. AND-01...AND-06 ve KUZ-05 için ilerleme yalnız VALIDATION.md’deki gerçek build/test/cihaz kanıtına göre entegrasyon sorumlusu tarafından işaretlenmelidir; yalnız kaynak kodunun bulunması cihaz demosunun tamamlandığı anlamına gelmez.

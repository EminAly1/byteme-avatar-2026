# Görev 7 — işletme içi kuzu parçalama

Başlangıç `main`: `e8c690d` (PR #1–#8 normal merge commit’leri geçmişte doğrulandı). Yalnız backend/, database/, tests/ değişir. Yeni mikroservis veya ayrı kesim stok defteri yoktur: cutting, mevcut Operation’ın bir türüdür. Ortak docs/ ve diğer ajan alanları korunur.

## Kaynak ve açık kararlar

`docs/AVATAR_Assessment.pdf` üç sayfası metin olarak, ilk sayfa ayrıca görsel olarak incelendi. PDF bütün kuzu için 25 kg × 11,50 EUR = **287,50 EUR** olduğunu, 351 EUR ile çeliştiğini ve parça toplamının 22 kg olduğunu söyler. Tek tek parça ağırlıklarını içeren görsel/tablo bu PDF’de bulunmuyor. Bu nedenle demo but/omuz/sırt/kaburga/kıyma ağırlıkları **6/4/4/5/3 kg**, referans değerleri **20/14/24/12/10 EUR/kg**, fire sınıfı/açıklaması ve satış fiyatı **kurgusal** olarak etiketlidir. Gerçek işletme verisi veya PDF’den çıkarılmış parça ağırlığı gibi sunulmaz.

Ürün kartında isteğe bağlı `species` (örn. Kuzu), mevcut raw/finished/byproduct türü ve kg stok birimi bulunur. Giriş hayvan türü, kaynak ürün, tedarikçi ve alış lotu kesin kayıtlardır. Yeni reçete türü, kartta species varsa onunla eşleşmelidir; eski species=null kartlar korunur. Reçete snapshot’ı species değerini işlem tarihinde saklar.

`POST /v1/receipts` satırına isteğe bağlı `unit_price` eklendi (EUR/stok birimi; kg üründe EUR/kg). `quantity × unit_price`, kuruşta ROUND_HALF_UP ile girilen `total_cost` ile eşleşmelidir; aksi halde 422 RECEIPT_PRICE_MISMATCH ve tüm alış rollback. `25`, `11.50`, `287.50` kabul edilir; `351.00` ile aynı fiyat verilirse reddedilir. Doğrulanmış toplam gerçek bedel otoritedir: birim fiyat verilmemiş eski alışlar korunur, 351 hiçbir zaman sessizce 287,50’ye veya tersine çevrilmez. Eski alışlar için yeni unit_price null’dır, fiyat uydurulmaz. Giriş tarihi, tedarikçi, konum ve lot mevcut alış FK’lerinde kalır.

## Endpoint ve gövdeler

Bütün yollar mevcut X-API-Key korumasındadır. Her POST mevcut UUID `Idempotency-Key` protokolünü kullanır; aynı anahtar/gövde aynı cevabı döndürür. Farklı gövde 409, validation 422, bulunamayan kayıt 404. Para ve miktarlar JSON string’dir.

| Yol | Gövde / sonuç |
| --- | --- |
| POST /v1/recipes | code, version (pozitif int), species, input_product_id, allocation_method=quantity/value, available? (true), lines:[product_id, reference_eur_per_kg?]. 201 yeni değişmez sürüm. |
| GET /v1/recipes | limit 1–100, UUID cursor; sürümler ve bütün kayıtlı parça satırları. |
| GET /v1/recipes/{id} | Tek sürümün tanımı ve satırları. |
| POST /v1/recipes/{id}/availability | `{"available":false}`; 200. İçeriği veya eski işlem snapshot’ını değiştirmez. |
| POST /v1/cuttings | `{"code":"KESIM-001","recipe_version_id":"UUID"}`; 201 Operation(kind=cutting), reçete ve politika snapshot’ı. Dış üretici/sevk gerekmez. |
| GET /v1/cuttings | Yalnız cutting türündeki Operation başlıkları; limit/cursor. Genel operasyon listesinde de aynı UUID’ler bulunur. |
| GET /v1/cuttings/{id} | Operasyon, snapshot, miktar/maliyetli girdiler/çıktılar, lot_links, sınıflandırılmış differences. |
| POST /v1/cuttings/{id}/post | consumed_inputs:[lot_id, location_id, quantity], output_location_id, outputs:[product_id,lot_code,quantity,unit?=kg,expires_at?,explanation?], differences?:[kind,quantity,reason]. 200 atomik kapanış. |

Reçetede giriş ürünü kg birimli raw, çıktılar kg birimli finished/byproduct olmalıdır. Çıktı ürünlerinin hepsi seçili sürümde tanımlı olmalıdır; sıfır fiili miktarlı parça satırı gönderilmez. Tek ürün birden fazla yeni lota ayrılabilir. Reçete miktarları fiili üretim miktarı yerine geçmez. Beklenen parçalar/referanslar önceden tanımlanır, fiili ağırlıklar kapanışta girilir.

Reçete içeriği güncelleme/silme endpoint’i yoktur. Aynı code+version tekrar oluşturulamaz; yeni anahtar için yeni version gerekir. available=false sürüm ile yeni taslak veya kapanış reddedilir; bu durum geçmiş operasyonu yeniden fiyatlamaz. Taslak oluşturulurken schema_version=1 snapshot içinde sürüm, tür, kaynak ürün, parça kartları, referans değerler ve maliyet politikası kopyalanır. Kapanış o snapshot’ı kullanır. Kapanmış emir tekrar post edilemez; başarılı idempotent replay hariçtir.

Genel `/operations/{id}/dispatch` ve `/operations/{id}/post` yalnız external_production kabul eder. Kesim için `/cuttings` yolları kullanılmalıdır; dış üretim yolu kesimi kapatamaz. Genel operasyon ayrıntısı mevcut biçimde okunabilir; kesim sınıflandırma ayrıntıları için cutting detail kullanılır.

## Ağırlık dengesi ve maliyet politikası v1

Her kaynak lot ve konum için fiili kg tüketilir. Girdi ve çıktı konumları işletme deposu olmalı; karantina/dış üretici kaynakları reddedilir. Blokeli/tarihi geçmiş lotlar kullanılamaz.

**Girdi kg = kaydedilmiş mamul kg + kaydedilmiş yan ürün kg + açıklamalı fark kg.** Fark otomatik doldurulmaz. differences türleri `waste` (fire) ve `other_loss` (diğer açıklanmış kayıp); her satır pozitif kg ve boş olmayan reason gerektirir. 25 kg giriş/22 kg ürün için 3 kg açıklanmazsa 422 MASS_BALANCE. Birden fazla fark satırı desteklenir. Bu satırlar OperationDifference FK’leriyle saklanır; kaynak tüketiminin içinde oldukları için ikinci kez stok düşümü oluşturmazlar.

Yan ürün kaybolan stok değildir: byproduct ürün kartına bağlı ayrı output/lot/pozitif stok hareketi ve zorunlu explanation ile kaydedilir. Örneğin 22 kg parça + 2 kg yan ürün + 1 kg açıklanmış diğer kayıp = 25 kg. differences içine `byproduct` yazıp stok kaydı atlamak reddedilir.

Dağıtılacak maliyet, tüketilen kaynak lotlarının **gerçek kümülatif tüketim maliyetlerinin toplamıdır**. Bu sürüm kesime ayrıca hizmet/işçilik bedeli eklemez; dış üretimin mevcut hizmet maliyeti akışı korunur.

- quantity: ağırlık = fiili çıktı kg.
- value: ağırlık = fiili çıktı kg × reçetedeki pozitif referans EUR/kg. Her parçanın referansı açıkça kayıtlı olmalı; satış fiyatı değildir.
- Her çıktı maliyeti = toplam gerçek tüketim maliyeti × kendi ağırlığı / bütün çıktı ağırlıklarının toplamı.
- Normal fire ve açıklanmış diğer kaybın maliyeti kaydedilmiş çıktılara tamamen yüklenir; ayrı bir gider muhasebesi yapılmaz. Yan ürün de seçilen yöntemde pozitif ağırlıkla pay alır. Sıfır maliyetli yan ürün/negatif hurda kredisi politikası uygulanmaz. Bu kararlar snapshot policies.version=1 içinde ayrıca kayıtlıdır.
- Decimal ve 48 haneli ara hesap kullanılır; ledger 6 ondalıktır. Ürün UUID+lot kodu sıralamasında kümülatif HALF_UP yuvarlama deterministiktir; son toplam gerçek tutara tam eşittir. Gösterim 2 hanelidir, gösterimlerden toplam yeniden hesaplanmaz.
- kg ve tutarlar DECIMAL(18,6) sınırına uymalı. Referans fiyat girişi en fazla 2 ondalık; value çarpımı pozitif ve 6 ondalıkta tam temsil edilebilir olmalıdır, aksi halde 422 ALLOCATION_PRECISION (sınır aşımında VALUE_OVERFLOW). Ağırlık gizlice yuvarlanmaz.
- LotLink miktarı para referansından bağımsız, fiili çıktı kg oranıyla tam tüketilen girdiyi dağıtır; toplamı tam girdi tüketimidir, açıklanmış kaybın payını da içerir. Bu kayıt fiziksel molekül ayrımı kanıtı değildir. Gerçek kayıp OperationDifference’ta ayrıca tutulur; recall bütün ortak çıktıları ihtiyatlı kapsar.

## Transaction, satış ve recall

Kilit sırası: operasyon → reçete sürümü → UUID sıralı kaynak lotlar → stok bakiye satırları. Lot kilidi alındıktan sonra blocked/expiry/konum/miktar kontrol edilir; yeni parça lotları, OperationInput/Output, LotLink, hareketler, bakiyeler, farklar, maliyet ve idempotency cevabı aynı transaction’da commit edilir. Yeni çıktı lotları commit’e kadar sadece bu transaction’a aittir. Hata tamamını rollback eder. Mevcut deadlock/timeout ve GraphChanged transaction retry korunur.

Recall operasyon/reçete kilidi almaz. Kesim kaynak lot kilidini yeni çıktıların bağlantıları commit edilene kadar tutar. Recall önce kazanırsa kesim blokeli girdiyi reddeder; kesim önce kazanırsa recall kilit sonrası genişleyen grafı görür, tüm transaction’ı yeniden başlatıp bütün yeni parça lotlarını da bloke eder.

Parça stokları doğrudan mevcut `/stocks`, `/sales`, `/lots/{id}/trace` ve `/recalls` ile çalışır. Yeni satış ayrı stok sistemi kullanmaz. Pozitif/negatif hareketler append-only defterdedir; sonradan ham SQL ile snapshot/blok/bağlantı değiştirmek bu garantinin dışındadır.

## Migration ve çalıştırma

Head `fa8791f3cf0e`, parent `bacb184a30d7`. Yeni tablolar recipe_versions, recipe_lines, operation_differences. Product.species; ReceiptLine.unit_price; Operation.recipe_version_id/allocation_snapshot; OperationOutput.reference_eur_per_kg/explanation nullable ek alanlardır. Eski dış üretim, stok, satış, recall kayıtları ve UUID’leri korunur. Downgrade yeni tür/reçete/fark/snapshot metadata’sını siler, mevcut lot/operasyon maliyetlerini, blokları ve stok defterini geri almaz. Bu nedenle audit kaybı olmayan geri dönüş için yedek ve ayrı işletme kararı gerekir; test downgrade yalnız izole şemadadır.

[README](README.md) ile güvenilir MYSQL_* / AVATAR_API_KEY ortamını yükleyip API’yi başlatın. İşletme verisinden ayrı demo veritabanında:

```bash
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini check
PYTHONPATH=backend backend/.venv/bin/python -m app.demo_cutting
```

Farklı port için AVATAR_API_BASE_URL ayarlayın. Demo iki yöntem için **iki ayrı 25 kg kuzu lotu** satın alır; aynı kuzu iki kez tüketilmez. Her biri 22 kg parça+3 kg açıkça kurgusal normal fire üretir. Bir but lotundan 1 kg satış, kaynak/parça ileri-geri trace ve stoktan bir kez düşüm doğrulanır. Sabit anahtarlarla tekrarlandığında kayıt çoğalmaz, geçmiş maliyetler değişmez. Eski app.demo, app.demo_sales_shipments ve app.demo_recall değiştirilmedi.

## Ortak belgelere aktarılacak işler

Ortak docs/ dosyaları değiştirilmedi. Entegrasyon sorumlusu API/ER/varsayım belgelerine yeni yolları, nullable alanları, üç tabloyu ve politika v1’i taşımalı. Checklist için KUZ-01/02/03/04 backend kabul kanıtları; KUZ-05’in stok/lot/satış backend kısmı ve LOT-11’in ileri/geri/recall testleri hazır. KUZ-06 hesap tutarsızlığı açıkça ele alındı; gerçek işletme belgesi ve fire sınıfı onayı hâlâ dışarıdan gelmelidir. Kotlin satışı, WEB-05 ekranı, DOC-03 birleşik demo ve TST-05’in Android/ML kısmı tamamlanmış değildir. Bu dosya checklist durumlarını kendiliğinden değiştirmez.

[Test kanıtı ve gerçek demo çıktısı](../database/cutting-validation.md).

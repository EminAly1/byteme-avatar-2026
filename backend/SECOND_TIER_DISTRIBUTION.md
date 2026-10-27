# İkinci kademe dağıtım — Görev 15

27 Ekim 2026 (Europe/Istanbul). Dal `feature/second-tier-distribution`; main tabanı `50aaca21646e9913a0cb58d13d3bbbec950b1390`. PR #1–#25 atalıkları doğrulandı; main'de ayrıca yalnız dokümantasyon içeren PR #26 bulunur. [Kabul kaydı](../database/second-tier-validation.md).

## Anlam ve sınır

Şirket → Market A sevkiyatı şirketin kesin stok çıkışıdır. Market A → kayıtlı Dağıtıcı X bildirimi **ayrı dağıtım kanıtıdır**; yeni şirket satışı veya ikinci stok tüketimi değildir. Mevcut API anahtarıyla sistem operatörü bildirimi kaydeder. Market kullanıcı oturumu, bağımsız market teyidi veya dış envanter doğrulaması yapılmaz.

İlk sürüm yalnız gerçek şirket ShipmentLine'ından tek ek dağıtım bağlantısını destekler. Üçüncü kademe, dış alıcının deposu/son tüketici satışları, ikinci kademe iadesi veya bildirimi iptal/düzeltme API'si yoktur. Yanlış kesin bildirim silinmez; düzeltme/ters belge süreci ayrı geliştirme gerektirir. Mevcut müşteri iadesi yalnız şirketin kayıtlı müşterisinden şirkete karantina kabulüdür; dağıtılmış malların geri toplanması olarak yorumlanamaz.

## Veri modeli

Migration **f1507a26b001**, parent **e1307a26b001**; tek yeni tablo `second_tier_distributions`, toplam 30 domain tablosu. Mevcut 29 tabloya kolon/kısıt değişikliği uygulanmaz.

Yeni satırda UUID id, source_shipment_line_id FK, source_customer_id FK, source_lot_id FK, product_id FK, recipient_party_id FK, quantity DECIMAL(18,6), unit, distributed_at, reference, evidence_note, recipient_name/contact snapshot ve created_at bulunur. Kaynak müşteri/lot/ürün istemciden alınmaz; gerçek sevkiyat/satış/hareket bağlantılarından doğrulanıp türetilir. Her kimlik gerçek FK'dır; redundant alanların kaynakla eşitliği servis transaction'ında denetlenir. Ürün/müşteri/lot adlarının benzerliği bağlantı kurmaz. Dağıtıcı, kayıtlı herhangi bir Party olabilir; kaynak marketin kendisi olamaz.

Alıcı snapshot'ı **bildirimin kaydedildiği anda** Party kartından alınır. Geri tarihli distributed_at için o tarihte bağımsız doğrulanmış iletişim iddiası taşımaz (`recipient_snapshot_basis=party_card_at_recording_time`). Kaynak market snapshot'ı asıl Shipment.recipient_name/contact kaydıdır. Party kartının sonraki değişiklikleri eski snapshot'ı değiştirmez; eksik iletişim null kalır.

Aynı kaynak sevkiyat satırı/reference çifti UNIQUE'dir: bu referans o kaynak satırına ait tek bildirim olayını tanımlar. Aynı belgedeki ayrı olaylar açıkça ayrı referanslarla kaydedilmelidir. UUID idempotency buna ek olarak ağ tekrarını korur. DB ayrıca pozitif miktar, kg/package/unit, paket/adet tam sayı ve farklı alıcı CHECK'lerini uygular. Kaynak tabloları doğrudan SQL ile değiştirerek bu protokolü atlamak desteklenmez.

## API

Tüm yollar mevcut `X-API-Key` korumasındadır. POST, UUID `Idempotency-Key` ister; 201 döner. Ondalıklar JSON string; kg en fazla altı ondalık, package/unit tam sayı; distributed_at timezone içeren zorunlu ISO8601'dir. Tarih UTC saklanır, kaynak shipped_at'tan önce veya kayıt anından ileride olamaz.

- `POST /v1/distributions/second-tier`
- `GET /v1/distributions/second-tier`
- `GET /v1/distributions/second-tier/{id}`

```json
{
  "source_shipment_line_id": "<gercek-sevkiyat-satiri-uuid>",
  "recipient_party_id": "<kayitli-alici-uuid>",
  "quantity": "12",
  "unit": "package",
  "distributed_at": "2026-10-27T09:00:00Z",
  "reference": "KURGUSAL-DAGITIM-001",
  "evidence_note": "KURGUSAL sistem operatörü tarafından kaydedilen market bildirimi"
}
```

Örnek tarih gerçek olay tarihiyle değiştirilir; gelecekteki olay kesin kayıt yapılamaz. source_customer_id/source_lot_id/product_id alanları gönderilmez; bunları değiştirmeye çalışan fazladan alanlar 422 üretir. Olmayan UUID 404; geçersiz Decimal/tarih/birim 422; tutarsız kaynak defteri 409 SOURCE_SHIPMENT_MISMATCH; yetersiz belgelenmiş kapasite 409 DOCUMENTED_QUANTITY_EXCEEDED; kronoloji çatışması 409 DISTRIBUTION_CHRONOLOGY_CONFLICT.

GET listesi limit 1–100, UUID cursor/next_cursor; isteğe bağlı source_shipment_line_id, source_lot_id ve recipient_party_id filtrelerini destekler. UUID sırası olay tarihi sırası değildir. GET detay kaynak sevkiyat/satır/lot/ürün/müşteri/alıcı FK'lerini, snapshot'ları, miktar/birim/tarih/referans/kanıt notunu döndürür. company_stock_effect ve company_financial_effect `none`; fiziksel market/alıcı stoğu ve son tüketici satışı null'dır. Gelir veya ikinci kademe satış maliyeti uydurulmaz.

## İade, kapasite ve zaman

Her kaynak ShipmentLine için, transaction kilidi altında:

**kayıtlı ikinci kademe miktarı + şirkete kayıtlı iade miktarı ≤ şirketin kaynak sevkiyat miktarı.**

İkinci kademe ve iade kayıtları, kaynak miktarın birbirinden ayrı tahsisleridir. Şirkete iade edilen miktar yeniden dış dağıtıma açılmaz; dağıtılmış miktarın şirkete iadesi ayrı zincir kanıtı olmadan desteklenmez. Örneğin 30 paket sevk, 12 paket ikinci kademe ve 5 paket şirket iadesi sonrasında yeni tahsis kapasitesi 13'tür. İkinci kademe ve şirket iadesinin toplam 30'u aşması 409 üretir. Yalnız referansı veya alıcıyı değiştirerek kapasite iki kez kullanılamaz.

Yeni dağıtım tarihi, o satırdaki son kayıtlı dağıtım/iade olayından önce olamaz. İkinci kademe kaydı bulunan satıra yeni iade tarihi de son dağıtım/iade olayından önce olamaz. Böylece karışık zincire geçmişe dönük olay sokulmaz; desteklenmeyen belge düzeltmesi açık 409 döner. Eşit tarih kabul edilir, kayıt sırası kapasiteyi güvenle sınırlar. İkinci kademe kaydı olmayan eski iade sözleşmesi korunur; mevcut iade tarih ve satış miktarı denetimleri sürer.

30 sevk ve 12 dağıtım için `unallocated_documented_quantity=18` matematiksel belge bakiyesidir. API bunu `unknown_distributions[].unallocated_documented_quantities[].quantity` olarak, kaynak satır/birim ve `physical_stock=false` ile verir. **Market A'da fiziksel 18 paket kaldığı anlamına gelmez.** Bilinmeyen satış, fire ve daha ileri dağıtım olabilir. Kayıtlı miktarın tamamı tahsis edilmiş olsa da dış envanter doğrulanmış sayılmaz.

## Kilit, idempotency ve stok maliyeti

Bağlı sevkiyatta sıra: idempotency claim → Sale → UUID sıralı Lot → ShipmentLine FOR UPDATE. Bağımsız sevkiyatta Sale bulunmaz; Lot → ShipmentLine sırası korunur. İade de mevcut Sale → sıralı Lot prefix'inden sonra aynı ShipmentLine kilidini alır. Kilit beklemesi sonrasında kapasite READ COMMITTED ile tekrar okunur. Birden çok iadede mevcut sıralı satış satırı dolaşımı korunur.

Yeni kayıt asıl satış/sevkiyatın müşteri/lot/ürün/miktar/birim/konum/stock_movement eşleşmesini kontrol eder; bağlı satışta kesin maliyet snapshot'ı da uyuşmalıdır. Kaynak satış iptali veya terslenmiş hareket kabul edilmez. Aynı miktar ikinci defa şirketten tüketilmez: StockBalance, StockMovement, lot original/consumed miktar/maliyeti, SaleLine, ShipmentLine ve şirket gelirleri değişmez. Yeni kesin kayıt ve idempotency cevabı tek transaction'dır; geç hata ikisini de rollback eder.

commands.execute'ın mevcut 1205/1213/GraphChanged en çok üç denemeli retry'si değiştirilmez. Aynı key/gövde aynı kayıt/201 cevabını döndürür; farklı gövde 409'dur. Yeni key ile aynı kaynak/reference yinelenirse UNIQUE çatışması olur. HTTP cevabı commit sonrasında kaybolsa da aynı key/gövde ikinci dağıtımı oluşturmaz.

## Trace ve recall

Mevcut ileri/geri trace ile recall GET raporuna gerçek `second_tier_distributions` eklenir. Bu olay **yeni üretim lotu veya LotLink oluşturmaz**; üretim soy ağacı aynen kalır. Birinci kademe `buyers` listesi Market A/B/C'yi korur; Dağıtıcı X ikinci kademe kayıt ve snapshot'ıyla görünür. Şirketin `total_shipped_quantities` toplamı 85 kalır; ikinci kademe 12 eklenip 97 yapılmaz.

unknown_distributions içindeki kayıtlı ikinci kademe alıcılar gösterilir; kaydı olmayan B/C için second_tier_recipients null'dır. distribution_completeness yalnız `partial_documentation_only` veya `not_documented`, external_inventory_verified false; market_remaining_quantity ve final_consumer_sold_quantity her durumda null'dır. Kısmi kayıt bütün dağıtımın bilindiği iddiasını oluşturmaz.

Bloke/recall edilmiş veya süresi geçmiş lotun tarihsel bildirimi kaydedilebilir: bu fiziksel sevk izni değildir. Lot kilidi recall ile yazmayı sıralar. Bildirim önce commit ederse recall raporu görür; recall önce commit ederse sonraki GET yeni bildirimi görür. Recall/RecallLot üyeliği, blokajlar ve eski POST replay cevabı değiştirilmez. GET mevcut kayıtlı bilgiyi tutarlı snapshot'tan raporlar; eski POST cevabının güncel rapor olduğu iddia edilmez.

## Kurulum, doğrulama ve demo

Mevcut backend bağımlılıkları kullanılır. Migration üretim açılışında create_all ile ikame edilmez. Yeni tablo boşsa parent'a downgrade mümkündür; tek bir audit kaydı varsa migration **ilk DDL'den önce** reddeder. Üretim audit kaydı sessizce silinemez.

Bu görevde yeni MySQL 8 instance/volume, 127.0.0.1:33329 kullanıldı. Demo `avatar_task15_demo_test`, yıkıcı core `avatar_task15_core_test`, migration `avatar_migration_test`; eski instance ve volume'lar korunur. Özel env repo dışında 0600 izinlidir. Kendi güvenilir env dosyanızı ve ayrı şemalarınızı hazırladıktan sonra:

```bash
python tools/release_env.py run --env-file /tmp/avatar-task15.env -- \
  backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
python tools/release_env.py run --env-file /tmp/avatar-task15.env -- \
  backend/.venv/bin/alembic -c backend/alembic.ini check
python tools/release_env.py run --env-file /tmp/avatar-task15.env --database avatar_task15_core_test --tests -- \
  backend/.venv/bin/python -m pytest tests ml/tests -q
python tools/release_env.py run --env-file /tmp/avatar-task15.env -- \
  backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8006
```

Ayrı terminal:

```bash
AVATAR_API_BASE_URL=http://127.0.0.1:8006 python tools/release_env.py run --env-file /tmp/avatar-task15.env -- \
  backend/.venv/bin/python -m app.demo_second_tier
```

Demo yalnız loopback ve ayrı *_test ortamı kabul eder. Değişmemiş mevcut üretim/market demosuyla KURGUSAL ET→URT→SUC/85 ve A/B/C 30/25/30 oluşturur; A→X 12 bildirimi, gerçek kayıp POST cevabı/same-key retry, ileri/geri trace ve ET recall'ını doğrular. Şirket defteri değişmez; fiziksel market stoğu null kalır. Tam akış ikinci kez çalışır, bütün 30 tablonun hash'i sabit olmalıdır. Yeni test kaynakları repoda; ham log/JUnit/geçici JSON yalnız /tmp altındadır.

Ortak docs/checklist, frontend, Android, ML eğitimi ve Compose değiştirilmez. LOT-10'un bu dar backend kapsamı için kanıt üretilir; ekran/cihaz kabulü ve birleşik main doğrulamasını entegrasyon sorumlusu ayrıca tamamlamalıdır.

# Rework / yeniden işleme — kg sürümü

27 Ekim 2026. `feature/rework-operations`; main tabanı `b9fa0b511ad3d6ea6b3da7d4da3bc8572cd7a83b` (PR #1–#23). [Doğrulama](../database/rework-validation.md).

Rework, daha önce kesin üretilmiş mamul/yan ürünün stoktan gerçek tüketimi, yeni işleme maliyeti ve **yeni lot üretimidir**. Kaynak lotun adını değiştirmez veya maliyetini yeniden yazmaz. İlk sürüm tek kaynak lot/konum ve kg birimiyle, bir veya çok sayıda çıktı lotuyla çalışır. Paket/adet dönüşümü, karantina serbest bırakma ve kalite değerlemesi bu sürümde yoktur.

## Veri modeli ve taslak

Yeni tablo veya migration gerekmedi. Mevcut Operation.kind CHECK'i rework'ü zaten kabul eder. Operation, OperationInput/Output/Difference, ServiceCost, Lot, LotLink, StockMovement ve StockBalance yeniden kullanılır. Şema head'i **e1307a26b001**, domain tablo sayısı29 olarak kalır.

Operation.allocation_snapshot içindeki sürümlü rework_plan, kaynağı/miktarı/nedeni/planlanan ürünleri ve teklif edilen hizmetleri dondurur. Plan UUID'leri create ve post sırasında doğrulanır; JSON plan **kesin lot soy ağacı veya fiilî maliyet kaydı değildir**. Taslak yalnız Operation ve idempotency kaydı ekler; stok ayırmaz/tüketmez, OperationInput/Output/LotLink/ServiceCost oluşturmaz. Plan değişmez; düzeltme için yeni kodla yeni taslak gerekir. Kesin FK zinciri yalnız kapanışta oluşur.

## API

Mevcut X-API-Key koruması ve UUID Idempotency-Key zorunluluğu geçerlidir. Decimal değerler JSON string; zamanlar UTC; SKT takvim kontrolü mevcut backend UTC gün politikasıyla tutarlıdır. Kodlar operasyonlar arasında benzersizdir.

- POST /v1/reworks →201
- GET /v1/reworks?limit=50&cursor=<uuid> →items/next_cursor, yalnız rework; UUID sıralaması tarih sırası değildir.
- GET /v1/reworks/{id} →plan, gerçek girdiler/çıktılar/farklar/maliyet ve lot bağlantıları.
- POST /v1/reworks/{id}/post →200

Taslak gövdesi (yer tutucular gerçek kayıt UUID'leriyle değiştirilir):

```json
{
  "code": "KURGUSAL-RW-001",
  "source_lot_id": "<uretilmis-kg-lot-uuid>",
  "source_location_id": "<isletme-deposu-uuid>",
  "input_quantity": "10",
  "unit": "kg",
  "reason": "KURGUSAL yeniden işleme",
  "output_product_ids": ["<kg-mamul-urun-uuid>"],
  "service_costs": [{"amount": "15.00", "invoice_reference": "KURGUSAL-TEKLIF"}]
}
```

Kapanış gövdesi:

```json
{
  "output_location_id": "<isletme-deposu-uuid>",
  "outputs": [
    {"product_id": "<kg-mamul-urun-uuid>", "lot_code": "KURGUSAL-RW-OUTPUT", "quantity": "9.5", "unit": "kg"}
  ],
  "differences": [
    {"kind": "other_loss", "quantity": "0.5", "reason": "KURGUSAL kayıtlı işleme kaybı"}
  ],
  "service_costs": [{"amount": "15.00", "invoice_reference": "KURGUSAL-FIILI-BEDEL"}]
}
```

`service_costs` kapanışta **zorunludur**, bedel yoksa açıkça `[]` gönderilir. Taslaktaki teklif/varsayım/AI tahmini sessizce kesin maliyete geçirilmez. Pozitif fiilî bedelde kayıt referansı zorunludur; her kalem mevcut ServiceCost'ta EUR olarak saklanır. Prototip fatura referansının gerçek dünyadaki içeriğini doğrulayan bir belge merkezi değildir.

Kaynak/miktar kapanış gövdesinden değiştirilemez; plan esas alınır. Çıktı ürünlerinin kümesi planla eşleşmelidir. Aynı ürünün farklı lot kodlu birden fazla çıktısı olabilir; aynı ürün/kod çifti tekrarlanamaz. Yan üründe explanation gerekir. Çıktılar product_id/lot_code sırasıyla döner; her biri gerçek yeni lot UUID'si, miktar, altı ondalık maliyet ve etkin SKT taşır.

## Kaynak, karantina ve SKT politikası

Kaynak hem taslakta hem kapanışta kilit altında tekrar kontrol edilir:

1. Konum warehouse olmalı. Karantina →409 **REWORK_QUALITY_RELEASE_REQUIRED**; ayrı kalite onayı ve değerleme gerekir. Dış üretici konumu da bu akışın kaynağı değildir.
2. Lot blocked/recall durumunda veya SKT geçmişse reddedilir. Gerçek konum bakiyesi yeterli olmalıdır.
3. Ürün kg birimli finished/byproduct olmalı. Paket/adet ve hammadde reddedilir.
4. Lotun OperationOutput FK'sı, posted external_production/cutting/rework operasyonuna bağlanmalıdır. Yalnız finished etiketiyle satın alınmış lot yeterli değildir.
5. Kaynak original_quantity/total_cost, kesin OperationOutput miktarı/maliyetiyle uyuşmalıdır.

Görev13 iade/iptali orijinal lotun karantina bakiyesinde tutar; tarihsel restored_cost bir kalite onayı değildir. Bu miktar tekrar kullanılamaz. Aynı lotun depoda kalan **orijinal, henüz tüketilmemiş** miktarı koşullar uygunsa kullanılabilir; tüketim algoritması orijinal brüt sayaçlarla çalışır. İade/iptal sayaçları geri sarılmaz veya rework finansmanına karıştırılmaz.

SKT:

- Bilinen kaynak SKT'sinde çıktı tarihi belirtilmez/null ise kaynak tarihi miras alınır; silinerek uzatılamaz.
- Daha erken tarih kabul edilir, daha geç tarih422 REWORK_EXPIRY_EXTENSION.
- Kaynak tarihi bilinmiyorsa çıktı da bilinmiyor kalır; yeni bir tarih atamak422 REWORK_EXPIRY_EVIDENCE_REQUIRED.
- Süresi geçmiş çıktı oluşturulmaz. Raf ömrü/kalite kanıtıyla uzatma süreci yoktur.

## Miktar, maliyet ve FK zinciri

Tam kg dengesi: **girdi = tüm mamul/yan ürün çıktıları + açıklanmış farklar**. Farklar mevcut OperationDifference'da waste/other_loss ve pozitif miktar/nedenle kaydedilir. Sıfır/negatif miktar, açıklamasız0,5kg veya denge hatası422. En az bir pozitif çıktı gerekir; yalnız imha operasyonu bu endpoint değildir.

Kesin maliyet:

- Kaynak payı, mevcut `consumption_cost(total_cost, original_quantity, consumed_quantity, consumed_cost, miktar)` algoritmasının **artımlı** sonucudur.
- Fiilî ek bedeller eklenir; toplam material + service'dir. Para Decimal, ledger DECIMAL(18,6), EUR gösterim2 ondalıktır.
- Dağılım fiilî çıktı kg oranında, product UUID/lot kodu sırasıyla kümülatif HALF_UP yapılır. Son artığın tamamı korunur.
- Kayıp maliyeti bütün kayıtlı çıktılara yüklenir; ayrı zarar/yan ürün piyasa değeri uydurulmaz. Değer ağırlıklı dağıtım bu sürümde yoktur.
- Kaynak original_quantity/total_cost ve geçmiş satış/transfer/iade/iptal maliyetleri değişmez. Yalnız yeni tüketimin brüt sayaç artışı kaydedilir. Her yeni lot kendi gerçek maliyetini taşır.

**KURGUSAL örnek:**20kg/200EUR kaynak lotun10kg'ı tüketilir:100EUR kaynak payı +15EUR kayıtlı işlem =115EUR.9,5kg çıktı +0,5kg açıklanmış kayıp; kaynak depoda10kg kalır.200EUR orijinal maliyet alanı değişmez. Bu örnek PDF'nin gerçek üretim ölçümü değildir.

Source Lot → OperationInput → Rework Operation → OperationOutput → **yeni Lot**; LotLink input/output FK'ları ve miktar atıflarıyla bağlar. rework_input/rework_output hareketleri operation_id FK'sı taşır. Tam tüketilen girdi miktarı, kayıp payı dahil, çıktı kg oranlarında LotLink'lere dağıtılır; bu fiziksel molekül ayrımı kanıtı değildir. Bir çıktı yeni rework'e kaynak olursa mevcut graf doğal olarak çok aşamalı büyür.

## Transaction, recall ve retry

Kilit sırası: idempotency claim → kendi Operation → UUID sıralı kaynak lot → stok bakiyesi. Başka/önceki operasyon başlığı kilitlenmez; recall operasyon kilidi almaz. Kaynak maliyet/tüketim, stok çıkışı, yeni lotlar, çıktı stokları, girdi/çıktı/link/fark/hizmet ve posted durumu tek transaction'dadır. Beklenmedik geç hata tamamını geri alır.

Recall önce kilidi kazanırsa kaynak blocked olur, rework kapanışı reddedilir. Rework önce commit ederse yeni FK çıktıları görünür; recall kilit sonrası grafı tekrar kontrol eder ve genişleme varsa mevcut GraphChanged protokolüyle bütün transaction'ı yeniden başlatır. Yeni rework çıktıları da bloke edilir. Graf veya recall algoritması değiştirilmedi; ad/kod eşleştirmesi yapılmaz.

commands.execute'ın1205/1213/GraphChanged için en çok3 denemesi korunur. Yeni rework'e özel gerçek1213 testi, haricî bakım kilidinin oluşturduğu döngüde rollback/retry ve tek tüketim/çıktıyı doğrular. Aynı key/body create veya post cevabını aynen döndürür; değişik gövde409. Başka key ile yeniden kapanış OPERATION_POSTED. Sonradan bloke olmuş bir işlemin eski cevabının replay edilmesi yeni stok üretmez.

## Çalıştırma ve tekrar demo

Gerçek koşu ayrı `avatar-task14-mysql` instance/volume, host127.0.0.1:33328 üzerinde yapıldı. Core `avatar_task14_core_test`, demo `avatar_task14_demo_test`, migration testleri aynı yeni instance içindeki `avatar_migration_test`; mevcut instance/volume'lar korunur. Özel env dosyası repo dışında0600 izinlidir. Backend bağımlılıkları ve bu ayrı şemalar hazırlanmış olmalıdır.

```bash
python tools/release_env.py run --env-file /tmp/avatar-task14.env --database avatar_task14_core_test --tests -- \
  backend/.venv/bin/python -m pytest tests ml/tests -q

python tools/release_env.py run --env-file /tmp/avatar-task14.env -- \
  backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
python tools/release_env.py run --env-file /tmp/avatar-task14.env -- \
  backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8005
```

Ayrı terminalde:

```bash
AVATAR_API_BASE_URL=http://127.0.0.1:8005 python tools/release_env.py run --env-file /tmp/avatar-task14.env -- \
  backend/.venv/bin/python -m app.demo_rework
```

Demo yalnız loopback ve ayrı `*_test` ortamı kabul eder. KURGUSAL alış→ilk üretim→rework→yeni lot→satış/sevkiyat→ata recall→LOT_BLOCKED akışını çalıştırır. İlk başarılı rework kapanışının gerçek HTTP cevabı proxy'de düşürülür; aynı UUID/gövdeyle retry aynı operasyonu döndürür. Bütün akış tekrar edilir, tüm29 tablonun tek aggregate hash'i eşit olmalıdır. Tarihler ilk üretimin kayıtlı SKT'sinden tekrar alınır; ertesi gün yeni request gövdesi üretilmez. Stok sıfırlanmaz.

Komut stdout'u kısa sonuç JSON'udur. Ham log/JUnit/geçici JSON'lar `/tmp` altında tutuldu; kaynak ağacına tekrar ekran görüntüsü veya büyük dump eklenmez. Ortak docs/checklist, frontend/Android/ML eğitim kodu ve Compose bu görevde değiştirilmez.

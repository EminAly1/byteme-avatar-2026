# Bağımsız lot transferi, müşteri iadesi ve sevk öncesi iptal

Görev 13, 26 Ekim 2026. Main tabanı `b569830` (PR #1–#21); branch `feature/lot-transfers-returns`. Yalnız backend/database/tests değişir. Bu belge ortak API/ER belgelerine aktarılacak **uygulanmış backend sözleşmesidir**; ortak docs/checklist ve istemciler bu görevde değiştirilmez. [Gerçek test ve demo sonuçları](../database/transfers-returns-validation.md).

## Güvenlik ve kapsam

Bütün yollar mevcut X-API-Key kontrolündedir; bu kullanıcı/rol sistemi değildir. Yazmada UUID Idempotency-Key gerekir. Ondalıklar JSON string, miktar en fazla 6, net EUR tutar 2 ondalıktır. Paket/adet miktarı tam sayı olmalıdır. Zaman alanları opsiyonel timezone içeren ISO8601; verilmezse sunucu UTC kayıt zamanı kullanılır. İşlem tarihi ile değişmez StockMovement.created_at kayıt zamanı ayrı kavramlardır.

**İade ve iptal stoğu yalnız karantinaya girer.** Satılabilir depoya otomatik restorasyon, kalite serbest bırakma veya yeniden değerleme uygulanmaz. Özellikle iptal, yeni bir müşteri iadesi değildir: yalnız hiç sevk edilmemiş satışın tam gelir/maliyet düzeltmesidir. Ürün şirketten çıkmamış olsa da bu dar ve güvenli sürüm, miktarı karantinaya geri alır. Ayrı kalite ve değerleme akışı olmadan tekrar satılamaz.

Lot.consumed_quantity/consumed_cost **geçmiş brüt tüketim sayaçlarıdır**. İade/iptalde geri sarılmaz, original_quantity/total_cost ve eski SaleLine maliyetleri değiştirilmez. Bu seçim kısmi tüketimlerde kümülatif yuvarlama algoritmasını korur. Karantina çıkışını sıradan transferle açmak bu değerleme garantisini bozar; API bunu reddeder. Gelecekteki kalite onayı, geri kazanım maliyetini ayrıca tüketebilen bir değerleme tasarımı ve testler gerektirir; konum türünü değiştirerek atlanamaz.

## 1. Transfer

`POST /v1/transfers` →201; `GET /v1/transfers?lot_id=<uuid>&limit=50&cursor=<uuid>`; `GET /v1/transfers/{id}`.

```json
{
  "from_location_id": "<depo-A-uuid>",
  "to_location_id": "<depo-B-uuid>",
  "lot_id": "<gercek-lot-uuid>",
  "quantity": "7",
  "unit": "kg",
  "reason": "KURGUSAL depo transferi",
  "reference": "KURGUSAL-TRANSFER-001",
  "transferred_at": "2026-10-26T08:00:00Z"
}
```

UUID alanlarındaki açıklayıcı yer tutucular çalıştırmada gerçek API kayıt UUID'leriyle değiştirilir. Liste items/next_cursor biçiminde ve UUID sıralıdır; cursor tarih sıralaması değildir. Detay gerçek product_id, out_movement_id/in_movement_id, iki hareket ve `cost_effect=none` döndürür. Hareketlerin transfer_group_id değeri transferin gerçek ID'sidir; iki ayrı hareket aynı lotta −7/+7 kaydeder. OperationInput veya tüketim maliyeti oluşturulmaz.20 kg için A13/B7, toplam20 ve194 EUR başlangıç maliyeti korunur.

Politika:

| Kaynak → hedef | Kural |
| --- | --- |
| Warehouse → warehouse | Lot blokeli veya SKT geçmiş olamaz; yeterli stok gerekir |
| Warehouse → quarantine | Blokeli/SKT geçmiş lot da **kısıtlı muhafaza** için taşınabilir; blok kaldırılmaz |
| Quarantine → quarantine | İzinli; stok kullanılabilir hale gelmez |
| Quarantine → warehouse |409 QUARANTINE_RELEASE_REQUIRED |
| Herhangi → external_producer veya tersi |422 INVALID_LOCATION; mevcut üretim dispatch protokolü kullanılır |

Aynı kaynak/hedef422; birim veya kesirli adet422; yetersiz stok409; bulunmayan kayıt404. Verilmiş transfer tarihi lot girişinden önce olamaz. Lot kilidi → bakiye kilitleri; çıkış, giriş, transfer ve idempotency cevabı tek transaction'dır. İkinci hareketin flush'ından sonra hata enjekte edilen testte bile tamamı rollback olur.

## 2. Müşteri iadesi

`POST /v1/returns` →201; `GET /v1/returns?sale_id=<uuid>&limit=50&cursor=<uuid>`; `GET /v1/returns/{id}`.

```json
{
  "sale_id": "<kaynak-satis-uuid>",
  "acceptance_location_id": "<karantina-uuid>",
  "reason": "KURGUSAL kısmi müşteri iadesi",
  "reference": "KURGUSAL-IADE-001",
  "lines": [
    {"sale_line_id": "<gercek-satis-satiri-uuid>", "quantity": "2", "unit": "kg"}
  ]
}
```

Opsiyonel returned_at, satıştan ve kaynak sevkiyattan önce olamaz. Müşteri/ürün/lot istemciden uydurulmaz, kaynak satış satırından alınır. Satır **kayıtlı bağlı sevkiyata** sahip olmalıdır; shipment_line_id fiziksel FK olarak saklanır. Kaynak shipment, sale, müşteri, lot, birim, miktar ve hareketin tutarlılığı kontrol edilir. Bağımsız sevkiyatta satış FK'sı yoksa bu endpoint otomatik eşleme yapmaz. Sevksiz satışta SALE_LINE_NOT_SHIPPED; iptal edilmiş satışta SALE_CANCELLED.

Aynı satış satırına çok sayıda kısmi iade yapılabilir. Sale başlığı FOR UPDATE kilitlenir; önceki iadeler bu kilit altında toplanır. Toplam miktar satılmış miktarı aşamaz (RETURN_EXCEEDS_SALE). Aynı request içinde satış satırı tekrarlanamaz. Kabul konumu zorunlu ve quarantine olmalıdır; eksik konum sessizce depoya yönlendirilmez. Blokeli/SKT geçmiş lot **iadeyle karantinaya kabul edilebilir**, satılabilir hale gelmez.

Her iade satırı orijinal lota pozitif customer_return hareketi ekler. Orijinal satış/çıkış değiştirilmez. **Kısmi iade, hareketin tam terslenmesi değildir:** reversal_of null, asıl satış/satır/sevkiyat FK'ları CustomerReturnLine üzerindedir. İadelerin toplamı tam satış miktarına ulaşsa da bunlar aynı kısmi kabul tarihçesidir; tam iptal hareketine dönüştürülmez.

## 3. İptal

`POST /v1/sales/{id}/cancel` →200; `GET /v1/sales/{id}/cancellation` detay/404 döndürür.

```json
{
  "acceptance_location_id": "<karantina-uuid>",
  "reason": "KURGUSAL sevk öncesi iptal"
}
```

Opsiyonel cancelled_at satıştan önce olamaz. İptal yalnız satışın tamamına uygulanır. Bir satırı bile sevk edilmişse SALE_ALREADY_SHIPPED; iade kaydı varsa SALE_HAS_RETURNS; daha önce iptalse SALE_ALREADY_CANCELLED. Bağlı sevkiyat aynı Sale kilidini aldığı için eşzamanlı iptal/sevkiyatta yalnız biri kazanır. İptal sonrası yeni sevkiyat SALE_CANCELLED ile reddedilir.

Her satır için aynı gerçek lot ve **orijinal depo konumunda** pozitif sale_cancellation hareketi yazılır. `reversal_of` orijinal negatif satış hareketine FK olur; miktar tam tersidir. Ardından aynı transaction içinde cancel_hold_out/cancel_hold_in hareketleri miktarı orijinal depodan karantinaya taşır. Bu çiftin transfer_group_id değeri iptal satırının ID’sidir ve toplamı sıfırdır. İptal satırı üç hareketi de stock_movement_id, quarantine_out_movement_id ve quarantine_in_movement_id FK’larıyla saklar. Detay cevabı movement ve quarantine_movements alanlarını ayrı döndürür. Orijinal depodaki geçici pozitif kayıt ayrı commit edilmez; okuyucu bu ara stoğu kullanılabilir görmez. Nihai durum satılabilir stok restorasyonu değildir; iptal edilen miktarın karantinaya tam geri kabulüdür. UNIQUE(reversal_of), NULL'ları serbest bırakarak her orijinal hareketin en fazla bir tam reversal'ını DB seviyesinde garanti eder. Satış/satır/önceki hareket silinmez, yeni SaleCancellation ve satırları kalıcıdır.

## 4. Maliyet, kredi ve kârlılık

`restored_cost` tarihsel **defter maliyetidir**; iade ürünün geri kazanılabilir piyasa değeri veya kalite onayı değildir. Karantina ürününe ilişkin değer düşüklüğü/vergi/imhaya dair veri yoksa bir tutar uydurulmaz; bunlar ayrı kalite/değerleme sürecinde ele alınmalıdır. Net kâr alanı yalnız kayıtlı satış kredisi ve tarihsel COGS düzeltmesine dayanır.

İade kredisi nakit ödeme veya resmî credit-note iddiası değildir. `cash_refund_status=not_recorded`; kaydedilen şey net satış geliri düzeltmesi ve tarihsel COGS ters kaydıdır. EUR dışı, vergi, iskonto, ödeme sağlayıcısı veya banka iadesi bu sürümde yoktur.

Satırın orijinal miktarı Q, toplam net tutarı R, kesin tüketim maliyeti C olsun. Önceki iade miktarı q0, yeni kümülatif miktar q1 için:

- Kredi = HALF_UP_2(R×q1/Q) − önceki kayıtlı krediler.
- Geri kazanım maliyeti = HALF_UP_6(C×q1/Q) − önceki kayıtlı maliyet düzeltmeleri.
- q1=Q olduğunda hedefler doğrudan R/C'dir; son artığın tamamı korunur.
- İptal, iadelerin olmadığı tam satış için her satırın R/C tutarını aynen kaydeder.

0,03 EUR tutarlı3 kg satışta0,5+0,5+2kg iade kredileri0,01+0,00+0,02EUR olur; ayrı satır yuvarlamasıyla para yaratılmaz. Maliyet **gösterim EKP'sinden veya güncel lot bakiyesinden hesaplanmaz**. Başlık toplamları DECIMAL(18,6) sınırı dışında ise VALUE_OVERFLOW422 ve tam rollback uygulanır.

Stok miktarı açıklaması: `on_hand = original_quantity − gross_consumed_quantity + returned_quantity + cancelled_quantity`. Değer açıklaması: `on_hand_cost = total_cost − gross_consumed_cost + recovered_cost`. Bu, aynı lotun orijinal maliyetini değiştirmek değildir; ayrı karantina geri kazanım kayıtlarının mutabakatıdır.

`GET /v1/sales/{id}/profitability`:

- Mevcut üst alanlar ve lines **orijinal satış gelirini ve tüketim maliyetini** korur; eski alanların anlamı değiştirilmez.
- Yeni adjustments: state(active/partially_returned/returned/cancelled), return_ids/cancellation_id, return_credit_eur, cancellation_credit_eur, cost_reversal_eur ve satır başına original_sold_quantity/returned_quantity/cancelled_quantity.
- Yeni net_after_adjustments: orijinal gelir − krediler; orijinal COGS − maliyet düzeltmeleri; bunlardan brüt kâr/marj. Gelir0 ise marj null.
- Read endpoint tek REPEATABLE READ snapshot kullanır; eşzamanlı iade commit'iyle başlık/satır miktarları karışmaz. GET tablo hash'lerini değiştirmez.

Demo:5 kg×20 EUR satışta gelir100/COGS48,50;2kg iade kredisi40 ve maliyet düzeltmesi19,40; net gelir60, COGS29,10, brüt kâr30,90EUR. Ayrı3 kg sevksiz satışın iptali60EUR/29,10EUR düzeltir; net0. Hiçbir nakit ödeme sonucu uydurulmaz.

## 5. Şema, trace ve recall

Yeni tablolar: stock_transfers, customer_returns, customer_return_lines, sale_cancellations, sale_cancellation_lines. Mevcut Lot kolonları ve Sale/SaleLine tutarları değişmez. Tüm anahtarlar gerçek FK; transferin iki hareketi, iade satırının kaynak SaleLine/ShipmentLine/lot/hareketi ve iptalin SaleLine/reversal hareketi saklanır. API müşteri ve product_id'yi kaynak kayıtlardan türetir.

Trace ileri/geri mevcut lot UUID'sini ve üretim FK grafını korur; yeni lot veya üretim ilişkisi uydurulmaz. Rapora transfers/customer_returns/sale_cancellations eklenir. Alıcı miktarları orijinal satılan/sevk edilen, iade ve iptal miktarlarını ayrı gösterir. recorded_delivery_less_returns_quantity yalnız kayıtlı sevk−iade dengesidir; **marketin kalan stoğu değildir**. market_remaining_quantity ve bilinmeyen ikinci kademe null kalır. affected_lots_only, çok lotlu başlığın tam tutarıyla yalnız etkilenen satırlarını ayırır.

Recall aynı gerçek lotu bloke eder; karantina stoku da bu lota aittir. İade/iptal blocked alanını değiştirmez. Recall önce de sonra da kazansa geri kabul karantinada kalır; yeni satış/warehouse transferi blokajı aşamaz. GET recall mevcut stok ve düzeltmeleri gösterir; recall'ın ilk idempotent cevabı tarihsel orijinal cevaptır.

Kilit sırası: idempotency claim → Sale (iade/iptal/bağlı sevkiyat için) → UUID sıralı lotlar → stok bakiyeleri. Transfer/recall Sale kilidi almaz. Recall'ın rapor SELECT'leri Sale başlığını kilitlemez; ters kilit döngüsü oluşturulmaz. Mevcut commands.execute tüm transaction'ı1205/1213 veya GraphChanged sonrası en çok3 kez dener. Aynı key/body orijinal cevabı döndürür; farklı body409. Replay sırasında blokeli hale gelmiş eski işlemin cevabı dönmesi yeni stok hareketi değildir.

## 6. Migration ve test/demo

Head **e1307a26b001**, parent dc9109a1f001. Upgrade eski çift reversal_of varsa **DDL'den önce** reddeder; tarihçe otomatik silinmez. Downgrade yeni beş tabloda herhangi bir kayıt varsa audit kaybını önlemek için DDL'den önce reddeder. Boş şemada child tablolar FK/indexleriyle birlikte kaldırılır; InnoDB'nin self-FK destek indeksi UNIQUE kaldırılmadan önce korunur. MySQL DDL auto-commit'tir; uygulama yazarları durdurulmadan downgrade yapılmaz. Bu, iş akışı iptalinin alternatifi değildir.

Gerçek koşuda ayrı avatar-task13-mysql instance/volume, host127.0.0.1:33327, core avatar_task13_core_test, son demo avatar_task13_acceptance_test (ilk taslak avatar_task13_demo_test korundu) ve yalnız migration testlerine ait avatar_migration_test kullanıldı. Mevcut release instance/volume'ları değiştirilmedi. Özel MYSQL_*/AVATAR_API_KEY env'i `/tmp/avatar-task13-final.env` içinde0600; Git'e eklenmez.

```bash
# Repository kökünde, önceden hazırlanmış özel Task13 ortamıyla:
python tools/release_env.py run --env-file /tmp/avatar-task13-final.env --database avatar_task13_core_test --tests -- \
  backend/.venv/bin/python -m pytest tests ml/tests -q

python tools/release_env.py run --env-file /tmp/avatar-task13-final.env -- \
  backend/.venv/bin/alembic -c backend/alembic.ini upgrade head

python tools/release_env.py run --env-file /tmp/avatar-task13-final.env -- \
  backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8004
```

Ayrı terminalde aynı özel env ve aynı API/DB ile:

```bash
AVATAR_API_BASE_URL=http://127.0.0.1:8004 python tools/release_env.py run --env-file /tmp/avatar-task13-final.env -- \
  backend/.venv/bin/python -m app.demo_transfers_returns --output /tmp/task13-demo.json
```

Demo sabit UUID5 request anahtarları ve aynı gövdelerle bütün akışı iki kez çalıştırır;29 tablo hash'i ve cevaplar eşit olmalıdır. İlk20 kg→13/7 transferinin tarihsel adımı, sonraki fiziksel durum10/2/5 ve blokajdan ayrı raporlanır. Stok resetlenmez. Eski app.demo/app.demo_sales_shipments/app.demo_cutting/app.demo_recall komutları da bu yeni modelle denendi; payload veya anahtarları değiştirilmedi.

Kanıt kapsamı: gerçek MySQL kilit yarışları, haricî bakım kilidinin zorladığı **gerçek1213 deadlock + transfer retry**, ayrı kontrollü1213 retry tavanı, iki transfer/satış, recall/transfer, iki iade, iade/iptal ve iptal/sevkiyat; gerçek TCP'de commit sonrasında cevap bekleme timeout'u ve aynı komutun replay'i. Test DB temizliği FK'leri kapatmadan reversal yapraklarını önce siler; bu yalnız izole test fixture'ıdır, işletme API'si değildir.

## Kalan kapsam

Kalite serbest bırakma/yeniden değerleme, iadenin satılabilir stoğa dönüşü, bağımsız sevkiyat iadesinin kaynağa otomatik eşlenmesi, kısmi satış iptali, nakit geri ödeme, resmî belge, rework ve istemci ekranları uygulanmadı. LOT-05'in transfer/iade/tam sevksiz iptal backend kısmı bu sürümdedir; rework ve kalite sonrası yeniden kullanım ayrı işlerdir. Ortak API/ER/checklist belgeleri entegrasyon sorumlusunca ayrıca güncellenmelidir.

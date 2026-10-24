# REST API sözleşmesi

## Şu anda uygulanan

| Metot / yol | Sonuç |
| --- | --- |
| GET /health | 200 `{"status":"ok"}`; yalnızca süreç canlılığı |
| GET /health/ready | MySQL üzerinde SELECT 1 başarılıysa 200 `{"status":"ok","database":"ok"}`; aksi halde 503 ve güvenli detail |
| GET /openapi.json | Yalnızca uygulanmış endpoint'lerin üretilmiş sözleşmesi |
| GET /docs | FastAPI geliştirme API dokümanı |

Frontend geliştirme sunucusu `/api/*` isteklerini backend’e prefix’i kaldırarak aktarır. Örneğin `/api/health` → `/health`, gelecekte `/api/v1/products` → `/v1/products`. Backend doğrudan `/v1` prefix’ini kullanır.

## Planlanan v1 (henüz uygulanmadı)

Backend prefix `/v1`. JSON UTF-8; kimlikler UUID, tarihler ISO8601 UTC. Para/miktar ondalık string: `"970.00"`, `"100.000000"`. Currency EUR. Listeler `{"items":[],"next_cursor":null}` ve limit≤100. Kullanıcı rolleri (admin/operator/sales/viewer) domain API açılmadan uygulanacak; health kimlik doğrulama gerektirmez.

Yazma komutları `Idempotency-Key: <UUID>` ister; aynı key+aynı canonical body aynı durum ve cevabı döndürür. Aynı key+farklı body 409. Başarılı create 201, post/action 200, doğrulama 422, bulunamadı 404, çatışma/blok/yetersiz stok 409, oturum 401/403. Domain hata formatı planı `{"error":{"code":"LOT_BLOCKED","message":"...","details":{}}}`; mevcut FastAPI health/validation cevabı bu domain envelope'una dahil değildir.

| Metot / yol | İstek / çıktı ve sorumluluk |
| --- | --- |
| GET, POST /v1/products | SKU, name, type, base_unit, package_weight_kg nullable |
| GET, POST /v1/parties | roller, ad, iletişim |
| POST /v1/receipts | supplier_id, received_at, lines:[product_id, external_lot_code, quantity, total_cost, expires_at?]; lot + giriş hareketleri atomik |
| GET /v1/recipes | sürümlü parçalama reçetesi ve dağıtım katsayıları |
| POST /v1/recipes | kind, output ürünleri, allocation_method, weights; yeni version |
| GET, POST /v1/operations | kind, code, producer_id?, recipe_version_id?; taslak oluşturma |
| POST /v1/operations/{id}/dispatch | from/to_location_id, lot_id+quantity satırları; dış üreticiye transfer, tüketim değil |
| POST /v1/operations/{id}/post | consumed_inputs, outputs, returned_inputs, service_costs, loss_quantity, loss_reason, allocation_method; gerçek kapanış, maliyet ve lot grafı atomik |
| GET /v1/operations/{id} | gerçek miktarlar, EKP, VKP varsa kâr/marj, tarihçe |
| GET /v1/stocks | lot_id/product_id/location_id filtreleri; mevcut, bloke, kullanılabilir miktar |
| GET /v1/stock-movements | lot/tarih/type filtreli değişmez defter |
| POST /v1/transfers | from/to_location_id, lot_id, quantity; iki hareket atomik |
| POST /v1/sales | customer_id?, lines:[lot_id,location_id,quantity,unit_price]; transaction, lot blok kontrolü; stock_movement_id içeren cevap |
| POST /v1/shipments | customer_id, sale_id?, lines:[lot_id,quantity,location_id]; sale_id varsa mevcut hareket referansı, ikinci stok düşümü yok |
| POST /v1/returns | original_line_id, lot_id, quantity, quarantine_location_id, reason; orijinal miktarı aşamaz, blok kendiliğinden kalkmaz |
| POST /v1/operations (kind=rework) | yeniden işleme de aynı input/output lot grafı protokolü |
| GET /v1/lots/{id}/trace?direction=forward\|backward | kesin lotlar, miktarlı edges, emirler, tedarikçi, mevcut stoklar, sevkiyatlar, bilinen alıcılar; unknown_distributions açıklaması |
| POST /v1/recalls | source_lot_id, reason; kaynak ve tüm türev lotları atomik blokla, recall id dön |
| GET /v1/recalls/{id} | affected_lots, customer bazlı miktarlar/sevkiyat/iletişim; yalnız kaydedilmiş ikinci kademe |
| GET /v1/reports/{purchases,production,cutting,sales,recalls} | tarih ve ürün filtresi; kaynak işlem kimliklerine inilebilir |
| POST /v1/predictions/production | planned input + model_version?; beklenen çıktı ve EKP, model sürümü/uyarılar |
| POST /v1/predictions/cutting | species, input_weight; beklenen parça ağırlıkları, model sürümü/uyarılar |
| GET /v1/operations/{id}/prediction-comparison | prediction, actual, deviation; henüz gerçekleşmeyen actual=null |

### Örnek kapanış sözleşmesi

```json
{
  "consumed_inputs": [{"lot_id": "<ET-2026-001 UUID>", "quantity": "100.000000"}],
  "outputs": [{"product_id": "<UUID>", "lot_code": "SUC-2026-045", "quantity": "85.000000", "unit": "package"}],
  "returned_inputs": [],
  "service_costs": [{"amount": "467.50", "currency": "EUR"}],
  "allocation_method": "quantity",
  "loss_quantity": "22.000000",
  "loss_reason": "Örnek açıklama; işletme doğrulaması gerekir"
}
```

Bu örnek yalnızca et satırını kısaltarak gösterir; PDF'nin tam demosunda 2 kg baharat ve 5 kg bağırsak lotları da consumed_inputs içinde bulunmalı. Eksik satırlı bu örnekle 1.543,50 EUR toplamı hesaplanamaz. Karma çıktı birimlerinde miktar anahtarı normalize kg esasını kullanır. Yanıt birim gerçek maliyeti 6 haneli string ve gösterim değerini ayrı alanlarda döndürür.

### Senkronizasyon

Android Room outbox → aynı REST komutları → server onayı → yerel durum güncellemesi. Cihaz stok/maliyet otoritesi değildir. Offline yalnızca taslak; recall kontrolü olmadan kesin satış yapılamaz. İlk sürüm online authoritative snapshot kullanır; delta sync endpoint'i şimdilik planlanmaz.

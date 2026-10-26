# Uygulanan REST API sözleşmesi

Görev 12. Normatif giriş şemaları [canlı sistemden alınan OpenAPI](release-validation/openapi.json), gerçek davranış [backend](release-validation/backend-tests.txt) ve [Chromium](release-validation/frontend-e2e.txt) testleriyle doğrulanır. Backend `/v1`, yerel frontend `/api/v1` kullanır; proxy yalnız `/api` önekini kaldırır.

## Ortak kurallar

- UUID kimlikleri; ISO8601 UTC zaman, SKT `YYYY-MM-DD`; EUR ve miktarlar JSON **string**. Birimler kg/package/unit.
- Bütün `/v1` yolları `X-API-Key` ister. Bu kullanıcı oturumu/RBAC değildir. Web anahtarı Node/Vite sürecinde, Android anahtarı runtime Keystore'da kalır.
- Yazmalarda UUID `Idempotency-Key` zorunlu. Aynı scope/key/canonical body orijinal durum/cevap; farklı body 409. Kayıp cevabı yeni key ile telafi etmeyin.
- Liste: `items`, `next_cursor`; limit 1–100. UUID cursor zaman sıralaması garantisi vermez. Bütün listelerde aynı filtreler yoktur; OpenAPI'deki gerçek query parametreleri esastır.
- Create 201; operasyon dispatch/post 200; validation 422; yok 404; blok/yetersiz stok/çakışma 409; yanlış anahtar 401; DB/model hazır değil 503. Domain hata: `{"error":{"code":"LOT_BLOCKED","message":"...","details":{}}}`. Pydantic/health hataları FastAPI `detail` biçimindedir.

## Gerçek yollar

| Metot / yol | Davranış |
| --- | --- |
| GET /health | DB'den bağımsız canlılık |
| GET /health/ready | MySQL SELECT 1; model hazırlığını ayrıca kontrol edin |
| GET /docs, /openapi.json | API açıklaması ve uygulanmış giriş şemaları |
| GET, POST /v1/products | sku/name/type/base_unit; opsiyonel species/package_weight_kg |
| GET, POST /v1/parties | name, roles supplier/customer/producer, opsiyonel contact |
| GET, POST /v1/locations | name/kind; dış üreticide party_id |
| GET, POST /v1/receipts | supplier_id/location_id/received_at/reference; lines: ürün, lot kodu, miktar, maliyet, opsiyonel unit_price/expires_at |
| GET /v1/receipts/{id} | Satır/lot FK'ları ve gerçek alış tutarları |
| GET, POST /v1/operations | Dış üretim taslağı; code/producer_id. Kesim için özel endpoint kullanılır. |
| GET /v1/operations/{id} | Gerçek input/output, cost, hizmet ve lot bağlantıları |
| POST /v1/operations/{id}/dispatch | from/to_location_id, lot+quantity; aynı lotun konumlar arası iki hareketi, tüketim değildir |
| POST /v1/operations/{id}/post | consumed_inputs, outputs, output_location_id, returned_inputs, service_costs, açıklanmış loss; atomik kapanış |
| GET /v1/lots, /v1/lots/{id} | Kesin lot kayıtları/SKT/blok ve kaynak ürün |
| GET /v1/stocks | lot_id/product_id/location_id filtreleri; kayıtlı ve kullanılabilir miktar |
| GET /v1/stock-movements | lot/location/operation/type filtreleri, değişmez defter |
| GET, POST /v1/recipes | code/version/species/input_product_id/allocation_method; lines product_id/reference_eur_per_kg |
| GET /v1/recipes/{id} | Gerçek sürüm ve parça kayıtları |
| POST /v1/recipes/{id}/availability | available; maliyet snapshot'larını değiştirmez |
| GET, POST /v1/cuttings | recipe_version_id/code ile kesim taslağı |
| GET /v1/cuttings/{id} | Fiilî girdiler/çıktılar/farklar, maliyet ve lot bağlantıları |
| POST /v1/cuttings/{id}/post | consumed_inputs, output_location_id, parça lotları ve açıklamalı differences; 25=22+3 dengesi |
| GET, POST /v1/sales | customer_id zorunlu; lines lot_id/location_id/quantity/unit?/unit_price; tek stok çıkışı |
| GET /v1/sales/{id} | Satır/StockMovement FK, net tutar ve tüketim maliyeti |
| GET /v1/sales/{id}/profitability | Salt okunur kayıtlı VKP/brüt kâr/marj; aşağıdaki sözleşme |
| GET, POST /v1/shipments | customer_id, opsiyonel sale_id; lot/location/quantity/unit ve bağlıysa sale_line_id |
| GET /v1/shipments/{id} | Alıcı snapshot'ı, bağlı satış ve hareket FK'ları |
| GET /v1/lots/{id}/trace?direction=forward\|backward | Kesin source/lots/context_lots/operations/edges/stocks/buyers ve ürün/birim bazlı sevk toplamı |
| POST /v1/recalls | source_lot_id/reason; bütün türevleri atomik bloke eder |
| GET /v1/recalls/{id} | Kesin üyelik, güncel bakiyeler, market/iletişim/sevk raporu |
| GET /v1/predictions/models | İki modelin metadata/özellik sınırları/sentetik MAE-RMSE bilgisi |
| POST /v1/predictions/production | İşlem öncesi kg/maliyet/ön teklif, et türü, paket ağırlığı, sentetik profil; opsiyonel operation_id/output_product_id |
| POST /v1/predictions/cutting | species=Kuzu/input_weight_kg/recipe_version_id/part_products; opsiyonel operation_id |
| GET /v1/predictions/{id} | Saklı tahmin, mevcut kesin gerçekleşme ve backend Decimal sapmaları |

Operasyon kapanışı gerçek location_id, output_location_id ve bütün girdi lotlarını ister. Eksik alanlı eski foundation örneği normatif değildir. [Çalışan üretim demo payload'ı](../backend/app/demo.py), [kesim](../backend/app/demo_cutting.py), [satış/sevkiyat](../backend/app/demo_sales_shipments.py), [ML payload'ları](../ml/INTEGRATION.md) ve OpenAPI tam örneklerdir.

Bağlı sevkiyat yalnız müşterisi/lotu/konumu/birimi/miktarı eşleşen, henüz sevk edilmemiş **tam satış satırını** kabul eder; mevcut hareketi paylaşır. Bağımsız sevkiyat yeni fiziksel çıkıştır, satış geliri üretmez.

## Kayıtlı satış kârlılığı

`GET /v1/sales/{sale_id}/profitability` kimlik doğrulamalı, salt okunur ve migration gerektirmeyen ek rapordur. Var olan POST ve satış ayrıntısı cevapları değişmedi.

- `net_revenue_eur`: Sale.total_amount, iki ondalık.
- `recognized_cost_eur`: satırların saklı consumed_cost toplamı, altı ondalık.
- `gross_profit_eur = net_revenue − recognized_cost`, altı ondalık; `gross_profit_display_eur` iki ondalık HALF_UP.
- `margin_percent = gross_profit / net_revenue × 100`, altı ondalık; net gelir sıfırsa **null**, zarar gizlenmez.
- `lines`: sale_line_id/lot_id/stock_movement_id/quantity/unit; `vkp_eur_per_unit` gerçek net satış birim fiyatı, `recognized_unit_cost_eur` satır maliyeti/miktarı; aynı gelir/maliyet/kâr/marj alanları.
- `basis=recorded_net_sale_and_consumed_lot_cost`, `currency=EUR`, kapsam sınırlamaları açıklanır. Vergi, iskonto, iade ve genel gider muhasebesi yoktur. Net şirket kârı veya gelecekteki fiyat tahmini değildir.

Kurgusal Market A örneği: net 750,00 EUR; kayıtlı maliyet 544,764706 EUR; brüt kâr 205,235294 EUR (gösterim 205,24); marj %27,364706. **25 EUR/paket demo varsayımıdır, PDF fiyatı değildir.** Tam örnekler [demo kanıtında](release-validation/demo.json). Sonradan lot tüketilmesi veya recall raporu değiştirmez; maliyet snapshot'tan gelir. GET öncesi/sonrası bütün domain tablolarının hash eşitliği MySQL testinde doğrulandı.

## ML ve senkronizasyon sınırı

Tahmin body'lerinde fiilî sonuç/EKP/kapanış maliyeti veya actual_* alanları kabul edilmez. Bağlı tahmin işlem başlamadan yapılır; geç kalmış tahmin 409 FORECAST_TOO_LATE. Model yok/geçersizse 503 MODEL_UNAVAILABLE; sahte fallback yoktur. GET eski tahmini yeniden hesaplamaz; saklı sürümü korur. Gerçekleşme yoksa actual/deviation null; gerçek sıfırsa yüzde null. İki model **SYNTHETIC**, gerçek tarihsel veri 0.

Room outbox aynı key/body ile onay alır; offline yalnız taslaktır. Cihaz stok ve maliyet hesaplamaz. Delta sync veya kapalı uygulamada arka plan gönderimi yoktur.

## Henüz uygulanmayan yollar

Genel `/transfers`, müşteri `/returns`/satış iptali, rework komutu, kullanıcı oturum/rol API'si, ikinci kademe dağıtım kayıt API'si, genel `/reports/*` ve `/operations/{id}/prediction-comparison` **yoktur**. Mevcut liste/detay/trace/prediction cevapları raporlama için kullanılır. Recall ve prediction için genel liste endpoint'i de yoktur; UI bilinen gerçek UUID'leri açar. Bu yolları taslak oldukları halde çalışan sözleşme gibi çağırmayın.

# FastAPI entegrasyonu, değişmez tahmin ve gerçekleşme

## Temiz yerel kurulum

Depo kökünde [README](README.md) bağımlılıklarını kurun. Gerçek işletme verisinden ayrı MySQL 8 kullanın. Parolaları dosya/Git/log yerine process ortamında sağlayın; aşağıdaki değerleri kendi izole ortamınızla doldurun:

```bash
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=3306 MYSQL_USER=avatar
export MYSQL_DATABASE=avatar_ml_demo_test
# MYSQL_PASSWORD ve AVATAR_API_KEY güvenli process ortamından verilmelidir.
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini check
# Varsayılan: repo/ml/models. Başka kurulum için mutlak yol:
export AVATAR_ML_MODEL_DIR="$PWD/ml/models"
PYTHONPATH=backend backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8009
```

Başka terminalde **aynı MYSQL_*/API anahtarı ortamı** ile:

```bash
AVATAR_API_BASE_URL=http://127.0.0.1:8009 backend/.venv/bin/python -m ml.scripts.demo_api
```

Bu komut yalnız loopback API ve adı `_test` ile biten DB ortamını kabul eder; API'nin de aynı process ortamıyla başlatılmasından operatör sorumludur. Ürün/alış/iki taslak oluşturur; **tahmini önce** kaydeder, sonra gerçek üretim/kesim motoruyla kapatır ve GET karşılaştırmalarını `ml/reports/demo.json` içine yazar. Sabit UUID/gövde ile tekrarlandığında aynı kayıt döner; çakışan veri otomatik sıfırlanmaz. 450 EUR ön teklif/profil varsayımı ve bütün işletme kayıtları demo verisidir. Model eğitimi/yeniden eğitimi API'de yapılmaz.

## Container kullanımı

Mevcut Docker Compose ve backend Dockerfile yalnız `backend/` context'ini taşır; kardeş `ml/` otomatik olarak image'a girmez. Ortak Compose dosyası bu görevde değiştirilmedi. Backend container'ına incelenmiş model dizinini **read-only bind mount** ile `/models` olarak bağlayıp `AVATAR_ML_MODEL_DIR=/models` verin; örneğin mevcut image için `--mount type=bind,src="$PWD/ml/models",dst=/models,readonly`. Aynı MySQL/API-key environment'ı gerekir. Mount yoksa tahmin endpoint'leri doğru biçimde 503 MODEL_UNAVAILABLE verir; health diğer model yollarından bağımsızdır. Bu görevde tam Docker Compose/image stack'i çalıştırılmadı; doğrulanan yol gerçek MySQL container + host FastAPI'dir.

## API sözleşmesi

Bütün yollar mevcut `X-API-Key` doğrulamasındadır. POST'larda ayrıca UUID `Idempotency-Key` zorunludur. Para ve miktarlar **JSON string**, biçim 6 ondalık; EUR ve kg/paket dışında birim kabul edilmez. Başarı 201; aynı kapsam/anahtar/gövde aynı 201 cevabı, farklı gövde 409 döndürür. Gerçekleşme okumak için GET çağrılır; POST replay cevabı zamanla değişmez.

### POST /v1/predictions/production

```json
{
  "operation_id": "<başlamamış external_production UUID; isteğe bağlı>",
  "output_product_id": "<paket ürün UUID; işlem bağlıysa zorunlu>",
  "meat_type": "beef",
  "meat_kg": "100",
  "spice_kg": "2",
  "casing_kg": "5",
  "meat_cost_eur": "970",
  "spice_cost_eur": "48",
  "casing_cost_eur": "58",
  "planned_producer_profile": "producer_a",
  "package_weight_kg": "1",
  "estimated_service_eur": "450",
  "quantity_unit": "package",
  "material_unit": "kg",
  "currency": "EUR"
}
```

Örnekteki `<...>` UUID yer tutucularını gerçek API kimlikleriyle değiştirin; ilişkisiz deneme için `operation_id`/`output_product_id` alanlarını tamamen çıkarabilirsiniz. Gövdeye `actual_*`, 85, 18,16, fiili fire veya kapanış toplamı eklenemez. Üretici profilleri **sentetik arketip**; gerçek şirket geçmişiyle eğitilmiş değildir. Üretici UUID'si bağlı operasyondan bağlama kopyalanır. Hammadde kg ve maliyetler açık plan varsayımıdır; bu sürüm bir üretim planı/lot rezervasyonu yapmaz, verilen planı kendiliğinden fiili lot tüketimi olarak kabul etmez.

Yanıt: id/kind/operation_id, predicted_at (UTC), kullanılan özellikler/bağlam, `predicted_finished_quantity`, `predicted_yield_ratio`, `predicted_ekp_eur_per_unit`, `predicted_total_cost_eur`, iki haneli `predicted_ekp_display`, para/birim, model/özellik/veri sürümü, veri hash'i, SYNTHETIC etiketi ve sınırlamalar. Gerçek JSON örneği [demo raporunda](reports/demo.json).

### POST /v1/predictions/cutting

```json
{
  "operation_id": "<başlamamış cutting UUID; isteğe bağlı>",
  "recipe_version_id": "<gerçek RecipeVersion UUID>",
  "species": "Kuzu",
  "input_weight_kg": "25",
  "unit": "kg",
  "part_products": {
    "leg": "<but Product UUID>",
    "shoulder": "<omuz Product UUID>",
    "back": "<sırt Product UUID>",
    "rib": "<kaburga Product UUID>",
    "mince": "<kıyma Product UUID>"
  }
}
```

Ürünler beş farklı kg mamul ve seçili reçetenin tam üyeleri olmalıdır. Caller'ın slot eşlemesi açık kaydedilir; anlamsal eşleme işletme konfigürasyonudur. Species Kuzu, reçete available=true ve varsa işlem reçete UUID'si eşleşmelidir. UUID, code, sürüm, ürün adları ve eşleme snapshot'tır. Öğrenilmemiş başka tür/yan ürün/reçete biçimleri reddedilir.

Yanıt her parça için `predicted_{leg|shoulder|back|rib|mince}_kg`, toplam, fark, verim, birim, metadata, uyarı ve snapshot bilgilerini içerir. Toplam yayımlanmış parçalardan Decimal ile türetilir; fark otomatik fire kaydı değildir.

### GET /v1/predictions/models

İki modelin metadata, eğitim/test metrikleri, desteklenen özellik kategorileri/sınırları ve sınırlamaları. DB yazmaz; eğitim yapmaz. Her worker, ilk başarılı yüklemede boyutu sınırlı JSON + SHA-256 çiftini doğrular ve cache'ler. Eksik/geçersiz model 503; sahte fallback yoktur. İncelenmiş yeni artifact aynı yere konduğunda worker yeniden başlatılmalıdır. SHA-256 bütünlük kontrolüdür, yayıncı imzası değildir; dağıtım dizini güvenilir operatöre aittir. Model katsayıları/şema/sonlu sayılar doğrulanır, pickle/joblib çalıştırılmaz.

### GET /v1/predictions/{id}

Orijinal tahmini yükler, **mevcut modeli çağırmaz**. Bağlı işlem kapandıysa kesin OperationInput/Output/Lot/Product FK ve Decimal maliyet alanlarından gerçekleşmeyi hesaplar. Tahmin yeniden eğitilmiş sürümle değiştirilmez.

```json
{
  "comparison": {
    "predicted_finished_quantity": {
      "predicted": "86.368585",
      "actual": "85.000000",
      "absolute_deviation": "1.368585",
      "percentage_deviation": "1.610100"
    }
  }
}
```

Mutlak sapma `abs(tahmin−gerçek)`; yüzde `mutlak_sapma / abs(gerçek) ×100`. Gerçek sıfırsa yüzde null. Gerçek yoksa gerçek/mutlak/yüzde null ve `actual_unavailable_reason` doludur. Farklar mümkün olan tam Decimal gerçekleşmeden hesaplanır; son gösterim 6 haneye yuvarlanır. İlişkisiz tahmin ileride otomatik bir operasyona bağlanmaz. Böyle bir karşılaştırma isteniyorsa bilinen taslak UUID'si tahmin anında verilmelidir.

Üretimde tüm gerçek çıktılar seçilmiş tek paket ürünü ve gerçek girdiler kg olmalıdır; başka mamul içeren kapanışta uydurma karşılaştırma yerine null/gerekçe döner. Kesimde beş parçadan farklı gerçek ürün varsa karşılaştırma null'dır. Fiilî tüketim plan miktarından farklı olabilir; gerçek verim fiilî giriş kütlesine dayanır.

## Kayıt ve transaction stratejisi

Alembic `dc9109a1f001` yalnız `prediction_records` tablosunu ekler: UUID, created_at, tür, nullable gerçek Operation FK, model sürümü, özellik şeması, özellik JSON, bağlam JSON, sonuç JSON. Mevcut idempotency kaydıyla tek transaction'da yazılır. Uygulamada update/delete yolu yoktur. Mevcut stok/lot/maliyet/recall tabloları tahmin tarafından yazılmaz; yalnız okunur. Downgrade tahmin audit tablosunu siler, ledger'ı değiştirmez; gerçek veri için yedek/operasyon kararı olmadan downgrade yapılmamalıdır.

Bağlı operasyon `FOR UPDATE` ile kilitlenir. Türü/status=draft kontrol edilir; sevk/işleme stok hareketi varsa yeni tahmin reddedilir. Böylece kapanıştan sonra geleceğe dönük tahminmiş gibi kayıt yapılamaz. Aynı anahtarlı eski başarılı istek model kaldırılmış veya işlem kapanmış olsa bile orijinal cevabı replay eder. Farklı anahtarlı yeni tahmin 409 FORECAST_TOO_LATE olur. Kesin stok/recall lock protokolü değiştirilmedi.

Ek hata kodları: 422 PREDICTION_OUT_OF_DOMAIN / PREDICTION_RECIPE_MISMATCH / PREDICTION_PRODUCT_MISMATCH, 404 NOT_FOUND, 503 MODEL_UNAVAILABLE; Pydantic biçim/birim/NaN/ek alan hataları standart 422, yanlış key 401. SQL hataları mevcut güvenli 503 sözleşmesindedir.

## Testler ve ortam ayrımı

```bash
backend/.venv/bin/python -m pytest ml/tests -q
# YIKICI testler: yalnız ayrı avatar_ml_core_test ve avatar_migration_test şemaları.
# Uygulama kullanıcısına yalnız bu izole şemalarda migration yetkisi verin.
export MYSQL_DATABASE=avatar_ml_core_test
AVATAR_MYSQL_TEST=1 AVATAR_CORE_MYSQL_TEST=1 backend/.venv/bin/python -m pytest tests ml/tests -q
```

Mevcut guard `_test` son ekini zorunlu kılar. `avatar_migration_test` migration roundtrip'lerinde temizlenir. Demo `avatar_ml_demo_test` ile bunlardan ayrıldı. Gerçek MySQL 8.0.46 kullanıldı; kilit/transaction kanıtı SQLite ile değiştirilmedi.

[Başlangıç](reports/baseline-tests.txt): 131 geçti. [Son paket](reports/full-tests.txt): 181 geçti (162 backend, 19 model); 0 fail/skip. 31 yeni backend testinin bir sıfır-yüzde dalı kontrollü `actual_values` stub'ı ile yardımcı aritmetiği doğrular; diğer senaryolarda gerçek işlem kapanışları/DB kullanılır. TestClient istekleri süreç içidir; ayrıca gerçek TCP HTTP demo iki kez çalıştırıldı ve DB'de 2 tahmin/2 işlem kaldı. [Gerçek DB kanıtı](reports/live-database.json).

Yeni testler: seed/etiket, ayrık tarih/ID, train-only scaler, baseline, miktar/EKP/parça sonuçları, negatif/NaN/sonsuz/taşan toplam koruması, metadata/checksum, güvenli 503, Pydantic/auth, transaction rollback, eşzamanlı idempotency, tarihsel sürümün **gerçek yeniden eğitim sonrası** korunması, ilk sevkten sonra tahmin reddi, bağlı gerçek sapma, lot/ledger/recall değişmezliği ve migration korunumu. Birleşik kodda frontend/Android testleri tekrar koşulmadı; dosyaları değiştirilmedi.

React/Android tahmin ekranı bu görevde geliştirilmedi; API kabulü UI kabulü değildir. Ortak checklist devri [README](README.md) tablosundadır.

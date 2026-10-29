# AI v2 — API, model dağıtımı ve kayıt güvenliği

## Yerel çalışma

[README](README.md) bağımlılıklarını kurun. Mevcut proje README'sindeki MySQL/Compose kurulumunu kullanın; testleri yalnız ayrı `_test` şemasında çalıştırın. Parola/API anahtarı güvenli process ortamından veya Git dışındaki özel env dosyasından gelir.

```bash
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini check
PYTHONPATH=backend backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Host'ta varsayılan model dizini repo `ml/models`; başka kurulumda `AVATAR_ML_MODEL_DIR` mutlak yolunu verin. Frontend'i aynı izole backend'e bağlayan sunucu `AVATAR_API_PROXY_TARGET=http://127.0.0.1:8000` ve sunucu tarafı API anahtarıyla başlatılır. `/yapay-zeka` formu anahtarı tarayıcıya taşımaz.

## Model metadata ve yeni aralıklar

`GET /v1/predictions/models`, mevcut `X-API-Key` ile iki modelin sürüm/tarih/veri hash'i/SYNTHETIC etiketi/metriklerini; `feature_schema`, `input_constraints` ve `example_inputs` değerlerini verir. Sayısal örnekler gerçek gerçekleşme veya ürün UUID'si içermez. Web sınırları aktif modelden alır; başarısız metadata yüklemesinde sahte form/model fallback'i yoktur.

| Alan | V2 desteklenen aralık |
| --- | --- |
| Et | 5–300 kg |
| Baharat | 0,05–12 kg **ve** etin %1–4’ü |
| Kılıf | 0,1–24 kg **ve** etin %2–8’i |
| Et / baharat / kılıf plan maliyeti | 0–6000 / 0–480 / 0–720 EUR |
| Paket ağırlığı | 0,25–2 kg/paket |
| Hizmet ön teklifi | 0–2400 EUR |
| Kuzu kesim girdisi | 5–80 kg |

Birimler/categorical değerler mevcut API ile aynı: beef/lamb, producer_a/b/c, EUR/package/kg ve Kuzu/five_parts_v1. Profiller gerçek firma geçmişi değildir. Dış dikdörtgendeki bütün uç kombinasyonların eğitimde ölçüldüğü iddia edilmez.

## Komutlar

Bütün POST'larda UUID `Idempotency-Key` gerekir; para/miktar JSON **string** olmalıdır. `actual_*`, fiili EKP veya kapanış toplamı girdi olamaz. Başarı 201; aynı key/body ilk cevabı döndürür, farklı gövde 409. Belirsiz sonuçta key/body aynen korunur.

25 kg üretim için `POST /v1/predictions/production`:

```json
{
  "meat_type": "beef", "meat_kg": "25", "spice_kg": "0.5", "casing_kg": "1.25",
  "meat_cost_eur": "242.50", "spice_cost_eur": "12.00", "casing_cost_eur": "14.50",
  "planned_producer_profile": "producer_a", "package_weight_kg": "1", "estimated_service_eur": "112.50"
}
```

Üretimde `operation_id` isteğe bağlıdır; varsa `output_product_id` zorunlu ve DB'deki paket ağırlığı girdiye eşit olmalıdır. Draft olması tek başına yeterli değildir: hammadde sevki başlamışsa 409 FORECAST_TOO_LATE döner. Bu kural kaldırılmadı. İlişkisiz tahmin için ürün/operasyon gerekmiyor; sonradan otomatik eşleme yapılmıyor.

`POST /v1/predictions/cutting`: mevcut `recipe_version_id`, beş farklı gerçek ürün UUID'sini içeren `part_products` (leg/shoulder/back/rib/mince), species=Kuzu, input_weight_kg ondalık metni ve isteğe bağlı `operation_id`. Reçete kullanılabilir Kuzu/beş kg mamul olmalı; bağlı kesimin reçetesi eşleşmelidir. Ürün adından otomatik anatomik eşleme uydurulmaz. Geçersiz reçete 422 PREDICTION_RECIPE_MISMATCH.

## Alan bazlı hata ve güvenli çıkarım

Statik Pydantic şeması transport tipini, pozitif miktar/sonlu ondalık ve birimleri kontrol eder. Aktif modelin aralık/oran denetimi **idempotency replay'den sonra**, komut transaction'ında yapılır. Böylece yeni modelin aralığı eski başarılı komutun tekrarını engellemez.

```json
{
  "error": {
    "code": "PREDICTION_OUT_OF_DOMAIN",
    "message": "Planlanan et: 5–300 kg sentetik model aralığında sonlu bir değer girin.",
    "details": { "fields": [{ "field": "meat_kg", "minimum": 5, "maximum": 300, "unit": "kg", "message": "Alan açıklaması" }] }
  }
}
```

HTTP 422; frontend bu alanları ilgili form hatasına bağlar. Miktar oranı hatasında seçili et miktarına göre gerçek min/max döner. Negatif/sıfır miktar, NaN/Infinity ve yanlış transport tipi Pydantic 422'sidir. Eksik, bozuk checksum/şema veya fiziksel olarak geçersiz v2 model çıktısı 503 MODEL_UNAVAILABLE döner; sessiz kırpma/fallback yoktur.

## Eski kayıt, kesin gerçekleşme ve bütünlük

`GET /v1/predictions/{id}` saklı sonucu/sürümü/tarihi döndürür; mevcut modeli çağırmaz. İlişkili operasyon kesin kapanmışsa gerçek FK ve Decimal alanlarından gerçekleşme/sapma hesaplar. Gerçek yoksa null/gerekçe, gerçek sıfırsa yüzde null. Kaydedilmiş tahmin yeni modelle değiştirilmez. V1 JSON çiftleri ve sabit testleri [arşivde](evaluation/v1/) korunur.

Tahmin ve idempotency dışında DB yazılmaz. Mevcut stock/cost/sales/recall kuralları modelden bağımsızdır. Yeni migration/tablo yoktur; mevcut migration head korunur. Canlı kabulde dolu stok/maliyet/satış/recall fixture'ları bulunan 28 kesin tablonun hash'i üç web senaryosu ve Docker tahminleri boyunca aynı kaldı. [Kabul raporu](../docs/AI_MODEL_V2_ACCEPTANCE.md).

## Docker ve geri dönüş

Backend Dockerfile'ın context'i **repo köküdür**, iki güncel `ml/models/*.json/*.sha256` çifti imaja kopyalanır. Eski “backend-only context/mount gerekli” Görev 09 açıklaması güncel değildir. Compose `AVATAR_ML_MODEL_DIR=/app/ml/models` ayarlar. Tek başına imaj çalıştırırken de bu yolu environment'tan verin.

```bash
docker build -f backend/Dockerfile -t avatar-api:ai-v2 .
# MySQL/API anahtarı özel runtime env üzerinden sağlanmalı;
# mevcut Docker Compose kurulumuyla bu imaj yeniden build edilebilir.
```

JSON + SHA256 çiftini birlikte incelenmiş artefakt olarak dağıtın; API worker'ını yeniden başlatın. SHA256 bütünlük denetimidir, yayıncı imzası değildir. Pickle/joblib veya API içinde eğitim yoktur. V1'e dönüş için arşivdeki iki çift ayrı güvenilir dizine kopyalanıp `AVATAR_ML_MODEL_DIR` bu dizine verilerek worker yeniden başlatılır; kaynak dosyaları silmek veya kayıtlı tahminleri değiştirmek gerekmez. Eski sabit benchmark'taki gerileme nedeniyle v2 genel gerçek doğruluk terfisi sayılmaz.

## Testler

```bash
backend/.venv/bin/python -m pytest ml/tests -q
# MYSQL_DATABASE yalnız ayrı *_test şeması; aşağıdaki testler bu şemayı temizler.
AVATAR_CORE_MYSQL_TEST=1 backend/.venv/bin/python -m pytest \
  tests/test_predictions_mysql.py tests/test_prediction_v2_mysql.py -q
cd frontend
npm test
npm run build
npx playwright test tests/browser/ai-model-v2.spec.ts
```

Gerçek Chromium için yerel API/Vite ve `AVATAR_E2E_DATABASE=..._test`, server-side `AVATAR_API_KEY`, gerekirse `AVATAR_E2E_API_URL` gerekir. Testler kendi izole fixture'ını oluşturabilir; kabulde ayrıca önceden hazırlanan kurgusal seed kullanılarak iş tablolarının değişmezliği ayrı ölçüldü. Gerçek işletme DB'sinde çalıştırmayın. Tam sonuçlar kabul raporundadır; eski `ml/reports/*` dosyaları v1 tarihsel kanıtıdır.

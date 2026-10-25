# Zorunlu ML — üretim ve kuzu parçalama

İki Ridge regresyonu gerçekten eğitildi, kronolojik ayrı testte değerlendirildi ve mevcut FastAPI/MySQL uygulamasından çağrıldı. **Verinin tamamı SYNTHETIC**; gerçek işletme başarımı henüz ölçülmedi. Bu katman yalnız karar desteğidir.

Görev 09 başlangıcı `4951281` (main, PR #1–#12 normal merge geçmişte mevcut). GitHub REST/GraphQL durum sorguları 403 verdi; Git geçmişi doğrudan incelendi. `AGENTS.md`, üç sayfalık PDF, varsayımlar, checklist, backend/kesim sözleşmeleri okundu. Bu görevin sahipliği `ml/`, `backend/`, `tests/`; Android, React ve ortak checklist değiştirilmedi.

## Kurulum ve tekrar üretme

Depo kökünde Python **3.12**:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt -r ml/requirements.txt
backend/.venv/bin/python -m ml.training.train
backend/.venv/bin/python -m ml.scripts.predict_examples
backend/.venv/bin/python -m pytest ml/tests -q
```

`train`, seed **202609** ile CSV/manifest dosyalarını tekrar üretir; train/validation/test=**360/120/120**, her model için **600**, toplam **1.200** sentetik kayıt. İstenirse `--data`, `--models`, `--evaluation` ile ayrı çıktı dizinleri ve tam artifact byte tekrar üretimi için `--trained-at` sabit UTC zaman damgası verilir. Mevcut modele yazma offline bir dağıtım adımıdır; çalışan API'nin modelini değiştirmek için incelenmiş artifact çiftlerini atomik yerleştirin ve API sürecini yeniden başlatın. API hiçbir istekte eğitim yapmaz.

Yalnız eğitim pandas/NumPy/scikit-learn gerektirir. API çıkarımı standart Python ile JSON katsayılarını kullanır; sklearn veya pickle/joblib yüklemez. İki model toplam yaklaşık **10 KB** JSON'dur. Büyük/özel veri `ml/private/` veya ignored `ml/artifacts/` altında tutulmalıdır; gerçek veriyi bu sentetik havuza eklemek v1 kapsamında değildir.

## Veri ve yöntem

Depoda tarihsel ölçüm veri seti yoktur: tek PDF örneği ile kurgusal demo/test kayıtları istatistiksel geçmiş kabul edilmedi. Dış bir işletme veritabanı erişilmedi/örneklenmedi. [Üretici](data/generate.py), [manifest ve SHA-256](data/manifest.json), [üretim CSV](data/production.csv), [kesim CSV](data/cutting.csv) kaynak ve üretim yöntemini açıklar. Tarihler dahi sentetiktir; kronolojik ayrım gerçek mevsimsellik kanıtı değildir. PDF'nin 85 paket/18,16 EUR ve kurgusal 6/4/4/5/3 kg kesim örneği eğitim satırı olarak kullanılmadı.

Her satır bağımsız bir kurgusal işlem grubudur; aynı işlem train/test'e bölünmez. Özellikler allowlist ile seçilir, `actual_*` hedefleri girdi olamaz. DictVectorizer ve StandardScaler yalnız ilk 360 satıra fit edilir. Ridge alpha=0.1/1/10 seçimi sonraki 120 validation satırında yapılır; son 120 test satırı seçimde kullanılmaz. Validation sonrasında yeniden fit yapılmaz. Referans yöntem training'deki ortalama verim/hizmet sapması veya parça oranıdır. Test metrikleri üretimde kullanılan fiziksel kısıtlamadan sonra hesaplanır; JSON çıkarımının sklearn çıktısıyla eşitliği eğitimde test edilir.

A: işlem öncesi kg, bilinen alış maliyetleri, sentetik üretici profili, et türü, paket ağırlığı ve ön tekliften **üretim verimi ve hizmet bedeli çarpanı** öğrenilir. Beklenen paket sayısı öğrenilmiş verimden; EKP ise bilinen malzeme + tahmini hizmet toplamının tahmini paket sayısına bölümünden gelir. Muhasebeleşmiş toplam/çıktı/firenin girdiye sızması yoktur.

B: Kuzu, giriş kg ve beş parçalı reçete şekliyle **beş parça oranı** öğrenilir. Tür/şekil bu veri setinde sabittir; diğer türler/reçete şekilleri için başarı iddiası yoktur. Gerçek `recipe_version_id` ve parça ürün UUID eşlemesi API'de doğrulanıp kayda alınır; sürümün kendisine eğitimde ölçülmemiş etki atfedilmez. Sonuçlar negatif olmayan ve toplamı giriş kg'yi aşmayan alana projekte edilir. Açıklanması beklenen fark matematiksel kalandır; otomatik fire sınıfı değildir.

## Kullanım ve kanıt

- [Üretim model kartı](MODEL_CARD_PRODUCTION.md)
- [Parçalama model kartı](MODEL_CARD_CUTTING.md)
- [Ayrı test metrikleri ve zayıf sonuçlar](EVALUATION_REPORT.md)
- [FastAPI, kayıt/sapma, Docker mount ve gerçek demo](INTEGRATION.md)
- [Makine okunur metrikler](evaluation/metrics.json), [gerçek HTTP demo sonuçları](reports/demo.json)
- [Test çıktısı](reports/full-tests.txt), [doğrulama özeti](reports/validation.json)

API: `POST /v1/predictions/production`, `POST /v1/predictions/cutting`, `GET /v1/predictions/models`, `GET /v1/predictions/{id}`. Mevcut X-API-Key ve UUID Idempotency-Key sözleşmeleri korunur. İlk üç POST/GET akışı gerçek HTTP ile denendi. Backend migration head: `dc9109a1f001`; yeni tek tablo `prediction_records`. Ledger, lot ve recall algoritmaları değiştirilmedi.

**Sonuç:** başlangıçtaki 131 test geçti; ek 31 backend/MySQL testi ve 19 model testiyle **181 geçti, 0 başarısız, 0 atlanan**. Gerçek HTTP demo ayrı `avatar_ml_demo_test`, yıkıcı testler `avatar_ml_core_test`/`avatar_migration_test` kullandı. Test verileri işletme verilerinden ayrıdır. Üretim UI entegrasyonu, gerçek veriyle eğitim ve kalibre belirsizlik aralıkları henüz yoktur.

## Entegrasyon sorumlusuna checklist devri

| Görev | Bu branch'teki gerçek kapsam | Önerilen durum |
| --- | --- | --- |
| ML-01 | A eğitimi, tahmin, API ve 85 paket gerçekleşmeyle sapma kanıtı | Tamamlandı — sentetik prototip |
| ML-02 | B eğitimi, fiziksel sınırlar, reçete UUID eşlemesi ve gerçekleşmeyle sapma | Tamamlandı — Kuzu/beş parça sentetik prototipi |
| ML-03 | SYNTHETIC veri/seed/hash/manifest; gerçek geçmiş 0 | Tamamlandı — gerçek veri edinimi ayrıca gerekli |
| ML-04 | Baseline, kronolojik ayrı test, hedef başına MAE/RMSE ve sürüm | Tamamlandı — sentetik değerlendirme |
| ML-05 | Değişmez kayıt, gerçek/sapma API'si tamam; React karşılaştırma ekranı geliştirilmedi | Devam ediyor |
| ML-06 | Operasyonel kayıt ayrımı, recall engeli, eski model sürümü ve 131 regresyon testi | Tamamlandı — test edilen prototip kapsamı |

Ortak `docs/PROJECT_CHECKLIST.md` değiştirilmedi. Bu durumlar main birleşimi veya tüm yarışma tesliminin tamamlandığı anlamına gelmez.

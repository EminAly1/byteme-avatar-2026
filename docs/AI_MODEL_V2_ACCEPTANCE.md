# Görev 22 — AI model v2 ve tahmin ekranı kabulü

29 Ekim 2026, Europe/Istanbul. Başlangıç main `d4206d1ba52c6d92c55294000ff74883222b4d75`; PR #37 normal merge geçmişinde doğrulandı. Branch: `feature/ai-model-v2-prediction-ux`. Bu kabul yerel sentetik prototip kapsamındadır; main merge veya gerçek işletme performansı kabulü değildir.

## Veri, eğitim ve sürüm

| Alan | V1 | V2 |
| --- | --- | --- |
| Kayıt/model | 600 | **3.000** |
| İki model toplamı | 1.200 | **6.000** |
| Train / validation / test | 360 / 120 / 120 | **1.800 / 600 / 600** |
| Veri sürümü / seed | synthetic-v1 / 202609 | **synthetic-v2 / 20261029** |
| Gerçek tarihsel satır | 0 | **0** |
| Üretim et girdisi | 60–160 kg | **5–300 kg** |
| Kuzu kesim girdisi | 18–40 kg | **5–80 kg** |
| Paket ağırlığı | 0,5–1,5 kg | **0,25–2 kg** |

V2 küçük/orta/büyük partiler, farklı fiyat/teklif/paket boyları, iki et türü, üç kurgusal üretici profili ve bağımsız süreç gürültüsü içerir. Beş kesim parçası pozitiftir; giriş = parça toplamı + açıklanması gereken fark. Baharat etin %1–4’ü, kılıf %2–8’i; diğer dış aralıklar [API belgesinde](../ml/INTEGRATION.md). 25 kg örneği 0,5 kg baharat, 1,25 kg kılıf ve 112,50 EUR bağımsız hizmet ön teklifiyle desteklenir. 25 kg et + 2 kg baharat/5 kg kılıf kombinasyonu yeni modelin belgelenmiş oranını aşar; gereksiz hata gibi gizlenmez, ilgili alanın doğru aralığı gösterilir.

DictVectorizer ve StandardScaler yalnız train üzerinde fit edilir. Ridge alpha=0,1/1/10 yalnız validation'da seçildi; test seçime/fit'e katılmadı. Seçim hedefleri train standart sapmasıyla normalize edilir. Validation'da train-mean baseline'dan iyi olma kapısı iki modelde geçti. Son test hedeflerini değiştirmek scaler/katsayı/alpha'yı değiştirmedi. Sabit timestamp ile tekrar eğitim byte düzeyinde aynı artefaktı üretir. Parti sınırlarının açıklayıcı segment etiketi gerçek miktara göre düzeltildi; bu düzeltmenin katsayı/scaler/alpha'yı değiştirmediği ayrıca kontrol edildi.

- Üretim: **`production-ridge-v2-a21520e1f03f`**, alpha **1**.
- Kesim: **`cutting-ridge-v2-d4f63323f8a6`**, alpha **0,1**.
- JSON formatı `avatar-linear-json-v1`, mevcut feature allowlist/vectorization ve `preprocess-v1` korunur. Veri/model sürümü ve checksum değişir; pickle/joblib yoktur.
- V1 JSON+sha256, eski manifest/metrikler ve 120+120 sabit test satırı [arşivde](../ml/evaluation/v1/) korundu. Ayrık ID'ler ve bütün aday metrikleri [metrics.json](../ml/evaluation/metrics.json) içinde.

## Karşılaştırma ve gerileme

Aşağıdaki satırlarda **aynı v2 ortak test örnekleri** kullanılır. Üretim n=66, kesim n=199. Hücreler **MAE / RMSE**'dir.

| Hedef | Birim | Baseline | V1 | V2 |
| --- | --- | --- | --- | --- |
| Mamul miktarı | paket | 2.569888 / 3.484266 | 1.288153 / 1.894631 | 1.180829 / 1.616089 |
| Birim EKP | EUR/paket | 0.961562 / 1.181889 | 0.386846 / 0.556740 | 0.390752 / 0.528683 |
| Parça toplamı | kg | 0.267374 / 0.343107 | 0.283204 / 0.365322 | 0.251176 / 0.325603 |

**V2 her hedefte iyileşme değildir.** Ortak üretim EKP MAE **0,386846 → 0,390752 EUR/paket**, toplam maliyet MAE **11,350841 → 11,613796 EUR** ve toplam maliyet RMSE **15,223476 → 15,576864 EUR** ile geriledi. EKP RMSE düşerken MAE yükseldi; tek metriğe bakılarak genel iyileşme çıkarılmadı. Değişmeyen eski 120 satırlık testte de v2 hataları arttı: örneğin üretim EKP RMSE **0,244472 → 0,348483 EUR/paket**, kesim toplam RMSE **0,265058 → 0,318115 kg**. Eski n=120 ile geniş v2 n=600 sonuçlarını doğrudan kıyaslayıp iyileşme ilan edilmedi.

V2 genişletilmiş SYNTHETIC v2 süreci için prototipte etkin; **genel gerçek doğruluk terfisi onaylanmadı**. Simülatör varsayımları değiştiğinden gerçek başarım çıkarılamaz. Test sonucuna göre simülatör/hedef/alpha ayarı yapılmadı. V1 dosyaları geri dönüş için korunur. [Bütün hedefler, baseline ve üç ayrı popülasyonun tam MAE/RMSE tabloları](../ml/EVALUATION_REPORT.md), [üretim kartı](../ml/MODEL_CARD_PRODUCTION.md), [kesim kartı](../ml/MODEL_CARD_CUTTING.md).

## API ve web sonuçları

Gerçek v1 HTTP API'sinde 25 kg ölçekli örnek **422** verdi; meat_kg, spice_kg, casing_kg, estimated_service_eur eski aralık dışındaydı. Aynı desteklenen örnek v2 API'de **201** verdi. Yeni Docker imajındaki 25 kg örnekleri:

| Sonuç | Değer |
| --- | --- |
| Üretim tahmini mamul | 21,192267 paket |
| Üretim tahmini toplam maliyet | 378,992297 EUR |
| Üretim tahmini EKP | 17,883519 EUR/paket |
| Üretim verimi | 0,792234 kg/kg |
| 25 kg kuzu tahmini parça toplamı | 21,797558 kg |
| Açıklanması gereken fark | 3,202442 kg |
| Kesim verimi | 0,871902 kg/kg |

Bunlar **tahmin**, gerçek işletme miktarı veya muhasebe toplamı değildir. Beklenen paket sayısı sürekli değerdir. Beş parça miktarı, toplam/fark, model sürümü, tarih, SYNTHETIC ve tahmin/gerçek/sapma ayrı gösterilir. Eski kayıt okunurken güncel model metrikleri eski kaydın performansı olarak sunulmaz.

Formlar aktif modelin `/predictions/models` metadata'sından min/max/oran/örnek alır. Placeholder gerçek sayısal örnektir; form başlangıçta boş kalır. Örnek doldurma ve eksik reçete/ürün için gerçek kurulum bağlantıları vardır. Kesimde gerçek reçete/beş ürün kullanıcı tarafından eşlenir; sahte UUID veya anlamsal eşleme eklenmedi. 390/768/1440 px ve mobil tek sütun kontrol edildi.

Backend alan bazında `PREDICTION_OUT_OF_DOMAIN` / 422 + field/minimum/maximum/unit/message döndürür; web ilgili alanı işaretler. Negatif/sıfır miktar, NaN/Infinity, anlamsız büyük değer ve desteklenmeyen oranlar reddedilir. V2 fiziksel olarak geçersiz ham model çıktısı sessizce kırpılmaz, 503 döner. Statik transport şeması idempotency replay'i yeni model sınırlarıyla bozmaz; model aralıkları komut service'inde replay'den sonra uygulanır.

## Gerçek testler ve bütünlük

| Kontrol | Sonuç |
| --- | --- |
| Gerçek MySQL hedefli backend | **143 geçti**, 0 başarısız/skip; 21 yeni v2 + mevcut 122 regresyon |
| ML | **44 geçti**, 0 başarısız/skip; 25 yeni + mevcut 19 |
| Son birleşik pytest koşusu | **187 geçti**, 1 mevcut Starlette/AnyIO deprecation uyarısı |
| React/Vitest | **102 geçti**, 0 başarısız/skip; 13 yeni + mevcut 89 |
| TypeScript / Vite build | **Geçti** |
| Gerçek Chromium | **6 farklı senaryo geçti**, 0 başarısız/skip; 3 yeni, 2 tahmin/gerçekleşme regresyonu, 1 gerçek eksik-model 503 |
| Erişilebilirlik / responsive | **7 otomatik WCAG A/AA taraması, 0 ihlal**; 390/768/1440 px, görseller ayrıca incelendi |
| Migration | Yeni tablo/migration yok; `alembic check` temiz |
| Yeni Docker imajı | Nonroot UID 1000; iki JSON+SHA yüklendi; health/ready 200, iki gerçek HTTP POST **201/201** |

Backend kapsamı: predictions 30, v2 21, alerts 28, core 20, cuttings 30, mevcut recall-review 14. Reçete/ürün uyuşmazlığı, geç tahmin reddi, eşzamanlı idempotency, eksik/bozuk model, eski tahminin yeni model veya model yokluğunda okunması ve başarısız işlem rollback'i dahildir. Geri çağırma motoru değiştirilmedi; ortak hata taşıyıcısına eklenen details alanı mevcut boş-details davranışını korur.

Testler yalnız **yeni** `avatar_task22_core_test` ve `avatar_task22_web_test` şemalarında çalıştı. Canlı web/Docker kabulü öncesinde kurgusal alış maliyeti, stok, satış ve recall kayıtları hazırlandı. Önce/sonra **28 kesin tablonun hash'i aynı** kaldı; yalnız `prediction_records`/`idempotency_requests` değişti. Sonraki gerçekleşme regresyonlarının fixture/kapanışları bu izolasyon ölçümünden ayrı fazdır. TestClient süreç içi testlerinden ayrıca gerçek TCP HTTP, Node proxy, Chromium ve container API testleri yapıldı.

Gerçek v1 tahmini eski artefaktla HTTP üzerinden kaydedildi; v2 API'den sürüm/zaman/sonuç değişmeden okundu. Kaybolan gerçek commit yanıtı reload sonrası aynı key/body ile tek tahmin cevabına döndü. Bağlı operasyon başlamadan tahmin kuralı, kesin Decimal maliyet motoru ve stok/lot/recall otoritesi korundu.

## Docker, kanıt ve kapsam sınırları

Normal Docker build bu ortamın paket DNS çözümlemesinde başarısız oldu. Mevcut proxy/CA build yöntemiyle TLS doğrulaması korunarak temiz imaj üretildi; runtime host network'e açılmadı. Kabul konteyneri izole MySQL namespace'ini paylaştı, API yalnız container loopback'inde yayınlandı. Başlangıçta dış kabul betiğinin `/app` import yolu eksikti; harness düzeltildi, uygulama import mimarisi değiştirilmedi. Bir frontend testindeki desteklenmeyen Testing Library seçeneği typecheck'te düzeltildi; assert silinmedi. Bütün bu ilk çıktılar korundu.

[Makine okunur özet ve ham kanıt hash'leri](ai-model-v2/acceptance.json). Ham JUnit/log/PNG/HTTP raporları `/tmp/avatar-task22/`, indirilebilir iki görünüm `/workspace/shared/downloads/avatar-task22/` altındadır. Büyük ham çıktılar Git'e eklenmedi. Eğitim tekrar üretim komutları [ml/README](../ml/README.md), API/dağıtım/geri dönüş [ml/INTEGRATION](../ml/INTEGRATION.md) içindedir.

Sırlar/env dosyaları ve API anahtarları Git'e eklenmedi. Beş gerçek özel değer kaynak ve son frontend bundle'ında arandı; eşleşme yok. Gerçek runtime anahtarı ortamdayken build geçti. Gitleaks aday ve commit geçmişi taramaları temiz. Test servisleri kapatıldı, önceki Compose demo servisleri HTTP 200/200 ile doğrulanarak geri başlatıldı; yeni test şemaları ve kanıtlar korundu.

Gerçek işletme verisi, gerçek doğruluk, kalibre belirsizlik aralığı, dış doğrulama ve drift izlemesi yoktur. Küçük ortak test, sentetik profiller veya artan satır sayısı gerçek başarıyı kanıtlamaz. Tam ilgisiz backend paketi, Android, belge/PDF merkezi ve internet dağıtımı bu görevde yeniden test edilmedi. Android, belge merkezi, recall kodu, genel tema/logo ve ortak PROJECT_CHECKLIST değiştirilmedi. Backend/ML/web/ortak sözleşme yazarlığı tek entegrasyon ajanında yürütüldü.

Branch commit/push ve PR erişim sonucu son Türkçe raporda belirtilir. Main'e birleştirme yapılmaz.

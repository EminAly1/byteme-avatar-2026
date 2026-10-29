# Model kartı — Kuzu parçalama v2

**Sürüm:** `cutting-ridge-v2-d4f63323f8a6`. **SYNTHETIC**, gerçek tarihsel satır **0**. Her model 3.000 işlem; 1.800/600/600 ayrım. Tekrar üretim için sabit eğitim zaman damgası: 2026-10-29T00:00:00+00:00; sabit seed 20261029.

[JSON](models/cutting.json), [checksum](models/cutting.sha256), [manifest](data/manifest.json), [eski artefakt](evaluation/v1/cutting.json).

## Desteklenen işlem öncesi girdiler

| Alan | Sınır / kategori |
| --- | --- |
| input_weight_kg | 5–80 kg |
| recipe_shape | five_parts_v1 |
| species | Kuzu |

Kuzu ve five_parts_v1 dışında eğitim yoktur. Giriş ağırlığı küçük/orta/büyük segmentlerde 5–80 kg; beş pozitif oran ve bağımsız parça gürültüsü vardır. Giriş = parça toplamı + pozitif açıklanması gereken fark. Reçete UUID’si ve parça ürünleri gerçek DB kaydıyla doğrulanır; model adlardan otomatik ürün/lot ilişkisi uydurmaz.

Beş farklı kg mamulün tamamı seçili kullanılabilir Kuzu reçetesinin üyeleri olmalıdır. Anlamsal slot eşlemesini kullanıcı seçer; reçete sürümüne gözlenmemiş bir fiziksel etki atfedilmez. Fark fire/yan ürün/ölçüm sınıfı değildir. Kesin kapanış mevcut tartım ve açıklama kurallarını kullanır.

## Yöntem, sonuçlar ve terfi sınırı

Train-only DictVectorizer + StandardScaler + Ridge, alpha **0.1**. Alpha yalnız validation'da seçildi; test model seçimi veya fit için kullanılmadı. Baseline train ortalama oranıdır. JSON formatı avatar-linear-json-v1, özellik şeması preprocess-v1 korunur; yeni veri/model sürümü v2’dir.

V2 geniş sentetik validation kapısı geçti. Ancak eski sabit v1 testinde gerileme vardır; v2’nin her hedefte genel iyileşme olduğu iddia edilmez. [Değerlendirme raporu](EVALUATION_REPORT.md) aynı satırlarda v1/baseline/v2 karşılaştırmasını, eski testteki gerilemeyi ve hedef/birim bazında MAE/RMSE’yi verir. Gerçek işletme başarımı veya istatistiksel anlamlılık kanıtlanmadı.

| V2 test hedefi | Birim | n | Baseline MAE / RMSE | V2 MAE / RMSE |
| --- | --- | --- | --- | --- |
| But | kg | 600 | 0.270001 / 0.434086 | 0.129030 / 0.190670 |
| Omuz | kg | 600 | 0.149168 / 0.231549 | 0.130913 / 0.194764 |
| Sırt | kg | 600 | 0.197052 / 0.307690 | 0.128628 / 0.188049 |
| Kaburga | kg | 600 | 0.181591 / 0.279620 | 0.134647 / 0.200164 |
| Kıyma | kg | 600 | 0.167165 / 0.258174 | 0.137021 / 0.199011 |
| Parça toplamı | kg | 600 | 0.443031 / 0.692119 | 0.285940 / 0.434307 |
| Açıklanması gereken fark | kg | 600 | 0.443031 / 0.692119 | 0.285940 / 0.434307 |
| Verim | ratio | 600 | 0.011987 / 0.014820 | 0.008536 / 0.010819 |

## Güvenlik ve bilimsel sınırlamalar

Doğrulanmış JSON + SHA256 yüklenir; pickle/joblib çalıştırılmaz. SHA bütünlük kontrolüdür, yayıncı imzası değildir. V2’de giriş dışı alanlar açıklamalı 422, sonlu olmayan/fiziksel olarak geçersiz model çıktısı 503; sessiz girdi/çıktı kırpması yoktur. Eksik/bozuk modelde sahte fallback yoktur. Worker ilk başarılı yüklemeyi cache’ler; incelenmiş çift dağıtımından sonra yeniden başlatılmalıdır.

Gerçek veri, kalibre güven aralıkları, dış doğrulama, gerçek üretici geçmişi ve drift izlemesi yoktur. Kesin para/stok/recall motorları modelden bağımsızdır. Eski tahmin sonucu/sürümü DB snapshot’ında saklıdır; yeni model veya model dosyasının yokluğu geçmişi yeniden hesaplatmaz. [Entegrasyon ve geri dönüş](INTEGRATION.md).

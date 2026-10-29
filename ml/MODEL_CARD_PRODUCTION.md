# Model kartı — Üretim verimi ve EKP v2

**Sürüm:** `production-ridge-v2-a21520e1f03f`. **SYNTHETIC**, gerçek tarihsel satır **0**. Her model 3.000 işlem; 1.800/600/600 ayrım. Tekrar üretim için sabit eğitim zaman damgası: 2026-10-29T00:00:00+00:00; sabit seed 20261029.

[JSON](models/production.json), [checksum](models/production.sha256), [manifest](data/manifest.json), [eski artefakt](evaluation/v1/production.json).

## Desteklenen işlem öncesi girdiler

| Alan | Sınır / kategori |
| --- | --- |
| casing_cost_eur | 0–720 EUR |
| casing_kg | 0.1–24 kg |
| estimated_service_eur | 0–2400 EUR |
| meat_cost_eur | 0–6000 EUR |
| meat_kg | 5–300 kg |
| meat_type | beef / lamb |
| package_weight_kg | 0.25–2 kg/package |
| planned_producer_profile | producer_a / producer_b / producer_c |
| spice_cost_eur | 0–480 EUR |
| spice_kg | 0.05–12 kg |

Baharat et miktarının %1–4’ü, kılıf %2–8’i olmalıdır. Örneğin 25 kg et için 0,25–1 kg baharat ve 0,5–2 kg kılıf desteklenir. Diğer sayısal sınırlar tasarımın dış dikdörtgenidir; bütün uç kombinasyonların gözlendiği anlamına gelmez. Planlı maliyetlerin sıfır olabilmesi muhasebe doğruluğu veya ücretsiz işletme örneklerinin ölçüldüğü iddiası değildir.

Küçük/orta/büyük et partileri, iki et türü, üç kurgusal üretici profili, beş paket ağırlığı, farklı malzeme fiyatları/ön teklifler ve bağımsız gözlenmeyen gürültü kullanıldı. Model verim oranı ve hizmet çarpanı öğrenir; miktar bu verimden, yaklaşık toplam planlı malzeme + tahmini hizmetten, EKP tahmini toplam/miktardan gelir. Girdiler actual_* ve gerçekleşmiş EKP içermez. Paket miktarı sürekli beklenen değerdir; kesin üretim adedi değildir.

İşleme bağlı tahminde paket mamul ve paket ağırlığı DB kaydıyla eşleşmelidir. İşlem başlamış/sevk edilmiş/kapalıysa yeni tahmin reddedilir. Tahmin stok rezervasyonu yapmaz, gerçek tüketimi veya faturayı değiştirmez.

## Yöntem, sonuçlar ve terfi sınırı

Train-only DictVectorizer + StandardScaler + Ridge, alpha **1**. Alpha yalnız validation'da seçildi; test model seçimi veya fit için kullanılmadı. Baseline train ortalama oranıdır. JSON formatı avatar-linear-json-v1, özellik şeması preprocess-v1 korunur; yeni veri/model sürümü v2’dir.

V2 geniş sentetik validation kapısı geçti. Ancak eski sabit v1 testinde gerileme vardır; v2’nin her hedefte genel iyileşme olduğu iddia edilmez. [Değerlendirme raporu](EVALUATION_REPORT.md) aynı satırlarda v1/baseline/v2 karşılaştırmasını, eski testteki gerilemeyi ve hedef/birim bazında MAE/RMSE’yi verir. Gerçek işletme başarımı veya istatistiksel anlamlılık kanıtlanmadı.

| V2 test hedefi | Birim | n | Baseline MAE / RMSE | V2 MAE / RMSE |
| --- | --- | --- | --- | --- |
| Mamul miktarı | package | 600 | 4.356980 / 9.309748 | 1.899243 / 3.843486 |
| Verim | ratio | 600 | 0.023154 / 0.027879 | 0.010307 / 0.012904 |
| Birim EKP | EUR/package | 600 | 0.903017 / 1.240929 | 0.350307 / 0.505783 |
| Toplam maliyet | EUR | 600 | 22.183457 / 38.596749 | 12.450015 / 22.321937 |

## Güvenlik ve bilimsel sınırlamalar

Doğrulanmış JSON + SHA256 yüklenir; pickle/joblib çalıştırılmaz. SHA bütünlük kontrolüdür, yayıncı imzası değildir. V2’de giriş dışı alanlar açıklamalı 422, sonlu olmayan/fiziksel olarak geçersiz model çıktısı 503; sessiz girdi/çıktı kırpması yoktur. Eksik/bozuk modelde sahte fallback yoktur. Worker ilk başarılı yüklemeyi cache’ler; incelenmiş çift dağıtımından sonra yeniden başlatılmalıdır.

Gerçek veri, kalibre güven aralıkları, dış doğrulama, gerçek üretici geçmişi ve drift izlemesi yoktur. Kesin para/stok/recall motorları modelden bağımsızdır. Eski tahmin sonucu/sürümü DB snapshot’ında saklıdır; yeni model veya model dosyasının yokluğu geçmişi yeniden hesaplatmaz. [Entegrasyon ve geri dönüş](INTEGRATION.md).

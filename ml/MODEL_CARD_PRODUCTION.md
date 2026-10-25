# Model A — üretim verimi ve EKP

**Sürüm:** `production-ridge-v1-a27a209e395c`. **Kaynak:** yalnız SYNTHETIC, gerçek geçmiş sayısı 0. [JSON model](models/production.json), [CSV/manifest](data/manifest.json), [tam metrikler](evaluation/metrics.json).

## Kullanım amacı

Dış üretim başlamadan paket miktarı, kg/kg üretim verimi, EUR/paket EKP ve tahmini toplam bedel için karar desteği. Gerçek tüketim, hizmet faturası, stok, lot bağlantısı ve recall kararlarının yerini almaz. Tahmin edilen paket miktarı sürekli beklenen değerdir; otomatik sipariş/lot adedi veya muhasebe kaydı değildir.

## Özellikler ve veri

| İşlem öncesi alan | Birim / desteklenen aralık |
| --- | --- |
| meat_type | beef / lamb; sentetik et türleri |
| meat_kg | 60–160 kg |
| spice_kg | 0,8–4,2 kg |
| casing_kg | 2–10,5 kg |
| meat_cost_eur / spice_cost_eur / casing_cost_eur | Bilinen planlı parti payının alış bedeli; sırasıyla 0–2500 / 0–150 / 0–200 EUR |
| planned_producer_profile | producer_a / producer_b / producer_c: **kurgusal profil**, gerçek firma kimliğinin öğrenilmiş karşılığı değildir |
| package_weight_kg | 0,5–1,5 kg/paket |
| estimated_service_eur | Üretim öncesi bağımsız ön teklif, 200–900 EUR; gerçekleşen paket × tarife girilmez |

Bu sınırlar veri üretim tasarımının dış dikdörtgenidir; bütün uç kombinasyonlar eğitimde gözlenmiş değildir. Sınır içinde de dağılım dışı kombinasyon riski vardır. Özellikle maliyet/ürün oranları gerçek işletme verisiyle doğrulanmalıdır. API paket ve kg dışında birimi, EUR dışında parayı reddeder. İşleme bağlı kayıtta ürün paket ağırlığı DB ile eşleşir ve üretici UUID'si bağlamda korunur; profilin seçimi kullanıcının açık sentetik varsayımıdır.

600 bağımsız sentetik işlem; hayalî kronolojik tarihle 360 train, 120 validation, 120 test. Üretici/et etkileri, miktar ve maliyet varyasyonu ile bağımsız gözlenmeyen süreç gürültüsü vardır. `actual_finished_quantity`, `actual_total_cost_eur`, `actual_yield_ratio`, `actual_service_factor`, EKP ve fiili fire özellik allowlist'inde yoktur. PDF örnek sonucu eğitime katılmadı.

## Yöntem

DictVectorizer + train-only StandardScaler + iki hedefli **Ridge**, alpha **10**. Alpha 0,1/1/10 validation'da seçildi; test seçime/fit'e katılmadı. Az özellikli, simülasyonda yaklaşık doğrusal etkiler için bu açıklanabilir model yeterli bulundu. RandomForest gibi daha karmaşık yöntem eklenmedi.

Öğrenilen hedefler: `y = finished_kg / planned_input_kg` ve `s = actual_service_eur / estimated_service_eur`. Hizmet hedefinin gerçek değeri yalnız eğitim etiketi olarak vardır. Başlangıç varsayımı planlanan girdilerin tamamının tüketileceğidir; gerçek iade/ikame tahmin sapmasına neden olur.

- Tahmini paket = `ŷ × (et + baharat + kılıf kg) / paket_kg`.
- Tahmini toplam = `bilinen planlı malzeme bedelleri + ön teklif × ŝ`.
- Tahmini EKP = `tahmini toplam / tahmini paket`.

Verim [0,01;1], hizmet çarpanı [0,01;3] aralığına fiziksel/güvenlik projeksiyonu uygulanır; sonlu olmayan sonuç reddedilir. Bunlar güven aralığı değildir. Baseline yalnız training ortalama verimi/hizmet çarpanını aynı formüllerde kullanır. Böylece model yalnız sonradan bilinen gerçek EKP formülünü tekrar çalıştırmaz; hem miktar hem hizmet sapması önceden öğrenilir.

ML hesabı kayan noktalı istatistiksel tahmindir; parasal defter değildir. API giriş/çıkışları ondalık metin, kesin gerçekleşme ve sapma hesabı Decimal'dır. Tahmin tutarları 6 hane ve EKP gösterimi 2 hane döner; bu tahminlerden kesin toplam/dağıtım üretilmez.

## Ayrılmış test sonucu (n=120, sentetik)

| Hedef | Birim | Baseline MAE / RMSE | Ridge MAE / RMSE |
| --- | --- | --- | --- |
| Miktar | paket | 2,647265 / 3,626324 | 1,133140 / 1,577510 |
| Verim | kg/kg | 0,017148 / 0,021050 | 0,007237 / 0,008839 |
| EKP | EUR/paket | 0,542426 / 0,674486 | 0,183869 / 0,244472 |
| Tahmini toplam bedel | EUR | 19,531858 / 24,919331 | 9,850957 / 12,590720 |

100/2/5 kg, 970/48/58 EUR, 1 kg paket, producer_a, beef ve **kurgusal bağımsız 450 EUR ön teklif** için: **86,368585 paket**, verim **0,807183**, tahmini toplam **1517,629016 EUR**, EKP **17,571540 EUR/paket**. Referans gerçekleşme 85 paket, 1543,50 EUR ve 18,16 gösterimdir. Bu örnekte EKP mutlak sapması **0,587284 EUR/paket**, test ortalama hatasından büyüktür; 85 ve 18,16 girdi değildir.

## Sınırlamalar ve sürümleme

Gerçek veri ile dış doğrulama, kalibre belirsizlik, çoklu mamul/yan ürün/iade özellikleri, üretici kimliklerinin gerçek geçmişte öğrenilmesi ve fiyat rejimi değişim takibi yoktur. Beklenen çıktı tek paket ürünüdür; gerçekleşme farklı/çok ürünlü ise karşılaştırma null ve gerekçeli döner. Recipe/ürün konfigürasyonu veya öğrenme yöntemi değişirse şema/release sürümü artırılmalıdır. `ridge-v1` sabit eğitim reçetesidir; veri SHA-256 kısaltması sürümdedir, tam hash metadata'dadır. Aynı seed, veri, pinli ortam ve sabit eğitim zamanı aynı artifact'i üretir.

Tahmin kaydı model sürümü/zamanı/özellikleri/sonucu saklar. Yeni model geldiğinde önceki sonuç yeniden hesaplanmaz. Eğitim komutu ve testler [README](README.md), gerçek API [INTEGRATION](INTEGRATION.md) belgesindedir.

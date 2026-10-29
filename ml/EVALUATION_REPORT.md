# Ayrık değerlendirme — AI Model v2

29 Ekim 2026. **SYNTHETIC; gerçek işletme satırı 0.** Metrikler benzetilmiş süreçte hatadır; gerçek doğruluk, güven aralığı veya yüzde başarı değildir. V1 artefaktları, manifest, metrikler ve 120+120 sabit test satırı [v1 arşivinde](evaluation/v1/) korundu.

## Deney tasarımı

Her model 3.000 bağımsız işlem: kronolojik 1.800 train / 600 validation / 600 test. Seed 20261029, veri sürümü synthetic-v2. Tarihler kurgusal; gerçek mevsimsellik veya zamansal genelleme kanıtlanmaz. Küçük/orta/büyük partiler ve farklı paket/maliyet/profil kapsamı hem train hem holdoutlarda vardır. Sınır süreçleri farklı kayıtlar ve bağımsız gürültü ile üretilir.

DictVectorizer ve StandardScaler yalnız train üzerinde fit edilir. Ridge alpha 0,1/1/10 yalnız validation'da seçilir. Hedefler train standart sapmalarıyla normalize edilir; seçim skoru farklı birimleri gelişigüzel toplamaz. Baseline yalnız train ortalama verimi/hizmet çarpanı veya parça oranıdır. Validation sonrasında yeniden fit yoktur. Önceden kodlanan prototip kabul kapısı validation normalized RMSE'nin baseline'dan düşük olmasıdır; test ve eski test bu kararı veya alpha'yı belirlemez. Her iki kapı geçti: üretim alpha=1, kesim alpha=0,1.

V2 yalnız v1 ile aynı dağılımdan daha çok satır değildir. Girdi kapsamı, parti/paket boyu ve fiyat dağılımları, küçük parti etkisi ve bağımsız süreç gürültüsü genişletildi. Bunlar yeni mühendislik varsayımlarıdır; simülatör değişikliği gerçek işletmeden öğrenilmiş iyileşme değildir. Son test hedefleri değiştirilince scaler/katsayı/alpha'nın değişmediği test edildi. Üretim sınır kayıtlarının parti etiketi miktara göre düzeltildi; bu yalnız kullanılmayan açıklayıcı sütunu değiştirdi: katsayı, scaler ve alpha byte-değer olarak aynı kaldı, test sonucuna göre yeniden ayarlanmadı.

## V2 geniş test — aynı 600 satırda baseline / yeni model

| Model / hedef | Birim | n | Baseline MAE / RMSE | V2 Ridge MAE / RMSE |
| --- | --- | --- | --- | --- |
| production / Mamul miktarı | package | 600 | 4.356980 / 9.309748 | 1.899243 / 3.843486 |
| production / Verim | ratio | 600 | 0.023154 / 0.027879 | 0.010307 / 0.012904 |
| production / Birim EKP | EUR/package | 600 | 0.903017 / 1.240929 | 0.350307 / 0.505783 |
| production / Toplam maliyet | EUR | 600 | 22.183457 / 38.596749 | 12.450015 / 22.321937 |
| cutting / But | kg | 600 | 0.270001 / 0.434086 | 0.129030 / 0.190670 |
| cutting / Omuz | kg | 600 | 0.149168 / 0.231549 | 0.130913 / 0.194764 |
| cutting / Sırt | kg | 600 | 0.197052 / 0.307690 | 0.128628 / 0.188049 |
| cutting / Kaburga | kg | 600 | 0.181591 / 0.279620 | 0.134647 / 0.200164 |
| cutting / Kıyma | kg | 600 | 0.167165 / 0.258174 | 0.137021 / 0.199011 |
| cutting / Parça toplamı | kg | 600 | 0.443031 / 0.692119 | 0.285940 / 0.434307 |
| cutting / Açıklanması gereken fark | kg | 600 | 0.443031 / 0.692119 | 0.285940 / 0.434307 |
| cutting / Verim | ratio | 600 | 0.011987 / 0.014820 | 0.008536 / 0.010819 |

## V2 testinin v1'in desteklediği ortak alt kümesi

Aynı satır/hedeflerde üç yöntem karşılaştırılır. Üretim n=66; kesim n=199. Alt küme yalnız özellik aralığıyla seçilir; hata sonucu veya hedefle seçilmez. V1'in desteklemediği küçük/büyük girdilere v1 için hayalî sonuç yazılmaz.

| Model / hedef | Birim | n | Baseline MAE / RMSE | V1 Ridge MAE / RMSE | V2 Ridge MAE / RMSE |
| --- | --- | --- | --- | --- | --- |
| production / Mamul miktarı | package | 66 | 2.569888 / 3.484266 | 1.288153 / 1.894631 | 1.180829 / 1.616089 |
| production / Verim | ratio | 66 | 0.022537 / 0.026747 | 0.010641 / 0.013963 | 0.010570 / 0.012898 |
| production / Birim EKP | EUR/package | 66 | 0.961562 / 1.181889 | 0.386846 / 0.556740 | 0.390752 / 0.528683 |
| production / Toplam maliyet | EUR | 66 | 19.336404 / 25.446926 | 11.350841 / 15.223476 | 11.613796 / 15.576864 |
| cutting / But | kg | 199 | 0.132665 / 0.167911 | 0.134481 / 0.180885 | 0.115756 / 0.148807 |
| cutting / Omuz | kg | 199 | 0.117823 / 0.151167 | 0.118004 / 0.153188 | 0.116978 / 0.150305 |
| cutting / Sırt | kg | 199 | 0.114107 / 0.142346 | 0.127919 / 0.166602 | 0.109926 / 0.138655 |
| cutting / Kaburga | kg | 199 | 0.131165 / 0.168281 | 0.134130 / 0.170972 | 0.127241 / 0.163279 |
| cutting / Kıyma | kg | 199 | 0.128839 / 0.164036 | 0.131622 / 0.168720 | 0.127078 / 0.161826 |
| cutting / Parça toplamı | kg | 199 | 0.267374 / 0.343107 | 0.283204 / 0.365322 | 0.251176 / 0.325603 |
| cutting / Açıklanması gereken fark | kg | 199 | 0.267374 / 0.343107 | 0.283204 / 0.365322 | 0.251176 / 0.325603 |
| cutting / Verim | ratio | 199 | 0.009215 / 0.011791 | 0.009539 / 0.011996 | 0.008571 / 0.010998 |

Üretimde ortak kümede **üç metrik geriledi**: EKP MAE **0,386846 → 0,390752 EUR/paket**, toplam maliyet MAE **11,350841 → 11,613796 EUR** ve toplam maliyet RMSE **15,223476 → 15,576864 EUR**. EKP RMSE düşmesine rağmen MAE artmıştır; bir metriğin iyileşmesi genel iyileşme sayılmaz. Diğer ortak metriklerde bu koşumda v2 daha iyi olsa da 66 satır ve tek sentetik seed istatistiksel üstünlük kanıtı değildir. Ayrı n=120 v1 hatasıyla n=600 geniş v2 hatasını doğrudan kıyaslamak doğru değildir.

## Değişmeyen v1 testindeki gerileme — aynı 120 satır

Aşağıdaki test eğitim/alpha/terfi seçimine katılmadı. Yeni süreç varsayımları nedeniyle eski sabit testte hata arttı; bu bulgu gizlenmedi.

| Model / hedef | Birim | n | V1 Ridge MAE / RMSE | V2 Ridge MAE / RMSE |
| --- | --- | --- | --- | --- |
| production / Mamul miktarı | package | 120 | 1.133140 / 1.577510 | 1.537622 / 2.209835 |
| production / Verim | ratio | 120 | 0.007237 / 0.008839 | 0.009907 / 0.012099 |
| production / Birim EKP | EUR/package | 120 | 0.183869 / 0.244472 | 0.266734 / 0.348483 |
| production / Toplam maliyet | EUR | 120 | 9.850957 / 12.590720 | 10.140018 / 13.119375 |
| cutting / But | kg | 120 | 0.086635 / 0.108347 | 0.120159 / 0.157945 |
| cutting / Omuz | kg | 120 | 0.100124 / 0.121375 | 0.102455 / 0.123735 |
| cutting / Sırt | kg | 120 | 0.102090 / 0.127824 | 0.114349 / 0.149920 |
| cutting / Kaburga | kg | 120 | 0.084369 / 0.107190 | 0.086387 / 0.111767 |
| cutting / Kıyma | kg | 120 | 0.098550 / 0.128122 | 0.101696 / 0.131946 |
| cutting / Parça toplamı | kg | 120 | 0.210162 / 0.265058 | 0.231654 / 0.318115 |
| cutting / Açıklanması gereken fark | kg | 120 | 0.210162 / 0.265058 | 0.231654 / 0.318115 |
| cutting / Verim | ratio | 120 | 0.007436 / 0.009053 | 0.008022 / 0.010226 |

**Karar:** V2, genişletilmiş SYNTHETIC v2 senaryosu için yerel prototipte etkinleştirildi; v1'e karşı genel doğruluk artışı onaylanmadı. Eski dağılım öncelikliyse v1'in korunmuş çiftleriyle geri dönüş mümkündür. Gerçek üretimde otomatik model terfisi veya gerçek başarım kabulü yoktur. Yeni veya eski gerçek işletme verisi edinilince ayrı dış doğrulama gerekir. Test sonuçlarına göre simülatör/hedef/alpha ayarı yapılmadı.

## Güvenli çıkarım ve sınırlamalar

V2 girişleri doğrulanmış artefaktın sınırları ve miktar oranlarıyla denetlenir. Sınır dışı alanlar 422 ve alan/birim/min/max ile döner; sessiz girdi kırpması yoktur. Fiziksel olarak geçersiz ham v2 model sonucu güvenilir tahminmiş gibi projekte edilmez; 503 ile reddedilir. V1 JSON çiftleri eski politikalarıyla okunabilir. API yayımlanmış kesim parçalarını altı hanede aşağı yuvarlar, toplam/farkı Decimal ile bu parçalardan üretir. Fark otomatik fire değildir.

Maliyetler ve sonuçlar karar destek tahminidir; kesin maliyet motoru, stok, satış, lot grafı veya recall model çıktısından yazılmaz. Beklenen paket sayısı sürekli değerdir; kesin üretim adedi değildir. Kuzu beş parça dışı reçete, yeni et türü/gerçek üretici kimliği, gerçek fiyat rejimi, hayvan yaşı/kondisyonu/operatör ve kalibre belirsizlik yoktur. Üretim para girdileri planlı maliyet ve bağımsız hizmet ön teklifidir; gerçekleşen miktar/EKP/hedef girdi olamaz.

[Eğitim komutları](README.md), [API ve dağıtım](INTEGRATION.md), [kabul raporu](../docs/AI_MODEL_V2_ACCEPTANCE.md), [tam metrikler ve ayrık ID'ler](evaluation/metrics.json).

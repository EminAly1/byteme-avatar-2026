# Model B — kuzu parçalama verimi

**Sürüm:** `cutting-ridge-v1-ddd7ab8f61fd`. **Kaynak:** yalnız SYNTHETIC; 600 satır (360/120/120), gerçek tarihsel kesim 0. [JSON model](models/cutting.json), [manifest](data/manifest.json), [değerlendirme](evaluation/metrics.json).

## Amaç, özellikler ve ürün eşlemesi

Parçalama başlamadan Kuzu, 18–40 kg giriş ağırlığı ve `five_parts_v1` şekli için but, omuz, sırt, kaburga, kıyma kg'larını tahmin eder. API ayrıca gerçek `recipe_version_id`, beş ayrı parça ürün UUID'si ve isteğe bağlı kesim `operation_id` ister; reçete türünü/sürümünü, üyelikleri, kg mamul türlerini ve müsaitliği DB'de doğrular. Tahmin kaydı gerçek sürüm, code, adlar ve caller tarafından ilan edilmiş parça→ürün eşlemesini korur; isimlerden kendiliğinden ürün/lot ilişkisi uydurmaz. Slot eşlemesinin anlamsal doğruluğunu işletme seçer/onaylar.

Tür ve reçete şekli eğitimde sabittir; öğrenilen ana etki **işlem öncesi giriş ağırlığıdır**. Reçete UUID/sürümü eğitimde bir tarihsel özellikmiş gibi kullanılmaz. Dağıtım anahtarının quantity/value seçimi muhasebe politikasıdır; kesim ağırlığına kanıtsız etki atfedilmez. Beşten farklı çıktı veya yan ürün içeren reçeteler bu model için reddedilir. Kuzu dışındaki türlere genelleme iddiası yoktur.

PDF yalnız toplam 22 kg'yi ve giriş 25 kg'yi belirtir. **6/4/4/5/3 kg demodaki kurgusal tartımlardır.** Eğitim generator'ündeki oran profilleri, ağırlık eğimleri ve gürültü de mühendislik varsayımıdır; ölçülmüş geçmiş değildir. Eğitimde çeşitlenen giriş ağırlıkları/oran profilleri ve bağımsız gözlenmeyen kesim gürültüsü kullanılır. Gerçek parça ağırlıkları ve fiili fark yalnız hedef/değerlendirmedir.

## Algoritma ve fiziksel sınırlar

Train-only DictVectorizer + StandardScaler + beş hedefli **Ridge**, alpha **0,1** (0,1/1/10 validation seçimi). Baseline training'deki sabit ortalama parça oranlarını kullanır. Az gözlenebilir özellikli sentetik süreç için açıklanabilir doğrusal yaklaşım seçildi; ilave karmaşık model eklenmedi.

Her hedef `parça_kg / giriş_kg` oranıdır. Negatif oranlar sıfırlanır; oranların toplamı 1'den büyükse hepsi toplamlarına bölünür. Ağırlıkla çarpıldıktan sonra API parça kg'larını 6 ondalıkta aşağı yuvarlar; toplam ve farkı Decimal ile bu yayımlanmış parçalardan türetir. Böylece **yayımlanmış parçalar toplamı ≤ giriş kg**, toplam+fark=giriş kg kalır. Sıfır/negatif/NaN/sonsuz girdi reddedilir; sonlu olmayan model sonucu 503 olur. Projeksiyon güven aralığı veya doğru tahmin garantisi değildir.

`predicted_difference_kg` giriş eksi tahmini parça toplamıdır. Bunun fire, yan ürün veya ölçüm farkı olduğu model tarafından sınıflandırılmaz. Gerçek kapanış her zamanki kesin miktar ve açıklamayı ister; tahmin hiçbir stok/lot/maliyet kaydı oluşturmaz.

## Test hatası (n=120, sentetik)

| Hedef | Birim | Baseline MAE / RMSE | Ridge MAE / RMSE |
| --- | --- | --- | --- |
| But | kg | 0,155579 / 0,187893 | 0,086635 / 0,108347 |
| Omuz | kg | 0,105016 / 0,127399 | 0,100124 / 0,121375 |
| Sırt | kg | 0,123697 / 0,157380 | 0,102090 / 0,127824 |
| Kaburga | kg | 0,089872 / 0,114425 | 0,084369 / 0,107190 |
| Kıyma | kg | 0,106808 / 0,137902 | 0,098550 / 0,128122 |
| Toplam | kg | 0,254808 / 0,333909 | 0,210162 / 0,265058 |
| Açıklanması beklenen fark | kg | 0,254808 / 0,333909 | 0,210162 / 0,265058 |
| Verim | kg/kg | 0,009108 / 0,011433 | 0,007436 / 0,009053 |

Omuz/kaburga/kıyma iyileşmeleri küçüktür; gözlenmeyen süreç farkları tek ağırlık özelliğinden öğrenilemez. Yalnız bu sentetik ayrımda tüm hedefler baseline'dan iyi çıktı; istatistiksel anlamlılık, gerçek işletme başarımı veya yeni reçete performansı gösterilmedi.

## 25 kg demo

| Parça | Tahmin kg | Gerçek ledger'a girilen **kurgusal demo** kg |
| --- | --- | --- |
| But | 5,875229 | 6 |
| Omuz | 4,025129 | 4 |
| Sırt | 3,950854 | 4 |
| Kaburga | 4,878152 | 5 |
| Kıyma | 3,077829 | 3 |
| Toplam | 21,807193 | 22 |
| Açıklanması gereken fark | 3,192807 | 3 (kurgusal fire sınıfı) |

Tahmini toplam verim **0,872288**; kurgusal gerçekleşme **0,88**. Giriş 25 kg ve alış bedeli 287,50 EUR mevcut Decimal motorunda kalır. Kesim modeli fiyat/maliyet tahmin etmez; para dağıtımı mevcut deterministik backend'dedir.

Gerçek ölçümler, hayvan yaşı/cinsi/kondisyonu, operatör, anatomik sınırlar ve yan ürün özellikleri yoktur. Yeni gerçek veri sürümü ayrı değerlendirilmeden eğitim başarı iddiası kurulamaz. İzlenebilirlik/recall sonuçlarına modelden hiçbir bağımlılık eklenmedi. Kullanım ve sürümleme [README](README.md), kayıt/gerçek/sapma [INTEGRATION](INTEGRATION.md) içindedir.

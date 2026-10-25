# Ayrılmış test değerlendirmesi — Görev 09

25 Ekim 2026. **Bütün eğitim/validation/test verileri SYNTHETIC; gerçek işletme performansı ölçülmedi.**

Her model 600 kayıt: kronolojik ilk 360 train, sonraki 120 validation, son 120 test. Seed 202609. Tarihler ve süreç etkileri kurgusaldır. Preprocessing yalnız train üzerinde fit edildi; alpha yalnız validation ile seçildi; test seçime katılmadı. Ayrık ID/tarih ve scaler kontrolleri otomatik test edildi.

Ridge, az özellikli sentetik süreç ve taşınabilir açıklanabilir katsayıları için seçildi. Baseline training ortalama verim/hizmet çarpanı veya parça oranıdır. Fiziksel projeksiyon her iki yöntem için aynı şekilde uygulanır. Heterojen birimler tek hata sayısında toplanmadı.

| Model / hedef | Birim | n test | Baseline MAE | Baseline RMSE | Ridge MAE | Ridge RMSE |
| --- | --- | --- | --- | --- | --- | --- |
| production / finished_quantity | package | 120 | 2.647265 | 3.626324 | 1.133140 | 1.577510 |
| production / yield_ratio | ratio | 120 | 0.017148 | 0.021050 | 0.007237 | 0.008839 |
| production / ekp_eur_per_unit | EUR/package | 120 | 0.542426 | 0.674486 | 0.183869 | 0.244472 |
| production / total_cost_eur | EUR | 120 | 19.531858 | 24.919331 | 9.850957 | 12.590720 |
| cutting / leg_kg | kg | 120 | 0.155579 | 0.187893 | 0.086635 | 0.108347 |
| cutting / shoulder_kg | kg | 120 | 0.105016 | 0.127399 | 0.100124 | 0.121375 |
| cutting / back_kg | kg | 120 | 0.123697 | 0.157380 | 0.102090 | 0.127824 |
| cutting / rib_kg | kg | 120 | 0.089872 | 0.114425 | 0.084369 | 0.107190 |
| cutting / mince_kg | kg | 120 | 0.106808 | 0.137902 | 0.098550 | 0.128122 |
| cutting / total_weight_kg | kg | 120 | 0.254808 | 0.333909 | 0.210162 | 0.265058 |
| cutting / difference_kg | kg | 120 | 0.254808 | 0.333909 | 0.210162 | 0.265058 |
| cutting / yield_ratio | ratio | 120 | 0.009108 | 0.011433 | 0.007436 | 0.009053 |

## Seçim ve zayıf sonuçlar

Üretim alpha=10, kesim alpha=0,1. Validation aday skorları/hedef hataları, ayrım tarihleri/ID'leri ve tam hassasiyetli metrikler [metrics.json](evaluation/metrics.json) içinde. Validation skoru üretimde farklı birimler ölçeklenerek, kesimde yalnız kg hedefleriyle kuruldu; bu skor son kullanıcıya tek genel doğruluk gibi sunulmaz.

Bu ayrımda hiçbir hedef baseline'dan kötü çıkmadı. Kesimde omuz/kaburga/kıyma kazanımları küçük; yalnız giriş ağırlığı gözlenmeyen hayvan/operatör farklarını açıklayamaz. Tek kurgusal holdout, üretici üretim kalitesini veya yeni reçete/tür başarısını kanıtlamaz. Güven aralığı, anlamlılık analizi ve gerçek veriyle dış doğrulama yoktur.

Üretim demo EKP sapması 0,587284 EUR/paket ile test MAE 0,183869'dan büyüktür. Tek demo hedefinin eğitim ortalamasıyla aynı çıkması beklenmez. 85 paket ve 18,16 EUR sonuçları girdiye eklenmedi; 450 EUR hizmet ön teklifi ve üretici profili kurgusal varsayımdır.

## Gerçek HTTP demo — tahmin ve gerçekleşme ayrı

Üretim gerçekleşmesi PDF referansı olarak gerçek demo ledger'ına girildi; kesim gerçekleşmesi gerçek ledger'a yazılmış **kurgusal** 6/4/4/5/3 kg ölçüleridir. Bunlar gerçek işletme tarihi değildir.

| Model / hedef | Tahmin | Demo gerçekleşme | Mutlak sapma | Yüzde (gerçek payda) |
| --- | --- | --- | --- | --- |
| production / yield_ratio | 0.807183 | 0.794393 | 0.012790 | 1.610095 |
| production / total_cost_eur | 1517.629016 | 1543.500000 | 25.870984 | 1.676125 |
| production / ekp_eur_per_unit | 17.571540 | 18.158824 | 0.587284 | 3.234150 |
| production / finished_quantity | 86.368585 | 85.000000 | 1.368585 | 1.610100 |
| cutting / leg_kg | 5.875229 | 6.000000 | 0.124771 | 2.079517 |
| cutting / rib_kg | 4.878152 | 5.000000 | 0.121848 | 2.436960 |
| cutting / back_kg | 3.950854 | 4.000000 | 0.049146 | 1.228650 |
| cutting / mince_kg | 3.077829 | 3.000000 | 0.077829 | 2.594300 |
| cutting / shoulder_kg | 4.025129 | 4.000000 | 0.025129 | 0.628225 |
| cutting / yield_ratio | 0.872288 | 0.880000 | 0.007712 | 0.876364 |
| cutting / difference_kg | 3.192807 | 3.000000 | 0.192807 | 6.426900 |
| cutting / total_weight_kg | 21.807193 | 22.000000 | 0.192807 | 0.876395 |

Tahmini toplam 21,807193 kg + açıklanması gereken 3,192807 kg = 25 kg; fark otomatik fire değildir. [Tam HTTP yanıtı](reports/demo.json).

## Doğrulanan çalışmalar

- Başlangıç: 131 backend testi, gerçek izole MySQL 8.0.46; [çıktı](reports/baseline-tests.txt).
- Son paket: **181 geçti, 0 fail, 0 skip** = önceki 131 + 31 yeni backend + 19 model testi; [çıktı](reports/full-tests.txt).
- 31 yeni backend testi: 30 forecast API/izolasyon vakası + 1 migration vakası. TestClient süreç içidir; sıfır yüzde-payda dalında kontrollü actual_values stub'ı kullanılır. Model yeniden eğitim/varyant testi gerçekten ikinci veri seed'iyle Ridge eğitir.
- İki ayrı senaryo gerçek TCP HTTP → FastAPI → MySQL ile çalıştı; idempotent tekrar aynı UUID'leri verdi. Demo DB'de 2 forecast, 2 operation, 10 lot, 20 movement, 8 kesin lot bağlantısı; [DB sayımları](reports/live-database.json).
- `/health`, `/health/ready`, iki POST, model listesi ve saved prediction GET gerçek HTTP akışındadır. Stok/lot/recall ayrımı yeni testlerde bütün operasyonel tabloların önce/sonra snapshot'ıyla denetlendi.
- Negatif/NaN/sonsuz girdi, model katsayısı/çıktısı, bozuk checksum/şema, eksik model, yanlış key, birim ve sızan hedef alanları için güvenli hata testleri geçti.
- Bir üçüncü taraf Starlette/AnyIO deprecation uyarısı var; test hatası değildir.

## Sınırlamalar ve çalıştırılmayanlar

İlk MySQL başlatma denemesi hazır olmama nedeniyle bağlantı hatası verdi; servis hazırlandıktan sonra temiz başlangıç koşusu 131 geçti. Eğitim doğrulamasındaki NumPy skaler tipiyle ilgili iki test hatası düzeltildi ve bütün paket tekrar koşularak 181 geçti. Bu başarısız ilk denemeler başarı gibi gösterilmedi.

Gerçek iş verisi, React tahmin/sapma ekranı, Android tahmin ekranı, üretim kullanıcı/rol yetkilendirmesi, canlı HTTPS dağıtımı ve model drift/güven aralığı çalışması yoktur. Frontend/Android testleri bu görevde tekrar çalıştırılmadı; tam Compose image/stack build çalıştırılmadı. API kullanan DB erişim sınırları mevcut prototype X-API-Key modelidir. Üretim operasyonlarına deploy veya main merge yapılmadı.

Yıkıcı testler `avatar_ml_core_test`/`avatar_migration_test`; gerçek HTTP demo ayrı `avatar_ml_demo_test`. Gerçek işletme verisi kullanılmadı. Kaynak kapsamı yalnız ml/, backend/, tests/; ortak checklist durumu [README devir tablosunda](README.md).

# Jüri videosu — en fazla 14 dakika 30 saniye

28 Ekim 2026. **Çekim planıdır; video çekildi/yüklendi iddiası değildir.** Kaynak: [final kabul](FINAL_RELEASE_READINESS.md), [kullanım](USER_GUIDE.md), [tekrarlanabilir demo](DEMO_RUNBOOK.md). Yarışma sınırı kullanıcı tarafından bildirilen **≤15 dakika**; 30 saniye güvenlik payı bırakılır.

## Çekimden önce

- Yalnız izole yerel *_test şemasını ve KURGUSAL/SYNTHETIC veriyi açın. Eski işletme verisi/volume'u silmeyin.
- Üç servis healthy, API ready, iki model ve gerçek PDF hazır olmalı. Aşağıdaki görünümleri önceden sekmelerde açın; uzun kurulum/indirme beklemelerini kaydetmeyin.
- Terminalde env, API anahtarı, fixture/Keystore veya gerçek müşteri bilgisi göstermeyin. Android bağlantısını kayıttan önce yapın.
- Android için taze 6 kg value but gerekir. Mevcut kabul kaydı 5 kg/blokeliyse geçmiş onayı gösterin; canlı 6→5 çekimi için ayrı yeni demo şeması hazırlayın, eski stoğu geri yazmayın.
- Mevcut posted işlemleri yeniden kapatmayın. Veri hazırlığını ve doğal satış/recall sırasını çekimden önce prova edin.

## Zaman çizelgesi

| Süre | Ekran / işlem | Anlatılacak kesin sonuç |
| --- | --- | --- |
| 0:00–1:00 | Dashboard | “ByteMe ekibinin üretim, maliyet ve lot izleme prototipi. Görülen bütün işletme kayıtları kurgusal.” Gerçek API özetleri; yeni marka iddiası yok |
| 1:00–2:00 | Kısa mimari görseli ve modüller | React→FastAPI→MySQL kesin defter; Kotlin Room taslak/cache/outbox; iki kayıtlı sentetik model. SQLite merkezî stok otoritesi değildir |
| 2:00–4:00 | `/alislar`, `/uretim/:id` | ET-2026-001→URT-2026-045→SUC-2026-045. Fiilî 970+48+58+467,50=1.543,50 EUR; 85 paket; gösterim EKP18,16. Yuvarlanmış EKP'den toplam yeniden hesaplanmaz |
| 4:00–5:20 | `/parcalama` ve işlem detayı | 25 kg giriş, 22 kg beş parça, açıklanmış3 kg; 287,50 EUR korunur. Miktar/değer dağıtımı ve gerçek parça lotları. 351 EUR kaynak tutarsızlığı açıklanır |
| 5:20–6:50 | Gerçek Kotlin uygulaması | Müşteri/lot/1 kg satış onayı, backend UUID ve 6→5 kg; Room/outbox aynı-key tekrar. Offline yalnız taslak. Kabul edilen emülatör sürümünü açık söyleyin; fiziksel cihaz diye sunmayın |
| 6:50–9:00 | `/hareketler`, rework, `/dagitimlar` | Transfer20→13/7; sevke bağlı iade/karantina ve sevksiz iptal; rework10→9,5+0,5 kg, 100+15=115 EUR; Market A→X12 kayıtlı ikinci kademe. Transfer anı ile sonraki bakiyeyi ayırın |
| 9:00–10:30 | `/izlenebilirlik`, `/geri-cagirma/:id` | ET kökünden SUC ve Market A/B/C; gerçek kayıtlı X. Şirket sevkiyatı85; tahsis edilmemiş18 fiziksel stok değildir. Blokeli yeni satış reddi; salt ekran uyarısı değil backend kontrolü |
| 10:30–12:00 | `/yapay-zeka`, `/uyarilar` | İki SYNTHETIC model, kayıtlı işlem öncesi tahmin ve kesin gerçekleşme ayrımı. SKT/blokaj/açık düşük stok eşiği, uygun EKP/verim sapması. İnceleme uyarısı deftere yazmaz; gerçek anomali doğruluğu iddiası yok |
| 12:00–13:30 | `/satislar/:id`, `/belgeler/satis/:id` | Backend kârlılık; orijinal satış ve iade/iptal ayrı. Geçici notu düzenle, gerçek Türkçe A4 PDF indir/aç; ayrı Yazdır. Müşteri PDF'sinde iç maliyet/kâr yok; resmî mali belge değildir |
| 13:30–14:30 | Dashboard ve kapanış | Gerçek FK izleme, transaction/idempotency, test kanıtı ve açık sınırlar. RBAC/TLS, resmî e-Fatura/OCR/arşiv ve gerçek veri model başarımı tamamlandı denmez. Repo/video teslim bağlantıları |

## OBS ile yerel kayıt

1. OBS Studio'da ekran/pencere yakalama ve mikrofon ekleyin. Bildirimleri kapatın, yalnız demo pencerelerini gösterin.
2. 1280×720 veya 1920×1080, 30 fps yeterlidir. Kaydı MKV olarak alın; OBS “Remux Recordings” ile paylaşılabilir MP4 üretilebilir.
3. 20 saniyelik ses/yazı okunabilirliği denemesi yapın. Asıl kayıtta zamanlayıcı kullanın; 14:30 hedefini aşan bölümleri yeniden çekin/kısaltın.
4. Son MP4'ü baştan sona açın; Türkçe yazı, Android ekranı ve indirilen PDF'nin göründüğünü kontrol edin. Dosya süresini medya oynatıcı veya `ffprobe` ile doğrulayın.
5. Ekip hesabından erişilebilir bağlantı sağlayın; gizli pencerede oturumsuz açılış ve videonun ≤15 dakika olduğunu doğrulayın. Gerçek video URL'sini e-posta taslağına ekip ekler.

Video çekilmeden/yüklenmeden TES-03/DOC-03 teslim materyali ve TES-05 gönderim tamamlandı sayılmaz. Gönderim/alındı ayrı insan adımıdır.

# AVATAR jüri videosu — 14 dakika 30 saniye

**31 Ekim 2026 · ByteMe.** Görev 21–25 arayüzleriyle güncellenmiş çekim planı;
video çekildi/yüklendi iddiası değildir. Kullanıcı sınırı **≤15 dakika**;
30 saniye güvenlik payı korunur. [Kurulum](INDIRME.md), [runbook](DEMO_RUNBOOK.md),
[güncel kabul](FINAL_RELEASE_READINESS.md).

## Çekimden önce

- PR #42 tabanı `f2a0a156d769793b16f17d5de09c5a0393f69aae` ve paketleme kodu
  `3f2c5db4d02b93ed3e9f3ba21e15fd8e6245fb6b`; tüm bileşenleri aynı checkout'tan kullanın.
- Yeni, yalnız KURGUSAL/SYNTHETIC `*_test` şeması; eski kayıt/volume temizlenmez.
  Önceden posted işlemi yeniden kapatmayın, stokları demo uğruna geri yazmayın.
- Ekranları ve gerçek PDF'yi önceden açın. Env, API anahtarı, fixture veya müşteri
  kişisel verisini kayda almayın. Yükleme/derleme süresini videoya katmayın.
- Android satış **recall'dan önce** yapılır. Canlı 6→5 kg için ayrı satılmamış,
  blokesiz demo lotu gerekir; geçmiş 5 kg/blokeli lot resetlenmez.
- **Güncel Preview için fiziksel/API28 cihaz kabulü yok.** Çekimden önce cihazda
  açılış, bağlantı, stok/uyarı/satış ve PDF provası yapılmalı. Olmazsa ilgili bölümde
  açık sınırı söyleyin ve doğrulanmış web/API kanıtını gösterin; native başarı uydurmayın.
  Eski uygulamayı uninstall/pm clear etmeyin. API35'i başlatmayın.

## Zaman çizelgesi

| Süre | Güncel ekran / işlem | Anlatım ve kabul sınırı |
| --- | --- | --- |
| 0:00–1:00 | AVATAR dashboard `/` | “ByteMe ekibinin AVATAR prototipi; bütün işletme verileri kurgusal.” Gerçek özetler, yeni menü ve mobil düzen |
| 1:00–2:00 | `/stoklar`, `/alislar` | Kayıtlı/kullanılabilir miktar, lot/SKT ve giriş maliyeti; blokeli stok satılabilir sayılmaz |
| 2:00–3:40 | `/uretim/:id` | ET-2026-001→URT-2026-045→SUC-2026-045 gerçek FK. 970+48+58+467,50=1.543,50 EUR,85 paket, gösterim EKP18,16; yuvarlak birimden toplam üretilmez |
| 3:40–4:50 | `/parcalama/:id` | 25 kg→22 kg+3 kg açıklanmış fark;287,50 EUR korunur. Beş parça/lot ve dağıtım yöntemi; PDF'deki351 EUR tutarsızlığını açıklayın |
| 4:50–6:10 | `/yapay-zeka` | İşlem öncesi tahmin/gerçek gerçekleşme ayrımı. **6.000 SYNTHETIC (3.000/model), 0 gerçek tarihsel kayıt. Bazı v1/v2 metrikleri geriledi**; genel doğruluk artışı yok. Gerçek model/sürüm ve hata tablosunu gösterin |
| 6:10–7:40 | Android Ana Sayfa→Stok→Satış→Bekleyenler→Uyarılar | Yalnız cihaz provası geçtiyse: doğru mikro miktar, gerçek uyarı,1 kg onay/backend UUID,6→5 kg, aynı-key tekrar; offline yalnız taslak. Prova yoksa web satışı ve host kanıtı, cihaz kabulünün eksik olduğu açıkça söylenir |
| 7:40–9:00 | `/izlenebilirlik`, `/geri-cagirma` | Kaynak/neden→**etki önizleme**→lot kodu doğrulama→kesinleştirme. Önizleme yazmaz; değişen etki409 ister. Gerçek türev/Market A/B/C ve kayıtlı X; kesin blokajdan sonra yeni satış LOT_BLOCKED |
| 9:00–10:00 | `/uyarilar` | Kritik/Uyarı/Bilgi, lot/kaynak ve önerilen işlem. Uygulama içi analiz, stok/recall yazmaz; push veya gerçek anomali doğruluğu iddiası yok |
| 10:00–11:30 | `/belgeler/satis/:id` | Ayrı geçici not düzenleme→**Önizle**→çok sayfalı gerçek PDF→indir. Kaynak müşteri/fiyat/miktar/lot kilitli; orijinal ve düzeltme ayrıdır, iç kâr müşteri PDF'sinde yok; resmî fatura değildir |
| 11:30–12:10 | Android Ana Sayfa→Belgeler | **Yalnız cihazda gerçekten açılabildiyse** PdfRenderer sayfa önizleme/SAF kaydet/paylaş. Aksi halde web PDF'yi gösterin ve Android native kabulünün beklediğini söyleyin; fixture ekranını canlı cihaz diye sunmayın |
| 12:10–13:30 | `/hareketler`, rework, `/dagitimlar` | Transfer20→13/7; sevke bağlı iade/karantina; rework10→9,5+0,5kg/115EUR; A→X12 kayıtlı, şirket sevkiyatı85. Tahsis edilmemiş18 fiziksel stok değildir |
| 13:30–14:30 | Mimari ve dashboard kapanış | React/Kotlin→FastAPI→MySQL; Room taslak/outbox. Decimal/transaction/kilit/idempotency, FK soy bağı;31 host+8 hedefli test tarihini söyleyin. Fiziksel/API35, RBAC/TLS, e-Fatura ve teslim sınırlarını açık bırakın |

## Kayıt ve teslim

1. Linux'ta OBS Studio ile pencere/mikrofon;1280×720 veya 1920×1080, 30 fps yeterlidir.
   Önce 20 sn ses/okunabilirlik provası. Bildirimleri ve özel pencereleri gizleyin.
2. MKV kaydını OBS Remux ile MP4'e dönüştürün. Baştan sona açın;
   `ffprobe` veya oynatıcıyla **≤15 dakika** ve okunabilir yazı/sesi doğrulayın.
3. Ekip hesabından video bağlantısı sağlayın; gizli pencerede oturumsuz erişimi deneyin.
   Gerçek URL'yi [e-posta taslağına](SUBMISSION_EMAIL_DRAFT.md) ekleyin.
4. **1 Kasım 2026 23:59 Türkiye saati** öncesi doğrulanmış organizasyon adresine
   kayıtlı ekip üyesi gönderir; gönderim/alındı ayrı kaydedilir.

Video/link ve gönderim yokken DOC-03, TES-03/TES-05 tamamlandı sayılmaz.

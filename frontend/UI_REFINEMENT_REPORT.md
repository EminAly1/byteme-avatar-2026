# ByteMe — Premium UI/UX refinement

Görev 11 · 25 Ekim 2026 · `feature/frontend-premium-ux`

## 1. Tasarım önce/sonra analizi

Başlangıç: `origin/main` = `63a9c86850db5927849bdb4a1e0fe7acb86ca987`.
PR #1–#16'nın merge commit'leri bu commit'in atasıdır: [Git kanıtı](validation-premium/history.json). GitHub GraphQL okuması 403 döndüğü için PR durumları API'den yeniden okunmuş gibi sunulmaz.

AGENTS.md, docs/FRONTEND_VISION.md (görüntülere dayalı son değerlendirme dahil), frontend/VALIDATION_V2.md ve validation-v2/screenshots altındaki 13 gerçek görüntü incelendi. Uygulama değişikliğinden önce 38 birim, 14 Chromium E2E ve 1 eksik-model testi gerçekten çalıştırıldı ve geçti.

Öncelikli kusurlar: dashboard'daki büyük tanıtım alanı göstergeleri aşağı itiyordu; mobil tabloların önemli sütunları yatay kaydırma gerektiriyordu; AI formu sonuçtan önce çok yer kaplıyordu; ürün/lot ayrımı ve recall alıcılarının önceliği zayıftı.

| Ekran | Önce | Sonra |
| --- | --- | --- |
| Dashboard | Büyük hero, önce ürün kartı sayısı; satış/sevkiyat özeti yok | Önce açık üretim ve stoklu lot/konum; gerçek son üretim, satış, sevkiyat ve lot kayıtları. Farklı birimler toplanmaz. Mobilde her listeden iki kayıt; tümüne bağlantı. |
| Kesim | Lot/ürün bitişik, maliyetler solda; mobil yatay tablo | 25 kg = 22 kg + 3 kg kayıtlı ağırlık özeti, gerçek maliyet ve dağıtım yöntemi; ayrı ürün/lot, sağ hizalı tutarlar, mobil kartlar. |
| Satış | İç içe satırlar, bağlamsız “Formu kapat”, uzun teknik kimlikler | Müşteri → lot/miktar/fiyat → gözden geçirme → ayrı kesin onay. “Satış geçmişine dön”; UUID ve hareket referansları açılır/kopyalanır. |
| İzleme | Bağlantı kimlikleri ana akışta | Gerçek FK akışı, yön okları, mobil dikey zincir; atıf ve teknik referanslar ayrı ayrıntıda. |
| Recall | Marketler uzun zincirin sonunda | Kaynak/durum/blok kapsamı → sevk toplamı ve A/B/C → zincir. İletişim ayrıntısı isteğe bağlı; market kalanı hâlâ “Bilinmiyor”. |
| AI | Uzun yeni tahmin formu önce; hassas sayılar/UUID/metrikler aynı ağırlıkta | Yeni ziyaret form ile başlar; seçili kayıt sonuç ile açılır. 3–4 KPI → gerçekleşme karşılaştırması → teknik detay. Tek bağlamsal sentetik veri uyarısı. |

## 2. Güncellenen bileşenler

- `components/presentation.tsx`: ortak sayfa başlığı, KPI, adımlar, kopyalanabilir açılır teknik referans, özet/uyarı bileşenleri.
- `components/dialogs.tsx`: mevcut native dialog/drawer ayrıldı; Tab/Shift+Tab/Escape ve odağı geri verme korundu. Kapalı details içindeki düğmeler `checkVisibility()` ile odak döngüsünden çıkarılır.
- `components/ui.tsx`: durumlar, gerçek loading skeleton, boş/hata sunumu, masaüstü tablo/mobil kart. Aynı satır verisi kullanılır; iki DOM kopyası oluşturulmaz.
- `hooks/useMediaQuery.ts`: değişen viewport'u takip eder. `workflow.tsx` uyumlu yeniden dışa aktarımları korur.
- `lib/presentation.ts`: yalnız AI gösteriminde ondalık metinleri BigInt ile yuvarlar; kaynak metni ve payload'ı değiştirmez.
- Route modülleri `React.lazy`/`Suspense` ile yüklenir. Dashboard form doğrulama paketlerini doğrudan içe aktarmaz.

## 3. Renk, tipografi ve aralıklar

[Semantik tokenlar](src/tokens.css): gece laciverti navigasyon `#102d35`, sıcak zemin `#f5f6f3`, beyaz yüzey, ana metin `#192f39`, ikincil metin `#536973`, işlem teal `#087363`; başarı/uyarı/hata için ayrı metin, yüzey ve sınır tokenları. Amber sentetik veri/işlem uyarısı, kırmızı bloke/geri çağırma/hata anlamındadır.

Başlık 30 px (mobil 26), bölüm 16–20, gövde 14, tablo 13, yardımcı metin 12 px; yoğun tablo ve navigasyon meta alanlarında 10–11 px kullanılır. Sistem fontu kullanılır; haricî font isteği yoktur. Ana aralıklar 4/8/12/16/20/24/32 px, yoğun satırlarda 14/18 px; köşeler 8/12/16 px. Gölgeler hafiftir. Focus çerçevesi 3 px; hover/pressed/disabled durumları ayrıdır.

Önceki style.css/v2.css üst üste override yapısı tek style.css ve tokens.css altında toplandı. Light tema kapsamı tamamlanır; dark tema eklenmedi. Kontrast ölçümü ve axe kanıtları bölüm 7'dedir.

## 4. Metin ve terminoloji

“Prediction UUID” yerine “Tahmin kaydı”, “Recall UUID” yerine “Geri çağırma kaydı”; teknik kimliğe erişim ve kopyalama korunur. Satış özetinde kesin tutarın sunucunun onayından sonra gösterileceği açıkça belirtilir; tarayıcıda satış toplamı hesaplanmaz. Hata mesajı aksiyonu açıklar, destek kodu açılır ayrıntıda saklanır.

AI tutarları 2, miktarlar en fazla 3, yüzdeler en fazla 2 ondalıkla Türkçe gösterilir. EKP birimi açıkça paket başınadır. Verim oranı yüzdeye, mutlak verim sapması yüzde puanına yalnız sunum için dönüştürülür. `null` gerçekleşme sayıya çevrilmez. Tam kaynak değerler, girdiler, model sürümü ve sınırlamalar açılabilir; sentetik doğruluk gerçek işletme doğruluğu gibi sunulmaz. Kesin muhasebe tutarlarının kaynak hassasiyeti korunur.

## 5. Masaüstü, tablet ve mobil

1440×900, 1024×768, 768×1024, 390×844, 360×800 gerçek Chromium ile kontrol edilir. Menü 1100 px altında odak döngülü drawer; tek kolon formlar ve 48 px mobil alanlar, 44 px işlem hedefleri, uzun kodlarda satır kırma kullanılır. 600 px altında tablolar etiketli karttır; mobilde gizli maliyet sütunu bırakılmaz.

Kartlar daha fazla dikey alan kullanabilir; bunun karşılığında miktar, EKP, durum ve bağlantılar yatay kaydırmadan okunur. Dashboard mobil listeleri iki kayda sınırlandırılır ve her bölüm tam listeye bağlanır. Kesim/izleme ekranındaki bütün kesin kayıtlar korunur. Yerel klavyenin açıldığı fiziksel Android/iOS cihaz testi bu çalışmada yapılmadı; Chromium viewport ve inputMode kontrolü fiziksel cihazın yerini tutmaz.

## 6. AI, recall ve satış bilgi hiyerarşisi

AI kaydı URL'den veya başarı sonrası açıldığında sonuç en üsttedir; yeni tahmin, geçmiş ve metrikler açılır bölümlerdedir. Yeni tahmin ekranında form açıktır. Kaynak uyarısı seçili sonuçta bir kez görünür; metrikler ayrıca sentetik test olarak etiketlidir. Model metrikleri seçili tahminin türüyle eşleşir.

Recall kaynak lot ve aktif blok durumuyla başlar. Sevk toplamı backend'in ürün/birim bazlı toplamıdır; A/B/C sıralaması yalnız gösterim sıralamasıdır. Her marketin gerçek sevk ve satış miktarı ayrı kalır; toplamları yeniden hesaplanmaz. Alıcı iletişimi ve teslim belgeleri açılır ayrıntıdadır. Satış ve bağlı sevkiyat ikinci kez toplanmaz.

Satış formu üç anlaşılır gruptadır; ardından aynı kesin onay diyaloğu açılır. Başarı sonrası gerçek satış ayrıntısına geçer. Bağlı sevkiyat mevcut stok hareketini, bağımsız sevkiyat yeni fiziksel çıkışı kullanmaya devam eder.

## 7. Erişilebilirlik ve test sonuçları

| Kontrol | Gerçek sonuç | Kanıt |
| --- | --- | --- |
| npm ci | Başlangıçta geçti; bağımlılık/lockfile değişmedi | [çıktı](validation-premium/logs/before-ci.txt) |
| npm run typecheck | Geçti | [çıktı](validation-premium/logs/after-typecheck.txt) |
| npm run build | Geçti, chunk boyutu uyarısı yok | [çıktı](validation-premium/logs/after-build.txt) |
| npm run test | **43/43**, önceki 38 + 5 sunum/erişilebilirlik testi | [çıktı](validation-premium/logs/after-unit.txt) |
| npm run test:e2e | **14/14**, gerçek MySQL/FastAPI/Chromium; 1,8 dakika | [çıktı](validation-premium/logs/after-e2e.txt), [işlem kanıtı](validation-premium/regression/acceptance.json) |
| npm run test:e2e:missing-models | **1/1**, gerçek 503 | [çıktı](validation-premium/logs/after-missing.txt) |
| Liste/form ekranlarında axe AA | 18 tarama, 0 ihlal | [JSON](validation-premium/regression/accessibility.json) |
| Dolu ayrıntı ekranları + mobil satış formunda axe | 15 tarama, 0 ihlal | [JSON](validation-premium/visual-checks.json) |
| Beş viewport × yedi dolu ekran | 35 kontrol, 0 yatay taşma, 0 adet 44×44 px altı görünür işlem hedefi, 0 pageerror | [çıktı](validation-premium/logs/after-visual.txt) |
| Tab / Shift+Tab / Escape / odağı geri verme | Menü, kesin onay ve sevkiyat drawer'ında geçti | Mevcut gerçek E2E senaryoları |
| Reduced motion | Tercih etkin, animasyonlu öğe 0 | [JSON](validation-premium/visual-checks.json) |
| Semantik renk kontrastı | 9 metin/yüzey çifti ≥4,5:1; ana metin 13,93:1, ikincil 5,78:1, ana buton 5,76:1 | [oranlar](validation-premium/contrast.json) |
| Aynı görsel fixture | 24 tablo / 315 satırın önce/sonra hash'leri aynı; Alembic head dc9109a1f001, ready=ok | [kanıt](validation-premium/fixture-verification.json) |
| Gizli bilgi / kapsam | Gerçek test anahtarı/parolaları değişikliklerde ve dist'te yok; yalnız frontend/ | [tarama](validation-premium/security.json) |

Tekrarlı geliştirme koşuları eski test veritabanında kayıt biriktirdi; bir axe koşusu 120 saniyelik süreyi aştı. Mevcut veriler silinmeden yeni `avatar_ux_acceptance_test` oluşturuldu, migration/demo adımlarıyla hazırlandı; nihai 14/14 koşusu burada tamamlandı. Görsel `avatar_ux_visual_test` hiç değiştirilmedi. Son koşularda başarısız/atlanan test yoktur. Backend pytest bu UI görevi için yeniden çalıştırılmadı; backend kodu değiştirilmedi. Son görsel mikro metin düzeltmesinden sonra typecheck/build/43 test ve 35 dolu ekran kontrolü tekrar geçti.

Ara koşularda mobil ikon bağlantısının erişilebilir adı, kapalı details içindeki düğmelerin Chromium'daki odak davranışı ve bir ikon import temizliği hatası bulundu/düzeltildi. Eski UUID/metin beklentileri yeni açılır sunuma uyarlandı; test senaryoları silinmedi veya atlanmadı. Son kontrollerin sonuçları yukarıdaki kayıtlarla gösterilir; ilk hatalı koşular başarı sayılmaz.

Otomatik axe, tam WCAG uygunluk sertifikası değildir. Fiziksel dokunma ergonomisi, ekran okuyucuyla baştan sona kullanım ve gerçek mobil klavye testi yapılmadı.

## 8. Gerçek ekran görüntüleri ve insan odaklı kabul

[Görüntü kökü](validation-premium/) · [önce manifest](validation-premium/before/manifest.json) · [sonra manifest](validation-premium/after/manifest.json) · [salt okunur yakalama betiği](validation-premium/capture.mjs).

Her `dashboard`, `cutting`, `sale`, `trace`, `recall`, `ai-production`, `ai-cutting` ekranının `before/` ve `after/` altında aynı isimli `-desktop.png` ve `-mobile.png` çifti vardır: 1440×900 ve 390×844. Ek `after/sale-form-mobile.png` yeni satış formunu gösterir. Bunlar gerçek Chromium görüntüleridir, mock/Figma değildir.

Veri: ayrı `avatar_ux_visual_test` veritabanı, mevcut backend demo komutları ve ML demo API'siyle oluşturuldu. Önce/sonra aynı UUID, kayıt, zaman ve miktarlara dayanır; bütün tablo parmak izleri karşılaştırılır. İşlem testleri farklı `avatar_ux_core_test` veritabanını kullanır. [Referans kayıtları](validation-premium/visual-reference.json) demo kimlikleri içerir, parola/anahtar içermez.

| Ekran | Masaüstü | Mobil |
| --- | --- | --- |
| Dashboard | [önce](validation-premium/before/dashboard-desktop.png) · [sonra](validation-premium/after/dashboard-desktop.png) | [önce](validation-premium/before/dashboard-mobile.png) · [sonra](validation-premium/after/dashboard-mobile.png) |
| Kesim | [önce](validation-premium/before/cutting-desktop.png) · [sonra](validation-premium/after/cutting-desktop.png) | [önce](validation-premium/before/cutting-mobile.png) · [sonra](validation-premium/after/cutting-mobile.png) |
| Satış | [önce](validation-premium/before/sale-desktop.png) · [sonra](validation-premium/after/sale-desktop.png) | [önce](validation-premium/before/sale-mobile.png) · [sonra](validation-premium/after/sale-mobile.png) |
| İzleme | [önce](validation-premium/before/trace-desktop.png) · [sonra](validation-premium/after/trace-desktop.png) | [önce](validation-premium/before/trace-mobile.png) · [sonra](validation-premium/after/trace-mobile.png) |
| Recall | [önce](validation-premium/before/recall-desktop.png) · [sonra](validation-premium/after/recall-desktop.png) | [önce](validation-premium/before/recall-mobile.png) · [sonra](validation-premium/after/recall-mobile.png) |
| Üretim AI | [önce](validation-premium/before/ai-production-desktop.png) · [sonra](validation-premium/after/ai-production-desktop.png) | [önce](validation-premium/before/ai-production-mobile.png) · [sonra](validation-premium/after/ai-production-mobile.png) |
| Kesim AI | [önce](validation-premium/before/ai-cutting-desktop.png) · [sonra](validation-premium/after/ai-cutting-desktop.png) | [önce](validation-premium/before/ai-cutting-mobile.png) · [sonra](validation-premium/after/ai-cutting-mobile.png) |

Son 15 görüntü tek tek görsel olarak incelendi. İlk görsel denemede lazy route'un yükleme durumunu erken yakalayan çekim betiği düzeltildi; son kanıtlar dolu kayıtların görünmesini bekler. Recall alıcı kartlarındaki tekrar eden iletişim/UUID alanları ikincil konuma alındı. AI kesim tablosundaki verim etiketi düzeltildi ve yeni görüntüler tekrar incelendi.

| Ekran | İlk bakışta amaç | Ana işlem | Bilgi sırası | Teknik detay | Renklerin görevi | Metin | Mobil değerlendirme |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dashboard | Kayıtlı işletme durumu | Dört açık işlem bağlantısı | KPI → varsa uyarı → işlemler → gerçek son kayıtlar | UUID yok | Teal eylem, rozetler gerçek durum | KPI birimleri/açıklamaları açık | İlk ekran KPI; iki kayıtlık listeler. Sayfa daha fazla gerçek modül içerdiğinden eski görüntüden uzundur. |
| Kesim | Ağırlık dengesi ve kesin maliyet | Taslakta tartım/kapanış, kesin kayıtta lot bağlantısı | 25=22+3 ve 287,50 EUR önce | Kesim referansı açılır, lot ayrıntısı kopyalanır | Adım durumu ve kesin kayıt | Referans değer satış fiyatından ayrıdır | Maliyet alanları yatay kaydırmadan okunur; kartlar sayfayı uzatır. Kapanış E2E masaüstünde, mobil ayrıntı/taşma kontrolü gerçek tarayıcıda. |
| Satış | Müşteri ve gerçek tutar / yeni lotlu satış | Gözden geçir → ayrı kesin onay | Müşteri → lot → miktar/fiyat → özet; tutar sunucudan | Satır/hareket kimlikleri isteğe bağlı | Teal işlem, yeşil kesin satış | Geçmişe dönüş ve onay açıklaması açık | Gerçek mobil satış tamamlandı; büyük alanlar ve etiketli kartlar. Fiziksel klavye ayrıca sınanmadı. |
| İzleme | Seçilen lotun gerçek ilişkileri | Lot/yön seçimi ve işlem/lot açma | Kaynak → işlem/FK çıkışı → konumlar → alıcı | Atıf ve FK referansları açılır | Blok kırmızı, ilişki akışı teal | Bağlam lotu ile kesin atalık ayrımı korunur | Dikey kaynak/çıktı zinciri; okunabilir kartlar, taşma yok. |
| Recall | Kaynak, aktif blok ve etki | Kapsamı inceleme; oluşturma ayrı onaylı | Kaynak/durum → kapsam → 85 paket, A/B/C 30/25/30 → zincir | İletişim/belge/referans ayrıntıda | Kırmızı kesin geri çağırma/blok | Market kalanı ve ikinci kademe “Bilinmiyor” | Bilinen marketler zincirden önce; her miktar açık. Kritik onay kaldırılmadı. |
| Üretim AI | Tahminin kesin kayıttan ayrı sonucu | Yeni tahmin açma; mevcut karşılaştırmayı okuma | Dört KPI → karşılaştırma → teknik | Model/UUID/tam değerler açılır | Amber sentetik kaynak | EKP/paket, kg ve yüzde açık | KPI ve karşılaştırma kartları okunur. AI oluşturma E2E masaüstünde; mobil sonuç ve responsive kontroller geçti. |
| Kesim AI | Beklenen kg, verim ve fark | Yeni tahmin / reçete eşlemesi | Üç KPI → parça dağılımı/gerçekleşme → teknik | Ham hassasiyet saklanmaz, açılır | Amber kaynak; kesin sonuç gibi yeşil sunulmaz | “Kesim verimi”, mutlak fark “puan” | Bütün parçalar görünür; uzun karşılaştırma aşağı kaydırılır, yatay taşma yok. |



Mobil tam sayfa yüksekliği aynı 390 px genişlikte: üretim AI 4035→2093 px, kesim AI 3829→2930 px; dashboard 2309→2932 px, kesim 2098→3302 px. Uzayan kart ekranları gizli sütunları görünür yapar; daha kısa oldukları iddia edilmez.

## 9. Performans karşılaştırması

[Önce build](validation-premium/logs/before-build.txt) · [sonra build](validation-premium/logs/after-build.txt) · [manifest hesabı](validation-premium/performance.json).

| Ölçüm | Önce | Sonra |
| --- | --- | --- |
| En büyük JS / entry | 543,15 kB | 280,01 kB |
| Entry + statik bağımlılıklar | Tek JS, 543,15 kB | 316,50 kB |
| Dashboard + shell + bütün statik bağımlılıkları | 543,15 kB | **332,49 kB** |
| Dashboard ilk JS, gzip (seviye 6 / dosya) | 162,63 kB | 107,70 kB |
| Tüm rotaların JS toplamı | 543,15 kB | 559,20 kB |
| CSS / gzip | 36,36 / 9,20 kB | 36,70 / 8,13 kB |

İlk dashboard JS yükü yaklaşık %38,8 azaldı. Code splitting toplam kodu ortadan kaldırmaz; bütün rotaların toplamı küçük parça maliyetleri nedeniyle arttı. Form/doğrulama kodu ilk dashboard bağımlılık kapanışında yoktur. Build manifest'i üretildi; HTML/manifest yardımcı dosyaları JS toplamına eklenmez.

Vite chunk uyarı eşiği değiştirilmedi. Üretim build'i doğrulandı; geliştirme proxy'sinin dışında dağıtılmış bir production sunucusu veya Lighthouse/Core Web Vitals ölçümü bu görevde yapılmadı. Route toplamları manifest'in statik import kapanışından çıkarılır; ağ gecikmesi ölçümü değildir.

## 10. Kullanılmayan / ertelenen fikirler

Dark tema, ağır grafik/animasyon kütüphanesi, gerçek zaman serisi olmayan grafik, örnek operasyon ekleme ve mobil native uygulama değişikliği eklenmedi. Mobil kartların çok uzun veri kümeleri için sanallaştırılması ve sunucu araması mevcut API kapsamının dışında kaldı. Yeni özellik, backend hesaplaması veya API değişikliği yapılmadı.

## 11. API ve iş kuralı regresyon kanıtları

[Değişmeyen sözleşme/komut hash'leri](validation-premium/scope.json): API istemcisi, tipler, payload üreticileri, validasyon ve pending/idempotency dosyaları değişmedi. `forms.tsx` yalnız dialog import yolunu değiştirir; gönderim/yeniden deneme mantığı aynıdır. Vite config farkı yalnız build manifest'idir; güvenli proxy/origin/host/gizli dosya engeli aynıdır.

Gerçek E2E; 1.543,50 EUR / 85 paket → 18,16 EUR EKP, iki ayrı 25 kg kesimde 287,50 EUR, açıklamasız farkın reddi ve gerçek 422, yan ürün/kayıp, lotlu satış → bağlı sevkiyat → bağımsız sevkiyat 10→9→9→7, 409 bloke lotta değişmeyen stok, süresi geçmiş lot, kayıp cevap/aynı idempotency key ve gövdeyle tek satış, ET→URT→SUC zinciri ve A/B/C 30/25/30, gerçek ML tahmin/gerçekleşme karşılaştırmalarını korur.

Backend, database, Android, ML, ortak tests, docs ve PROJECT_CHECKLIST dosyaları değişmedi. X-API-Key yalnız Node proxy'sinde kalır; DOM/storage/bundle sızıntısı gerçek değerle tarayıcı dışından karşılaştırılır. Anahtar test için bile page.evaluate argümanına aktarılmaz. Testler yalnız izole `*_test` veritabanlarında çalışır; bu görevde gerçek işletme verisi silinmez.

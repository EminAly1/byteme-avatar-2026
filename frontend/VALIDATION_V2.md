# Frontend v2 — gerçek entegrasyon ve görsel kabul

**Kanıt tarihi:** 25 Ekim 2026. **Başlangıç main:** `99356d4` (PR #14). **Branch:** `feature/frontend-v2-integration`. Yalnız frontend/ değişti. AGENTS.md, PDF'nin üç sayfası, checklist, FRONTEND_VISION, satış/sevkiyat, trace/recall, cutting ve ML sözleşmeleri incelendi; çalışan `/openapi.json` ile request tipleri yenilendi.

PR #1–#14 için normal merge commit'leri uzak main geçmişinde doğrulandı. GitHub API durum sorgusu 403 Forbidden verdi; [Git geçmişi kanıtı](validation-v2/pr-history.json). Bu çalışma main'e birleştirilmedi; push/PR sonucu teslim raporundadır.

## Ortam ve komut sonuçları

Node 24.19.0, npm 11.9.0; sistem Chromium **154.0.8037.57**, headless Linux. Gerçek MySQL **8.0.46**, ayrı `avatar_frontend_v2_test`; mevcut backend Alembic head `dc9109a1f001`. FastAPI 127.0.0.1:8000, Vite yalnız 127.0.0.1:5173. Model eksikliği için aynı izole DB ile **ayrı FastAPI 8002** ve olmayan model dizini kullanıldı. İşletme/paylaşılan demo DB'si kullanılmadı; bütün girişler kurgusal test/demo verisidir. Testler kayıt silmedi; satış/recall gibi kalıcı etkiler yalnız bu izole şemadadır.

| Kontrol | Gerçek sonuç | Kanıt |
| --- | --- | --- |
| Değişiklik öncesi typecheck/build/npm ci | Geçti; npm cache /tmp altına alındı | Başlangıç ortam doğrulaması |
| Önceki unit/component paketi | **25 geçti** | [baseline-unit](validation-v2/reports/baseline-unit.txt) |
| Önceki Chromium paketi | **4 geçti** | [baseline-e2e](validation-v2/reports/baseline-e2e.txt) |
| Son `npm ci` | **140 paket**, başarı | [ci](validation-v2/reports/npm-ci.txt) |
| Son `npm run typecheck` | Başarı | [typecheck](validation-v2/reports/typecheck.txt) |
| Son `npm run build` | Başarı | [build](validation-v2/reports/build.txt) |
| Son `npm run test` | **38 geçti** = eski 25 + yeni 13 | [unit](validation-v2/reports/unit.txt) |
| `npm run test:e2e` | **14 geçti** = dört eski senaryo + on yeni kabul testi | [Chromium](validation-v2/reports/chromium.txt) |
| `npm run test:e2e:missing-models` | **1 geçti**, gerçek backend 503, response mock yok | [missing-models](validation-v2/reports/missing-models.txt) |
| Son mobil hedef boyutu düzenlemesi sonrası | Responsive + axe **2 tekrar geçti**, eski mobil senaryo **1 tekrar geçti** | [responsive](validation-v2/reports/responsive.txt), [legacy-mobile](validation-v2/reports/legacy-mobile.txt) |

Klavye sınırları için mevcut iki senaryo ayrıca tekrar koşuldu ve geçti: [Tab/Shift+Tab, Escape ve odak dönüşü](validation-v2/reports/keyboard.txt).

**15 farklı son Chromium testi** (14 normal + 1 eksik-model); ek tekrarlar yeni test olarak sayılmadı. Son kabul koşularında başarısız/skip yok. İlk dört eski senaryo korunur: çok satırlı alış–dış üretim, mevcut PDF demosu, tablet/mobil, proxy güvenliği. V1'in artık yanlış olan “recall geliştirilmedi” beklentisi, gerçek modüle erişim ve kaynak/onay olmadan recall başlatılmaması beklentisine güncellendi; test silinmedi veya skip edilmedi.

Build, JS chunk'ının yaklaşık **543 kB minified / 162 kB gzip** olması nedeniyle Vite 500 kB uyarısı verir; hata değildir. Route code splitting sonraki performans işidir; eşik yükseltilip uyarı gizlenmedi. npm/Playwright'ın renk ortamı ve sürüm bildirimi test başarısızlığı değildir.

## Gerçek iş kabul senaryoları

| Senaryo | Gerçekten çalıştırılan kapsam |
| --- | --- |
| Eski dış üretim | Chromium UI'den firma/depo/ürün, üç satırlı alış, sevk, fiilî kapanış; 85 paket, 1.543,50 EUR, 18,16 gösterim EKP ve kesin lot bağlantıları |
| Reçete ve iki kesim | Kart/alış fixture'ı gerçek API'de; **reçete ve quantity/value sürümleri, taslak, tartım ve kapanış UI'de**. İki ayrı 25 kg kaynak lot, her biri 22 kg + açıklanmış 3 kg. Toplam maliyet her biri 287,50 EUR; dağıtımlar farklı |
| Kütle dengesi/422 | Fark eksikse ve açıklama boşsa istemcide onay açılmıyor. Ayrıca kontrollü request fault injection ile gerçek backend MASS_BALANCE 422 üretildi; stok 25 kg kaldı. Düzeltilmiş UI isteği sonra başarıyla kapandı |
| Yan ürün/diğer kayıp | Altı çıktılı reçete fixture'ı API'de; tartım/kapanış UI'de. 22 kg mamul + ayrı **2 kg yan ürün lot/stok** + açıklanmış **1 kg other_loss**. Açıklamasız yan ürün istemcide reddedildi |
| Reçete kullanılabilirliği | UI'den kapatma POST'u; kapalı rozeti ve eski kapanış maliyetinin 287,50 EUR kalması doğrulandı |
| Satış/sevkiyat | Gerçek 10 kg lot fixture'ından UI satışı 1 kg; UI bağlı sevkiyat **aynı StockMovement UUID**; UI bağımsız sevkiyat 2 kg. Merkezî stok **10→9→9→7** |
| Trace/recall | Canonical demo, mevcut backend komutuyla gerçek DB'ye yüklendi. UI ileri/geri FK raporu; kaynak ET → URT → SUC. Recall ön görünümünde POST yok; Escape iptali odak döndürür. Açık onayla gerçek recall UUID/üyelik/blok oluşur |
| Market raporu | Gerçek API raporunda Market A/B/C 30/25/30; **backend toplamı 85 paket**. İletişimler kurgusal demo snapshot'larıdır. Market kalanı, son tüketici ve ikinci kademe dağıtım **Bilinmiyor** |
| Blok/SKT | Blokeli ve SKT'si geçmiş pozitif bakiye seçenekleri kapalı. Seçimden sonra ayrı API recall'ıyla oluşturulan eski-cache yarışında UI POST'u gerçek LOT_BLOCKED 409 aldı; 10 kg stok değişmedi. Backend expired yarışının ayrı UI vakası çalıştırılmadı |
| Belirsiz ağ sonucu | Proxy üzerinden gerçek POST 201 commit edildi, response bilerek kaybettirildi. Sayfa yenilendi; sessionStorage'daki donmuş gövde + **aynı UUID** retry edildi; aynı satış UUID, stok yalnız bir kez 10→9 |
| Üretim AI | UI formu ve ön tahmin POST/GET'i; işlem kapanmadan gerçekleşme null. Mevcut gerçek API ile fixture operasyonu kapatıldı, UI yenilemesinde 85 paket ve backend Decimal sapma okundu |
| Kesim AI | UI'de gerçek reçete/beş ürün UUID eşlemesi ve tahmin POST/GET'i. Gerçek API ile fixture kesimi kapatıldı; UI'de 22 kg, parça gerçekleri ve sapma okundu. Model sürümü/zaman/UUID görünür |
| Eksik model | Var olmayan model dizinli ikinci backend gerçekten 503 döndürdü. Form/tahmin/metrik uydurulmadı; anlaşılır hata gösterildi. Bu profil response interception kullanmaz |

Ağ ve 422 vakalarındaki interception **gerçek backend işlemine kontrollü hata uygulamak** içindir; başarılı API cevapları fixture JSON ile taklit edilmedi. Unit/component testlerinde fetch mock kullanılır ve gerçek API kanıtından ayrı tutulur. AI gerçekleşme kapanışları fixture yardımcılarıyla gerçek API üzerinden yapıldı; UI kapanışı ayrıca dış üretim ve kesim testlerinde doğrulandı. [Senaryo UUID kanıtları](validation-v2/acceptance.json).

## API kapsaması

- Mevcut ürün/parti/konum/alış/lot/stok/hareket/operasyon listeleri ve yazmaları korunur; dış üretim listesi kesim türünü yanlışlıkla göstermez, dashboard doğru detay modülüne açar.
- Reçete list/create/get/availability; cutting list/create/get/post.
- Sales list/create/get; shipments list/create/get; bağlı ve bağımsız gövdeler ayrıdır.
- Lots/{id}/trace forward/backward; recalls POST ve GET/{id}.
- Predictions/models GET; production/cutting POST; predictions/{id} GET.

Backend'de recall/prediction **liste endpoint'i yoktur**. UI yalnız bu sekmede alınan gerçek UUID/zaman referanslarını tutar, bilinen UUID ile kayıt açar. Global tarihçe uydurulmadı. Reçetede parça→ürün seçimi açık kullanıcı konfigürasyonudur; lot bağları isim benzerliğinden türetilmez.

## Responsive, erişilebilirlik ve görüntüler

**360×800, 390×844, 768×1024, 1024×768, 1440×900** boyutlarında yedi ana route'un sayfa taşması kontrol edildi; 390 genişlikte gerçek lotlu satış onaylandı. Eski 834×1112 tablet testi de korunur. Mobil menü odak sınırı/Escape/odak dönüşü, native onay dialog'u ve drawer davranışı test edildi. Görünen mobil aksiyon hedefleri en az 44 px olarak ölçüldü: [ölçüm](validation-v2/mobile-targets.json). Geniş tablolarda kontrollü yatay kaydırma, açıklayıcı ipucu ve klavyeyle odaklanabilir region bulunur; form ve sayfa gövdesi yatay taşmaz. Reduced-motion CSS desteği vardır.

Axe-core WCAG 2 A/AA + 2.1 AA denetimi **dokuz sayfa × desktop/mobil = 18 görünümde 0 ihlal** verdi: [sonuç](validation-v2/accessibility.json). Bulunan yardımcı metin/eyebrow kontrastları düzeltildi. Bu sonuç tüm WCAG uygunluğu veya ekran okuyucu sertifikasyonu değildir; fiziksel tablet/telefon, Safari ve Firefox test edilmedi.

Bütün PNG'ler gerçek Chromium render'ından, `fullPage:true` ile alındı; görüntü yüksekliği viewport'tan büyük olabilir. Görsel düzenleme/mock/Figma kullanılmadı. Son kaynak üzerinde salt-okuma Chromium çekimiyle zorunlu ekranlar yenilendi. Baseline, main kaynaklarının geçici export'uyla aynı izole DB'de çalıştırıldı; test kayıtları arttığı için before/after sayaçlarının eşit olması beklenmez.

| Ekran | Gerçek PNG |
| --- | --- |
| Önceki dashboard | [baseline-dashboard-desktop.png](validation-v2/screenshots/baseline-dashboard-desktop.png) |
| Dashboard desktop / mobil | [desktop](validation-v2/screenshots/dashboard-desktop.png), [mobil](validation-v2/screenshots/dashboard-mobile.png) |
| Kuzu parçalama desktop / tablet / mobil | [desktop](validation-v2/screenshots/cutting-desktop.png), [tablet](validation-v2/screenshots/cutting-tablet.png), [mobil](validation-v2/screenshots/cutting-mobile.png) |
| Lot izleme desktop | [trace-desktop.png](validation-v2/screenshots/trace-desktop.png) |
| Kesin recall sonucu | [recall-desktop.png](validation-v2/screenshots/recall-desktop.png) |
| AI üretim / kesim desktop | [üretim](validation-v2/screenshots/ai-production-desktop.png), [kesim](validation-v2/screenshots/ai-cutting-desktop.png) |
| AI mobil | [ai-mobile.png](validation-v2/screenshots/ai-mobile.png) |
| Lotlu satış mobil | [sale-mobile.png](validation-v2/screenshots/sale-mobile.png) |
| Gerçek model 503 | [model-unavailable-desktop.png](validation-v2/screenshots/model-unavailable-desktop.png) |

[PNG ölçü/hash manifesti](validation-v2/screenshots.json). FullPage screenshot'ında odaklanmamış skip-link'in çizilmesini önlemek için standart visually-hidden/focus-visible stili kullanıldı; klavye erişimi korunur.

## Güvenlik ve sınırlar

Mevcut loopback proxy/auth/CORS değişmezleri korundu. Browser ağ istekleri X-API-Key taşımaz; Host/Origin/originsiz POST/gizli dosya engelleri eski gerçek browser testinde geçer. VITE_* veya browser storage'a secret konmadı. Sızıntı karşılaştırması Node test process'inde yapılır: browser'dan yalnız metin/storage içeriği geri alınır. İlk test yardımcı sürümünün secret'ı page.evaluate argümanına geçirmesi kaldırıldı; son kabul koşusu güvenli sürümledir. Bu yalnız izole test anahtarıydı; uygulama proxy sözleşmesi değiştirilmedi. Son kaynak/build/evidence dosyaları gerçek test parolaları/API anahtarı için tarandı.

Kesin para, stok, lot ve recall kararları backend'dedir. Frontend tahmini kesin maliyet olarak kaydetmez. Sentetik model uyarısı iki form/sonuçta görünür; MAE/RMSE birimleri belirtilir, yüzde doğruluk iddiası yoktur. Gerçekleşme yoksa sayı üretilmez; yüzde sapma tanımsızsa çizgi gösterilir.

Eksik kalanlar: üretim kullanıcı oturumu/rol/TLS/dağıtım, fiziksel cihaz/diğer tarayıcı kabulü, büyük veri için sunucu filtre/toplam ve kademeli liste, route splitting performans işi. Bu görevde tam Docker Compose image/stack, backend pytest, Android ve ML eğitim test paketleri tekrar çalıştırılmadı; kaynakları değişmedi. Gerçek üretim verisi kullanılmadı. İki AI modeli gerçek işletme doğruluğu açısından hâlâ doğrulanmış değildir.

İlk denemelerde npm'in salt-okunur home cache yolu ve MySQL hazır olmama hataları giderildi. UI/test iterasyonlarında nested-select label eşlemesi, mobil menü odağı, native dialog'un Tab sınırında tarayıcı çubuğuna geçişi, kontrast ve geniş listelerde eşzamanlı detay istekleri düzeltildi. Native modal semantiği korunarak dialog/drawer içinde Tab/Shift+Tab döngüsü açıkça denetlendi. Detaylar 4'lü gruplarla okunur; test beklemesi gerçek ağ süresini kapsar. Başarısız ilk denemeler son başarı sayısına katılmadı.

## Ortak checklist için devir

`docs/PROJECT_CHECKLIST.md` değiştirilmedi. Aşağıdakiler bu branch'teki test edilen prototip kapsamıdır; main birleşimi veya yarışma tesliminin bittiği anlamına gelmez.

| ID | Önerilen durum / kanıt |
| --- | --- |
| WEB-01 | Tamamlandı: gerçek dashboard/katalog/parti/depo API ve eski regresyon |
| WEB-02 | Tamamlandı: alış–stok–dış üretim, 1.543,50/18,16 EUR ve kesin ilişkiler gerçek UI testi |
| WEB-03 | Tamamlandı: Decimal string, cursor, dialog, gerçek commit sonrası kayıp cevap ve aynı anahtarlı retry |
| WEB-04 | Tamamlandı: beş viewport, klavye, 18 görünüm axe denetimi ve korunmuş proxy testleri; Chromium kapsamı |
| WEB-05 | Tamamlandı: temel parçalama/satış/sevkiyat/trace/recall/iki AI ekranları ve yukarıdaki gerçek API kanıtı |
| WEB-06 | Doğrulama gerekiyor: üretim oturumu/rol/dağıtım uygulanmadı; mevcut local proxy üretim auth'u sayılmaz |
| ML-05 | Tamamlandı: iki modelin gerçek tahmin UUID/zaman/sürümü ve kapanış sonrası gerçek/sapma web karşılaştırması; sentetik prototip |

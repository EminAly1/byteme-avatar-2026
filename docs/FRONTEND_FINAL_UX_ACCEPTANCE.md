# Görev 23 — Web UI/UX kabul kanıtı

Başlangıç: `origin/main` `f5b46fe` (Görev 22, PR #38 birleşmiş). Çalışma branch’i: `feature/frontend-final-ux-v3`. Referans: [Issue #39](https://github.com/EminAly1/byteme-avatar-2026/issues/39). Kapsam: frontend ve bu kabul belgesi; iş defteri, backend, Android, model eğitimi ve PROJECT_CHECKLIST değiştirilmedi.

## Ön denetim

Değişikliklerden önce gerçek Chromium’da 29 rota × 390/768/1440 px = **87 ekran** yakalandı ve sekiz görsel inceleme panosunda incelendi. Tam çözünürlüklü özgün görüntüler ayrıca saklandı. Parçalama fixture’ındaki ilk yanlış UUID eşlemesi düzeltilip üç görüntü yeniden çekildi; reddedilen görüntüler uygulama hatası sayılmadı.

- [x] **P1:** Satış ayrıntısında iç içe fragment’lerden düzleştirilen tablo hücreleri React anahtar çakışması üretiyordu. Üst anahtar yolu korunarak düzeltildi; regresyon testi eklendi.
- [x] **P1:** Belge düzenleme formu ve salt okunur belge aynı uzun sayfadaydı. Görüntüleme ve `/duzenle` ekranları ayrıldı.
- [x] **P1:** Kapalı mobil yan menü klavye sırasından çıkmıyordu. `inert`, görünür odak sırası ve mobil kapanış davranışı eklendi.
- [x] **P2:** Düz menü iş akışını anlatmıyordu. Yedi grup ve sorgu parametresini dikkate alan aktif işlem işareti eklendi.
- [x] **P2:** Görünür marka ByteMe, favicon eksikti. AVATAR ve mevcut Android ikonunun vektör geometrisi kullanıldı.
- [x] **P2:** 768/1440 px ölçümlerinde 48 adet 44 px’den dar eylem görüldü. Ortak eylem ve sekmelerde minimum hedef boyutu düzenlendi.
- [x] **P2:** Bazı ana sayfalarda kısa iş açıklaması yoktu; firma, depo ve üretim formuna üstten erişim zayıftı. Rota açıklamaları ve mevcut formlara bağlantılar eklendi.
- [x] Başlangıçtaki 87 geçerli ekranda kök yatay taşma görülmedi. Bu bulgu 360/1024 px hakkında kanıt değildir; son test matrisi ayrıca çalıştırılır.

## Belge deneyimi ve veri sınırı

Liste müşteri, lot, durum ve backend’den gelen düzeltme sonrası tutarı gösterir. Sayfa başına en fazla 20 satış ve bunlara ait kaynak GET’leri alınır; müşteri/tutar üretmek için frontend hesabı yapılmaz. Her kartta Görüntüle, Taslak düzenle, PDF indir ve Önizle vardır. Kalıcı arşiv veya satış silme eylemi eklenmedi.

Eski `/belgeler/satis/:id` bağlantısı salt okunur görünümdür. `/duzenle` yalnız mevcut izinli taslak alanlarını değiştirir. “Değişiklikleri bu görünümde uygula” yalnız bellekteki görünümü günceller; sunucu kaydı izlenimi veren Kaydet yoktur. Belge ekranından ayrılınca geçici alanlar sıfırlanır. Kaynak müşteri, miktar, fiyat, lot ve maliyetler kilitli kalır. Tarih, uzunluk ve 21 satır sınırı doğrulanır.

Modal gerçek PDF endpoint’inden gelen `application/pdf` ve `%PDF-` doğrulanmış dosyayı işler. Yeni tek çalışma bağımlılığı `pdfjs-dist@6.4.299`: çok sayfalı mobil önizleme için, worker yerel build’den yüklenir; haricî görüntüleyici/CDN yoktur. PDF.js yalnız modal içeriği ihtiyaç duyduğunda yüklenir. Erişilebilir metin görünümü, yakınlaştırma, Escape, odak döngüsü ve geri dönüş, gövde kaydırma kilidi vardır. İndirme PDF’yi güncel fingerprint ile yeniden ister; yazdırma öncesi kaynak tekrar doğrulanır. Web Share yalnız cihaz dosya paylaşımını desteklediğinde gösterilir.

Proforma resmî e-Fatura değildir. Vergi, GİB numarası, tahsilat veya kalıcı arşiv uydurulmaz. Teknik UUID’ler belgede isteğe bağlı ayrıntıya taşındı; gerçek PDF’nin backend’deki kaynak referansları korunur.

## Marka ve tasarım devri

Görünür ürün adı AVATAR. `frontend/public/avatar-icon.svg`, Android `ic_avatar_foreground.xml` içindeki 48×48 koordinatlarını ve `launcher_bg` #006C57 rengini aynen taşır. Sidebar, favicon ve bekleme göstergesi aynı dosyayı kullanır. Android dosyaları ve ekip adı olan ByteMe’nin yarışma belgeleri değişmedi.

Android Görev 24 için: marka rengi #006C57, koyu metin #192F39, ikincil metin #536973; 8/12/16 px köşeler, 8/12/16/24 px aralıklar; web’de en az 44×44 CSS px eylem alanı (Android’de 48 dp dokunma hedeflerine uyarlanmalı); açıklamalı alanlar, belirgin odak, hata/başarı/boş durumları. Web para hesabı yapmaz; API ondalık metnini gösterir. İkon yükleme animasyonu azaltılmış hareket tercihinde kapanır, sabit bekleme süresi yoktur.

## Son doğrulama — 29 Ekim 2026

Node 24.19, Python 3.12, MySQL 8 ve gerçek sistem Chromium’u kullanıldı. İşletme verisi kullanılmadı; `avatar_task23_web_test`, `avatar_task23_documents_test`, `avatar_task23_alerts_test`, `avatar_task23_empty_test` ayrı şemalardır. Dört şemaya mevcut Alembic head uygulandı. API `/health/ready` gerçek MySQL ile kontrol edildi. Şema veya backend kodu değiştirilmedi.

| Kontrol | Sonuç / kanıt |
| --- | --- |
| Temiz `npm ci` | 144 paket kuruldu; güncel lockfile kullanıldı |
| `npm run typecheck` | Başarılı; son test yardımcı değişikliği sonrasında tekrar başarılı |
| `npm run build` | Başarılı; yerel PDF worker üretildi, PDF motoru ayrı lazy chunk |
| `npm test -- --maxWorkers=2` | **103/103**, 12 test dosyası; mevcut 102 test korundu, fragment anahtar regresyonu eklendi |
| Eski gerçek iş akışı tarayıcı grubu | **32 farklı senaryonun tamamı doğrulandı**: son toplu koşu 31/32, soğuk AI formu yükleme zaman aşımı sonrasında aynı test tek başına 1/1 geçti. Tek toplu 32/32 sonucu iddia edilmiyor |
| Belge Chromium grubu | **3/3**; gerçek indirme, Türkçe metin, MIME/no-store, A4 ölçüleri, modal üzerinden yazdırma, 45 satır/8 sayfa, iade/iptal ve gerçek 401/404 |
| Uyarı Chromium grubu | **4/4**; altı gerçek uyarı, filtreler, kaynak bağlantıları, salt GET, 390/768/1440 axe |
| Eksik model Chromium grubu | **1/1**; gerçek backend 503, görünür hata, sahte sonuç/metrik yok |
| Yeni UI Chromium grubu | **7/7**; 31 rota × beş genişlik; bütün menü bağlantıları, odak döngüsü, scroll kilidi, taslak doğrulama ve gerçek çok sayfalı PDF |
| Boş veri ilk kullanım | **20 ana rota**, 390 px, gerçek boş MySQL şeması; hata/taşma/yazma yok. Beş eski `/plan/*` yönlendirmesi ve 404’ten genel bakışa dönüş doğrulandı |
| Otomatik erişilebilirlik | Yeni matriste **62 rota taraması** (31 × 390/1440), sıfır WCAG 2 A/AA ve 2.1 AA axe ihlali; ek modal ve eski regresyon taramaları da geçti |
| Gerçek klavye | Menü ilk/son odak döngüsü, Escape ve tetikleyiciye dönüş; modal kapat/Tab/Shift+Tab/Escape ve odak iadesi; eski drawer/form/recall kontrolleri geçti |
| ESLint | Repoda lint script’i veya ESLint yapılandırması yok; çalıştırılmış gibi gösterilmedi |
| Gizli bilgi denetimi | Frontend kaynaklarında Gitleaks: bulgu yok; son commit ayrıca taranır. Ortam dosyaları yalnız repo dışındaki 0600 özel dosyalarda |

Toplam **47 farklı Chromium senaryosunun her biri başarılı bir koşuda doğrulandı** (32 eski iş akışı + 3 belge + 4 uyarı + 1 eksik model + 7 yeni UI). İlk başarısız koşular aşağıda ayrı raporlanır; tek toplu koşuda 47/47 iddiası yok.

Yeni rota matrisi her genişlikte başlık, açıklama, yüklemenin bitmesi, alert, console error, uncaught exception, kök yatay taşma ve görünür buton/eylem/sekme boyutlarını kontrol eder. Canvas üzerinde gerçek PDF sayfaları render edilir; sadece HTML taslağı PDF gibi gösterilmez. A4 HTML metin görünümü ayrıca erişilebilir alternatif olarak sunulur. Otomatik axe taraması tam WCAG uygunluk sertifikası değildir.

| Genişlik | Rota | Konsol / exception | Kök taşma | 44 px altı ölçülen eylem | Axe |
| --- | ---: | ---: | ---: | ---: | --- |
| 360 | 31 | 0 | 0 | 0 | Bu genişlikte çalıştırılmadı |
| 390 | 31 | 0 | 0 | 0 | 31 tarama, 0 ihlal |
| 768 | 31 | 0 | 0 | 0 | Eski operasyon/uyarı taramaları da geçti |
| 1024 | 31 | 0 | 0 | 0 | Bu genişlikte çalıştırılmadı |
| 1440 | 31 | 0 | 0 | 0 | 31 tarama, 0 ihlal |

### Rota envanteri

Detay UUID’leri sentetik seed çıktılarından alınır; repoda sabit işletme UUID’si kodlanmaz. `final-ux.spec.ts` tüm bu rotaları beş genişlikte dolaşır. Satış ayrıntısı kârlılık sekmesini de içerir; kârlılık için uydurma yeni API/rota eklenmedi.

| # | Test edilen rota |
| ---: | --- |
| 1 | `/` |
| 2 | `/urunler` |
| 3 | `/is-ortaklari` |
| 4 | `/depolar` |
| 5 | `/alislar` |
| 6 | `/stoklar` |
| 7 | `/hareketler` |
| 8 | `/uretim` |
| 9 | `/parcalama` |
| 10 | `/hareketler?islem=rework` |
| 11 | `/satislar` |
| 12 | `/sevkiyatlar` |
| 13 | `/dagitimlar` |
| 14 | `/hareketler?islem=iade` |
| 15 | `/hareketler?islem=iptal` |
| 16 | `/izlenebilirlik` |
| 17 | `/geri-cagirma` |
| 18 | `/uyarilar` |
| 19 | `/yapay-zeka` |
| 20 | `/belgeler` |
| 21 | `/uretim/:id` |
| 22 | `/parcalama/:id` |
| 23 | `/satislar/:id` |
| 24 | `/dagitimlar/:id` |
| 25 | `/hareketler/rework/:id` |
| 26 | `/geri-cagirma/:id` |
| 27 | `/izlenebilirlik?lot=:id` |
| 28 | `/yapay-zeka?prediction=:id` |
| 29 | `/belgeler/satis/:id` |
| 30 | `/belgeler/satis/:id/duzenle` |
| 31 | `/belgeler/satis/:id` |

### Başlangıç hataları ve yeniden doğrulama

- Satış ayrıntısı, 768/1440: React “same key .0/.1” hatası. `Table.flatten` fragment üst anahtarlarını korur; yeni birim testi ve tüm rota matrisi hatanın kaybolduğunu doğruladı.
- Kapalı mobil menü: görünmez linkler klavye sırasındaydı. `inert` ve yalnız görünür odak adaylarıyla düzeltildi; bütün menü bağlantıları gerçek tıklamayla doğrulandı.
- İlk PDF modal denemesinde önizleme düğmesi hazırlanma sırasında disabled olunca odak kayboluyordu. Açan öğe istekten önce yakalanır; kapanışta odak geri verilir. Gerçek Chromium testi geçti.
- Son görsel incelemede mobil sayfa başlığı eylemler nedeniyle daralıyordu; başlık ve eylem satırları ayrıldı. Desktop modal Tailwind reset’i nedeniyle köşeye yaslanıyordu; merkezleme açık `margin:auto` ile düzeltildi. 768/1440 gerçek dialog sınırları ve 390 tam ekran davranışı test edildi.
- İlk eski entegrasyon koşusunda iptal yanıt kaybı senaryosu beş saniyelik beklemede kaldı. Aynı test tek başına geçti; son toplu koşuda da geçti. Son toplu koşudaki AI formu ilk yükleme beklemesi beş saniyeyi aştı; aynı değişmemiş test tek başına 1/1 geçti. Hiçbir assertion silinmedi, timeout artırılarak geçiş zorlanmadı, test atlanmadı.
- Belge testinin ilk root-dizin koşusu PDF ayrıştırıcı Python yolunu yanlış çözdü (ENOENT). Yardımcı yol test dosyasının URL’sine bağlandı; cwd’den bağımsız düzeltmeyle **3/3** yeniden geçti. Ürün PDF servisi bu koşuda da gerçek PDF döndürmüştü.
- İlk core seed hazırlığı API hazır olmadan başladı ve bağlantı reddedildi; API hazır olduktan sonra tekrar başarılı oldu. Veri sıfırlanmadı. İlk grep ile test seçimi eski uyarı seed yolunu bulamadı; gruplar açık dosya ve seed parametreleriyle çalıştırıldı.

### Defter değişmezliği

Belge ve uyarı browser grupları sırasında gerçek MySQL’de **30 tablonun** tamamı öncesi/sonrası karşılaştırıldı. İkisi de aynı hash ile bitti:

- Belgeler: `85197f8d2d31f5aafc07bf66d9ed5f20c316452ce657c14782d93648feba447f`
- Uyarılar: `3f9d62cbf0cb6a97cb4313cae75ec0551d1655ed927fbc7378389e1f2eabe9a4`

Üretim/satış/recall/idempotency testlerinin yazmaları yalnız `web_test` şemasındadır; salt okunur belge ve uyarı grupları ayrı şemalarda çalıştırıldı. Gerçek iş akışında 1.543,50 EUR / gösterilen 18,16 EUR EKP, lot zinciri, negatif stok reddi, rework maliyeti ve kayıp yanıtla aynı key/body tekrarları mevcut backend ile doğrulandı. Backend pytest bu frontend görevinde yeniden çalıştırılmadı; bu satır backend birim test sonucu iddia etmez.

### Görsel kanıt

Git’te seçilmiş gerçek görüntüler:

- Önceki birleşik belge: [390](evidence/frontend-final-ux-v3/before-document-390.png), [768](evidence/frontend-final-ux-v3/before-document-768.png), [1440](evidence/frontend-final-ux-v3/before-document-1440.png).
- Yeni liste: [390](evidence/frontend-final-ux-v3/document-list-390.png), [768](evidence/frontend-final-ux-v3/document-list-768.png), [1440](evidence/frontend-final-ux-v3/document-list-1440.png).
- Salt okunur ve düzenleme: [Görüntüle 390](evidence/frontend-final-ux-v3/document-view-390.png), [Taslak düzenle 390](evidence/frontend-final-ux-v3/document-edit-390.png).
- Gerçek PDF modalı: [390](evidence/frontend-final-ux-v3/pdf-modal-390.png), [768](evidence/frontend-final-ux-v3/pdf-modal-768.png), [1440](evidence/frontend-final-ux-v3/pdf-modal-1440.png).
- [Sekiz sayfalı PDF modalı, 390 px](evidence/frontend-final-ux-v3/pdf-long-390.png).
- Menü: [390](evidence/frontend-final-ux-v3/navigation-390.png), [768](evidence/frontend-final-ux-v3/navigation-768.png), [1440](evidence/frontend-final-ux-v3/navigation-1440.png).
- [155 ekranın makine okunur rota denetimi](evidence/frontend-final-ux-v3/route-audit.json), [PDF/defter/test özeti](evidence/frontend-final-ux-v3/summary.json).

87 geçerli önceki ekran ve 155 son rota ekranı özgün tam çözünürlükte, ayrıca sekizer inceleme panosunda korundu. Panolar yerleşim karşılaştırması içindir; yoğun veri listelerinde küçük görüntülerin yerine özgün PNG’ler kullanılmalıdır. Tam paket çalışma ortamında `/workspace/artifacts/avatar-task23-ux-evidence.zip` olarak paylaşılır; ortam dosyaları/anahtarlar pakete alınmaz.

### Yeniden çalıştırma

README’deki MySQL/özel ortam kurulumu ve mevcut Alembic head gereklidir. Yalnız `*_test` veritabanları kullanın. `tools/release_env.py run --env-file <özel-dosya> -- <komut>` gizli değerleri process ortamına alır; browser’a anahtar konmaz. Frontend Vite proxy’si aynı test backend’ine gitmelidir. İlk seed işlemleri `tools/verify_release_demo.py`, `app.demo_rework`, `app.demo_second_tier`, `app.demo_documents --prepare` ve ayrı şemada `app.demo_alerts --prepare` mevcut araçlarıyla yapıldı. Yeni model eğitilmedi.

- Normal iş akışı grubu: Playwright `dashboard.spec.ts integration-v2.spec.ts operational-flows.spec.ts release-hardening.spec.ts ai-model-v2.spec.ts recall-safety.spec.ts accessibility-v2.spec.ts`.
- Yeni matris: `final-ux.spec.ts`; `AVATAR_FINAL_UX_SEED_DIR` altında `core-seed.json`, `documents-seed.json`, `rework.json`, `second-tier.json` gerekir. `AVATAR_E2E_ARTIFACT_DIR` görüntü/JSON dizinidir.
- Belgeler: ayrı belgeler şeması, `AVATAR_DOCUMENT_DEMO_SEED=<demo_documents çıktısı>` ile `documents.spec.ts`. `pypdf` kurulu backend Python’u kullanılır; farklı venv için `AVATAR_PDF_PYTHON` verilebilir.
- Uyarılar: ayrı şema, `AVATAR_ALERT_DEMO_SEED=<demo_alerts çıktısı>` ve seed’in `stock_thresholds` değeri backend’de `AVATAR_ALERT_STOCK_THRESHOLDS` olmalı; `alerts.spec.ts`.
- Eksik model: ayrı local API’de `AVATAR_ML_MODEL_DIR` boş dizin; `npm run test:e2e:missing-models` kendi 5173 Vite sürecini açtığı için önceden bu port boşaltılmalı.

`AVATAR_E2E_DATABASE` ve API anahtarı global setup tarafından zorunlu tutulur. CI’de browser gruplarını seri çalıştırmak, beş saniyelik eski ilk-yükleme kontrollerinde kaynak paylaşımı kaynaklı dalgalanmayı azaltır. Gitleaks ve `git diff --check` son teslimde yeniden kontrol edilir.

### Kalanlar / kabul sınırı

- **P0/P1:** Test edilen rota, veri boyutu ve Chromium akışlarında bilinen açık ürün hatası yok. Bu, tüm cihaz ve tüm veri boyutlarında hatasızlık iddiası değildir.
- **P2:** Çok sayıda master/stok kaydında dikey liste uzar. Mevcut filtreler, mobil kartlar ve forma üstten kısayollar korundu/iyileştirildi; tüm master modüllerine yeni sunucu sayfalama arayüzü eklenmedi. Belge listesi 20 ile sınırlıdır.
- **P2 — test altyapısı:** Paralel ağır Chromium/axe koşularında eski kısa ilk-yükleme beklemeleri zaman aşımı üretebilir; yukarıdaki ilk başarısızlıklar ve tekrarlar ayrı kaydedildi.
- **Doğrulama sınırı:** Gerçek Android/iOS cihazı, Safari/Firefox, işletim sistemi paylaşım paneli ve fiziksel yazıcı kullanılmadı. Headless Chromium yazdırma olayı, A4 PDF çıktısı ve Share capability kontrolü doğrulandı; gerçek mobil paylaşım tamamlandı denmiyor. Sekiz sayfadan çok daha büyük PDF için bellek/performans ölçümü yapılmadı.
- Docker üretim frontend imajı bu görevde yeniden kurulmadı; npm production build ve gerçek Vite→FastAPI→MySQL entegrasyonu test edildi. Önceki yerel Docker demosu verileri korunur ve görev sonunda önceki sürümüyle geri açılır. Public production onayı veya release kararı değiştirilmedi.
- Android, ML/model dosyaları, backend, veritabanı şeması, AGENTS ve PROJECT_CHECKLIST değişmedi. Main’e merge yapılmaz.

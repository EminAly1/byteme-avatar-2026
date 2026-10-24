# ByteMe AVATAR 2026 — Proje tamamlanma checklist’i

**Teslim:** 1 Kasım 2026, **23:59 Europe/Istanbul (UTC+3)**. Tarih/saat kullanıcı talimatıdır; PDF’de teslim tarihi yoktur.

**Gereksinim kaynağı:** [AVATAR_Assessment.pdf](AVATAR_Assessment.pdf), 3 sayfa. **Kanıt tarihi:** 24 Ekim 2026. [Güncel entegrasyon ve test raporu](INTEGRATION_VALIDATION_2026-10-24.md).

## Durumlar ve kapsam

- **Tamamlandı:** Belirtilen dar kapsam için çalışan kaynak ve test/işlevsel doğrulama var; bu, main birleşimi veya bütün yarışma tesliminin tamamlandığı anlamına gelmez.
- **Devam ediyor:** Modülün bir kısmı çalışıyor, bütün kabul senaryosu tamamlanmadı.
- **Başlanmadı:** Çalıştırılabilir akış yok; yalnız yönerge/tasarım bulunması uygulama sayılmaz.
- **Doğrulama gerekiyor:** Gerekli ortam, uçtan uca, insan veya GitHub doğrulaması eksik/engelli.

**GitHub birleşim güncellemesi (24 Ekim 2026):** [PR #1](https://github.com/EminAly1/byteme-avatar-2026/pull/1), [PR #2](https://github.com/EminAly1/byteme-avatar-2026/pull/2) ve [PR #3](https://github.com/EminAly1/byteme-avatar-2026/pull/3) sırasıyla **normal merge commit** ile `main` dalına birleştirildi. Son birleşim commit'i: `7837a85097e2fd50c8da672a03803c319296d344`. Aşağıdaki başarılı testler aynı kaynak ağacının izole yerel birleşim adayında koşulmuştur; son uzak `main` üzerinde yeniden test **henüz yapılmadı**.

## 1. Proje altyapısı

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| ALT-01 | Monorepo ve üç ajan için dosya sahipliği | Tamamlandı | [AGENTS.md](../AGENTS.md), [PR #1](https://github.com/EminAly1/byteme-avatar-2026/pull/1); mevcut kurulum/test yolları çalıştı. Android/ML klasörleri yalnız yönergedir. |
| ALT-02 | FastAPI health ve MySQL ready | Tamamlandı | [main.py](../backend/app/main.py), [health testleri](../tests/test_health.py); gerçek iki endpoint 200. |
| ALT-03 | Environment üzerinden MySQL 8, Alembic migration, FK/CHECK ve Decimal alanlar | Tamamlandı | [database.py](../backend/app/database.py), [migration](../backend/alembic/versions/eeea4b5dd1a8_create_production_and_stock_ledger_core.py), [migration testi](../tests/test_migrations_mysql.py); MySQL 8.0.46 üzerinde upgrade/check/downgrade/upgrade geçti. |
| ALT-04 | Yerel proxy sınırı ve gizli bilgileri Git/tarayıcı dışında tutma | Tamamlandı | [proxy](../frontend/server/proxy.ts), [browser testi](../frontend/tests/browser/dashboard.spec.ts); Host/Origin, dosya erişimi ve key sızıntısı kontrolleri geçti. Üretim auth’u değildir. |
| ALT-05 | Üç PR’ı normal merge commit ile sırayla main’e alma, hedefleri değiştirme | Tamamlandı | PR #1, #2 ve #3 GitHub üzerinde birleştirildi; `main` son birleşim commit'i `7837a850`. Son `main` testleri TST-06 kapsamında ayrıca doğrulanmalı. |
| ALT-06 | Tek komutla bütün servislerin çalıştığı Docker Compose | Doğrulama gerekiyor | [Compose](../docker-compose.yml) API anahtarını enjekte etmiyor; frontend hedefi `http://backend:8000`, loopback kuralıyla uyumsuz. Tam image build/stack bu görevde çalıştırılmadı. Doğrulanan yol: izole MySQL container + host FastAPI/Vite. |
| ALT-07 | Üretim kullanıcı oturumu, roller ve yetkilendirme | Başlanmadı | [API anahtarı kontrolü](../backend/app/api.py) yalnız güvenilir yerel istemciler içindir. |

## 2. Üretim ve EKP

PDF s.1, Görev 1.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| URT-01 | Hammadde/ürün kartı, birim, tedarikçi, alış fiyatı, lot ve stok | Tamamlandı | [API](../backend/app/api.py), [şemalar](../backend/app/schemas.py), [core testleri](../tests/test_core_mysql.py); browser’dan üç satırlı alış çalıştı. |
| URT-02 | Dış üretim emri ve mülkiyet değişmeden üreticiye hammadde sevki | Tamamlandı | [services.py](../backend/app/services.py) create_operation/dispatch; sevk tüketim maliyeti oluşturmaz, defter dengesi test edildi. |
| URT-03 | Fiilî tüketim/iade, hizmet faturası referansı, mamul kabulü ve açıklamalı miktar farkıyla atomik kapanış | Tamamlandı | [services.py](../backend/app/services.py), MySQL rollback/iade testleri, gerçek browser kapanışı. İade kapsamı üretim hammaddesidir. |
| URT-04 | 970 + 48 + 58 + 467,50 = 1.543,50 EUR; 85 paket için 18,16 EUR gösterim EKP | Tamamlandı | [costing testleri](../tests/test_costing.py), `test_full_required_cost_stock_and_exact_lot_links`; HTTP ve browser aynı sonucu verdi. |
| URT-05 | Decimal ve kısmi lot/çoklu çıktıda maliyet toplamının korunması | Tamamlandı | [costing.py](../backend/app/costing.py), partial_lot ve multiple_outputs MySQL testleri. Toplam gösterim EKP’sinden yeniden hesaplanmaz. |
| URT-06 | Stok transaction’ı, satır kilidi, negatif stok kontrolü, idempotency ve tarihçe | Tamamlandı | [commands.py](../backend/app/commands.py), gerçek MySQL stok yarışı/tek kapanış/lock bekleme/rollback testleri. |
| URT-07 | VKP, brüt kâr ve satış marjını backend’de hesaplayıp gösterme | Başlanmadı | Mevcut API üretim maliyetlerini döndürüyor; satış fiyatı/kâr/marj akışı yok. |
| URT-08 | Gerçek deadlock üreterek sınırlı retry’ı doğrulama | Doğrulama gerekiyor | Retry kodu var; gerçek kilit ve yarış test edildi, zorlanmış deadlock senaryosu çalıştırılmadı. |

## 3. Kuzu parçalama

PDF s.1, Görev 2. Tabloda `cutting` türünün bulunması çalışan parçalama akışı değildir.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| KUZ-01 | Hayvan/parti, tür, giriş ağırlığı, gerçek toplam alış maliyeti ve işlem tarihi | Başlanmadı | [Model planı](data-model.md); çalışan parçalama endpoint’i yok. |
| KUZ-02 | Önceden tanımlanabilen reçete ve sürümlü dağıtım anahtarı | Başlanmadı | Reçete/anahtar tabloları ve API’si gerekli. |
| KUZ-03 | But/sırt/omuz/kaburga/kıyma fiilî ağırlıkları; fire/yan ürün ve ağırlık dengesi | Başlanmadı | Parçalama kapanışı ve denge testleri gerekli. |
| KUZ-04 | Miktar veya değer ağırlıklı maliyet dağıtımı; toplam maliyet eşitliği | Başlanmadı | Dış üretimin mevcut miktar dağıtımı kuzu/değer ağırlıklı dağıtımın tamamlandığı anlamına gelmez. |
| KUZ-05 | Giriş lotundan bütün parça lotlarına bağlantı, lot stokları ve Kotlin satışı | Başlanmadı | Parçalama + stok + Android uçtan uca demo gerekli. |
| KUZ-06 | 25×11,50=287,50 / 351 EUR ve 22 kg parça toplamı tutarsızlıklarını kararla bağlama | Doğrulama gerekiyor | [assumptions.md](assumptions.md) farkları kaydeder; gerçek alış belgesi ve 3 kg farkın işletme açıklaması gerekli. Otomatik fire varsayılmaz. |

## 4. Android Kotlin ve satış

PDF s.1/s.3. [android/README.md](../android/README.md) yalnız yönergedir; Kotlin/Compose/Room/Retrofit uygulama kodu yoktur.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| AND-01 | Kotlin/Compose uygulaması, sabit SDK/JDK/Gradle ve cihaz/emülatör build’i | Başlanmadı | Çalıştırılabilir Kotlin kaynakları/build kanıtı yok. |
| AND-02 | Room/SQLite yerel saklama ve Retrofit istemcisi | Başlanmadı | Uygulama ve persistence/API testleri gerekli. |
| AND-03 | SQLite–MySQL tutarlı sync; outbox, idempotent tekrar ve çatışma yönetimi | Başlanmadı | Tasarım notu var; bağlantı kesilmesi/yeniden bağlanma uygulaması ve testi yok. Offline kesin satış varsayılmıyor. |
| AND-04 | Her satış satırında lot, miktar ve kesin stok hareketi | Başlanmadı | Merkezi satış transaction’ı ve Android onay akışı gerekli. |
| AND-05 | Geri çağrılan lotun satışını aynı transaction’da engelleme | Başlanmadı | Satış/recall yarış testi ve cihaz hata gösterimi gerekli. |
| AND-06 | Parçalanan kuzu ürünlerinin Kotlin üzerinden lot bazlı satışı | Başlanmadı | KUZ-05/AND-04 sonrası ikinci görevin uçtan uca demosu. |

## 5. Lot izlenebilirliği ve geri çağırma

PDF s.2, Görev 3. Doğrudan emir ilişkisi, çok adımlı ileri/geri izleme yerine geçmez.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| LOT-01 | Alışta tedarikçi, lot numarası, tarih ve miktar kaydı | Tamamlandı | [Lot/Receipt modelleri](../backend/app/models.py), gerçek çok satırlı alış ve lot bağlantısı testleri. |
| LOT-02 | Uygun ürünlerde son tüketim tarihi girişinin tam uçtan uca kabulü | Doğrulama gerekiyor | Alan/validation var; expired lot engeli test edildi. SKT’nin alış UI→DB roundtrip’i ayrı kabul testiyle doğrulanmalı. |
| LOT-03 | Miktarlı çoktan çoğa hammadde–emir–mamul ilişkileri, kısmi lotun farklı emirlere girmesi | Tamamlandı | [LotLink/Input/Output](../backend/app/models.py); multiple_outputs ve partial_lot MySQL testleri. İlişkiler tahmin değildir. |
| LOT-04 | ET-2026-001 → URT-2026-045 → SUC-2026-045 / 85 paket kesin ilişkisi | Tamamlandı | [HTTP demo](../backend/app/demo.py), [browser testi](../frontend/tests/browser/dashboard.spec.ts); kaynak lotlar ve 85 paket doğrulandı. Henüz market sevkiyatı yok. |
| LOT-05 | Bağımsız depo transferi, satış, müşteri iadesi, rework ve fire hareketlerinin tamamı | Devam ediyor | Üretici sevki/tüketim/mamul kabulü/hammadde iadesi çalışıyor; diğer bağımsız endpoint’ler eksik. |
| LOT-06 | Sorunlu hammaddeden tüm türev lot, stok, sevkiyat ve bilinen alıcıya ileri izleme | Başlanmadı | Recursive graf traversal ve rapor/test gerekli. |
| LOT-07 | Mamulden hammadde/tedarikçi/emirlere çok adımlı geriye izleme | Başlanmadı | Emir ayrıntısındaki doğrudan bağlantılar var; recursive endpoint yok. |
| LOT-08 | Recall kaydı, türev lotları atomik bloklama, satış/üretimle yarışın önlenmesi | Başlanmadı | blocked alanı/sevk engeli var; recall komutu, türev bloklama ve satış kapısı yok. |
| LOT-09 | Market A/B/C’ye 30/25/30 paket sevki ve ET lotundan etkilenen market/iletişim listesi | Başlanmadı | Kesin lotlu satış/sevkiyat, müşteri miktar/iletişim raporu ve zorunlu üçüncü demo gerekli. |
| LOT-10 | İkinci kademe dağıtımı yalnız kayıt varsa kesin gösterme | Başlanmadı | Alıcı zinciri/rapor davranışı gerekli; bilinmeyen alıcı tahmin edilmez. |
| LOT-11 | Parçalama girişinden bütün parça lotlarına aynı izlenebilirlik zinciri | Başlanmadı | Kuzu akışıyla birlikte ilişki/ileri-geri testleri gerekli. |

## 6. Zorunlu yapay zekâ modelleri

PDF s.2. [ml/README.md](../ml/README.md) plandır; eğitim kodu, veri seti ve model artifact’ı yoktur.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| ML-01 | Geçmiş üretim emirlerinden beklenen mamul miktarı ve EKP tahmini (A) | Başlanmadı | pandas/scikit-learn eğitim/tahmin akışı gerekli. |
| ML-02 | Tür, giriş ağırlığı ve geçmişten beklenen parça ağırlıkları tahmini (B) | Başlanmadı | Parçalama veri kaynağı ve ayrı model/evaluasyon gerekli. |
| ML-03 | Örnek/anonymize veri, sentetik veri etiketi ve küçük veri sınırlamaları | Başlanmadı | Veri dosyası/açıklaması/örnek sayıları sunulmalı. |
| ML-04 | Yöntem açıklaması, basit referans karşılaştırması ve ayrı testte hata ölçümü | Başlanmadı | İki model için baseline ve birimleri belirtilen metrikler (örn. kg/EUR-birim MAE) gerekli. |
| ML-05 | Tahmin, gerçek sonuç ve sapmayı API/web üzerinde birlikte gösterme | Başlanmadı | Model sürümü, API entegrasyonu ve gerçek karşılaştırma ekranı gerekli. |
| ML-06 | Lot/recall sonuçlarını ML’den bağımsız kesin ilişkilerde tutma | Doğrulama gerekiyor | Core deterministiktir; ML eklendikten sonra ayrım regresyonla doğrulanmalı. |

OCR/fatura okuma ve anomali uyarıları PDF’de **isteğe bağlıdır**; iki zorunlu modelin yerine geçmez.

## 7. Frontend entegrasyonu

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| WEB-01 | Türkçe dashboard, ürün, iş ortağı/depo ve gerçek API | Tamamlandı | [pages](../frontend/src/pages), [istemci](../frontend/src/lib/api.ts), 25 frontend testi ve 4 gerçek browser testi. Satış/kâr metriği uydurulmaz. |
| WEB-02 | Çok satırlı alış, stok/movement, ayrı emir–dispatch–post ve EKP/lot sonucu | Tamamlandı | [browser testi](../frontend/tests/browser/dashboard.spec.ts); 1.543,50 / 18,16 EUR ve 85 paket doğrulandı. |
| WEB-03 | Decimal string, next_cursor, durumlar, onay ve aynı anahtarlı retry | Tamamlandı | [API](../frontend/tests/api.test.ts), [form](../frontend/tests/forms.test.tsx), [validation](../frontend/tests/validation.test.ts). Kayıp yanıt retry’i bileşen testinde simüledir. |
| WEB-04 | Masaüstü/tablet/mobil görünüm ve loopback proxy | Tamamlandı | Chromium 1440×1000 / 834×1112 / 390×844; taşma ve proxy testleri geçti. Tüm cihaz/tarayıcıların kapsamlı testi değildir. |
| WEB-05 | Parçalama/satış/tam lot/recall/ML gerçek işlem ekranları | Devam ediyor | Navigasyon ve “Geliştirme aşamasında” var; çalışan backend akışı/UI eksik. |
| WEB-06 | Üretim oturumu ve yetkili dağıtım | Doğrulama gerekiyor | Vite anahtarı yerel demoya uygundur; üretim auth/deployment uygulanmadı. |

## 8. Otomatik testler

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| TST-01 | Mevcut backend health/config/Decimal/stok/iş kuralları | Tamamlandı | 24 Ekim tam seçim **38 passed**, 1 upstream deprecation warning; [tests](../tests). |
| TST-02 | Gerçek MySQL migration, satır kilidi, yarış, rollback ve idempotency | Tamamlandı | [core](../tests/test_core_mysql.py), [migration](../tests/test_migrations_mysql.py); sıfırdan ayrı test instance’ında. |
| TST-03 | Temiz npm kurulumu, typecheck, build ve frontend unit/component | Tamamlandı | `npm ci`, typecheck/build başarılı; **25 passed**. |
| TST-04 | Gerçek FastAPI/MySQL/Vite/Chromium ile alış–üretim–stok ve demo | Tamamlandı | **4 passed**; mock backend kullanılmadı. [Rapor](INTEGRATION_VALIDATION_2026-10-24.md). |
| TST-05 | Parçalama, Kotlin satış/sync, recall yarışları ve iki ML modelinin değerlendirmesi | Başlanmadı | İlgili çalışan modüller ve kabul testleri eksik. |
| TST-06 | GitHub main merge sonrası kontroller ve PR check/policy doğrulaması | Doğrulama gerekiyor | Üç PR artık `main` içinde; bu raporun testleri yerel birleşim adayında koşuldu. Son `main` ve güncel CI/PR kontrolleri ayrı çalıştırılmalı. |

## 9. Dokümantasyon ve demo

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| DOC-01 | PDF, ER/API, varsayımlar ve kurulum belgelerini tek güncel sözleşmede birleştirme | Devam ediyor | [ER](data-model.md), [API](api-contract.md), [assumptions](assumptions.md), [backend README](../backend/README.md), [frontend README](../frontend/README.md) var; ortak eski “henüz uygulanmadı” durumları konsolide edilmeli. |
| DOC-02 | Tekrarlanabilir alış/dış üretim/EKP örnek kaydı | Tamamlandı | [app.demo](../backend/app/demo.py) izole web test DB’sinde iki kez aynı emir/lot cevabını verdi. |
| DOC-03 | Üç görevin uçtan uca demosu ve alış/üretim/parçalama/lot/satış/recall raporları | Devam ediyor | Alış/üretim/stok görünümü çalışıyor; parçalama/Kotlin satış/sevkiyat/recall demoları ve raporları eksik. |
| DOC-04 | ML yöntem/örnek tahmin/doğruluk raporu | Başlanmadı | Yalnız plan var; model sonucu ve hata ölçümü yok. |
| DOC-05 | Temiz makinede tek, tutarlı kurulum ve demo çalıştırma | Doğrulama gerekiyor | Host venv/Vite + izole MySQL doğrulandı; tam Compose/fresh release kurulumu doğrulanmadı. |

## 10. Yarışma teslimi

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| TES-01 | İlk üç PR ve ayrı checklist PR’ını main’e alma | Devam ediyor | İlk üç PR birleştirildi; `docs/project-checklist` dalındaki ayrı checklist PR'ının inceleme ve birleşimi bekleniyor. |
| TES-02 | Üç ana akış + kullanılabilir Kotlin uygulaması + iki zorunlu ML çalışmasının kabulü | Başlanmadı | Çalışan temel var; bütün yarışma kapsamı kabul edilebilir durumda değil. |
| TES-03 | Son kaynak/kurulum/örnek kayıt/test/doküman paketi ve temiz kurulumdan demo | Başlanmadı | Entegre main, eksik modüller ve release paketi gerekli. |
| TES-04 | Final sensitive-data kontrolü, sürüm etiketi ve yeniden üretilebilirlik | Doğrulama gerekiyor | Final paket/tag yok; önceki yerel secret kontrolleri final teslim kanıtı değildir. |
| TES-05 | **1 Kasım 2026 23:59 Europe/Istanbul** öncesi gönderim ve alındı doğrulaması | Başlanmadı | Yarışma e-postası: kayıtlı ekip üyesinin aynı e-postayı yanıtlayarak public GitHub deposu ve herkesin izleyebildiği en fazla 15 dakikalık video bağlantısını göndermesi gerekir. Gönderim/alındı kanıtı yok. |

## Bir sonraki kritik backend işi

**Lot bazlı satış/sevkiyat ve buna bağlı ileri/geri izleme–recall:** 85 paketi Market A/B/C’ye 30/25/30 kaydetmek, ET-2026-001’den bütün etkilenen lot/market/stoğa ulaşmak, recall ve satışta aynı lot kilidi altında blok denetlemek, yarış testlerini geçirmek. Bu iş zorunlu üçüncü demoyu ve Android satışını açar. Kuzu parçalama reçetesi/dağıtımı ayrı modül görevi olarak sürdürülmelidir.

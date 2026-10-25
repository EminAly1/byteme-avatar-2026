# ByteMe AVATAR 2026 — Proje tamamlanma checklist’i

**Teslim:** 1 Kasım 2026, **23:59 Europe/Istanbul (UTC+3)**. Tarih/saat kullanıcı talimatıdır; PDF’de teslim tarihi yoktur.

**Gereksinim kaynağı:** [AVATAR_Assessment.pdf](AVATAR_Assessment.pdf), 3 sayfa. **Kanıt tarihi:** 25 Ekim 2026 (Görev 09 ML PR #13 dahil). [Güncel entegrasyon ve test raporu](INTEGRATION_VALIDATION_2026-10-24.md).

## Durumlar ve kapsam

- **Tamamlandı:** Belirtilen dar kapsam için çalışan kaynak ve test/işlevsel doğrulama var; bu, main birleşimi veya bütün yarışma tesliminin tamamlandığı anlamına gelmez.
- **Devam ediyor:** Modülün bir kısmı çalışıyor, bütün kabul senaryosu tamamlanmadı.
- **Başlanmadı:** Çalıştırılabilir akış yok; yalnız yönerge/tasarım bulunması uygulama sayılmaz.
- **Doğrulama gerekiyor:** Gerekli ortam, uçtan uca, insan veya GitHub doğrulaması eksik/engelli.

**GitHub birleşim güncellemesi (24 Ekim 2026):** [PR #1](https://github.com/EminAly1/byteme-avatar-2026/pull/1), [PR #2](https://github.com/EminAly1/byteme-avatar-2026/pull/2) ve [PR #3](https://github.com/EminAly1/byteme-avatar-2026/pull/3) sırasıyla **normal merge commit** ile `main` dalına birleştirildi. Son birleşim commit'i: `7837a85097e2fd50c8da672a03803c319296d344`. Aşağıdaki başarılı testler aynı kaynak ağacının izole yerel birleşim adayında koşulmuştur; son uzak `main` üzerinde yeniden test **henüz yapılmadı**.

**24 Ekim Görev 5 güncellemesi:** [PR #5](https://github.com/EminAly1/byteme-avatar-2026/pull/5) satış/sevkiyat çekirdeğini `main` üzerine normal merge ile ekledi (`e1589d8f219a4ab689348f6b4f698829ab0193dd`). [76 test raporu](../database/sales-shipments-validation.md) izole MySQL'deki Codex koşusuna dayanır; birleşik son `main` üzerinde bağımsız tekrar gereklidir. Bu görev **lot izleme/geri çağırma veya Android satışı bitmiş** anlamına gelmez.

**Görev 6 ek güncellemesi:** [PR #7](https://github.com/EminAly1/byteme-avatar-2026/pull/7) normal merge ile `main` üzerine eklendi (`3d9125e862e8ad77a7c10dcf331633ecc22f8d5e`). [100 test raporu](../database/trace-recall-validation.md): izole gerçek MySQL'de 84 MySQL testi + 16 bağımsız test geçti; son birleşik `main` üzerinde bağımsız tekrar hâlâ gerekli. Android, kuzu parçalama ve iki ML modeli tamamlanmış değildir.

**Görev 7 ek güncellemesi:** [PR #9](https://github.com/EminAly1/byteme-avatar-2026/pull/9) `main` üzerine normal merge ile eklendi (`21d9b31fe26d17bd60765b9f77456e290c7bcc3e`). [131 test raporu](../database/cutting-validation.md): ayrı test MySQL 8'de 115 DB ve 16 diğer test; son merge sonrası `main` bağımsız test doğrulaması bekliyor. Ayrı kalite hedefi: [Profesyonel React UX/UI tasarım şartnamesi](FRONTEND_VISION.md). Bu doküman mevcut UI'ın tamamlandığı anlamına gelmez.

**Görev 8 güncellemesi (25 Ekim):** [PR #11](https://github.com/EminAly1/byteme-avatar-2026/pull/11) `main` üzerine normal merge ile alındı (`94281b6f493d5a1cb66ce953efa6087641454d96`). [Android doğrulama raporu](../android/VALIDATION.md): 16 farklı host testi debug+release'de toplam 32 başarılı çalışma, API 28 AOSP emülatörde 4 farklı cihaz testi iki koşuda toplam 6 başarılı çalışma, gerçek MySQL ile 6 kg→5 kg kuzu but satışı, idempotent tekrar ve LOT_BLOCKED, offline taslak kalıcılığı, lint ve debug APK build. **API 35 instrumentation çöktü; API 35 ve fiziksel telefon doğrulanmadı.** APK build artefaktıdır, Git'e commit edilmedi. Release auth/HTTPS, son birleşik main ve final cihaz/saha kontrolleri ayrıca bekler.

**Görev 09 güncellemesi (25 Ekim):** [PR #13](https://github.com/EminAly1/byteme-avatar-2026/pull/13) `main` üzerine normal merge ile eklendi (`eb0cece585e0b9ab4c3e26daeddb719158c04791`). [ML değerlendirme](../ml/EVALUATION_REPORT.md): her iki model 600 **SYNTHETIC** kayıtla eğitildi; gerçek tarihsel veri 0; 360 eğitim/120 validation/120 test; Ridge üretim/EKP ve Kuzu/beş parça verimi. [181 test raporu](../ml/reports/validation.json): önceki 131 + 31 yeni backend + 19 ML, 0 fail/skip, gerçek API/MySQL HTTP demo. **Gerçek dünyadaki model performansı doğrulanmadı.** React tahmin/gerçek/sapma ekranı ve tümleşik son `main` testleri bekliyor.

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
| KUZ-01 | Hayvan/parti, tür, giriş ağırlığı, gerçek toplam alış maliyeti ve işlem tarihi | Tamamlandı | [Görev 7](../backend/CUTTING.md): Product.species + lot/receipt/supplier/location ve opsiyonel unit_price; 25×11,50=287,50 demo ve MySQL kabul testi. |
| KUZ-02 | Önceden tanımlanabilen reçete ve sürümlü dağıtım anahtarı | Tamamlandı | [RecipeVersion ve RecipeLine](../backend/app/models.py), `allocation_snapshot` ve kullanılabilirlik endpoint'leri; eski kayıt maliyeti sürümden bağımsız korunuyor. |
| KUZ-03 | But/sırt/omuz/kaburga/kıyma fiilî ağırlıkları; fire/yan ürün ve ağırlık dengesi | Tamamlandı | [cuttings.py](../backend/app/cuttings.py), [MySQL raporu](../database/cutting-validation.md): fiilî 22 kg ve açıklanmış 3 kg fark; byproduct ayrı lot/stok. Demo parça ağırlıkları kurgusaldır. |
| KUZ-04 | Miktar veya değer ağırlıklı maliyet dağıtımı; toplam maliyet eşitliği | Tamamlandı | [Görev 7](../backend/CUTTING.md): quantity/value referans anahtarı ve Decimal toplamı; 287,500000 EUR iki yöntemde de korunuyor; sürümlü snapshot/test var. |
| KUZ-05 | Giriş lotundan bütün parça lotlarına bağlantı, lot stokları ve Kotlin satışı | Tamamlandı | [PR #9](https://github.com/EminAly1/byteme-avatar-2026/pull/9) + [PR #11](https://github.com/EminAly1/byteme-avatar-2026/pull/11): gerçek API 28 emülatöründen kuzu but lotu 6 kg→1 kg satış→5 kg merkezî stok, satış/hareket ID ve recall blokajı. API 35/fiziksel cihaz henüz doğrulanmadı. |
| KUZ-06 | 25×11,50=287,50 / 351 EUR ve 22 kg parça toplamı tutarsızlıklarını kararla bağlama | Doğrulama gerekiyor | [assumptions.md](assumptions.md) farkları kaydeder; gerçek alış belgesi ve 3 kg farkın işletme açıklaması gerekli. Otomatik fire varsayılmaz. |

## 4. Android Kotlin ve satış

PDF s.1/s.3. [android/README.md](../android/README.md) yalnız yönergedir; Kotlin/Compose/Room/Retrofit uygulama kodu yoktur.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| AND-01 | Kotlin/Compose uygulaması, sabit SDK/JDK/Gradle ve cihaz/emülatör build’i | Tamamlandı | [Kurulum/sürümler](../android/ANDROID_SETUP.md) ve [validation](../android/VALIDATION.md): Compose Material 3, Gradle test/lint/assembleDebug, API 28 AOSP emülatör. API 35 instrumentation başarısız, fiziksel cihaz henüz yok. |
| AND-02 | Room/SQLite yerel saklama ve Retrofit istemcisi | Tamamlandı | [Android veri katmanı](../android/README.md): sekiz Room tablo, Retrofit/FK, katalog cache, yerel işlem kalıcılığı; host + cihaz DB testi. |
| AND-03 | SQLite–MySQL tutarlı sync; outbox, idempotent tekrar ve çatışma yönetimi | Tamamlandı | [Android validation](../android/VALIDATION.md): kalıcı UUID/gövde, FIFO gönderim, backend onaylı satış, 409 çatışma, offline yalnız taslak, süreç sonrası kalıcılık; uygulama açıkken senkronizasyon. Kapalı uygulamada arka plan gönderimi yok. |
| AND-04 | Her satış satırında lot, miktar ve kesin stok hareketi | Tamamlandı | [API 28 gerçek satış testi](../android/VALIDATION.md): Kotlin→FastAPI→MySQL lot/miktar/StockMovement UUID; 1 kg stok yalnızca bir kez düştü. |
| AND-05 | Geri çağrılan lotun satışını aynı transaction’da engelleme | Tamamlandı | [PR #7](https://github.com/EminAly1/byteme-avatar-2026/pull/7) transaction/yarış koruması + [Android test](../android/VALIDATION.md): eski önbellekle satışta 409 LOT_BLOCKED; UI NEEDS_ACTION, merkezî stok/satış değişmedi. |
| AND-06 | Parçalanan kuzu ürünlerinin Kotlin üzerinden lot bazlı satışı | Tamamlandı | [Demo](../android/VALIDATION.md): kesilmiş value yöntemli kuzu butundan Android Compose'da 1 kg kesin satış; 6→5 kg, idempotent replay ve recall reddi. |

## 5. Lot izlenebilirliği ve geri çağırma

PDF s.2, Görev 3. Doğrudan emir ilişkisi, çok adımlı ileri/geri izleme yerine geçmez.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| LOT-01 | Alışta tedarikçi, lot numarası, tarih ve miktar kaydı | Tamamlandı | [Lot/Receipt modelleri](../backend/app/models.py), gerçek çok satırlı alış ve lot bağlantısı testleri. |
| LOT-02 | Uygun ürünlerde son tüketim tarihi girişinin tam uçtan uca kabulü | Doğrulama gerekiyor | Alan/validation var; expired lot engeli test edildi. SKT’nin alış UI→DB roundtrip’i ayrı kabul testiyle doğrulanmalı. |
| LOT-03 | Miktarlı çoktan çoğa hammadde–emir–mamul ilişkileri, kısmi lotun farklı emirlere girmesi | Tamamlandı | [LotLink/Input/Output](../backend/app/models.py); multiple_outputs ve partial_lot MySQL testleri. İlişkiler tahmin değildir. |
| LOT-04 | ET-2026-001 → URT-2026-045 → SUC-2026-045 / 85 paket kesin ilişkisi | Tamamlandı | [HTTP demo](../backend/app/demo.py), [browser testi](../frontend/tests/browser/dashboard.spec.ts); kaynak lotlar ve 85 paket doğrulandı. Henüz market sevkiyatı yok. |
| LOT-05 | Bağımsız depo transferi, satış, müşteri iadesi, rework ve fire hareketlerinin tamamı | Devam ediyor | Satış ve bağımsız/bağlı sevkiyat API'leri [PR #5](https://github.com/EminAly1/byteme-avatar-2026/pull/5) ile eklendi. Genel depo transferi, müşteri iadesi/iptali ve rework hâlâ eksik. |
| LOT-06 | Sorunlu hammaddeden tüm türev lot, stok, sevkiyat ve bilinen alıcıya ileri izleme | Tamamlandı | [lot_graph.py](../backend/app/lot_graph.py) + [traceability.py](../backend/app/traceability.py), [test raporu](../database/trace-recall-validation.md): gerçek FK ile çok aşamalı ileri izleme ve market alıcı raporu. |
| LOT-07 | Mamulden hammadde/tedarikçi/emirlere çok adımlı geriye izleme | Tamamlandı | [trace](../backend/TRACE_RECALL.md) ve [MySQL testleri](../tests/test_trace_recall_mysql.py): mamulden atalara, girdilere, emir ve tedarikçi FK'larına geriye izleme. |
| LOT-08 | Recall kaydı, türev lotları atomik bloklama, satış/üretimle yarışın önlenmesi | Tamamlandı | [recalls.py](../backend/app/recalls.py): sıralı lot kilitleri, graf revalidation ve atomik recall; MySQL'de satış/üretim yarışları test edildi. Üretim ölçeğinde yük testi ve blok kaldırma API'si kapsam dışı. |
| LOT-09 | Market A/B/C’ye 30/25/30 paket sevki ve ET lotundan etkilenen market/iletişim listesi | Tamamlandı | [demo_recall.py](../backend/app/demo_recall.py) ve [test raporu](../database/trace-recall-validation.md): ET→SUC gerçek FK; A/B/C 30/25/30, toplam 85 ve contact snapshot; bilinmeyen market kalanları null. |
| LOT-10 | İkinci kademe dağıtımı yalnız kayıt varsa kesin gösterme | Başlanmadı | Alıcı zinciri/rapor davranışı gerekli; bilinmeyen alıcı tahmin edilmez. |
| LOT-11 | Parçalama girişinden bütün parça lotlarına aynı izlenebilirlik zinciri | Tamamlandı | [Cutting testleri](../tests/test_cuttings_mysql.py): kaynak kuzu→parça ileri/geri izleme, lot FK ve recall ile parça bloklama. |

## 6. Zorunlu yapay zekâ modelleri

PDF s.2. [ml/README.md](../ml/README.md) plandır; eğitim kodu, veri seti ve model artifact’ı yoktur.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| ML-01 | Geçmiş üretim emirlerinden beklenen mamul miktarı ve EKP tahmini (A) | Tamamlandı | [Üretim model kartı](../ml/MODEL_CARD_PRODUCTION.md): 600 sentetik işlemle Ridge verim/hizmet çarpanı eğitimi; tahmini paket ve EKP API'si; gerçek işletme doğruluğu henüz yok. |
| ML-02 | Tür, giriş ağırlığı ve geçmişten beklenen parça ağırlıkları tahmini (B) | Tamamlandı | [Kesim model kartı](../ml/MODEL_CARD_CUTTING.md): 25 kg Kuzu/beş parça Ridge oran tahmini; fiziksel sınır ve reçete UUID eşlemesi; sentetik model, gerçek işletme doğruluğu yok. |
| ML-03 | Örnek/anonymize veri, sentetik veri etiketi ve küçük veri sınırlamaları | Tamamlandı | [manifest](../ml/data/manifest.json) + [README](../ml/README.md): 600+600 SYNTHETIC, hash/seed/sürüm; gerçek tarihsel veri 0 olduğu açıkça kaydedildi. |
| ML-04 | Yöntem açıklaması, basit referans karşılaştırması ve ayrı testte hata ölçümü | Tamamlandı | [Değerlendirme](../ml/EVALUATION_REPORT.md): her hedef için baseline/Ridge MAE ve RMSE, 360/120/120 zamansal sentetik ayrım, küçük kazanç/sınırlama şeffaf. |
| ML-05 | Tahmin, gerçek sonuç ve sapmayı API/web üzerinde birlikte gösterme | Devam ediyor | [Prediction API](../ml/INTEGRATION.md): değişmez tahmin UUID, model sürümü, gerçek/sapma karşılaştırma API'si hazır; **React web ekranı henüz yok.** |
| ML-06 | Lot/recall sonuçlarını ML’den bağımsız kesin ilişkilerde tutma | Tamamlandı | [ML API ve test raporu](../ml/EVALUATION_REPORT.md): stok/lot/recall öncesi-sonrası snapshot eşitliği ve eski 131 backend testi; tahmin ayrı PredictionRecord tablosunda. |

OCR/fatura okuma ve anomali uyarıları PDF’de **isteğe bağlıdır**; iki zorunlu modelin yerine geçmez.

## 7. Frontend entegrasyonu

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| WEB-01 | Türkçe dashboard, ürün, iş ortağı/depo ve gerçek API | Tamamlandı | [pages](../frontend/src/pages), [istemci](../frontend/src/lib/api.ts), 25 frontend testi ve 4 gerçek browser testi. Satış/kâr metriği uydurulmaz. |
| WEB-02 | Çok satırlı alış, stok/movement, ayrı emir–dispatch–post ve EKP/lot sonucu | Tamamlandı | [browser testi](../frontend/tests/browser/dashboard.spec.ts); 1.543,50 / 18,16 EUR ve 85 paket doğrulandı. |
| WEB-03 | Decimal string, next_cursor, durumlar, onay ve aynı anahtarlı retry | Tamamlandı | [API](../frontend/tests/api.test.ts), [form](../frontend/tests/forms.test.tsx), [validation](../frontend/tests/validation.test.ts). Kayıp yanıt retry’i bileşen testinde simüledir. |
| WEB-04 | Masaüstü/tablet/mobil görünüm ve loopback proxy | Tamamlandı | Chromium 1440×1000 / 834×1112 / 390×844; taşma ve proxy testleri geçti. Tüm cihaz/tarayıcıların kapsamlı testi değildir. |
| WEB-05 | Parçalama/satış/tam lot/recall/ML gerçek işlem ekranları | Devam ediyor | Yeni backend API'leri var ancak ekran entegrasyonları eksik; [FRONTEND_VISION.md](FRONTEND_VISION.md) modern desktop/tablet/mobil tasarım, erişilebilirlik ve gerçek veri UX kabul kriterlerini tanımlar. |
| WEB-06 | Üretim oturumu ve yetkili dağıtım | Doğrulama gerekiyor | Vite anahtarı yerel demoya uygundur; üretim auth/deployment uygulanmadı. |

## 8. Otomatik testler

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| TST-01 | Mevcut backend health/config/Decimal/stok/iş kuralları | Tamamlandı | [Görev 09 test raporu](../ml/reports/validation.json): önceki 131 backend korunarak toplam 181 test (162 backend + 19 ML), gerçek izole MySQL; son merge sonrası main ve frontend/Android testleri ayrıca koşulmalı. |
| TST-02 | Gerçek MySQL migration, satır kilidi, yarış, rollback ve idempotency | Tamamlandı | [Görev 7 MySQL testleri](../tests/test_cuttings_mysql.py), [migration](../tests/test_cutting_migrations_mysql.py) ve eski satış/recall testleri: parçalama/recall kilit yarışı, maliyet/rollback ve şema geçişleri. |
| TST-03 | Temiz npm kurulumu, typecheck, build ve frontend unit/component | Tamamlandı | `npm ci`, typecheck/build başarılı; **25 passed**. |
| TST-04 | Gerçek FastAPI/MySQL/Vite/Chromium ile alış–üretim–stok ve demo | Tamamlandı | **4 passed**; mock backend kullanılmadı. [Rapor](INTEGRATION_VALIDATION_2026-10-24.md). |
| TST-05 | Parçalama, Kotlin satış/sync, recall yarışları ve iki ML modelinin değerlendirmesi | Tamamlandı | [Kesim/recall](../database/cutting-validation.md), [API 28 Android cihazı](../android/VALIDATION.md) ve [iki sentetik ML modeli](../ml/EVALUATION_REPORT.md) ayrı kabul testlerinde doğrulandı. **Tümünün yeni main'de tek koşuda testi, API 35 ve gerçek veri hâlâ TST-06/final doğrulama kapsamı.** |
| TST-06 | GitHub main merge sonrası kontroller ve PR check/policy doğrulaması | Doğrulama gerekiyor | Üç PR artık `main` içinde; bu raporun testleri yerel birleşim adayında koşuldu. Son `main` ve güncel CI/PR kontrolleri ayrı çalıştırılmalı. |

## 9. Dokümantasyon ve demo

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| DOC-01 | PDF, ER/API, varsayımlar ve kurulum belgelerini tek güncel sözleşmede birleştirme | Devam ediyor | [ER](data-model.md), [API](api-contract.md), [assumptions](assumptions.md), [backend README](../backend/README.md), [frontend README](../frontend/README.md) var; ortak eski “henüz uygulanmadı” durumları konsolide edilmeli. |
| DOC-02 | Tekrarlanabilir alış/dış üretim/EKP örnek kaydı | Tamamlandı | [app.demo](../backend/app/demo.py) ve [demo_sales_shipments.py](../backend/app/demo_sales_shipments.py) iki kez idempotent çalıştı; 85 paket 30/25/30 sevk ve 16 defter hareketi raporlandı. |
| DOC-03 | Üç görevin uçtan uca demosu ve alış/üretim/parçalama/lot/satış/recall raporları | Devam ediyor | Dış üretim, kuzu parçalama, recall, API 28 Android satış ve [iki zorunlu ML HTTP demosu](../ml/EVALUATION_REPORT.md) ayrı doğrulandı. Tek bütünleşik web/Android demo videosu ve son kabul hâlâ eksik. |
| DOC-04 | ML yöntem/örnek tahmin/doğruluk raporu | Tamamlandı | [Model A](../ml/MODEL_CARD_PRODUCTION.md), [Model B](../ml/MODEL_CARD_CUTTING.md), [metrikler](../ml/EVALUATION_REPORT.md) ve [API örneği](../ml/reports/demo.json); gerçek veri/kalibre aralık yok. |
| DOC-05 | Temiz makinede tek, tutarlı kurulum ve demo çalıştırma | Doğrulama gerekiyor | Host venv/Vite + izole MySQL doğrulandı; tam Compose/fresh release kurulumu doğrulanmadı. |

## 10. Yarışma teslimi

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| TES-01 | İlk üç PR ve ayrı checklist PR’ını main’e alma | Tamamlandı | [PR #1](https://github.com/EminAly1/byteme-avatar-2026/pull/1), [#2](https://github.com/EminAly1/byteme-avatar-2026/pull/2), [#3](https://github.com/EminAly1/byteme-avatar-2026/pull/3) ve [#4](https://github.com/EminAly1/byteme-avatar-2026/pull/4) main'e birleşti. Sonraki geliştirme PR'ları ayrı takip edilir. |
| TES-02 | Üç ana akış + kullanılabilir Kotlin uygulaması + iki zorunlu ML çalışmasının kabulü | Devam ediyor | Üç zorunlu iş akışının backend'i, API 28 Kotlin satışı ve iki sentetik ML modeli ayrı ayrı gösterildi; **tek birleşik UI/Android/demo ve release kabulü hâlâ yapılmadı.** |
| TES-03 | Son kaynak/kurulum/örnek kayıt/test/doküman paketi ve temiz kurulumdan demo | Başlanmadı | Entegre main, eksik modüller ve release paketi gerekli. |
| TES-04 | Final sensitive-data kontrolü, sürüm etiketi ve yeniden üretilebilirlik | Doğrulama gerekiyor | Final paket/tag yok; önceki yerel secret kontrolleri final teslim kanıtı değildir. |
| TES-05 | **1 Kasım 2026 23:59 Europe/Istanbul** öncesi gönderim ve alındı doğrulaması | Başlanmadı | Yarışma e-postası: kayıtlı ekip üyesinin aynı e-postayı yanıtlayarak public GitHub deposu ve herkesin izleyebildiği en fazla 15 dakikalık video bağlantısını göndermesi gerekir. Gönderim/alındı kanıtı yok. |

## Bir sonraki kritik backend işi

**Lot bazlı satış/sevkiyat ve buna bağlı ileri/geri izleme–recall:** 85 paketi Market A/B/C’ye 30/25/30 kaydetmek, ET-2026-001’den bütün etkilenen lot/market/stoğa ulaşmak, recall ve satışta aynı lot kilidi altında blok denetlemek, yarış testlerini geçirmek. Bu iş zorunlu üçüncü demoyu ve Android satışını açar. Kuzu parçalama reçetesi/dağıtımı ayrı modül görevi olarak sürdürülmelidir.

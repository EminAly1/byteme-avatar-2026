# ByteMe AVATAR 2026 — Proje tamamlanma checklist’i

**Teslim:** 1 Kasım 2026, **23:59 Europe/Istanbul (UTC+3)**. Tarih/saat kullanıcı talimatıdır; PDF’de teslim tarihi yoktur.

**Gereksinim kaynağı:** [AVATAR_Assessment.pdf](AVATAR_Assessment.pdf), 3 sayfa. **Güncel kısa kabul:** 31 Ekim 2026; aşağıdaki 28 Ekim Görev19 tam-suite kanıtı ayrıca korunur. [Güncel entegrasyon ve test raporu](INTEGRATION_VALIDATION_2026-10-24.md).

## 31 Ekim — Görev 26 son paketleme durumu

Bu bölüm güncel durumu belirtir; yukarıdaki tarihli raporlar ve aşağıdaki eski test
sayıları tarihsel kanıttır. Güncel main **f2a0a156d769793b16f17d5de09c5a0393f69aae**:
Görev 21–25, PR #37/#38/#40/#41/#42 birleşmiştir. Paketleme ayrı
`feature/final-delivery-packaging` branch'inde; main'e kendimiz merge yapmadık.
[Son kabul](FINAL_RELEASE_READINESS.md), [JSON](final-delivery/acceptance.json),
[İndir ve kur](INDIRME.md).

| ID | Son görev | Durum | Kanıt / açık sınır |
| --- | --- | --- | --- |
| REL26-01 | Aynı kaynak tabanı ve Görev 21–25 atalarını kontrol | Tamamlandı | PR42/f2a0a15; backend/web/ML iş kodu değişmedi |
| REL26-02 | Güncel kısa web/backend/ML kapısı | Tamamlandı | typecheck/build, MySQL8/health/ready/migration/check,5 recall+3 gerçek PDF=8 passed,30tablo değişmezliği,iki checksum/yükleme/tahmin |
| REL26-03 | Veri silmeden Preview APK paketleme | Tamamlandı | com.byteme.avatar.preview, 0.1.0-preview.2;31/31 host,debug/preview lint0/build; APK kimlik/imza/hash doğrulandı. Cihaz kurulumu bu maddenin kapsamı değil |
| REL26-04 | Preview fiziksel/API28 açılış, uyarı, satış/offline ve PDF/SAF/paylaşma | Doğrulama gerekiyor | Hazır cihaz yok; eski API28 kanıtı yeni APK'ye taşınmaz. API35 **NO ACCEPTANCE / 0 test** |
| REL26-05 | Gerçek Release/APK yayın alanı | Doğrulama gerekiyor | Releases API **Forbidden**; tag/asset/download URL yok. Yerel APK/hash ve manuel adımlar INDIRME'de |
| REL26-06 | Linux kullanıcı/indirme/video/taslak belgeleri | Tamamlandı | README,INDIRME,USER_GUIDE,DEMO_RUNBOOK,14:30 FINAL_DEMO_SCRIPT ve gönderilmemiş taslak güncellendi |
| REL26-07 | Final PR/main incelemesi ve son GitHub check/policy | Devam ediyor | Paketleme branch'i; main'e merge edilmedi. PR/compare son kabulde |
| REL26-08 | Video/link, gerçek e-posta ve alındı | Başlanmadı | Video çekilmedi/yüklenmedi; gönderim/alındı yok. Son tarih 1 Kasım 2026, 23:59 Türkiye |

**Güncel GO:** kısa kapı kapsamındaki yerel web/backend/ML ve APK paketleme.
**NO-GO:** eksiksiz resmî teslim/public APK dağıtımı ve internete açık üretim.
TST-06,TES-03,TES-04,DOC-03 devam eder; TES-05 başlanmadı. ML toplam **6.000
SYNTHETIC/0 gerçek tarihsel**; bazı metrikler gerilemiştir. RBAC/TLS/e-Fatura yoktur.

**Tarihsel release entegrasyonu (26 Ekim):** [PR #20](https://github.com/EminAly1/byteme-avatar-2026/pull/20) `main` üzerine normal merge ile alındı (`9b33892b35c787559bae4d77211b1008a0a8bae4`). [RELEASE_READINESS.md](RELEASE_READINESS.md) ve [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md): izole MySQL8'de 194 backend+ML testi, 45 frontend unit, 15 Chromium E2E + 1 gerçek missing-model 503; Android API28 4/4, API35 3/4 (önceden korunmuş kanıtlar, 26 Ekimde yeniden çalıştırılmadı). Üç servisli Docker Compose yerel demo GO, **tam PDF teslimi NO-GO** (transfer, müşteri iade/iptali, rework, ikinci kademe kabulü, video/tag/gönderim). 135 dosyalık PR içinde çok sayıda üretilmiş test logu ve PNG var; kullanıcı isteğine göre test kaynakları korunarak final temizlikte CI/Release arşivine taşınmalı. Eski tarihli ilerleme notları tarihsel bağlamdır, güncel durum için aşağıdaki maddeleri ve bu paragrafı esas alın.

**Görev 13 güncellemesi (27 Ekim):** [PR #22](https://github.com/EminAly1/byteme-avatar-2026/pull/22) normal merge ile `main` üzerine eklendi (`42403d20baa45db25c9d8e62ec3947db594c0f05`). [Transfer/iade API ve maliyet politikası](../backend/TRANSFERS_RETURNS.md), [gerçek MySQL kanıtı](../database/transfers-returns-validation.md): önceki 194 + 62 yeni = **256 başarılı test**; 20 kg→13/7 kg iki depoya atomik transfer, sevke bağlı 2 kg müşteri iadesi, 40 EUR kredi/19,40 EUR tarihsel maliyet düzeltmesi, tam sevksiz satış iptali karantina, 29 tablo replay hash kararlılığı. **Rework hâlâ eksik**, LOT-05 devam ediyor. React/Android ekranları ve son birleşik `main` testleri bu görevde tekrar çalıştırılmadı. Üretilmiş test log/JSON/PNG'ler final temizlikte kanıtlar korunarak ayrılacak.

**Görev 14 rework (27 Ekim):** [PR #24](https://github.com/EminAly1/byteme-avatar-2026/pull/24) `main` dalına normal merge ile alındı (`27a38bd2aac75481ee8ab9b3ae2a4c3912394b88`). [Backend rework sözleşmesi](../backend/REWORK.md) ve [MySQL kabul raporu](../database/rework-validation.md): önceki 256 + 52 yeni = **308 passed** (289 backend+19 ML); tek üretilmiş kg mamul lotu, atomik 10→9,5+0,5kg açıklamalı fark, 100+15=115 EUR kesin maliyet; çok aşamalı FK trace/recall, gerçek 1213 deadlock/idempotency ve 29 tablo tekrar hash sabit. **İlk başlangıç koşusunda açıklanamayan 1 DB503 görüldü; değişiklik yapılmadan tekrar ve final testleri geçti.** LOT-05 rework backend kısmı artık mevcut ancak **React/Android kullanıcı akışı ve son birleşik main kabulü bekleniyor.** Karantina kalite onayı/yeniden değerleme yoktur; gerçek gıda uygunluğu iddia edilmez.

**Görev 15 güncellemesi (27 Ekim):** [PR #27](https://github.com/EminAly1/byteme-avatar-2026/pull/27) main'e normal merge edildi (`a601105b0d4c7f50ced7520193b31e32a4a6ca0d`). [İkinci kademe API](../backend/SECOND_TIER_DISTRIBUTION.md), [gerçek MySQL kabul](../database/second-tier-validation.md): 308 önceki +52 yeni = **360 passed** (341 backend +19 ML); 30/25/30=85 şirket sevkiyatı üzerine A→X 12 paket bildirim, 18 paket yalnız belgelenmemiş kapasite, **fiziksel market stoğu bilinmiyor**. İade/dağıtım yarışı, 1213 deadlock, migration ve recall raporu doğrulandı. **LOT-10 backend çalışıyor, React kullanıcı ekranı ve tam birleşik `main` doğrulaması henüz yok.** Önceki dönemlere ait NO-GO tarihsel notları, yeni backend'i yok sayacak şekilde okunmamalıdır. Final jüri videosu/release/gönderim açık.

**Görev 16 web kabulü (27 Ekim):** [PR #29](https://github.com/EminAly1/byteme-avatar-2026/pull/29) normal merge ile `main` dalına alındı (`58a832adae7764405823d2aae3859ed9ed6deea4`). [React entegrasyon raporu](../frontend/OPERATIONS_INTEGRATION_REPORT.md): 45 eski +20 yeni = **65/65 unit**, yeni modül odaklı 11 yeni +3 eski = **14/14 gerçek Chromium/FastAPI/MySQL**; typecheck/build başarılı. Transfer, sevke bağlı müşteri iadesi, sevksiz satış tam iptali, kg rework, ikinci kademe kayıt ve recall, satışın backend VKP/net brüt kâr gösterimi gerçek web ekranlarında. A→X 12, toplam 85, tahsis edilmemiş 18 **fiziksel stok iddiası değil**. **LOT-05, LOT-10, URT-07 desteklenen dar proje kapsamı için tamamlandı**; çok satırlı iade UI, karmaşık rework formları, QA serbest bırakma, üçüncü kademe ve public RBAC/TLS bu sürümün kapsamı dışında. **Tam birleşik `main` backend/frontend/Android testi ve jüri video/gönderimi yapılmadı; TST-06/TES/DOC açık.**

**Görev 19 final aday kabulü (28 Ekim):** [PR #35](https://github.com/EminAly1/byteme-avatar-2026/pull/35) main'e alındı (`00811ab89d1bb9f2bbc4ea0bb4571af8a1d588ca`). [Final kabul](FINAL_RELEASE_READINESS.md), [JSON kanıt](final-release/acceptance.json), [kullanım kılavuzu](USER_GUIDE.md), [14:30 video çekim planı](FINAL_DEMO_SCRIPT.md), [gönderilmemiş e-posta taslağı](SUBMISSION_EMAIL_DRAFT.md). İzole güncel 28 Ekim `main` tabanı üzerinde **427 backend+ML (408+19)**, **83 React unit**, **34 ayrı Chromium senaryosu** (ilk iki seed/proxy hatası hedefli tekrar ile geçti), **32 Android host yürütümü / 16 tekil**, API28 **4/4**; **API35 0 instrumentation ve NO acceptance**. Docker/MySQL/Alembic `f1507a26b001`, iki sentetik model, gerçek Docker PDF ve 30 tablo hash'i korundu. **Yerel jüri demo GO; video/public link, release tag/APK yayın, son main check ve gerçek e-posta/alındı yok: tam teslim NO-GO.** Public üretim auth/RBAC/TLS olmadığından NO-GO. Daha eski kısımlardaki “transfer/rework/ikinci kademe eksik” notları tarihsel durumlardır.

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

**Görev 10 güncellemesi (25 Ekim):** [PR #15](https://github.com/EminAly1/byteme-avatar-2026/pull/15) `main` üzerine normal merge ile eklendi (`fe1dca979e92b522fa6815a3e68fe5e230760d1e`). [Frontend V2 doğrulama raporu](../frontend/VALIDATION_V2.md): 38 unit/component + 14 gerçek FastAPI/MySQL/Chromium E2E + 1 gerçek eksik-model 503 senaryosu; 18 görünümde otomatik axe denetimi 0 ihlal; beş viewport ve 13 gerçek Chromium ekran görüntüsü. Kuzu parçalama, satış/sevkiyat, lot trace, recall ve iki ML tahmin/sapma ekranları gerçek backend ile çalıştı. **Bu işlevsel prototip kabulüdür; premium UI/UX son rötuşları, tam birleşik main regresyonu, üretim auth/TLS/dağıtım, Android API 35 ve final teslim bekliyor.**

**Görev 11 görsel kabulü (25 Ekim):** [PR #17](https://github.com/EminAly1/byteme-avatar-2026/pull/17) normal merge ile `main` üzerine eklendi (`56314099f8f260aa582fd3750e43c63b49135bfd`). [UI refinement raporu](../frontend/UI_REFINEMENT_REPORT.md) ve [önce/sonra gerçek Chromium görüntüleri](../frontend/validation-premium/): dashboard öncelikleri, mobil satış/kesim kartları, teknik referans açıklığı, AI özet+hassasiyet, recall market etkisi, renk/metin/erişilebilirlik. Codex'in son izole test raporu: **43 unit/component + 14 gerçek E2E + 1 gerçek model-503, 35 responsive ve 33 axe görünümü otomatik sıfır ihlalle** geçti. İlk yüklenen JS yaklaşık 543→332 kB raporlandı. Bunlar yalnız frontend kodunda doğrulanan değişikliklerdir; final birleşik `main` regresyonu, fiziksel mobil/çok tarayıcı, Compose ve release kontrolleri halen bekler.

## 1. Proje altyapısı

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| ALT-01 | Monorepo ve üç ajan için dosya sahipliği | Tamamlandı | [AGENTS.md](../AGENTS.md), [PR #1](https://github.com/EminAly1/byteme-avatar-2026/pull/1); mevcut kurulum/test yolları çalıştı. Android/ML uygulamaları sonradan eklendi; REL26 güncel kabulü gösterir. |
| ALT-02 | FastAPI health ve MySQL ready | Tamamlandı | [main.py](../backend/app/main.py), [health testleri](../tests/test_health.py); gerçek iki endpoint 200. |
| ALT-03 | Environment üzerinden MySQL 8, Alembic migration, FK/CHECK ve Decimal alanlar | Tamamlandı | [database.py](../backend/app/database.py), [migration](../backend/alembic/versions/eeea4b5dd1a8_create_production_and_stock_ledger_core.py), [migration testi](../tests/test_migrations_mysql.py); MySQL 8.0.46 üzerinde upgrade/check/downgrade/upgrade geçti. |
| ALT-04 | Yerel proxy sınırı ve gizli bilgileri Git/tarayıcı dışında tutma | Tamamlandı | [proxy](../frontend/server/proxy.ts), [browser testi](../frontend/tests/browser/dashboard.spec.ts); Host/Origin, dosya erişimi ve key sızıntısı kontrolleri geçti. Üretim auth’u değildir. |
| ALT-05 | Üç PR’ı normal merge commit ile sırayla main’e alma, hedefleri değiştirme | Tamamlandı | PR #1, #2 ve #3 GitHub üzerinde birleştirildi; `main` son birleşim commit'i `7837a850`. Son `main` testleri TST-06 kapsamında ayrıca doğrulanmalı. |
| ALT-06 | Tek komutla bütün servislerin çalıştığı Docker Compose | Tamamlandı | [PR #20](https://github.com/EminAly1/byteme-avatar-2026/pull/20), [Compose release](RELEASE_READINESS.md): MySQL 8, FastAPI, React healthy; izolasyon, migration, modeller, loopback. Normal DNS build bu bulutta başarısız; belgeli proxy/CA build başarılı. Yerel demo kapsamı. |
| ALT-07 | Üretim kullanıcı oturumu, roller ve yetkilendirme | Başlanmadı | [Final release](FINAL_RELEASE_READINESS.md): yerel X-API-Key/loopback koruması var, ancak gerçek kullanıcı hesabı/roller/RBAC/TLS ve üretim güvenliği yok. İnternete açık yayına hazır değil. |

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
| URT-07 | VKP, brüt kâr ve satış marjını backend’de hesaplayıp gösterme | Tamamlandı | [PR #20](https://github.com/EminAly1/byteme-avatar-2026/pull/20) backend `GET /v1/sales/{id}/profitability` + [PR #29](https://github.com/EminAly1/byteme-avatar-2026/pull/29) `/satislar/:id` premium paneli; backend Decimal VWK/VKP, kayıtlı tüketim maliyeti, brüt kâr/marj ve iade/iptal sonrası net değerler gösteriliyor. Vergi/iskonto/genel gider veya nakit tahsilat hesaplanmıyor. |
| URT-08 | Gerçek deadlock üreterek sınırlı retry’ı doğrulama | Tamamlandı | [Gerçek 1213 deadlock MySQL testleri](../tests/test_release_deadlock_mysql.py) ve [release raporu](RELEASE_READINESS.md): transaction retry/replay, ayrı kontrollü retry-tavanı testi. |

## 3. Kuzu parçalama

PDF s.1, Görev 2. Tabloda `cutting` türünün bulunması çalışan parçalama akışı değildir.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| KUZ-01 | Hayvan/parti, tür, giriş ağırlığı, gerçek toplam alış maliyeti ve işlem tarihi | Tamamlandı | [Görev 7](../backend/CUTTING.md): Product.species + lot/receipt/supplier/location ve opsiyonel unit_price; 25×11,50=287,50 demo ve MySQL kabul testi. |
| KUZ-02 | Önceden tanımlanabilen reçete ve sürümlü dağıtım anahtarı | Tamamlandı | [RecipeVersion ve RecipeLine](../backend/app/models.py), `allocation_snapshot` ve kullanılabilirlik endpoint'leri; eski kayıt maliyeti sürümden bağımsız korunuyor. |
| KUZ-03 | But/sırt/omuz/kaburga/kıyma fiilî ağırlıkları; fire/yan ürün ve ağırlık dengesi | Tamamlandı | [cuttings.py](../backend/app/cuttings.py), [MySQL raporu](../database/cutting-validation.md): fiilî 22 kg ve açıklanmış 3 kg fark; byproduct ayrı lot/stok. Demo parça ağırlıkları kurgusaldır. |
| KUZ-04 | Miktar veya değer ağırlıklı maliyet dağıtımı; toplam maliyet eşitliği | Tamamlandı | [Görev 7](../backend/CUTTING.md): quantity/value referans anahtarı ve Decimal toplamı; 287,500000 EUR iki yöntemde de korunuyor; sürümlü snapshot/test var. |
| KUZ-05 | Giriş lotundan bütün parça lotlarına bağlantı, lot stokları ve Kotlin satışı | Tamamlandı | [PR #9](https://github.com/EminAly1/byteme-avatar-2026/pull/9) + [PR #11](https://github.com/EminAly1/byteme-avatar-2026/pull/11): gerçek API 28 emülatöründen kuzu but lotu 6 kg→1 kg satış→5 kg merkezî stok, satış/hareket ID ve recall blokajı. API 35/fiziksel cihaz henüz doğrulanmadı. |
| KUZ-06 | 25×11,50=287,50 / 351 EUR ve 22 kg parça toplamı tutarsızlıklarını kararla bağlama | Tamamlandı | [varsayımlar](assumptions.md), [cutting doğrulama](../database/cutting-validation.md): demo alış 25×11,50=287,50 EUR; 351 EUR PDF tutarsızlığı raporlu, 22 kg çıktı+3 kg **açıklanmış fark**, otomatik fire yok. Gerçek işletme faturasıyla doğrulandı iddiası yok. |

## 4. Android Kotlin ve satış

PDF s.1/s.3. [Android](../android/README.md) uygulaması mevcut; [Görev24](ANDROID_PREMIUM_UX_ACCEPTANCE.md), [Görev25](ANDROID_DOCUMENTS_ACCEPTANCE.md) ve REL26 yeni paketleme/cihaz kabul sınırlarını ayrı gösterir.

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
| LOT-02 | Uygun ürünlerde son tüketim tarihi girişinin tam uçtan uca kabulü | Tamamlandı | [PR #20](https://github.com/EminAly1/byteme-avatar-2026/pull/20): gerçek Chromium alış UI→MySQL lot SKT roundtrip ve son kullanma/bloklama testi geçti. |
| LOT-03 | Miktarlı çoktan çoğa hammadde–emir–mamul ilişkileri, kısmi lotun farklı emirlere girmesi | Tamamlandı | [LotLink/Input/Output](../backend/app/models.py); multiple_outputs ve partial_lot MySQL testleri. İlişkiler tahmin değildir. |
| LOT-04 | ET-2026-001 → URT-2026-045 → SUC-2026-045 / 85 paket kesin ilişkisi | Tamamlandı | [HTTP demo](../backend/app/demo.py), [browser testi](../frontend/tests/browser/dashboard.spec.ts); kaynak lotlar ve 85 paket doğrulandı. Henüz market sevkiyatı yok. |
| LOT-05 | Bağımsız depo transferi, satış, müşteri iadesi, rework ve fire hareketlerinin tamamı | Tamamlandı | [PR #22](https://github.com/EminAly1/byteme-avatar-2026/pull/22) atomik transfer/iade/iptal, [#24](https://github.com/EminAly1/byteme-avatar-2026/pull/24) kg rework/kayıp ve [#29](https://github.com/EminAly1/byteme-avatar-2026/pull/29) web `/hareketler` gerçek API kabulü. Karantina/blokaj/recall korunuyor. UI ilk sürümde tek satırlı iade, tek kayıp/hizmet rework; kalite serbest bırakma ve fiziksel Android operatör UI bu maddenin dar kabulüne dahil değil. Son birleşik tam test TST-06'da açık. |
| LOT-06 | Sorunlu hammaddeden tüm türev lot, stok, sevkiyat ve bilinen alıcıya ileri izleme | Tamamlandı | [lot_graph.py](../backend/app/lot_graph.py) + [traceability.py](../backend/app/traceability.py), [test raporu](../database/trace-recall-validation.md): gerçek FK ile çok aşamalı ileri izleme ve market alıcı raporu. |
| LOT-07 | Mamulden hammadde/tedarikçi/emirlere çok adımlı geriye izleme | Tamamlandı | [trace](../backend/TRACE_RECALL.md) ve [MySQL testleri](../tests/test_trace_recall_mysql.py): mamulden atalara, girdilere, emir ve tedarikçi FK'larına geriye izleme. |
| LOT-08 | Recall kaydı, türev lotları atomik bloklama, satış/üretimle yarışın önlenmesi | Tamamlandı | [recalls.py](../backend/app/recalls.py): sıralı lot kilitleri, graf revalidation ve atomik recall; MySQL'de satış/üretim yarışları test edildi. Üretim ölçeğinde yük testi ve blok kaldırma API'si kapsam dışı. |
| LOT-09 | Market A/B/C’ye 30/25/30 paket sevki ve ET lotundan etkilenen market/iletişim listesi | Tamamlandı | [demo_recall.py](../backend/app/demo_recall.py) ve [test raporu](../database/trace-recall-validation.md): ET→SUC gerçek FK; A/B/C 30/25/30, toplam 85 ve contact snapshot; bilinmeyen market kalanları null. |
| LOT-10 | İkinci kademe dağıtımı yalnız kayıt varsa kesin gösterme | Tamamlandı | [PR #27](https://github.com/EminAly1/byteme-avatar-2026/pull/27) audit/FK ve [#29](https://github.com/EminAly1/byteme-avatar-2026/pull/29) `/dagitimlar` + recall React kabulü: Market A→X **12** kayıtlı, A/B/C şirket sevkiyatı **85**; belgelenmiş tahsis edilmemiş **18 paket fiziksel stok değil**. Gerçek üçüncü kademe/market stoğu bilinmiyor; başarı yalnız kayıtlı ikinci kademe içindir. |
| LOT-11 | Parçalama girişinden bütün parça lotlarına aynı izlenebilirlik zinciri | Tamamlandı | [Cutting testleri](../tests/test_cuttings_mysql.py): kaynak kuzu→parça ileri/geri izleme, lot FK ve recall ile parça bloklama. |

## 6. Zorunlu yapay zekâ modelleri

PDF s.2. [ML kaynak/model kartları](../ml/README.md) ve [Görev22 v2 kabulü](AI_MODEL_V2_ACCEPTANCE.md) mevcuttur; eski v1 sayıları tarihsel raporlarda korunur.

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| ML-01 | Geçmiş üretim emirlerinden beklenen mamul miktarı ve EKP tahmini (A) | Tamamlandı | [Üretim model kartı](../ml/MODEL_CARD_PRODUCTION.md): güncel v2: 3.000 sentetik işlemle Ridge verim/hizmet çarpanı eğitimi; tahmini paket ve EKP API'si; gerçek işletme doğruluğu henüz yok. |
| ML-02 | Tür, giriş ağırlığı ve geçmişten beklenen parça ağırlıkları tahmini (B) | Tamamlandı | [Kesim model kartı](../ml/MODEL_CARD_CUTTING.md): 25 kg Kuzu/beş parça Ridge oran tahmini; fiziksel sınır ve reçete UUID eşlemesi; sentetik model, gerçek işletme doğruluğu yok. |
| ML-03 | Örnek/anonymize veri, sentetik veri etiketi ve küçük veri sınırlamaları | Tamamlandı | [manifest](../ml/data/manifest.json) + [README](../ml/README.md): güncel 3.000+3.000=6.000 SYNTHETIC, hash/seed/sürüm; gerçek tarihsel veri 0 olduğu açıkça kaydedildi. |
| ML-04 | Yöntem açıklaması, basit referans karşılaştırması ve ayrı testte hata ölçümü | Tamamlandı | [Değerlendirme](../ml/EVALUATION_REPORT.md): her hedef için baseline/Ridge MAE ve RMSE, v2/model 1.800/600/600 zamansal sentetik ayrım, bazı metrik gerilemeleri şeffaf; eski v1 karşılaştırmaları korunur. |
| ML-05 | Tahmin, gerçek sonuç ve sapmayı API/web üzerinde birlikte gösterme | Tamamlandı | [Frontend v2 gerçek E2E](../frontend/VALIDATION_V2.md): üretim/kesim tahminleri; prediction UUID/sürüm/zaman, işlem kapanınca backend kaynaklı gerçek ve sapma tabloları; SYNTHETIC etiketi görünür. |
| ML-06 | Lot/recall sonuçlarını ML’den bağımsız kesin ilişkilerde tutma | Tamamlandı | [ML API ve test raporu](../ml/EVALUATION_REPORT.md): stok/lot/recall öncesi-sonrası snapshot eşitliği ve eski 131 backend testi; tahmin ayrı PredictionRecord tablosunda. |

OCR/fatura okuma ve anomali uyarıları PDF’de **isteğe bağlıdır**; iki zorunlu modelin yerine geçmez.

## 7. Frontend entegrasyonu

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| WEB-01 | Türkçe dashboard, ürün, iş ortağı/depo ve gerçek API | Tamamlandı | [Premium UI/UX raporu](../frontend/UI_REFINEMENT_REPORT.md): ilk ekranda gerçek operasyon özeti, satış/sevkiyat, net mikro metinler, hızlı aksiyonlar ve korunmuş API. |
| WEB-02 | Çok satırlı alış, stok/movement, ayrı emir–dispatch–post ve EKP/lot sonucu | Tamamlandı | [browser testi](../frontend/tests/browser/dashboard.spec.ts); 1.543,50 / 18,16 EUR ve 85 paket doğrulandı. |
| WEB-03 | Decimal string, next_cursor, durumlar, onay ve aynı anahtarlı retry | Tamamlandı | [Frontend v2 gerçek E2E](../frontend/VALIDATION_V2.md): commit sonrası response kaybı, aynı UUID+gövdeyle güvenli retry, tek kesin satış; Decimal string ve cursor/proxy koruması. |
| WEB-04 | Masaüstü/tablet/mobil görünüm ve loopback proxy | Tamamlandı | [Premium UX](../frontend/UI_REFINEMENT_REPORT.md): beş viewport/35 dolu ekran kontrolü ve 33 axe taraması 0 otomatik ihlal; mobil kartlar, 44px dokunma, odak ve loopback proxy korunuyor. Gerçek fiziksel telefon ve farklı tarayıcı henüz test edilmedi. |
| WEB-05 | Parçalama/satış/tam lot/recall/ML gerçek işlem ekranları | Tamamlandı | [PR #17](https://github.com/EminAly1/byteme-avatar-2026/pull/17): gerçek satış/recall/cutting/AI akışları korundu, teknik ID'ler ikincil, AI özet ve mobil kartlar, market etki sırası iyileştirildi; 14 Chromium E2E + 1 gerçek model 503 testi raporlandı. |
| WEB-06 | Üretim oturumu ve yetkili dağıtım | Başlanmadı | [Final release](FINAL_RELEASE_READINESS.md): React/Node proxy yerel demo için doğrulandı; gerçek kullanıcı oturumu, RBAC, TLS ve production deployment hâlâ NO-GO. |

## 8. Otomatik testler

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| TST-01 | Mevcut backend health/config/Decimal/stok/iş kuralları | Tamamlandı | [Görev 15 MySQL kabulü](../database/second-tier-validation.md): önceki 308 + 52 yeni = **360 passed** (341 backend +19 ML), 0 failed/skipped. Son birleşik main üzerinde bağımsız bütünleşik koşu TST-06'da açık. |
| TST-02 | Gerçek MySQL migration, satır kilidi, yarış, rollback ve idempotency | Tamamlandı | [İkinci kademe MySQL yarışları](../tests/test_second_tier_mysql.py), [migration](../tests/test_second_tier_migrations_mysql.py): müşteri iade/dağıtım iki kilit sırası, gerçek 1213 deadlock/retry, taşma ve kronoloji reddi, rollback/replay ve önceki rework/transfer testleri. |
| TST-03 | Temiz npm kurulumu, typecheck, build ve frontend unit/component | Tamamlandı | [Görev 16 raporu](../frontend/OPERATIONS_INTEGRATION_REPORT.md): `npm ci`, typecheck, build ve **65 unit passed** (45 önceki+20 yeni) gerçek Codex çalışma ortamında. Main'de son birleşik CI ayrıca TST-06 altında. |
| TST-04 | Gerçek FastAPI/MySQL/Vite/Chromium ile alış–üretim–stok ve demo | Tamamlandı | [Görev 12](release-validation/frontend-e2e.txt) önceki 15 Chromium+ayrı 503; [Görev 16](../frontend/OPERATIONS_INTEGRATION_REPORT.md) farklı kaynak sürümünde **14 hedefli gerçek Chromium** (11 yeni+3 mevcut) operasyon/UI akışı, görünüm/erişilebilirlik kontrolü; bütün eski E2E tek koşuda tekrarlanmadı (TST-06). |
| TST-05 | Parçalama, Kotlin satış/sync, recall yarışları ve iki ML modelinin değerlendirmesi | Tamamlandı | [Kesim/recall](../database/cutting-validation.md), [API 28 Android cihazı](../android/VALIDATION.md) ve [iki sentetik ML modeli](../ml/EVALUATION_REPORT.md) ayrı kabul testlerinde doğrulandı. **Tümünün yeni main'de tek koşuda testi, API 35 ve gerçek veri hâlâ TST-06/final doğrulama kapsamı.** |
| TST-06 | GitHub main merge sonrası kontroller ve PR check/policy doğrulaması | Devam ediyor | 31 Ekim PR42 tabanında kısa kapı geçti (REL26); paketleme main birleşimi ve GitHub check/policy erişimi bekler. Tarihsel tam-suite: [PR #35](https://github.com/EminAly1/byteme-avatar-2026/pull/35) main'e birleşen Task19 kabulü: güncel birleşik PR #1–#34 kaynak tabanında **427 backend/ML, 83 unit, 34 ayrı Chromium, API28 4/4**; local Compose/DB/PDF GO. **PR #35 merge sonrası yeni main smoke/GitHub check/policy kontrolü, API35 (0 instrumentation), fiziksel cihaz kabulü açık.** |

## 9. Dokümantasyon ve demo

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| DOC-01 | PDF, ER/API, varsayımlar ve kurulum belgelerini tek güncel sözleşmede birleştirme | Tamamlandı | [PR #20](https://github.com/EminAly1/byteme-avatar-2026/pull/20): kök README, API/ER/veri modeli, requirements/assumptions, [release readiness](RELEASE_READINESS.md) ve [runbook](DEMO_RUNBOOK.md) güncel; zorunlu eksikler açıkça listeli. |
| DOC-02 | Tekrarlanabilir alış/dış üretim/EKP örnek kaydı | Tamamlandı | [app.demo](../backend/app/demo.py) ve [demo_sales_shipments.py](../backend/app/demo_sales_shipments.py) iki kez idempotent çalıştı; 85 paket 30/25/30 sevk ve 16 defter hareketi raporlandı. |
| DOC-03 | Üç görevin uçtan uca demosu ve alış/üretim/parçalama/lot/satış/recall raporları | Devam ediyor | [Final demo runbook](DEMO_RUNBOOK.md), [14:30 kayıt planı](FINAL_DEMO_SCRIPT.md): alış/üretim/kuzu/Android/lot recall/transfer/iade/rework/ikinci kademe, iki sentetik ML, uyarı/PDF aynı kurgusal DB'de çalıştı. **Gerçek ≤15dk jüri videosu çekilmedi/yüklenmedi; gönderim yok.** |
| DOC-04 | ML yöntem/örnek tahmin/doğruluk raporu | Tamamlandı | [Model A](../ml/MODEL_CARD_PRODUCTION.md), [Model B](../ml/MODEL_CARD_CUTTING.md), [metrikler](../ml/EVALUATION_REPORT.md) ve [API örneği](../ml/reports/demo.json); gerçek veri/kalibre aralık yok. |
| DOC-05 | Temiz makinede tek, tutarlı kurulum ve demo çalıştırma | Tamamlandı | [PR #20](https://github.com/EminAly1/byteme-avatar-2026/pull/20), [kurulum](../README.md), [runbook](DEMO_RUNBOOK.md): yeni Compose proje/volume, image, migration, iki ML ve MySQL/FastAPI/React healthy; ağ DNS kısıtında belgeli proxy/CA ile build. Bu bulutta kabul, tüm OS'lerde garanti değil. |

## 10. Yarışma teslimi

| ID | Görev | Durum | Kanıt / kalan iş |
| --- | --- | --- | --- |
| TES-01 | İlk üç PR ve ayrı checklist PR’ını main’e alma | Tamamlandı | [PR #1](https://github.com/EminAly1/byteme-avatar-2026/pull/1), [#2](https://github.com/EminAly1/byteme-avatar-2026/pull/2), [#3](https://github.com/EminAly1/byteme-avatar-2026/pull/3) ve [#4](https://github.com/EminAly1/byteme-avatar-2026/pull/4) main'e birleşti. Sonraki geliştirme PR'ları ayrı takip edilir. |
| TES-02 | Üç ana akış + kullanılabilir Kotlin uygulaması + iki zorunlu ML çalışmasının kabulü | Tamamlandı | [Task19 final kabul raporu](FINAL_RELEASE_READINESS.md): üç zorunlu iş akışı, çalışan Kotlin/Room Android API28 **4/4**, iki SYNTHETIC ML ve aynı DB üzerinde 427 backend/ML+83 web+34 ayrı Chromium ile **desteklenen yerel prototip kapsamı tamamlandı**. API35 instrumentation **0**, fiziksel cihaz yok; gerçek dünya ML ve üretim güvenliği kabulü iddia edilmez. Son main smoke TST-06'da açık. |
| TES-03 | Son kaynak/kurulum/örnek kayıt/test/doküman paketi ve temiz kurulumdan demo | Devam ediyor | [README](../README.md), [USER_GUIDE](USER_GUIDE.md), [FINAL_RELEASE_READINESS](FINAL_RELEASE_READINESS.md) ve [DEMO_RUNBOOK](DEMO_RUNBOOK.md): izolasyonlu temiz Compose, kurulum, seed, API28 debug APK ve final kabul belgeleri hazır. **GitHub Release/tag, erişilebilir APK yayın URL'si, gerçek video ve resmî teslim paketi açık.** |
| TES-04 | Final sensitive-data kontrolü, sürüm etiketi ve yeniden üretilebilirlik | Devam ediyor | [Task19 güvenlik/yeniden üretim kanıtı](final-release/acceptance.json): Gitleaks 0 bulgu, APK162 üye/36+36 bundle kontrolü, loopback/anahtar, iki ML checksum, Docker ReportLab, Alembic head ve restart sonrası 30 tablo hash eşit. **PR #35 merge sonrası tekrar kontrol, final sürüm etiketi ve public APK/artefakt yayın yok.** |
| TES-05 | **1 Kasım 2026 23:59 Europe/Istanbul** öncesi gönderim ve alındı doğrulaması | Başlanmadı | **Son tarih 1 Kasım 2026 23:59 Türkiye saati.** [E-posta taslağı](SUBMISSION_EMAIL_DRAFT.md) mevcut; public repo bağlantısı yerinde, **≤15 dakika gerçek video URL'si yok, e-posta gönderilmedi, alındı teyidi alınmadı**. Kayıtlı ekip üyesinin doğrulanmış organizasyon adresine gönderimi gerekli. |

## Bir sonraki kritik iş

Teslim için **Preview cihaz provası → yetkili Release/APK yayını → paketleme PR/main
incelemesi → 14:30 video/oturumsuz erişim → ekip gönderimi/alındı**. Lotlu satış,
parçalama ve kontrollü recall zaten mevcuttur; yeniden geliştirme açılmaz.
Backend'in sonraki üretim önceliği gerçek oturum/roller/RBAC ve TLS/operasyon
kabulüdür; bugünkü yerel teslimi geciktiren yeni özellik olarak eklenmez.

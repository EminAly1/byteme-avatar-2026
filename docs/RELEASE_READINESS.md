# Release readiness — Görev 12

İlk kabul **25 Ekim**, sonlandırma **26 Ekim 2026 (Europe/Istanbul)**. İlk main tabanı **`12dbb144497d3c35697a53debabbf218d53a0684`**; son güncel main **`ad5bfa3ed1e8401262db50238a1a4127a0326b62`**. PR #19 yalnız `docs/EXTRA_FEATURES_ROADMAP.md` ekledi; çalışma dalı fast-forward ile güncellendi, entegrasyon değişiklikleri korundu. PR #1–#18'in merge commit'lerinin bu main'in atası olduğu doğrulandı; başlangıç çalışma ağacı temizdi. [Git kanıtı](release-validation/initial-state.json). Çalışma dalı `feature/release-integration-v1`; main'e merge yapılmadı. AGENTS ve PROJECT_CHECKLIST değiştirilmedi.

**Yerel prototip demosu: GO. Bütün PDF gereksinimlerini karşılayan resmî teslim: NO-GO.** Genel depo transferi, müşteri iadesi/iptali ve rework eksiktir. Final video, resmî paket ve gönderim/alındı henüz yoktur. İnternet üretimi kullanıcı oturumu, roller ve TLS olmadan NO-GO. HTTPS üzerinden fiziksel cihaz bağlantısı da test edilmedi. Son tarih kullanıcı talimatıyla **1 Kasım 2026 23:59 Europe/Istanbul**; PDF'de tarih yoktur.

## Oturum yenilenmesi ve kanıt sınırı

26 Ekim ortam yenilenmesinde kaynak/diff, Docker image ve volume’ları, kayıtlı JSON/XML/PNG kanıtları ve Android host build çıktıları korundu. `/tmp` içindeki eski ham loglar, özel env dosyaları ve geçici Android JDK/SDK kayboldu. Özel env, mevcut durmuş release container yapılandırmasından değerler gösterilmeden kurtarıldı. Eski ham loglar yeniden oluşturulmuş gibi sunulmaz. Android cihaz/host koşuları bu sonlandırmada tekrarlanmadı; korunmuş XML/state/retry çıktıları ve APK hash’i doğrulandı. Backend/ML, npm, Chromium, Compose ve demo son kontrollerinin yeni çıktıları ayrıca kaydedildi. [Provenance](release-validation/finalization-state.json).

İlk son pytest koşusu MySQL container yeniden oluşturulurken başladı:3fail/32error/159pass, bağlantı kaybı. [Kesilen koşu](release-validation/backend-resume-interrupted.txt) korunur. Servisler healthy olduktan sonra aynı paket kod/test değişikliği olmadan194/194 geçti. Bu altyapı çakışması başarılı koşu diye sayılmaz.

## Kurulum kabulü

Yeni `avatar-release-v1` projesi ve **yeni** `avatar-release-v1_mysql_data` volume'u kullanıldı. Önceden mevcut kullanıcı DB/volume'ları silinmedi veya resetlenmedi. Core, migration, web, API28 ve API35 şemaları ayrıdır. Jüri şeması `avatar_release_demo_acceptance_test`, yalnız kurgusal kayıt içerir. Gerçek env/fixture dosyaları repo dışında 0600 izinleriyle tutuldu.

| Kontrol | Gerçek sonuç ve kanıt |
| --- | --- |
| Compose config/build | Config geçti. Normal build dış DNS nedeniyle başarısızdı; uygulama hatası sayılmadı. Build sırasında proxy ve doğrulanmış CA secret'ı kullanan override ile iki image sıfırdan üretildi. TLS kapatılmadı. [Build log](release-validation/compose-build.txt) |
| Üç servis | MySQL 8.0.46, FastAPI ve Vite birlikte healthy; Alembic head `dc9109a1f001`; iki model image içinde. Backend/frontend UID1000. [Son smoke](release-validation/compose-restored-final.json) |
| Ağ ve anahtar | Host publish yalnız 127.0.0.1:33326/8000/5173. Frontend backend'in ağ namespace'ini paylaşır, upstream literal127.0.0.1:8000 kalır. Container bind0.0.0.0 açık server opt-in'dir; Host/Origin kuralı sabittir. |
| Gerçek güvenlik istekleri | Browser key almaz; sahte istemci key'i proxy'de değiştirilir. Dış Host/Origin, origin'siz write ve cross-site istek403; doğrudan API anahtarsız401. |
| Host alternatifi | Aynı container MySQL + host loopback FastAPI/Vite ile health, ready, web, iki model, auth ve Host kontrolü geçti. [Smoke](release-validation/host-fallback.json), [tam demo tekrarı](release-validation/demo-host-fallback.json) |
| Migration | Temiz şemada upgrade; gerçek MySQL downgrade/upgrade ve metadata/FK/CHECK testleri tam regresyonda geçti. Startup Alembic kullanır, create_all kullanmaz. |

Build override yalnız image üretimine uygulanır. Üç uygulama servisi runtime'da host network kullanmaz. Android ADB'nin ayrı geçici **test aracı**, host loopback5037 kullanır; uygulama dağıtımı değildir. Override'sız normal DNS build'i bu ortamda başarılı sayılmadı. [Kurulum ve komutlar](../README.md), [runbook](DEMO_RUNBOOK.md).

## Test kabulü

| Paket | Geçen | Başarısız / atlanan / kapsam | Kanıt |
| --- | --- | --- | --- |
| Başlangıç main backend+ML | 181 | 0/0; değişiklik öncesi | [Başlangıç notu](release-validation/finalization-state.json) |
| Son backend+ML | **194 = 175 backend + 19 ML** | 0/0; gerçek MySQL8; bir Starlette/AnyIO deprecation uyarısı | [pytest](release-validation/backend-tests.txt) |
| Frontend ci/typecheck/build | Başarılı | Host ve image'da npm ci; premium src/CSS değişmedi | [typecheck](release-validation/frontend-typecheck.txt), [build](release-validation/frontend-build.txt) |
| Frontend unit/component | **45** | 0/0; eski43 korundu | [unit](release-validation/frontend-unit.txt) |
| Gerçek Chromium E2E | **15** | 0/0; eski14 + alışUI→SKT→DB→lot drawer | [Son E2E](release-validation/frontend-e2e.txt), [ilk kabul](release-validation/frontend/acceptance.json), [son artefaktlar](release-validation/frontend-final/) |
| Gerçek eksik model | **1** | 503 doğrulandı, sahte tahmin yok | [test](release-validation/frontend-missing-model.txt) |
| Android host | **32 yürütüm, 16 farklı test** | Debug+release; 0fail/error/skip; lint0issue; debug ve test APK build geçti | [JSON](release-validation/android-host.json), [Korunmuş XML/lint raporları](release-validation/android/host/) |
| Android API28 AOSP x86_64 | **4/4** | 0fail/skip; gerçek Kotlin→MySQL, Room, Keystore, offline | [JSON](release-validation/android/api28.json), [XML](release-validation/android/api28-results.xml), [replay/kalıcılık](release-validation/android/api28-state.json) |
| Android API35 AOSP x86_64 | **Sıcak tekrarda3/4** | İlk Gradle koşusu keşif öncesi ANR; tekrarda offline testi başarısız, tam kabul yok | [ilk sonuç](release-validation/android/api35.json), [retry](release-validation/android/api35-retry.json), [çıktı](release-validation/android/api35-retry.txt) |
| Fiziksel telefon / Safari / Firefox | Çalıştırılmadı | Doğrulanmadı | Açık risk |

Backend önceki181 testi korur; ek13 testin8'i demo sınırları,3'ü kârlılık,2'si deadlock kabulüdür. Bir test **gerçek InnoDB1213 deadlock** üretir; kurban transaction rollback, aynı komutun sınırlı retry'ı ve replay doğrulanır. İkinci test kontrollü driver1213 ile retry tavanını doğrular; gerçek deadlock testi diye sunulmaz. Stok/recall yarışları, maliyet dengesi, migration ve ML'nin defteri değiştirmemesi eski paket içinde geçti.

Frontend bu sürümde18 axe görünümünde0 otomatik ihlal, beş viewport ve gerçek ekran görüntüleri üretti. Görev11'in33 axe raporu tarihsel kanıttır; burada33 tarama tekrarlandı denmez. [Güncel artefaktlar](release-validation/frontend/). İlk seed'siz web denemesinde canonical lot bulunmadı; ayrı web şeması seed edildi. Gizli dosya testinde SPA200 davranışı görüldü; dar kapsamlı403 middleware eklendi ve son15 test geçti. Tasarım ve iş mantığı değiştirilmedi. 26 Ekim ilk sonlandırma koşusu14/15 geçti; aynı sevkiyat testi tek başına da başarısızdı. Native modal odağı hazır olmadan Escape gönderilmesi görüldü. Test, odak hazır olmasını ve Escape sonrasında pencerenin kapanmasını ayrıca doğrulayacak şekilde senkronize edildi; assertion kaldırılmadı, sabit sleep eklenmedi. [İlk hata](release-validation/frontend-e2e-first-finalization.txt) ve [görüntü](release-validation/frontend-final-failure/screenshot.png) korunur; son tam koşu ayrıca kaydedilir.

API28'in ilk koşusunda uzun UI adımlarından sonra testin tekrar kullandığı HTTP istemcisinde EOF oluştu. Server'da gerçek satış vardı; eski MySQL/Room verisi korundu. Yalnız iki **salt-okunur test stok kontrolü** bağımsız istemciye geçirildi; uygulama POST/retry/Room kodu ve assertion'lar korunur. Yeni izole şemada4/4 geçti. [İlk sonuç](release-validation/android-api28-first-attempt.json) saklanır.

API35 ilk koşusunda Android ActivityManager, uygulama başlangıcı tamamlanmadığı için süreci ANR ile öldürdü;0 test keşfedildi. Sıcak başlangıçla doğrudan AndroidJUnitRunner tekrarı gerçek satış/recall, SQLite ve Keystore testlerini geçirdi. **OfflineDeviceTest.kt:35**, bağlantının false olmasını60 saniye beklerken başarısız oldu. Sonradan Wi-Fi/data kapalı dumpsys kontrolünde default ağ yoktu; callback/state zamanlamasının kök nedeni kesinleştirilmedi. Test gevşetilmedi veya skip edilmedi. API35 offline davranışı açık platform riski; eski Google APIs35 image ve fiziksel telefon ayrıca doğrulanmadı. KVM yoktu; yazılım emülasyonu kullanıldı.

APK Git'e eklenmez: `android/app/build/outputs/apk/debug/app-debug.apk`; SHA256 **`4cdb02856b54841bd71036b82976f0e24011c73532f57da9a12e022af0c9d804`**. Bu hash mevcut APK'ye aittir; yeni build değişebilir.

## Birleşik demo

[HTTP demo](release-validation/demo.json), [Kotlin sonrası tam tekrar](release-validation/demo-after-android.json) ve [API28 state](release-validation/android/api28-state.json) aynı jüri şemasına aittir. React E2E ayrı web şemasında çalıştı. API35 denemesi de ayrı şemadadır; [cihaz sonrası replay](release-validation/demo-api35-after-android.json) onun kayıtlarını korur.

- Girdiler ve hizmet: **1.543,50 EUR / 85 paket**, gösterimEKP **18,16 EUR**. Hassas hesap ve toplam dengesi korunur;85×18,16'dan toplam üretilmez.
- İki ayrı kuzu, miktar/değer dağıtımı: her biri **25kg →22kg + açıklamalı3kg**, **287,50 EUR**. PDF'nin351EUR çelişkisi açıklanır; kurgusal fark gerçek fire politikası sayılmaz.
- Gerçek Kotlin Compose satışında value but **6→5kg**. Aynı key/body aynı satış, satır ve hareketi döndürür. Room yeniden açma ve process restart sonrası key/body/state korunur. Offline taslak server satışı oluşturmaz.
- SUC85 paket MarketA/B/C'ye **30/25/30**. Satışa bağlı sevkiyat ikinci kez stok düşmez. ET→URT→SUC gerçek FK ile ileri/geri izlenir; kayıtlı alıcı/contact snapshot'ları gösterilir, bilinmeyen market kalanı/ikinci kademe uydurulmaz.
- ET recall ve ayrı kuzu kaynağı recall; stale Android satışı409LOT_BLOCKED/NEEDS_ACTION, yeni satış veya stok değişimi yok.
- İki gerçek tahmin API'si, kapanmış85/22 gerçek sonuçları ve sapmaları; prediction kaydı kesin defter hesaplarını değiştirmez.
- Gerçek commit sonrası ilk satış cevabı test proxy'sinde düşürüldü; aynı key/body ile **aynı satış** döndü. Tam akış iki kez, Kotlin'den sonra da tekrarlandı;24 tablonun satır sayıları/hash'leri aynı. Kör yeni key kullanılmadı.
- Kârlılık GET,24 tablo hash'ini değiştirmedi. MarketA:750 gelir−544,764706 tüketim maliyeti=205,235294EUR brüt kâr; gösterim205,24; marj%27,364706. Vergi/iskonto/genel gider yok; şirket net kârı değildir. Özel React kâr paneli henüz yok.

Tüm demo şeması **KURGUSAL/SYNTHETIC**; [manifest](release-validation/demo-records.json) her kayıt kimliğini etiketler. Eski seed payload'ları idempotency kayıtlarını bozmamak için değiştirilmedi. Gerçek kişi iletişimi kullanılmadı; örnek adresler `.invalid` alanındadır.

## ML ve güvenlik

[İlk reproducibility](release-validation/ml-reproducibility.json), [26 Ekim tekrar üretimi](release-validation/ml-final-reproducibility.json): seed 202609; model başına 600 SYNTHETIC kayıt,360/120/120 split; gerçek tarihsel kayıt 0. İki dış retrain byte-identical; CSV hash'leri, kayıtlı ağırlıklar ve artifact SHA doğrulandı. Baseline/Ridge MAE/RMSE ve metadata raporda. Eski modellerin üstüne yazılmadı. Gerçek işletme başarımı veya kalibre güven aralığı iddiası yok.

[Son güvenlik taraması](release-validation/security-final.json): mevcut Git ref/geçmişinde Gitleaks8.24.3 **0 sızıntı**; güncel nonignored kaynak export'unda0. Gerçek özel credential byte'larıyla kaynak, frontend dist, **açılmış iki APK içeriği**, image config/history tarandı:0 eşleşme. Bu, bilinmeyen bütün secret'lar için garanti değildir.

Geniş yerel dizin taraması, ignore edilen `.env` ve `backend/.env.runtime` içinde3 yerel credential buldu. Dosyalar önceden mevcuttu,0600 ve Git'te/geçmişte değiller. Değerler raporlanmadı; dosyalar silinmedi veya değiştirilmedi. Yeni demo dış env'de farklı üretilmiş değerler kullanır. Source/build'e veya paylaşılan loga taşınmaları halinde ilgili anahtarların yenilenmesi gerekir; mevcut kanıt Git sızıntısı göstermez. Bütün yerel disk için0 bulgu denmez. Yeni kayıt manifestindeki primary_key başlığı altında65 kurgusal UUID genel scanner tarafından yanlış eşleşti; gerçek credential byte eşleşmesi0 idi. Manifest kimliği identity_columns/identity_values ile açıkça ayırır; scanner allowlist eklenmedi. [İnceleme](release-validation/security-manifest-review.json).

X-API-Key yalnız yerel demo istemcisini doğrular. Kullanıcı oturumu/roller ve internet TLS dağıtımı uygulanmadı. Demo CLI yalnız literal loopback ve ayrı `*_test` ortamını kabul eder;8 test bunu doğrular. User DB/volume'ları korunur.

## P0 / P1 / P2

| Seviye | Durum | Teslim etkisi |
| --- | --- | --- |
| P0 | **Giderildi:** Compose key eksikliği, proxy upstream uyumsuzluğu, dosya izinleri, startup migration ve model taşıma | Üç servis healthy; browser key almaz; loopback sınırı korunur |
| P0 | **Giderildi:** kayıp cevap ve demo replay kabulündeki güvenilirlik açığı | Gerçek HTTP/Kotlin aynı-key tekrarları ve24 tablo hash eşitliği; stok/yarış regresyonları |
| P1 | **Giderildi:** backend VKP/brüt kâr/marj | Kesin SaleLine maliyetinden salt-okunur GET,3 MySQL testi; özel web paneli açık |
| P1 | **Giderildi:** deadlock ve SKT kanıtı | Gerçek1213+retry, ayrı kontrollü retry tavanı; gerçek alışUI→DB→lot SKT |
| P1 | **Açık:** genel depo transferi, müşteri iadesi/iptali ve rework | PDF'nin istediği lot hareketlerinin tamamı mevcut değil. Satış/sevkiyat, üretim hammadde iadesi ve fire bunların yerine geçmez |
| P1 | **Açık/koşullu:** ikinci kademe dağıtım | Birinci alıcılar kesin; ikinci kademe kayıt/API yok. Null doğru, zincir kabulü tamamlanmadı |
| P1 | **Açık:** API35 offline kabulü |3/4 geçti; network state timeout çözülmedi. Demo kabulü API28 ile sınırlı |
| P1 | **Açık:** final video, resmî paket/tag ve gönderim/alındı | Test sonucu resmî teslim kanıtı değildir |
| P2 | **Açık:** gerçek kullanıcı auth/RBAC/TLS | Yerel demo engeli değil; internet üretimi içinP0 engel |
| P2 | **Açık:** fiziksel telefon, Safari/Firefox, diğer API35 varyantları | Test edilmedi; Chromium emülasyonu veya API28 bunların yerine geçmez |
| P2 | **Açık:** resmî fatura/proforma/irsaliye PDF çıktısı ve genel filtreli raporlar | REST satış/sevkiyat kayıtları resmî belge üretimi değildir; [opsiyonel yol haritasında](EXTRA_FEATURES_ROADMAP.md) ayrıca planlı, bu görevde başlanmadı |
| P2 | **Açık:** gerçek veriyle model genellemesi, yük/ölçek, tüm transitif kilitler ve image pinning | Sentetik prototip sınırları |

Açık yerel-demoP0 tespit edilmedi. Resmî PDF tesliminin NO-GO nedeni başlıca eksik hareket akışları ve teslim materyalleridir. Sonraki en kritik backend işi: **genel depo transferi ve müşteri iade/iptalini ters hareket, gerçek lot FK, aynı transaction/kilit/idempotency ve recall yarış testleriyle eklemek; ardından rework**. Ayrı küçük PR'lar kullanılmalı.

## Checklist önerileri — dosya değiştirilmedi

Bunlar review önerisidir; `docs/PROJECT_CHECKLIST.md` bu branch'te değiştirilmedi. Tamamlandı yalnız belirtilen kabul kapsamıdır.

| ID | Önerilen durum | Kanıt / kalan |
| --- | --- | --- |
| ALT-06 | Tamamlandı (yerel Compose) | Build workaround belgeli;3 servis/migration/model/loopback smoke |
| ALT-07 | Başlanmadı | Gerçek oturum ve roller yok |
| URT-07 | Devam ediyor | Backend formülleri ve3 test var; özel frontend gösterimi yok |
| URT-08 | Tamamlandı | Gerçek deadlock ve ayrı retry tavanı testi |
| KUZ-06 | Tamamlandı (PDF çelişkisinin açıklaması) |25×11,50=287,50;22+3 açıklamalı demo. Gerçek fatura/işletme sınıfı onayı iddiası yok |
| LOT-02 | Tamamlandı | Gerçek SKT alışUI→DB→lot drawer kabulü |
| LOT-05 | Devam ediyor | Genel transfer, müşteri iadesi/iptali, rework eksik |
| LOT-10 | Başlanmadı / kapsam açıklaması gerekli | İkinci kademe kayıt yok; null döndürmek zincir uygulaması değildir |
| WEB-06 | Başlanmadı | Güvenli yerel proxy üretim oturumu/dağıtımı değildir |
| TST-06 | Devam ediyor | PR1–19 main ve yerel aday regresyonu geçti; bu releasePR merge ve GitHub check/policy kabulü yok |
| DOC-01 | Tamamlandı (bu sürüm sözleşmeleri) | README/ER/API/requirements/assumptions güncellendi |
| DOC-05 | Tamamlandı (bu bulutta yeni Compose volume) | Temiz image/migration/model ve host fallback; her OS için garanti değil |
| TES-02 | Devam ediyor | Üç çekirdek akış+Kotlin+2ML birleşik kanıtlı; eksik hareketler/final video var |
| TES-03 | Devam ediyor | Kaynak/belge/runbook/test kanıtı hazır; review merge, resmî paket ve video bekler |
| TES-04 | Devam ediyor | Kaynak/build/geçmiş taraması ve ML tekrar üretimi geçti; resmî tag/paket yok |
| TES-05 | Başlanmadı | Gönderim/alındı yapılmadı |

## Video ve GitHub

[DEMO_RUNBOOK](DEMO_RUNBOOK.md),11 adım, gerçek Kotlin fixture önkoşulları, mevcut satışın güvenli tekrarı, ayrı test DB'leri ve video hazırlığını verir. Önce smoke, sonra onaylı Kotlin/recall ve web maliyet/ML ekranları; secret ekranları kayda alınmaz. Resmî paket, video/public erişim, kayıtlı ekip üyesinin gönderimi ve alındı kontrolü bekler. E-posta gönderilmedi.

Bu branch test edilen değişikliklerle commit/push edilir ve main hedefli PR açılması denenir.403 halinde branch/compare bağlantısı verilir. Main'e merge yetkisi bu görevde kullanılmaz. PR sonucu son raporda belirtilir; açıkP1 kapsamı kapanmadan tüm yarışma gereksinimleri tamamlandı sayılmaz.

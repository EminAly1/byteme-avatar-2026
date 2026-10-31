# AVATAR — Son teslim ve paketleme kabulü

**31 Ekim 2026 · ByteMe.** Son teslim: **1 Kasım 2026 23:59 Türkiye saati**.
[İndir/kur](INDIRME.md) · [Kullanım](USER_GUIDE.md) · [14:30 video](FINAL_DEMO_SCRIPT.md)
· [Makinece okunabilir kısa kabul](final-delivery/acceptance.json).

## Kaynak ve GitHub durumu

- Paketleme çalışmasının başlangıç `origin/main` tabanı: **`f2a0a156d769793b16f17d5de09c5a0393f69aae`**,
  PR #42 merge commit'i; Görev 21/#37, 22/#38, 23/#40, 24/#41, 25/#42 ataları doğrulandı.
- Paketleme çalışma branch'i **`feature/final-delivery-packaging`**. Android/web/backend/ML aynı checkout;
  backend/frontend/ML iş kodları ve eski kanıtlar değiştirilmedi.
- Paketleme kod commit'i **`3f2c5db4d02b93ed3e9f3ba21e15fd8e6245fb6b`**, GitHub'a push edildi.
  Son doküman commit'i için branch başını kullanın; APK'nin kodu bu commit'tir.
- **31 Ekim birleşim güncellemesi:** [PR #43](https://github.com/EminAly1/byteme-avatar-2026/pull/43) `main` dalına alındı; merge **`81155d2c1b4bf1a200e11c37b9f223c5ec14afce`**. Birleşim sonrası GitHub check/policy ve fiziksel cihaz kabulü hâlâ bekliyor.
- `v0.1.0-preview.2` uzak etiketi boştu; gerçek APK ile `gh release create` denendi.
  Releases API kontrolünde **Forbidden**: Release/tag/asset oluşmadı; gerçek indirme URL'si yok.
  Yerel APK ve manuel yayın adımları [INDIRME](INDIRME.md) içinde.

## Bu sürümde yeniden yapılan minimum kabul

| Kontrol | Sonuç | Gerçek kapsam |
| --- | --- | --- |
| React | typecheck + production build başarılı | Mevcut node_modules; npm ci/unit/Chromium ve responsive matris yeniden koşulmadı |
| MySQL/FastAPI | MySQL 8.0.46; HTTP `/health` 200 ve `/health/ready` 200 | Yeni `avatar-final26-mysql`, yalnız 127.0.0.1:33426; kaynak API 127.0.0.1:8026, ready şeması `avatar_final26_test` |
| Alembic | upgrade head + check başarılı, fark yok | `f1507a26b001`; ayrı `avatar_final26_core_test` fixture migration'ı da aynı head'e geldi |
| Kontrollü recall | **5 passed** | Salt-okunur stabil önizleme; yanlış kaynak reddi; stale etki409→yeniden onay→LOT_BLOCKED; eşzamanlı aynı-key replay; hata sonrası tam rollback |
| PDF/MySQL | **3 passed**, toplam backend **8/8**,0 failure/error/skip | Gerçek API handler/TestClient→InnoDB→ReportLab; Türkçe PDF, 30 tablo değişmezliği, değişen kaynak409. Bir Starlette dependency deprecation uyarısı var |
| PDF dosyası | application/pdf, `%PDF-`, **2 sayfa/49.016 byte**, pypdf strict açıldı | Ayrı gerçek üretim; öncesi/sonrası30 domain tablo hash'i eşit; cihaz PdfRenderer testi değildir |
| ML | İki JSON+SHA256 doğrulama/yükleme; birer tahmin başarılı | Üretim 85,866219 paket/tahmini EKP 17,689378; kesim 21,797561 kg toplam. Gerçek 85 paket/EKP 18,16 ile karıştırılmaz |
| Android host | **31/31**,0 failure/error/skip | `testDebugUnitTest` yeniden çalıştı; test silme/skip/assertion gevşetme yok |
| Android lint/build | debug + preview **0 lint issue**, assembleDebug ve assemblePreview başarılı | Debug APK değişmediği için assembleDebug UP-TO-DATE; yeni Preview gerçekten derlendi. Compile SDK35 cihaz kabulü değildir |
| Cihaz | **API28/fiziksel: yapılmadı; API35: NO ACCEPTANCE / 0 test** | Hazır cihaz/ADB yok; emülatör kurulmadı/API35 başlatılmadı. Eski API28 4/4 bu APK'nin kabulü değildir |
| Güvenlik | diff check, Gitleaks ve özel dosya/değer taraması | APK/özel env/Keystore/raw log Git dışında; Preview APK'de özel key/env/fixture ve güncel sır eşleşmesi yok |

PDF SHA256: `0bfc9f2419ccc55f008b44a2852807febc6f6612427d597dae882003f3d57b09`.
Yalnız yeni `*_test` şemaları kullanıldı; pytest demo şemasından ayrıldı. Eski
kullanıcı DB/volume'ları silinmedi. Docker backend/frontend image'ları ve tüm eski
suiteler bu görevde yeniden build/test edilmedi; önceki sonuçlar aşağıda tarihleriyle korunur.

## Android imza güvenliği — B seçildi

Mevcut özel araç dizininde yalnız yeni debug keystore bulundu; özgün eski
sertifikaya karşılık gelen anahtar mevcut değil. Eski APK sertifika SHA256'sı
`21506045a6ba21558ddbd67d3bd5b65133c0d992189377e9ed833ce60a8e62de`,
mevcut anahtarın sertifikası
`b9fbe028ac6c63fc1f873fbe446a0693be3f6260d57807f89d75ad6ef0418f9f`.

**AVATAR Preview**, `com.byteme.avatar.preview`, **0.1.0-preview.2/code1**,
minSdk26/target35; **17.002.344 byte**, debug imzalı ve debuggable demo varyantıdır.
APK: `/workspace/artifacts/AVATAR-Preview-v0.1.0-preview.2.apk`.
SHA256: **`bd530439c53cdd1675f91f038aa9d0036b3ae02162dca8544d531f7337d856cf`**.

Namespace/Activity/ikon ve standart `com.byteme.avatar` debug paketi korunur.
Preview farklı paket/UID ve FileProvider authority ile ayrı veri alanına kurulacak
şekilde paketlendi; **telefonda kurulum denenmedi**. Eski uygulama uninstall,
pm clear, veri silme veya zorla overwrite yapılmadı. Eski Room/outbox/Keystore
Preview'a otomatik taşınmaz. Frozen key/body, şema ve satış mantığı değiştirilmedi.
Native PDF çizimi, SAF/paylaşma, canlı uyarı/stok/satış ve veri koruma cihaz provası bekler.

## Karar ve kalan insan adımları

| Alan | Karar | Kalan |
| --- | --- | --- |
| Yerel web/backend/ML ve APK paketleme | **GO — belirtilen kısa kapı kapsamında** | 31 Ekim testleri yukarıda; bütün eski suite yeniden kabulü iddia edilmez |
| Güncel Android canlı gösterim | **Doğrulama gerekiyor** | Güvenli yeni Preview kurulum/bağlantı; stok/uyarı/satış/offline ve native PDF provası |
| Herkese açık APK dağıtımı | **NO-GO** | Release API Forbidden; yetkili ekip gerçek asset yayımlayıp indirme/hash'i doğrulamalı |
| Eksiksiz yarışma teslimi | **NO-GO** | Fiziksel cihaz provası, gerçek ≤15dk video/link, gönderim/alındı yok |
| İnternete açık üretim | **NO-GO** | Kullanıcı oturumu/RBAC/TLS, operasyon ve gerçek veriyle ML kabulü yok |

ML toplam **6.000 SYNTHETIC (3.000/model), 0 gerçek tarihsel kayıt**. V2 bazı ortak
metriklerde ve eski sabit testte geriledi; genel doğruluk artışı kabul edilmedi
([değerlendirme](../ml/EVALUATION_REPORT.md)). Proforma resmî e-Fatura/e-Arşiv değildir.
**Video çekilmedi/yüklenmedi; e-posta gönderilmedi; alındı teyidi yok.**
[14:30 plan](FINAL_DEMO_SCRIPT.md), [gönderilmemiş taslak](SUBMISSION_EMAIL_DRAFT.md).

## Main temizliği için son PR raporu

İnceleme kapsamı: ayrı Android Preview varyantı ve son teslim belgeleri; yeni iş
özelliği/şema değişikliği yok. APK/anahtar/özel env/raw log kaynak commit'ine alınmaz.
Kısa kapı başarılı; [PR #43](https://github.com/EminAly1/byteme-avatar-2026/pull/43) GitHub bağlantısıyla açılıp `main` dalına normal merge edildi. İlk Codex PR denemesi GraphQL **Forbidden** almıştı; bu sorun sonradan çözüldü. **Birleşim sonrası tam CI, cihaz ve GitHub check/policy kabulü yeniden yapılmadı.** Aşağıdaki rapor **28 Ekim tarihsel kanıtıdır**; sayaçları
31 Ekim testleriyle toplanmaz ve yeni APK cihaz kabulü olarak kullanılamaz.

---

## Tarihsel rapor — 28 Ekim / Görev19

**28 Ekim 2026, Europe/Istanbul.** Test edilen main tabanı **`02a080677dee59a3940ad232d4fa716c92a84469`**. PR #1–#34'ün 34 normal merge commit'i bu tabanın atasıdır. Çalışma dalı `feature/final-release-acceptance`; main'e merge veya erken final tag yapılmadı. [Makinece okunabilir kabul özeti](final-release/acceptance.json).

| Karar | Sonuç | Sınır |
| --- | --- | --- |
| Yerel jüri demosu | **GO** | Loopback Compose, KURGUSAL/SYNTHETIC veri, desteklenen API28 Android kabulü; API35 garanti edilmez |
| Eksiksiz yarışma teslim paketi | **NO-GO** | Gerçek ≤15dk video/link, review/main birleşimi, final tag/paket ve gönderim/alındı eksik; API35 riski açık |
| Gerçek internete açık üretim | **NO-GO** | Gerçek kullanıcı oturumu, RBAC/TLS, üretim güvenliği/operasyon ve gerçek veriyle model kabulü yok |

Son teslim ekip talimatıyla **1 Kasım 2026 23:59 Europe/Istanbul**. 30 Ekim aday hedefi, 31 Ekim son kontrol/video payıdır; başarılı test gönderim kanıtı değildir.

## Temiz kurulum ve gerçek düzeltmeler

Yeni **avatar-final19** Compose projesi / **avatar-final19_mysql_data** volume'u; önceki **15 volume korundu**. Demo `avatar_final19_demo_test`; yıkıcı pytest `avatar_final19_core_test`, migration `avatar_migration_test`; legacy/operasyon, anomali, PDF, eksik model ve API35 için ayrıca *_test şemaları. Eski Task13–18 ve işletme şemaları resetlenmedi. Özel env/fixture/CA/SDK yalnız repo dışında.

Normal `--no-cache` Docker build DNS çözümlemesinde başarısız oldu. Mevcut `release_env build-proxy` ile host build ağı + doğrulanmış CA secret'ı kullanılarak backend/frontend image'ları yeniden üretildi. **TLS doğrulaması kapatılmadı.** Runtime uygulama servisleri host network kullanmaz. Eski Task18 Vite süreci doğrulanıp yalnız o süreç durdurularak 5173 çakışması çözüldü.

Yalnız kabulde görülen üç küçük araç düzeltmesi yapıldı; stok/maliyet/lot/recall/ML/Android iş kodları yeniden yazılmadı:

1. `tools/verify_compose.py` eski `dc9109a1f001` sabitini bıraktı; container Alembic kaynak head'i ile DB head'i karşılaştırılır. Loopback HTTP kontrolleri dış proxy kullanmaz.
2. `tools/release_env.py run`, miras alınan büyük/küçük harf HTTP proxy bypass listesine 127.0.0.1/localhost/10.0.2.2 ekler. Legacy seed'in yerel anahtarlı istekleri dış proxy'ye gitmez.
3. `app.demo_documents` varsayılanını Görev18'e özel 8009 yerine standart yerel **8000** yapar; açık `AVATAR_API_BASE_URL` desteği korunur.

README ve eski readiness/runbook güncellendi; tarihsel kanıtlar korundu. PROJECT_CHECKLIST, EXTRA_FEATURES_ROADMAP, AGENTS, migration/test kaynakları, model/font/lisans ve Gradle wrapper silinmedi/değiştirilmedi. Eski log/PNG'ler doküman bağlantılarıyla tarihsel kanıttır; Release taşıma yetkisi/altyapısı olmadığı için kanıt kaybettirecek temizlik zorlanmadı. Yeni ham log/JUnit/PDF/PNG/SDK dosyaları Git'e alınmadı.

## Docker kabulü

- **MySQL 8.0.46, FastAPI ve React/Vite healthy.** Yayımlanan portlar yalnız **127.0.0.1:33330, :8000, :5173**. Backend/frontend root olmayan kullanıcıyla çalışır; frontend backend ağ namespace'ini paylaşır.
- Alembic head **`f1507a26b001`**; temiz upgrade ve `alembic check` başarılı, metadata farkı yok. Yeni şema/migration eklenmedi.
- İki JSON modeli image içinde `load_model()` checksum/format/provenance kontrolünden geçti. Her ikisi **SYNTHETIC**, gerçek tarihsel veri0; gerçek dünya doğruluğu iddia edilmez.
- **ReportLab5.1.0**, DejaVu Regular/Bold ve dağıtım lisansı container içinde erişilebilir. PDF'ler gerçek Docker API'sinden `application/pdf` olarak üretildi; host-only başarı değildir.
- Frontend image içinde gerçek runtime API anahtarı mevcutken typecheck/build yapıldı; **36 build dosyasında anahtar yok**. Proxy yabancı Host/Origin/cross-site/origin'siz yazmayı403, doğrudan API anahtarsız isteği401 döndürdü.
- Yeni MySQL container restart'ından sonra bütün **30 domain tablosunun hash'i aynı**; aynı volume ve hazır servisler korundu.

## Birleşik testler

| Paket | Gerçek sonuç | Kapsam / sınır |
| --- | --- | --- |
| Backend + ML | **427 passed = 408 backend +19 ML**, 0 failure/error/skip | Otomatik keşif427; tüm `tests ml/tests` tek tam koşu,326,04sn; gerçek yeni MySQL instance |
| Frontend npm ci/typecheck/build | Başarılı | İlk npm cache'i salt-okunur home yüzünden başarısızdı; repo dışı yazılabilir cache ile temiz kurulum geçti. Host ve container build doğrulandı |
| React unit/component | **83 passed**, 0 failed/skipped | Bütün mevcut paket |
| Normal Chromium paketleri | **33 farklı senaryo kabul edildi** | Eski/operasyon26 + anomali4 + belge3; aynı kaynak/image, fixture çatışmasını önlemek için ayrı test şemaları |
| Gerçek missing-model profili | **1 passed** | Ayrı host API8002 + otomatik Vite, gerçek503; model silinmedi veya sahte tahmin kullanılmadı |
| Android JDK/wrapper | Başarılı | Temurin17.0.17+10 java+javac; wrapper8.10.2 JAR resmî checksum eşleşti, distribution checksum pin'i kullanıldı |
| Android host | **32 yürütüm /16 farklı test**, 0 failed/error/skipped | Debug+release; aynı kaynakla kaynak değiştirmeden tekrar geçti |
| Android lint / APK | Başarılı; **0 lint issue** | Lint analizi ayrıca yeniden çalıştırıldı; debug ve androidTest APK güncel koddan üretildi |
| Android API28 AOSP x86_64 | **4/4**, 0 failed/skipped | Gerçek Kotlin→Docker FastAPI→MySQL, UI, Room reopen, Keystore, offline;268,56sn |
| Android API35 AOSP x86_64 | **Kabul yok;0 instrumentation testi yürütülebildi** | Boot/ADB oldu; package/activity servisleri ilk kurulumda Broken pipe/NPE, sıcak APK kurulum tekrarı “Can't find service: package”. Önceki60sn offline timeout riski kapanmadı |
| Fiziksel cihaz / Firefox / Safari | Çalıştırılmadı | Emülatör/Chromium bunların yerine geçmez |

İlk legacy browser koşusu **24 passed,1 failure+1 error** idi: dış HTTP proxy yüzünden canonical seed403 almış ve ET/SUC kayıtları hazırlanmamıştı. Loopback bypass ve seed düzeltildi; **yalnız iki etkilenen test** aynı assertion'larla tekrar geçti. Böylece **34 farklı Chromium senaryosunun tamamı** (33+1) kabul edildi; ilk hatalar gizlenmedi,36 ayrı başarılı test iddia edilmez.

İlk Android debug host koşusu15/16 geçti; ComposeSmokeTest diyalogda AppNotIdleException verdi. İki yazılım emülatörü duraklatılarak kaynak/test değişikliği olmadan debug+release32/32 geçti; ilk XML/log repo dışında korundu. API28 native tam4/4 ayrıca geçti. API35 başarısız kurulum, geçmiş Task12'deki3/4 ile birleştirilip bugünkü başarı gibi sunulmaz. KVM yoktu; geçici SDK/JDK ve ayrı loopback ADB test container'ı kullanıldı. Test silinmedi, skip eklenmedi veya assertion gevşetilmedi.

## Tek demo veritabanındaki iş zinciri

Mevcut demo araçları yeniden kullanıldı; yeni muhasebe motoru yazılmadı. Bütün kayıtlar KURGUSAL/SYNTHETIC manifestiyle işaretlidir.

- **ET→URT→SUC:**970+48+58+467,50=**1.543,50 EUR**,85 paket, gösterim EKP**18,16**; gerçek input/output/lot FK'leri.
- **Kuzu:**25→22+3 kg açıklanmış fark, **287,50 EUR**, miktar/değer reçeteleri ve parça lotları. PDF'deki351EUR tutarsızlığı korunarak açıklanır.
- **Kotlin:**aynı main demo şemasında value but **6→5 kg**, tek satış/satır/hareket; aynı key/body replay aynı satış. Recall sonrası NEEDS_ACTION/LOT_BLOCKED, offline taslak outbox/kesin satış oluşturmaz. Process restart sonrası Room key/body/state ve merkezî hash korunur.
- **Transfer/iade/iptal:**transfer anında20→13/7kg; ardından gerçek sevke bağlı2kg iade ve uygun sevksiz satış iptali, yalnız karantina. 13/7 ile sonraki final bakiyeler karıştırılmaz; nakit iadesi iddia edilmez.
- **Rework:**10→9,5+0,5kg açıklanmış fark;100+15=**115 EUR**; yeni lot/soy bağı, kaynak/çıktı recall ve satış reddi.
- **İkinci kademe:**Market A/B/C30/25/30, A→X**12** kayıtlı; şirket sevkiyatı**85** kalır. Tahsis edilmemiş18, bilinmeyen market fiziksel stoğu değildir.
- **İki ML ve uyarı:**kayıtlı tahmin/posted sonuç, sentetik sınırlar; birleşik demoda**19 uyarı** (15 kritik+4 uyarı, altı kod). Farklı demolar birleştiği için sadece Task17'nin altı satırı beklenmez. %15 ve düşük stok eşikleri açık demo etiketlidir.
- **PDF:**Market A750EUR/1sayfa; kısmi iade625→575EUR, tam iade750→0 ve iptal15,98→0 ayrı gösterilir; uzun45kalem/2bağlı sevkiyat **138,60EUR/8A4sayfa**. Türkçe gerçek dosyalar pypdf strict parser ile açıldı. İç maliyet/kâr müşteri PDF'sinde yoktur; resmî mali belge değildir.

Kayıp satış, rework kapanışı ve dağıtım cevabı sonrası aynı key/body ile aynı kayıt döndü. Bütün mevcut demo modülleri Kotlin kabulünden sonra tekrar çalıştırıldı; GET/uyarı/PDF ve tam senaryo replay'i yeni kesin kayıt oluşturmadı. Ardından MySQL restart'ı da aynı30tabloyu korudu. Son ortak SHA256:

`9b31d27b070bc3f4267c35ab29c141a6c0f340e2efffe78d3fadde5095f686f5`

## APK ve paylaşım

- Yol: `android/app/build/outputs/apk/debug/app-debug.apk`
- Boyut: **17.608.683 byte**; package **com.byteme.avatar**, minSdk**26**, target/compileSdk**35**, version0.1.0/code1.
- SHA256: **`dea339c1fb9a1bcfddf61227a512c530310431d570957cda76b3695c7341b33e`**.
- Bu **debug APK**; gerçek release imzalama anahtarı üretilmedi veya varmış gibi sunulmadı. API28 kabulü güncel APK ile yapıldı.
- GitHub Releases API erişimi Forbidden olduğu için uzak APK/Release yayımlanamadı. Kaynak ağacına APK commit edilmedi. Kullanıcıya aynı hash'li ayrı indirme artefaktı hazırlandı; yerel üretim/yükleme komutları [USER_GUIDE](USER_GUIDE.md) içinde.

## Güvenlik, dokümanlar ve açık işler

APK'nin162 ZIP üyesi, host36 ve container36 build dosyası gerçek gizli değerlerle kontrol edildi:0 eşleşme. Gitleaks8.24.3 ile516 kaynak dosyası ve bütün mevcut yerel Git geçmişi sıfır bulgu verdi;10 gerçek gizli değerin kaynakta byte eşleşmesi0. `.env`, fixture, Keystore ve PDF/loglar kaynak Git'e alınmadı. Container port/proxy/model/font/lisans/schema kabulü geçti. Bilerek erişilemez dış proxy miras alınırken bile loopback health200 regresyonu geçti. Son commit sonrasında geçmiş taraması tekrar edilir. X-API-Key üretim rol sistemi değildir.

[USER_GUIDE](USER_GUIDE.md), güncel [DEMO_RUNBOOK](DEMO_RUNBOOK.md), **14:30** [FINAL_DEMO_SCRIPT](FINAL_DEMO_SCRIPT.md) ve [SUBMISSION_EMAIL_DRAFT](SUBMISSION_EMAIL_DRAFT.md) hazır. Repo ve raw README28Ekim'de oturumsuzHTTP200 verdi. **Video çekilmedi/yüklenmedi; gerçek video URL'si yok. E-posta gönderilmedi, alındı teyidi yok.** Taslaktaki alıcı/video/sonmain/tag yer tutucularını ekip doğrular.

| Öncelik | Güncel durum |
| --- | --- |
| Yerel P0 | Açık yerel iş akışı engeli bulunmadı; stale migration, yanlış demo portu ve loopback proxy/seed sorunları giderildi |
| P1 | API35 platform kabulü/önceki offline riski; PR/main review ve son CI/policy; gerçek video/link, tag/paket ve gönderim/alındı |
| P2 / üretim için P0 | Gerçek auth/RBAC/TLS, fiziksel cihaz/diğer tarayıcılar, operasyon/backup/yük ve gerçek veri model genellemesi |

## Checklist durum önerileri — ortak dosya değiştirilmedi

| ID | Kanıtlı öneri | Kalan |
| --- | --- | --- |
| TST-06 | Devam ediyor | Main tabanında yerel birleşik427/83/34 ve API28 kabulü var; bu PR merge sonrası GitHub check/policy erişimi doğrulanmadı |
| DOC-03 | Devam ediyor | Bütün iş demoları/raporlar hazır; gerçek jüri videosu yok |
| TES-02 | Tamamlandı — desteklenen yerel API28 ve sentetik ML prototip kapsamı | API35/fiziksel cihaz ve gerçek veri genellemesi ayrı açık sınır |
| TES-03 | Devam ediyor | Kaynak/kılavuz/demo/APK hazır; review/tag/video ve resmî paket açık |
| TES-04 | Devam ediyor | Yerel güvenlik/yeniden üretim kanıtı hazır; merge sonrası final tag/paket yok |
| TES-05 | Başlanmadı | Gerçek gönderim zamanı ve alındı kanıtı yok |
| ALT-07 | Başlanmadı | Gerçek kullanıcı oturumu/roller yok |
| WEB-06 | Başlanmadı | Üretim oturumu/RBAC/TLS dağıtımı yok |

Önerilen son sıra: PR incelemesi/main birleşimi → ilgili son main smoke/CI → uygun `v0.1.0-rc.1` benzeri tag → gerçek ≤15dk video ve erişim kontrolü → kayıtlı ekip üyesinin doğrulanmış adrese gönderimi/alındı. Feature branch'e erken final tag bağlanmadı.

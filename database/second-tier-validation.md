# Görev 15 — İkinci kademe dağıtım kabulü

**27 Ekim 2026, Europe/Istanbul.** Başlangıç main: `50aaca21646e9913a0cb58d13d3bbbec950b1390`. PR #1–#25 merge commit'leri main atası olarak doğrulandı; ek PR #26 dokümantasyon değişikliğidir. Başlangıç çalışma ağacı temizdi. Branch `feature/second-tier-distribution`; main'e doğrudan yazılmaz. PDF'nin ikinci sayfasındaki “İkinci kademe dağıtım yalnızca kaydedilmişse kesin olarak gösterilir” gereksinimi uygulanır. [API ve politika](../backend/SECOND_TIER_DISTRIBUTION.md).

## Gerçek MySQL testleri

Yeni `avatar-task15-mysql`, `avatar-task15-mysql-data`, MySQL 8.0.46/InnoDB, host `127.0.0.1:33329`. Yıkıcı core yalnız `avatar_task15_core_test`, migration yalnız aynı yeni instance içindeki `avatar_migration_test`; demo ayrı `avatar_task15_demo_test`. Özel env `/tmp` altında 0600; parolalar rapora/loga yazılmaz. Önceki instance/veritabanları temizlenmez.

| Kontrol | Sonuç |
| --- | --- |
| Değişiklik öncesi ilk başlangıç paketi | **308 passed**, 139,51 saniye; başarısız/atlanmış yok |
| Yeni test paketi | **52 passed**, 73,07 saniye; başarısız/atlanmış yok |
| Son tam backend/ML paketi | **360 passed**, 223,99 saniye; 341 backend + 19 ML, başarısız/atlanmış yok |
| Migration | **f1507a26b001**, parent e1307a26b001; 29 → 30 domain tablosu |
| Alembic upgrade/check | Gerçek demo DB'de başarılı; yeni fark bulunmadı |
| API smoke | Health/ready 200; yeni liste anahtarsız 401, anahtarla 200; model listesi 200 |

Görev 14'teki açıklanamayan başlangıç DB503 bu görevin ilk 308 testlik koşusunda tekrarlanmadı. Tek kütüphane uyarısı mevcut Starlette/AnyIO deprecation'dır. Geliştirme sırasında MySQL CHECK ihlalinin sürücüde 3819 OperationalError olduğu görüldü; yeni migration testi beklenen kesin MySQL hata kodunu denetler. Son kabul koşusunda bu test geçti; eski assertion'lar değiştirilmedi.

52 yeni testin 42'si API/transaction, 10'u migration/FK/CHECK kapsamıdır:

- Kesin ShipmentLine/Lot/Product/Party FK'leri; kaynak müşteri/satış/lot/ürün/miktar/hareket tutarsızlığında 409; client kaynak kimliklerini yeniden atayamaz.
- Party kartı değiştiğinde alıcı snapshot'ı korunur. Bilinmeyen fiziksel stok ve tüketici satışı null kalır.
- Pozitif Decimal string; paket/adet tam sayı, kg altı hane; hatalı tarih/birim, bilinmeyen UUID, boş kanıt/referans, fazla miktar ve aynı alıcı reddi.
- İdempotency replay, aynı key/farklı gövde, aynı referans/yeni key, eşzamanlı aynı-key istekler; UUID liste/filter sayfalaması ve auth.
- Bildirim bütün eski stok/maliyet/gelir tablolarını değiştirmez; bağımsız sevkiyat da yeni şirket satışı veya ikinci çıkış oluşturmaz.
- 30 kaynak, 12 dağıtım + 18 iade iki işlem sırasında da toplam 30; fazlası reddedilir. Geri tarihli karışık olay açık kronoloji hatasıyla tamamen rollback olur.
- Geç flush sonrası zorlanan hata yeni audit satırını ve idempotency kaydını beraber geri alır.
- Recall sonrasında tarihsel bildirim GET raporuna girer; üyelik/blokaj/üretim ilişkileri değişmez. Blokeli veya süresi geçmiş malı raporlamak yeni fiziksel sevk izni değildir.
- Migration upgrade/boş downgrade bütün 29 eski tablonun hash'lerini korur. Beş gerçek FK, sayılan birim ve diğer CHECK'ler MySQL'de doğrulanır. Dolu audit tablosunun downgrade'ı ilk DDL'den önce reddedilir.

## Kilit yarışları ve retry

Gerçek iki yazıcılı MySQL koşuları:

1. Aynı 30 paketlik kaynak için farklı alıcılara iki 20 paket talep → yalnız biri 201, diğeri 409; kayıtlı toplam 20.
2. İade 20 / dağıtım 20 yarışı iki sırada → kazanan 201, diğeri 409 DOCUMENTED_QUANTITY_EXCEEDED. Sale → sıralı Lot → ShipmentLine kilit düzeni ortak; ikinci writer'ın gerçek kilitte beklemesi testte doğrulandı.
3. Recall / bildirim iki sırada → iki audit işlemi de geçerli; lot bloke kalır, güncel recall GET bildirimi gösterir. Fiziksel stok tüketilmediği için recall sonrası tarihsel kanıt gizlenmez.
4. Haricî bakım Party kilitlerini tutup kaynak Lot'u istedi; yeni dağıtım Lot'u tutup alıcı FK'sını bekledi. **Gerçek InnoDB 1213** yakalandı, yeni işlem rollback/retry oldu; iki deneme sonunda tek dağıtım satırı kaldı. Mevcut commands.execute retry tavanı değiştirilmedi.

## Gerçek TCP HTTP demosu

`python -m app.demo_second_tier` ilk başarılı POST cevabını **sunucu commit'inden sonra** yerel proxy'de düşürdü. İstemci aynı UUID/key, aynı gövde hash'i ve aynı dağıtım UUID'siyle devam etti. Yeni satırın oluşturulması şirketin önceki 28 iş tablosunda hiçbir değişiklik yapmadı; 29. eski tablo olan idempotency'ye yalnız yeni komut kaydı eklendi.

| KURGUSAL kayıt | Doğrulanan sonuç |
| --- | --- |
| ET hammadde lotu | c2e36db9-a4c0-4806-a004-49bb554546da; ET-2026-001 |
| SUC mamul lotu | 39a28fa9-f50a-496a-9cce-8daec25ea203; SUC-2026-045 / 85 paket |
| Üretim maliyeti | 1.543,50 EUR, gösterim EKP 18,16 EUR |
| Şirket sevkiyatı | A/B/C = 30/25/30; toplam **85**, ikinci kademe ile 97 yapılmadı |
| Kaynak A sevkiyat satırı | c5bd1b6b-cb44-4b2a-9164-32c1fef8f7f1 |
| İkinci kademe | b2b69722-52d2-4305-bc06-7251e4e25220; A → Dağıtıcı X, **12 paket** |
| Kayıtlı alıcı | e244c1f0-e844-4c3c-a911-6dd0a79256a4; Dağıtıcı X (KURGUSAL DEMO) |
| Belgelenmiş tahsis edilmemiş miktar | **18 paket**; fiziksel kalan stok iddiası değildir |
| Market stoğu / tüketici satışı | **null**; B/C için ikinci kademe alıcıları da null |
| ET recall | bde3df38-6cf9-4ab4-a403-526c47b8d7c2; SUC bloke, A/B/C ve kayıtlı X raporda |

İlk yeni senaryoda dağıtım ET recall'ından önce oluşturuldu. Eski diğer demolar eklenince DB bilinçli olarak büyüdü; bu ilk hash ile daha sonraki bütün DB hash'inin eşit olduğu iddia edilmez. İlk ve sonraki ikinci kademe **iş sonuçları aynıydı**. Eski demolar hazırlandıktan sonraki iki dış demo komutunun tüm sonuçları eşitti; her komut ayrıca akışı iki kez çalıştırdı. 30 tablonun tekrar öncesi/sonrası aggregate SHA256 değeri:

`a3e6e3f18c94e1993eeb011d9eb1d4e0608fc1f42427a5b95ba31ad030e03caa`

Tek ikinci kademe satırı bulundu; mükerrer bildirim, lot, tüketim veya gelir oluşmadı. API `127.0.0.1:8006` üzerinde gerçek FastAPI/MySQL bağlantısı kullandı. Demo verileri kurgusaldır; gerçek Dağıtıcı X işletmesi veya ticari işlem iddiası yoktur.

## Eski demolar ve kapsam sınırı

Değişmemiş `tools/verify_release_demo.py`, `app.demo_transfers_returns`, `app.demo_rework` yeni demo tekrarından önce ve sonra çalıştırıldı. Şu iş nesneleri aynı kaldı: üretim/market/recall/kuzu/tahminler/kârlılık; Task13 scenario; Task14 flow.

- Üretim 1.543,50 EUR / 85 paket / 18,16 gösterim EKP.
- İki kuzu 25 kg → 22 kg + 3 kg / 287,50 EUR.
- Market A/B/C 30/25/30 ve gerçek ET→SUC lot zinciri.
- Transfer 20 → A13/B7; müşteri iadesi, karantina ve satış iptali.
- Rework 10 → 9,5 + 0,5 kg / 115 EUR.
- İki sentetik ML modeli ve gerçek sonuç/sapma karşılaştırması.

Android kaynakları ve eski 6→5 kg Kotlin kabul kanıtları korunmuştur. **Bu görevde Android instrumentation yeniden çalıştırılmadı:** çalışır adb/emülatör bulunmadı. Kotlin/Room/device, frontend, fiziksel cihaz veya birleşik main kabulü yeniden başarılı sayılmaz. Yalnız backend/ML testleri ve gerçek HTTP akışları bu tarihte yeniden koşuldu.

Üçüncü kademe, market stok doğrulaması, alıcının başka satışları, bağımsız market oturumu, ikinci kademe geri toplama ve düzeltme/iptal protokolü kapsam dışıdır. LOT-10'un **kayıtlı ikinci kademe backend** kabulü için kanıt hazırdır; ortak checklist değiştirilmedi. Web/Android sunumu ve birleşik main kabulünü entegrasyon sorumlusu ayrıca değerlendirmelidir. Üçüncü kademenin bu sürümde var olduğu iddia edilmez.

Ham log/JUnit/geçici JSON'lar yalnız `/tmp/avatar-task15-*` altındadır; kaynak ağacına büyük döküm veya tekrar ekran görüntüsü eklenmez. Geçici kanıtlar ortam yenilenmesinde kaybolursa bu belge ve test kaynakları yeniden koşu tarifidir; kaybolmuş çıktılar yeniden üretilmiş sayılmaz.

## Commit öncesi güvenlik ve koruma

Gitleaks 8.24.3 ile 475 kaynak dosyası ve tüm yerel ref'lerin Git geçmişi tarandı; iki tarama da sıfır bulgu verdi. Özel env dosyalarındaki dokuz gerçek gizli değer için birebir içerik kontrolünde de eşleşme yoktu. Gizli değerler gösterilmedi; `.env`, ham log, geçici JSON, JUnit, APK veya ekran görüntüsü commit adaylarına eklenmedi.

Yalnız backend/database/tests altında 12 dosya değişti. services, costing, commands, lot_graph, recalls, sales, cuttings ve reworks çekirdek dosyaları origin/main ile bayt düzeyinde aynı kaldı. İade çekirdeğine yalnız ortak ikinci kademe kapasite/kronoloji kontrolü eklendi. Başlangıçtaki 14 Docker volume'unun tamamı korundu. Python AST, yerel belge bağlantıları ve git diff --check kontrolleri geçti; ortak docs/checklist, istemciler, ML eğitimi ve Compose değiştirilmedi.

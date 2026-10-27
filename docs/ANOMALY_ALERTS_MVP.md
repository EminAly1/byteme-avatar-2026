# EK-02 — Akıllı uyarı merkezi MVP

27 Ekim 2026, Europe/Istanbul. Main tabanı `254da2751055843565059e1bb98a6ab7d002e1f2`; PR #29/#30 doğrulandı. Branch `feature/anomaly-alert-center`. Bu belge dar kapsamlı yerel kabul kaydıdır; ortak checklist/roadmap değiştirilmedi.

## Kurallar, kaynaklar ve eşikler

Beş kural ailesi, altı kod; uyarılar **güncel salt okunur değerlendirmedir**, teslim edilmiş kalıcı bildirim değildir.

| Aile / kod | Gerçek kaynak ve koşul |
| --- | --- |
| SKT: EXPIRY_PAST / EXPIRY_SOON | StockBalance→Lot→Product/Location. Pozitif fiziksel stokta Türkiye gününe göre SKT < bugün kritik; 0–7 gün uyarı. Null tarih uydurulmaz; daha uzak tarih ve sıfır bakiye uyarı üretmez |
| LOT_BLOCKED_STOCK | Pozitif bakiye + Lot.blocked. Konum ve mevcut RecallLot→Recall FK'leri gösterilir; kullanılabilir miktar 0. Recall yoksa nedeni uydurulmaz |
| LOW_AVAILABLE_STOCK | Açık ürün UUID/birim/eşik konfigürasyonu. Ürün bazında yalnız warehouse kullanılabilir stoğu; karantina/dış üretici/blokeli/geçmiş SKT hariç. Toplam < eşik; eşit değer uyarı değildir. Eşiksiz/birimi uyumsuz/bilinmeyen ürün için uyarı yok |
| PRODUCTION_EKP_DEVIATION | Posted dış üretim + aynı hedef paket ürününe bağlı, işlem başlamadan kayıtlı geçerli tahmin. Kesin EKP = Operation.total_cost / gerçek paket çıktısı; aynı EUR/paket metriği karşılaştırılır |
| YIELD_DEVIATION | Posted dış üretim veya beş parçalı kg kuzu reçetesi + geçerli kayıtlı işlem öncesi tahmin. Gerçek çıktı kg / gerçek girdi kg; paket çıktıda kayıtlı paket ağırlığıyla aynı kg/kg anlamı korunur |

Sapma yüzdesi mevcut comparison sözleşmesiyle **|gerçek − tahmin| / |gerçek| × 100**; yalnız eşik üstü (> varsayılan %15) gösterilir. Sıfır gerçek paydada yüzde uydurulmaz. %15 **demo inceleme eşiğidir**, işletme standardı/kanıtlanmış anomali sınıflandırıcısı değildir. 25 kg→22 kg + açıklanmış 3 kg fark tek başına alarm değildir. Hesap Decimal; API ondalıkları string, gerçek maliyet/lot kaydı değiştirilmez.

## Konfigürasyon

API process environment'ı; frontend/VITE veya yeni DB tablosu kullanılmaz:

```text
AVATAR_ALERT_POLICY_VERSION=ek02-v1
AVATAR_ALERT_EXPIRY_DAYS=7
AVATAR_ALERT_COST_PERCENT=15
AVATAR_ALERT_YIELD_PERCENT=15
AVATAR_ALERT_DEVIATION_ORIGIN=demo
AVATAR_ALERT_STOCK_THRESHOLDS={"<gercek-urun-uuid>":{"quantity":"5","unit":"kg","origin":"demo"}}
```

Yer tutucuyu gerçek ürün UUID'siyle değiştirin. Düşük stok varsayılanı **boş sözlük**; rastgele eşik yoktur. En fazla 200 ürün; Decimal quantity string, package/unit eşiği tam sayı. Origin demo veya operator_configured. SKT penceresi 0–30, pozitif sapma eşikleri en fazla %1000/4 ondalıkla sınırlandırılmıştır. Değişiklikte API sürecini yeniden başlatın. Eşik/değer/birim/köken/politika sürümünden kanonik fingerprint üretilir; eşdeğer Decimal yazımları kimliği değiştirmez.

SKT uyarı günü **Europe/Istanbul**'dur. Mevcut satış korumasının UTC gün politikası değiştirilmedi; bu modül yeni blokaj yapmaz. Ürün bazlı düşük stok, marketlerin bilinmeyen fiziksel stoğu değildir.

## Kayıt ilişkileri ve model sınırı

PredictionRecord.operation_id gerçek Operation FK'sıdır. Tahmin Operation.created_at sonrası, ilk operation StockMovement.created_at ve posted_at öncesi olmalı. Aynı işlemde son uygun işlem öncesi kayıt seçilir; en büyük sapma seçilmez. Input/Output→Lot→Product topluca okunur; hedef ürün, birim, paket ağırlığı veya kuzu reçete/parça eşleşmesi yoksa karşılaştırılmaz. Rework için yeni tahmin metriği icat edilmedi.

Kayıtlı değerler yeniden tahmin edilmez. Kurulu JSON modelinin mevcut checksum/metadata doğrulaması, model sürümü, özellik şeması, dataset hash ve SYNTHETIC köken eşleşmesi gerekir. Geçersiz/eksik/değişmiş model paketi veya uyumsuz snapshot diagnostics ile açıklanır; stok uyarıları çalışmaya devam eder. Yeni sürümle eşleşmeyen tarihsel paket bu MVP'de karşılaştırılmaz; eski Prediction GET ve kayıtlı tahmin değiştirilmez. PortableModel.predict çağrılmadığı testte doğrulandı. Sentetik sınırlamalar kullanıcıya gösterilir; yeni ML eğitimi/anomali doğruluğu iddiası yoktur.

## API, kimlik ve performans

X-API-Key korumalı **GET /v1/alerts**, **GET /v1/alerts/summary**, **GET /v1/alerts/{id}**. POST veya onay/blokaj komutu yoktur. Liste severity (critical/warning/info), rule_code, kaynak lot_id/operation_id; limit 1–100 ve cursor kabul eder. Lot/işlem filtresi kaynak tipini sınırlar; ürün bazlı düşük stok tek lota indirgenmez. Özet aktif filtre kapsamındaki güncel sayıdır. Bilgi filtresi desteklenir; mevcut kurallar gereksiz info satırı üretmez.

ID = UUID5(kural, kaynak UUID, konum, politika fingerprint); aynı kaynak/kural/konum her GET'te çoğalmaz. Öncelik → kaynak türü → UUID/konum → kural sırası kararlıdır. Cursor politika/gün/filtre bağlamına bağlıdır; değişirse 409 ile baştan yenileme istenir. GET'ler arasında kayıtlar değişebilir; tarihsel snapshot veya okunma geçmişi saklanmaz. Artık tetiklenmeyen ID için detay 404 döner.

Kaynaklar **250'lik keyset SQL partileri** ve toplu ilişkilerle okunur; kayıt başına SELECT yoktur. Bellekte yalnız istenen sayfa tutulur. Tam güncel sayılar için sunucu kaynakları akış halinde değerlendirir; özet önbelleği/materialized view yoktur. 1.001 gerçek stok satırında en fazla 16 SQL ifadesi, yalnız SELECT/SET ve 10 kayıtlık yanıt doğrulandı. Bu, üretim ölçeği yük testi değildir.

Her değerlendirme tek REPEATABLE READ snapshot ve **SET TRANSACTION READ ONLY** kullanır; autoflush kapalıdır. Kazara INSERT denemesi gerçek MySQL **1792** ile reddedildi; 30 tablonun hash'i korundu. Sonraki normal POST başarıyla çalıştı: havuza dönen bağlantı yazıcıyı salt okunur bırakmaz. Session kapanışında rollback; commands, stok, fiyat, lot grafı veya recall değişmez.

## React ve kabul

**/uyarilar**: özet, öncelik/kural/kaynak filtreleri, sunucudan en fazla 20 satır/sayfa, güncel detay drawer'ı ve kaynak bağlantıları. Model satırında yüzde sapma ile yüzde eşiği eşleştirilir; gerçek EUR/paket veya kg/kg ayrı gösterilir. Demo eşikleri etiketlidir. Dashboard yalnız küçük GET summary özeti ve merkeze bağlantı içerir. Kaynak stok bağlantısı gerçek ürün filtresini açar. Teknik UUID'ler ikincildir; boş/hata/uyumsuz karşılaştırma durumları veri uydurmaz.

| Gerçek kontrol | Sonuç |
| --- | --- |
| Hedefli pytest | **53 passed**: 17 yeni config + 28 yeni MySQL + mevcut 4 config/4 health; başarısız/atlanmış yok |
| Typecheck/build | Başarılı |
| React birim/bileşen | **72 passed**: önceki 65 + 7 yeni; başarısız/atlanmış yok |
| Gerçek Chromium | **4 passed**, başarısız/atlanmış yok; liste/filtre/detay, gerçek kaynak, model kökeni, boş veri/API401, dashboard, 390/768/1440 px ve otomatik erişilebilirlik |
| Alembic | Yeni migration/tablo yok; head f1507a26b001, 30 domain tablosu; check fark bulmadı |

MySQL **8.0.46/InnoDB**, mevcut izole instance 127.0.0.1:33329; yıkıcı test yalnız yeni `avatar_task17_core_test`, demo/tarayıcı yalnız yeni `avatar_task17_demo_test`. Önceki core/demo şemaları sıfırlanmadı. Test saatinin kontrol edildiği İstanbul gece yarısı, tarih/null/sıfır stok, karantina/blokaj, birim/eşik sınırları, geç/eksik/bozuk tahmin, son uygun tahmin, normal kuzu farkı, kararlı ID/cursor ve salt okunurluk doğrulandı.

## Tekrarlanabilir gerçek demo

Özel env dosyası repo dışında 0600; API 127.0.0.1:8008. Ayrı *_test şeması/migration hazırlandıktan sonra `python -m app.demo_alerts --prepare` mevcut API'lerle **KURGUSAL** kayıtları açıkça oluşturur; kısa JSON stdout'u /tmp'ye kaydedilir. Hazırlık, analiz değildir: işlem öncesi tahmin/üretim/recall gerçek yazıları yalnız bu açık aşamadadır. JSON'daki stock_thresholds API env'ine konup API yeniden başlatılır.

Ardından `python -m app.demo_alerts --verify --seed-file /tmp/avatar-task17-seed.json` yalnız GET çalıştırır: 3 gün sonra SKT, blokeli 3 paket, geçmiş SKT, 2 kg < demo 5 kg; önceden kayıtlı tahminli posted 40 paket/1.543,50 EUR işleminde EKP/verim sapmaları. Kayıtlı 67 kg fark **kurgusal stres örneğidir**, işletme ölçümü/kanıtsız fire sınıfı değildir.

Gerçek demoda **6 uyarı = 2 kritik + 4 uyarı**. Tekrar kimlikleri sabit; 30 tablonun önce/sonra SHA256'sı:

`d81fa833f19fe269663059ccc22b56a646f7ff63b249aace0bc5927b537f1543`

Model karşılaştırması gerçek Operation `efafe5b9-5da1-4723-93ad-3ac740af46f5`, kayıtlı Prediction `52ec0cca-19c9-465d-9bc6-ceac23978f75` FK'sından gelir; kesin EKP **38,587500 EUR/paket**. GET tekrarları yeni satış/maliyet/stok/recall/idempotency veya tahmin oluşturmadı.

## Sınırlar

360 backend testinin tamamı, bütün eski Chromium paketleri, Android ve ML eğitim pipeline'ı bu görevde yeniden çalıştırılmadı. Mevcut defter/lot/maliyet/tahmin motorları değiştirilmedi; hedefli sonuçlar birleşik 31 Ekim kabulünün yerine geçmez. Tarihsel alarm/arşiv/okundu durumu, e-posta/push, yeni anomali modeli, eşik düzenleme UI'sı, üretim yük/rol/TLS kabulü ve proforma bu MVP'de yoktur. Ham log/JUnit/JSON/PNG yalnız /tmp altında; repoya yığılmadı.

**EK-02 önerisi:** Açıklanabilir salt okunur MVP yerel kabulü için kanıt hazır; main merge ve son birleşik kabul ayrı. PROJECT_CHECKLIST ve EXTRA_FEATURES_ROADMAP değiştirilmedi.

Güvenlik/koruma: Gitleaks 8.24.3 ile 496 kaynak dosyası ve tüm yerel Git geçmişi sıfır bulgu verdi. Dokuz gerçek gizli değer kaynakta ve 34 build dosyasında bulunmadı; gerçek HTTP yanıtları da anahtar/parola sızdırmadı. 13 mevcut çekirdek motor dosyası, package/lock/pending/proxy ve ortak checklist/roadmap değişmedi. Başlangıçtaki 15 Docker volume'u korundu. Yalnız izin verilen 18 dosya değişti; git diff --check temiz.

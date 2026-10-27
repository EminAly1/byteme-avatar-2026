# Görev 14 — Rework kabulü

**27 Ekim 2026 (Europe/Istanbul).** Main tabanı `b9fa0b511ad3d6ea6b3da7d4da3bc8572cd7a83b`; PR #1–#23 merge commit'lerinin main atası olduğu Git üzerinden doğrulandı. Başlangıç ağacı temiz; dal `feature/rework-operations`. Uygulanan sözleşme: [backend/REWORK.md](../backend/REWORK.md).

## Test sonucu ve kapsam

| Kontrol | Gerçek sonuç |
| --- | --- |
| Başlangıç paketi, değişiklik öncesi | **256 passed**, başarısız/atlanmış yok; gerçek ayrı MySQL 8 |
| Yeni rework testleri | **52 passed**, başarısız/atlanmış yok |
| Son tam backend/ML paketi | **308 passed**, başarısız/atlanmış yok: 289 backend + 19 ML |
| Son paket süresi | 128,05 saniye; tek Starlette/AnyIO deprecation uyarısı |
| Şema | Yeni tablo/migration yok; 29 domain tablosu; head e1307a26b001; Alembic check fark bulmadı |
| Smoke | API health/ready 200; yeni liste anahtarsız 401/anahtarla 200; mevcut iki model erişilebilir |

İlk başlangıç denemesinde255 test geçti, bir ürün oluşturma fixture'ı DB503 verdi. Kök neden kesinleştirilmedi. Kaynak değişmeden, bağlantı hata kodu yakalayıcısıyla yapılan tekrar256/256 geçti; yakalanan bağlantı hatası listesi boştu. Son308 testi de değiştirilmemiş eski256'yı korudu. İlk koşu başarı sayılmadı; test kaldırılmadı/skip edilmedi, hata gizlemek için assertion değiştirilmedi.

Yeni pakette: taslakta stok/maliyet etkisi yok;10=9,5+0,5kg;100+15=115EUR; açıklamasız/sıfır/negatif miktarlar; çift ve çoklu çıktıda toplam/yuvarlama; üretilmiş mamul ve yan ürün; satın alınmış finished/hammadde/paket kaynak reddi; bozuk kaynak defteri ve plan; blocked/expired/quarantine; yetersiz stok; SKT mirası/kısaltma/uzatma reddi; karantina ve dış konum reddi; idempotency; geç SQL flush sonrasında rollback; çok aşamalı trace/recall; rework çıktısının satışı; geçmiş satış/iade/iptal maliyetlerinin korunması doğrulandı.

Özel kuruş/mikro test:3kg/100EUR lotundan önce1kg satış33,333333EUR; sonraki1kg rework tüketimi **33,333334EUR**; son1kg satış33,333333EUR. Geçmiş maliyet değiştirilmeden toplam100EUR korunur. Rework15EUR işlemle48,333334EUR yeni lot üretir; toplam ekonomik tutar115EUR olur. Gösterim birim maliyetiyle tekrar hesap yapılmaz.

## Gerçek MySQL yarışları

- İki ayrı rework ve rework/satış, rework/transfer aynı20kg kaynaktan15kg almaya çalıştı: yalnız bir işlem commit etti, depoda5kg kaldı.
- Recall önce gerçek lot kilidini kazanınca rework409LOT_BLOCKED; kaynak ve çıktı hareketleri oluşturulmadı.
- Rework önce kapanınca ata recall'ı yeni rework lotunu da kapsayıp bloke etti. Testlerde kazananın gerçek kilidi tutuldu ve ikinci HTTP writer'ın beklemesi doğrulandı.
- Haricî bakım transaction'ı hedef Location kilidini tutup kaynak lotu istedi; rework kaynak lotu tutup çıktı konumunu istedi. **Gerçek InnoDB1213** yakalandı, rework rollback/retry oldu; yalnız bir OperationInput/Output ve bir tüketim maliyeti kaldı.
- Mevcut commands.execute üç deneme tavanı ve eski gerçek deadlock/timeout testleri308 pakette korundu. Yeni kontrollü geç hata, kaynak sayaçları ve yeni lot/link/bakiye/idempotency yazılarının tamamını geri aldı.

## Gerçek HTTP demo

Yeni `python -m app.demo_rework`, gerçek loopback TCP→FastAPI→MySQL kullanır. Geçici proxy ilk başarılı rework post cevabını **sunucu commit'inden sonra** düşürdü. Aynı UUID, gövde hash'i ve operasyon ID'siyle retry başarılı; ikinci kesin rework oluşmadı.

İki dış komutun her biri iki tam iç akış çalıştırdı. Sonuç JSON'ları aynı, tekrar öncesi/sonrası29 tablonun aggregate SHA256 değeri eşit:

`ac3cb15a2f14a01d24eff445b9497c5da4ac6f30f9b9960a48d6c4dfa79c4053`

| KURGUSAL kayıt | Doğrulanan değer |
| --- | --- |
| Hammadde kökü |9dfb546c-38b6-42ed-86ac-c6cceeef1a87 |
| İlk üretim mamul lotu |4c752106-8e86-4ffc-86a5-38c9fec70885;20kg/200EUR |
| Rework |d34b478b-79d7-4c10-a073-96fc3e07f531;10kg kaynak,100EUR +15EUR hizmet |
| Yeni lot |905d4038-8f2f-4a60-8a89-7e0c69c56863;9,5kg/115EUR;0,5kg açıklanmış kayıp |
| Kaynak kalan |10kg; original_quantity20/total_cost200 değişmedi |
| Satış/sevkiyat |Yeni lottan1kg; kalan8,5kg; aynı kesin hareketi paylaşan bağlı sevkiyat |
| SKT |Kaynak ve çıktı2026-11-26; rework uzatmadı |
| Ata recall |ae8c737a-88b8-43e6-9e5e-4515aee8118e; yeni lot dahil tüm türevler blokeli |
| Son yeni satış |409LOT_BLOCKED; kullanılabilir miktar0 |

Bu ölçüler **KURGUSAL matematiksel demo**; PDF'de gerçek üretim ölçüsü olarak verilmiş sayılmaz. Tarihler ilk üretim kaydından tekrar okunur; ertesi gün request body değişerek idempotency çatışması yaratılmaz. Nakit ödeme veya kalite/raf ömrü belgesi doğrulandı iddiası yoktur.

## Eski demoların korunması

Rework akışından önce ve sonra mevcut `tools/verify_release_demo.py` ve `app.demo_transfers_returns` çalıştırıldı. Bilinçli yeni rework kayıtları global DB'yi büyüttüğü için **eski/yeni bütün DB hash'i eşit denmedi**; eski iş sonuçları ayrı karşılaştırıldı:

- Dış üretim1.543,50EUR /85paket /18,16 gösterimEKP.
- İki ayrı kuzu25kg→22+3kg /287,50EUR.
- Market A/B/C30/25/30; ET→SUC kesin FK ve recall.
- Transfer20kg→A13/B7; ardından iade/iptal senaryosu10/2/5kg.
- Satış kârlılığı, tarihsel kredi/maliyet düzeltmeleri ve karantina durumu.
- İki sentetik ML tahmini ve gerçek sonuç/sapma.

Eski üretim/market/kuzu/recall/prediction/profit nesneleri ve Task13 scenario nesnesi önce/sonra aynıydı. Yeni rework'ün kendi tekrarında bütün29 tablo hash'i sabit kaldı. Demo stokları sıfırlanmadı.

## İzolasyon, dosya sınırı ve sınırlar

Yeni `avatar-task14-mysql` ve `avatar-task14-mysql-data` kullanıldı; MySQL8.0.46, host127.0.0.1:33328. Core avatar_task14_core_test, demo avatar_task14_demo_test, migration avatar_migration_test bu **yeni instance** içindedir. Eski kullanıcı/release/Task13 volume'ları korunur. Özel env repo dışında0600; API yalnız127.0.0.1:8005. Yıkıcı fixture yalnız ayrı *_test şemalarında çalıştı.

Yalnız backend/database/tests değiştirildi. Model, maliyet algoritması, genel stock services, lot_graph, recall, transfer/iade/iptal çekirdeği ve commands.execute değiştirilmedi. Frontend/Android/ML eğitimi, Compose ve ortak docs/checklist'e dokunulmadı; bu görevde istemci cihaz/tarayıcı kabulü yapılmış sayılmaz.

Ham loglar, JUnit ve geçici JSON'lar `/tmp/avatar-task14-*` altında tutuldu; kaynak ağacına büyük log, tekrar görüntü veya JSON dökümü eklenmedi. Bu belge tarihli ve küçük kabul kaydıdır; test kaynakları ve tekrar komutları repodadır. Geçici çıktılar ortam yenilenmesinde kaybolursa yeniden üretilmiş gibi sunulmamalıdır.

LOT-05'in eksik **rework backend** hareketi bu sürümle uygulandı. Ancak maddeye otomatik Tamamlandı yazılmadı: kg dışı/daha çok kaynak, karantina kalite serbest bırakma/değerleme, gerçek cihaz/frontend ekran entegrasyonu, ikinci kademe dağıtım ve final birleşik kabul ayrıca değerlendirilmelidir. Kullanıcı/rol/TLS üretim dağıtımı ve gerçek işletme kalite süreçleri bu task'ın kapsamı değildir. Rework tahmini/AI kesin maliyet yerine kullanılmadı.

## Commit öncesi güvenlik ve koruma kontrolü

Gitleaks 8.24.3 ile 468 commit adayı kaynak dosyası ve tüm yerel ref'lerin Git geçmişi tarandı; iki tarama da sıfır bulguyla geçti. Repo dışındaki özel env dosyalarından okunan altı gerçek gizli değer için ayrıca birebir içerik kontrolü yapıldı; eşleşme bulunmadı. Değerler rapora veya loga yazılmadı, `.env` dosyaları commit adaylarına eklenmedi.

Yalnız bu görevin yedi dosyası backend/database/tests altında değişti. Sekiz ortak çekirdek dosyası origin/main ile bayt düzeyinde aynı kaldı. Başlangıçtaki 13 Docker volume'unun tamamı yerinde. Python AST, belge bağlantıları ve `git diff --check` kontrolleri geçti. Ham güvenlik raporları da kaynak ağacına eklenmedi.

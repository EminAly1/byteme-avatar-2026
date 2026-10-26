# Görev 13 — MySQL transfer/iade/iptal kabulü

**26 Ekim 2026, Europe/Istanbul.** Main tabanı `b569830` üzerinde PR #1–#21 atalık kontrolü geçti. Başlangıç çalışma ağacı temizdi; `feature/lot-transfers-returns` dalı açıldı. [Git kanıtı](transfers-returns-validation/initial-state.json). Kod/sözleşme: [backend/TRANSFERS_RETURNS.md](../backend/TRANSFERS_RETURNS.md).

## Sonuç

**256 test başarılı, 0 başarısız, 0 atlanan:** önceki **194** korunarak **62** yeni test eklendi. Toplam **237 backend + 19 ML**. [Tam pytest çıktısı](transfers-returns-validation/pytest.txt), [JUnit XML](transfers-returns-validation/pytest.xml), [sonuç JSON](transfers-returns-validation/results.json). Bu sayılar son üç hareketli iptal koduna aittir; prototype sonuçlarıyla toplanmaz.

| Paket | Gerçek kapsam | Geçen |
| --- | --- | --- |
| Değişiklik öncesi baseline | Yeni, ayrı MySQL üzerinde bütün eski backend/ML |194 |
| Yeni MySQL domain testleri | Transfer, kısmi/tam iade, iptal, kâr, FK, gerçek kilit yarışları, rollback/deadlock |56 |
| Yeni gerçek HTTP testleri | Transfer/iade/iptal commit'inden sonra TCP read timeout ve aynı key/body replay |3 |
| Yeni migration testleri | Eski veri korunması, duplicate reversal preflight, audit kaybını önleyen downgrade reddi |3 |
| Son tam paket | Önceki194 + yeni62; ML19 dahil |256 |

[Baseline](transfers-returns-validation/baseline.txt) değişiklikten önce koşuldu. [63 testlik erken satış/trace regresyonu](transfers-returns-validation/early-regression.txt) final paketin yerine geçmez; ayrı tarihsel ara kanıttır. Tek uyarı Starlette/AnyIO deprecation'dır. React/Android veya ML eğitim kodu değiştirilmedi; bu görevde istemci cihaz/tarayıcı testleri yeniden koşuldu denmez. İki ML'nin gerçek API çağrıları ve eski ML testleri doğrulandı.

## İzolasyon ve migration

- Ayrı MySQL **8.0.46 / InnoDB** instance: `avatar-task13-mysql`, host loopback33327, yeni `avatar-task13-mysql-data` volume'u.
- Core test: `avatar_task13_core_test`; migration testi: bu yeni instance içindeki `avatar_migration_test`; final demo: `avatar_task13_acceptance_test`. İlk taslak demo `avatar_task13_demo_test` korundu.
- Eski release/kullanıcı instance ve volume'ları silinmedi, resetlenmedi. Yıkıcı fixture yalnız ayrı `*_test` şemalarında; self-FK temizliği reversal yapraklarını önce siler, FOREIGN_KEY_CHECKS kapatılmaz.
- Özel env/anahtar/parolalar repo dışında0600 dosyalarda. API yalnız127.0.0.1:8004 üzerinde. [Health/ready/auth/model smoke](transfers-returns-validation/smoke.json), [gerçek OpenAPI](transfers-returns-validation/openapi.json).

Migration **e1307a26b001 → parent dc9109a1f001** beş tablo ekler: stock_transfers, customer_returns, customer_return_lines, sale_cancellations, sale_cancellation_lines. StockMovement.reversal_of için UNIQUE eklenir. Eski Lot/Sale/SaleLine değerleri ve maliyet algoritması yeniden yazılmaz.

Upgrade eski duplicate reversal varsa **DDL'den önce** durur; kayıtlar otomatik silinmez. Boş yeni tablolarda downgrade/upgrade ve Alembic metadata check geçti; eski lot/satış/maliyet satırlarının eşitliği doğrulandı. Yeni iş kayıtları varsa downgrade DDL'den önce reddedilir; audit bilgisi düşürülmez. MySQL self-FK destek indeksi UNIQUE kaldırılmadan önce korunur; child tabloyla indeks/FK birlikte kaldırılır. MySQL DDL auto-commit olduğu için bu işlemler DML transaction rollback garantisiyle karıştırılmaz.

## İş kabulü

| Senaryo | Kanıtlanan sonuç |
| --- | --- |
|20kg lot,7kg A→B | A13/B7; toplam20; lot toplam maliyeti194EUR, tüketim sayaçları0/0 |
| Kısmi ve ters yön transfer | Doğru bakiye; sıfır maliyet tüketimi; iki hareket ve gerçek Transfer FK'ları |
| Aynı kaynak/hedef, yanlış birim/lokasyon, yetersiz stok |422/404/409 ve tam rollback; negatif stok yok |
| Transferin ikinci gerçek SQL hareketinden sonra kontrollü hata | İki hareket/bakiye/idempotency claim dahil başlangıç snapshot'ı geri geldi |
| Blokeli/SKT geçmiş lot | Satılabilir depoya transfer yok; yalnız karantinaya muhafaza; blok kaldırılmaz |
| Karantinadan depoya transfer | QUARANTINE_RELEASE_REQUIRED; kalite/değerleme bypass yok |
| Kaynak satış5kg, kısmi iade2kg | Gerçek SaleLine ve ShipmentLine FK; kredi40EUR, maliyet düzeltmesi19,40EUR; karantina2kg |
| Çoklu kısmi iade | Toplam orijinal satışı aşamaz; tam miktarda kredi ve COGS artığı tam eşit; aynı key çift giriş yapmaz |
|0,03EUR/3kg, iadeler0,5+0,5+2kg | Krediler0,01+0,00+0,02EUR; kuruş yaratılmaz |
| İptal | Yalnız hiç sevk edilmemiş satışın tamamı; ikinci iptal ve sonradan sevkiyat reddi |
| Tam reversal | Aynı lot/konumda karşı miktar; orijinal harekete FK ve DB UNIQUE; ardından tek transaction'da karantina çıkış/giriş çifti |
| İptalin son karantina girişinde hata | Üç hareket, finansal olay ve idempotency kaydı tamamen rollback |
| İptal ortasında eşzamanlı okuyucu | Orijinal depodaki geçici pozitif kayıt görünmez; commit sonrası yalnız karantina artar |
| Önceki satıştan sonra başka tüketim, sonra ilk satışın iptali | Lot tüketim sayaçları geri sarılmaz; geçmiş maliyetler ve sonraki tam tüketim artığı korunur |
| Kâr raporu | Orijinal satış ayrı; adjustments ve net_after_adjustments ayrı; sıfır gelirde marj null; GET hiçbir tabloyu değiştirmez |
| GET kâr sürerken iade commit'i | Tek REPEATABLE READ snapshot; gelir düzeltmesi ve iade miktarı farklı anlardan karışmaz |

İade edilmiş ürün doğrudan satılabilir stoğa dönmez. Sevk öncesi iptal, orijinal konumda tam terslemeyi ve karantinaya fiziksel muhafaza çiftini **tek commit** ile kaydeder. Üç hareketin tamamı SaleCancellationLine FK'larıyla bağlıdır. Brüt lot tüketimi tarihsel kalır; finansal kredi/maliyet geri kazanımı ayrı kayıttır. Bu dar kapsam güvenlidir; satılabilir stok restorasyonu veya kalite onayı tamamlandı değildir.

PDF mamul lotu için ek kabul:30paket satışın1+29paket iadesi18,158824 +526,605882EUR maliyet düzeltir;20paket ayrı iptal363,176470EUR ve son35paket satış635,558824EUR ile toplam1.543,50EUR korunur. 18,16 gösteriminden maliyet üretilmez. Gerçek ET atası recall’ı, karantinadaki50paketi de bloke eder; üretim FK kenarları değişmez.

## Gerçek MySQL eşzamanlılık kanıtları

- İki transfer ile transfer/satış aynı kaynağı tüketmeye çalışır: yalnız biri stok sınırı içinde commit eder.
- Transfer/recall iki kilit sırasıyla: gerçek ilk lot kilidi tutulur, ikinci HTTP writer'ın MySQL'de beklediği doğrulanır; recall kazanırsa normal transfer reddedilir.
- İki kısmi iade aynı Sale başlığında yarışır: sınır aşılmaz. Aynı key ile eşzamanlı iki iade yalnız bir kabul oluşturur.
- İade/iptal, sevkli ve sevksiz satışta iki sırayla sınanır. Fiziksel durumun izin verdiği akış kazanır; ikisi birden stok iadesi oluşturmaz.
- İptal/sevkiyat iki sırayla: Sale kilidini kazanan tek akış commit eder, diğeri409.
- Recall/iade ve recall/iptal iki sırayla: miktar karantinada, aynı lot blokeli ve kullanılabilir miktar0 kalır.
- Haricî bakım transaction'ı Location kilidiyle gerçek InnoDB1213 döngüsü üretir. Driver hatası gerçekten yakalanır; küçük transfer transaction'ı rollback/retry olur, sonunda tek Transfer ve iki hareket vardır.
- Ayrı kontrollü1213 testi üç retry tavanını doğrular; altı gerçek kısmi hareket/bakiye yazısının tümü geri alınır. Kontrollü hata gerçek deadlock testi diye sunulmaz.
- Gerçek loopback TCP'de API commit'i gözlenir, proxy cevabı tutulur ve sonra client read timeout tetiklenir. Transfer/iade/iptal aynı UUID/gövdeyle tekrarlandığında aynı ID/cevap ve değişmeyen29 tablo hash'i döner.

## Son gerçek demo ve tekrar

[Son demo](transfers-returns-validation/demo-task13.json), [ikinci dış komut](transfers-returns-validation/demo-task13-repeat.json), [çıktı](transfers-returns-validation/demo.txt). İki dış komutun her biri iki tam iç akış çalıştırdı; cevaplar ve29 tablonun hash'leri aynı, mükerrer kesin kayıt yok.

1. KURGUSAL alış:20kg/194EUR, Depo A.
2. Bağımsız transfer7kg: A13/B7. Bu tarihsel adım, daha sonraki satışların **güncel** bakiyelerinden ayrı raporlanır.
3. Depo B'den5kg×20EUR satış ve bağlı sevkiyat: B2, gelir100, kesin COGS48,50.
4. Müşteri2kg iade: karantina2; net satış kredisi40, maliyet düzeltmesi19,40.
5. Depo A'dan ayrı3kg sevksiz satış ve tam iptal:60EUR/29,10EUR düzeltme; aynı konum reversal + karantina muhafaza çifti.
6. Son fiziksel bakiye **A10/B2/karantina5kg**. Lot brüt tüketimi8kg/77,60EUR; orijinal miktar20 ve maliyet194 değişmez.
7. İlk satışın net sonucu gelir60/COGS29,10/brüt kâr30,90EUR; iptal edilmiş ayrı satışın net sonucu0. Nakit geri ödeme kaydı yoktur.
8. Recall sonrası bütün bu bakiyeler blokeli/kullanılabilir0; yeni satış409LOT_BLOCKED.

[Eski demo önce](transfers-returns-validation/legacy-demo-before.json) ve [yeni demo sonra](transfers-returns-validation/legacy-demo-after.json): üretim1.543,50/18,16, SUC85, Market A/B/C30/25/30, iki25kg kuzu/287,50, trace/recall, iki model ve mevcut kârlılık sonuçları aynı. Yeni Task13 kayıtları eski lot/satış/operasyonları değiştirmedi.

## Geliştirme sırasında yakalananlar

İlk testlerde self-FK fixture temizliği ve MySQL FK destek indeksini ayrı drop etme sorunu yakalanıp düzeltildi. Kısa ağ süresine dayanan timeout testi, timeout'u ancak gerçek commit gözlendikten sonra kuracak şekilde sağlamlaştırıldı; business assertion gevşetilmedi. Son muhasebe incelemesinde iptal, tam konum reversal'ı + iki karantina hareketi olarak kesinleştirildi.

`development-prototype/` önceki, artık kabul sürümü olmayan taslağın kanıtlarını tutar; eski demo DB silinmedi. `development-migration-failure.txt` eski başarısız geliştirme koşusudur. **Son kabul yalnız256/256 çıktısı ve avatar_task13_acceptance_test demolarıdır.**

## Kalan kapsam ve LOT-05

Tamamlanan backend kabulü: bağımsız lot transferi; gerçek satış/sevkiyat kaynaklı kısmi/tam müşteri iadesi; yalnız sevksiz satışın tam iptali; gerçek FK hareketleri; stok/maliyet dengesi; transaction/idempotency/recall ve yarışlar; orijinal/düzeltilmiş kârlılığın ayrılması.

Kalan: **rework**, ayrı kalite onayı ve geri kazanım stoğunu güvenle yeniden değerleyip kullanıma açma, bağımsız sevkiyat iadesinin kaynak satışa eşlenmesi, kısmi iptal, nakit iade/ödeme ve istemci ekranları. LOT-05'in tamamına bitti denmez. Ortak API/ER/checklist bu görev sınırı gereği değiştirilmedi; entegrasyon sorumlusu yeni sözleşmeyi bu backend belgesinden aktarabilir. Fiziksel cihaz veya frontend kabulü yapılmış sayılmaz.

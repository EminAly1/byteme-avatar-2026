# Görev 5 — satış/sevkiyat doğrulama raporu

Tarih: 24 Ekim 2026. Branch: feature/sales-shipments. Başlangıç origin/main: **6341cfb24e0a6526694efe13af60041aa5f80875**; PR #1–#4 normal merge geçmişi fetch ile doğrulandı. AGENTS.md, PDF, ER/API planı ve güncel checklist okundu.

## Uygulanan kapsam

Yeni tablolar: sales, sale_lines, shipments, shipment_lines. Migration **81f4da20f36b**, parent **eeea4b5dd1a8**. Party/lot/product/location/stock_movement ve sale_line ilişkileri gerçek FK’lerdir; sevkiyatta stock_movement_id ve sale_line_id unique’dir. Çekirdek lot grafı değiştirilmedi.

Yeni kaynaklar backend/app/sales.py, demo_sales_shipments.py, migration ve iki test dosyasıdır; API/şemalar/modeller genişletildi. Sözleşme ve çalıştırma [backend/SALES_SHIPMENTS.md](../backend/SALES_SHIPMENTS.md) içindedir. Yalnız backend/, database/, tests/ değişir; root docs/checklist, frontend ve Android korunur.

## İzolasyon ve sonuçlar

Sıfırdan MySQL 8.0.46 container’ı `avatar-sales-20261024-e87e83`, ayrı yeni volume ve loopback port 33308 ile kullanıldı. Sır değerleri yalnız 0600 geçici environment dosyalarındadır. İşletme veya mevcut demo DB’si silinmedi/değiştirilmedi.

- avatar_sales_test: veri silen API/core testleri, `_test` güvenlik kontrolü korunur.
- avatar_migration_test: ayrı migration zinciri testi.
- avatar_sales_demo_test: gerçek HTTP üretim + market demo komutu.

| Kontrol | Sonuç |
| --- | --- |
| Kod eklenmeden güncel main backend tabanı | **38 passed**, 1 Starlette/anyio deprecation warning |
| Özellik sonrası tam MySQL pytest | **76 passed**, **0 failed / 0 skipped**, aynı 1 upstream warning |
| Regresyon | Önceki 38 test kaynağı/assertion’ları değiştirilmedi; hepsi geçti. Yeni 38 vaka eklendi. |
| Varsayılan pytest (MySQL opt-in kapalı) | 16 passed, 60 skipped; bu skip’ler başarı sayılmaz. Yukarıdaki tam MySQL koşusunda 76 vakanın tamamı çalıştırıldı. |
| Canlı API smoke | Ayrı test DB’sine bağlı health/ready/OpenAPI ve yeni sales/shipments GET koleksiyonları HTTP 200; üç satış ve üç sevkiyat doğrulandı. |
| pip check | No broken requirements found |
| Alembic upgrade/check | Başarılı; metadata ile fark yok |
| Migration roundtrip | Hem bütün zincirde upgrade/check/downgrade/upgrade hem v1 stock verisini v2→v1’de koruma testi geçti |
| Gerçek HTTP demo | Boş test DB’sinde üretim + üç market satış/sevkiyatı çalıştı; tekrar koşusu byte olarak aynı JSON cevabı verdi |

Tam komut (MYSQL_HOST/PORT/USER/PASSWORD process ortamında doğru izole instance’ı göstermeli):

```bash
MYSQL_DATABASE=avatar_sales_test AVATAR_MYSQL_TEST=1 AVATAR_CORE_MYSQL_TEST=1 backend/.venv/bin/python -m pytest tests -q
```

## Gerçek demo sonucu

ET-2026-001 → URT-2026-045 → SUC-2026-045 / 85 paket korundu. Üretim toplamı 1543.500000 EUR, gösterim EKP 18.16 EUR.

| Market | Kesin sevkiyat |
| --- | --- |
| A | 30.000000 paket |
| B | 25.000000 paket |
| C | 30.000000 paket |
| Toplam | **85.000000 paket** |

İşletme mamul bakiyesi **0**. İki komut çalıştırması sonrasında DB’de aynı **5 party (tedarikçi, üretici, 3 market), 3 sale, 3 sale_line, 3 shipment, 3 shipment_line ve 16 stock_movement** vardı. 13 üretim hareketine yalnız 3 sale hareketi eklendi; bağlı sevkiyat yeni hareket yaratmadı. Tekrar koşusu kayıtları çoğaltmadı.

Alıcılar/iletişimler KURGUSAL DEMO ve `.invalid` email olarak işaretlidir; gerçek kişi/işletme bilgisi değildir. 25,00 EUR satış fiyatı kurgusal demo değeridir. Markette kalan miktar ve son tüketici satışı bilinmez/null’dır; 85 paket sevk bu iki kavramla eşitlenmez.

## Doğrulanan güvenlik ve iş kuralları

- Normal satışta lot/ürün/konum/birim/fiyat/UTC tarih ve kesin hareket kaydı; Decimal satır/başlık yuvarlaması ve maliyet koruması.
- Yetersiz stok, negatif/sıfır/fazla hassasiyet, sayısal JSON para/miktar, yanlış birim ve kesirli paket reddi.
- Aynı anahtar replay ve farklı gövde çakışması; eşzamanlı aynı anahtar yalnız bir satış oluşturur.
- Satış/satış ve satış/bağımsız sevkiyat yarışında 85 paketten iki adet 80’lik çıkış yapılamaz.
- Blokeli/SKT geçmiş/karantina/dış üretici kaynağı reddedilir; lot kilidi beklenirken bloke edilen lot satılamaz.
- Geçersiz ikinci satır veya geç toplam-tutar taşmasında header/satır/stok/maliyet/hareket/idempotency yazılarının tamamı rollback edilir.
- Bağımsız sevkiyat tek fiziksel çıkış; bağlı sevkiyat sıfır stokta dahi mevcut sale hareketini kullanır, ikinci maliyet/tüketim yaratmaz.
- Müşteri/satış satırı/lot/konum/birim/tam miktar eşleşmesi; kısmi veya karışık bağlı/bağımsız istek reddi; shipment tarihi satıştan önce olamaz.
- Aynı satış hareketini ikinci kez sevk engeli ve eşzamanlı tek claim; farklı header’a aynı movement’ı bağlama girişimi DB unique ile reddedilir.
- Sonradan değişen party bilgileri sevkiyat snapshot’ını değiştirmez; bilinmeyen contact null kalır. Referanslı müşteri FK ile korunur.
- Fixture olarak ters hareket verilmiş satışın sevki engellenir. Bu test müşteri iadesi/iptal API’si uygulandığı anlamına gelmez.
- GET liste/detail, satış cursor sayfalaması ve mevcut X-API-Key/Idempotency-Key koruması.

Kilit testinin gözlemcisi, eski readiness testinin engine cache temizlemesi nedeniyle fixture engine’i yerine request’in gerçekten kullandığı engine’e bağlanacak şekilde düzeltildi; test/assertion kaldırılmadı. Son tam koşuda bütün 76 test geçti.

## Sonraki recall görevi için hazır ilişkiler

`OperationInput → LotLink → OperationOutput → Lot → SaleLine → Sale → Party` ve `Lot → ShipmentLine → Shipment → Party` yolları kesin FK kayıtlarıdır. Bağlı sevkiyatta `ShipmentLine.sale_line_id → SaleLine.id` ve ortak movement_id vardır. Snapshot ve shipped_at kaydı bilinen alıcıyı tarihsel olarak korur. Genel trace API/recall traversal bu görevde yoktur.

Recall yazarı sıralı lot kilidi altında blocked güncellemelidir. Satış blok kontrolünü aynı kilit altında yapar. Satış ters hareketi/iptali yazarı, bağlı sevkiyatla uyumlu **sale header → sorted lots** lock sırasını izlemelidir. Finansal/stock raporlarda bağlı sale ve shipment maliyet snapshot’larını çift saymayın; tek çıkış stock_movement_id ile tanımlıdır.

## Eksikler ve ortak belge değişiklik istekleri

- Recall algoritması, recursive ileri/geri izleme ve etkilenen market raporu yazılmadı; fiilî geri çağırma/satış yarışı uçtan uca testi yoktur. Mevcut blocked alanına karşı kilit testi bunun yerine recall tamamlandı diye sunulmaz.
- Müşteri iadesi/iptal API’si, kısmi sevkiyat, genel transfer, kuzu parçalama, Android ve frontend satış ekranı yoktur. Frontend testleri ve Docker stack bu görevde çalıştırılmadı.
- Yerel API anahtarı korunur; üretim kullanıcı/rol oturumu eklenmedi.
- docs/api-contract.md: zorunlu customer_id, birim/fiyat, linked sale_line_id/tam miktar ve snapshot sözleşmesi güncellenmeli.
- docs/data-model.md: dört gerçek tablo, FK/unique ve iki shipment modunun maliyet/hareket anlamı eklenmeli.
- Frontend sahibi OpenAPI tiplerini yeniden üretip satış/sevkiyat ve movement türü ekranlarını gerçek API’ye bağlamalı.
- docs/PROJECT_CHECKLIST.md **değiştirilmedi**. TST-01/TST-02 kanıtı 76 testle güncellenebilir; DOC-02 demo kapsamına A/B/C sevkiyatı eklenebilir. LOT-05’in satış/sevkiyat alt kapsamı, LOT-09’un 30/25/30 kayıt alt kapsamı ve AND-04’ün merkezi satış kayıt alt kapsamı artık hazırdır. Bu geniş ID’lerin tamamı bitmiş değildir: recall raporu/diğer hareketler/Android hala eksik; bütün ID’leri Tamamlandı işaretlemeyin. DOC-03 de üç görevin tüm demosu olmadığı için Devam ediyor kalır.

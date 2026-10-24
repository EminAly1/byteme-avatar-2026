# Lot bazlı satış ve market sevkiyatı — Görev 5

Bu modül `main` commit’i `6341cfb24e0a6526694efe13af60041aa5f80875` üzerine eklenir. Kaynak değişiklikleri yalnız backend/, database/ ve tests/ içindedir. Recall algoritması, müşteri iadesi API’si ve frontend/Android ekranları bu görevde uygulanmaz.

## Kurulum ve migration

Mevcut backend/README.md kurulumunu kullanın; process ortamında MYSQL_* ve AVATAR_API_KEY gerekir. API açılışında tablo yaratılmaz.

```bash
# Repo kökünde, kendi güvenilir process environment’ınız yüklenmişken
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini check
backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Yeni head `81f4da20f36b`, parent `eeea4b5dd1a8`’dir. Yalnız sales/sale_lines/shipments/shipment_lines tablolarını ekler; eski lot/stok ilişkilerini değiştirmez. `downgrade eeea4b5dd1a8` satış/sevkiyat tablolarını ve verilerini siler; üretim/stok tabloları kalır. Üretimde yedeksiz downgrade çalıştırmayın. Stok verisinin v1→v2→v1 geçişinde korunduğu izole MySQL testi vardır.

## API sözleşmesi

Tüm yollar mevcut **X-API-Key** korumasındadır. Her POST **Idempotency-Key: UUID** ister. Para ve miktar JSON string; para birimi EUR, tarihler ISO8601 timezone içeren değerlerdir, çıktı UTC’dir. Tarih atlanırsa ilk başarılı komutta server zamanı kaydedilir; replay yeni tarih üretmez.

| Metot/yol | Davranış |
| --- | --- |
| POST /v1/sales | Kesin satış; her satırdan bir kez stok ve lot maliyeti çıkarır. 201. |
| GET /v1/sales | Başlık listesi, limit 1–100, UUID cursor ve next_cursor. |
| GET /v1/sales/{id} | Başlık + satırlar; lot/ürün/konum/birim/fiyat ve stok hareketi kimlikleri. |
| POST /v1/shipments | Bağımsız fiziksel çıkış veya mevcut satış hareketinin teslim belgesi. 201. |
| GET /v1/shipments | Başlık listesi, limit/cursor/next_cursor. |
| GET /v1/shipments/{id} | Alıcı snapshot’ı, satış ve miktarlı lot/hareket/satış satırı bağlantıları. |

### Satış oluşturma

```json
{
  "customer_id": "<customer rolündeki party UUID>",
  "currency": "EUR",
  "lines": [{
    "lot_id": "<lot UUID>",
    "location_id": "<işletme deposu UUID>",
    "quantity": "30",
    "unit": "package",
    "unit_price": "25.00"
  }]
}
```

Opsiyonel `sold_at`: örn. `2026-10-24T15:00:00Z`. customer_id bu sürümde **zorunludur**; anonim müşteri akışı yoktur. Müşteri `parties.roles` içinde customer taşımalıdır. Bir satışta aynı lot/konum tek satırdır (1–100 satır). `unit` atlanırsa ürünün stok birimi alınır; verilirse aynı olmalıdır. Adet/paket tamsayıdır. Kg miktarı en fazla 6, birim fiyat en fazla 2 ondalık hane taşır; sayısal JSON veya farklı para birimi reddedilir.

Satış taslak/rezervasyon değildir: POST commit’i stok çıkışıdır. Satış başlığı total_amount; satır product_id, lot_id, location_id, quantity, unit, unit_price, total_amount, consumed_cost ve stock_movement_id döndürür. Satır tutarı Decimal(quantity×unit_price) üzerinden kuruşa ROUND_HALF_UP; başlık tutarı satır toplamlarının toplamıdır. Fiyat/tutar string’leri 2 hane; miktar/maliyet 6 hanedir. Mevcut API’lerle uyumlu 12 tamsayı hane sınırı aşılırsa 422 ve rollback olur. Vergi/indirim, kâr/marj hesapları bu modülde yoktur.

### Bağımsız sevkiyat

```json
{
  "customer_id": "<party UUID>",
  "lines": [{"lot_id":"<UUID>","location_id":"<UUID>","quantity":"30","unit":"package"}]
}
```

sale_id ve sale_line_id bulunmaz/null’dır. Tek yeni `shipment` stok hareketi ve lot maliyet tüketimi kaydedilir. Bu bir satış/fatura kaydı değildir; gelir veya satış fiyatı uydurulmaz.

### Satışa bağlı sevkiyat

```json
{
  "customer_id": "<satış müşterisinin UUID’si>",
  "sale_id": "<satış UUID>",
  "lines": [{
    "sale_line_id":"<o satışın satır UUID’si>",
    "lot_id":"<aynı lot UUID>",
    "location_id":"<aynı çıkış deposu UUID>",
    "quantity":"30",
    "unit":"package"
  }]
}
```

- sale_id varsa **her** satırda sale_line_id zorunludur. Bağımsız ve bağlı satırlar aynı sevkiyatta karıştırılamaz.
- Müşteri, satış, lot, konum, birim ve miktar birebir eşleşmelidir. Satış satırı **tamamıyla ve tek sefer** sevk edilir; bu sürümde bölme/kısmi sevkiyat yoktur.
- Bir satışın farklı satırları ayrı sevkiyat başlıklarında taşınabilir. Her satış satırının ve her stok hareketinin en çok bir sevkiyat satırı vardır; DB UNIQUE kısıtları da bunu korur.
- Kaynak stok satış sırasında düşmüştür: bağlı sevkiyat bakiye/maliyet sayaçlarını değiştirmez ve yeni stok hareketi yaratmaz. Kaynak bakiye sıfırken geçerli bir bağlı sevkiyat yapılabilir.
- Gönderim anında lot blok/SKT/konum kontrolü yine kilit altında yapılır. Satış hareketiyle uyuşmayan veya ters hareketi olan satış sevk edilemez.
- Opsiyonel shipped_at atlanırsa ilk commit zamanı alınır; bağlı sevkiyat tarihi satıştan önce olamaz.

Alıcı adı ve iletişim client’tan alınmaz; gerçek party kaydından snapshot olur. Bilinmeyen iletişim **null** saklanır; sonradan party adı/iletişimi değişse de mevcut sevkiyat snapshot’ı değişmez.

## Transaction, kilit ve maliyet

Mevcut commands.execute kullanılır: idempotency kaydı ve bütün iş yazıları tek transaction’dır. Aynı anahtar/kanonik gövde aynı kayıt/HTTP durumunu döndürür; farklı gövde 409. Başarısız transaction anahtarı da rollback eder; düzeltilmiş komut aynı anahtarla yeniden gönderilebilir. Başarılı eski isteğin replay’i yeni işlem değildir; daha sonra bloke edilen lotta da geçmiş cevabın dönmesi yeni stok çıkışı oluşturmaz.

Satış/bağımsız sevkiyat tüm lotları UUID sırasıyla `FOR UPDATE` kilitler. Kaynak yalnız warehouse olabilir; quarantine/external_producer, blokeli ve tarihi geçmiş lotlar reddedilir. Negatif stok, ürün birimi/adet hassasiyeti ve lotun toplam tüketimi denetlenir. Lot maliyeti mevcut kümülatif `consumption_cost` ile tahsis edilir; son çıkış kalan maliyeti tam alır.

Bağlı sevkiyatta lock sırası **sale başlığı → sıralı lotlar → bakiye/claim** şeklindedir. Gelecekteki satış iptali/ters hareket modülü aynı prefix’i kullanmalıdır. Gelecek recall komutu lot kilidini alıp blocked durumunu güncellemelidir; satış blocked kontrolünü bu kilit altında yapar. Bu görev gerçek recall traversal/blok algoritmasını içermez.

ShipmentLine.consumed_cost, bağlı satışın maliyet snapshot’ını tekrar gösterir; yeni gider değildir. Finansal toplamları SaleLine + ShipmentLine toplamı olarak çift saymayın; kesin çıkış olayı tek stock_movement_id’dir. Mevcut stok defteri ve lot tüketim sayaçları bir kez değişir.

### Hata örnekleri

401 hatalı API anahtarı; 422 geçersiz header/gövde, birim/bağlantı/tarih/rol/tutar; 404 olmayan kayıt; 409 yetersiz stok/bloke/SKT/uygun olmayan konum, idempotency çakışması veya tekrar sevk; 503 veritabanı/transaction retry gereksinimi. Domain hata gövdesi mevcut error.code/message/details şeklindedir; Pydantic doğrulaması standart FastAPI detail formatıdır.

## İdempotent yarışma demosu

Boş veya yalnız test/demo amaçlı DB’de migration’ı uygulayın. Backend ile aynı AVATAR_API_KEY process ortamındayken:

```bash
# Repo kökünde; varsayılan hedef 127.0.0.1:8000
PYTHONPATH=backend backend/.venv/bin/python -m app.demo_sales_shipments
# Farklı yerel backend portu için AVATAR_API_BASE_URL kullanılabilir.
```

Komut mevcut `app.demo`’yu değiştirmeden çağırır; onun namespace/anahtarlarını ve üretim JSON sözleşmesini korur. Ardından üç customer, üç satış ve satışlara bağlı üç sevkiyat yaratır. Yeni komutlar ayrı ve sabit v1 demo UUID’leri kullanır. Yarım kalırsa aynı komutla devam edilir; global tek transaction değildir, her API komutu atomiktir. Çakışan kullanıcı verisini silmez/üstüne yazmaz.

| Kurgusal market | Sevk edilen paket |
| --- | --- |
| Market A | 30 |
| Market B | 25 |
| Market C | 30 |

Müşteri adları KURGUSAL DEMO olarak işaretlidir, email’ler ayrılmış `.invalid` alanındadır. 25,00 EUR birim satış fiyatı yalnız **kurgusal demo** değeridir; PDF’de verilmiş VKP değildir.

Üretim toplamı 1543.50, gösterim EKP 18.16 olarak kalır. İlk başarılı çalıştırma sonunda üç yeni sale hareketiyle toplam stok hareketi sayısı 16, işletme mamul bakiyesi 0’dır; sevkiyatlar yeni hareket yaratmaz. İkinci çalıştırma aynı kimlikleri/cevabı verir.

**Sevk edilen miktar = markette kalan stok = son tüketici satışı değildir.** Çıktı market_remaining_quantity ve final_consumer_sold_quantity alanlarında null döndürür; sonraki dağıtımı tahmin etmez.

## Testler ve sonraki entegrasyon

Mevcut iki `_test` şeması yerine kendi izole MySQL instance’ınızı kullanabilirsiniz; destructive testler yalnız *_test DB’ye bağlanmalıdır. Migration testi ayrıca avatar_migration_test şemasını kullanır; bu da aynı izole instance’ta olmalıdır.

```bash
MYSQL_DATABASE=avatar_sales_test AVATAR_MYSQL_TEST=1 AVATAR_CORE_MYSQL_TEST=1 backend/.venv/bin/python -m pytest tests -q
```

Yeni fixture/test kaynakları tests/test_sales_shipments_mysql.py ve tests/test_sales_migrations_mysql.py. Sonuçlar ve ortak doküman/checklist değişiklik istekleri: [database/sales-shipments-validation.md](../database/sales-shipments-validation.md). Frontend OpenAPI tipleri/ekranları ve docs/ sözleşmeleri bu görevde değiştirilmedi.

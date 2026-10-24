# Backend A — alış, stok ve dış üretim çekirdeği

Foundation/backend/frontend/checklist PR’ları main’e birleştirilmiştir. Görev 5, main 6341cfb üzerine lot bazlı satış ve sevkiyat ekler; ayrıntılı yeni sözleşme [SALES_SHIPMENTS.md](SALES_SHIPMENTS.md) içindedir. Yalnız backend/, database/, tests/ değiştirilir; ortak docs/ ve Compose korunur.

## Çalıştırma

Python 3.12, MySQL 8.0.16+ (CHECK enforcement), InnoDB ve requirements-dev.txt gerekir. API süreci şema oluşturmaz; önce Alembic uygulanır.

```bash
# Repo kökünde, kendi güvenilir yerel .env dosyanız mevcutken
python -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
# Bulut makinesinin salt okunur home dizini için gerekirse:
export DOCKER_CONFIG=/tmp/avatar-docker
mkdir -p "$DOCKER_CONFIG"
docker compose up -d mysql
set -a
. ./.env
set +a
# MYSQL_HOST=127.0.0.1; DB sağlıklı duruma gelmeli.
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini check
# AVATAR_API_KEY değerini güvenli ortam ayarından/process ortamından verin.
# Yerel bir anahtar üretmek için değeri ekrana basmadan:
export AVATAR_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

AVATAR_API_KEY process secret’ıdır; Git’e, frontend VITE_* alanlarına veya loglara koymayın. `/health`, `/health/ready`, `/docs`, `/openapi.json` açıktır; tüm `/v1` yolları `X-API-Key` ister. Anahtar yapılandırılmamışsa iş API’si 503, hatalı/eksikse 401 döner. Bu, güvenilir yerel prototip istemcileri için başlangıç korumasıdır; kullanıcı oturumu, rol bazlı yetkilendirme ve TLS sonlandırması henüz uygulanmadı.

Ortak Compose dosyası AVATAR_API_KEY enjekte etmez; entegrasyon sorumlusu bunu güvenli runtime binding ile eklemelidir. Anahtarsız Compose backend health kontrolünü geçse bile iş API’si fail-closed kalır. Mevcut frontend yalnızca açık `/health` kullanır ve değiştirilmedi.

## Uygulanan REST yolları

Backend prefix `/v1`; Vite proxy prefix’i ile web isteği `/api/v1/...` olur. Para/miktar JSON string, EUR sabit, UTC zamanlar. Decimal değerler en çok 6 hane (fatura tutarı 2 hane), adet/paket miktarları tamsayıdır. Pydantic ek alanları reddeder. GET listelerinde limit 1–100 ve UUID cursor vardır; stok cursor’ı `lot_id:location_id` biçimindedir.

| Yol | Davranış |
| --- | --- |
| GET, POST /v1/products | Ürün kartı: sku, name, type, base_unit; paket için package_weight_kg zorunlu. Bu sürümde güncelleme yok; dönüşüm oluşturulduktan sonra sabittir. |
| GET, POST /v1/parties | name, roles (supplier/producer/customer), contact; tedarikçi ve dış üretici bu tek tabloda rollerle ayrılır. |
| GET, POST /v1/locations | name, kind (warehouse/external_producer/quarantine); dış üretici konumu producer party_id ister. |
| GET, POST /v1/receipts | supplier_id, location_id, received_at? (UTC), reference?, lines:[product_id, external_lot_code, quantity, total_cost, expires_at?]. Alış, lot, giriş hareketi ve bakiye atomiktir. |
| GET /v1/receipts/{id} | Alış satırları ve oluşan kesin lot kimlikleri. |
| GET /v1/lots ve /v1/lots/{id} | Lot, gerçek maliyet, başlangıç/tüketim miktarları. Lot doğrudan yaratılamaz; alış veya üretim sonucunda oluşur. |
| GET /v1/stocks | lot_id/product_id/location_id filtreleri; quantity ve available_quantity. Blokeli, tarihi geçmiş veya karantina stok kullanılabilir değildir. |
| GET /v1/stock-movements | lot_id/location_id/operation_id filtreleri; imzalı değişmez defter. |
| GET, POST /v1/operations | code, kind=external_production, producer_id; taslak dış üretim emri. |
| POST /v1/operations/{id}/dispatch | from_location_id, to_location_id, lines:[lot_id,quantity]; kendi depodan emrin üretici konumuna iki eşleşen hareket, tüketim/maliyet değil. |
| POST /v1/operations/{id}/post | consumed_inputs:[lot_id,location_id,quantity], returned_inputs:[lot_id,from_location_id,to_location_id,quantity]?, output_location_id, outputs:[product_id,lot_code,quantity,unit?,expires_at?], service_costs:[amount,currency,invoice_reference?]?, loss_quantity (kg), loss_reason?, allocation_method=quantity. |
| GET /v1/operations/{id} | Kayıtlı tüketim/çıktı/hizmet maliyeti, gerçek kaynak/çıktı lot kimlikleri ve miktarlı lot_links; EKP ve gösterim değerleri. |

Her POST `Idempotency-Key: UUID` ister. Aynı kapsam+anahtar+kanonik gövde aynı HTTP durumunu/cevabını döndürür; farklı gövde 409. Anahtar kaydı iş işlemiyle aynı transaction’da commit edilir; başarısız komut kaydedilmez ve düzeltildikten sonra tekrar kullanılabilir. received_at atlanmış alışın tekrarı yeni timestamp üretmez. Domain hatası `error.code/message/details`; Pydantic 422 doğrulama formatı FastAPI’nin standart formatıdır.

## Stok ve maliyet değişmezleri

1. MySQL izolasyonu READ COMMITTED’dir: idempotency kontrolünden sonra beklenen emir kilidi açıldığında yeni commit edilmiş sevkler görünür. Emir önce, sonra etkilenen lotlar UUID sırasıyla `SELECT ... FOR UPDATE` ile kilitlenir. Yeni stok bakiye satırı da aynı lot kilidi altında oluşturulur. Bakiye satırları ayrıca kilitlenir; DB CHECK negatif stoğu engeller.
2. Sevk edilen miktarın tamamı kapanışta tüketim veya iadeyle açıklanır. Başka emrin aynı üreticideki stoğu tüketilemez. Blok/tarih kontrolü kilit altında tekrar yapılır.
3. Tüketilen kg = çıktı kg + açıkça girilmiş fire/fark kg. Paket dönüşümü ürün kaydına dayanır. Birim türü `unit` için kg dönüşümü yoksa üretim kapanışı reddedilir; bu sürüm yalnızca kg ve ağırlığı kayıtlı paketleri üretimde destekler.
4. İadeler tüketim maliyetine girmez. Kısmi lot maliyeti kümülatif Decimal oranıyla dağıtılır; son tüketimde lotun kalan maliyeti tam alınır. Transfer maliyet tüketmez.
5. Malzeme + gerçek hizmet = çıktı lotlarına dağıtılmış toplam. Birden çok çıktı normalize kg ağırlığıyla dağıtılır; kümülatif yuvarlama toplamı korur, negatif artık üretmez. `unit_cost` 6 haneli, `unit_cost_display` 2 hanelidir; toplam bu gösterimden geri hesaplanmaz.
6. Lot bağlantıları FK ile operation_input/output kayıtlarına gider. Karışımın tüm ortak çıktılarıyla kayıt ilişkisi kurulur; kaydedilen miktar dağıtım kaydıdır, fiziksel molekül ayrımı garantisi değildir. Bağlantı miktarı hassasiyet altında sıfıra düşerse kapanış reddedilir.
7. MySQL deadlock/lock timeout (1213/1205) tüm transaction’ı en çok 3 kez tekrarlar. Kapanmış emir tekrar değiştirilemez; başarılı idempotent replay bunun dışındadır.

Lot bazlı satış ve bağımsız/bağlı sevkiyat Görev 5 ile [uygulanmıştır](SALES_SHIPMENTS.md). Parçalama, recall raporu/blok endpoint’i, değer ağırlıklı dağıtım ve genel transfer endpoint’i bu aşamada yoktur. Şema kind=cutting/rework, çoktan çoğa lot ilişkisi, lot.blocked ve hareket reversal_of alanlarıyla sonraki migration’lara zemin sağlar; bunlar tamamlanmış iş akışları değildir.

## Gerçek HTTP demo

Ayrı terminalde aynı MYSQL_* ve AVATAR_API_KEY process ortamıyla:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.demo
```

Bu komut API üzerinden örnek ürün/tedarikçi/depo/alış, ET-2026-001 lotu, URT-2026-045 emri ve SUC-2026-045 / 85 paket kaydeder. Sabit idempotency anahtarlarıyla tekrar çalıştırılabilir; mevcut çakışan demo kayıtları varsa üstüne yazmaz. Toplam 1543.500000, gösterilen EKP 18.16 ve 3 lot bağlantısını doğrular. Gerçek iş veritabanı yerine demo veritabanında çalıştırın; 22 kg farkın nedeni örnektir, işletme onayı değildir.

## Testler

Varsayılan (MySQL çekirdek testleri açıkça skip):

```bash
backend/.venv/bin/python -m pytest tests -q
```

MySQL çekirdek testleri **veriyi siler**: sadece sonunda `_test` olan ayrı MYSQL_DATABASE kabul edilir. `avatar_core_test` ve `avatar_migration_test` boş şemalarını yönetici oluşturmalı; uygulama kullanıcısına bu iki şemada migration yetkisi vermelidir. Üretim DB parolası/bağlantısı kullanmayın.

```bash
# .env'den MYSQL_* yüklendikten sonra
export MYSQL_DATABASE=avatar_core_test
AVATAR_MYSQL_TEST=1 AVATAR_CORE_MYSQL_TEST=1 backend/.venv/bin/python -m pytest tests -q
```

`avatar_core_test` her test başında temizlenir; `avatar_migration_test` upgrade/downgrade testi için kullanılır. Gerçek MySQL kilit/yarış testleri SQLite ile ikame edilmez. Sonuç raporu database/backend-core-validation.md altındadır.

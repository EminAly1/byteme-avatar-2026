# Görev 6 doğrulama — 24 Ekim 2026

Başlangıç commit’i: `b90fcb28b882dff7e3207f2341a6d96936d214ae` (`main`, PR #1–#6 birleşmiş). Çalışma branch’i `feature/lot-trace-recall`; main’e yazılmadı. Başlangıçta çalışma dizini temizdi; önceki dosyalar korundu. Sadece backend/, database/, tests/ değiştirildi.

## Gerçek ortam ve testler

- Docker `mysql:8.0`; sorgulanan sunucu sürümü **8.0.46**, InnoDB. Bu görev için yeni konteyner ve yeni volume oluşturuldu; mevcut işletme veritabanı kullanılmadı.
- `avatar_trace_test`: veri temizleyen çekirdek testleri. `avatar_migration_test`: yalnız migration upgrade/downgrade. `avatar_trace_demo_test`: HTTP demo. Üçü aynı yeni izole MySQL instance’ında; hepsi `_test` ile biter. Credentials rastgele üretildi, yalnız /tmp içindeki mode 0600 process ortam dosyalarında tutuldu; Git’e/loglara eklenmedi.
- Python 3.12, mevcut backend/.venv bağımlılıkları. SQLite ile kilit testi yapılmadı.
- Başlangıç: **76 passed**, 0 failed, 0 skipped, 13.82 s.
- Bütün testler: **100 passed**, 0 failed, 0 skipped, 24.15 s. Önceki 76 + 24 yeni test; eski test dosyaları/assertion’ları değiştirilmedi. Toplamın **84’ü gerçek MySQL test dosyalarında**, 16’sı DB gerektirmeyen configuration/health/costing vb. testleridir; 100’ünün tamamı DB testi diye sunulmaz.
- Yeni testlerin 23’ü `test_trace_recall_mysql.py`, biri `test_recall_migrations_mysql.py`. Son yarış testi güçlendirmesinde kilit beklenirken Future’ın tamamlanmadığı da doğrulandı; bu modül ayrıca yeniden çalıştırıldı (23 passed).
- Tek uyarı: mevcut Starlette TestClient / AnyIO BlockingPortal deprecation. Test başarısızlığı değildir.

Kullanılan tam test komutu (parola/anahtar dışarıdan güvenli process ortamında):

```bash
MYSQL_DATABASE=avatar_trace_test AVATAR_MYSQL_TEST=1 AVATAR_CORE_MYSQL_TEST=1 \
  backend/.venv/bin/python -m pytest tests -q
```

## Doğrulanan davranışlar

- Tek seviyeli ileri/geri izleme, bütün bileşen miktarları/tedarikçi FK’si; bağlamdaki ortak girdiler etkilenmiş kaynaklar olarak bloke edilmez.
- Farklı kodlarla çok aşamalı ve birleşen üretimler; bir hammaddenin farklı üretimlere girmesi; çoktan çoğa bağlantı. Eksik LotLink miktar kaydı ortak çıktıyı gizlemez, bilinmeyen miktar null’dır.
- Adversarial tarihsel cycle fixture’ında sonlanma ve cycle bayrağı. Bu fixture API üzerinden döngü üretildiği anlamına gelmez.
- Aynı müşteri/lot için tekrarlı sevkiyatlar ve tarihsel iletişim snapshot’ları; aynı isimli farklı UUID müşterileri birleşmez. Satış ve bağlı sevkiyat toplamı iki kez sayılmaz. Satışı olup henüz sevki olmayan alıcı ayrı miktarla gösterilir.
- Gerçek MySQL transaction yarışlarında iki kazanan sırası: recall önce / satış önce, recall önce / üretim önce. SQL event ve Future timeout ile bekleyen writer’ın kilit serbest bırakılmadan tamamlanmadığı doğrulandı.
- Üretim önce kazanıp yeni çıktı commit ettiğinde ilk recall grafı genişler; tüm recall transaction’ı yeniden başlar (iki deneme), yeni lot da bloke edilir. Bir recall kaydı, üç üye kalır.
- Aynı anahtarlı eşzamanlı recall bir kez commit edilir; örtüşen farklı recall’lar tutarlı lot kilidi sırasını kullanır. Blokeli lot yeni satış/bağımsız sevkiyat/üretim/sevk için kullanılamaz.
- Geçersiz istek hiçbir recall/blok/idempotency kaydı bırakmaz. Bloklar flush edildikten sonra **enjekte edilmiş rapor hatası** ile başlık/üyeler/bloklar/anahtarın birlikte rollback edildiği doğrulandı. Bu test gerçek ağ/DB kesintisi değildir. Sürekli GraphChanged sinyali de enjekte edilerek üç deneme sonrası 503 ve temiz rollback doğrulandı; gerçek closure genişlemesi ayrıca yukarıdaki MySQL yarışında test edildi.
- GET snapshot izolasyonu bağlantı havuzundaki sonraki writer’a sızmaz; writer READ COMMITTED kalır.
- Migration: base → head → metadata check → base → head eski testleri de geçti. Yeni v2 → v3 → v2 → v3 testi önceden var olan satış/stokları korur, downgrade bloke bayrağını kaldırmaz. Head **bacb184a30d7**; parent **81f4da20f36b**.

## Gerçek HTTP demo

Uvicorn 127.0.0.1:8006, demo veritabanı ve rastgele iş API anahtarıyla çalıştırıldı. `/health` ve `/health/ready` HTTP 200. Demo veritabanında `alembic upgrade head` ve `alembic check` başarılı; metadata farkı yok.

```bash
AVATAR_API_BASE_URL=http://127.0.0.1:8006 PYTHONPATH=backend \
  backend/.venv/bin/python -m app.demo_recall
```

Komut iki kez çalıştırıldı; çıktılar aynı. Kurgusal örnek sonuç:

| Kontrol | Sonuç |
| --- | --- |
| Üretim zinciri | ET-2026-001 → URT-2026-045 → SUC-2026-045 |
| Toplam üretim maliyeti / gösterilen EKP | 1543.500000 EUR / 18.16 EUR (önceki maliyet testi ve kullanılan üretim demosu korundu) |
| ET ve SUC blocked | true / true |
| Market A sevk | 30.000000 package |
| Market B sevk | 25.000000 package |
| Market C sevk | 30.000000 package |
| Toplam sevk | 85.000000 package |
| Yeni SUC satışı | 409 LOT_BLOCKED |
| Market kalanı / son tüketici satışı | null / null; bilinmiyor |
| İki demo sonrası kayıtlar | 1 Recall, 2 RecallLot, 3 Sale, 3 Shipment, 16 StockMovement |

Rapor HTTP üzerinden gerçek FK ve sevkiyat kayıtlarından üretildi; API’de örneğe özel ET/SUC/A/B/C dallanması yoktur. İkinci demo yeni recall veya stok hareketi üretmedi.

## Kapsam ve entegrasyon devri

İkinci kademe dağıtım kayıt modeli, bildirim e-posta/SMS’i, recall kapatma/blok kaldırma, Android ekranı, frontend rapor ekranı, parçalama ve ML bu görevde uygulanmadı/test edilmedi. Üretim ölçeğinde performans testi yapılmadı. Web/Android uçtan uca akışının tamamlandığı iddia edilmez. Mevcut API anahtarı koruması kullanıcı/rol bazlı production kimlik sistemi değildir.

Entegrasyon sorumlusu ortak docs/data-model.md ve docs/api-contract.md’yi [backend sözleşmesi](../backend/TRACE_RECALL.md) ile güncellemeli. Checklist doğrudan değiştirilmedi: **LOT-06, LOT-07, LOT-08, LOT-09** için tamamlanma kanıtı hazır; **LOT-10, AND-05, DOC-03** kısmi ilerler, tamamı bitmiş sayılamaz. LOT-11 henüz parçalama kabulü gerektirir.

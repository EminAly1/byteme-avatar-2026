# MySQL üretim ve stok çekirdeği

Şema kaynağı `backend/app/models.py`; kurulum kaynağı tek Alembic zinciridir. İlk revision `eeea4b5dd1a8` ürün, parti/tedarikçi, konum/depo, lot, alış/satır, emir/girdi/çıktı, hizmet, lot bağlantısı, stok bakiye/hareketi ve idempotency tablolarını oluşturur. Uygulama açılışında `create_all` yoktur.

```bash
# Repo kökünde MYSQL_* process ortamı yüklüyken
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini check
```

MySQL 8.0.16+ / InnoDB, utf8mb4; Decimal alanlar DECIMAL(18,6), UTC DATETIME(6). Alış/hizmet API tutarları kuruş hassasiyetinde girilir; toplam dağıtımı 6 hanede saklanır. Gerçek lot giriş miktarı/maliyeti sabittir; tüketilen miktar/maliyet kümülatif izlenir. Veri deposu Compose mysql_data volume’udur.

`downgrade base` bütün çekirdek tablolarını ve içlerindeki verileri kaldırır; geliştirme/test dışında yedeksiz çalıştırmayın. MySQL indeksleri FK’lerle birlikte ilgili tablo kaldırıldığında silinir. Upgrade → metadata check → downgrade → tekrar upgrade ayrı `avatar_migration_test` şemasında doğrulanır.

Örnek kayıtları SQL kopyasıyla eklemeyin; `backend/app/demo.py` gerçek HTTP API üzerinden tekrar çalıştırılabilir ET-2026-001 → URT-2026-045 → SUC-2026-045 senaryosunu oluşturur. Market A/B/C sevkiyatları Görev 5, kaynak lotuna göre izleme/recall Görev 6 ile eklendi.

Detaylı çalıştırma/sözleşme: ../backend/README.md. Mevcut ortak docs/data-model.md ve docs/api-contract.md planlama belgeleridir; alan sahipliği nedeniyle bu görevde değiştirilmedi. Gerçek uygulama OpenAPI’si ve backend README bu çekirdek diliminin güncel sözleşmesidir.

## Görev 5 — satış/sevkiyat migration’ı

Görev 5 revision’ı `81f4da20f36b` (parent `eeea4b5dd1a8`). sales/sale_lines/shipments/shipment_lines FK ve unique kısıtlarıyla eklenir; eski stok şeması korunur. Bağımsız sevkiyat stok çıkarır, satışa bağlı sevkiyat mevcut hareketi tek kez sahiplenir. [Sözleşme](../backend/SALES_SHIPMENTS.md) ve [76 testlik kanıt](sales-shipments-validation.md).

## Görev 6 — recall migration’ı

Yeni head `bacb184a30d7` (parent `81f4da20f36b`): recalls / recall_lots. Kaynak ve türev üyeler gerçek lot FK’leriyle kaydedilir. Eski stok/satış kayıtları korunur; downgrade recall audit tablolarını siler, lot bloklarını kaldırmaz. [API ve kilit protokolü](../backend/TRACE_RECALL.md), [gerçek MySQL kanıtı](trace-recall-validation.md).

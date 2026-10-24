# Veritabanı

MySQL 8.0 merkezi otoritedir. ER taslağı: ../docs/data-model.md. SQLAlchemy modelleri ve tek Alembic migration zinciri backend/ altında Ajan A'nın sorumluluğundadır; bu klasöre paralel şema/DDL kopyası eklemeyin.

Şu aşamada yalnızca bağlantı altyapısı vardır; domain tabloları ve örnek senaryo verileri sonraki görevdir. Bootstrap migration domain şeması oluşturmaz. Gelecek seed komutu tekrar çalıştırılabilir olmalı ve PDF'deki ET-2026-001 → URT-2026-045 → SUC-2026-045 → Market A/B/C (30/25/30) kayıtlarını oluşturmalıdır; bu veri henüz yüklenmedi.

Karakter seti utf8mb4; miktarlar DECIMAL(18,6), maliyetler DECIMAL(18,6), tahsilat tutarları DECIMAL(18,2); zamanlar UTC. Tüm tablolar InnoDB. Kalıcı veri Compose mysql_data volume'unda tutulur; `docker compose down -v` veriyi siler.

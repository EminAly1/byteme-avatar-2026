# ByteMe — AVATAR 2026

Gıda üretimi, gerçek maliyet, satış, lot izlenebilirliği ve iki ML çalışması için monorepo temeli. Hedef teslim: **1 Kasım 2026**. Gereksinim kaynağı: [AVATAR_Assessment.pdf](docs/AVATAR_Assessment.pdf).

Bu aşamada FastAPI sağlık uçları, MySQL bağlantısı ve React başlangıcı uygulanmıştır. Üretim, maliyet dağıtımı, lot grafı, satış ve geri çağırma API'leri **tasarımdır**, henüz çalışan iş modülleri değildir. Android ve ML klasörleri yalnızca sonraki geliştirme yönergelerini içerir.

## Yapı ve mimari

```text
backend/       FastAPI, SQLAlchemy, Alembic, Dockerfile
frontend/      React, TypeScript, Vite, Tailwind, Dockerfile
android/       Kotlin/Compose/Room/Retrofit geliştirme yönergesi
ml/            pandas/scikit-learn model ve değerlendirme yönergesi
database/      Şema sahipliği ve örnek veri planı
docs/          Kaynak PDF, ER, REST sözleşmesi, varsayımlar, test raporu
tests/         Backend unit ve opt-in gerçek MySQL testi
```

Başlangıç mimarisi modüler monolittir: Web ve Android → REST/FastAPI → SQLAlchemy → MySQL 8. Room cihaz önbelleği/outbox, MySQL merkezi otoritedir. ML eğitim ve tahmin katmanı gerçek stok/lot kayıtlarını değiştirmez. Gereksiz mikroservis yoktur. Tüm para hesapları backend'de Decimal, DB'de DECIMAL ve API'de string olacaktır. Stok ve lot değişiklikleri tek transaction içinde tutulacaktır.

[AGENTS.md](AGENTS.md) dosya sahipliğini, [data-model.md](docs/data-model.md) ER taslağını, [api-contract.md](docs/api-contract.md) uygulanan ve planlanan API'leri, [assumptions.md](docs/assumptions.md) PDF tutarsızlıklarını açıklar. [requirements.md](docs/requirements.md) gereksinimlerin kapsam ve sahiplik eşlemesidir.

## Docker Compose ile geliştirme

Gerekenler: Docker Engine + Compose v2, boş 3306/8000/5173 portları, Docker Hub/PyPI/npm erişimi. Bu yapı geliştirme içindir; üretim dağıtımı veya kimlik doğrulama henüz yoktur.

```bash
cp .env.example .env
# .env içindeki MYSQL_PASSWORD ve MYSQL_ROOT_PASSWORD değerlerini değiştirin.
docker compose config --quiet
docker compose up --build -d
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:5173/api/health
docker compose ps
```

Web geliştirme portu 5173, API portu 8000; FastAPI OpenAPI arayüzü `/docs`. `/health` yalnızca süreç canlılığını, `/health/ready` gerçek MySQL `SELECT 1` sonucunu ölçer. Frontend `/api/health` çağrısını Vite proxy üzerinden backend'e yollar; ekranda görünen durum DB hazırlık garantisi değildir.

```bash
docker compose logs --tail=100 backend mysql frontend
docker compose stop
# Tekrar başlatma (imajlar oluşturulmuşsa):
docker compose up -d
```

MySQL verisi `mysql_data` volume'unda saklanır. `docker compose down -v` veriyi siler; rutin durdurmada kullanmayın. İlk volume oluşturulduktan sonra .env parolasını değiştirmek DB kullanıcısının parolasını kendiliğinden değiştirmez.

**Bu bulut ortamının sınırı:** MySQL container'ı gerçekten çalıştırıldı; backend/frontend Docker build'lerinde bağımlılık indirme adımı container DNS/proxy çözümleme hatası aldı. Tam üç-container akışı doğrulanamadı. Buna karşılık aynı MySQL'e host üzerinde çalışan backend ve frontend ile erişim başarılıdır. Sertifika/TLS doğrulaması kapatılmadı. Ayrıntılar [test-results.md](docs/test-results.md).

## Yerel geliştirme — bu ortamda doğrulanan yol

Python 3.12 ve Node 24 ile doğrulandı (frontend Node >=22.12 ister). MySQL için Docker kullanın. Repoda gerçek .env yoksa yukarıdaki örneği kopyalayıp değiştirin. Aşağıdaki shell yüklemesi yalnızca kendi güvenilir yerel .env dosyanız içindir.

```bash
# Repo kökünde
python -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
docker compose up -d mysql
set -a
. ./.env
set +a
# MYSQL_HOST yerel geliştirmede 127.0.0.1 olmalı.
cd backend
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Ayrı terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite proxy varsayılanı `http://127.0.0.1:8000`; gerekirse `frontend/.env.example` üzerinden `VITE_API_PROXY_TARGET` değiştirilebilir. `VITE_*` değerleri sır içeremez.

Salt okunur home dizinine sahip bu bulut makinesinde paket/Docker CLI önbellekleri için gerektiğinde `PIP_CACHE_DIR=/tmp/avatar-pip-cache`, `npm_config_cache=/tmp/avatar-npm-cache` ve `DOCKER_CONFIG=/tmp/avatar-docker` kullanın. Bunlar uygulama değişkeni değildir; export edilerek yukarıdaki komutlar çalıştırılabilir.

## Test ve build

```bash
# Repo kökünde: MySQL gerektirmeyen kontroller (9 passed, 1 skipped beklenir)
backend/.venv/bin/python -m pytest tests -q
backend/.venv/bin/python -m pip check

# Gerçek MySQL 8 çalışırken; .env process'e yukarıdaki gibi yüklenmiş olmalı
AVATAR_MYSQL_TEST=1 backend/.venv/bin/python -m pytest tests -q
# Bu çalışmada: 10 passed, 1 deprecation warning

cd frontend
npm run typecheck
npm run build
```

Alembic altyapısı `backend/alembic.ini` altındadır. `cd backend && .venv/bin/alembic heads` şu anda boştur: henüz domain migration yoktur. Şema Ajan A tarafından migration olarak eklenecek; başlangıçta otomatik `create_all` yoktur.

Testler şu an maliyet/stock/recall iş mantığını doğrulamaz; bu iş mantığı henüz uygulanmadı. Android SDK/Gradle build'i, ML eğitim/evaluasyon ve tarayıcı otomasyonu bu aşamada çalıştırılmadı.

## Sonraki üç paralel görev

1. **A — Backend/veri:** ER'den Alembic tabloları; alış/lot ve üretim/parçalama gerçek maliyeti; idempotent stok transaction'ları; ET-2026-001 geri çağırma senaryosu ve MySQL yarış testleri.
2. **B — Web:** sözleşme üzerinden alış/üretim/parçalama formları, maliyet ve lot/recall raporları; backend hesaplarını gösterme, iş mantığı kopyalamama.
3. **C — Android/ML:** önce Kotlin satış + Room outbox + Retrofit onay/çatışma akışı; sonra iki ML modeli, baseline karşılaştırması, MAE ve veri sınırlamaları.

Ortak sözleşme dosyalarında tek yazar kuralı AGENTS.md'dedir. Üç uçtan uca demo ve zorunlu ML değerlendirmesi teslim öncesi ayrı kabul kapılarıdır. Bu foundation tek başına yarışma teslimi değildir.

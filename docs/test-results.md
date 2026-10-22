# Foundation doğrulama raporu

Tarih: 22 Ekim 2026. İlk doğrulama branch’i: feature/avatar-foundation; yeniden doğrulama ve yayın hazırlığı: setup/project-foundation. PDF 3 sayfa olarak pdftotext ile okundu ve kaynak dosya docs/ altında saklandı.

| Kontrol | Gerçek sonuç |
| --- | --- |
| pytest: config, health, DB yardımcıları | 9 test geçti; readiness başarılı/hatalı dalları mock içerir, DB yardımcı testi SQLite kullanır |
| pytest: gerçek MySQL opt-in dahil | `AVATAR_MYSQL_TEST=1 ... pytest tests -q`: **10 passed**, 1 Starlette/anyio deprecation uyarısı; MySQL 8.0.46 ve gerçek readiness doğrulandı |
| pip check | No broken requirements found |
| Alembic heads | Boş; henüz domain migration yok, şema kurulmuş sayılmaz |
| npm ci | Başarılı, package-lock.json ile |
| npm run typecheck | Başarılı |
| npm run build | Başarılı (Vite üretim çıktısı); browser iş akışı testi değildir |
| docker compose config --quiet | Başarılı |
| MySQL container | mysql:8.0 çekildi, 8.0.46 çalıştı; normal app kullanıcısıyla SELECT VERSION(),1 başarılı |
| Gerçek host Uvicorn GET /health | HTTP 200, status=ok |
| Gerçek host Uvicorn GET /health/ready | HTTP 200, status=ok,database=ok; MySQL container'ına TCP bağlantısı |
| Gerçek Vite GET / ve /src/App.tsx | HTTP 200 HTML ve dönüştürülmüş React/TypeScript modülü |
| Gerçek Vite GET /api/health | HTTP 200 status=ok; Vite→FastAPI proxy doğrulandı |
| Docker backend/frontend imajları | **Başarısız:** build içinden paket registry/proxy DNS çözümlemesi; build network=host ve proxy build args ile tanı denendi. TLS doğrulama kapatılmadı. Tam Compose stack hazır denemez |

MySQL çalıştırılmadığında `AVATAR_MYSQL_TEST` verilmez: 9 passed, 1 skipped beklenir. Bu skip açıkça görünür; MySQL testinin yerine geçmez.

Çalıştırılmayanlar: tarayıcı otomasyonu/ekran etkileşimi; Android (kod, Gradle wrapper ve SDK yapılandırması yok); ML (kod/veri/model yok); domain migration, maliyet/stock concurrency, lot ve recall uçtan uca demoları (henüz uygulanmadı). Bunlar environment test başarısı diye sunulmaz.

Eksik/engelli noktalar: container build ağı erişimi çözülmeden üç servisli Docker build doğrulanamaz. Android ve ML araç/bağımlılık sürümleri ilgili ilk geliştirme PR'ında sabitlenip kurulmalıdır. İşletme maliyet/yan ürün politikalarının varsayımları ayrıca doğrulanmalıdır.

## Commit/push hazırlığında yeniden doğrulama — 22 Ekim 2026

- Uzak `origin/main`, `f263f19` commit’ine ilerlemişti; yalnızca `docs` adlı bir satırlık boş dosya eklenmişti. Aynı içerik `docs/main-placeholder.txt` altında korunarak foundation branch’i bu main üzerine taşındı. Main değiştirilmedi.
- MySQL kapalıyken varsayılan pytest: **9 passed, 1 skipped, 1 warning**. MySQL container’ı başlatıldıktan sonra opt-in dahil: **10 passed, 1 warning**.
- `pip check`, `alembic heads` (boş), `npm run typecheck`, `npm run build`, `docker compose config --quiet` yeniden çalıştırıldı ve başarılı.
- Yeni host Uvicorn/Vite süreçleriyle `/health`, `/health/ready`, `/openapi.json`, frontend HTML/TSX ve proxy `/api/health` HTTP 200 ve beklenen içerikle doğrulandı.
- Önceki tam Docker imaj build denemelerinin DNS/proxy hatası tarihsel sonuçtur; bu görevde imaj build’i yeniden denenmedi. MySQL container’ı + host backend/frontend yolu tekrar doğrulandı.
- Git okuma ve main fetch başarılı. GitHub API bağlantısında HTTP CONNECT 403 (egress proxy) görüldü; bu sonuç tek başına repository PR yetkisinin olmadığını kanıtlamaz.
- Secret kontrolü commit index’inde yapılır: gerçek `.env` dosyaları ve build/cache çıktıları dışarıda kalır; örnek parolalar yalnızca `.env.example` dosyalarındadır, test dosyasındaki parola sabit bir test verisidir.

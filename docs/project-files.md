# Proje dosyaları envanteri

Önceki foundation çalışması korunarak incelendi. Aşağıdaki liste kaynak, yapılandırma, doküman ve test dosyalarının tamamıdır. `.env`, `.venv`, `node_modules`, `dist` ve cache çıktıları dahil değildir.

README.md ve .gitignore mevcut dosyalar güncellenerek hazırlandı; diğer foundation dosyaları önceki görevde oluşturuldu. Bu görevde `docs/main-placeholder.txt`, uzak main’deki boş `docs` dosyasının içerik değişmeden taşınmış halidir; bu envanter ise yeni eklenmiştir.

```text
.env.example
.gitignore
AGENTS.md
README.md
android/README.md
backend/.dockerignore
backend/Dockerfile
backend/alembic.ini
backend/alembic/env.py
backend/alembic/script.py.mako
backend/alembic/versions/.gitkeep
backend/app/__init__.py
backend/app/config.py
backend/app/database.py
backend/app/main.py
backend/requirements-dev.txt
backend/requirements.txt
database/README.md
docker-compose.yml
docs/AVATAR_Assessment.pdf
docs/api-contract.md
docs/assumptions.md
docs/data-model.md
docs/main-placeholder.txt
docs/project-files.md
docs/requirements.md
docs/test-results.md
frontend/.dockerignore
frontend/.env.example
frontend/Dockerfile
frontend/index.html
frontend/package-lock.json
frontend/package.json
frontend/src/App.tsx
frontend/src/main.tsx
frontend/src/style.css
frontend/tsconfig.json
frontend/vite.config.ts
ml/README.md
tests/conftest.py
tests/test_config.py
tests/test_database.py
tests/test_health.py
tests/test_mysql_integration.py
```

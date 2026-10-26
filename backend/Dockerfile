FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
# Optional CA is supplied by BuildKit, never copied into an image layer.
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY ml/models ./ml/models
RUN chmod -R a+rX /app && useradd --create-home avatar
USER avatar
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

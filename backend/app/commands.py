"""Idempotent transactions. Duplicate-key waits serialize identical commands."""
import hashlib
import json
import time
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.database import get_engine
from app.errors import DomainError, GraphChanged
from app.models import IdempotencyRequest


def canonical(value):
    if isinstance(value, Decimal):
        return format(value.normalize(), 'f')
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value) if not isinstance(value, (str, int, bool, type(None))) else value


def replay(record, digest):
    if record.request_hash != digest:
        raise DomainError('IDEMPOTENCY_CONFLICT', 'Aynı anahtar farklı istekle kullanıldı')
    return record.response, record.http_status


def execute(scope, key, payload, action, status=201):
    digest = hashlib.sha256(json.dumps(canonical(payload.model_dump()), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    try:
        engine = get_engine()
    except ValueError:
        raise DomainError('DATABASE_UNAVAILABLE', 'Veritabanı yapılandırılmamış', 503) from None
    for attempt in range(3):
        try:
            with Session(engine, expire_on_commit=False) as db, db.begin():
                record = db.get(IdempotencyRequest, (scope, str(key)))
                if record:
                    return replay(record, digest)
                record = IdempotencyRequest(scope=scope, key=str(key), request_hash=digest)
                db.add(record)
                db.flush()  # Unique PK waits for a concurrent winning transaction.
                body = action(db, payload)
                record.response, record.http_status = body, status
                db.flush()
            return body, status
        except IntegrityError:
            # The losing INSERT was rolled back; a new transaction sees winner.
            with Session(engine) as db:
                record = db.get(IdempotencyRequest, (scope, str(key)))
                if record:
                    return replay(record, digest)
            raise DomainError('CONFLICT', 'Benzersiz kayıt veya ilişki kısıtı ihlal edildi') from None
        except GraphChanged:
            # No additional out-of-order locks: discard the old closure, its
            # idempotency row and all effects before acquiring the enlarged set.
            if attempt == 2:
                raise DomainError('TRANSACTION_RETRY', 'Lot grafı değişti; aynı idempotency anahtarıyla tekrar deneyin', 503) from None
            time.sleep(0.02 * (attempt+1))
        except OperationalError as exc:
            errno = getattr(exc.orig, 'args', [None])[0]
            if errno not in (1205, 1213):
                raise
            if attempt == 2:
                raise DomainError('TRANSACTION_RETRY', 'Transaction tekrar denenmeli; aynı idempotency anahtarını kullanın', 503) from None
            time.sleep(0.02 * (attempt+1))

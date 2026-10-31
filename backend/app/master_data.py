"""Small master-data edits; immutable inventory/accounting records are never changed."""
from sqlalchemy import JSON, func, select
from app import models as m, services
from app.errors import DomainError


def locked(db, model, record_id):
    row = db.scalar(select(model).where(model.id == str(record_id)).with_for_update())
    if row is None:
        raise DomainError('NOT_FOUND', 'Kayıt bulunamadı; listeyi yenileyin.', 404)
    return row


def update(db, model, record_id, payload):
    row = locked(db, model, record_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.flush()
    return services.entity(row)


def referenced(db, model, record_id):
    # Parent X-lock serializes FK insertion/deletion. Actual InnoDB FKs remain
    # the last line of defence if another transaction began before our read.
    for table in m.Base.metadata.sorted_tables:
        for column in table.columns:
            if any(fk.column.table.name == model.__tablename__ for fk in column.foreign_keys):
                if db.execute(select(column).where(column == str(record_id)).limit(1)).first():
                    return True
        # Draft rework plans/prediction contexts also keep IDs in JSON snapshots.
        # Command receipts are audit/idempotency history, not live business FKs.
        if table.name != m.IdempotencyRequest.__tablename__:
            for column in table.columns:
                if isinstance(column.type, JSON):
                    if db.execute(select(column).where(func.json_search(column, 'one', str(record_id)).is_not(None)).limit(1)).first():
                        return True
    return False


def delete(db, model, record_id):
    row = locked(db, model, record_id)
    if referenced(db, model, record_id):
        raise DomainError('MASTER_IN_USE', 'Bu kayıt iş kayıtlarında veya başka bir kartta kullanılıyor. Geçmişi korumak için silinemez.', 409)
    result = {'id': row.id, 'deleted': True}
    db.delete(row)
    db.flush()
    return result

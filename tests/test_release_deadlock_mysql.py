"""Force a real InnoDB deadlock to verify transaction rollback + retry."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import event, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import models as m
from app.commands import execute
from app.commands import get_engine as command_engine
from app.errors import DomainError

pytestmark = pytest.mark.skipif(os.getenv('AVATAR_CORE_MYSQL_TEST') != '1', reason='Dedicated *_test MySQL schema required')


class Payload(BaseModel):
    label: str


def test_real_deadlock_rolls_back_victim_and_retries_same_command(mysql_core):
    with Session(mysql_core) as db, db.begin():
        assert db.scalar(text('SELECT @@innodb_deadlock_detect')) == 1
        rows = [m.Location(name='KURGUSAL deadlock A', kind='warehouse'), m.Location(name='KURGUSAL deadlock B', kind='warehouse')]
        db.add_all(rows); db.flush(); ids = [r.id for r in rows]
    barrier = Barrier(2); calls = [0, 0]; errors = []

    def capture(context):
        if getattr(context.original_exception, 'args', (None,))[0] == 1213:
            errors.append(1213)

    # Other regression cases intentionally clear the cached engine. Observe the
    # engine execute() actually uses, rather than a prior fixture connection.
    observed_engine = command_engine()
    assert observed_engine.url.database == mysql_core.url.database
    event.listen(observed_engine, 'handle_error', capture)
    keys = [str(uuid4()), str(uuid4())]
    scope = 'release-deadlock'

    def worker(index):
        def action(db, payload):
            calls[index] += 1
            first = db.scalar(select(m.Location).where(m.Location.id == ids[index]).with_for_update())
            first.name += ' committed'
            db.flush()
            if calls[index] == 1:
                barrier.wait(timeout=10)
            second = db.scalar(select(m.Location).where(m.Location.id == ids[1-index]).with_for_update())
            second.name += ' committed'
            return {'label': payload.label}
        return execute(scope, keys[index], Payload(label=str(index)), action)

    try:
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(worker, i) for i in range(2)]
            assert [f.result(timeout=20) for f in futures] == [({'label': '0'}, 201), ({'label': '1'}, 201)]
        assert errors and sorted(calls) == [1, 2]
        with Session(mysql_core) as db:
            assert all(db.get(m.Location, id).name.count(' committed') == 2 for id in ids)
            assert all(db.get(m.IdempotencyRequest, (scope, key)).http_status == 201 for key in keys)
        # Replaying the victim does not execute its action or append a third effect.
        assert worker(calls.index(2)) == ({'label': str(calls.index(2))}, 201)
        assert sorted(calls) == [1, 2]
    finally:
        event.remove(observed_engine, 'handle_error', capture)


def test_retry_exhaustion_is_bounded_and_leaves_no_partial_command(mysql_core, monkeypatch):
    # Controlled driver error checks the bound; the preceding test supplies the
    # real two-connection InnoDB deadlock evidence.
    attempts = []
    monkeypatch.setattr('app.commands.time.sleep', lambda _: None)
    key = str(uuid4()); scope = 'release-exhaustion'
    def action(db, payload):
        attempts.append(1)
        db.add(m.Location(name='must roll back', kind='warehouse')); db.flush()
        raise OperationalError('controlled deadlock', {}, Exception(1213, 'controlled test'))
    with pytest.raises(DomainError) as caught:
        execute(scope, key, Payload(label='test'), action)
    assert caught.value.code == 'TRANSACTION_RETRY' and len(attempts) == 3
    with Session(mysql_core) as db:
        assert db.get(m.IdempotencyRequest, (scope, key)) is None
        assert not db.scalars(select(m.Location)).all()

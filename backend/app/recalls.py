"""Monotonic recalls with a locked, revalidated forward closure."""
import hashlib
import json

from sqlalchemy import select

from app import lot_graph as graph, models as m, services, traceability
from app.errors import DomainError, GraphChanged


def fingerprint(report):
    # Bind the whole recorded impact, including source identity, blocked status,
    # stock locations/quantities, shipments and second-tier evidence. No TTL or
    # artificial wait. A fresh review is required if any of these changes.
    encoded = json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return 'recall-v1:' + hashlib.sha256(encoded).hexdigest()


def preview(db, source_id):
    # Coherent read-only snapshot: no command/idempotency/recall row is written.
    db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
    services.get(db, m.Lot, source_id)
    report = traceability.report(db, source_id, graph.walk(db, source_id))
    return {'preview_fingerprint': fingerprint(report), 'report': report}


def create_recall(db, request):
    services.get(db, m.Lot, request.source_lot_id)
    before = graph.walk(db, request.source_lot_id)
    lots = services.lock_lots(db, before.lot_ids)
    after = graph.walk(db, request.source_lot_id)
    if before.lot_ids != after.lot_ids:
        # A production holding an input lock won the race. Its newly committed
        # children require a fresh globally sorted lock set, never extra locks
        # tacked onto the current transaction.
        raise GraphChanged()
    if getattr(request, 'preview_fingerprint', None) is not None:
        source = lots[str(request.source_lot_id)]
        if source.external_code != request.confirmation_lot_code:
            raise DomainError('RECALL_SOURCE_MISMATCH', 'Kaynak lot kodu eşleşmiyor; kaynağı yeniden inceleyin')
        current = traceability.report(db, request.source_lot_id, after)
        if fingerprint(current) != request.preview_fingerprint:
            raise DomainError('RECALL_PREVIEW_STALE', 'Kaynak veya etki kapsamı değişti; güncel önizlemeyi yeniden inceleyin')
    recall = m.Recall(source_lot_id=str(request.source_lot_id), reason=request.reason)
    db.add(recall)
    db.flush()
    for lot_id in sorted(after.lot_ids):
        lots[lot_id].blocked = True
        db.add(m.RecallLot(recall_id=recall.id, lot_id=lot_id))
    db.flush()
    return render(db, recall, after)


def render(db, recall, traversal):
    return {**services.entity(recall), 'membership_scope': 'frozen_at_creation',
            'report_scope': 'current_recorded_stocks_and_distribution',
            'report': traceability.report(db, recall.source_lot_id, traversal)}


def recall_detail(db, recall_id):
    db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
    recall = services.get(db, m.Recall, recall_id)
    membership = frozenset(db.scalars(select(m.RecallLot.lot_id).where(m.RecallLot.recall_id == recall.id)))
    # Membership is persisted, not recomputed or widened by a GET request.
    operation_ids = graph.walk(db, recall.source_lot_id).operation_ids
    return render(db, recall, graph.Walk(membership, operation_ids))

"""Monotonic recalls with a locked, revalidated forward closure."""
from sqlalchemy import select

from app import lot_graph as graph, models as m, services, traceability
from app.errors import GraphChanged


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

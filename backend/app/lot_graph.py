"""Iterative FK traversal. Shared operations conservatively connect all outputs.

LotLink stores recorded quantity allocation, not proof of physical separation.
No guessed quantity or external lot code participates in reachability.
"""
from collections import deque
from dataclasses import dataclass

from sqlalchemy import select

from app import models as m


@dataclass(frozen=True)
class Walk:
    lot_ids: frozenset[str]
    operation_ids: frozenset[str]


def chunks(values, size=400):
    values = sorted(set(values))
    for i in range(0, len(values), size):
        yield values[i:i+size]


def rows_for(db, model, column, values):
    rows = []
    for batch in chunks(values):
        rows.extend(db.scalars(select(model).where(column.in_(batch))))
    return sorted(rows, key=lambda x: x.id)


def walk(db, source_id, direction='forward'):
    seen, operations, frontier = {str(source_id)}, set(), {str(source_id)}
    src, dst = (m.OperationInput, m.OperationOutput) if direction == 'forward' else (m.OperationOutput, m.OperationInput)
    while frontier:
        discovered = {r.operation_id for r in rows_for(db, src, src.lot_id, frontier)} - operations
        operations.update(discovered)
        frontier = {r.lot_id for r in rows_for(db, dst, dst.operation_id, discovered)} - seen
        seen.update(frontier)
    return Walk(frozenset(seen), frozenset(operations))


def has_cycle(lot_ids, edges):
    """Kahn's algorithm also handles converging paths and repeated edges."""
    adjacent = {lot: set() for lot in lot_ids}
    indegree = dict.fromkeys(lot_ids, 0)
    for edge in edges:
        a, b = edge['input_lot_id'], edge['output_lot_id']
        if a in adjacent and b in adjacent and b not in adjacent[a]:
            adjacent[a].add(b)
            indegree[b] += 1
    pending = deque(sorted(k for k, v in indegree.items() if v == 0))
    visited = 0
    while pending:
        visited += 1
        for child in sorted(adjacent[pending.popleft()]):
            indegree[child] -= 1
            if indegree[child] == 0:
                pending.append(child)
    return visited != len(lot_ids)

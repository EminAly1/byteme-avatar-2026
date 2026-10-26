"""Read reports over recorded production and first-tier distribution only."""
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from app import lot_graph as graph, models as m, services
from app.errors import DomainError


def quantity(value):
    return format(value, '.6f')


def distribution(db, lot_ids):
    from app import inventory_adjustments as adjustments
    sale_lines = graph.rows_for(db, m.SaleLine, m.SaleLine.lot_id, lot_ids)
    shipment_lines = graph.rows_for(db, m.ShipmentLine, m.ShipmentLine.lot_id, lot_ids)
    sales = graph.rows_for(db, m.Sale, m.Sale.id, [x.sale_id for x in sale_lines])
    shipments = graph.rows_for(db, m.Shipment, m.Shipment.id, [x.shipment_id for x in shipment_lines])
    sale_map, ship_map = {x.id: x for x in sales}, {x.id: x for x in shipments}
    parties = graph.rows_for(db, m.Party, m.Party.id, [x.customer_id for x in sales+shipments])
    buyers = {p.id: {'customer_id': p.id, 'current_customer': services.entity(p), 'recipient_snapshots': [], 'quantities': []} for p in parties}
    totals = defaultdict(Decimal)
    groups = {}
    shipped_movements = set()
    linked_sale_lines = {x.sale_line_id for x in shipment_lines if x.sale_line_id}
    returns = graph.rows_for(db, m.CustomerReturnLine, m.CustomerReturnLine.lot_id, lot_ids)
    cancellations = graph.rows_for(db, m.SaleCancellationLine, m.SaleCancellationLine.lot_id, lot_ids)
    returned_quantities, cancelled_quantities = defaultdict(Decimal), defaultdict(Decimal)
    for row in returns:
        returned_quantities[row.sale_line_id] += row.quantity
    for row in cancellations:
        cancelled_quantities[row.sale_line_id] += row.quantity

    def group(customer_id, line):
        key = (customer_id, line.lot_id, line.product_id, line.unit)
        if key not in groups:
            groups[key] = {'lot_id': line.lot_id, 'product_id': line.product_id, 'unit': line.unit,
                           'recorded_sale_quantity': Decimal(0), 'unshipped_sale_quantity': Decimal(0),
                           'shipped_quantity': Decimal(0), 'sale_line_ids': [], 'shipment_line_ids': []}
            groups[key].update(returned_quantity=Decimal(0), cancelled_sale_quantity=Decimal(0))
        return groups[key]

    for line in sale_lines:
        entry = group(sale_map[line.sale_id].customer_id, line)
        entry['recorded_sale_quantity'] += line.quantity
        entry['returned_quantity'] += returned_quantities[line.id]
        entry['cancelled_sale_quantity'] += cancelled_quantities[line.id]
        if line.id not in linked_sale_lines:
            entry['unshipped_sale_quantity'] += line.quantity - cancelled_quantities[line.id]
        entry['sale_line_ids'].append(line.id)
    for shipment in shipments:
        buyers[shipment.customer_id]['recipient_snapshots'].append({
            'shipment_id': shipment.id, 'shipped_at': services.entity(shipment)['shipped_at'],
            'recipient_name': shipment.recipient_name, 'recipient_contact': shipment.recipient_contact})
    for line in shipment_lines:
        entry = group(ship_map[line.shipment_id].customer_id, line)
        entry['shipment_line_ids'].append(line.id)
        # A linked sale and shipment share one movement. Only shipment lines
        # establish shipped quantity; never add sales to this total.
        if line.stock_movement_id not in shipped_movements:
            shipped_movements.add(line.stock_movement_id)
            entry['shipped_quantity'] += line.quantity
            totals[(line.product_id, line.unit)] += line.quantity
    for (customer_id, *_), entry in sorted(groups.items()):
        # This is only the recorded shipped-minus-returned balance. It is not
        # the customer's remaining stock or proof of end-consumer sales.
        entry['recorded_delivery_less_returns_quantity'] = entry['shipped_quantity'] - entry['returned_quantity']
        buyers[customer_id]['quantities'].append({k: quantity(v) if isinstance(v, Decimal) else v for k, v in entry.items()})
    return_headers = graph.rows_for(db, m.CustomerReturn, m.CustomerReturn.id, [x.return_id for x in returns])
    cancellation_headers = graph.rows_for(db, m.SaleCancellation, m.SaleCancellation.id, [x.cancellation_id for x in cancellations])
    return {
        'sales': [{**services.entity(s), 'line_scope': 'affected_lots_only', 'lines': [services.entity(x) for x in sale_lines if x.sale_id == s.id]} for s in sales],
        'shipments': [{**services.entity(s), 'line_scope': 'affected_lots_only', 'lines': [services.entity(x) for x in shipment_lines if x.shipment_id == s.id]} for s in shipments],
        'buyers': [buyers[k] for k in sorted(buyers)],
        'customer_returns': [{**adjustments.correction_summary(row), 'line_scope': 'affected_lots_only',
                              'lines': [services.entity(line) for line in returns if line.return_id == row.id]}
                             for row in return_headers],
        'sale_cancellations': [{**adjustments.correction_summary(row), 'line_scope': 'affected_lots_only',
                                'lines': [services.entity(line) for line in cancellations if line.cancellation_id == row.id]}
                               for row in cancellation_headers],
        'total_shipped_quantities': [{'product_id': p, 'unit': u, 'quantity': quantity(q)} for (p, u), q in sorted(totals.items())],
        'second_tier_distributions': [],
        'unknown_distributions': [{'customer_id': k, 'market_remaining_quantity': None, 'final_consumer_sold_quantity': None,
                                   'second_tier_recipients': None} for k in sorted(buyers)],
        'distribution_scope': 'Recorded company-to-customer deliveries only; no second-tier records exist in this schema. Shipped quantity is not market remaining stock or end-consumer sales.',
    }


def report(db, source_id, traversal, direction='forward'):
    services.get(db, m.Lot, source_id)
    # Include dispatched draft orders, without inventing unposted output lots.
    movements = graph.rows_for(db, m.StockMovement, m.StockMovement.lot_id, traversal.lot_ids)
    transfers = graph.rows_for(db, m.StockTransfer, m.StockTransfer.lot_id, traversal.lot_ids)
    operation_ids = set(traversal.operation_ids) | {x.operation_id for x in movements if x.operation_id}
    operations = graph.rows_for(db, m.Operation, m.Operation.id, operation_ids)
    inputs = graph.rows_for(db, m.OperationInput, m.OperationInput.operation_id, operation_ids)
    outputs = graph.rows_for(db, m.OperationOutput, m.OperationOutput.operation_id, operation_ids)
    context_ids = {x.lot_id for x in inputs+outputs} - traversal.lot_ids
    all_lots = graph.rows_for(db, m.Lot, m.Lot.id, traversal.lot_ids | context_ids)
    products = {x.id: services.entity(x) for x in graph.rows_for(db, m.Product, m.Product.id, [x.product_id for x in all_lots])}
    suppliers = {x.id: services.entity(x) for x in graph.rows_for(db, m.Party, m.Party.id, [x.supplier_id for x in all_lots if x.supplier_id])}
    lot_map = {x.id: x for x in all_lots}
    lots = {x.id: {**services.entity(x), 'product': products[x.product_id], 'supplier': suppliers.get(x.supplier_id)} for x in all_lots}
    links = graph.rows_for(db, m.LotLink, m.LotLink.input_id, [x.id for x in inputs])
    link_map = {(x.input_id, x.output_id): x for x in links}
    edges = []
    inputs_by_op, outputs_by_op = defaultdict(list), defaultdict(list)
    for row in inputs:
        inputs_by_op[row.operation_id].append(row)
    for row in outputs:
        outputs_by_op[row.operation_id].append(row)
    for op_id in sorted(traversal.operation_ids):
        for src in inputs_by_op[op_id]:
            for dst in outputs_by_op[op_id]:
                link = link_map.get((src.id, dst.id))
                edges.append({'operation_id': op_id, 'input_id': src.id, 'output_id': dst.id,
                              'input_lot_id': src.lot_id, 'output_lot_id': dst.lot_id,
                              'consumed_input_quantity': quantity(src.quantity), 'output_quantity': quantity(dst.quantity),
                              'lot_link_id': link.id if link else None,
                              'attributed_input_quantity': quantity(link.attributed_input_quantity) if link else None,
                              'basis': 'recorded_shared_operation_all_outputs',
                              'physical_separation_verified': False})
    stocks = []
    for batch in graph.chunks(traversal.lot_ids):
        rows = db.execute(select(m.StockBalance, m.Location).join(m.Location, m.Location.id == m.StockBalance.location_id)
                          .where(m.StockBalance.lot_id.in_(batch)).order_by(m.StockBalance.lot_id, m.StockBalance.location_id))
        for balance, location in rows:
            lot = lot_map[balance.lot_id]
            unavailable = location.kind == 'quarantine'
            try:
                services.usable(lot)
            except DomainError:
                unavailable = True
            stocks.append({**services.entity(balance), 'product_id': lot.product_id, 'unit': products[lot.product_id]['base_unit'],
                           'location': services.entity(location), 'blocked': lot.blocked,
                           'available_quantity': '0.000000' if unavailable else quantity(balance.quantity)})
    return {
        'source_lot': lots[str(source_id)], 'direction': direction,
        'lots': [lots[k] for k in sorted(traversal.lot_ids)],
        'context_lots': [lots[k] for k in sorted(context_ids)],
        'affected_finished_lot_ids': sorted(k for k in traversal.lot_ids if lots[k]['product']['type'] != 'raw'),
        'operations': [{**services.entity(op), 'inputs': [services.entity(x) for x in inputs_by_op[op.id]],
                        'outputs': [services.entity(x) for x in outputs_by_op[op.id]]} for op in operations],
        'edges': edges, 'cycle_detected': graph.has_cycle(traversal.lot_ids, edges),
        'stocks': stocks,
        'blocked_stocks': [x for x in stocks if x['blocked'] and Decimal(x['quantity']) > 0],
        'transfers': [services.entity(row) for row in transfers],
        **distribution(db, traversal.lot_ids),
    }


def trace(db, source_id, direction):
    # A coherent read-only snapshot; no writer inherits this isolation override.
    db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
    services.get(db, m.Lot, source_id)
    return report(db, source_id, graph.walk(db, source_id, direction), direction)

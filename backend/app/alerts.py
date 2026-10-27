"""Current read-only operational evaluation. No persistence, inference or commands.

Bounded keyset source batches and fixed batch joins avoid per-record queries.
Only one visible page is retained; counts stream over the same DB snapshot.
"""
import base64
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, exists, func, or_, select, tuple_
from sqlalchemy.orm import aliased

from app import models as m
from app.config import get_settings
from app.errors import DomainError
from app.ml_runtime import LIMITATIONS, ModelUnavailable, load_model
from app.predictions import decimal_text

BATCH_SIZE = 250
NAMESPACE = UUID('ed0c32ad-98c4-5043-9a85-83e5d2b7c017')
RULES = ('EXPIRY_PAST', 'EXPIRY_SOON', 'LOT_BLOCKED_STOCK', 'LOW_AVAILABLE_STOCK',
         'PRODUCTION_EKP_DEVIATION', 'YIELD_DEVIATION')
ISTANBUL = ZoneInfo('Europe/Istanbul')
ZERO = Decimal(0)


def clock():
    return datetime.now(timezone.utc)


def policy(settings):
    value = {'version': settings.avatar_alert_policy_version, 'expiry_days': settings.avatar_alert_expiry_days,
             'cost_percent': decimal_text(settings.avatar_alert_cost_percent), 'yield_percent': decimal_text(settings.avatar_alert_yield_percent),
             'deviation_origin': settings.avatar_alert_deviation_origin,
             'stock_thresholds': {str(k): v.model_dump(mode='json') | {'quantity': decimal_text(v.quantity)} for k, v in settings.avatar_alert_stock_thresholds.items()}}
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:20]
    return value | {'fingerprint': digest, 'timezone': 'Europe/Istanbul'}


def emit(rule, source_type, source_id, location_id, evaluated_at, current_policy, **fields):
    identity = f'{rule}:{source_type}:{source_id}:{location_id}:{current_policy["fingerprint"]}'
    severity = 'critical' if rule in ('EXPIRY_PAST', 'LOT_BLOCKED_STOCK') else 'warning'
    identifier = str(uuid5(NAMESPACE, identity))
    stage = {'lot': '0', 'product': '1', 'operation': '2'}[source_type]
    return {'id': identifier, 'rule_code': rule, 'severity': severity, 'source_type': source_type,
            'source_id': source_id, 'location_id': location_id or None,
            'evaluated_at': evaluated_at.isoformat(), 'evaluation_kind': 'current_read_only_analysis',
            'policy_version': current_policy['version'], 'policy_fingerprint': current_policy['fingerprint'],
            **fields, '_sort': ('0' if severity == 'critical' else '1', stage, source_id, location_id, rule, identifier)}


def stock_alerts(db, settings, now, current_policy, critical, lot_id=None):
    today = now.date()
    query = select(m.StockBalance, m.Lot, m.Product, m.Location).join(m.Lot, m.Lot.id == m.StockBalance.lot_id) \
        .join(m.Product, m.Product.id == m.Lot.product_id).join(m.Location, m.Location.id == m.StockBalance.location_id) \
        .where(m.StockBalance.quantity > 0)
    query = query.where(or_(m.Lot.blocked.is_(True), m.Lot.expires_at < today)) if critical else query.where(
        m.Lot.expires_at.between(today, today + timedelta(days=settings.avatar_alert_expiry_days)))
    if lot_id:
        query = query.where(m.Lot.id == str(lot_id))
    after = None
    while True:
        page = query
        if after:
            page = page.where(tuple_(m.StockBalance.lot_id, m.StockBalance.location_id) > after)
        rows = db.execute(page.order_by(m.StockBalance.lot_id, m.StockBalance.location_id).limit(BATCH_SIZE)).all()
        if not rows:
            return
        blocked_ids = {lot.id for _, lot, _, _ in rows if lot.blocked}
        recalls = defaultdict(list)
        if blocked_ids:
            for membership, recall in db.execute(select(m.RecallLot, m.Recall).join(m.Recall, m.Recall.id == m.RecallLot.recall_id)
                                                  .where(m.RecallLot.lot_id.in_(blocked_ids)).order_by(m.Recall.id)):
                recalls[membership.lot_id].append({'recall_id': recall.id, 'source_lot_id': recall.source_lot_id})
        for balance, lot, product, location in rows:
            days = (lot.expires_at - today).days if lot.expires_at else None
            available = location.kind == 'warehouse' and not lot.blocked and (days is None or days >= 0)
            evidence = {'product_id': product.id, 'product_name': product.name, 'lot_code': lot.external_code,
                        'location_id': location.id, 'location_name': location.name, 'location_kind': location.kind,
                        'physical_quantity': decimal_text(balance.quantity), 'quantity_unit': product.base_unit,
                        'available_quantity': decimal_text(balance.quantity if available else ZERO),
                        'expires_at': lot.expires_at.isoformat() if lot.expires_at else None, 'days_remaining': days}
            links = [{'label': 'Lot kaydını incele', 'href': '/izlenebilirlik?lot=' + lot.id}]
            rules = (['EXPIRY_PAST'] if days is not None and days < 0 else []) + (['LOT_BLOCKED_STOCK'] if lot.blocked else []) if critical else ['EXPIRY_SOON']
            for rule in sorted(rules):
                if rule == 'LOT_BLOCKED_STOCK':
                    title, message = 'Bloke stok', 'Pozitif fiziksel bakiye blokeli; kullanılabilir miktar sıfırdır.'
                    extra = {'related_recalls': recalls[lot.id]}
                    related = links + [{'label': 'İlgili geri çağırma', 'href': '/geri-cagirma/' + row['recall_id']} for row in recalls[lot.id]]
                    observed, threshold, unit = decimal_text(balance.quantity), '0', product.base_unit
                    action = 'Mevcut blokaj ve kayıtlı recall belgelerini inceleyin; otomatik serbest bırakma yapılmaz.'
                else:
                    title = 'Son tüketim tarihi geçmiş' if rule == 'EXPIRY_PAST' else 'Son tüketim tarihi yaklaşıyor'
                    message = f'{lot.external_code}: SKT {lot.expires_at.isoformat()}, Türkiye gününe göre {days} gün.'
                    extra, related = {}, links
                    observed, threshold, unit = str(days), '0' if rule == 'EXPIRY_PAST' else str(settings.avatar_alert_expiry_days), 'day'
                    action = 'Lot ve konum kaydını inceleyin; uygun kalite/stok işlemini yetkili kişi ayrıca değerlendirmeli.'
                yield emit(rule, 'lot', lot.id, location.id, now, current_policy, title=title, message=message,
                           source_label=product.name + ' · ' + lot.external_code, observed_value=observed,
                           threshold_value=threshold, unit=unit, threshold_unit=unit, threshold_origin='configured_review_window',
                           recommended_action=action, related_links=related, evidence=evidence | extra)
        after = (rows[-1][0].lot_id, rows[-1][0].location_id)
        if len(rows) < BATCH_SIZE:
            return


def low_stock_alerts(db, settings, now, current_policy, diagnostics):
    thresholds = {str(key): value for key, value in settings.avatar_alert_stock_thresholds.items()}
    if not thresholds:
        return
    usable = and_(m.Location.kind == 'warehouse', m.Lot.blocked.is_(False),
                  or_(m.Lot.expires_at.is_(None), m.Lot.expires_at >= now.date()))
    amount = func.coalesce(func.sum(case((usable, m.StockBalance.quantity), else_=0)), 0)
    rows = db.execute(select(m.Product, amount).outerjoin(m.Lot, m.Lot.product_id == m.Product.id)
                      .outerjoin(m.StockBalance, m.StockBalance.lot_id == m.Lot.id)
                      .outerjoin(m.Location, m.Location.id == m.StockBalance.location_id)
                      .where(m.Product.id.in_(thresholds)).group_by(m.Product.id).order_by(m.Product.id)).all()
    diagnostics['unknown_threshold_products'] += len(thresholds) - len(rows)
    for product, available in rows:
        threshold = thresholds[product.id]
        if product.base_unit != threshold.unit:
            diagnostics['threshold_unit_mismatch'] += 1
            continue
        if available < threshold.quantity:
            yield emit('LOW_AVAILABLE_STOCK', 'product', product.id, '', now, current_policy,
                       title='Tanımlı eşik altında kullanılabilir stok', source_label=product.name,
                       message='Ürün bazında işletme depolarının kullanılabilir stoğu tanımlı eşiğin altında. Karantina, dış üretici, blokeli ve süresi geçmiş stok hariçtir.',
                       observed_value=decimal_text(available), threshold_value=decimal_text(threshold.quantity),
                       unit=product.base_unit, threshold_unit=product.base_unit, threshold_origin=threshold.origin,
                       recommended_action='Stok ve tanımlı eşiği inceleyin; bu uyarı alış veya stok hareketi oluşturmaz.',
                       related_links=[{'label': 'Ürün stoklarını incele', 'href': '/stoklar?product=' + product.id}],
                       evidence={'product_id': product.id, 'product_name': product.name, 'analysis_scope': 'product_warehouse_available_stock',
                                 'excluded_locations': ['quarantine', 'external_producer']})


def number(value):
    if not isinstance(value, str) or len(value) > 80:
        raise ValueError('Invalid recorded decimal')
    result = Decimal(value)
    if not result.is_finite() or result < 0 or result >= Decimal('1e12'):
        raise ValueError('Invalid recorded decimal')
    return result


def comparison(record, op, inputs, outputs, artifact):
    """Pure batch equivalent of the existing comparison; no inference or DB get."""
    meta = artifact.document['metadata']
    snapshot = record.prediction
    if not isinstance(snapshot, dict) or not isinstance(record.context, dict) or not isinstance(record.features, dict):
        raise ValueError('Invalid recorded snapshot')
    for key in ('model_version', 'feature_schema_version', 'data_origin', 'dataset_hash'):
        if snapshot.get(key) != meta[key]:
            raise ValueError('Artifact provenance mismatch')
    if record.model_version != meta['model_version'] or record.feature_schema_version != meta['feature_schema_version']:
        raise ValueError('Record provenance mismatch')
    if not inputs or not outputs or any(product.base_unit != 'kg' for _, _, product in inputs):
        raise ValueError('Unsupported inputs')
    mass = sum((row.quantity for row, _, _ in inputs), ZERO)
    if mass <= 0:
        raise ValueError('No denominator')
    predicted_yield = number(snapshot['predicted_yield_ratio'])
    if not 0 < predicted_yield <= 1:
        raise ValueError('Invalid yield')
    if record.kind == 'production':
        target = record.context['output_product_id']
        package_weight = number(record.features['package_weight_kg'])
        if (snapshot.get('quantity_unit') != 'package' or snapshot.get('currency') != 'EUR' or package_weight <= 0
                or any(lot.product_id != target or product.base_unit != 'package' or product.package_weight_kg != package_weight
                       for _, lot, product in outputs)):
            raise ValueError('Unsupported output unit/target')
        quantity = sum((row.quantity for row, _, _ in outputs), ZERO)
        if quantity <= 0:
            raise ValueError('No denominator')
        return [('PRODUCTION_EKP_DEVIATION', op.total_cost / quantity, number(snapshot['predicted_ekp_eur_per_unit']), 'EUR/package'),
                ('YIELD_DEVIATION', quantity * package_weight / mass, predicted_yield, 'kg/kg')]
    mapping = record.context['part_products']
    if (record.context.get('recipe_version_id') != op.recipe_version_id or not isinstance(mapping, dict)
            or set(mapping) != {'leg', 'shoulder', 'back', 'rib', 'mince'} or len(set(mapping.values())) != 5
            or any(product.base_unit != 'kg' or lot.product_id not in mapping.values() for _, lot, product in outputs)):
        raise ValueError('Unsupported cutting shape')
    return [('YIELD_DEVIATION', sum((row.quantity for row, _, _ in outputs), ZERO) / mass, predicted_yield, 'kg/kg')]


def forecast_alerts(db, settings, now, current_policy, diagnostics, operation_id=None):
    first = select(m.StockMovement.operation_id, func.min(m.StockMovement.created_at).label('started_at')) \
        .where(m.StockMovement.operation_id.is_not(None)).group_by(m.StockMovement.operation_id).subquery()
    newer = aliased(m.PredictionRecord)
    expected = or_(and_(m.PredictionRecord.kind == 'production', m.Operation.kind == 'external_production'),
                   and_(m.PredictionRecord.kind == 'cutting', m.Operation.kind == 'cutting'))
    query = select(m.PredictionRecord, m.Operation).join(m.Operation, m.Operation.id == m.PredictionRecord.operation_id) \
        .join(first, first.c.operation_id == m.Operation.id).where(m.Operation.status == 'posted', expected,
            m.PredictionRecord.created_at >= m.Operation.created_at,
            m.PredictionRecord.created_at < first.c.started_at, m.PredictionRecord.created_at < m.Operation.posted_at)
    # Latest eligible pre-start record, not the one with the largest deviation.
    query = query.where(~exists(select(newer.id).where(newer.operation_id == m.Operation.id,
        newer.kind == m.PredictionRecord.kind, newer.created_at >= m.Operation.created_at,
        newer.created_at < first.c.started_at, newer.created_at < m.Operation.posted_at,
        or_(newer.created_at > m.PredictionRecord.created_at,
            and_(newer.created_at == m.PredictionRecord.created_at, newer.id > m.PredictionRecord.id)))))
    if operation_id:
        query = query.where(m.Operation.id == str(operation_id))
    artifacts = {}
    after = None
    while True:
        page = query.where(m.Operation.id > after) if after else query
        rows = db.execute(page.order_by(m.Operation.id).limit(BATCH_SIZE)).all()
        if not rows:
            return
        identifiers = [op.id for _, op in rows]
        def ledger_rows(model):
            return db.execute(select(model, m.Lot, m.Product).join(m.Lot, m.Lot.id == model.lot_id)
                              .join(m.Product, m.Product.id == m.Lot.product_id).where(model.operation_id.in_(identifiers))).all()
        inputs, outputs = defaultdict(list), defaultdict(list)
        for row in ledger_rows(m.OperationInput):
            inputs[row[0].operation_id].append(row)
        for row in ledger_rows(m.OperationOutput):
            outputs[row[0].operation_id].append(row)
        for record, op in rows:
            diagnostics['inspected_predictions'] += 1
            if record.kind not in artifacts:
                try:
                    artifacts[record.kind] = load_model(settings.avatar_ml_model_dir, record.kind)
                except ModelUnavailable:
                    artifacts[record.kind] = None
            artifact = artifacts[record.kind]
            if artifact is None:
                diagnostics['model_unavailable'] += 1
                continue
            try:
                with localcontext() as ctx:
                    ctx.prec = 48
                    values = comparison(record, op, inputs[op.id], outputs[op.id], artifact)
                    for rule, actual, predicted, unit in sorted(values):
                        if actual <= 0:
                            diagnostics['zero_actual_denominator'] += 1
                            continue
                        deviation = abs(actual - predicted) / abs(actual) * 100
                        threshold = settings.avatar_alert_cost_percent if rule == 'PRODUCTION_EKP_DEVIATION' else settings.avatar_alert_yield_percent
                        if deviation <= threshold:
                            continue
                        yield emit(rule, 'operation', op.id, '', now, current_policy,
                            title='Tahmin–gerçekleşme karşılaştırması', source_label=op.code,
                            message='Kayıtlı işlem öncesi tahmin ile kesin sonuç inceleme eşiğini aşıyor. Bu, kanıtlanmış anomali sınıflandırıcısı değildir.',
                            observed_value=decimal_text(actual), predicted_value=decimal_text(predicted),
                            difference_value=decimal_text(actual - predicted), deviation_percent=decimal_text(deviation),
                            threshold_value=decimal_text(threshold), threshold_unit='%', unit=unit,
                            threshold_origin=settings.avatar_alert_deviation_origin,
                            recommended_action='Kesin işlem ve kayıtlı tahmini birlikte inceleyin; muhasebe veya lot kaydını tahmine göre değiştirmeyin.',
                            related_links=[{'label': 'Kesin işlemi incele', 'href': ('/uretim/' if record.kind == 'production' else '/parcalama/') + op.id},
                                           {'label': 'Kayıtlı tahmini incele', 'href': '/yapay-zeka?prediction=' + record.id}],
                            evidence={'prediction_id': record.id, 'operation_id': op.id, 'operation_kind': op.kind,
                                'prediction_recorded_at': record.created_at.replace(tzinfo=timezone.utc).isoformat(),
                                'posted_at': op.posted_at.replace(tzinfo=timezone.utc).isoformat(),
                                'model_version': record.model_version, 'data_origin': record.prediction['data_origin'],
                                'prediction_limitations': LIMITATIONS, 'percentage_denominator': 'abs(actual)',
                                'explained_difference_kg': decimal_text(op.loss_quantity), 'new_prediction_created': False})
            except (KeyError, TypeError, ValueError, InvalidOperation, AttributeError):
                diagnostics['invalid_or_incompatible_snapshot'] += 1
        after = rows[-1][1].id
        if len(rows) < BATCH_SIZE:
            return


def alert_stream(db, settings, now, current_policy, diagnostics, lot_id=None, operation_id=None):
    if not operation_id:
        yield from stock_alerts(db, settings, now, current_policy, True, lot_id)
        yield from stock_alerts(db, settings, now, current_policy, False, lot_id)
        if not lot_id:
            yield from low_stock_alerts(db, settings, now, current_policy, diagnostics)
    if not lot_id:
        yield from forecast_alerts(db, settings, now, current_policy, diagnostics, operation_id)


def decode_cursor(cursor, context):
    if not cursor:
        return None
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor + '=' * (-len(cursor) % 4)))
        key = value['after']
        if not isinstance(key, list) or len(key) != 6 or any(not isinstance(x, str) or len(x) > 100 for x in key):
            raise ValueError()
        if value['context'] != context:
            raise DomainError('ALERT_CURSOR_STALE', 'Tarih, eşik veya filtre değişti; uyarı listesini baştan yenileyin')
        return tuple(key)
    except DomainError:
        raise
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise DomainError('ALERT_CURSOR_INVALID', 'Uyarı sayfa işareti geçersiz; listeyi baştan yenileyin', 422) from None


def evaluate(db, *, severity=None, rule_code=None, lot_id=None, operation_id=None, limit=50, cursor=None, identifier=None):
    # Transaction-local read-only mode; connection rollback/return restores the
    # engine's normal READ COMMITTED writer behavior. Never flush this Session.
    db.autoflush = False
    connection = db.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
    connection.exec_driver_sql('SET TRANSACTION READ ONLY')
    settings = get_settings()
    now = clock().astimezone(ISTANBUL)
    current_policy = policy(settings)
    context = [now.date().isoformat(), current_policy['fingerprint'], severity, rule_code,
               str(lot_id) if lot_id else None, str(operation_id) if operation_id else None]
    after = decode_cursor(cursor, context)
    items, counts, rules, diagnostics = [], Counter(), Counter(), Counter()
    total = 0
    for row in alert_stream(db, settings, now, current_policy, diagnostics, lot_id, operation_id):
        if (severity and row['severity'] != severity) or (rule_code and row['rule_code'] != rule_code):
            continue
        key = row.pop('_sort')
        if identifier:
            if row['id'] == str(identifier):
                return row
            continue
        total += 1
        counts[row['severity']] += 1
        rules[row['rule_code']] += 1
        if limit and len(items) <= limit and (after is None or key > after):
            items.append((key, row))
    if identifier:
        raise DomainError('NOT_FOUND', 'Uyarı güncel değerlendirmede yok; kaynak durumunu veya eşikleri yenileyin', 404)
    next_cursor = None
    if len(items) > limit:
        encoded = {'after': items[limit - 1][0], 'context': context}
        next_cursor = base64.urlsafe_b64encode(json.dumps(encoded, separators=(',', ':')).encode()).decode().rstrip('=')
    return {'items': [row for _, row in items[:limit]], 'next_cursor': next_cursor,
            'summary': {'total': total, 'critical': counts['critical'], 'warning': counts['warning'], 'info': counts['info'],
                        'by_rule': dict(rules)},
            'evaluated_at': now.isoformat(), 'policy': current_policy,
            'diagnostics': dict(diagnostics), 'history_persisted': False,
            'scope': 'current_recorded_sources; product low stock uses warehouse availability; lot/operation filters match source type'}

"""In-house cutting over the existing operation/lot ledger and recall protocol."""
from decimal import Decimal, localcontext

from sqlalchemy import select

from app import models as m, services
from app.costing import allocate, consumption_cost, quantize
from app.errors import DomainError

POLICIES = {
    'version': 1,
    'waste_cost': 'absorbed_by_all_recorded_outputs',
    'other_loss_cost': 'absorbed_by_all_recorded_outputs',
    'byproduct_cost': 'included_with_positive_selected_allocation_weight',
    'lot_link_quantity': 'full_consumed_input_allocated_by_physical_output_kg_including_loss',
    'rounding': 'six_decimal_cumulative_half_up_sorted_product_id_lot_code',
}


def recipe_detail(db, row):
    return {**services.entity(row), 'lines': [services.entity(x) for x in db.scalars(
        select(m.RecipeLine).where(m.RecipeLine.recipe_version_id == row.id).order_by(m.RecipeLine.product_id))]}


def create_recipe(db, request):
    source = services.get(db, m.Product, request.input_product_id)
    if source.base_unit != 'kg' or source.type != 'raw':
        raise DomainError('INVALID_RECIPE_INPUT', 'Kaynak ürün kg birimli hammadde olmalı', 422)
    if source.species and source.species.casefold() != request.species.casefold():
        raise DomainError('RECIPE_SPECIES_MISMATCH', 'Reçete türü kaynak ürün türüyle uyuşmuyor', 422)
    row = m.RecipeVersion(code=request.code, version=request.version, species=request.species,
                          input_product_id=source.id, allocation_method=request.allocation_method, available=request.available)
    db.add(row); db.flush()
    for line in sorted(request.lines, key=lambda x: str(x.product_id)):
        product = services.get(db, m.Product, line.product_id)
        if product.base_unit != 'kg' or product.type not in ('finished', 'byproduct'):
            raise DomainError('INVALID_RECIPE_OUTPUT', 'Parçalar kg birimli mamul veya yan ürün olmalı', 422)
        db.add(m.RecipeLine(recipe_version_id=row.id, product_id=product.id, reference_eur_per_kg=line.reference_eur_per_kg))
    db.flush()
    return recipe_detail(db, row)


def set_availability(db, recipe_id, request):
    row = services.get(db, m.RecipeVersion, recipe_id, lock=True)
    row.available = request.available
    db.flush()
    return recipe_detail(db, row)


def snapshot(db, recipe):
    detail = recipe_detail(db, recipe)
    return {'schema_version': 1, 'recipe_version_id': recipe.id, 'code': recipe.code, 'version': recipe.version,
            'species': recipe.species, 'input_product_id': recipe.input_product_id,
            'allocation_method': recipe.allocation_method, 'policies': dict(POLICIES),
            'lines': [{**line, 'product': services.entity(services.get(db, m.Product, line['product_id']))} for line in detail['lines']]}


def create_cutting(db, request):
    recipe = services.get(db, m.RecipeVersion, request.recipe_version_id, lock=True)
    if not recipe.available:
        raise DomainError('RECIPE_UNAVAILABLE', 'Reçete sürümü kullanıma kapalı')
    op = m.Operation(code=request.code, kind='cutting', recipe_version_id=recipe.id,
                     allocation_method=recipe.allocation_method, allocation_snapshot=snapshot(db, recipe))
    db.add(op); db.flush()
    return cutting_detail(db, op)


def cutting_detail(db, op):
    if op.kind != 'cutting':
        raise DomainError('NOT_FOUND', 'Parçalama kaydı bulunamadı', 404)
    differences = db.scalars(select(m.OperationDifference).where(m.OperationDifference.operation_id == op.id).order_by(m.OperationDifference.id))
    return {**services.operation_detail(db, op), 'differences': [services.entity(x) for x in differences]}


def post_cutting(db, operation_id, request):
    # Same order as production: operation -> recipe -> sorted input lots -> balances.
    # Recall never locks operation/recipe rows and revalidates graph closure.
    op = services.draft_operation(db, operation_id, kind='cutting')
    recipe = services.get(db, m.RecipeVersion, op.recipe_version_id, lock=True)
    if not recipe.available:
        raise DomainError('RECIPE_UNAVAILABLE', 'Reçete sürümü kullanıma kapalı')
    destination = services.get(db, m.Location, request.output_location_id)
    if destination.kind != 'warehouse':
        raise DomainError('INVALID_LOCATION', 'Parçalar işletme deposuna kabul edilmelidir', 422)
    lots = services.lock_lots(db, [x.lot_id for x in request.consumed_inputs])
    for line in request.consumed_inputs:
        lot = lots[str(line.lot_id)]
        services.usable(lot)
        if lot.product_id != op.allocation_snapshot['input_product_id']:
            raise DomainError('RECIPE_INPUT_MISMATCH', 'Kaynak lot reçetenin giriş ürünüyle uyuşmuyor', 422)
        if services.get(db, m.Location, line.location_id).kind != 'warehouse':
            raise DomainError('INVALID_LOCATION', 'Parçalama girdisi işletme deposunda olmalıdır', 422)
    ordered = sorted(request.outputs, key=lambda x: (str(x.product_id), x.lot_code))
    recipe_lines = {x['product_id']: x for x in op.allocation_snapshot['lines']}
    weights, references = [], []
    for item in ordered:
        entry = recipe_lines.get(str(item.product_id))
        if entry is None:
            raise DomainError('RECIPE_OUTPUT_MISMATCH', 'Çıktı ürünü reçete sürümünde tanımlı değil', 422)
        if entry['product']['type'] == 'byproduct' and not item.explanation:
            raise DomainError('BYPRODUCT_EXPLANATION', 'Yan ürün için miktar ve açıklama gerekli', 422)
        reference = Decimal(entry['reference_eur_per_kg']) if entry['reference_eur_per_kg'] is not None else None
        with localcontext() as ctx:
            ctx.prec = 48
            weight = item.quantity if op.allocation_method == 'quantity' else item.quantity * reference
        if weight <= 0 or quantize(weight) != weight:
            raise DomainError('ALLOCATION_PRECISION', 'Pozitif dağıtım ağırlığı 6 ondalık hassasiyetine sığmalıdır', 422)
        weights.append(weight); references.append(reference)
    input_kg = quantize(sum((x.quantity for x in request.consumed_inputs), Decimal(0)))
    output_kg = quantize(sum((x.quantity for x in ordered), Decimal(0)))
    loss_kg = quantize(sum((x.quantity for x in request.differences), Decimal(0)))
    if input_kg != output_kg + loss_kg:
        raise DomainError('MASS_BALANCE', 'Girdi kg = ürün/yan ürün kg + sınıflandırılmış açıklamalı fark kg olmalıdır', 422)
    inputs = []
    for line in sorted(request.consumed_inputs, key=lambda x: (str(x.lot_id), str(x.location_id))):
        lot = lots[str(line.lot_id)]
        cost = consumption_cost(lot.total_cost, lot.original_quantity, lot.consumed_quantity, lot.consumed_cost, line.quantity)
        services.move(db, lot.id, str(line.location_id), -line.quantity, 'cutting_input', op.id)
        lot.consumed_quantity += line.quantity; lot.consumed_cost += cost
        row = m.OperationInput(operation_id=op.id, lot_id=lot.id, location_id=str(line.location_id), quantity=line.quantity, consumed_cost=cost)
        db.add(row); db.flush(); inputs.append(row)
    op.total_material_cost = quantize(sum((x.consumed_cost for x in inputs), Decimal(0)))
    op.total_service_cost = Decimal(0)
    op.total_cost = op.total_material_cost
    outputs = []
    for item, weight, reference, cost in zip(ordered, weights, references, allocate(op.total_cost, weights)):
        lot = m.Lot(product_id=str(item.product_id), external_code=item.lot_code, received_at=m.now(),
                    expires_at=item.expires_at, original_quantity=item.quantity, total_cost=cost)
        db.add(lot); db.flush()
        row = m.OperationOutput(operation_id=op.id, lot_id=lot.id, quantity=item.quantity, allocation_weight=weight,
                                reference_eur_per_kg=reference, explanation=item.explanation, allocated_cost=cost)
        db.add(row); db.flush(); outputs.append(row)
        services.move(db, lot.id, destination.id, item.quantity, 'cutting_output', op.id)
    # Quantity attribution remains physical-kg based, independent of monetary key.
    for src in inputs:
        for dst, attributed in zip(outputs, allocate(src.quantity, [x.quantity for x in ordered])):
            if attributed <= 0:
                raise DomainError('LINK_PRECISION', 'Lot bağlantısı miktarı saklama hassasiyetinin altında', 422)
            db.add(m.LotLink(input_id=src.id, output_id=dst.id, attributed_input_quantity=attributed))
    for difference in request.differences:
        db.add(m.OperationDifference(operation_id=op.id, **difference.model_dump()))
    op.loss_quantity = loss_kg
    op.loss_reason = 'Sınıflandırılmış farklar: operation_differences kayıtları' if loss_kg else None
    op.status, op.posted_at = 'posted', m.now()
    db.flush()
    return cutting_detail(db, op)

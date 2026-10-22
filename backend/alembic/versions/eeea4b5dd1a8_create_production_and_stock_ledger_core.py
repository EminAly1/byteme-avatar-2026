"""Create production and stock ledger core

Revision ID: eeea4b5dd1a8
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
revision = 'eeea4b5dd1a8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('idempotency_requests',
    sa.Column('scope', sa.String(length=128), nullable=False),
    sa.Column('key', sa.String(length=36), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('http_status', sa.Integer(), nullable=False),
    sa.Column('response', sa.JSON(), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.PrimaryKeyConstraint('scope', 'key'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('parties',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('roles', sa.JSON(), nullable=False),
    sa.Column('contact', sa.String(length=300), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('products',
    sa.Column('sku', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('type', sa.String(length=24), nullable=False),
    sa.Column('base_unit', sa.String(length=16), nullable=False),
    sa.Column('package_weight_kg', sa.Numeric(precision=18, scale=6), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("base_unit IN ('kg','package','unit')", name='ck_product_unit'),
    sa.CheckConstraint("type IN ('raw','finished','byproduct')", name='ck_product_type'),
    sa.CheckConstraint('package_weight_kg IS NULL OR package_weight_kg > 0', name='ck_product_weight'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sku'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('locations',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('party_id', sa.String(length=36), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("kind IN ('warehouse','external_producer','quarantine')", name='ck_location_kind'),
    sa.ForeignKeyConstraint(['party_id'], ['parties.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('lots',
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('supplier_id', sa.String(length=36), nullable=True),
    sa.Column('external_code', sa.String(length=100), nullable=False),
    sa.Column('received_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('expires_at', sa.Date(), nullable=True),
    sa.Column('blocked', sa.Boolean(), nullable=False),
    sa.Column('original_quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('total_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('consumed_quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('consumed_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('consumed_cost >= 0 AND consumed_cost <= total_cost', name='ck_lot_consumed_cost'),
    sa.CheckConstraint('consumed_quantity >= 0 AND consumed_quantity <= original_quantity', name='ck_lot_consumed'),
    sa.CheckConstraint('original_quantity > 0', name='ck_lot_original'),
    sa.CheckConstraint('total_cost >= 0', name='ck_lot_cost'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['parties.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_lots_external_code', 'lots', ['external_code'], unique=False)
    op.create_table('operations',
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('producer_id', sa.String(length=36), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('posted_at', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('total_material_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('total_service_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('total_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('loss_quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('loss_reason', sa.String(length=500), nullable=True),
    sa.Column('allocation_method', sa.String(length=16), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("kind IN ('external_production','cutting','rework')", name='ck_operation_kind'),
    sa.CheckConstraint("status IN ('draft','posted')", name='ck_operation_status'),
    sa.CheckConstraint('total_material_cost >= 0 AND total_service_cost >= 0 AND total_cost >= 0 AND loss_quantity >= 0', name='ck_operation_values'),
    sa.ForeignKeyConstraint(['producer_id'], ['parties.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('operation_inputs',
    sa.Column('operation_id', sa.String(length=36), nullable=False),
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('location_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('consumed_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('quantity > 0 AND consumed_cost >= 0', name='ck_input_values'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('operation_id', 'lot_id', 'location_id', name='uq_operation_input'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('operation_outputs',
    sa.Column('operation_id', sa.String(length=36), nullable=False),
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('allocation_weight', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('allocated_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('quantity > 0 AND allocation_weight > 0 AND allocated_cost >= 0', name='ck_output_values'),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('lot_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('receipts',
    sa.Column('supplier_id', sa.String(length=36), nullable=False),
    sa.Column('location_id', sa.String(length=36), nullable=False),
    sa.Column('received_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('reference', sa.String(length=100), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['parties.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('service_costs',
    sa.Column('operation_id', sa.String(length=36), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('invoice_reference', sa.String(length=100), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("amount >= 0 AND currency = 'EUR'", name='ck_service_amount'),
    sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('stock_balances',
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('location_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.CheckConstraint('quantity >= 0', name='ck_balance_nonnegative'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.PrimaryKeyConstraint('lot_id', 'location_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('lot_links',
    sa.Column('input_id', sa.String(length=36), nullable=False),
    sa.Column('output_id', sa.String(length=36), nullable=False),
    sa.Column('attributed_input_quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('attributed_input_quantity > 0', name='ck_link_quantity'),
    sa.ForeignKeyConstraint(['input_id'], ['operation_inputs.id'], ),
    sa.ForeignKeyConstraint(['output_id'], ['operation_outputs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('input_id', 'output_id', name='uq_lot_link'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('receipt_lines',
    sa.Column('receipt_id', sa.String(length=36), nullable=False),
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('total_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('quantity > 0 AND total_cost >= 0', name='ck_receipt_values'),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('lot_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('stock_movements',
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('location_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('type', sa.String(length=32), nullable=False),
    sa.Column('operation_id', sa.String(length=36), nullable=True),
    sa.Column('receipt_line_id', sa.String(length=36), nullable=True),
    sa.Column('transfer_group_id', sa.String(length=36), nullable=True),
    sa.Column('reversal_of', sa.String(length=36), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('quantity <> 0', name='ck_movement_nonzero'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], ),
    sa.ForeignKeyConstraint(['receipt_line_id'], ['receipt_lines.id'], ),
    sa.ForeignKeyConstraint(['reversal_of'], ['stock_movements.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_movement_lot_location', 'stock_movements', ['lot_id', 'location_id', 'id'], unique=False)
    op.create_index('ix_movement_operation', 'stock_movements', ['operation_id'], unique=False)


def downgrade():
    # Dropping a table also drops indexes. MySQL must retain FK indexes until
    # the referencing table itself is removed.
    op.drop_table('stock_movements')
    op.drop_table('receipt_lines')
    op.drop_table('lot_links')
    op.drop_table('stock_balances')
    op.drop_table('service_costs')
    op.drop_table('receipts')
    op.drop_table('operation_outputs')
    op.drop_table('operation_inputs')
    op.drop_table('operations')
    op.drop_table('lots')
    op.drop_table('locations')
    op.drop_table('products')
    op.drop_table('parties')
    op.drop_table('idempotency_requests')

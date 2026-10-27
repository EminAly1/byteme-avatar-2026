"""Add atomic lot transfers and quarantine sale corrections

Revision ID: e1307a26b001
Revises: dc9109a1f001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
revision = 'e1307a26b001'
down_revision = 'dc9109a1f001'
branch_labels = None
depends_on = None


def upgrade():
    # MySQL DDL auto-commits. Reject ambiguous legacy reversals before any DDL;
    # never delete or deduplicate historical ledger records during migration.
    duplicate = op.get_bind().execute(sa.text(
        'SELECT reversal_of FROM stock_movements WHERE reversal_of IS NOT NULL '
        'GROUP BY reversal_of HAVING COUNT(*) > 1 LIMIT 1')).first()
    if duplicate:
        raise RuntimeError('Duplicate legacy reversal_of values require explicit audit review; migration did not change data.')
    op.create_table('customer_returns',
    sa.Column('sale_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('acceptance_location_id', sa.String(length=36), nullable=False),
    sa.Column('returned_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('reference', sa.String(length=100), nullable=True),
    sa.Column('credit_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('restored_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('credit_amount >= 0 AND restored_cost >= 0', name='ck_return_amounts'),
    sa.ForeignKeyConstraint(['acceptance_location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['customer_id'], ['parties.id'], ),
    sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_return_sale', 'customer_returns', ['sale_id', 'id'], unique=False)
    op.create_table('sale_cancellations',
    sa.Column('sale_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('acceptance_location_id', sa.String(length=36), nullable=False),
    sa.Column('cancelled_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('credit_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('restored_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('credit_amount >= 0 AND restored_cost >= 0', name='ck_cancel_amounts'),
    sa.ForeignKeyConstraint(['acceptance_location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['customer_id'], ['parties.id'], ),
    sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sale_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('stock_transfers',
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('from_location_id', sa.String(length=36), nullable=False),
    sa.Column('to_location_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=16), nullable=False),
    sa.Column('transferred_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('reference', sa.String(length=100), nullable=True),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('out_movement_id', sa.String(length=36), nullable=False),
    sa.Column('in_movement_id', sa.String(length=36), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("unit IN ('kg','package','unit')", name='ck_transfer_unit'),
    sa.CheckConstraint('quantity > 0 AND from_location_id <> to_location_id', name='ck_transfer_values'),
    sa.ForeignKeyConstraint(['from_location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['in_movement_id'], ['stock_movements.id'], ),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['out_movement_id'], ['stock_movements.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['to_location_id'], ['locations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('in_movement_id'),
    sa.UniqueConstraint('out_movement_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_transfer_lot', 'stock_transfers', ['lot_id', 'id'], unique=False)
    op.create_table('sale_cancellation_lines',
    sa.Column('cancellation_id', sa.String(length=36), nullable=False),
    sa.Column('sale_line_id', sa.String(length=36), nullable=False),
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('stock_movement_id', sa.String(length=36), nullable=False),
    sa.Column('quarantine_out_movement_id', sa.String(length=36), nullable=False),
    sa.Column('quarantine_in_movement_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=16), nullable=False),
    sa.Column('credit_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('restored_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("unit IN ('kg','package','unit')", name='ck_cancel_line_unit'),
    sa.CheckConstraint('quantity > 0 AND credit_amount >= 0 AND restored_cost >= 0', name='ck_cancel_line_values'),
    sa.ForeignKeyConstraint(['cancellation_id'], ['sale_cancellations.id'], ),
    sa.ForeignKeyConstraint(['quarantine_out_movement_id'], ['stock_movements.id'], ),
    sa.ForeignKeyConstraint(['quarantine_in_movement_id'], ['stock_movements.id'], ),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['sale_line_id'], ['sale_lines.id'], ),
    sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sale_line_id'),
    sa.UniqueConstraint('quarantine_out_movement_id'),
    sa.UniqueConstraint('quarantine_in_movement_id'),
    sa.UniqueConstraint('stock_movement_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('customer_return_lines',
    sa.Column('return_id', sa.String(length=36), nullable=False),
    sa.Column('sale_line_id', sa.String(length=36), nullable=False),
    sa.Column('shipment_line_id', sa.String(length=36), nullable=False),
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('stock_movement_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=16), nullable=False),
    sa.Column('credit_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('restored_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("unit IN ('kg','package','unit')", name='ck_return_line_unit'),
    sa.CheckConstraint('quantity > 0 AND credit_amount >= 0 AND restored_cost >= 0', name='ck_return_line_values'),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['return_id'], ['customer_returns.id'], ),
    sa.ForeignKeyConstraint(['sale_line_id'], ['sale_lines.id'], ),
    sa.ForeignKeyConstraint(['shipment_line_id'], ['shipment_lines.id'], ),
    sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('return_id', 'sale_line_id', name='uq_return_sale_line'),
    sa.UniqueConstraint('stock_movement_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_return_line_sale', 'customer_return_lines', ['sale_line_id', 'id'], unique=False)
    op.create_unique_constraint('uq_movement_reversal', 'stock_movements', ['reversal_of'])


def downgrade():
    # Removing posted correction headers would orphan the append-only ledger.
    # Refuse before any DDL; only empty/new test installations may downgrade.
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for table in ('stock_transfers', 'customer_returns', 'customer_return_lines',
                  'sale_cancellations', 'sale_cancellation_lines'):
        if table in tables and op.get_bind().scalar(sa.text('SELECT COUNT(*) FROM ' + table)):
            raise RuntimeError('Posted transfer/return/cancellation audit records exist; destructive downgrade refused.')
    # InnoDB may replace the old implicit FK index with the new unique index.
    # Restore an equivalent nonunique supporting index before dropping UNIQUE;
    # never disable foreign-key checks or remove the self-FK to force a downgrade.
    indexes = sa.inspect(op.get_bind()).get_indexes('stock_movements')
    if any(index['name'] == 'uq_movement_reversal' for index in indexes):
        if not any(not index['unique'] and index['column_names'] == ['reversal_of'] for index in indexes):
            op.create_index('reversal_of', 'stock_movements', ['reversal_of'], unique=False)
        op.drop_constraint('uq_movement_reversal', 'stock_movements', type_='unique')
    # Drop each child table with its indexes/FKs, not its FK-supporting index
    # first. Empty partial DDL from an interrupted downgrade can be resumed.
    for table in ('customer_return_lines', 'sale_cancellation_lines', 'stock_transfers',
                  'sale_cancellations', 'customer_returns'):
        if table in tables:
            op.drop_table(table)

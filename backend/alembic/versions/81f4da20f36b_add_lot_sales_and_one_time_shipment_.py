"""Add lot sales and one-time shipment links

Revision ID: 81f4da20f36b
Revises: eeea4b5dd1a8
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
revision = '81f4da20f36b'
down_revision = 'eeea4b5dd1a8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('sales',
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('sold_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("currency = 'EUR' AND total_amount >= 0", name='ck_sale_amount'),
    sa.ForeignKeyConstraint(['customer_id'], ['parties.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_sale_customer', 'sales', ['customer_id', 'id'], unique=False)
    op.create_table('shipments',
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('sale_id', sa.String(length=36), nullable=True),
    sa.Column('recipient_name', sa.String(length=200), nullable=False),
    sa.Column('recipient_contact', sa.String(length=300), nullable=True),
    sa.Column('shipped_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['parties.id'], ),
    sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_shipment_customer', 'shipments', ['customer_id', 'id'], unique=False)
    op.create_table('sale_lines',
    sa.Column('sale_id', sa.String(length=36), nullable=False),
    sa.Column('line_no', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('location_id', sa.String(length=36), nullable=False),
    sa.Column('stock_movement_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=16), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('consumed_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("unit IN ('kg','package','unit')", name='ck_sale_line_unit'),
    sa.CheckConstraint('line_no > 0 AND quantity > 0 AND unit_price >= 0 AND total_amount >= 0 AND consumed_cost >= 0', name='ck_sale_line_values'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], ),
    sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sale_id', 'line_no', name='uq_sale_line_number'),
    sa.UniqueConstraint('sale_id', 'lot_id', 'location_id', name='uq_sale_lot_location'),
    sa.UniqueConstraint('stock_movement_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_sale_line_lot', 'sale_lines', ['lot_id', 'sale_id'], unique=False)
    op.create_table('shipment_lines',
    sa.Column('shipment_id', sa.String(length=36), nullable=False),
    sa.Column('line_no', sa.Integer(), nullable=False),
    sa.Column('sale_line_id', sa.String(length=36), nullable=True),
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.Column('location_id', sa.String(length=36), nullable=False),
    sa.Column('stock_movement_id', sa.String(length=36), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('unit', sa.String(length=16), nullable=False),
    sa.Column('consumed_cost', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("unit IN ('kg','package','unit')", name='ck_shipment_line_unit'),
    sa.CheckConstraint('line_no > 0 AND quantity > 0 AND consumed_cost >= 0', name='ck_shipment_line_values'),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['sale_line_id'], ['sale_lines.id'], ),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], ),
    sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sale_line_id'),
    sa.UniqueConstraint('shipment_id', 'line_no', name='uq_shipment_line_number'),
    sa.UniqueConstraint('shipment_id', 'lot_id', 'location_id', name='uq_shipment_lot_location'),
    sa.UniqueConstraint('stock_movement_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_shipment_line_lot', 'shipment_lines', ['lot_id', 'shipment_id'], unique=False)


def downgrade():
    # MySQL FK indexes are removed together with their owning tables.
    op.drop_table('shipment_lines')
    op.drop_table('sale_lines')
    op.drop_table('shipments')
    op.drop_table('sales')

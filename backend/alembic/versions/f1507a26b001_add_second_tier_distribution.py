"""Add append-only operator-reported second-tier distribution.

Revision ID: f1507a26b001
Revises: e1307a26b001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'f1507a26b001'
down_revision = 'e1307a26b001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('second_tier_distributions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
        sa.Column('source_shipment_line_id', sa.String(36), sa.ForeignKey('shipment_lines.id'), nullable=False),
        sa.Column('source_customer_id', sa.String(36), sa.ForeignKey('parties.id'), nullable=False),
        sa.Column('source_lot_id', sa.String(36), sa.ForeignKey('lots.id'), nullable=False),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('recipient_party_id', sa.String(36), sa.ForeignKey('parties.id'), nullable=False),
        sa.Column('recipient_name', sa.String(200), nullable=False),
        sa.Column('recipient_contact', sa.String(300), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 6), nullable=False),
        sa.Column('unit', sa.String(16), nullable=False),
        sa.Column('distributed_at', mysql.DATETIME(fsp=6), nullable=False),
        sa.Column('reference', sa.String(100), nullable=False),
        sa.Column('evidence_note', sa.String(500), nullable=False),
        sa.CheckConstraint('quantity > 0', name='ck_second_tier_quantity'),
        sa.CheckConstraint("unit IN ('kg','package','unit')", name='ck_second_tier_unit'),
        sa.CheckConstraint("unit = 'kg' OR quantity = FLOOR(quantity)", name='ck_second_tier_counted'),
        sa.CheckConstraint('source_customer_id <> recipient_party_id', name='ck_second_tier_recipient'),
        sa.UniqueConstraint('source_shipment_line_id', 'reference', name='uq_second_tier_reference'),
        mysql_engine='InnoDB', mysql_charset='utf8mb4')
    op.create_index('ix_second_tier_lot', 'second_tier_distributions', ['source_lot_id', 'id'])
    op.create_index('ix_second_tier_recipient', 'second_tier_distributions', ['recipient_party_id', 'id'])


def downgrade():
    # MySQL DDL auto-commits. Refuse BEFORE the first DDL if audit data exists.
    bind = op.get_bind()
    if 'second_tier_distributions' in sa.inspect(bind).get_table_names():
        if bind.scalar(sa.text('SELECT COUNT(*) FROM second_tier_distributions')):
            raise RuntimeError('Second-tier audit records exist; destructive downgrade refused.')
        op.drop_table('second_tier_distributions')

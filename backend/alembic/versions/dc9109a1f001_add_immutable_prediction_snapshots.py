"""Separate decision-support snapshots; existing ledger tables untouched.

Revision ID: dc9109a1f001
Revises: fa8791f3cf0e
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'dc9109a1f001'
down_revision = 'fa8791f3cf0e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('prediction_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('operation_id', sa.String(36), nullable=True),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('feature_schema_version', sa.String(40), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('context', sa.JSON(), nullable=False),
        sa.Column('prediction', sa.JSON(), nullable=False),
        sa.CheckConstraint("kind IN ('production','cutting')", name='ck_prediction_kind'),
        sa.ForeignKeyConstraint(['operation_id'], ['operations.id']),
        sa.PrimaryKeyConstraint('id'), mysql_engine='InnoDB', mysql_charset='utf8mb4')
    op.create_index('ix_prediction_operation', 'prediction_records', ['operation_id','created_at'])


def downgrade():
    # Forecast audit history is removed only on explicit downgrade; no ledger row changes.
    op.drop_table('prediction_records')

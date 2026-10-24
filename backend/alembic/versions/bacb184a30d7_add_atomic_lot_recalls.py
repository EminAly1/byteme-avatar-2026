"""add atomic lot recalls

Revision ID: bacb184a30d7
Revises: 81f4da20f36b
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
revision = 'bacb184a30d7'
down_revision = '81f4da20f36b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('recalls',
    sa.Column('source_lot_id', sa.String(length=36), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.ForeignKeyConstraint(['source_lot_id'], ['lots.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('recall_lots',
    sa.Column('recall_id', sa.String(length=36), nullable=False),
    sa.Column('lot_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['lot_id'], ['lots.id'], ),
    sa.ForeignKeyConstraint(['recall_id'], ['recalls.id'], ),
    sa.PrimaryKeyConstraint('recall_id', 'lot_id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )


def downgrade():
    op.drop_table('recall_lots')
    op.drop_table('recalls')

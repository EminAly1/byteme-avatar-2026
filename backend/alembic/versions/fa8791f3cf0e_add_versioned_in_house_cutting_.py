"""add versioned in-house cutting allocations

Revision ID: fa8791f3cf0e
Revises: bacb184a30d7
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
revision = 'fa8791f3cf0e'
down_revision = 'bacb184a30d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('species', sa.String(length=200), server_default=sa.text('NULL'), nullable=True))
    op.create_table('recipe_versions',
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('species', sa.String(length=200), nullable=False),
    sa.Column('input_product_id', sa.String(length=36), nullable=False),
    sa.Column('allocation_method', sa.String(length=16), nullable=False),
    sa.Column('available', sa.Boolean(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("allocation_method IN ('quantity','value')", name='ck_recipe_method'),
    sa.CheckConstraint('version > 0', name='ck_recipe_version'),
    sa.ForeignKeyConstraint(['input_product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code', 'version', name='uq_recipe_version'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('recipe_lines',
    sa.Column('recipe_version_id', sa.String(length=36), nullable=False),
    sa.Column('product_id', sa.String(length=36), nullable=False),
    sa.Column('reference_eur_per_kg', sa.Numeric(precision=18, scale=6), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint('reference_eur_per_kg IS NULL OR reference_eur_per_kg > 0', name='ck_recipe_reference'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['recipe_version_id'], ['recipe_versions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('recipe_version_id', 'product_id', name='uq_recipe_product'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('operation_differences',
    sa.Column('operation_id', sa.String(length=36), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.CheckConstraint("kind IN ('waste','other_loss')", name='ck_difference_kind'),
    sa.CheckConstraint('quantity > 0', name='ck_difference_quantity'),
    sa.ForeignKeyConstraint(['operation_id'], ['operations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.add_column('operation_outputs', sa.Column('reference_eur_per_kg', sa.Numeric(precision=18, scale=6), nullable=True))
    op.add_column('operation_outputs', sa.Column('explanation', sa.String(length=500), nullable=True))
    op.add_column('operations', sa.Column('recipe_version_id', sa.String(length=36), nullable=True))
    op.add_column('operations', sa.Column('allocation_snapshot', sa.JSON(none_as_null=True), nullable=True))
    op.create_foreign_key('fk_operations_recipe_version', 'operations', 'recipe_versions', ['recipe_version_id'], ['id'])
    op.add_column('receipt_lines', sa.Column('unit_price', sa.Numeric(precision=18, scale=6), nullable=True))


def downgrade():
    op.drop_column('receipt_lines', 'unit_price')
    op.drop_constraint('fk_operations_recipe_version', 'operations', type_='foreignkey')
    op.drop_column('operations', 'allocation_snapshot')
    op.drop_column('operations', 'recipe_version_id')
    op.drop_column('operation_outputs', 'explanation')
    op.drop_column('operation_outputs', 'reference_eur_per_kg')
    op.drop_table('operation_differences')
    op.drop_table('recipe_lines')
    op.drop_table('recipe_versions')
    op.drop_column('products', 'species')

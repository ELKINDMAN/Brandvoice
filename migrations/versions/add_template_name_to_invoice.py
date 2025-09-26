"""add template_name to Invoice

Revision ID: add_template_name_field
Revises: 815651a1ca0a
Create Date: 2025-09-26
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_template_name_field'
down_revision = '815651a1ca0a'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('invoice') as batch_op:
        batch_op.add_column(sa.Column('template_name', sa.String(length=100), nullable=True))
    # Optionally populate existing rows with default
    op.execute("UPDATE invoice SET template_name='invoice_template_1.html' WHERE template_name IS NULL")


def downgrade():
    with op.batch_alter_table('invoice') as batch_op:
        batch_op.drop_column('template_name')

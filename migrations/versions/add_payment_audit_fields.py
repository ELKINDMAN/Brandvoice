"""Add audit fields to payment

Revision ID: add_payment_audit_fields
Revises: add_payment_callback_log
Create Date: 2025-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_payment_audit_fields'
down_revision = 'add_payment_callback_log'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('payment') as batch_op:
        batch_op.add_column(sa.Column('flw_transaction_id', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('verified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('failure_reason', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('raw_meta', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('payment') as batch_op:
        batch_op.drop_column('flw_transaction_id')
        batch_op.drop_column('verified_at')
        batch_op.drop_column('failure_reason')
        batch_op.drop_column('raw_meta')

"""Add payment callback log table

Revision ID: add_payment_callback_log
Revises: add_failed_email_table
Create Date: 2025-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_payment_callback_log'
down_revision = 'add_subscription_table'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'payment_callback_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('payment_id', sa.Integer(), sa.ForeignKey('payment.id'), nullable=False),
        sa.Column('raw_query', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_payment_callback_log_payment_id', 'payment_callback_log', ['payment_id'])


def downgrade():
    op.drop_index('ix_payment_callback_log_payment_id', table_name='payment_callback_log')
    op.drop_table('payment_callback_log')

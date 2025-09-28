"""Add subscription table

Revision ID: add_subscription_table
Revises: add_subscription_payment
Create Date: 2025-09-28
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = 'add_subscription_table'
down_revision = 'add_last_renewal_reminder_field'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'subscription',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('plan_code', sa.String(length=100), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('current_period_start', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('last_tx_ref', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_subscription_user_plan', 'subscription', ['user_id', 'plan_code'], unique=False)


def downgrade():
    op.drop_index('ix_subscription_user_plan', table_name='subscription')
    op.drop_table('subscription')

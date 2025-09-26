"""Add trial, subscription, reset + payment model

Revision ID: add_subscription_payment
Revises: add_template_name_field
Create Date: 2025-09-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_subscription_payment'
down_revision = 'add_template_name_field'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('trial_start', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_premium', sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column('premium_expires_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('password_reset_token', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('password_reset_sent_at', sa.DateTime(), nullable=True))

    op.create_table(
        'payment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('tx_ref', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='initialized'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('tx_ref'),
    )

    # Initialize trial_start for existing users
    op.execute("UPDATE user SET trial_start = CURRENT_TIMESTAMP WHERE trial_start IS NULL")


def downgrade():
    op.drop_table('payment')
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('trial_start')
        batch_op.drop_column('is_premium')
        batch_op.drop_column('premium_expires_at')
        batch_op.drop_column('password_reset_token')
        batch_op.drop_column('password_reset_sent_at')

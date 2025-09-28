"""add last_renewal_reminder_sent_at field

Revision ID: add_last_renewal_reminder_field
Revises: add_subscription_payment
Create Date: 2025-09-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_last_renewal_reminder_field'
down_revision = 'add_subscription_payment'
branch_labels = None
depends_on = None


def upgrade():
	with op.batch_alter_table('user') as batch_op:
		batch_op.add_column(sa.Column('last_renewal_reminder_sent_at', sa.DateTime(), nullable=True))


def downgrade():
	with op.batch_alter_table('user') as batch_op:
		batch_op.drop_column('last_renewal_reminder_sent_at')


"""Create failed_email table (post hoc)

Revision ID: add_failed_email_table_post
Revises: add_webhook_log_table
Create Date: 2025-09-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'add_failed_email_table_post'
down_revision = 'add_webhook_log_table'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'failed_email' in inspector.get_table_names():
        return
    op.create_table(
        'failed_email',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('to_address', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_failed_email_to_address', 'failed_email', ['to_address'])


def downgrade():
    op.drop_index('ix_failed_email_to_address', table_name='failed_email')
    op.drop_table('failed_email')

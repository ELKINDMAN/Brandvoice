"""Add webhook log table

Revision ID: add_webhook_log_table
Revises: add_payment_audit_fields
Create Date: 2025-09-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'add_webhook_log_table'
down_revision = 'add_payment_audit_fields'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = inspector.get_table_names()
    if 'webhook_log' in existing:
        # Table (and likely index) already created in a prior partial run; skip.
        return
    op.create_table(
        'webhook_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tx_ref', sa.String(length=255), nullable=True),
        sa.Column('event', sa.String(length=100), nullable=True),
        sa.Column('payload_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    # Create index only if not auto-created and still missing
    # For SQLite, simple attempt guarded by inspection
    # (SQLite doesn't list indexes by column easily without pragma; keep simple)
    try:
        op.create_index('ix_webhook_log_tx_ref', 'webhook_log', ['tx_ref'])
    except Exception:
        pass


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'webhook_log' in inspector.get_table_names():
        try:
            op.drop_index('ix_webhook_log_tx_ref', table_name='webhook_log')
        except Exception:
            pass
        op.drop_table('webhook_log')

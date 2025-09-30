"""Add location field to business_profile

Revision ID: add_business_profile_location
Revises: add_failed_email_table_post
Create Date: 2025-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_business_profile_location'
down_revision = 'add_failed_email_table_post'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('business_profile') as batch_op:
        batch_op.add_column(sa.Column('location', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('business_profile') as batch_op:
        batch_op.drop_column('location')

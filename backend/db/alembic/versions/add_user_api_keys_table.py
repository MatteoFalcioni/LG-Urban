"""Add UserAPIKeys table for encrypted API key storage

Revision ID: add_user_api_keys
Revises: ac00f878b352
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_api_keys'
down_revision = 'ac00f878b352'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_api_keys table
    op.create_table('user_api_keys',
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('openai_key', sa.Text(), nullable=True),
        sa.Column('anthropic_key', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )
    
    # Create index on user_id
    op.create_index(op.f('ix_user_api_keys_user_id'), 'user_api_keys', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f('ix_user_api_keys_user_id'), table_name='user_api_keys')
    
    # Drop table
    op.drop_table('user_api_keys')

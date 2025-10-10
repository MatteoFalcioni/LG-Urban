"""rename_message_key_to_message_id

Revision ID: ac00f878b352
Revises: 0001_baseline
Create Date: 2025-10-06 17:31:41.895589
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'ac00f878b352'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('messages', 'message_key', new_column_name='message_id')


def downgrade() -> None:
    op.alter_column('messages', 'message_id', new_column_name='message_key')



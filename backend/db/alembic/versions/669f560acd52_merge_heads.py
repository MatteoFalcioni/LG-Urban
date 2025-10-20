"""merge_heads

Revision ID: 669f560acd52
Revises: 980ae8fe2fe4, add_user_api_keys
Create Date: 2025-10-20 14:57:02.947472
"""

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '669f560acd52'
down_revision = ('980ae8fe2fe4', 'add_user_api_keys')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass



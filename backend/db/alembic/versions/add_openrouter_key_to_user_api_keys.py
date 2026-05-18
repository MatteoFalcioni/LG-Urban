"""Add openrouter_key column to user_api_keys table

Revision ID: add_openrouter_key
Revises: 669f560acd52
Create Date: 2025-02-12 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_openrouter_key"
down_revision = "669f560acd52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add openrouter_key column to user_api_keys table
    op.add_column(
        "user_api_keys",
        sa.Column("openrouter_key", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Remove openrouter_key column from user_api_keys table
    op.drop_column("user_api_keys", "openrouter_key")

"""added field created_at for booking table

Revision ID: 1c94a21a2fb7
Revises: 41a8d65ff17d
Create Date: 2025-07-03 13:53:18.624294

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c94a21a2fb7'
down_revision: Union[str, Sequence[str], None] = '41a8d65ff17d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite-compatible way to add created_at column
    
    # Step 1: Add column without default (SQLite allows this)
    op.add_column('bookings', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    
    # Step 2: Update existing rows with current timestamp
    from sqlalchemy import text
    connection = op.get_bind()
    connection.execute(text("UPDATE bookings SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bookings', 'created_at')
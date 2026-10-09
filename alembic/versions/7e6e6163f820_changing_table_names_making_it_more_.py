"""changing table names, making it more distinct

Revision ID: 7e6e6163f820
Revises: 80eebe7436f5
Create Date: 2026-10-04 08:33:23.969175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e6e6163f820'
down_revision: Union[str, Sequence[str], None] = '80eebe7436f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('healthy_electric_baseline', 'healthy_electric_features')
    op.rename_table('healthy_vibration_baseline', 'healthy_vibration_features')


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table('healthy_electric_features', 'healthy_electric_baseline')
    op.rename_table('healthy_vibration_features', 'healthy_vibration_baseline')
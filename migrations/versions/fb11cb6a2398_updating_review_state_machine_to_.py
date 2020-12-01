"""Updating review state machine to include NEEDS_IMPROVEMENT state.

Revision ID: fb11cb6a2398
Revises: 4d799bc13b95
Create Date: 2020-09-13 11:03:39.400868

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "fb11cb6a2398"
down_revision = "4d799bc13b95"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="vulnerability",
        column_name="state",
        type_=sa.Enum(
            "NEW",
            "NEEDS_IMPROVEMENT",
            "READY",
            "IN_REVIEW",
            "REVIEWED",
            "PUBLISHED",
            "ARCHIVED",
            name="vulnerabilitystate",
        ),
        nullable=False,
    )


def downgrade():
    op.alter_column(
        table_name="vulnerability",
        column_name="state",
        type_=sa.Enum(
            "NEW",
            "READY",
            "IN_REVIEW",
            "REVIEWED",
            "PUBLISHED",
            "ARCHIVED",
            name="vulnerabilitystate",
        ),
        nullable=False,
    )

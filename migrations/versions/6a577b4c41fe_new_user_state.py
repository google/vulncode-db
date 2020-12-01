"""new user state

Revision ID: 6a577b4c41fe
Revises: 6704686720fa
Create Date: 2020-11-24 13:13:25.967425

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6a577b4c41fe"
down_revision = "6704686720fa"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "user",
        "state",
        existing_type=sa.Enum("REGISTERED", "ACTIVE", "BLOCKED", name="userstate"),
        type_=sa.Enum(
            "REGISTERED", "ACTIVE", "BLOCKED", "FIRST_LOGIN", name="userstate"
        ),
    )


def downgrade():
    op.alter_column(
        "user",
        "state",
        type_=sa.Enum("REGISTERED", "ACTIVE", "BLOCKED", name="userstate"),
        existing_type=sa.Enum(
            "REGISTERED", "ACTIVE", "BLOCKED", "FIRST_LOGIN", name="userstate"
        ),
    )

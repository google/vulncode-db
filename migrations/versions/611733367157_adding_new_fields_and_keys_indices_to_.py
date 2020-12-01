"""Adding new fields and keys / indices to the vulnerability table to support states.

Revision ID: 611733367157
Revises: 9a935d8fb960
Create Date: 2020-04-25 11:52:22.369350

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "611733367157"
down_revision = "9a935d8fb960"
branch_labels = None
depends_on = None


def upgrade():
    # Drop all foreign keys on vulnerability.id as we intend to update it.
    op.drop_constraint(
        "vulnerability_git_commits_ibfk_1",
        "vulnerability_git_commits",
        type_="foreignkey",
    )
    # To make things simpler we will sever the complete link to vulnerability resources for now.
    op.drop_constraint(
        "vulnerability_resources_ibfk_1", "vulnerability_resources", type_="foreignkey"
    )
    op.drop_column("vulnerability_resources", "vulnerability_details_id")
    # ----------------------------------------------------------------------------------------------------
    # Add new columns to the vulnerability table.
    op.add_column(
        "vulnerability", sa.Column("review_feedback", sa.Text(), nullable=True)
    )
    op.add_column(
        "vulnerability", sa.Column("reviewer_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_reviewer_id", "vulnerability", "user", ["reviewer_id"], ["id"]
    )
    op.add_column(
        "vulnerability",
        sa.Column(
            "state",
            sa.Enum(
                "NEW",
                "READY",
                "IN_REVIEW",
                "REVIEWED",
                "PUBLISHED",
                "ARCHIVED",
                name="vulnerabilitystate",
            ),
            nullable=False,
        ),
    )
    op.add_column("vulnerability", sa.Column("version", sa.Integer(), nullable=False))
    # Update the vulnerability primary key.
    # Remove autoincrement from the PK as there can only be one auto key and it has to be the PK.
    op.alter_column(
        "vulnerability",
        "id",
        existing_type=sa.Integer(),
        autoincrement=False,
        nullable=False,
    )
    op.drop_constraint("id", "vulnerability", type_="primary")
    # Now we can define a new primary key.
    op.create_primary_key("pk", "vulnerability", ["id", "version"])
    # Re-enable auto incrementing for the id column, too.
    op.alter_column(
        "vulnerability",
        "id",
        existing_type=sa.Integer(),
        autoincrement=True,
        nullable=False,
    )
    # ---------------------------------------------------------------------------------------------------
    # A CVE ID can appear multiple times across different versions so we need to remove it's unique constraint.
    op.drop_index("cve_id", table_name="vulnerability")
    op.create_unique_constraint("uk_ver_cve_id", "vulnerability", ["version", "cve_id"])
    op.create_index(
        op.f("ix_vulnerability_cve_id"), "vulnerability", ["cve_id"], unique=False
    )
    # ----------------------------------------------------------------------------------------------------
    # Now that the vulnerability multi column primary key is intact, create the foreign keys again.
    op.add_column(
        "vulnerability_git_commits", sa.Column("version", sa.Integer(), nullable=False)
    )
    op.alter_column(
        "vulnerability_git_commits",
        "vulnerability_details_id",
        existing_type=mysql.INTEGER(display_width=11),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_vuln",
        "vulnerability_git_commits",
        "vulnerability",
        ["vulnerability_details_id", "version"],
        ["id", "version"],
    )


def downgrade():
    op.drop_constraint("fk_vuln", "vulnerability_git_commits", type_="foreignkey")
    op.alter_column(
        "vulnerability_git_commits",
        "vulnerability_details_id",
        existing_type=mysql.INTEGER(display_width=11),
        nullable=True,
    )
    op.drop_column("vulnerability_git_commits", "version")

    op.drop_index(op.f("ix_vulnerability_cve_id"), table_name="vulnerability")
    op.drop_constraint("uk_ver_cve_id", "vulnerability", type_="unique")
    op.create_index("cve_id", "vulnerability", ["cve_id"], unique=True)
    # Remove autoincrement from the PK as there can only be one auto key and it has to be the PK.
    op.alter_column(
        "vulnerability",
        "id",
        existing_type=sa.Integer(),
        autoincrement=False,
        nullable=False,
    )
    op.drop_constraint("pk", "vulnerability", type_="primary")
    op.create_primary_key("id", "vulnerability", ["id"])
    op.alter_column(
        "vulnerability",
        "id",
        existing_type=sa.Integer(),
        autoincrement=True,
        nullable=False,
    )

    op.drop_column("vulnerability", "version")
    op.drop_column("vulnerability", "state")
    op.drop_constraint("fk_reviewer_id", "vulnerability", type_="foreignkey")
    op.drop_column("vulnerability", "reviewer_id")
    op.drop_column("vulnerability", "review_feedback")

    op.add_column(
        "vulnerability_resources",
        sa.Column(
            "vulnerability_details_id",
            mysql.INTEGER(display_width=11),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "vulnerability_resources_ibfk_1",
        "vulnerability_resources",
        "vulnerability",
        ["vulnerability_details_id"],
        ["id"],
    )
    op.create_foreign_key(
        "vulnerability_git_commits_ibfk_1",
        "vulnerability_git_commits",
        "vulnerability",
        ["vulnerability_details_id"],
        ["id"],
    )

"""add post generation tables

Revision ID: c3d4e5f6a7b8
Revises: 8aa59c24587b
Create Date: 2026-06-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "8aa59c24587b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "request_filters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_uuid", sa.String(), nullable=False),
        sa.Column("site", sa.Enum("COPART", "IAAI", name="auctionenum"), nullable=False),
        sa.Column("make", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("year_to", sa.Integer(), nullable=True),
        sa.Column("odo_from", sa.Integer(), nullable=True),
        sa.Column("odo_to", sa.Integer(), nullable=True),
        sa.Column("document", sa.String(), nullable=True),
        sa.Column("transmission", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("auction_date_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auction_date_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("drive", sa.String(), nullable=True),
        sa.Column("auction_time", sa.String(), nullable=True),
        sa.Column(
            "stage",
            sa.Enum("FAILED", "IN_PROGRESS", "COMPLETED", name="requeststage"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "post",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lot_id", sa.Integer(), nullable=False),
        sa.Column("auction", sa.Enum("COPART", "IAAI", name="auctionenum"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("make", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("odometer", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("reserve_price", sa.Integer(), nullable=True),
        sa.Column("vin", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_price", sa.Integer(), nullable=False),
        sa.Column("shipping_price", sa.Integer(), nullable=False),
        sa.Column("broker_fee", sa.Integer(), nullable=False, server_default="299"),
        sa.Column("average_sell_price", sa.Integer(), nullable=True),
        sa.Column("primary_damage", sa.String(), nullable=True),
        sa.Column("is_posted", sa.Boolean(), nullable=False),
        sa.Column("image_description", sa.String(), nullable=True),
        sa.Column("images", sa.String(), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["request_filters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "generation_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "job_type",
            sa.Enum(
                "with_filters",
                "manually",
                "add_comment",
                "generate_image",
                "publish_post",
                name="generationjobtype",
            ),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "done", "failed", name="generationjobstatus"),
            nullable=False,
        ),
        sa.Column("user_uuid", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("generation_job")
    op.drop_table("post")
    op.drop_table("request_filters")
    op.execute("DROP TYPE IF EXISTS generationjobtype")
    op.execute("DROP TYPE IF EXISTS generationjobstatus")
    op.execute("DROP TYPE IF EXISTS requeststage")
    op.execute("DROP TYPE IF EXISTS auctionenum")

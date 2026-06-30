"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nodes",
        sa.Column("node_id", sa.String(length=128), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="offline"),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_metrics", sa.JSON(), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("node_id", sa.String(length=128), sa.ForeignKey("nodes.node_id"), index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_ref", sa.String(length=512), nullable=True),
        sa.Column("snapshot_omitted_reason", sa.String(length=128), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
    )
    op.create_table(
        "detections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(length=64), sa.ForeignKey("events.event_id"), index=True),
        sa.Column("label", sa.String(length=128), index=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=256), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("detections")
    op.drop_table("events")
    op.drop_table("users")
    op.drop_table("nodes")

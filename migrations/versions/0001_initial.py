"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watch_targets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("market", sa.String(length=16), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "target_type", name="uq_watch_targets_symbol_type"),
    )
    op.create_index("ix_watch_targets_symbol", "watch_targets", ["symbol"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("data_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_items_created_at", "evidence_items", ["created_at"])
    op.create_index("ix_evidence_items_symbol", "evidence_items", ["symbol"])

    op.create_table(
        "push_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("push_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("push_id", name="uq_push_records_push_id"),
    )
    op.create_index("ix_push_records_created_at", "push_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_push_records_created_at", table_name="push_records")
    op.drop_table("push_records")

    op.drop_index("ix_evidence_items_symbol", table_name="evidence_items")
    op.drop_index("ix_evidence_items_created_at", table_name="evidence_items")
    op.drop_table("evidence_items")

    op.drop_table("app_settings")

    op.drop_index("ix_watch_targets_symbol", table_name="watch_targets")
    op.drop_table("watch_targets")

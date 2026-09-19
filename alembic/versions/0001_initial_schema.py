"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-19 08:39:47.012832
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("api_key_hash", sa.String(), nullable=True),
        sa.Column("api_key_created_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_servers")),
        sa.UniqueConstraint("api_key_hash", name=op.f("uq_servers_api_key_hash")),
        sa.UniqueConstraint("name", name=op.f("uq_servers_name")),
    )
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["servers.id"],
            name=op.f("fk_books_server_id_servers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_books")),
    )
    with op.batch_alter_table("books", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_books_author"), ["author"], unique=False)
        batch_op.create_index(batch_op.f("ix_books_category"), ["category"], unique=False)
        batch_op.create_index(batch_op.f("ix_books_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_books_server_id"), ["server_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("books", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_books_server_id"))
        batch_op.drop_index(batch_op.f("ix_books_created_at"))
        batch_op.drop_index(batch_op.f("ix_books_category"))
        batch_op.drop_index(batch_op.f("ix_books_author"))

    op.drop_table("books")
    op.drop_table("servers")

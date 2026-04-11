"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-04-11
"""

import sqlalchemy as sa
from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("mode", sa.Text, nullable=False, server_default="'general'"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column(
            "session_id",
            sa.Text,
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tool_name", sa.Text, nullable=True),
        sa.Column("is_compressed", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "profile",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("height_cm", sa.Float, nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("build", sa.Text, nullable=True),
        sa.Column("fitness_level", sa.Text, nullable=True),
        sa.Column("injury_history", sa.Text, nullable=True),
        sa.Column("dietary_restrictions", sa.Text, nullable=True),
        sa.Column("dietary_preferences", sa.Text, nullable=True),
        sa.Column("dietary_approach", sa.Text, nullable=True),
        sa.Column("aesthetic_style", sa.Text, nullable=True),
        sa.Column("brand_rejections", sa.Text, nullable=True),
        sa.Column("climate", sa.Text, nullable=True),
        sa.Column("activity_level", sa.Text, nullable=True),
        sa.Column("living_situation", sa.Text, nullable=True),
        sa.Column("country", sa.Text, nullable=True),
        sa.Column("budget_psychology", sa.Text, nullable=True),
        sa.Column("fitness_goal", sa.Text, nullable=True),
        sa.Column("dietary_goal", sa.Text, nullable=True),
        sa.Column("lifestyle_focus", sa.Text, nullable=True),
        sa.Column("first_session_at", sa.DateTime, nullable=True),
        sa.Column("field_timestamps", sa.Text, nullable=False, server_default=sa.text("'{}'")),
    )

    op.create_table(
        "history",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("item_name", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("domain", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("follow_up_due_at", sa.DateTime, nullable=True),
        sa.Column("check_in_due_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "preferences",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("dimension", sa.Text, nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
    )

    settings_table = sa.table(
        "settings",
        sa.column("key", sa.Text),
        sa.column("value", sa.Text),
    )
    op.bulk_insert(
        settings_table,
        [
            {"key": "follow_up_cadence", "value": '"off"'},
            {"key": "proactive_surfacing", "value": '"true"'},
            {
                "key": "decay_thresholds",
                "value": (
                    '{"goals": 60, "fitness_level": 90, "dietary_approach": 90,'
                    ' "body_metrics": 180, "taste_lifestyle": 365}'
                ),
            },
            {"key": "max_tool_calls_per_turn", "value": '"6"'},
        ],
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("preferences")
    op.drop_table("history")
    op.drop_table("profile")
    op.drop_table("messages")
    op.drop_table("sessions")

"""Add indices for frequently queried columns

Revision ID: 002_add_indices
Revises: 001_initial
Create Date: 2026-04-18
"""

from alembic import op

revision = "002_add_indices"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_messages_session_id", "messages", ["session_id"])
    op.create_index("idx_history_domain", "history", ["domain"])
    op.create_index("idx_history_status", "history", ["status"])
    op.create_index("idx_history_follow_up_due", "history", ["follow_up_due_at"])
    op.create_index("idx_history_check_in_due", "history", ["check_in_due_at"])
    op.create_index("idx_preferences_dimension", "preferences", ["dimension"])


def downgrade() -> None:
    op.drop_index("idx_messages_session_id", "messages")
    op.drop_index("idx_history_domain", "history")
    op.drop_index("idx_history_status", "history")
    op.drop_index("idx_history_follow_up_due", "history")
    op.drop_index("idx_history_check_in_due", "history")
    op.drop_index("idx_preferences_dimension", "preferences")

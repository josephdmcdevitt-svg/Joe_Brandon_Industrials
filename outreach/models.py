"""
Outreach tracking models - supplements database/models.py

Adds OutreachState (per-company follow-up tracking) and
NotificationAccount (secondary Gmail for internal reminders only).
These tables are created alongside the main schema via init_db().
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

# ---------------------------------------------------------------------------
# Pull in the shared declarative Base so these tables are registered with
# the same metadata that init_db() calls create_all() on.
# ---------------------------------------------------------------------------
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import Base  # noqa: E402


class OutreachState(Base):
    """
    One row per (company, contact, user) combination.
    Tracks where a prospect sits in the follow-up cadence.

    Status lifecycle:
        new  ->  awaiting_reply  ->  replied
                                  ->  suppressed
                                  ->  closed
    """

    __tablename__ = "outreach_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id = Column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Gmail thread that ties all messages in this sequence together
    gmail_thread_id = Column(String(256), nullable=True, index=True)

    # Timestamps
    first_sent_at = Column(DateTime, nullable=True)
    last_sent_at = Column(DateTime, nullable=True)
    reply_detected_at = Column(DateTime, nullable=True)
    next_followup_due = Column(DateTime, nullable=True, index=True)

    # Cadence position
    # 0 = initial outreach sent, 1 = FU1 sent, 2 = FU2 sent, 3 = FU3 sent
    current_followup_stage = Column(Integer, default=0, nullable=False)

    # Reply tracking
    reply_detected = Column(Boolean, default=False, nullable=False)

    # Status: new | awaiting_reply | replied | suppressed | closed
    status = Column(String(32), default="new", nullable=False)
    closed_reason = Column(String(128), nullable=True)

    # Optional JSON string — stores a custom cadence list if the user
    # overrides the default for this specific outreach sequence.
    followup_cadence = Column(Text, nullable=True)

    # Safety flags
    is_suppressed = Column(Boolean, default=False, nullable=False)
    suppression_reason = Column(String(256), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_outreach_status_user", "status", "user_id"),
        Index("ix_outreach_followup_due", "next_followup_due", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<OutreachState id={self.id} company_id={self.company_id} "
            f"stage={self.current_followup_stage} status={self.status!r}>"
        )


class NotificationAccount(Base):
    """
    Optional secondary Gmail account used ONLY to send internal reminders
    to the user (e.g. daily digest, follow-up nudges).

    MUST NOT be used to contact prospects.
    """

    __tablename__ = "notification_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    email = Column(String(255), nullable=False)
    gmail_refresh_token = Column(Text, nullable=True)
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<NotificationAccount id={self.id} email={self.email!r} active={self.is_active}>"

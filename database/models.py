from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Pipeline stage constants
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    "new_lead",
    "enriched",
    "draft_ready",
    "contacted",
    "replied",
    "call_scheduled",
    "audit_sold",
    "audit_delivered",
    "implementation_opportunity",
    "closed_lost",
]

DRAFT_TYPES = ["email_initial", "email_followup", "linkedin_message", "call_script"]
DRAFT_STATUSES = ["draft", "approved", "sent", "failed"]
SENT_EMAIL_STATUSES = ["sent", "delivered", "replied", "bounced"]
SUPPRESSION_REASONS = ["unsubscribed", "do_not_contact", "bounced", "complaint"]


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    gmail_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gmail_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    daily_send_cap: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="created_by", foreign_keys="Company.created_by_id"
    )
    drafts: Mapped[list["Draft"]] = relationship("Draft", back_populates="user")
    sent_emails: Mapped[list["SentEmail"]] = relationship("SentEmail", back_populates="user")
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="user")
    notes: Mapped[list["Note"]] = relationship("Note", back_populates="user")
    suppression_entries: Mapped[list["SuppressionEntry"]] = relationship(
        "SuppressionEntry", back_populates="added_by"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metro_area: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sub_industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    employee_count_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_revenue_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_revenue_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revenue_is_estimated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ownership_style: Mapped[str] = mapped_column(
        String(64), default="owner-operated", nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON-encoded list fields
    probable_systems: Mapped[str | None] = mapped_column(Text, nullable=True)
    pain_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_opportunities: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_fit_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    offer_conversion_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offer_conversion_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    pipeline_stage: Mapped[str] = mapped_column(
        String(64), default="new_lead", nullable=False, index=True
    )
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)

    enriched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    created_by: Mapped["User | None"] = relationship(
        "User", back_populates="companies", foreign_keys=[created_by_id]
    )
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="company", cascade="all, delete-orphan"
    )
    drafts: Mapped[list["Draft"]] = relationship(
        "Draft", back_populates="company", cascade="all, delete-orphan"
    )
    sent_emails: Mapped[list["SentEmail"]] = relationship(
        "SentEmail", back_populates="company", cascade="all, delete-orphan"
    )
    company_notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="company", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_companies_industry_stage", "industry", "pipeline_stage"),
        Index("ix_companies_metro_stage", "metro_area", "pipeline_stage"),
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name!r} stage={self.pipeline_stage!r}>"


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_decision_maker: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suppression_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="contacts")
    drafts: Mapped[list["Draft"]] = relationship("Draft", back_populates="contact")
    sent_emails: Mapped[list["SentEmail"]] = relationship("SentEmail", back_populates="contact")

    def __repr__(self) -> str:
        return (
            f"<Contact id={self.id} name={self.first_name!r} {self.last_name!r} "
            f"email={self.email!r}>"
        )


# ---------------------------------------------------------------------------
# Draft
# ---------------------------------------------------------------------------
class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    draft_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    gmail_draft_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="drafts")
    contact: Mapped["Contact | None"] = relationship("Contact", back_populates="drafts")
    user: Mapped["User | None"] = relationship("User", back_populates="drafts")
    sent_email: Mapped["SentEmail | None"] = relationship(
        "SentEmail", back_populates="draft", uselist=False
    )

    def __repr__(self) -> str:
        return (
            f"<Draft id={self.id} type={self.draft_type!r} status={self.status!r} "
            f"company_id={self.company_id}>"
        )


# ---------------------------------------------------------------------------
# SentEmail
# ---------------------------------------------------------------------------
class SentEmail(Base):
    __tablename__ = "sent_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("drafts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="sent", nullable=False, index=True)

    # Relationships
    draft: Mapped["Draft | None"] = relationship("Draft", back_populates="sent_email")
    company: Mapped["Company"] = relationship("Company", back_populates="sent_emails")
    contact: Mapped["Contact | None"] = relationship("Contact", back_populates="sent_emails")
    user: Mapped["User | None"] = relationship("User", back_populates="sent_emails")

    def __repr__(self) -> str:
        return (
            f"<SentEmail id={self.id} to={self.recipient_email!r} "
            f"status={self.status!r} sent_at={self.sent_at}>"
        )


# ---------------------------------------------------------------------------
# SuppressionEntry
# ---------------------------------------------------------------------------
class SuppressionEntry(Base):
    __tablename__ = "suppression_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    added_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    added_by: Mapped["User | None"] = relationship(
        "User", back_populates="suppression_entries"
    )

    def __repr__(self) -> str:
        return f"<SuppressionEntry email={self.email!r} reason={self.reason!r}>"


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------
class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="activities")

    __table_args__ = (
        Index("ix_activities_entity", "entity_type", "entity_id"),
        Index("ix_activities_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Activity id={self.id} action={self.action!r} "
            f"entity_type={self.entity_type!r} entity_id={self.entity_id}>"
        )


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------
class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="company_notes")
    user: Mapped["User | None"] = relationship("User", back_populates="notes")

    def __repr__(self) -> str:
        return f"<Note id={self.id} company_id={self.company_id} user_id={self.user_id}>"

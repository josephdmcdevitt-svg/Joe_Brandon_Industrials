"""
Follow-Up Workflow Engine

Human-supervised follow-up management. NO automatic sending.
All follow-ups require explicit user review and approval before anything
leaves this application.

Compliance rules enforced here:
  - No email is ever sent from this module.
  - No bulk or batch sending is initiated here.
  - No randomised or scheduled timing — cadence is calendar-based only.
  - Every action that would result in an email requires the user to
    explicitly approve it through the Streamlit UI.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cadence configuration
# ---------------------------------------------------------------------------
# Delays are expressed in *business days* (Mon-Fri, no weekends) after the
# date the previous email was sent.
DEFAULT_CADENCE: list[dict] = [
    {"stage": 1, "delay_business_days": 3,  "label": "Follow-Up 1 (3 business days)"},
    {"stage": 2, "delay_business_days": 7,  "label": "Follow-Up 2 (7 business days)"},
    {"stage": 3, "delay_business_days": 14, "label": "Follow-Up 3 (14 business days)"},
]

MAX_FOLLOWUPS = 3


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def add_business_days(start_date: datetime, business_days: int) -> datetime:
    """
    Return the date that is *business_days* Mon-Fri days after *start_date*.
    Saturdays and Sundays are skipped entirely.

    Examples
    --------
    >>> add_business_days(datetime(2024, 3, 14), 3)  # Thursday + 3bd -> Tuesday
    datetime(2024, 3, 19, ...)
    """
    if business_days < 0:
        raise ValueError("business_days must be >= 0")

    current = start_date
    days_added = 0
    while days_added < business_days:
        current += timedelta(days=1)
        # weekday() returns 0=Mon .. 6=Sun; skip 5=Sat and 6=Sun
        if current.weekday() < 5:
            days_added += 1

    return current


def get_followup_cadence(custom_cadence: Optional[list[dict]] = None) -> list[dict]:
    """
    Return the cadence schedule to use for a given outreach sequence.

    If *custom_cadence* is provided and non-empty it overrides the global
    DEFAULT_CADENCE.  Each entry must contain at minimum:
        {"stage": int, "delay_business_days": int, "label": str}
    """
    if custom_cadence:
        return custom_cadence
    return DEFAULT_CADENCE


# ---------------------------------------------------------------------------
# Main tracker class
# ---------------------------------------------------------------------------

class OutreachTracker:
    """
    Manages follow-up state for company/contact pairs.

    All methods that would result in sending email ONLY update database
    state and return data for the UI to display.  The UI is responsible for
    the actual send action after the user clicks an explicit approval button.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_create_state(
        self,
        company_id: int,
        contact_id: int,
        user_id: int,
    ) -> "OutreachState":  # type: ignore[name-defined]
        """Fetch an existing OutreachState or create a fresh one."""
        # Import here to avoid circular imports at module level
        from outreach.models import OutreachState

        state = (
            self._session.query(OutreachState)
            .filter_by(company_id=company_id, contact_id=contact_id, user_id=user_id)
            .first()
        )
        if state is None:
            state = OutreachState(
                company_id=company_id,
                contact_id=contact_id,
                user_id=user_id,
                status="new",
                current_followup_stage=0,
            )
            self._session.add(state)
            self._session.flush()
            logger.debug(
                "Created new OutreachState company_id=%s contact_id=%s",
                company_id, contact_id,
            )
        return state

    def _get_cadence_for_state(self, state: "OutreachState") -> list[dict]:  # type: ignore[name-defined]
        """Parse the cadence stored on a state row, falling back to default."""
        if state.followup_cadence:
            try:
                return json.loads(state.followup_cadence)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Could not parse followup_cadence JSON for OutreachState id=%s, "
                    "using default",
                    state.id,
                )
        return DEFAULT_CADENCE

    def _log_activity(
        self,
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: int,
        details: Optional[str] = None,
    ) -> None:
        """Append an Activity row for audit-trail purposes."""
        from database.models import Activity

        activity = Activity(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        self._session.add(activity)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_send(
        self,
        company_id: int,
        contact_id: int,
        user_id: int,
        draft_id: int,
        gmail_message_id: str,
        gmail_thread_id: str,
    ) -> dict:
        """
        Record that an email was approved and sent by the user.

        Updates (or creates) the OutreachState for this company/contact,
        advances the stage counter, and calculates the next follow-up due
        date based on the cadence.

        Returns the updated tracking-state as a plain dict for the UI.

        NOTE: This method does NOT send any email.  It is called AFTER the
        Gmail API send has already succeeded via user action in the UI.
        """
        from database.models import Company, Contact, SentEmail

        now = datetime.utcnow()

        state = self._get_or_create_state(company_id, contact_id, user_id)

        # Set first_sent_at only on the very first send
        if state.first_sent_at is None:
            state.first_sent_at = now

        state.last_sent_at = now
        state.gmail_thread_id = gmail_thread_id
        state.reply_detected = False
        state.status = "awaiting_reply"

        # Advance stage: 0 -> 1 means "initial sent", 1->2 means "FU1 sent", etc.
        state.current_followup_stage += 1

        # Calculate when the NEXT follow-up would be due (if we haven't
        # exhausted the cadence)
        cadence = self._get_cadence_for_state(state)
        next_stage_index = state.current_followup_stage  # already incremented above

        # cadence list is 0-indexed: index 0 = stage 1 (first follow-up)
        if next_stage_index <= len(cadence) and next_stage_index <= MAX_FOLLOWUPS:
            cadence_entry = cadence[next_stage_index - 1]  # -1 because stage starts at 1
            # Only set next due if there IS a next follow-up in the sequence
            remaining_stages = [c for c in cadence if c["stage"] > state.current_followup_stage - 1]
            if remaining_stages:
                next_entry = remaining_stages[0]
                state.next_followup_due = add_business_days(
                    now, next_entry["delay_business_days"]
                )
            else:
                state.next_followup_due = None
        else:
            # No more follow-ups in cadence
            state.next_followup_due = None

        state.updated_at = now

        # Update the associated Draft status
        from database.models import Draft
        draft = self._session.get(Draft, draft_id)
        if draft is not None:
            draft.status = "sent"

        # Log the activity
        company = self._session.get(Company, company_id)
        company_name = company.name if company else f"company_id={company_id}"
        self._log_activity(
            user_id=user_id,
            action="email_sent",
            entity_type="company",
            entity_id=company_id,
            details=json.dumps({
                "gmail_message_id": gmail_message_id,
                "gmail_thread_id": gmail_thread_id,
                "stage": state.current_followup_stage,
                "draft_id": draft_id,
            }),
        )

        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            logger.exception("Failed to commit record_send for company_id=%s", company_id)
            raise

        result = {
            "company_id": company_id,
            "company_name": company_name,
            "contact_id": contact_id,
            "user_id": user_id,
            "gmail_thread_id": gmail_thread_id,
            "first_sent_at": state.first_sent_at,
            "last_sent_at": state.last_sent_at,
            "current_followup_stage": state.current_followup_stage,
            "next_followup_due": state.next_followup_due,
            "status": state.status,
        }
        logger.info(
            "Recorded send: company=%s stage=%s next_due=%s",
            company_name, state.current_followup_stage, state.next_followup_due,
        )
        return result

    # ------------------------------------------------------------------

    def check_for_reply(self, company_id: int, gmail_service) -> bool:
        """
        Check the Gmail thread for this company for replies from external
        addresses (i.e. not from the user themselves).

        If a reply is found the OutreachState is updated:
            - reply_detected = True
            - reply_detected_at = now
            - status = "replied"
            - next_followup_due = None  (no further follow-up needed)

        Returns True if a reply was detected, False otherwise.

        *gmail_service* is an authenticated googleapiclient Resource object.
        """
        from database.models import Company

        state = (
            self._session.query(__import__("outreach.models", fromlist=["OutreachState"]).OutreachState)
            .filter_by(company_id=company_id)
            .first()
        )

        # Re-import cleanly
        from outreach.models import OutreachState

        state = (
            self._session.query(OutreachState)
            .filter_by(company_id=company_id)
            .filter(OutreachState.gmail_thread_id.isnot(None))
            .first()
        )

        if state is None or not state.gmail_thread_id:
            logger.debug("No outreach state / thread for company_id=%s", company_id)
            return False

        if state.reply_detected:
            logger.debug(
                "Reply already recorded for company_id=%s, skipping API check", company_id
            )
            return True

        try:
            thread_data = (
                gmail_service.users()
                .threads()
                .get(userId="me", id=state.gmail_thread_id, format="metadata")
                .execute()
            )
        except Exception:
            logger.exception(
                "Gmail API error checking thread %s for company_id=%s",
                state.gmail_thread_id, company_id,
            )
            return False

        messages = thread_data.get("messages", [])
        if len(messages) <= 1:
            # Only the original outbound message — no reply yet
            return False

        # Identify the user's own email address (sender of the original message)
        # The first message in the thread is always ours.
        first_msg_headers = {
            h["name"].lower(): h["value"]
            for h in messages[0].get("payload", {}).get("headers", [])
        }
        our_email = first_msg_headers.get("from", "").lower()

        reply_found = False
        reply_snippet = ""
        reply_timestamp = None

        for msg in messages[1:]:
            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            sender = headers.get("from", "").lower()

            # A reply is any message where the sender is NOT us
            if our_email and our_email in sender:
                continue  # This is a follow-up we sent in the same thread

            # External reply detected
            reply_found = True
            reply_snippet = msg.get("snippet", "")

            # internalDate is epoch ms as a string
            internal_date_ms = msg.get("internalDate")
            if internal_date_ms:
                try:
                    reply_timestamp = datetime.utcfromtimestamp(int(internal_date_ms) / 1000)
                except (ValueError, TypeError):
                    reply_timestamp = datetime.utcnow()
            else:
                reply_timestamp = datetime.utcnow()
            break

        if reply_found:
            now = datetime.utcnow()
            state.reply_detected = True
            state.reply_detected_at = reply_timestamp or now
            state.status = "replied"
            state.next_followup_due = None
            state.updated_at = now

            # Update SentEmail rows for this thread
            from database.models import SentEmail

            sent = (
                self._session.query(SentEmail)
                .filter_by(gmail_thread_id=state.gmail_thread_id)
                .all()
            )
            for s in sent:
                if s.status == "sent":
                    s.status = "replied"
                    s.replied_at = reply_timestamp or now

            # Update Company pipeline stage
            company = self._session.get(Company, company_id)
            if company and company.pipeline_stage not in (
                "call_scheduled", "audit_sold", "audit_delivered",
                "implementation_opportunity", "closed_lost",
            ):
                company.pipeline_stage = "replied"

            self._log_activity(
                user_id=state.user_id,
                action="reply_detected",
                entity_type="company",
                entity_id=company_id,
                details=json.dumps({
                    "gmail_thread_id": state.gmail_thread_id,
                    "snippet": reply_snippet[:200],
                    "detected_at": (reply_timestamp or now).isoformat(),
                }),
            )

            try:
                self._session.commit()
            except Exception:
                self._session.rollback()
                logger.exception(
                    "Failed to commit reply detection for company_id=%s", company_id
                )
                raise

            logger.info("Reply detected for company_id=%s", company_id)

        return reply_found

    # ------------------------------------------------------------------

    def batch_check_replies(self, user_id: int, gmail_service) -> list[dict]:
        """
        Check ALL active outreach threads for *user_id* for replies.

        Only checks threads where status = "awaiting_reply" and no reply
        has been recorded yet, to minimise unnecessary API calls.

        Returns a list of dicts:
            [{"company_id": int, "company_name": str, "replied": bool}, ...]
        """
        from database.models import Company
        from outreach.models import OutreachState

        active_states = (
            self._session.query(OutreachState)
            .filter(
                OutreachState.user_id == user_id,
                OutreachState.status == "awaiting_reply",
                OutreachState.reply_detected == False,  # noqa: E712
                OutreachState.gmail_thread_id.isnot(None),
            )
            .all()
        )

        results = []
        for state in active_states:
            company = self._session.get(Company, state.company_id)
            company_name = company.name if company else f"company_id={state.company_id}"
            try:
                replied = self.check_for_reply(state.company_id, gmail_service)
            except Exception:
                logger.exception(
                    "Error checking reply for company_id=%s", state.company_id
                )
                replied = False

            results.append({
                "company_id": state.company_id,
                "company_name": company_name,
                "replied": replied,
            })

        logger.info(
            "batch_check_replies: checked %d threads, %d replies found",
            len(results),
            sum(1 for r in results if r["replied"]),
        )
        return results

    # ------------------------------------------------------------------

    def get_followups_due(self, user_id: int) -> list[dict]:
        """
        Return all outreach records where a follow-up email is now due and
        has not yet been sent.

        Filters applied:
          - status = "awaiting_reply"
          - reply_detected = False
          - next_followup_due <= today (UTC)
          - current_followup_stage < MAX_FOLLOWUPS
          - is_suppressed = False
          - contact.do_not_contact = False

        Each returned dict contains enough information for the UI to
        display the full context and present an approval button.

        NO email is sent by this method.
        """
        from database.models import Company, Contact
        from outreach.models import OutreachState

        today = datetime.utcnow()

        states = (
            self._session.query(OutreachState)
            .filter(
                OutreachState.user_id == user_id,
                OutreachState.status == "awaiting_reply",
                OutreachState.reply_detected == False,  # noqa: E712
                OutreachState.next_followup_due <= today,
                OutreachState.current_followup_stage < MAX_FOLLOWUPS,
                OutreachState.is_suppressed == False,  # noqa: E712
            )
            .order_by(OutreachState.next_followup_due)
            .all()
        )

        results = []
        for state in states:
            # Safety check: verify the contact has not been flagged DNC
            contact = self._session.get(Contact, state.contact_id)
            if contact is None or contact.do_not_contact:
                continue

            company = self._session.get(Company, state.company_id)
            if company is None:
                continue

            cadence = self._get_cadence_for_state(state)
            next_stage = state.current_followup_stage + 1
            cadence_entry = next((c for c in cadence if c["stage"] == next_stage), None)
            stage_label = cadence_entry["label"] if cadence_entry else f"Follow-Up {next_stage}"

            days_overdue = (today - state.next_followup_due).days if state.next_followup_due else 0

            results.append({
                "outreach_state_id": state.id,
                "company_id": company.id,
                "company_name": company.name,
                "company_website": company.website,
                "company_industry": company.industry,
                "contact_id": contact.id,
                "contact_name": f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
                "contact_email": contact.email,
                "contact_title": contact.title,
                "gmail_thread_id": state.gmail_thread_id,
                "current_stage": state.current_followup_stage,
                "next_stage": next_stage,
                "stage_label": stage_label,
                "next_followup_due": state.next_followup_due,
                "days_overdue": max(days_overdue, 0),
                "last_sent_at": state.last_sent_at,
                "first_sent_at": state.first_sent_at,
            })

        logger.info(
            "get_followups_due: found %d follow-ups due for user_id=%s", len(results), user_id
        )
        return results

    # ------------------------------------------------------------------

    def get_pipeline_counts(self, user_id: int) -> dict:
        """
        Return counts of outreach records in each pipeline bucket.

        Returns:
            {
                "followup_due": int,   # due and not yet sent
                "awaiting_reply": int, # sent, waiting, not yet due
                "replied": int,
                "suppressed": int,
                "closed": int,
            }
        """
        from outreach.models import OutreachState

        today = datetime.utcnow()

        rows = (
            self._session.query(OutreachState.status, func.count(OutreachState.id))
            .filter(OutreachState.user_id == user_id)
            .group_by(OutreachState.status)
            .all()
        )
        raw_counts = {status: count for status, count in rows}

        # "followup_due" is a subset of "awaiting_reply" where next_followup_due has passed
        followup_due_count = (
            self._session.query(func.count(OutreachState.id))
            .filter(
                OutreachState.user_id == user_id,
                OutreachState.status == "awaiting_reply",
                OutreachState.reply_detected == False,  # noqa: E712
                OutreachState.next_followup_due <= today,
                OutreachState.current_followup_stage < MAX_FOLLOWUPS,
                OutreachState.is_suppressed == False,  # noqa: E712
            )
            .scalar()
            or 0
        )

        return {
            "followup_due": followup_due_count,
            "awaiting_reply": raw_counts.get("awaiting_reply", 0),
            "replied": raw_counts.get("replied", 0),
            "suppressed": raw_counts.get("suppressed", 0),
            "closed": raw_counts.get("closed", 0),
        }

    # ------------------------------------------------------------------

    def mark_closed(self, company_id: int, reason: str = "closed_lost") -> None:
        """
        Mark an outreach sequence as closed (no further follow-up).

        Clears the next_followup_due date so the record no longer surfaces
        in the follow-up queue.
        """
        from outreach.models import OutreachState

        state = (
            self._session.query(OutreachState)
            .filter_by(company_id=company_id)
            .first()
        )
        if state is None:
            logger.warning("mark_closed: no OutreachState found for company_id=%s", company_id)
            return

        state.status = "closed"
        state.closed_reason = reason
        state.next_followup_due = None
        state.updated_at = datetime.utcnow()

        self._log_activity(
            user_id=state.user_id,
            action="outreach_closed",
            entity_type="company",
            entity_id=company_id,
            details=json.dumps({"reason": reason}),
        )

        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            logger.exception("Failed to commit mark_closed for company_id=%s", company_id)
            raise

        logger.info("Outreach closed for company_id=%s, reason=%s", company_id, reason)

    # ------------------------------------------------------------------

    def mark_do_not_contact(
        self,
        session: Session,
        company_id: int,
        contact_id: int,
        reason: str,
    ) -> None:
        """
        Flag a contact as do-not-contact and add them to the suppression list.

        Steps performed:
          1. Sets Contact.do_not_contact = True
          2. Creates or updates a SuppressionEntry for the contact's email
          3. Sets OutreachState.is_suppressed = True, status = "suppressed"
          4. Logs the action

        NO email is sent.
        """
        from database.models import Contact, SuppressionEntry
        from outreach.models import OutreachState

        contact = session.get(Contact, contact_id)
        if contact is None:
            logger.warning("mark_do_not_contact: contact_id=%s not found", contact_id)
            return

        # 1. Flag the contact
        contact.do_not_contact = True
        contact.suppression_reason = reason
        contact.updated_at = datetime.utcnow()

        # 2. Add to suppression list (upsert pattern)
        if contact.email:
            existing = (
                session.query(SuppressionEntry)
                .filter_by(email=contact.email.lower())
                .first()
            )
            if existing is None:
                suppression = SuppressionEntry(
                    email=contact.email.lower(),
                    company_name=None,  # filled in below
                    reason=reason,
                )
                session.add(suppression)

                # Attach company name if available
                from database.models import Company
                company = session.get(Company, company_id)
                if company:
                    suppression.company_name = company.name
            else:
                existing.reason = reason

        # 3. Update outreach state
        state = (
            session.query(OutreachState)
            .filter_by(company_id=company_id, contact_id=contact_id)
            .first()
        )
        if state is not None:
            state.is_suppressed = True
            state.suppression_reason = reason
            state.status = "suppressed"
            state.next_followup_due = None
            state.updated_at = datetime.utcnow()

            # 4. Log
            self._log_activity(
                user_id=state.user_id,
                action="contact_suppressed",
                entity_type="contact",
                entity_id=contact_id,
                details=json.dumps({"reason": reason, "company_id": company_id}),
            )

        try:
            session.commit()
        except Exception:
            session.rollback()
            logger.exception(
                "Failed to commit mark_do_not_contact for contact_id=%s", contact_id
            )
            raise

        logger.info(
            "Contact id=%s marked do-not-contact, reason=%s", contact_id, reason
        )

    # ------------------------------------------------------------------

    def can_send(
        self,
        session: Session,
        company_id: int,
        contact_id: int,
        user_id: int,
    ) -> tuple[bool, str]:
        """
        Evaluate ALL safety gates before allowing a send action.

        Returns (True, "Clear to send") if every gate passes.
        Returns (False, "<reason>") if any gate blocks the send.

        Gates checked in order:
          1. Contact.is_suppressed (OutreachState)
          2. Contact.do_not_contact
          3. Reply already detected
          4. Daily send cap reached
          5. Email in SuppressionEntry table
        """
        from database.models import Contact, SentEmail, SuppressionEntry, User
        from outreach.models import OutreachState

        # --- Gate 1: OutreachState suppression flag ------------------
        state = (
            session.query(OutreachState)
            .filter_by(company_id=company_id, contact_id=contact_id, user_id=user_id)
            .first()
        )
        if state is not None and state.is_suppressed:
            reason = state.suppression_reason or "suppressed"
            return False, f"Contact is suppressed: {reason}"

        # --- Gate 2: Contact DNC flag --------------------------------
        contact = session.get(Contact, contact_id)
        if contact is None:
            return False, "Contact record not found"
        if contact.do_not_contact:
            return False, "Contact marked do not contact"

        # --- Gate 3: Reply already received --------------------------
        if state is not None and state.reply_detected:
            return False, "Reply already received — no further follow-up needed"

        # --- Gate 4: Daily send cap ----------------------------------
        user = session.get(User, user_id)
        if user is None:
            return False, "User record not found"

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        sends_today = (
            session.query(func.count(SentEmail.id))
            .filter(
                SentEmail.user_id == user_id,
                SentEmail.sent_at >= today_start,
            )
            .scalar()
            or 0
        )
        daily_cap = user.daily_send_cap or 20
        if sends_today >= daily_cap:
            return False, f"Daily send limit reached ({sends_today}/{daily_cap})"

        # --- Gate 5: Suppression list --------------------------------
        if contact.email:
            suppressed = (
                session.query(SuppressionEntry)
                .filter_by(email=contact.email.lower())
                .first()
            )
            if suppressed is not None:
                return False, f"Email is on suppression list (reason: {suppressed.reason})"

        return True, "Clear to send"

    # ------------------------------------------------------------------

    def get_outreach_timeline(self, company_id: int) -> list[dict]:
        """
        Build a chronological timeline of all outreach events for a company.

        Pulls from three sources:
          - SentEmail rows (outbound sends)
          - Activity rows with action in (email_sent, reply_detected,
            outreach_closed, contact_suppressed)
          - OutreachState for current status summary

        Returns a list of event dicts sorted oldest-first:
            [
                {
                    "timestamp": datetime,
                    "event_type": str,   # "send" | "reply" | "status_change" | "note"
                    "stage": int | None,
                    "subject": str | None,
                    "snippet": str | None,
                    "details": dict,
                },
                ...
            ]
        """
        from database.models import Activity, Draft, SentEmail
        from outreach.models import OutreachState

        timeline: list[dict] = []

        # --- Sent emails --------------------------------------------
        sent_emails = (
            self._session.query(SentEmail)
            .filter_by(company_id=company_id)
            .order_by(SentEmail.sent_at)
            .all()
        )
        for se in sent_emails:
            # Try to get the draft subject
            subject = se.subject
            timeline.append({
                "timestamp": se.sent_at,
                "event_type": "send",
                "stage": None,  # enriched below from Activity if available
                "subject": subject,
                "snippet": None,
                "details": {
                    "sent_email_id": se.id,
                    "recipient_email": se.recipient_email,
                    "gmail_message_id": se.gmail_message_id,
                    "gmail_thread_id": se.gmail_thread_id,
                    "status": se.status,
                },
            })
            # If a reply was recorded on this SentEmail, add a reply event
            if se.replied_at:
                timeline.append({
                    "timestamp": se.replied_at,
                    "event_type": "reply",
                    "stage": None,
                    "subject": None,
                    "snippet": None,
                    "details": {
                        "sent_email_id": se.id,
                        "gmail_thread_id": se.gmail_thread_id,
                    },
                })

        # --- Relevant Activity rows ---------------------------------
        relevant_actions = {
            "email_sent", "reply_detected", "outreach_closed", "contact_suppressed",
        }
        activities = (
            self._session.query(Activity)
            .filter(
                Activity.entity_type == "company",
                Activity.entity_id == company_id,
                Activity.action.in_(relevant_actions),
            )
            .order_by(Activity.created_at)
            .all()
        )
        for act in activities:
            extra: dict = {}
            if act.details:
                try:
                    extra = json.loads(act.details)
                except (json.JSONDecodeError, TypeError):
                    extra = {"raw": act.details}

            event_type_map = {
                "email_sent": "send",
                "reply_detected": "reply",
                "outreach_closed": "status_change",
                "contact_suppressed": "status_change",
            }

            timeline.append({
                "timestamp": act.created_at,
                "event_type": event_type_map.get(act.action, "note"),
                "stage": extra.get("stage"),
                "subject": None,
                "snippet": extra.get("snippet"),
                "details": extra,
            })

        # --- OutreachState summary event ----------------------------
        state = (
            self._session.query(OutreachState)
            .filter_by(company_id=company_id)
            .first()
        )
        if state is not None:
            timeline.append({
                "timestamp": state.updated_at,
                "event_type": "status_change",
                "stage": state.current_followup_stage,
                "subject": None,
                "snippet": None,
                "details": {
                    "status": state.status,
                    "next_followup_due": (
                        state.next_followup_due.isoformat()
                        if state.next_followup_due else None
                    ),
                    "reply_detected": state.reply_detected,
                },
            })

        # Deduplicate and sort
        # Use (timestamp, event_type, str(details)) as a dedup key
        seen: set[tuple] = set()
        unique_timeline = []
        for event in timeline:
            key = (event["timestamp"], event["event_type"], json.dumps(event["details"], default=str))
            if key not in seen:
                seen.add(key)
                unique_timeline.append(event)

        unique_timeline.sort(key=lambda e: e["timestamp"] or datetime.min)
        return unique_timeline

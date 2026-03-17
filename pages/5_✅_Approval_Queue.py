"""
Approval Queue — Manual review, approval, and single-send page.
Compliance-focused: every send requires explicit human approval.
No st.set_page_config() here; it lives in app.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import streamlit as st

from database.db import get_session, init_db
from database.models import Activity, Company, Contact, Draft, SentEmail
from utils.helpers import compliance_warning

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user(session):
    user_id = st.session_state.get("user_id")
    if not user_id:
        return None
    from database.models import User
    return session.query(User).filter_by(id=user_id).first()


def _daily_send_status(session, user_id: int) -> tuple[int, int]:
    """Returns (sent_today, daily_cap)."""
    from auth.gmail import check_daily_sends
    try:
        sent, remaining = check_daily_sends(session, user_id)
        from database.models import User
        user = session.query(User).filter_by(id=user_id).first()
        cap = user.daily_send_cap if user else 20
        return sent, cap
    except Exception:
        return 0, 20


def _suppression_check(session, email: str) -> tuple[bool, str]:
    """Returns (is_suppressed, reason)."""
    if not email:
        return False, ""
    from auth.gmail import is_suppressed
    from database.models import SuppressionEntry
    try:
        suppressed = is_suppressed(session, email)
        if suppressed:
            entry = session.query(SuppressionEntry).filter(
                SentEmail.recipient_email.ilike(email)
            ).first()
            reason = entry.reason if entry else "suppressed"
            return True, reason
        return False, ""
    except Exception:
        return False, ""


def _get_gmail_service(user):
    """Try to build a Gmail service from the user's refresh token."""
    if not user or not user.gmail_connected or not user.gmail_refresh_token:
        return None
    try:
        from auth.gmail import get_gmail_service
        return get_gmail_service(user.gmail_refresh_token)
    except Exception:
        return None


def _do_send(session, draft: Draft, user, service) -> tuple[bool, str]:
    """
    Execute the full send flow for one draft:
    1. can_send() gate check
    2. Create Gmail draft
    3. Send it
    4. Record SentEmail
    5. Update OutreachState
    6. Log Activity
    Returns (success, message).
    """
    from outreach.followup_engine import OutreachTracker
    from auth.gmail import create_gmail_draft, send_single_email, is_suppressed

    contact = draft.contact
    if not contact or not contact.email:
        return False, "No contact email on this draft."

    # Safety: suppression check
    if is_suppressed(session, contact.email):
        return False, f"{contact.email} is on the suppression list."

    # can_send() gate
    tracker = OutreachTracker(session)
    ok, reason = tracker.can_send(session, draft.company_id, draft.contact_id, user.id)
    if not ok:
        return False, reason

    # Gmail send
    if service is None:
        return False, "Gmail not connected. Connect Gmail in Settings to send."

    try:
        gmail_draft_id = create_gmail_draft(
            service,
            to_email=contact.email,
            subject=draft.subject or "(no subject)",
            body=draft.body,
        )
        send_result = send_single_email(service, gmail_draft_id)
        message_id = send_result.get("message_id", "")
        thread_id = send_result.get("thread_id", "")
    except Exception as e:
        return False, f"Gmail API error: {e}"

    # Record in DB
    try:
        sent_email = SentEmail(
            draft_id=draft.id,
            company_id=draft.company_id,
            contact_id=draft.contact_id,
            user_id=user.id,
            subject=draft.subject or "(no subject)",
            body=draft.body,
            recipient_email=contact.email,
            gmail_message_id=message_id,
            gmail_thread_id=thread_id,
            sent_at=datetime.utcnow(),
            status="sent",
        )
        session.add(sent_email)

        draft.status = "sent"
        draft.gmail_draft_id = gmail_draft_id

        tracker.record_send(
            company_id=draft.company_id,
            contact_id=draft.contact_id,
            user_id=user.id,
            draft_id=draft.id,
            gmail_message_id=message_id,
            gmail_thread_id=thread_id,
        )

        activity = Activity(
            user_id=user.id,
            action="email_sent",
            entity_type="company",
            entity_id=draft.company_id,
            details=f"Sent draft id={draft.id} to {contact.email}",
        )
        session.add(activity)
        session.commit()
        return True, f"Sent to {contact.email}."
    except Exception as e:
        session.rollback()
        return False, f"Database error after send: {e}"


def _render_draft_card(session, draft: Draft, user, service, key_prefix: str = ""):
    """Render a single draft card with approve/send/delete actions."""
    company = draft.company
    contact = draft.contact

    company_name = company.name if company else f"Company #{draft.company_id}"
    contact_name = ""
    contact_email = ""
    if contact:
        contact_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
        contact_email = contact.email or ""

    # Suppression check
    supp, supp_reason = _suppression_check(session, contact_email)

    status_colors = {"draft": "blue", "approved": "green", "sent": "gray", "failed": "red"}
    status_color = status_colors.get(draft.status, "blue")

    header = (
        f"**{company_name}** | {draft.draft_type.replace('_', ' ').title()} | "
        f":{status_color}[{draft.status.upper()}]"
    )
    if contact_name:
        header += f" | {contact_name}"
    if contact_email:
        header += f" <{contact_email}>"

    with st.expander(header, expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption(f"Type: {draft.draft_type.replace('_', ' ').title()}")
            st.caption(f"Created: {draft.created_at.strftime('%b %d, %Y %H:%M')}")
            if draft.approved_at:
                st.caption(f"Approved: {draft.approved_at.strftime('%b %d, %Y %H:%M')}")
        with col_b:
            if supp:
                st.error(f"SUPPRESSED — {supp_reason}. Do not send.")
            elif contact and contact.do_not_contact:
                st.error("Contact marked Do Not Contact.")
            else:
                st.success("Suppression check: Clear")

        st.divider()

        # Editable fields
        if draft.subject is not None:
            new_subject = st.text_input(
                "Subject", value=draft.subject, key=f"{key_prefix}_subj_{draft.id}"
            )
        else:
            new_subject = None

        new_body = st.text_area(
            "Body", value=draft.body, height=250, key=f"{key_prefix}_body_{draft.id}"
        )

        # Save edits button (only shows when changes detected)
        if new_body != draft.body or (new_subject is not None and new_subject != draft.subject):
            if st.button("Save Edits", key=f"{key_prefix}_save_{draft.id}"):
                try:
                    draft.body = new_body
                    if new_subject is not None:
                        draft.subject = new_subject
                    draft.updated_at = datetime.utcnow()
                    session.commit()
                    st.success("Edits saved.")
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Error: {e}")

        st.divider()

        col1, col2, col3 = st.columns(3)

        # Approve
        with col1:
            if draft.status == "draft":
                if st.button("Approve", key=f"{key_prefix}_approve_{draft.id}", use_container_width=True):
                    try:
                        draft.status = "approved"
                        draft.approved_at = datetime.utcnow()
                        session.commit()
                        st.success("Draft approved.")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error: {e}")
            else:
                st.caption(f"Status: {draft.status}")

        # Send
        with col2:
            send_enabled = draft.status == "approved" and not supp and not (contact and contact.do_not_contact)
            if st.button(
                "Send",
                key=f"{key_prefix}_send_{draft.id}",
                disabled=not send_enabled,
                type="primary" if send_enabled else "secondary",
                use_container_width=True,
            ):
                with st.spinner("Sending..."):
                    success, msg = _do_send(session, draft, user, service)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        # Delete
        with col3:
            if st.button("Delete Draft", key=f"{key_prefix}_del_{draft.id}", use_container_width=True):
                try:
                    session.delete(draft)
                    session.commit()
                    st.success("Draft deleted.")
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Error: {e}")

        if draft.status == "approved" and send_enabled:
            st.caption("Ready to send. Gmail must be connected in Settings.")
        elif draft.status == "draft":
            st.caption("Approve this draft before sending.")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Approval Queue")
st.caption("Every email must be manually approved and sent one at a time. No automated sending.")

# Compliance banner
st.error(compliance_warning(), icon=None)

init_db()
session = get_session()

try:
    user = _get_user(session)
    user_id = user.id if user else None

    # -----------------------------------------------------------------------
    # Daily send status
    # -----------------------------------------------------------------------
    if user_id:
        sent_today, daily_cap = _daily_send_status(session, user_id)
        pct = sent_today / daily_cap if daily_cap > 0 else 0
        st.metric("Daily Sends", f"{sent_today} / {daily_cap}")
        st.progress(min(pct, 1.0), text=f"{sent_today} sent today out of {daily_cap} allowed")
    else:
        st.info("No user session detected. Some features require authentication.")
        sent_today, daily_cap = 0, 20

    # Gmail service
    service = _get_gmail_service(user) if user else None
    if not service:
        st.warning("Gmail not connected — you can approve drafts but cannot send until Gmail is connected in Settings.")

    st.divider()

    tab1, tab2 = st.tabs(["Pending Approval", "Follow-Ups Due"])

    # -----------------------------------------------------------------------
    # Tab 1: Pending Approval
    # -----------------------------------------------------------------------
    with tab1:
        pending_drafts = (
            session.query(Draft)
            .filter(Draft.status.in_(["draft", "approved"]))
            .order_by(Draft.created_at.desc())
            .all()
        )

        if not pending_drafts:
            st.info("No drafts pending approval. Generate drafts in the Messaging Studio.")
        else:
            st.caption(f"{len(pending_drafts)} draft(s) awaiting review.")
            for d in pending_drafts:
                _render_draft_card(session, d, user, service, key_prefix="pend")

    # -----------------------------------------------------------------------
    # Tab 2: Follow-Ups Due
    # -----------------------------------------------------------------------
    with tab2:
        if not user_id:
            st.info("User session required to view follow-ups.")
        else:
            from outreach.followup_engine import OutreachTracker
            from messaging.drafts import generate_followup, generate_draft_fallback

            tracker = OutreachTracker(session)

            try:
                followups_due = tracker.get_followups_due(user_id)
            except Exception as e:
                st.error(f"Error loading follow-ups: {e}")
                followups_due = []

            if not followups_due:
                st.info("No follow-ups are currently due.")
            else:
                st.caption(f"{len(followups_due)} follow-up(s) due.")

                for fu in followups_due:
                    with st.expander(
                        f"**{fu['company_name']}** | {fu['stage_label']} | "
                        f"{fu['days_overdue']} days overdue | {fu.get('contact_name', '')}",
                        expanded=False,
                    ):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.caption(f"Contact: {fu.get('contact_name', 'N/A')}")
                            st.caption(f"Email: {fu.get('contact_email', 'N/A')}")
                        with col2:
                            last_sent = fu.get("last_sent_at")
                            st.caption(f"Last sent: {last_sent.strftime('%b %d, %Y') if last_sent else 'Unknown'}")
                            st.caption(f"Follow-up stage: {fu['next_stage']}")
                        with col3:
                            due_date = fu.get("next_followup_due")
                            st.caption(f"Due: {due_date.strftime('%b %d, %Y') if due_date else 'Now'}")
                            st.caption(f"Days overdue: {fu['days_overdue']}")

                        api_key = st.session_state.get("anthropic_api_key", "")

                        if st.button("Generate Follow-Up Draft", key=f"fu_gen_{fu['outreach_state_id']}"):
                            with st.spinner("Generating..."):
                                company = session.query(Company).filter_by(id=fu["company_id"]).first()
                                contact = session.query(Contact).filter_by(id=fu["contact_id"]).first()
                                if company and contact:
                                    import json as _json
                                    def _parse(v):
                                        if v is None: return []
                                        if isinstance(v, list): return v
                                        try: return _json.loads(v)
                                        except: return []

                                    c_dict = {
                                        "name": company.name,
                                        "industry": company.industry or "",
                                        "description": company.description or "",
                                        "pain_points": _parse(company.pain_points),
                                        "ai_opportunities": _parse(company.ai_opportunities),
                                    }
                                    ct_dict = {
                                        "first_name": contact.first_name or "",
                                        "last_name": contact.last_name or "",
                                        "title": contact.title or "",
                                        "email": contact.email or "",
                                    }
                                    try:
                                        if api_key:
                                            result = generate_followup(c_dict, ct_dict, api_key, fu["next_stage"])
                                        else:
                                            result = generate_draft_fallback(c_dict, ct_dict, "email_followup")
                                        st.session_state[f"fu_draft_{fu['outreach_state_id']}"] = result
                                    except Exception as e:
                                        st.error(f"Generation error: {e}")

                        draft_result = st.session_state.get(f"fu_draft_{fu['outreach_state_id']}")
                        if draft_result:
                            subject_val = draft_result.get("subject", "")
                            body_val = draft_result.get("body", "")
                            edited_subject = st.text_input("Subject", value=subject_val, key=f"fu_subj_{fu['outreach_state_id']}")
                            edited_body = st.text_area("Body", value=body_val, height=200, key=f"fu_body_{fu['outreach_state_id']}")

                            if st.button("Save as Draft", key=f"fu_save_{fu['outreach_state_id']}"):
                                new_draft = Draft(
                                    company_id=fu["company_id"],
                                    contact_id=fu["contact_id"],
                                    user_id=user_id,
                                    draft_type="email_followup",
                                    subject=edited_subject,
                                    body=edited_body,
                                    tone="practical",
                                    status="draft",
                                )
                                try:
                                    session.add(new_draft)
                                    session.commit()
                                    st.success("Draft saved. Find it in Pending Approval tab.")
                                    st.session_state.pop(f"fu_draft_{fu['outreach_state_id']}", None)
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"Error: {e}")

finally:
    session.close()

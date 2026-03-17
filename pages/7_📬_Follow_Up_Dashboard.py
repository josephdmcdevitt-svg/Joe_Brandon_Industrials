"""
Follow-Up Dashboard — Full follow-up management view.
No st.set_page_config() here; it lives in app.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

import streamlit as st

from database.db import get_session, init_db
from database.models import Company, Contact, SentEmail, SuppressionEntry
from outreach.followup_engine import OutreachTracker, DEFAULT_CADENCE
from outreach.models import OutreachState
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


def _get_gmail_service(user):
    if not user or not user.gmail_connected or not user.gmail_refresh_token:
        return None
    try:
        from auth.gmail import get_gmail_service
        return get_gmail_service(user.gmail_refresh_token)
    except Exception:
        return None


def _replied_this_week(session) -> list:
    """OutreachState rows where status='replied' and reply_detected_at in last 7 days."""
    since = datetime.utcnow() - timedelta(days=7)
    return (
        session.query(OutreachState)
        .filter(
            OutreachState.status == "replied",
            OutreachState.reply_detected_at >= since,
        )
        .order_by(OutreachState.reply_detected_at.desc())
        .all()
    )


def _awaiting_reply(session, user_id: int) -> list:
    """OutreachState rows awaiting reply but not yet due for follow-up."""
    today = datetime.utcnow()
    return (
        session.query(OutreachState)
        .filter(
            OutreachState.user_id == user_id,
            OutreachState.status == "awaiting_reply",
            OutreachState.reply_detected == False,  # noqa: E712
            (
                (OutreachState.next_followup_due == None) |
                (OutreachState.next_followup_due > today)
            ),
        )
        .order_by(OutreachState.last_sent_at.desc())
        .all()
    )


def _suppressed_states(session) -> list:
    return (
        session.query(OutreachState)
        .filter(OutreachState.status == "suppressed")
        .order_by(OutreachState.updated_at.desc())
        .all()
    )


def _closed_states(session) -> list:
    return (
        session.query(OutreachState)
        .filter(OutreachState.status == "closed")
        .order_by(OutreachState.updated_at.desc())
        .all()
    )


def _replied_states(session) -> list:
    return (
        session.query(OutreachState)
        .filter(OutreachState.status == "replied")
        .order_by(OutreachState.reply_detected_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Follow-Up Dashboard")
st.caption("Monitor the full outreach cadence and manage follow-up actions.")

init_db()
session = get_session()

try:
    user = _get_user(session)
    user_id = user.id if user else None
    service = _get_gmail_service(user) if user else None

    if not user_id:
        st.info("User session not detected. Authentication required for full functionality.")

    # -----------------------------------------------------------------------
    # Top metrics
    # -----------------------------------------------------------------------
    tracker = OutreachTracker(session) if user_id else None
    pipeline_counts = tracker.get_pipeline_counts(user_id) if tracker else {}

    followups_due_count = pipeline_counts.get("followup_due", 0)
    awaiting_reply_count = pipeline_counts.get("awaiting_reply", 0)
    replied_week_count = len(_replied_this_week(session))
    replied_total = pipeline_counts.get("replied", 0)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Follow-Ups Due", followups_due_count, delta="action needed" if followups_due_count > 0 else None, delta_color="inverse")
    with m2:
        st.metric("Awaiting Reply", awaiting_reply_count)
    with m3:
        st.metric("Replied This Week", replied_week_count)
    with m4:
        total_active = awaiting_reply_count + replied_total + pipeline_counts.get("suppressed", 0)
        st.metric("Total Active Sequences", total_active)

    # -----------------------------------------------------------------------
    # Cadence settings
    # -----------------------------------------------------------------------
    with st.expander("Cadence Settings", expanded=False):
        st.caption("These settings configure the default follow-up delays. Changes apply to new sequences only.")

        cadence = st.session_state.get("custom_cadence", DEFAULT_CADENCE)

        updated_cadence = []
        col1, col2, col3 = st.columns(3)
        with col1:
            fu1 = st.number_input(
                "Follow-Up 1 (business days after initial)",
                min_value=1, max_value=30,
                value=cadence[0]["delay_business_days"] if len(cadence) > 0 else 3,
                key="cadence_fu1",
            )
            updated_cadence.append({"stage": 1, "delay_business_days": int(fu1), "label": f"Follow-Up 1 ({fu1} business days)"})

        with col2:
            fu2 = st.number_input(
                "Follow-Up 2 (business days after FU1)",
                min_value=1, max_value=60,
                value=cadence[1]["delay_business_days"] if len(cadence) > 1 else 7,
                key="cadence_fu2",
            )
            updated_cadence.append({"stage": 2, "delay_business_days": int(fu2), "label": f"Follow-Up 2 ({fu2} business days)"})

        with col3:
            fu3 = st.number_input(
                "Follow-Up 3 (business days after FU2)",
                min_value=1, max_value=90,
                value=cadence[2]["delay_business_days"] if len(cadence) > 2 else 14,
                key="cadence_fu3",
            )
            updated_cadence.append({"stage": 3, "delay_business_days": int(fu3), "label": f"Follow-Up 3 ({fu3} business days)"})

        if st.button("Save Cadence Settings"):
            st.session_state["custom_cadence"] = updated_cadence
            st.success("Cadence settings saved for this session.")

    st.divider()

    # -----------------------------------------------------------------------
    # Tabs
    # -----------------------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Follow-Up Due",
        "Awaiting Reply",
        "Replied",
        "Suppressed",
        "Closed",
    ])

    # -----------------------------------------------------------------------
    # Tab 1: Follow-Up Due
    # -----------------------------------------------------------------------
    with tab1:
        st.warning(compliance_warning(), icon=None)

        followups_due = []
        if tracker:
            try:
                followups_due = tracker.get_followups_due(user_id)
            except Exception as e:
                st.error(f"Error loading follow-ups: {e}")

        if not followups_due:
            st.success("No follow-ups are currently due.")
        else:
            api_key = st.session_state.get("anthropic_api_key", "")

            for fu in followups_due:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])

                    with col1:
                        st.markdown(f"**{fu['company_name']}**")
                        st.caption(f"{fu.get('contact_name', 'No contact')} | {fu.get('contact_email', 'No email')}")
                        st.caption(f"Industry: {fu.get('company_industry', 'N/A')}")

                    with col2:
                        last_sent = fu.get("last_sent_at")
                        st.caption(f"Last sent: {last_sent.strftime('%b %d, %Y') if last_sent else 'Unknown'}")
                        due_date = fu.get("next_followup_due")
                        st.caption(f"Due: {due_date.strftime('%b %d, %Y') if due_date else 'Now'}")

                    with col3:
                        st.caption(f"Stage: {fu['stage_label']}")
                        overdue_days = fu.get("days_overdue", 0)
                        if overdue_days > 0:
                            st.caption(f"Overdue by {overdue_days} days")
                        else:
                            st.caption("Due today")

                    col_gen, col_skip, col_close = st.columns(3)

                    with col_gen:
                        if st.button("Generate Draft", key=f"fu_gen_{fu['outreach_state_id']}"):
                            with st.spinner("Generating..."):
                                import json as _json
                                company = session.query(Company).filter_by(id=fu["company_id"]).first()
                                contact = session.query(Contact).filter_by(id=fu["contact_id"]).first()
                                if company and contact:
                                    def _p(v):
                                        if v is None: return []
                                        if isinstance(v, list): return v
                                        try: return _json.loads(v)
                                        except: return []
                                    c_dict = {
                                        "name": company.name,
                                        "industry": company.industry or "",
                                        "description": company.description or "",
                                        "pain_points": _p(company.pain_points),
                                        "ai_opportunities": _p(company.ai_opportunities),
                                    }
                                    ct_dict = {
                                        "first_name": contact.first_name or "",
                                        "last_name": contact.last_name or "",
                                        "title": contact.title or "",
                                        "email": contact.email or "",
                                    }
                                    from messaging.drafts import generate_followup, generate_draft_fallback
                                    try:
                                        if api_key:
                                            result = generate_followup(c_dict, ct_dict, api_key, fu["next_stage"])
                                        else:
                                            result = generate_draft_fallback(c_dict, ct_dict, "email_followup")
                                        st.session_state[f"fudue_draft_{fu['outreach_state_id']}"] = result
                                    except Exception as e:
                                        st.error(f"Generation error: {e}")

                    with col_skip:
                        if st.button("Skip", key=f"fu_skip_{fu['outreach_state_id']}"):
                            # Push next_followup_due forward 3 more business days
                            state = session.query(OutreachState).filter_by(id=fu["outreach_state_id"]).first()
                            if state:
                                from outreach.followup_engine import add_business_days
                                state.next_followup_due = add_business_days(datetime.utcnow(), 3)
                                try:
                                    session.commit()
                                    st.success("Follow-up pushed forward 3 business days.")
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"Error: {e}")

                    with col_close:
                        if st.button("Mark Closed", key=f"fu_close_{fu['outreach_state_id']}"):
                            try:
                                tracker.mark_closed(fu["company_id"], reason="closed_manually")
                                st.success("Marked closed.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

                    # Show generated draft if available
                    draft_result = st.session_state.get(f"fudue_draft_{fu['outreach_state_id']}")
                    if draft_result:
                        st.divider()
                        from database.models import Draft
                        edited_subject = st.text_input(
                            "Subject", value=draft_result.get("subject", ""),
                            key=f"fudue_subj_{fu['outreach_state_id']}"
                        )
                        edited_body = st.text_area(
                            "Body", value=draft_result.get("body", ""),
                            height=200, key=f"fudue_body_{fu['outreach_state_id']}"
                        )
                        if st.button("Save Draft for Approval", key=f"fudue_save_{fu['outreach_state_id']}"):
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
                                st.success("Draft saved. Go to Approval Queue to review and send.")
                                st.session_state.pop(f"fudue_draft_{fu['outreach_state_id']}", None)
                                st.rerun()
                            except Exception as e:
                                session.rollback()
                                st.error(f"Error: {e}")

    # -----------------------------------------------------------------------
    # Tab 2: Awaiting Reply
    # -----------------------------------------------------------------------
    with tab2:
        awaiting = _awaiting_reply(session, user_id) if user_id else []

        if awaiting:
            if st.button("Check for Replies (Requires Gmail)", use_container_width=True):
                if service:
                    with st.spinner("Checking Gmail threads..."):
                        try:
                            results = tracker.batch_check_replies(user_id, service)
                            replied_count = sum(1 for r in results if r["replied"])
                            st.success(f"Checked {len(results)} threads. {replied_count} new reply(ies) detected.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error checking replies: {e}")
                else:
                    st.error("Gmail must be connected in Settings to check for replies.")

        if not awaiting:
            st.info("No outreach currently awaiting reply.")
        else:
            st.caption(f"{len(awaiting)} contact(s) awaiting reply.")
            for state in awaiting:
                company = session.query(Company).filter_by(id=state.company_id).first()
                contact = session.query(Contact).filter_by(id=state.contact_id).first()

                company_name = company.name if company else f"Company #{state.company_id}"
                contact_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip() if contact else "N/A"
                contact_email = contact.email if contact else "N/A"

                now = datetime.utcnow()
                days_waiting = (now - state.last_sent_at).days if state.last_sent_at else 0
                next_due = state.next_followup_due

                with st.container(border=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**{company_name}**")
                        st.caption(f"{contact_name} | {contact_email}")
                    with col2:
                        last_sent = state.last_sent_at
                        st.caption(f"Last sent: {last_sent.strftime('%b %d, %Y') if last_sent else 'N/A'}")
                        st.caption(f"Days waiting: {days_waiting}")
                    with col3:
                        st.caption(f"Follow-up stage: {state.current_followup_stage}")
                        if next_due:
                            st.caption(f"Next follow-up due: {next_due.strftime('%b %d, %Y')}")
                        else:
                            st.caption("No further follow-ups scheduled")

    # -----------------------------------------------------------------------
    # Tab 3: Replied
    # -----------------------------------------------------------------------
    with tab3:
        replied_states = _replied_states(session)

        if not replied_states:
            st.info("No replies recorded yet.")
        else:
            st.caption(f"{len(replied_states)} contact(s) have replied.")
            for state in replied_states:
                company = session.query(Company).filter_by(id=state.company_id).first()
                contact = session.query(Contact).filter_by(id=state.contact_id).first()

                company_name = company.name if company else f"Company #{state.company_id}"
                contact_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip() if contact else "N/A"

                # Get last sent email for snippet
                last_sent_email = (
                    session.query(SentEmail)
                    .filter_by(company_id=state.company_id)
                    .order_by(SentEmail.sent_at.desc())
                    .first()
                )

                with st.container(border=True):
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.markdown(f"**{company_name}**")
                        st.caption(f"Contact: {contact_name}")
                        if state.reply_detected_at:
                            st.caption(f"Replied: {state.reply_detected_at.strftime('%b %d, %Y')}")
                        if last_sent_email and last_sent_email.subject:
                            st.caption(f"Thread: {last_sent_email.subject}")
                    with col2:
                        # Move to Call Scheduled
                        if company and company.pipeline_stage not in ("call_scheduled", "audit_sold", "audit_delivered"):
                            if st.button("Move to Call Scheduled", key=f"replied_call_{state.id}"):
                                company.pipeline_stage = "call_scheduled"
                                company.updated_at = datetime.utcnow()
                                try:
                                    session.commit()
                                    st.success("Moved to Call Scheduled.")
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"Error: {e}")
                        else:
                            st.caption(f"Stage: {company.pipeline_stage if company else 'N/A'}")

    # -----------------------------------------------------------------------
    # Tab 4: Suppressed
    # -----------------------------------------------------------------------
    with tab4:
        suppressed_states = _suppressed_states(session)
        suppression_entries = session.query(SuppressionEntry).order_by(SuppressionEntry.created_at.desc()).all()

        if not suppressed_states and not suppression_entries:
            st.info("No suppressed contacts.")
        else:
            if suppressed_states:
                st.subheader("Suppressed Outreach Sequences")
                for state in suppressed_states:
                    company = session.query(Company).filter_by(id=state.company_id).first()
                    contact = session.query(Contact).filter_by(id=state.contact_id).first()
                    company_name = company.name if company else f"Company #{state.company_id}"
                    contact_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip() if contact else "N/A"
                    contact_email = contact.email if contact else ""

                    with st.container(border=True):
                        st.markdown(f"**{company_name}** | {contact_name} | {contact_email}")
                        st.caption(f"Reason: {state.suppression_reason or 'Not specified'}")
                        st.caption(f"Suppressed: {state.updated_at.strftime('%b %d, %Y')}")

            if suppression_entries:
                st.subheader("Suppression List")
                for entry in suppression_entries:
                    with st.container(border=True):
                        st.markdown(f"**{entry.email}**")
                        if entry.company_name:
                            st.caption(f"Company: {entry.company_name}")
                        st.caption(f"Reason: {entry.reason}")
                        st.caption(f"Added: {entry.created_at.strftime('%b %d, %Y')}")

    # -----------------------------------------------------------------------
    # Tab 5: Closed
    # -----------------------------------------------------------------------
    with tab5:
        closed_states = _closed_states(session)

        if not closed_states:
            st.info("No closed outreach sequences.")
        else:
            st.caption(f"{len(closed_states)} closed sequence(s).")
            for state in closed_states:
                company = session.query(Company).filter_by(id=state.company_id).first()
                contact = session.query(Contact).filter_by(id=state.contact_id).first()
                company_name = company.name if company else f"Company #{state.company_id}"
                contact_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip() if contact else "N/A"

                with st.container(border=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**{company_name}**")
                        st.caption(f"Contact: {contact_name}")
                    with col2:
                        st.caption(f"Reason: {state.closed_reason or 'Not specified'}")
                        st.caption(f"Closed: {state.updated_at.strftime('%b %d, %Y')}")

finally:
    session.close()

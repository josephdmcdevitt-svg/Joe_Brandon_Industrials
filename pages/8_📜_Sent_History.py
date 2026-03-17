"""
Sent History — Full log of all emails sent through the system.
No st.set_page_config() here; it lives in app.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from database.db import get_session, init_db
from database.models import Company, Contact, SentEmail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_dataframe(sent_emails: list) -> pd.DataFrame:
    rows = []
    for se in sent_emails:
        company_name = se.company.name if se.company else f"Company #{se.company_id}"
        contact_name = ""
        if se.contact:
            contact_name = f"{se.contact.first_name or ''} {se.contact.last_name or ''}".strip()

        thread_link = ""
        if se.gmail_thread_id:
            thread_link = f"https://mail.google.com/mail/u/0/#inbox/{se.gmail_thread_id}"

        rows.append({
            "ID": se.id,
            "Date Sent": se.sent_at.strftime("%Y-%m-%d %H:%M") if se.sent_at else "",
            "Company": company_name,
            "Contact": contact_name,
            "Email": se.recipient_email,
            "Subject": se.subject or "",
            "Status": se.status,
            "Replied At": se.replied_at.strftime("%Y-%m-%d %H:%M") if se.replied_at else "",
            "Thread Link": thread_link,
            "_body": se.body,
            "_id": se.id,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Sent History")
st.caption("Complete log of all emails sent through this system.")

init_db()
session = get_session()

try:
    # -----------------------------------------------------------------------
    # Filters
    # -----------------------------------------------------------------------
    st.subheader("Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Date range
        default_start = datetime.utcnow() - timedelta(days=30)
        date_from = st.date_input("From Date", value=default_start.date(), key="hist_from")

    with col2:
        date_to = st.date_input("To Date", value=datetime.utcnow().date(), key="hist_to")

    with col3:
        status_filter = st.selectbox(
            "Status",
            ["All", "sent", "delivered", "replied", "bounced"],
            key="hist_status",
        )

    # Company filter
    companies = session.query(Company).order_by(Company.name).all()
    company_options = ["All Companies"] + [c.name for c in companies]
    company_filter = st.selectbox("Company", company_options, key="hist_company")

    # -----------------------------------------------------------------------
    # Query
    # -----------------------------------------------------------------------
    query = session.query(SentEmail).order_by(SentEmail.sent_at.desc())

    if date_from:
        from_dt = datetime.combine(date_from, datetime.min.time())
        query = query.filter(SentEmail.sent_at >= from_dt)

    if date_to:
        to_dt = datetime.combine(date_to, datetime.max.time())
        query = query.filter(SentEmail.sent_at <= to_dt)

    if status_filter != "All":
        query = query.filter(SentEmail.status == status_filter)

    if company_filter != "All Companies":
        company_obj = next((c for c in companies if c.name == company_filter), None)
        if company_obj:
            query = query.filter(SentEmail.company_id == company_obj.id)

    sent_emails = query.all()

    # -----------------------------------------------------------------------
    # Metrics
    # -----------------------------------------------------------------------
    total_sent = len(sent_emails)
    total_replied = sum(1 for se in sent_emails if se.status == "replied")
    total_bounced = sum(1 for se in sent_emails if se.status == "bounced")
    reply_rate = round((total_replied / total_sent * 100), 1) if total_sent > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Sent", total_sent)
    with m2:
        st.metric("Replies", total_replied)
    with m3:
        st.metric("Reply Rate", f"{reply_rate}%")
    with m4:
        st.metric("Bounced", total_bounced)

    st.divider()

    if not sent_emails:
        st.info("No sent emails match the current filters.")
    else:
        # -----------------------------------------------------------------------
        # Table display
        # -----------------------------------------------------------------------
        df = _build_dataframe(sent_emails)

        display_cols = ["Date Sent", "Company", "Contact", "Email", "Subject", "Status", "Replied At"]
        st.dataframe(
            df[display_cols],
            use_container_width=True,
            hide_index=True,
        )

        # -----------------------------------------------------------------------
        # Export to CSV
        # -----------------------------------------------------------------------
        export_df = df[["Date Sent", "Company", "Contact", "Email", "Subject", "Status", "Replied At", "Thread Link"]]
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Export to CSV",
            data=csv_bytes,
            file_name=f"sent_history_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

        # -----------------------------------------------------------------------
        # Expandable detail rows
        # -----------------------------------------------------------------------
        st.divider()
        st.subheader("Email Details")
        st.caption("Click any email to view the full body and thread information.")

        for se in sent_emails:
            company_name = se.company.name if se.company else f"Company #{se.company_id}"
            contact_name = ""
            if se.contact:
                contact_name = f"{se.contact.first_name or ''} {se.contact.last_name or ''}".strip()

            sent_date = se.sent_at.strftime("%b %d, %Y %H:%M") if se.sent_at else "Unknown"
            status_color = {"sent": "blue", "replied": "green", "bounced": "red", "delivered": "gray"}.get(se.status, "blue")

            header = (
                f"**{company_name}** | {sent_date} | "
                f":{status_color}[{se.status.upper()}]"
            )
            if contact_name:
                header += f" | {contact_name}"

            with st.expander(header, expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"To: {se.recipient_email}")
                    st.caption(f"Subject: {se.subject or '(no subject)'}")
                    st.caption(f"Sent: {sent_date}")
                with col2:
                    if se.replied_at:
                        st.caption(f"Replied: {se.replied_at.strftime('%b %d, %Y %H:%M')}")
                    if se.gmail_message_id:
                        st.caption(f"Message ID: {se.gmail_message_id}")
                    if se.gmail_thread_id:
                        thread_url = f"https://mail.google.com/mail/u/0/#inbox/{se.gmail_thread_id}"
                        st.markdown(f"[Open Thread in Gmail]({thread_url})")

                st.divider()
                st.text_area(
                    "Email Body",
                    value=se.body,
                    height=200,
                    key=f"body_view_{se.id}",
                    disabled=True,
                )

                # If Gmail connected, offer to view thread replies
                user = None
                user_id = st.session_state.get("user_id")
                if user_id:
                    from database.models import User
                    user = session.query(User).filter_by(id=user_id).first()

                if user and user.gmail_connected and user.gmail_refresh_token and se.gmail_thread_id:
                    if st.button("Load Thread Replies from Gmail", key=f"thread_load_{se.id}"):
                        try:
                            from auth.gmail import get_gmail_service, get_thread_replies
                            svc = get_gmail_service(user.gmail_refresh_token)
                            messages = get_thread_replies(svc, se.gmail_thread_id)
                            st.session_state[f"thread_msgs_{se.id}"] = messages
                        except Exception as e:
                            st.error(f"Could not load thread: {e}")

                    thread_msgs = st.session_state.get(f"thread_msgs_{se.id}")
                    if thread_msgs:
                        st.subheader("Thread Messages")
                        for i, msg in enumerate(thread_msgs):
                            with st.expander(f"Message {i+1} — From: {msg.get('from', 'Unknown')} | {msg.get('date', '')}", expanded=(i > 0)):
                                st.caption(f"Snippet: {msg.get('snippet', '')}")
                                if msg.get("body"):
                                    st.text_area(
                                        "Full Message",
                                        value=msg["body"],
                                        height=150,
                                        key=f"thread_body_{se.id}_{i}",
                                        disabled=True,
                                    )

finally:
    session.close()

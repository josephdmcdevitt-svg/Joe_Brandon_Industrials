"""
Suppression List — Manage emails that must not be contacted.
No st.set_page_config() here; it lives in app.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from database.db import get_session, init_db
from database.models import SuppressionEntry
from utils.helpers import compliance_warning

SUPPRESSION_REASONS = ["unsubscribed", "do_not_contact", "bounced", "complaint"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_suppression(session, email: str, reason: str, company_name: str, user_id) -> tuple[bool, str]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Invalid email address."

    existing = session.query(SuppressionEntry).filter_by(email=email).first()
    if existing:
        return False, f"{email} is already on the suppression list (reason: {existing.reason})."

    entry = SuppressionEntry(
        email=email,
        company_name=company_name.strip() if company_name else None,
        reason=reason,
        added_by_id=user_id,
    )
    try:
        session.add(entry)
        session.commit()
        return True, f"Added {email} to suppression list."
    except Exception as e:
        session.rollback()
        return False, f"Error: {e}"


def _remove_suppression(session, entry_id: int) -> tuple[bool, str]:
    entry = session.query(SuppressionEntry).filter_by(id=entry_id).first()
    if not entry:
        return False, "Entry not found."
    email = entry.email
    try:
        session.delete(entry)
        session.commit()
        return True, f"Removed {email} from suppression list."
    except Exception as e:
        session.rollback()
        return False, f"Error: {e}"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Suppression List")
st.caption("Emails on this list will never be contacted by this system.")

st.error(compliance_warning(), icon=None)

init_db()
session = get_session()

try:
    user_id = st.session_state.get("user_id")

    # -----------------------------------------------------------------------
    # Search / filter
    # -----------------------------------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("Search by email or company", placeholder="Type to filter...")
    with col2:
        reason_filter = st.selectbox("Filter by reason", ["All"] + SUPPRESSION_REASONS)

    # -----------------------------------------------------------------------
    # Load and filter
    # -----------------------------------------------------------------------
    query = session.query(SuppressionEntry).order_by(SuppressionEntry.created_at.desc())
    all_entries = query.all()

    filtered_entries = all_entries
    if search_term:
        term = search_term.strip().lower()
        filtered_entries = [
            e for e in filtered_entries
            if term in (e.email or "").lower() or term in (e.company_name or "").lower()
        ]
    if reason_filter != "All":
        filtered_entries = [e for e in filtered_entries if e.reason == reason_filter]

    # -----------------------------------------------------------------------
    # Metrics
    # -----------------------------------------------------------------------
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Suppressed", len(all_entries))
    with m2:
        st.metric("Showing", len(filtered_entries))
    with m3:
        unsubscribed = sum(1 for e in all_entries if e.reason == "unsubscribed")
        st.metric("Unsubscribed", unsubscribed)

    st.divider()

    # -----------------------------------------------------------------------
    # Add new suppression
    # -----------------------------------------------------------------------
    with st.expander("Add to Suppression List", expanded=False):
        col_a, col_b, col_c = st.columns([2, 1, 2])
        with col_a:
            new_email = st.text_input("Email Address", placeholder="contact@company.com", key="supp_email")
        with col_b:
            new_reason = st.selectbox("Reason", SUPPRESSION_REASONS, key="supp_reason")
        with col_c:
            new_company = st.text_input("Company Name (optional)", key="supp_company")

        if st.button("Add to Suppression List", type="primary"):
            if not new_email:
                st.error("Email address is required.")
            else:
                success, msg = _add_suppression(session, new_email, new_reason, new_company, user_id)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # -----------------------------------------------------------------------
    # Bulk import via CSV
    # -----------------------------------------------------------------------
    with st.expander("Bulk Import from CSV", expanded=False):
        st.caption("Upload a CSV with an 'email' column (and optional 'company' and 'reason' columns).")
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="supp_csv")
        bulk_reason = st.selectbox("Default reason for all imported emails", SUPPRESSION_REASONS, key="bulk_reason")

        if uploaded and st.button("Import CSV"):
            try:
                df = pd.read_csv(uploaded, dtype=str).fillna("")
                if "email" not in [c.lower() for c in df.columns]:
                    st.error("CSV must have an 'email' column.")
                else:
                    # Normalize column names
                    df.columns = [c.lower().strip() for c in df.columns]

                    added = 0
                    skipped = 0
                    errors = []

                    for _, row in df.iterrows():
                        email_val = str(row.get("email", "")).strip().lower()
                        if not email_val or "@" not in email_val:
                            skipped += 1
                            continue

                        company_val = str(row.get("company", "")).strip()
                        reason_val = str(row.get("reason", "")).strip()
                        if reason_val not in SUPPRESSION_REASONS:
                            reason_val = bulk_reason

                        existing = session.query(SuppressionEntry).filter_by(email=email_val).first()
                        if existing:
                            skipped += 1
                            continue

                        entry = SuppressionEntry(
                            email=email_val,
                            company_name=company_val or None,
                            reason=reason_val,
                            added_by_id=user_id,
                        )
                        session.add(entry)
                        added += 1

                    try:
                        session.commit()
                        st.success(f"Imported {added} emails. Skipped {skipped} (already present or invalid).")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error saving: {e}")

            except Exception as e:
                st.error(f"Could not read CSV: {e}")

    st.divider()

    # -----------------------------------------------------------------------
    # Suppression table
    # -----------------------------------------------------------------------
    if not filtered_entries:
        st.info("No suppression entries match your filters." if (search_term or reason_filter != "All") else "The suppression list is empty.")
    else:
        st.subheader(f"Suppression Entries ({len(filtered_entries)})")

        # Pending confirmation key
        if "confirm_remove" not in st.session_state:
            st.session_state["confirm_remove"] = None

        for entry in filtered_entries:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                with col1:
                    st.markdown(f"**{entry.email}**")
                    if entry.company_name:
                        st.caption(f"Company: {entry.company_name}")

                with col2:
                    reason_colors = {
                        "unsubscribed": "orange",
                        "do_not_contact": "red",
                        "bounced": "gray",
                        "complaint": "red",
                    }
                    rc = reason_colors.get(entry.reason, "gray")
                    st.markdown(f":{rc}[{entry.reason.replace('_', ' ').title()}]")

                with col3:
                    st.caption(f"Added: {entry.created_at.strftime('%b %d, %Y')}")
                    if entry.added_by:
                        st.caption(f"By: {entry.added_by.name if entry.added_by else 'System'}")

                with col4:
                    # Remove with confirmation
                    if st.session_state["confirm_remove"] == entry.id:
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Yes", key=f"confirm_yes_{entry.id}", type="primary"):
                                success, msg = _remove_suppression(session, entry.id)
                                st.session_state["confirm_remove"] = None
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with col_no:
                            if st.button("No", key=f"confirm_no_{entry.id}"):
                                st.session_state["confirm_remove"] = None
                                st.rerun()
                    else:
                        if st.button("Remove", key=f"remove_{entry.id}"):
                            st.session_state["confirm_remove"] = entry.id
                            st.rerun()

        # -----------------------------------------------------------------------
        # Export
        # -----------------------------------------------------------------------
        st.divider()
        export_rows = [
            {
                "email": e.email,
                "company": e.company_name or "",
                "reason": e.reason,
                "date_added": e.created_at.strftime("%Y-%m-%d"),
            }
            for e in filtered_entries
        ]
        export_df = pd.DataFrame(export_rows)
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Export Suppression List (CSV)",
            data=csv_bytes,
            file_name=f"suppression_list_{datetime.utcnow().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

finally:
    session.close()

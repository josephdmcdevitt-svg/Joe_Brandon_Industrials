"""
Settings & Integrations page.
No st.set_page_config() here; it lives in app.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import streamlit as st

from database.db import get_session, init_db
from database.models import Activity, Company, Contact, Draft, SentEmail, SuppressionEntry
from utils.helpers import compliance_warning, founder_credibility_block

APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user(session):
    user_id = st.session_state.get("user_id")
    if not user_id:
        return None
    from database.models import User
    return session.query(User).filter_by(id=user_id).first()


def _seed_sample_data(session, user_id) -> str:
    """Insert sample companies, contacts, and drafts for testing."""
    from database.models import Company, Contact, Draft

    sample_companies = [
        {
            "name": "Apex HVAC & Mechanical",
            "city": "Chicago",
            "state": "IL",
            "metro_area": "Chicago",
            "industry": "Construction & Trades",
            "sub_industry": "HVAC Contractor",
            "employee_count_min": 8,
            "employee_count_max": 22,
            "estimated_revenue_min": 1_500_000,
            "estimated_revenue_max": 3_000_000,
            "description": "Family-owned HVAC business, third generation, serving residential and light commercial customers in Chicagoland.",
            "pipeline_stage": "new_lead",
            "ai_fit_score": 78,
        },
        {
            "name": "Greenway Dental Group",
            "city": "Nashville",
            "state": "TN",
            "metro_area": "Nashville",
            "industry": "Healthcare Practices",
            "sub_industry": "Dental Office",
            "employee_count_min": 12,
            "employee_count_max": 30,
            "estimated_revenue_min": 2_000_000,
            "estimated_revenue_max": 5_000_000,
            "description": "Multi-dentist group practice with two locations. High patient volume, paper-heavy intake and billing.",
            "pipeline_stage": "enriched",
            "ai_fit_score": 85,
        },
        {
            "name": "Summit Marketing Partners",
            "city": "Dallas",
            "state": "TX",
            "metro_area": "Dallas",
            "industry": "Professional Services",
            "sub_industry": "Marketing Agency",
            "employee_count_min": 6,
            "employee_count_max": 18,
            "estimated_revenue_min": 800_000,
            "estimated_revenue_max": 2_000_000,
            "description": "Independent marketing agency serving mid-size B2B clients. Time tracking and invoicing done manually in spreadsheets.",
            "pipeline_stage": "contacted",
            "ai_fit_score": 72,
        },
    ]

    sample_contacts = [
        {"company_idx": 0, "first_name": "Mike", "last_name": "Torres", "title": "Owner", "email": "mike@apexhvac-sample.com", "is_decision_maker": True},
        {"company_idx": 1, "first_name": "Dr. Sarah", "last_name": "Lin", "title": "Practice Owner", "email": "sarah@greenwaydentalgroup-sample.com", "is_decision_maker": True},
        {"company_idx": 2, "first_name": "James", "last_name": "Waller", "title": "Founder & CEO", "email": "james@summitmarketing-sample.com", "is_decision_maker": True},
    ]

    created_companies = []
    for i, cd in enumerate(sample_companies):
        existing = session.query(Company).filter_by(name=cd["name"]).first()
        if existing:
            created_companies.append(existing)
            continue
        c = Company(
            name=cd["name"],
            city=cd["city"],
            state=cd["state"],
            metro_area=cd["metro_area"],
            industry=cd["industry"],
            sub_industry=cd["sub_industry"],
            employee_count_min=cd["employee_count_min"],
            employee_count_max=cd["employee_count_max"],
            estimated_revenue_min=cd["estimated_revenue_min"],
            estimated_revenue_max=cd["estimated_revenue_max"],
            description=cd["description"],
            pipeline_stage=cd["pipeline_stage"],
            ai_fit_score=cd["ai_fit_score"],
            source="sample_data",
            created_by_id=user_id,
        )
        session.add(c)
        session.flush()
        created_companies.append(c)

    for sc in sample_contacts:
        company = created_companies[sc["company_idx"]]
        existing = session.query(Contact).filter_by(
            company_id=company.id, email=sc["email"]
        ).first()
        if existing:
            continue
        ct = Contact(
            company_id=company.id,
            first_name=sc["first_name"],
            last_name=sc["last_name"],
            title=sc["title"],
            email=sc["email"],
            is_decision_maker=sc["is_decision_maker"],
            email_source="sample_data",
        )
        session.add(ct)

    session.flush()

    # Add a sample draft for the first company
    if created_companies:
        c = created_companies[0]
        contacts = [ct for ct in c.contacts]
        if contacts:
            existing_draft = session.query(Draft).filter_by(company_id=c.id, draft_type="email_initial").first()
            if not existing_draft:
                d = Draft(
                    company_id=c.id,
                    contact_id=contacts[0].id,
                    user_id=user_id,
                    draft_type="email_initial",
                    subject=f"Operational systems for {c.name}",
                    body=(
                        f"Hi {contacts[0].first_name},\n\n"
                        f"I work with owner-operated HVAC businesses to identify where operations are leaking time and money — "
                        f"things like job costing in spreadsheets, scheduling by text, and invoices without a system behind them.\n\n"
                        f"We do a 60-minute recorded session with the owner, then deliver a full workflow map, "
                        f"a prioritized list of automation opportunities, and a 30-60-90 day roadmap within 48 hours.\n\n"
                        f"Would it make sense to spend 15 minutes talking through what this would look like for {c.name}?\n\n"
                        f"Brandon Rye\n(Ex-Citigroup / FedEx Ops / Columbia MBA)"
                    ),
                    tone="practical",
                    status="draft",
                )
                session.add(d)

    try:
        session.commit()
        return f"Sample data seeded: {len(created_companies)} companies, {len(sample_contacts)} contacts."
    except Exception as e:
        session.rollback()
        return f"Error seeding data: {e}"


def _export_all_data(session) -> bytes:
    """Export all companies with their contacts to CSV."""
    from discovery.pipeline import export_companies_csv
    return export_companies_csv(session)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Settings")
st.caption("Configure your account, integrations, and system preferences.")

init_db()
session = get_session()

try:
    user = _get_user(session)
    user_id = user.id if user else None

    # -----------------------------------------------------------------------
    # Section 1: Profile
    # -----------------------------------------------------------------------
    with st.expander("Profile", expanded=True):
        if not user:
            st.info("No user session detected. Sign in to view profile settings.")
        else:
            col1, col2 = st.columns([1, 3])
            with col1:
                if user.picture_url:
                    st.image(user.picture_url, width=80)
                else:
                    st.markdown(
                        '<div style="width:80px;height:80px;border-radius:50%;background:#4A90E2;'
                        'display:flex;align-items:center;justify-content:center;'
                        'font-size:2em;color:white;">👤</div>',
                        unsafe_allow_html=True,
                    )
            with col2:
                st.markdown(f"**{user.name}**")
                st.caption(f"Email: {user.email}")
                st.caption(f"Account created: {user.created_at.strftime('%B %d, %Y')}")
                st.caption(f"Gmail connected: {'Yes' if user.gmail_connected else 'No'}")

    # -----------------------------------------------------------------------
    # Section 2: Gmail Integration
    # -----------------------------------------------------------------------
    with st.expander("Gmail Integration", expanded=False):
        if not user:
            st.info("Sign in to configure Gmail integration.")
        else:
            if user.gmail_connected:
                st.success("Gmail is connected.")
                st.caption("Your Gmail account is connected and ready to send emails.")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Test Gmail Connection"):
                        try:
                            from auth.gmail import get_gmail_service
                            svc = get_gmail_service(user.gmail_refresh_token)
                            profile = svc.users().getProfile(userId="me").execute()
                            st.success(f"Connected as: {profile.get('emailAddress', 'unknown')}")
                        except Exception as e:
                            st.error(f"Connection test failed: {e}")

                with col2:
                    if st.button("Disconnect Gmail", type="secondary"):
                        user.gmail_connected = False
                        user.gmail_refresh_token = None
                        try:
                            session.commit()
                            st.success("Gmail disconnected.")
                            st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Error: {e}")

            else:
                st.warning("Gmail is not connected.")
                st.caption(
                    "Connect your Gmail account to send emails directly from this app. "
                    "All sends require manual approval — no automated or bulk sending."
                )
                try:
                    from auth.gmail import get_gmail_auth_url
                    auth_url = get_gmail_auth_url(user.email)
                    st.markdown(f"[Connect Gmail Account]({auth_url})")
                except Exception:
                    st.caption("Gmail OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file.")

    # -----------------------------------------------------------------------
    # Section 3: Notification Account
    # -----------------------------------------------------------------------
    with st.expander("Notification Account (Internal Reminders)", expanded=False):
        st.caption(
            "Connect a secondary Gmail account used ONLY for internal reminders (e.g. daily digests, "
            "follow-up nudges to yourself). This account is never used to contact prospects."
        )
        if not user_id:
            st.info("Sign in to configure the notification account.")
        else:
            from outreach.models import NotificationAccount
            notif_account = (
                session.query(NotificationAccount)
                .filter_by(user_id=user_id)
                .first()
            )
            if notif_account and notif_account.is_active:
                st.success(f"Notification account connected: {notif_account.email}")
                if st.button("Disconnect Notification Account"):
                    notif_account.is_active = False
                    try:
                        session.commit()
                        st.success("Notification account disconnected.")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error: {e}")
            else:
                notif_email = st.text_input("Notification email address", placeholder="your-internal@gmail.com")
                if st.button("Save Notification Account"):
                    if notif_email and "@" in notif_email:
                        if notif_account:
                            notif_account.email = notif_email.strip()
                            notif_account.is_active = True
                        else:
                            new_notif = NotificationAccount(
                                user_id=user_id,
                                email=notif_email.strip(),
                                is_active=True,
                            )
                            session.add(new_notif)
                        try:
                            session.commit()
                            st.success(f"Notification account set to {notif_email}.")
                            st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Error: {e}")
                    else:
                        st.error("Enter a valid email address.")

    # -----------------------------------------------------------------------
    # Section 4: Send Limits
    # -----------------------------------------------------------------------
    with st.expander("Send Limits", expanded=False):
        st.caption("Control the maximum number of emails sent per day. Compliance requirement: keep this low.")

        if not user:
            st.info("Sign in to configure send limits.")
        else:
            current_cap = user.daily_send_cap or 20
            new_cap = st.slider(
                "Daily Send Cap",
                min_value=1,
                max_value=50,
                value=current_cap,
                step=1,
                help="Maximum emails allowed per calendar day. Enforced before every send.",
            )
            if new_cap != current_cap:
                if st.button("Save Send Limit"):
                    user.daily_send_cap = new_cap
                    try:
                        session.commit()
                        st.success(f"Daily send cap updated to {new_cap}.")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error: {e}")

            # Show today's usage
            if user_id:
                from auth.gmail import check_daily_sends
                try:
                    sent_today, remaining = check_daily_sends(session, user_id)
                    st.caption(f"Today: {sent_today} sent / {new_cap} allowed / {remaining} remaining")
                except Exception:
                    pass

    # -----------------------------------------------------------------------
    # Section 5: Follow-Up Cadence
    # -----------------------------------------------------------------------
    with st.expander("Follow-Up Cadence", expanded=False):
        st.caption(
            "Default number of business days to wait after each send before the next follow-up is due. "
            "Changes here apply to newly-created outreach sequences only."
        )
        from outreach.followup_engine import DEFAULT_CADENCE
        cadence = st.session_state.get("custom_cadence", DEFAULT_CADENCE)

        col1, col2, col3 = st.columns(3)
        with col1:
            fu1 = st.number_input("Follow-Up 1 delay (business days)", min_value=1, max_value=30, value=cadence[0]["delay_business_days"] if cadence else 3)
        with col2:
            fu2 = st.number_input("Follow-Up 2 delay (business days)", min_value=1, max_value=60, value=cadence[1]["delay_business_days"] if len(cadence) > 1 else 7)
        with col3:
            fu3 = st.number_input("Follow-Up 3 delay (business days)", min_value=1, max_value=90, value=cadence[2]["delay_business_days"] if len(cadence) > 2 else 14)

        if st.button("Save Cadence"):
            new_cadence = [
                {"stage": 1, "delay_business_days": int(fu1), "label": f"Follow-Up 1 ({fu1} business days)"},
                {"stage": 2, "delay_business_days": int(fu2), "label": f"Follow-Up 2 ({fu2} business days)"},
                {"stage": 3, "delay_business_days": int(fu3), "label": f"Follow-Up 3 ({fu3} business days)"},
            ]
            st.session_state["custom_cadence"] = new_cadence
            st.success("Cadence saved for this session.")

    # -----------------------------------------------------------------------
    # Section 6: API Keys
    # -----------------------------------------------------------------------
    with st.expander("API Keys", expanded=False):
        st.caption(
            "Your Anthropic API key is stored in session state only — it is never written to the database or disk. "
            "You will need to re-enter it each session."
        )

        current_key = st.session_state.get("anthropic_api_key", "")
        key_display = f"...{current_key[-6:]}" if len(current_key) > 6 else ("Set" if current_key else "Not set")
        st.caption(f"Current Anthropic key: {key_display}")

        new_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Used for Claude-powered draft generation. Never stored in the database.",
        )
        if st.button("Save API Key"):
            if new_key.strip():
                st.session_state["anthropic_api_key"] = new_key.strip()
                st.success("API key saved to session.")
            else:
                st.error("Enter a valid API key.")

        if current_key:
            if st.button("Clear API Key", type="secondary"):
                st.session_state.pop("anthropic_api_key", None)
                st.success("API key cleared.")
                st.rerun()

    # -----------------------------------------------------------------------
    # Section 7: Data Management
    # -----------------------------------------------------------------------
    with st.expander("Data Management", expanded=False):
        # Database stats
        company_count = session.query(Company).count()
        contact_count = session.query(Contact).count()
        draft_count = session.query(Draft).count()
        sent_count = session.query(SentEmail).count()
        suppression_count = session.query(SuppressionEntry).count()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Companies", company_count)
            st.metric("Contacts", contact_count)
        with col2:
            st.metric("Drafts", draft_count)
            st.metric("Sent Emails", sent_count)
        with col3:
            st.metric("Suppressed", suppression_count)

        st.divider()

        col_seed, col_export = st.columns(2)

        with col_seed:
            st.caption("Add sample companies and contacts for testing.")
            if st.button("Seed Sample Data", use_container_width=True):
                msg = _seed_sample_data(session, user_id)
                if "Error" in msg:
                    st.error(msg)
                else:
                    st.success(msg)
                    st.rerun()

        with col_export:
            st.caption("Export all companies and contacts to CSV.")
            if st.button("Export All Data", use_container_width=True):
                try:
                    csv_bytes = _export_all_data(session)
                    st.download_button(
                        label="Download CSV",
                        data=csv_bytes,
                        file_name=f"all_companies_{datetime.utcnow().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                    )
                except Exception as e:
                    st.error(f"Export error: {e}")

        st.divider()
        st.subheader("Import Companies from CSV")
        st.caption("Upload a CSV with columns: Company Name, Website, City, State, Industry, Email, Contact Name, Contact Title.")
        uploaded_csv = st.file_uploader("Upload company CSV", type=["csv"], key="import_csv")

        if uploaded_csv and st.button("Import CSV"):
            from discovery.pipeline import CSVImportSource
            source = CSVImportSource()
            try:
                result = source.import_csv(session, uploaded_csv)
                session.commit()
                st.success(
                    f"Import complete: {result['imported']} imported, {result['skipped']} skipped."
                )
                if result["errors"]:
                    st.warning(f"Errors on {len(result['errors'])} rows. First few: {result['errors'][:3]}")
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Import failed: {e}")

    # -----------------------------------------------------------------------
    # Section 8: About
    # -----------------------------------------------------------------------
    with st.expander("About This App", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("AI Systems Audit Pipeline")
            st.caption(f"Version {APP_VERSION}")
            st.divider()
            st.subheader("About Brandon Rye")
            st.write(founder_credibility_block())

        with col2:
            st.caption("Future Legend")
            st.caption("AI Systems Audit &")
            st.caption("Deployment Blueprint")

        st.divider()
        st.subheader("Compliance Statement")
        st.error(compliance_warning(), icon=None)
        st.write(
            "This application is designed for individual, manual outreach only. "
            "It enforces a daily send cap, requires explicit approval before every email is sent, "
            "maintains a suppression list that is checked before every send, and does not support "
            "automated or scheduled email delivery of any kind. "
            "All outreach generated by this tool must be reviewed and approved by the user before sending."
        )

finally:
    session.close()

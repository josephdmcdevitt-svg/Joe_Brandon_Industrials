import streamlit as st
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Systems Audit Pipeline",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Database init with full error reporting
# ---------------------------------------------------------------------------
db_ready = False
try:
    from database.db import init_db, get_engine
    from database.models import Company, Draft, Activity
    init_db()
    db_ready = True
except Exception as e:
    st.error(f"Database init failed: {e}")
    st.code(traceback.format_exc())

try:
    from outreach.models import OutreachState, NotificationAccount
    OutreachState.__table__.create(get_engine(), checkfirst=True)
    NotificationAccount.__table__.create(get_engine(), checkfirst=True)
except Exception as e:
    st.warning(f"Outreach tables: {e}")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def _get_or_create_demo_user():
    from database.db import get_session
    from database.models import User
    session = get_session()
    try:
        demo = session.query(User).filter_by(google_id="demo_user_local").first()
        if demo is None:
            demo = User(
                google_id="demo_user_local",
                email="demo@local.dev",
                name="Demo User",
                picture_url=None,
                gmail_connected=False,
            )
            session.add(demo)
            session.commit()
            session.refresh(demo)
        return {
            "id": demo.id,
            "name": demo.name,
            "email": demo.email,
            "picture_url": demo.picture_url,
        }
    finally:
        session.close()


def _handle_oauth_callback(code: str):
    from auth.google_auth import handle_oauth_callback, get_or_create_user
    from database.db import get_session
    try:
        user_info = handle_oauth_callback(code)
        session = get_session()
        try:
            user = get_or_create_user(session, user_info)
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "picture_url": user.picture_url,
            }
        finally:
            session.close()
    except Exception as e:
        st.error(f"Google sign-in failed: {e}")
        return None


def _get_quick_stats(user_id: int) -> dict:
    from database.db import get_session
    from datetime import datetime
    session = get_session()
    try:
        total_leads = session.query(Company).count()
        drafts_pending = (
            session.query(Draft)
            .filter(Draft.status == "draft", Draft.user_id == user_id)
            .count()
        )
        try:
            from outreach.models import OutreachState
            now = datetime.utcnow()
            followups_due = (
                session.query(OutreachState)
                .filter(
                    OutreachState.user_id == user_id,
                    OutreachState.status == "awaiting_reply",
                    OutreachState.next_followup_due <= now,
                    OutreachState.is_suppressed == False,
                )
                .count()
            )
        except Exception:
            followups_due = 0
        return {
            "total_leads": total_leads,
            "drafts_pending": drafts_pending,
            "followups_due": followups_due,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Check for OAuth callback
# ---------------------------------------------------------------------------
params = st.query_params
if "code" in params and "user" not in st.session_state:
    code = params["code"]
    with st.spinner("Signing you in with Google..."):
        user_data = _handle_oauth_callback(code)
    if user_data:
        st.session_state["user"] = user_data
        st.query_params.clear()
        st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
if "user" in st.session_state:
    user = st.session_state["user"]
    stats = _get_quick_stats(user["id"])

    with st.sidebar:
        st.markdown("### Account")
        if user.get("picture_url"):
            st.image(user["picture_url"], width=48)
        st.markdown(f"**{user['name']}**")
        st.caption(user["email"])
        st.divider()

        st.markdown("### Quick Stats")
        col1, col2 = st.columns(2)
        col1.metric("Total Leads", stats["total_leads"])
        col2.metric("Follow-ups Due", stats["followups_due"])
        st.metric("Drafts Pending Review", stats["drafts_pending"])
        st.divider()

        if st.button("Sign Out", use_container_width=True):
            for key in ["user", "selected_company_id"]:
                st.session_state.pop(key, None)
            st.rerun()

        st.caption(
            "Every email requires manual review and approval before sending. "
            "No bulk or automated sending."
        )


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.markdown(
        """
        <div style="text-align: center; padding: 3rem 1rem 1rem 1rem;">
            <h1 style="font-size: 2.4rem; font-weight: 700;">AI Systems Audit Pipeline</h1>
            <p style="font-size: 1.15rem; color: #666; margin-top: 0.25rem;">
                Find, score, and engage small businesses for AI consulting
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown(
            """
            **What this tool does:**
            - Manages a pipeline of small-business leads (5-20 employees, $500K-$5M revenue)
            - Scores each company on AI fit and likelihood to buy the *AI Systems Audit & Deployment Blueprint*
            - Generates personalized cold outreach drafts for manual review before sending
            - Tracks follow-up cadence and pipeline stage across all prospects

            **The offer:** A 60-minute recorded strategy session with the business owner.
            Deliverables within 48 hours: current-state workflow map, AI leverage points
            ranked by ROI, recommended tool stack, 30-60-90 day roadmap, and estimated
            cost savings.
            """
        )

        st.divider()

        google_available = bool(
            os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")
        )

        if google_available:
            from auth.google_auth import get_google_auth_url
            auth_url = get_google_auth_url()
            st.link_button(
                "Sign in with Google",
                url=auth_url,
                use_container_width=True,
                type="primary",
            )
            st.caption("Google sign-in syncs your Gmail account for managing draft outreach.")
            st.markdown("")

        if st.button(
            "Continue as Demo User",
            use_container_width=True,
            type="secondary" if google_available else "primary",
        ):
            demo_user = _get_or_create_demo_user()
            st.session_state["user"] = demo_user
            st.rerun()

        if not google_available:
            st.info(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET in your .env file to enable Google sign-in."
            )

else:
    user = st.session_state["user"]
    stats = _get_quick_stats(user["id"])

    st.title(f"Welcome back, {user['name'].split()[0]}.")
    st.caption("AI Systems Audit Pipeline")
    st.markdown("")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Leads", stats["total_leads"])
    col2.metric("Follow-ups Due", stats["followups_due"], delta_color="inverse")
    col3.metric("Drafts Pending Review", stats["drafts_pending"])

    st.divider()
    st.subheader("Where to go next")

    nav_col1, nav_col2, nav_col3 = st.columns(3)
    with nav_col1:
        st.markdown("**Dashboard**")
        st.markdown("Pipeline funnel, score distribution, top leads, and recent activity.")
    with nav_col2:
        st.markdown("**Lead Explorer**")
        st.markdown("Search and filter all companies. Sort by score, stage, or recency.")
    with nav_col3:
        st.markdown("**Lead Detail**")
        st.markdown("Deep-dive on a single company: scores, contacts, notes, and outreach drafts.")

    if stats["followups_due"] > 0:
        st.warning(
            f"You have **{stats['followups_due']} follow-up(s) due**. "
            "Check the Follow-Up Dashboard to action them."
        )

    st.divider()
    st.caption(
        "Compliance reminder: Every email draft requires manual review and approval "
        "before sending. This system does not support bulk or automated sending."
    )

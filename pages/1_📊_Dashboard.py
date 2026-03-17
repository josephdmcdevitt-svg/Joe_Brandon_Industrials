"""
Dashboard - Pipeline overview, metrics, funnel, score distribution, top leads, activity.
Do NOT call st.set_page_config() here — it is set in app.py.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from database.db import get_session
from database.models import Company, Contact, Draft, SentEmail, Activity
from utils.helpers import (
    PIPELINE_STAGES,
    get_stage_label,
    get_stage_color,
    format_revenue,
    format_employees,
    parse_json_field,
)


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.warning("Please sign in to access this page.")
    st.page_link("app.py", label="Go to sign-in page")
    st.stop()

user = st.session_state["user"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_dashboard_data():
    session = get_session()
    try:
        companies = session.query(Company).all()
        activities = (
            session.query(Activity)
            .order_by(Activity.created_at.desc())
            .limit(20)
            .all()
        )

        company_rows = []
        for c in companies:
            primary_contact = None
            for contact in c.contacts:
                if contact.is_decision_maker and not contact.do_not_contact:
                    primary_contact = contact
                    break
            if primary_contact is None and c.contacts:
                primary_contact = c.contacts[0]

            company_rows.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "metro_area": c.metro_area or "",
                    "industry": c.industry or "",
                    "pipeline_stage": c.pipeline_stage or "new_lead",
                    "ai_fit_score": c.ai_fit_score,
                    "offer_conversion_score": c.offer_conversion_score,
                    "enriched": c.enriched,
                    "created_at": c.created_at,
                    "primary_contact": (
                        f"{primary_contact.first_name or ''} {primary_contact.last_name or ''}".strip()
                        if primary_contact
                        else ""
                    ),
                }
            )

        activity_rows = []
        for a in activities:
            activity_rows.append(
                {
                    "action": a.action,
                    "entity_type": a.entity_type or "",
                    "entity_id": a.entity_id,
                    "details": a.details or "",
                    "created_at": a.created_at,
                }
            )

        drafts_pending = (
            session.query(Draft)
            .filter(Draft.status == "draft", Draft.user_id == user["id"])
            .count()
        )

        from outreach.models import OutreachState
        now = datetime.utcnow()
        followups_due = (
            session.query(OutreachState)
            .filter(
                OutreachState.user_id == user["id"],
                OutreachState.status == "awaiting_reply",
                OutreachState.next_followup_due <= now,
                OutreachState.is_suppressed == False,
            )
            .count()
        )

        return {
            "companies": company_rows,
            "activities": activity_rows,
            "drafts_pending": drafts_pending,
            "followups_due": followups_due,
        }
    finally:
        session.close()


data = load_dashboard_data()
df = pd.DataFrame(data["companies"])


# ---------------------------------------------------------------------------
# Computed metrics
# ---------------------------------------------------------------------------

stage_keys = [s[0] for s in PIPELINE_STAGES]

total_companies = len(df)
enriched_count = int(df["enriched"].sum()) if not df.empty else 0
drafts_ready = int((df["pipeline_stage"] == "draft_ready").sum()) if not df.empty else 0
contacted_count = int((df["pipeline_stage"] == "contacted").sum()) if not df.empty else 0
replied_count = int((df["pipeline_stage"] == "replied").sum()) if not df.empty else 0
audits_sold = int((df["pipeline_stage"] == "audit_sold").sum()) if not df.empty else 0


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("Pipeline Dashboard")
st.caption(f"Last refreshed: {datetime.now().strftime('%b %d, %Y %I:%M %p')}")

if data["followups_due"] > 0:
    st.warning(
        f"{data['followups_due']} follow-up(s) are due. "
        "Filter by 'Contacted' stage in Lead Explorer to action them."
    )

st.divider()


# ---------------------------------------------------------------------------
# Top metrics row
# ---------------------------------------------------------------------------

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Companies", total_companies)
m2.metric("Enriched", enriched_count)
m3.metric("Drafts Ready", drafts_ready)
m4.metric("Contacted", contacted_count)
m5.metric("Replied", replied_count)
m6.metric("Audits Sold", audits_sold)

st.markdown("")


# ---------------------------------------------------------------------------
# Row 2: Pipeline funnel + Score distribution
# ---------------------------------------------------------------------------

chart_col, score_col = st.columns([3, 2])

with chart_col:
    st.subheader("Pipeline Funnel")
    if not df.empty:
        stage_counts = df["pipeline_stage"].value_counts().to_dict()
        funnel_labels = []
        funnel_values = []
        funnel_colors = []
        for stage_key, stage_label in PIPELINE_STAGES:
            count = stage_counts.get(stage_key, 0)
            funnel_labels.append(stage_label)
            funnel_values.append(count)
            funnel_colors.append(get_stage_color(stage_key))

        fig_funnel = go.Figure(
            go.Bar(
                x=funnel_labels,
                y=funnel_values,
                marker_color=funnel_colors,
                text=funnel_values,
                textposition="outside",
            )
        )
        fig_funnel.update_layout(
            xaxis_tickangle=-35,
            yaxis_title="Companies",
            margin=dict(t=20, b=10, l=0, r=0),
            height=300,
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig_funnel.update_xaxes(showgrid=False)
        fig_funnel.update_yaxes(gridcolor="#f0f0f0")
        st.plotly_chart(fig_funnel, use_container_width=True)
    else:
        st.info("No companies in the pipeline yet.")

with score_col:
    st.subheader("AI Fit Score Distribution")
    scored_df = df[df["ai_fit_score"].notna()] if not df.empty else pd.DataFrame()
    if not scored_df.empty:
        fig_hist = px.histogram(
            scored_df,
            x="ai_fit_score",
            nbins=10,
            range_x=[0, 100],
            color_discrete_sequence=["#4A90E2"],
        )
        fig_hist.update_layout(
            xaxis_title="AI Fit Score",
            yaxis_title="Companies",
            margin=dict(t=20, b=10, l=0, r=0),
            height=300,
            showlegend=False,
            bargap=0.05,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig_hist.update_yaxes(gridcolor="#f0f0f0")
        # Add colored reference lines
        fig_hist.add_vline(x=70, line_dash="dash", line_color="#27ae60", annotation_text="70 (High)")
        fig_hist.add_vline(x=40, line_dash="dash", line_color="#e67e22", annotation_text="40 (Low)")
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No scored companies yet. Run the scorer from Lead Detail.")

st.divider()


# ---------------------------------------------------------------------------
# Row 3: Top 10 leads + Activity feed
# ---------------------------------------------------------------------------

leads_col, activity_col = st.columns([3, 2])

with leads_col:
    st.subheader("Top 10 Highest-Scored Leads")
    if not df.empty:
        top_df = (
            df[df["ai_fit_score"].notna()]
            .sort_values("ai_fit_score", ascending=False)
            .head(10)
            .copy()
        )

        if not top_df.empty:
            # Build display dataframe
            display_rows = []
            for _, row in top_df.iterrows():
                score = int(row["ai_fit_score"]) if pd.notna(row["ai_fit_score"]) else None
                offer = int(row["offer_conversion_score"]) if pd.notna(row["offer_conversion_score"]) else None
                stage_label = get_stage_label(row["pipeline_stage"])

                if score is not None and score >= 70:
                    score_display = f"🟢 {score}"
                elif score is not None and score >= 40:
                    score_display = f"🟡 {score}"
                else:
                    score_display = f"🔴 {score}" if score is not None else "—"

                display_rows.append(
                    {
                        "Company": row["name"],
                        "Metro": row["metro_area"] or "—",
                        "Industry": row["industry"] or "—",
                        "AI Fit": score_display,
                        "Offer Score": offer if offer is not None else "—",
                        "Stage": stage_label,
                        "Primary Contact": row["primary_contact"] or "—",
                    }
                )

            display_df = pd.DataFrame(display_rows)
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=370,
            )

            # Quick link to open a lead in detail view
            st.caption("Select a company in Lead Explorer to open its detail view.")
        else:
            st.info("Score companies to see the top leads list.")
    else:
        st.info("No companies in the pipeline yet.")

with activity_col:
    st.subheader("Recent Activity")
    activities = data["activities"]
    if activities:
        for act in activities:
            ts = act["created_at"]
            if isinstance(ts, datetime):
                ago = datetime.utcnow() - ts
                if ago.days > 0:
                    time_str = f"{ago.days}d ago"
                elif ago.seconds >= 3600:
                    time_str = f"{ago.seconds // 3600}h ago"
                else:
                    time_str = f"{ago.seconds // 60}m ago"
            else:
                time_str = str(ts)[:10] if ts else ""

            action_icon_map = {
                "enriched": "✨",
                "scored": "📊",
                "draft_created": "✏️",
                "email_sent": "📧",
                "stage_changed": "🔄",
                "note_added": "📝",
                "contact_added": "👤",
                "do_not_contact": "🚫",
            }
            icon = action_icon_map.get(act["action"], "•")

            details_preview = act["details"][:60] + "..." if len(act["details"]) > 60 else act["details"]

            st.markdown(
                f"{icon} **{act['action'].replace('_', ' ').title()}** "
                f"<span style='color:#888; font-size:0.8rem;'>{time_str}</span>",
                unsafe_allow_html=True,
            )
            if details_preview:
                st.caption(details_preview)
    else:
        st.info("No activity recorded yet.")

st.divider()

# Follow-up prompt
if data["followups_due"] > 0:
    st.info(
        f"**{data['followups_due']} follow-up(s) due.** "
        "Go to Lead Explorer and filter by 'Contacted' stage to find and action them."
    )
    st.page_link("pages/2_🔎_Lead_Explorer.py", label="Open Lead Explorer")

# Drafts pending
if data["drafts_pending"] > 0:
    st.info(
        f"**{data['drafts_pending']} draft(s) pending your review.** "
        "Open a lead from the Lead Explorer and review drafts in the Lead Detail page."
    )

"""
Pipeline Board — Kanban-style view of all companies by stage.
No st.set_page_config() here; it lives in app.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import streamlit as st

from database.db import get_session, init_db
from database.models import Activity, Company, Contact, SentEmail
from utils.helpers import PIPELINE_STAGES, get_stage_color, get_stage_label

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _primary_contact(company: Company):
    for c in company.contacts:
        if c.is_decision_maker:
            return c
    if company.contacts:
        return company.contacts[0]
    return None


def _last_activity_date(session, company_id: int):
    act = (
        session.query(Activity)
        .filter(Activity.entity_id == company_id, Activity.entity_type == "company")
        .order_by(Activity.created_at.desc())
        .first()
    )
    return act.created_at if act else None


def _pipeline_summary(session):
    """Returns dict of stage_key -> list[Company]."""
    companies = session.query(Company).order_by(Company.name).all()
    buckets = {key: [] for key, _ in PIPELINE_STAGES}
    for c in companies:
        stage = c.pipeline_stage or "new_lead"
        if stage not in buckets:
            stage = "new_lead"
        buckets[stage].append(c)
    return buckets, companies


def _conversion_rate(session) -> float:
    """Percent of all contacted companies that reached audit_sold."""
    total_contacted = (
        session.query(Company)
        .filter(Company.pipeline_stage.in_([
            "contacted", "replied", "call_scheduled",
            "audit_sold", "audit_delivered", "implementation_opportunity", "closed_lost"
        ]))
        .count()
    )
    audit_sold = (
        session.query(Company)
        .filter(Company.pipeline_stage == "audit_sold")
        .count()
    )
    if total_contacted == 0:
        return 0.0
    return round((audit_sold / total_contacted) * 100, 1)


def _avg_days_in_pipeline(session) -> float:
    """Average days from created_at to now for companies still active."""
    active_companies = (
        session.query(Company)
        .filter(Company.pipeline_stage.notin_(["closed_lost", "audit_delivered"]))
        .all()
    )
    if not active_companies:
        return 0.0
    now = datetime.utcnow()
    total_days = sum((now - c.created_at).days for c in active_companies)
    return round(total_days / len(active_companies), 1)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Pipeline Board")
st.caption("Track all companies through the outreach and sales pipeline.")

init_db()
session = get_session()

try:
    buckets, all_companies = _pipeline_summary(session)

    # -----------------------------------------------------------------------
    # Summary stats
    # -----------------------------------------------------------------------
    total = len(all_companies)
    conversion = _conversion_rate(session)
    avg_days = _avg_days_in_pipeline(session)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total in Pipeline", total)
    with m2:
        st.metric("Conversion Rate", f"{conversion}%", help="Audit Sold / Total Contacted")
    with m3:
        st.metric("Avg Days in Pipeline", f"{avg_days} days", help="Active companies only")

    st.divider()

    # -----------------------------------------------------------------------
    # Stage move section
    # -----------------------------------------------------------------------
    with st.expander("Move a Company to a New Stage", expanded=False):
        if not all_companies:
            st.caption("No companies yet.")
        else:
            col_a, col_b, col_c = st.columns([2, 2, 1])
            with col_a:
                move_company_name = st.selectbox(
                    "Company",
                    [c.name for c in all_companies],
                    key="move_company",
                )
            with col_b:
                new_stage_label = st.selectbox(
                    "Move to Stage",
                    [label for _, label in PIPELINE_STAGES],
                    key="move_stage",
                )
            with col_c:
                st.write("")
                st.write("")
                move_clicked = st.button("Move", type="primary", use_container_width=True)

            if move_clicked:
                company_to_move = next((c for c in all_companies if c.name == move_company_name), None)
                new_stage_key = next((k for k, label in PIPELINE_STAGES if label == new_stage_label), None)
                if company_to_move and new_stage_key:
                    old_stage = company_to_move.pipeline_stage
                    company_to_move.pipeline_stage = new_stage_key
                    company_to_move.updated_at = datetime.utcnow()
                    activity = Activity(
                        user_id=st.session_state.get("user_id"),
                        action="stage_changed",
                        entity_type="company",
                        entity_id=company_to_move.id,
                        details=f"Stage changed from {old_stage} to {new_stage_key}",
                    )
                    try:
                        session.add(activity)
                        session.commit()
                        st.success(f"Moved {move_company_name} to {new_stage_label}.")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error: {e}")

    st.divider()

    # -----------------------------------------------------------------------
    # Kanban board — active stages only (skip noise stages for display)
    # -----------------------------------------------------------------------
    # Show all stages in 3-column rows
    stage_keys = [key for key, _ in PIPELINE_STAGES]
    n_cols = 3
    rows = [stage_keys[i:i + n_cols] for i in range(0, len(stage_keys), n_cols)]

    for row_stages in rows:
        cols = st.columns(len(row_stages))
        for col, stage_key in zip(cols, row_stages):
            stage_label = get_stage_label(stage_key)
            stage_color = get_stage_color(stage_key)
            stage_companies = buckets.get(stage_key, [])

            with col:
                # Stage header with color indicator
                st.markdown(
                    f'<div style="background-color:{stage_color};padding:6px 10px;'
                    f'border-radius:6px;margin-bottom:8px;">'
                    f'<strong style="color:#fff;text-shadow:0 1px 2px rgba(0,0,0,0.4);">'
                    f'{stage_label}</strong> '
                    f'<span style="background:rgba(255,255,255,0.3);border-radius:10px;'
                    f'padding:1px 7px;font-size:0.85em;color:#fff;">{len(stage_companies)}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if not stage_companies:
                    st.caption("—")
                else:
                    for c in stage_companies:
                        contact = _primary_contact(c)
                        contact_name = ""
                        if contact:
                            contact_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()

                        last_act = _last_activity_date(session, c.id)
                        last_act_str = last_act.strftime("%b %d") if last_act else "—"

                        score_str = f"Score: {c.ai_fit_score}" if c.ai_fit_score is not None else "Not scored"

                        with st.container(border=True):
                            st.markdown(f"**{c.name}**")
                            if c.industry:
                                st.caption(c.industry)
                            st.caption(score_str)
                            if contact_name:
                                st.caption(f"Contact: {contact_name}")
                            st.caption(f"Last activity: {last_act_str}")

finally:
    session.close()

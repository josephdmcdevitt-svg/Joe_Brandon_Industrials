"""
Email Leads — Shows leads with verified emails (actionable) vs. without (archive).
"""
import streamlit as st
import pandas as pd
import os
import json
from database.db import get_session
from database.models import Company, Contact
from utils.helpers import (
    METRO_AREAS, INDUSTRIES, format_revenue, format_employees,
    get_stage_label, get_stage_color, compliance_warning
)

st.title("Email Leads")

session = get_session()

# --- Load all companies with their primary contacts ---
companies = session.query(Company).order_by(Company.ai_fit_score.desc()).all()

if not companies:
    st.info("No leads in the database yet. Import leads from Settings or the Lead Explorer.")
    session.close()
    st.stop()

# Build dataframe
rows = []
for c in companies:
    contacts = session.query(Contact).filter(Contact.company_id == c.id).all()
    # Find contact with email, prefer decision maker
    email_contact = None
    any_contact = None
    for contact in contacts:
        if not any_contact:
            any_contact = contact
        if contact.email and contact.email.strip() and contact.email.strip().upper() != "N/A":
            if not email_contact or contact.is_decision_maker:
                email_contact = contact

    contact_to_use = email_contact or any_contact
    has_email = email_contact is not None

    rows.append({
        "id": c.id,
        "company_name": c.name,
        "city": c.city,
        "state": c.state,
        "metro_area": c.metro_area,
        "industry": c.industry,
        "sub_industry": c.sub_industry or "",
        "employees": format_employees(c.employee_count_min or 0, c.employee_count_max or 0),
        "revenue": format_revenue(
            c.estimated_revenue_min or 0,
            c.estimated_revenue_max or 0,
            c.revenue_is_estimated
        ),
        "ai_fit_score": c.ai_fit_score or 0,
        "offer_score": c.offer_conversion_score or 0,
        "pipeline_stage": get_stage_label(c.pipeline_stage or "new_lead"),
        "contact_name": f"{contact_to_use.first_name or ''} {contact_to_use.last_name or ''}".strip() if contact_to_use else "N/A",
        "contact_title": contact_to_use.title if contact_to_use else "N/A",
        "contact_email": email_contact.email if email_contact else "N/A",
        "has_email": has_email,
    })

session.close()

df = pd.DataFrame(rows)

# --- Metrics ---
total = len(df)
with_email = df["has_email"].sum()
without_email = total - with_email
pct = (with_email / total * 100) if total > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Leads", f"{total:,}")
col2.metric("With Email", f"{int(with_email):,}")
col3.metric("Without Email", f"{int(without_email):,}")
col4.metric("Email Coverage", f"{pct:.0f}%")

st.divider()

# --- Tabs ---
tab_actionable, tab_archive = st.tabs(["Actionable Leads (Have Email)", "Archive (No Email)"])

# --- Filters (shared) ---
with st.sidebar:
    st.subheader("Filters")
    search = st.text_input("Search company name", "")

    metro_filter = st.multiselect("Metro Area", sorted(df["metro_area"].dropna().unique().tolist()))

    industry_filter = st.multiselect("Industry", sorted(df["industry"].dropna().unique().tolist()))

    score_range = st.slider("Min AI Fit Score", 0, 100, 0)

    sort_by = st.selectbox("Sort by", [
        "AI Fit Score (High to Low)",
        "Offer Score (High to Low)",
        "Company Name (A-Z)",
    ])

def apply_filters(data):
    filtered = data.copy()
    if search:
        filtered = filtered[filtered["company_name"].str.contains(search, case=False, na=False)]
    if metro_filter:
        filtered = filtered[filtered["metro_area"].isin(metro_filter)]
    if industry_filter:
        filtered = filtered[filtered["industry"].isin(industry_filter)]
    if score_range > 0:
        filtered = filtered[filtered["ai_fit_score"] >= score_range]

    if sort_by == "AI Fit Score (High to Low)":
        filtered = filtered.sort_values("ai_fit_score", ascending=False)
    elif sort_by == "Offer Score (High to Low)":
        filtered = filtered.sort_values("offer_score", ascending=False)
    elif sort_by == "Company Name (A-Z)":
        filtered = filtered.sort_values("company_name")

    return filtered

# --- Actionable Tab ---
with tab_actionable:
    st.subheader("Leads with Verified Emails — Ready for Outreach")
    st.caption(compliance_warning())

    email_df = apply_filters(df[df["has_email"] == True])

    if email_df.empty:
        st.info("No leads with emails match your filters.")
    else:
        st.write(f"**{len(email_df)} leads** ready for outreach")

        display_cols = [
            "company_name", "metro_area", "industry", "employees",
            "ai_fit_score", "offer_score", "contact_name",
            "contact_title", "contact_email", "pipeline_stage"
        ]

        st.dataframe(
            email_df[display_cols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            column_config={
                "company_name": st.column_config.TextColumn("Company", width="medium"),
                "metro_area": st.column_config.TextColumn("Metro", width="small"),
                "industry": st.column_config.TextColumn("Industry", width="medium"),
                "employees": st.column_config.TextColumn("Size", width="small"),
                "ai_fit_score": st.column_config.ProgressColumn(
                    "AI Fit", min_value=0, max_value=100, format="%d"
                ),
                "offer_score": st.column_config.ProgressColumn(
                    "Offer Score", min_value=0, max_value=100, format="%d"
                ),
                "contact_name": st.column_config.TextColumn("Contact", width="medium"),
                "contact_title": st.column_config.TextColumn("Title", width="small"),
                "contact_email": st.column_config.TextColumn("Email", width="medium"),
                "pipeline_stage": st.column_config.TextColumn("Stage", width="small"),
            }
        )

        # Export actionable leads
        csv_data = email_df[display_cols + ["city", "state", "revenue"]].to_csv(index=False)
        st.download_button(
            "Export Email Leads to CSV",
            csv_data,
            file_name="actionable_email_leads.csv",
            mime="text/csv",
        )

        # Quick action: select lead for drafting
        st.divider()
        st.subheader("Quick Draft")
        selected_company = st.selectbox(
            "Select a lead to draft outreach",
            email_df["company_name"].tolist(),
            index=None,
            placeholder="Choose a company..."
        )
        if selected_company:
            lead = email_df[email_df["company_name"] == selected_company].iloc[0]
            st.write(f"**{lead['company_name']}** — {lead['industry']} in {lead['metro_area']}")
            st.write(f"Contact: {lead['contact_name']} ({lead['contact_title']}) — {lead['contact_email']}")
            st.write(f"AI Fit: {lead['ai_fit_score']} | Offer Score: {lead['offer_score']}")

            if st.button("Go to Messaging Studio"):
                st.session_state["selected_company_id"] = lead["id"]
                st.switch_page("pages/4_✉️_Messaging_Studio.py")

# --- Archive Tab ---
with tab_archive:
    st.subheader("Leads Without Email — Needs Enrichment")
    st.caption("These leads need email addresses before outreach. Use Apollo.io, Hunter.io, or manual research.")

    no_email_df = apply_filters(df[df["has_email"] == False])

    if no_email_df.empty:
        st.info("No leads without emails match your filters.")
    else:
        st.write(f"**{len(no_email_df)} leads** need email enrichment")

        archive_cols = [
            "company_name", "metro_area", "industry", "employees",
            "ai_fit_score", "offer_score", "contact_name", "contact_title", "pipeline_stage"
        ]

        st.dataframe(
            no_email_df[archive_cols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            column_config={
                "company_name": st.column_config.TextColumn("Company", width="medium"),
                "metro_area": st.column_config.TextColumn("Metro", width="small"),
                "industry": st.column_config.TextColumn("Industry", width="medium"),
                "employees": st.column_config.TextColumn("Size", width="small"),
                "ai_fit_score": st.column_config.ProgressColumn(
                    "AI Fit", min_value=0, max_value=100, format="%d"
                ),
                "offer_score": st.column_config.ProgressColumn(
                    "Offer Score", min_value=0, max_value=100, format="%d"
                ),
                "contact_name": st.column_config.TextColumn("Contact", width="medium"),
                "contact_title": st.column_config.TextColumn("Title", width="small"),
                "pipeline_stage": st.column_config.TextColumn("Stage", width="small"),
            }
        )

        # Export archive for enrichment
        csv_data = no_email_df[archive_cols + ["city", "state"]].to_csv(index=False)
        st.download_button(
            "Export Archive to CSV (for enrichment)",
            csv_data,
            file_name="leads_need_email.csv",
            mime="text/csv",
        )

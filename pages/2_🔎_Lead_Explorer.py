"""
Lead Explorer - Searchable, filterable lead table.
Do NOT call st.set_page_config() here — it is set in app.py.
"""
import streamlit as st
import pandas as pd
import io

from database.db import get_session
from database.models import Company, Contact
from utils.helpers import (
    METRO_AREAS,
    INDUSTRIES,
    PIPELINE_STAGES,
    REVENUE_BANDS,
    format_revenue,
    format_employees,
    get_stage_label,
    get_stage_color,
)


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.warning("Please sign in to access this page.")
    st.page_link("app.py", label="Go to sign-in page")
    st.stop()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)
def load_all_companies():
    session = get_session()
    try:
        companies = session.query(Company).order_by(Company.created_at.desc()).all()
        rows = []
        for c in companies:
            # Primary contact
            primary_contact = None
            for contact in c.contacts:
                if contact.is_decision_maker and not contact.do_not_contact:
                    primary_contact = contact
                    break
            if primary_contact is None and c.contacts:
                for contact in c.contacts:
                    if not contact.do_not_contact:
                        primary_contact = contact
                        break
            if primary_contact is None and c.contacts:
                primary_contact = c.contacts[0]

            contact_name = ""
            if primary_contact:
                contact_name = f"{primary_contact.first_name or ''} {primary_contact.last_name or ''}".strip()

            # Mid-point for employee range (for slider filtering)
            emp_mid = None
            if c.employee_count_min is not None and c.employee_count_max is not None:
                emp_mid = (c.employee_count_min + c.employee_count_max) / 2
            elif c.employee_count_min is not None:
                emp_mid = float(c.employee_count_min)
            elif c.employee_count_max is not None:
                emp_mid = float(c.employee_count_max)

            # Revenue mid-point
            rev_mid = None
            if c.estimated_revenue_min is not None and c.estimated_revenue_max is not None:
                rev_mid = (c.estimated_revenue_min + c.estimated_revenue_max) / 2
            elif c.estimated_revenue_min is not None:
                rev_mid = float(c.estimated_revenue_min)
            elif c.estimated_revenue_max is not None:
                rev_mid = float(c.estimated_revenue_max)

            rows.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "website": c.website or "",
                    "metro_area": c.metro_area or "",
                    "industry": c.industry or "",
                    "employee_count_min": c.employee_count_min,
                    "employee_count_max": c.employee_count_max,
                    "emp_mid": emp_mid,
                    "estimated_revenue_min": c.estimated_revenue_min,
                    "estimated_revenue_max": c.estimated_revenue_max,
                    "revenue_is_estimated": c.revenue_is_estimated,
                    "rev_mid": rev_mid,
                    "ai_fit_score": c.ai_fit_score,
                    "offer_conversion_score": c.offer_conversion_score,
                    "pipeline_stage": c.pipeline_stage or "new_lead",
                    "enriched": c.enriched,
                    "description": c.description or "",
                    "tags": c.tags or "",
                    "primary_contact": contact_name,
                    "created_at": c.created_at,
                }
            )
        return rows
    finally:
        session.close()


all_rows = load_all_companies()
df_all = pd.DataFrame(all_rows) if all_rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("Lead Explorer")
st.caption(f"{len(all_rows)} total companies in database")

st.markdown("")


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

with st.expander("Filters", expanded=True):
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        search_text = st.text_input(
            "Search by company name or description",
            placeholder="e.g. Smith HVAC",
        )

        all_metro = sorted(METRO_AREAS)
        selected_metros = st.multiselect(
            "Metro Area",
            options=all_metro,
            default=[],
        )

    with f_col2:
        all_industries = sorted(INDUSTRIES.keys())
        selected_industries = st.multiselect(
            "Industry (category)",
            options=all_industries,
            default=[],
        )

        stage_options = [(k, get_stage_label(k)) for k, _ in PIPELINE_STAGES]
        selected_stages = st.multiselect(
            "Pipeline Stage",
            options=[k for k, _ in stage_options],
            format_func=lambda k: get_stage_label(k),
            default=[],
        )

    with f_col3:
        emp_range = st.slider("Employee Count (midpoint)", min_value=1, max_value=100, value=(1, 100))
        score_range = st.slider("AI Fit Score", min_value=0, max_value=100, value=(0, 100))

        revenue_band_labels = [label for _, _, label in REVENUE_BANDS]
        selected_rev_bands = st.multiselect(
            "Revenue Band",
            options=revenue_band_labels,
            default=[],
        )

    sort_by = st.selectbox(
        "Sort by",
        options=[
            "AI Fit Score (highest first)",
            "Offer Conversion Score (highest first)",
            "Company Name (A-Z)",
            "Recently Added",
        ],
        index=0,
    )


# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------

if df_all.empty:
    filtered_df = df_all.copy()
else:
    filtered_df = df_all.copy()

    # Text search
    if search_text.strip():
        q = search_text.strip().lower()
        mask = (
            filtered_df["name"].str.lower().str.contains(q, na=False)
            | filtered_df["description"].str.lower().str.contains(q, na=False)
        )
        filtered_df = filtered_df[mask]

    # Metro area
    if selected_metros:
        filtered_df = filtered_df[filtered_df["metro_area"].isin(selected_metros)]

    # Industry (matches against industry category keys)
    if selected_industries:
        industry_lower = [i.lower() for i in selected_industries]
        filtered_df = filtered_df[
            filtered_df["industry"].str.lower().apply(
                lambda ind: any(cat.lower() in ind for cat in selected_industries)
                if ind
                else False
            )
        ]

    # Pipeline stage
    if selected_stages:
        filtered_df = filtered_df[filtered_df["pipeline_stage"].isin(selected_stages)]

    # Employee range
    emp_has_data = filtered_df["emp_mid"].notna()
    if emp_has_data.any():
        filtered_df = filtered_df[
            ~emp_has_data
            | (
                (filtered_df["emp_mid"] >= emp_range[0])
                & (filtered_df["emp_mid"] <= emp_range[1])
            )
        ]

    # AI fit score
    score_has_data = filtered_df["ai_fit_score"].notna()
    filtered_df = filtered_df[
        ~score_has_data
        | (
            (filtered_df["ai_fit_score"] >= score_range[0])
            & (filtered_df["ai_fit_score"] <= score_range[1])
        )
    ]

    # Revenue bands
    if selected_rev_bands:
        selected_band_ranges = [
            (lo, hi) for lo, hi, label in REVENUE_BANDS if label in selected_rev_bands
        ]

        def _in_band(rev_mid):
            if rev_mid is None or pd.isna(rev_mid):
                return False
            for lo, hi in selected_band_ranges:
                if lo <= rev_mid <= hi:
                    return True
            return False

        filtered_df = filtered_df[filtered_df["rev_mid"].apply(_in_band)]

    # Sort
    if sort_by == "AI Fit Score (highest first)":
        filtered_df = filtered_df.sort_values("ai_fit_score", ascending=False, na_position="last")
    elif sort_by == "Offer Conversion Score (highest first)":
        filtered_df = filtered_df.sort_values(
            "offer_conversion_score", ascending=False, na_position="last"
        )
    elif sort_by == "Company Name (A-Z)":
        filtered_df = filtered_df.sort_values("name", ascending=True)
    elif sort_by == "Recently Added":
        filtered_df = filtered_df.sort_values("created_at", ascending=False, na_position="last")


st.markdown(f"**{len(filtered_df)} companies** match your filters")
st.markdown("")


# ---------------------------------------------------------------------------
# Results table
# ---------------------------------------------------------------------------

if filtered_df.empty:
    st.info("No companies match the current filters.")
else:
    # Build display dataframe
    display_rows = []
    for _, row in filtered_df.iterrows():
        score = row["ai_fit_score"]
        offer = row["offer_conversion_score"]
        stage_key = row["pipeline_stage"]

        # Score with color indicator
        if pd.notna(score):
            score_int = int(score)
            if score_int >= 70:
                score_display = f"🟢 {score_int}"
            elif score_int >= 40:
                score_display = f"🟡 {score_int}"
            else:
                score_display = f"🔴 {score_int}"
        else:
            score_display = "—"

        offer_display = int(offer) if pd.notna(offer) else "—"

        # Revenue display
        if pd.notna(row.get("estimated_revenue_min")) and pd.notna(row.get("estimated_revenue_max")):
            rev_str = format_revenue(
                int(row["estimated_revenue_min"]),
                int(row["estimated_revenue_max"]),
                bool(row.get("revenue_is_estimated", True)),
            )
        else:
            rev_str = "—"

        # Employee display
        if pd.notna(row.get("employee_count_min")) and pd.notna(row.get("employee_count_max")):
            emp_str = format_employees(int(row["employee_count_min"]), int(row["employee_count_max"]))
        elif pd.notna(row.get("employee_count_min")):
            emp_str = f"{int(row['employee_count_min'])}+"
        else:
            emp_str = "—"

        display_rows.append(
            {
                "_id": row["id"],
                "Company": row["name"],
                "Metro": row["metro_area"] or "—",
                "Industry": row["industry"] or "—",
                "Employees": emp_str,
                "Revenue": rev_str,
                "AI Fit": score_display,
                "Offer Score": offer_display,
                "Stage": get_stage_label(stage_key),
                "Primary Contact": row["primary_contact"] or "—",
            }
        )

    display_df = pd.DataFrame(display_rows)

    # Show table (without _id column visible)
    visible_cols = [c for c in display_df.columns if c != "_id"]
    st.dataframe(
        display_df[visible_cols],
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    st.markdown("")

    # Row actions: select a company to view detail
    action_col1, action_col2 = st.columns([2, 1])

    with action_col1:
        company_names = [row["Company"] for row in display_rows]
        selected_name = st.selectbox(
            "Open a company in Lead Detail:",
            options=["— Select a company —"] + company_names,
        )
        if selected_name and selected_name != "— Select a company —":
            # Find the id
            matching = [r for r in display_rows if r["Company"] == selected_name]
            if matching:
                if st.button("Open Lead Detail", type="primary"):
                    st.session_state["selected_company_id"] = matching[0]["_id"]
                    st.switch_page("pages/3_🏢_Lead_Detail.py")

    with action_col2:
        # CSV export
        export_df = display_df[visible_cols].copy()
        csv_buffer = io.StringIO()
        export_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Export to CSV",
            data=csv_buffer.getvalue(),
            file_name="leads_export.csv",
            mime="text/csv",
            use_container_width=True,
        )

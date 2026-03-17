"""
Lead Detail - Deep-dive view for a single company.
Do NOT call st.set_page_config() here — it is set in app.py.
"""
import json
import streamlit as st
from datetime import datetime

from database.db import get_session
from database.models import Company, Contact, Draft, SentEmail, Note, Activity
from utils.helpers import (
    PIPELINE_STAGES,
    get_stage_label,
    get_stage_color,
    format_revenue,
    format_employees,
    parse_json_field,
    compliance_warning,
)
from scoring.lead_scorer import score_company
from enrichment.enricher import enrich_and_save


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.warning("Please sign in to access this page.")
    st.page_link("app.py", label="Go to sign-in page")
    st.stop()

user = st.session_state["user"]


# ---------------------------------------------------------------------------
# Company selection guard
# ---------------------------------------------------------------------------

if "selected_company_id" not in st.session_state or st.session_state["selected_company_id"] is None:
    st.title("Lead Detail")
    st.info(
        "No company selected. Go to Lead Explorer, search for a company, and click 'Open Lead Detail'."
    )
    st.page_link("pages/2_🔎_Lead_Explorer.py", label="Go to Lead Explorer")
    st.stop()

company_id = st.session_state["selected_company_id"]


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

def load_company(cid: int):
    session = get_session()
    try:
        company = session.query(Company).filter(Company.id == cid).first()
        if not company:
            return None, [], [], []

        contacts = (
            session.query(Contact)
            .filter(Contact.company_id == cid)
            .order_by(Contact.is_decision_maker.desc(), Contact.created_at.asc())
            .all()
        )

        notes = (
            session.query(Note)
            .filter(Note.company_id == cid)
            .order_by(Note.created_at.desc())
            .all()
        )

        sent_emails = (
            session.query(SentEmail)
            .filter(SentEmail.company_id == cid)
            .order_by(SentEmail.sent_at.desc())
            .all()
        )

        # Serialize to dicts while session is open
        company_data = {
            "id": company.id,
            "name": company.name,
            "website": company.website or "",
            "city": company.city or "",
            "state": company.state or "",
            "metro_area": company.metro_area or "",
            "industry": company.industry or "",
            "sub_industry": company.sub_industry or "",
            "employee_count_min": company.employee_count_min,
            "employee_count_max": company.employee_count_max,
            "estimated_revenue_min": company.estimated_revenue_min,
            "estimated_revenue_max": company.estimated_revenue_max,
            "revenue_is_estimated": company.revenue_is_estimated,
            "ownership_style": company.ownership_style or "",
            "description": company.description or "",
            "probable_systems": parse_json_field(company.probable_systems),
            "pain_points": parse_json_field(company.pain_points),
            "ai_opportunities": parse_json_field(company.ai_opportunities),
            "ai_fit_score": company.ai_fit_score,
            "offer_conversion_score": company.offer_conversion_score,
            "ai_fit_reasons": parse_json_field(company.ai_fit_reasons),
            "offer_conversion_reasons": parse_json_field(company.offer_conversion_reasons),
            "pipeline_stage": company.pipeline_stage or "new_lead",
            "tags": company.tags or "",
            "enriched": company.enriched,
            "enriched_at": company.enriched_at,
            "source": company.source or "",
            "source_url": company.source_url or "",
            "created_at": company.created_at,
        }

        contacts_data = [
            {
                "id": ct.id,
                "first_name": ct.first_name or "",
                "last_name": ct.last_name or "",
                "title": ct.title or "",
                "email": ct.email or "",
                "phone": ct.phone or "",
                "is_decision_maker": ct.is_decision_maker,
                "do_not_contact": ct.do_not_contact,
                "suppression_reason": ct.suppression_reason or "",
            }
            for ct in contacts
        ]

        notes_data = [
            {
                "id": n.id,
                "content": n.content,
                "created_at": n.created_at,
            }
            for n in notes
        ]

        sent_data = [
            {
                "id": s.id,
                "subject": s.subject,
                "recipient_email": s.recipient_email,
                "sent_at": s.sent_at,
                "status": s.status,
                "replied_at": s.replied_at,
            }
            for s in sent_emails
        ]

        return company_data, contacts_data, notes_data, sent_data
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

company, contacts, notes, sent_emails = load_company(company_id)

if company is None:
    st.error(f"Company with ID {company_id} not found.")
    if st.button("Back to Lead Explorer"):
        del st.session_state["selected_company_id"]
        st.switch_page("pages/2_🔎_Lead_Explorer.py")
    st.stop()


# ---------------------------------------------------------------------------
# Helper: score color
# ---------------------------------------------------------------------------

def _score_color(score):
    if score is None:
        return "#AAAAAA"
    if score >= 70:
        return "#27ae60"
    if score >= 40:
        return "#e67e22"
    return "#e74c3c"


def _score_label(score):
    if score is None:
        return "Not scored"
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _log_activity(action: str, details: str = ""):
    session = get_session()
    try:
        act = Activity(
            user_id=user["id"],
            action=action,
            entity_type="company",
            entity_id=company_id,
            details=details,
        )
        session.add(act)
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Company header
# ---------------------------------------------------------------------------

back_col, title_col = st.columns([1, 8])
with back_col:
    if st.button("Back"):
        st.switch_page("pages/2_🔎_Lead_Explorer.py")

st.title(company["name"])

header_parts = []
if company["city"] or company["state"]:
    header_parts.append(f"{company['city']}, {company['state']}".strip(", "))
if company["metro_area"]:
    header_parts.append(company["metro_area"])
if company["industry"]:
    header_parts.append(company["industry"])
if company["website"]:
    header_parts.append(f"[{company['website']}]({company['website']})")

st.markdown("  |  ".join(header_parts) if header_parts else "_No location or industry data_")

if company["enriched"] and company["enriched_at"]:
    st.caption(f"Enriched {company['enriched_at'].strftime('%b %d, %Y')}")

st.divider()


# ---------------------------------------------------------------------------
# Action buttons row
# ---------------------------------------------------------------------------

act_col1, act_col2, act_col3, act_col4 = st.columns(4)

with act_col1:
    enrich_btn = st.button("Enrich with AI", use_container_width=True, type="primary")

with act_col2:
    rescore_btn = st.button("Re-Score", use_container_width=True)

with act_col3:
    draft_btn = st.button("Draft Outreach", use_container_width=True)

with act_col4:
    dnc_btn = st.button("Mark Do Not Contact", use_container_width=True, type="secondary")


# -- Handle Enrich
if enrich_btn:
    api_key = st.session_state.get("anthropic_api_key") or None
    with st.spinner("Enriching company data..."):
        session = get_session()
        try:
            result = enrich_and_save(session, company_id, api_key=api_key)
            _log_activity("enriched", f"Enriched company '{company['name']}'")
            st.success("Enrichment complete. Reload the page to see updated data.")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Enrichment failed: {e}")
        finally:
            session.close()

# -- Handle Re-Score
if rescore_btn:
    with st.spinner("Scoring..."):
        company_dict = {
            "name": company["name"],
            "industry": company["industry"],
            "description": company["description"],
            "employees": company["employee_count_min"],
            "revenue": company["estimated_revenue_min"],
            "pain_points": company["pain_points"],
            "probable_systems": company["probable_systems"],
            "ownership_style": company["ownership_style"],
        }
        results = score_company(company_dict)
        session = get_session()
        try:
            c = session.query(Company).filter(Company.id == company_id).first()
            if c:
                c.ai_fit_score = results["ai_fit_score"]
                c.ai_fit_reasons = json.dumps(results["ai_fit_reasons"])
                c.offer_conversion_score = results["offer_conversion_score"]
                c.offer_conversion_reasons = json.dumps(results["offer_conversion_reasons"])
                session.commit()
            _log_activity("scored", f"Re-scored '{company['name']}'")
            st.success(
                f"Scored: AI Fit = {results['ai_fit_score']}, "
                f"Offer Score = {results['offer_conversion_score']}"
            )
            st.cache_data.clear()
        finally:
            session.close()

# -- Handle Draft Outreach
if draft_btn:
    st.session_state["draft_company_id"] = company_id
    st.info(
        "Draft generation coming in the Messaging page. "
        "For now, use the Drafts section below — the full Messaging page will be added next."
    )

# -- Handle Do Not Contact
if dnc_btn:
    st.warning(
        f"Are you sure you want to mark **{company['name']}** as Do Not Contact? "
        "This will suppress all contacts at this company."
    )
    confirm_col1, confirm_col2 = st.columns(2)
    with confirm_col1:
        if st.button("Yes, mark Do Not Contact", type="primary"):
            session = get_session()
            try:
                ctcts = session.query(Contact).filter(Contact.company_id == company_id).all()
                for ct in ctcts:
                    ct.do_not_contact = True
                    ct.suppression_reason = "do_not_contact"
                session.commit()
                _log_activity("do_not_contact", f"Marked all contacts at '{company['name']}' as DNC")
                st.success("All contacts marked as Do Not Contact.")
                st.cache_data.clear()
            finally:
                session.close()
    with confirm_col2:
        if st.button("Cancel"):
            st.rerun()

st.markdown("")


# ---------------------------------------------------------------------------
# Main 2-column layout: Overview / Scores
# ---------------------------------------------------------------------------

left_col, right_col = st.columns([3, 2])

with left_col:
    # Company description
    st.subheader("Company Overview")
    if company["description"]:
        st.markdown(company["description"])
    else:
        st.caption("No description yet. Click 'Enrich with AI' to generate one.")

    # Probable systems
    if company["probable_systems"]:
        st.markdown("")
        st.markdown("**Probable Systems in Use**")
        tags_html = " ".join(
            f'<span style="background:#e8f0fe; color:#1a73e8; border-radius:12px; '
            f'padding:3px 10px; font-size:0.82rem; margin:2px; display:inline-block;">{s}</span>'
            for s in company["probable_systems"]
        )
        st.markdown(tags_html, unsafe_allow_html=True)

    # Pain points
    if company["pain_points"]:
        st.markdown("")
        st.markdown("**Known Pain Points**")
        for pt in company["pain_points"]:
            clean_pt = str(pt).replace("[Inferred] ", "")
            st.markdown(f"- {clean_pt}")

    # AI opportunities
    if company["ai_opportunities"]:
        st.markdown("")
        st.markdown("**AI Opportunities**")
        for opp in company["ai_opportunities"]:
            clean_opp = str(opp).replace("[Inferred] ", "")
            st.markdown(f"- {clean_opp}")

    # Company meta
    st.markdown("")
    with st.expander("Company Details"):
        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            if company["employee_count_min"] is not None and company["employee_count_max"] is not None:
                st.markdown(
                    f"**Employees:** {format_employees(company['employee_count_min'], company['employee_count_max'])}"
                )
            if company["estimated_revenue_min"] is not None and company["estimated_revenue_max"] is not None:
                st.markdown(
                    f"**Revenue:** {format_revenue(company['estimated_revenue_min'], company['estimated_revenue_max'], company['revenue_is_estimated'])}"
                )
            if company["ownership_style"]:
                st.markdown(f"**Ownership:** {company['ownership_style'].title()}")
        with meta_col2:
            if company["source"]:
                st.markdown(f"**Source:** {company['source']}")
            if company["tags"]:
                st.markdown(f"**Tags:** {company['tags']}")
            st.markdown(f"**Added:** {company['created_at'].strftime('%b %d, %Y') if company['created_at'] else '—'}")


with right_col:
    # Score cards
    st.subheader("Scores")

    ai_score = company["ai_fit_score"]
    offer_score = company["offer_conversion_score"]
    ai_color = _score_color(ai_score)
    offer_color = _score_color(offer_score)

    score_card1, score_card2 = st.columns(2)

    with score_card1:
        ai_display = str(ai_score) if ai_score is not None else "—"
        st.markdown(
            f"""
            <div style="border:1px solid #ddd; border-radius:8px; padding:16px; text-align:center;">
                <div style="color:#666; font-size:0.8rem; margin-bottom:4px;">AI Fit Score</div>
                <div style="color:{ai_color}; font-size:2.8rem; font-weight:700; line-height:1;">{ai_display}</div>
                <div style="color:{ai_color}; font-size:0.8rem; margin-top:4px;">{_score_label(ai_score)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with score_card2:
        offer_display = str(offer_score) if offer_score is not None else "—"
        st.markdown(
            f"""
            <div style="border:1px solid #ddd; border-radius:8px; padding:16px; text-align:center;">
                <div style="color:#666; font-size:0.8rem; margin-bottom:4px;">Offer Score</div>
                <div style="color:{offer_color}; font-size:2.8rem; font-weight:700; line-height:1;">{offer_display}</div>
                <div style="color:{offer_color}; font-size:0.8rem; margin-top:4px;">{_score_label(offer_score)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Score reasons
    if company["ai_fit_reasons"]:
        st.markdown("")
        with st.expander("AI Fit Score Reasons", expanded=True):
            for reason in company["ai_fit_reasons"]:
                st.markdown(f"- {reason}")

    if company["offer_conversion_reasons"]:
        with st.expander("Offer Score Reasons"):
            for reason in company["offer_conversion_reasons"]:
                st.markdown(f"- {reason}")

    # Pipeline stage selector
    st.markdown("")
    st.markdown("**Pipeline Stage**")
    stage_keys = [k for k, _ in PIPELINE_STAGES]
    stage_labels = [get_stage_label(k) for k in stage_keys]
    current_idx = stage_keys.index(company["pipeline_stage"]) if company["pipeline_stage"] in stage_keys else 0

    new_stage_label = st.selectbox(
        "Update pipeline stage",
        options=stage_labels,
        index=current_idx,
        label_visibility="collapsed",
    )
    new_stage_key = stage_keys[stage_labels.index(new_stage_label)]

    if new_stage_key != company["pipeline_stage"]:
        if st.button("Save Stage Update", type="primary"):
            session = get_session()
            try:
                c = session.query(Company).filter(Company.id == company_id).first()
                if c:
                    old_stage = c.pipeline_stage
                    c.pipeline_stage = new_stage_key
                    session.commit()
                    _log_activity(
                        "stage_changed",
                        f"Stage: {get_stage_label(old_stage)} -> {get_stage_label(new_stage_key)}",
                    )
                    st.success(f"Stage updated to: {new_stage_label}")
                    st.cache_data.clear()
                    st.rerun()
            finally:
                session.close()

    # Tags editor
    st.markdown("")
    st.markdown("**Tags**")
    current_tags = company["tags"]
    new_tags = st.text_input(
        "Edit tags (comma-separated)",
        value=current_tags,
        label_visibility="collapsed",
        placeholder="e.g. hot-lead, chicago, hvac",
    )
    if new_tags != current_tags:
        if st.button("Save Tags"):
            session = get_session()
            try:
                c = session.query(Company).filter(Company.id == company_id).first()
                if c:
                    c.tags = new_tags
                    session.commit()
                    st.success("Tags saved.")
                    st.cache_data.clear()
                    st.rerun()
            finally:
                session.close()


st.divider()


# ---------------------------------------------------------------------------
# Contacts section
# ---------------------------------------------------------------------------

st.subheader("Contacts")

if contacts:
    for ct in contacts:
        full_name = f"{ct['first_name']} {ct['last_name']}".strip() or "Unnamed Contact"
        dm_badge = " 🏅 Decision Maker" if ct["is_decision_maker"] else ""
        dnc_badge = " 🚫 Do Not Contact" if ct["do_not_contact"] else ""
        label = f"**{full_name}**{dm_badge}{dnc_badge}"
        if ct["title"]:
            label += f" — {ct['title']}"

        with st.container():
            ct_col1, ct_col2, ct_col3 = st.columns([3, 2, 1])
            with ct_col1:
                st.markdown(label)
                if ct["email"]:
                    st.caption(ct["email"])
                if ct["phone"]:
                    st.caption(ct["phone"])
            with ct_col2:
                if ct["suppression_reason"] and ct["do_not_contact"]:
                    st.caption(f"Suppressed: {ct['suppression_reason']}")
            with ct_col3:
                if not ct["do_not_contact"]:
                    if st.button("DNC", key=f"dnc_{ct['id']}", help="Mark as Do Not Contact"):
                        session = get_session()
                        try:
                            contact = session.query(Contact).filter(Contact.id == ct["id"]).first()
                            if contact:
                                contact.do_not_contact = True
                                contact.suppression_reason = "do_not_contact"
                                session.commit()
                                _log_activity("do_not_contact", f"Marked contact {full_name} as DNC")
                                st.cache_data.clear()
                                st.rerun()
                        finally:
                            session.close()
                else:
                    if st.button("Restore", key=f"restore_{ct['id']}", help="Remove DNC flag"):
                        session = get_session()
                        try:
                            contact = session.query(Contact).filter(Contact.id == ct["id"]).first()
                            if contact:
                                contact.do_not_contact = False
                                contact.suppression_reason = None
                                session.commit()
                                st.cache_data.clear()
                                st.rerun()
                        finally:
                            session.close()
else:
    st.caption("No contacts yet.")

# Add contact form
with st.expander("Add Contact"):
    with st.form("add_contact_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        new_first = c1.text_input("First Name")
        new_last = c2.text_input("Last Name")
        c3, c4 = st.columns(2)
        new_title = c3.text_input("Title")
        new_email = c4.text_input("Email")
        c5, c6 = st.columns(2)
        new_phone = c5.text_input("Phone")
        new_dm = c6.checkbox("Decision Maker")
        submitted = st.form_submit_button("Add Contact")

        if submitted:
            if not new_first and not new_last:
                st.warning("Please enter at least a first or last name.")
            else:
                session = get_session()
                try:
                    new_contact = Contact(
                        company_id=company_id,
                        first_name=new_first.strip() or None,
                        last_name=new_last.strip() or None,
                        title=new_title.strip() or None,
                        email=new_email.strip() or None,
                        phone=new_phone.strip() or None,
                        is_decision_maker=new_dm,
                        do_not_contact=False,
                    )
                    session.add(new_contact)
                    session.commit()
                    _log_activity(
                        "contact_added",
                        f"Added contact: {new_first} {new_last} ({new_title})",
                    )
                    st.success(f"Contact added: {new_first} {new_last}")
                    st.cache_data.clear()
                    st.rerun()
                finally:
                    session.close()

st.divider()


# ---------------------------------------------------------------------------
# Notes section
# ---------------------------------------------------------------------------

st.subheader("Notes")

if notes:
    for note in notes:
        ts = note["created_at"]
        ts_str = ts.strftime("%b %d, %Y %I:%M %p") if isinstance(ts, datetime) else str(ts)
        st.markdown(
            f"<div style='background:#f8f9fa; border-left:3px solid #dee2e6; "
            f"padding:10px 14px; border-radius:4px; margin-bottom:8px;'>"
            f"<div style='font-size:0.78rem; color:#888; margin-bottom:4px;'>{ts_str}</div>"
            f"{note['content']}"
            f"</div>",
            unsafe_allow_html=True,
        )
else:
    st.caption("No notes yet.")

# Add note form
with st.form("add_note_form", clear_on_submit=True):
    new_note_text = st.text_area("Add a note", placeholder="Type your note here...", height=90)
    note_submitted = st.form_submit_button("Save Note")
    if note_submitted:
        if new_note_text.strip():
            session = get_session()
            try:
                note_obj = Note(
                    company_id=company_id,
                    user_id=user["id"],
                    content=new_note_text.strip(),
                )
                session.add(note_obj)
                session.commit()
                _log_activity("note_added", f"Note added to '{company['name']}'")
                st.success("Note saved.")
                st.cache_data.clear()
                st.rerun()
            finally:
                session.close()
        else:
            st.warning("Note cannot be empty.")

st.divider()


# ---------------------------------------------------------------------------
# Outreach timeline
# ---------------------------------------------------------------------------

st.subheader("Outreach Timeline")

if sent_emails:
    st.markdown(compliance_warning())
    st.markdown("")
    for email in sent_emails:
        sent_at_str = (
            email["sent_at"].strftime("%b %d, %Y %I:%M %p")
            if isinstance(email["sent_at"], datetime)
            else str(email["sent_at"])
        )
        replied_str = ""
        if email["replied_at"]:
            replied_str = (
                f" — Replied {email['replied_at'].strftime('%b %d, %Y')}"
                if isinstance(email["replied_at"], datetime)
                else ""
            )

        status_icon = {
            "sent": "📤",
            "delivered": "📬",
            "replied": "💬",
            "bounced": "⚠️",
        }.get(email["status"], "•")

        st.markdown(
            f"{status_icon} **{email['subject']}**  \n"
            f"<span style='color:#888; font-size:0.82rem;'>To: {email['recipient_email']} | "
            f"{sent_at_str}{replied_str} | Status: {email['status'].title()}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("")
else:
    st.caption("No outreach sent to this company yet.")

st.divider()
st.caption(compliance_warning())

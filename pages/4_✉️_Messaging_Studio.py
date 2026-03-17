"""
Messaging Studio — Draft generation and review.
No st.set_page_config() here; it lives in app.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import streamlit as st

from database.db import get_session, init_db
from database.models import Company, Contact, Draft
from utils.helpers import compliance_warning, PIPELINE_STAGES, get_stage_label

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MESSAGE_TYPES = [
    ("Initial Email",     "email_initial",  1),
    ("Follow-Up 1",       "email_followup", 1),
    ("Follow-Up 2",       "email_followup", 2),
    ("Follow-Up 3",       "email_followup", 3),
    ("LinkedIn Message",  "linkedin",       0),
    ("Call Script",       "call_script",    0),
]

TONE_OPTIONS = ["Practical", "Friendly", "Direct", "Consultative"]


def _company_to_dict(c: Company) -> dict:
    import json
    def _parse(val):
        if val is None:
            return []
        if isinstance(val, list):
            return val
        try:
            return json.loads(val)
        except Exception:
            return []

    return {
        "id": c.id,
        "name": c.name,
        "industry": c.industry or "",
        "description": c.description or "",
        "pain_points": _parse(c.pain_points),
        "ai_opportunities": _parse(c.ai_opportunities),
        "website": c.website or "",
    }


def _contact_to_dict(ct: Contact) -> dict:
    return {
        "id": ct.id,
        "first_name": ct.first_name or "",
        "last_name": ct.last_name or "",
        "name": f"{ct.first_name or ''} {ct.last_name or ''}".strip(),
        "title": ct.title or "",
        "email": ct.email or "",
    }


def _generate(company_dict: dict, contact_dict: dict, msg_type_label: str, tone: str, api_key: str) -> dict:
    """Call the appropriate generator. Returns a result dict."""
    from messaging.drafts import (
        generate_email_draft,
        generate_followup,
        generate_linkedin_message,
        generate_call_script,
        generate_draft_fallback,
    )

    tone_lower = tone.lower()

    try:
        if msg_type_label == "Initial Email":
            if api_key:
                return generate_email_draft(company_dict, contact_dict, api_key, tone_lower)
            return generate_draft_fallback(company_dict, contact_dict, "email_initial")

        elif msg_type_label in ("Follow-Up 1", "Follow-Up 2", "Follow-Up 3"):
            fu_num = int(msg_type_label.split()[-1])
            if api_key:
                return generate_followup(company_dict, contact_dict, api_key, fu_num)
            return generate_draft_fallback(company_dict, contact_dict, "email_followup")

        elif msg_type_label == "LinkedIn Message":
            if api_key:
                return generate_linkedin_message(company_dict, contact_dict, api_key)
            return generate_draft_fallback(company_dict, contact_dict, "linkedin")

        elif msg_type_label == "Call Script":
            if api_key:
                return generate_call_script(company_dict, contact_dict, api_key)
            return generate_draft_fallback(company_dict, contact_dict, "call_script")

    except Exception as e:
        return {"error": str(e)}

    return {"error": "Unknown message type."}


def _draft_type_key(msg_type_label: str) -> str:
    mapping = {
        "Initial Email": "email_initial",
        "Follow-Up 1": "email_followup",
        "Follow-Up 2": "email_followup",
        "Follow-Up 3": "email_followup",
        "LinkedIn Message": "linkedin_message",
        "Call Script": "call_script",
    }
    return mapping.get(msg_type_label, "email_initial")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Messaging Studio")
st.caption("Generate, edit, and save outreach drafts for review before sending.")

init_db()
session = get_session()

try:
    companies = session.query(Company).order_by(Company.name).all()

    if not companies:
        st.info("No companies in the database yet. Add companies first via the Lead Discovery page.")
        st.stop()

    # -----------------------------------------------------------------------
    # Company selector — pre-select from session state if set by Lead Detail
    # -----------------------------------------------------------------------
    company_names = [c.name for c in companies]
    company_map = {c.name: c for c in companies}

    preselect_name = None
    if "messaging_company_id" in st.session_state:
        for c in companies:
            if c.id == st.session_state["messaging_company_id"]:
                preselect_name = c.name
                break

    default_idx = company_names.index(preselect_name) if preselect_name and preselect_name in company_names else 0

    col1, col2 = st.columns(2)
    with col1:
        selected_company_name = st.selectbox("Company", company_names, index=default_idx)
    selected_company = company_map[selected_company_name]

    # -----------------------------------------------------------------------
    # Contact selector
    # -----------------------------------------------------------------------
    contacts = [ct for ct in selected_company.contacts if not ct.do_not_contact]

    with col2:
        if not contacts:
            st.selectbox("Contact", ["No contacts — add one first"], disabled=True)
            st.stop()

        contact_labels = [
            f"{ct.first_name or ''} {ct.last_name or ''}".strip() + (f" <{ct.email}>" if ct.email else "")
            for ct in contacts
        ]
        selected_contact_idx = st.selectbox("Contact", range(len(contacts)), format_func=lambda i: contact_labels[i])
        selected_contact = contacts[selected_contact_idx]

    # -----------------------------------------------------------------------
    # Message type and tone
    # -----------------------------------------------------------------------
    col3, col4 = st.columns(2)
    with col3:
        msg_type_label = st.selectbox("Message Type", [m[0] for m in MESSAGE_TYPES])
    with col4:
        tone = st.selectbox("Tone", TONE_OPTIONS, index=0)

    # API key from session state
    api_key = st.session_state.get("anthropic_api_key", "")
    if not api_key:
        st.caption("No Anthropic API key set — will use template fallback. Add your key in Settings.")

    # -----------------------------------------------------------------------
    # Generate button
    # -----------------------------------------------------------------------
    generate_clicked = st.button("Generate Draft", type="primary", use_container_width=True)

    if generate_clicked:
        with st.spinner("Generating..."):
            company_dict = _company_to_dict(selected_company)
            contact_dict = _contact_to_dict(selected_contact)
            result = _generate(company_dict, contact_dict, msg_type_label, tone, api_key)

        if "error" in result:
            st.error(f"Generation failed: {result['error']}")
        else:
            st.session_state["current_draft_result"] = result
            st.session_state["current_draft_company_id"] = selected_company.id
            st.session_state["current_draft_contact_id"] = selected_contact.id
            st.session_state["current_draft_type"] = msg_type_label
            st.session_state["current_draft_tone"] = tone

    # -----------------------------------------------------------------------
    # Show generated draft for editing
    # -----------------------------------------------------------------------
    result = st.session_state.get("current_draft_result")
    if (
        result
        and st.session_state.get("current_draft_company_id") == selected_company.id
        and st.session_state.get("current_draft_contact_id") == selected_contact.id
    ):
        st.divider()
        st.subheader("Review & Edit Draft")

        # Compliance warning
        st.warning(compliance_warning(), icon=None)

        draft_type_key = _draft_type_key(st.session_state.get("current_draft_type", msg_type_label))
        is_email = draft_type_key in ("email_initial", "email_followup")
        is_linkedin = draft_type_key == "linkedin_message"
        is_call = draft_type_key == "call_script"

        if is_email:
            subject_val = result.get("subject", "")
            edited_subject = st.text_input("Subject Line", value=subject_val, key="edit_subject")
            body_val = result.get("body", "")
            edited_body = st.text_area("Email Body", value=body_val, height=300, key="edit_body")

        elif is_linkedin:
            body_val = result.get("body", "")
            char_count = len(body_val)
            edited_body = st.text_area(
                f"LinkedIn Message ({char_count}/300 chars)",
                value=body_val,
                height=150,
                key="edit_body",
            )
            edited_subject = ""
            if len(edited_body) > 300:
                st.error("LinkedIn messages must be 300 characters or fewer.")

        elif is_call:
            script_val = result.get("script", result.get("body", ""))
            edited_body = st.text_area("Call Script", value=script_val, height=400, key="edit_body")
            edited_subject = ""

        else:
            body_val = result.get("body", "")
            edited_body = st.text_area("Content", value=body_val, height=300, key="edit_body")
            edited_subject = ""

        col_regen, col_save = st.columns(2)

        with col_regen:
            if st.button("Regenerate", use_container_width=True):
                with st.spinner("Regenerating..."):
                    company_dict = _company_to_dict(selected_company)
                    contact_dict = _contact_to_dict(selected_contact)
                    new_result = _generate(
                        company_dict, contact_dict,
                        st.session_state.get("current_draft_type", msg_type_label),
                        st.session_state.get("current_draft_tone", tone),
                        api_key,
                    )
                if "error" in new_result:
                    st.error(new_result["error"])
                else:
                    st.session_state["current_draft_result"] = new_result
                    st.rerun()

        with col_save:
            save_clicked = st.button("Save as Draft", type="primary", use_container_width=True)

        if save_clicked:
            body_to_save = edited_body
            subject_to_save = edited_subject if is_email else None

            user_id = st.session_state.get("user_id")
            draft = Draft(
                company_id=selected_company.id,
                contact_id=selected_contact.id,
                user_id=user_id,
                draft_type=draft_type_key,
                subject=subject_to_save,
                body=body_to_save,
                tone=st.session_state.get("current_draft_tone", tone).lower(),
                status="draft",
            )
            try:
                session.add(draft)
                session.commit()
                st.success("Draft saved successfully.")
                st.session_state.pop("current_draft_result", None)
            except Exception as e:
                session.rollback()
                st.error(f"Failed to save draft: {e}")

    # -----------------------------------------------------------------------
    # Saved drafts section
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader(f"Saved Drafts for {selected_company.name}")

    company_drafts = (
        session.query(Draft)
        .filter(Draft.company_id == selected_company.id)
        .order_by(Draft.created_at.desc())
        .all()
    )

    if not company_drafts:
        st.caption("No drafts saved for this company yet.")
    else:
        for d in company_drafts:
            contact_label = ""
            if d.contact:
                contact_label = f"{d.contact.first_name or ''} {d.contact.last_name or ''}".strip()

            status_color = {"draft": "blue", "approved": "green", "sent": "gray", "failed": "red"}.get(d.status, "blue")
            header = f"**{d.draft_type.replace('_', ' ').title()}** — :{status_color}[{d.status.upper()}] — {d.created_at.strftime('%b %d, %Y %H:%M')}"
            if contact_label:
                header += f" | {contact_label}"

            with st.expander(header, expanded=False):
                if d.subject:
                    st.text_input("Subject", value=d.subject, key=f"draft_subj_{d.id}", disabled=True)

                new_body = st.text_area("Body", value=d.body, height=250, key=f"draft_body_{d.id}")

                col_load, col_del = st.columns(2)
                with col_load:
                    if st.button("Load for Editing", key=f"load_{d.id}"):
                        if d.draft_type == "email_initial":
                            st.session_state["current_draft_result"] = {"subject": d.subject or "", "body": d.body}
                            st.session_state["current_draft_type"] = "Initial Email"
                        elif d.draft_type == "email_followup":
                            st.session_state["current_draft_result"] = {"subject": d.subject or "", "body": d.body}
                            st.session_state["current_draft_type"] = "Follow-Up 1"
                        elif d.draft_type == "linkedin_message":
                            st.session_state["current_draft_result"] = {"body": d.body}
                            st.session_state["current_draft_type"] = "LinkedIn Message"
                        elif d.draft_type == "call_script":
                            st.session_state["current_draft_result"] = {"script": d.body}
                            st.session_state["current_draft_type"] = "Call Script"
                        st.session_state["current_draft_company_id"] = selected_company.id
                        st.session_state["current_draft_contact_id"] = d.contact_id
                        st.rerun()

                with col_del:
                    if st.button("Delete", key=f"del_{d.id}", type="secondary"):
                        try:
                            session.delete(d)
                            session.commit()
                            st.success("Draft deleted.")
                            st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Error: {e}")

                # Allow saving edits to body inline
                if new_body != d.body:
                    if st.button("Save Body Edits", key=f"save_edit_{d.id}"):
                        try:
                            d.body = new_body
                            d.updated_at = datetime.utcnow()
                            session.commit()
                            st.success("Saved.")
                            st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Error: {e}")

finally:
    session.close()

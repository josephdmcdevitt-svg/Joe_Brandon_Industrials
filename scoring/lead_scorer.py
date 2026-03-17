"""
Lead scoring module for AI Systems Audit & Deployment Blueprint consulting offer.
Scores SMB companies on AI fit and likelihood to purchase the audit.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_lower(*fields) -> str:
    """Concatenate and lowercase multiple string or list fields for keyword scanning."""
    parts = []
    for field in fields:
        if isinstance(field, str):
            parts.append(field.lower())
        elif isinstance(field, list):
            parts.append(" ".join(str(x) for x in field).lower())
    return " ".join(parts)


def _count_keywords(text: str, keywords: list[str]) -> list[str]:
    """Return the subset of keywords that appear in text."""
    return [kw for kw in keywords if kw.lower() in text]


# ---------------------------------------------------------------------------
# score_ai_fit
# ---------------------------------------------------------------------------

def score_ai_fit(company: dict) -> tuple[int, list[str]]:
    """
    Rule-based AI fit score (0-100) for the AI Systems Audit offer.

    Returns
    -------
    (score, top_5_reasons)
        score       : integer 0-100
        top_5_reasons : list of up to 5 human-readable reason strings
    """
    score = 0
    reason_candidates: list[tuple[int, str]] = []  # (points_earned, reason_text)

    industry = (company.get("industry") or "").lower()
    description = (company.get("description") or "").lower()
    pain_points = company.get("pain_points") or []
    probable_systems = company.get("probable_systems") or []
    employees_raw = company.get("employees") or company.get("employee_count") or 0
    revenue_raw = company.get("revenue") or company.get("annual_revenue") or 0

    try:
        employees = int(employees_raw)
    except (TypeError, ValueError):
        employees = 0

    try:
        revenue = float(str(revenue_raw).replace(",", "").replace("$", "").replace("K", "000").replace("M", "000000"))
    except (TypeError, ValueError):
        revenue = 0.0

    # ------------------------------------------------------------------
    # 1. Industry fit (max 20 pts)
    # ------------------------------------------------------------------
    construction_trades_kw = ["construction", "trades", "contractor", "plumbing", "electrical", "hvac",
                               "roofing", "landscaping", "painting", "flooring", "remodeling", "excavation"]
    healthcare_kw = ["healthcare", "medical", "dental", "chiropractic", "optometry", "therapy",
                     "physical therapy", "mental health", "clinic", "practice", "physician"]
    professional_kw = ["accounting", "law", "legal", "consulting", "marketing agency", "staffing",
                       "recruiting", "insurance", "real estate", "financial advisory", "cpa"]
    franchise_kw = ["franchise", "franchisee", "franchised"]

    if any(kw in industry for kw in construction_trades_kw):
        pts = 20
        score += pts
        reason_candidates.append((pts, f"Industry ({industry.title()}) is a top fit — trades and construction are highly operationally intensive"))
    elif any(kw in industry for kw in healthcare_kw):
        pts = 20
        score += pts
        reason_candidates.append((pts, f"Healthcare practice industry is a top fit — high scheduling, billing, and intake complexity"))
    elif any(kw in industry for kw in professional_kw):
        pts = 18
        score += pts
        reason_candidates.append((pts, f"Professional services industry is a strong fit — time tracking, billing, and client management are common pain points"))
    elif any(kw in industry for kw in franchise_kw):
        pts = 17
        score += pts
        reason_candidates.append((pts, f"Franchise operator is a strong fit — multi-location coordination and SOP enforcement drive AI value"))
    else:
        pts = 10
        score += pts
        reason_candidates.append((pts, f"Industry ({industry.title() if industry else 'Unknown'}) has moderate AI fit potential"))

    # ------------------------------------------------------------------
    # 2. Employee sweet spot (max 15 pts)
    # ------------------------------------------------------------------
    if 5 <= employees <= 20:
        pts = 15
        score += pts
        reason_candidates.append((pts, f"Employee count ({employees}) is in the ideal 5-20 range — small enough to need systems, large enough to benefit"))
    elif 21 <= employees <= 50:
        pts = 10
        score += pts
        reason_candidates.append((pts, f"Employee count ({employees}) is slightly above target but still operationally relevant"))
    elif 1 <= employees <= 4:
        pts = 8
        score += pts
        reason_candidates.append((pts, f"Employee count ({employees}) is below the sweet spot — lower complexity but owner is likely overwhelmed"))
    elif employees > 50:
        pts = 5
        score += pts
        reason_candidates.append((pts, f"Employee count ({employees}) is above the SMB target range — may have existing systems in place"))
    else:
        reason_candidates.append((0, "Employee count unknown — cannot assess operational complexity"))

    # ------------------------------------------------------------------
    # 3. Revenue sweet spot (max 10 pts)
    # ------------------------------------------------------------------
    if 500_000 <= revenue <= 5_000_000:
        pts = 10
        score += pts
        reason_candidates.append((pts, f"Revenue (${revenue:,.0f}) is in the ideal $500K-$5M range — has budget and operational scale to benefit"))
    elif 5_000_000 < revenue <= 10_000_000:
        pts = 7
        score += pts
        reason_candidates.append((pts, f"Revenue (${revenue:,.0f}) is above the core target — still benefits but may have more resources already"))
    elif 0 < revenue < 500_000:
        pts = 4
        score += pts
        reason_candidates.append((pts, f"Revenue (${revenue:,.0f}) is below $500K — budget may be a barrier"))
    elif revenue > 10_000_000:
        pts = 5
        score += pts
        reason_candidates.append((pts, f"Revenue (${revenue:,.0f}) exceeds $10M — larger org may need different engagement model"))
    else:
        reason_candidates.append((0, "Revenue data unknown — cannot assess budget fit"))

    # ------------------------------------------------------------------
    # 4. Workflow complexity signals (max 20 pts)
    # ------------------------------------------------------------------
    workflow_keywords = [
        "manual", "spreadsheet", "paper", "scheduling", "dispatch",
        "invoicing", "billing", "job costing", "quoting", "estimates",
        "subcontractor", "payroll"
    ]
    scan_text = _text_lower(description, pain_points)
    found_workflow_kw = _count_keywords(scan_text, workflow_keywords)
    workflow_pts = min(len(found_workflow_kw) * 2, 20)
    score += workflow_pts
    if found_workflow_kw:
        reason_candidates.append((workflow_pts, f"Workflow complexity signals detected: {', '.join(found_workflow_kw[:5])} — strong indicators of manual process burden"))
    else:
        reason_candidates.append((0, "No specific workflow complexity keywords found in description or pain points"))

    # ------------------------------------------------------------------
    # 5. System fragmentation (max 10 pts)
    # ------------------------------------------------------------------
    systems_text = _text_lower(probable_systems)
    system_pts = 0
    system_notes = []

    if "quickbooks" in systems_text:
        system_pts += 3
        system_notes.append("QuickBooks")
    if "google sheets" in systems_text:
        system_pts += 3
        system_notes.append("Google Sheets")
    if "paper" in systems_text:
        system_pts += 3
        system_notes.append("paper-based processes")
    if "excel" in systems_text:
        system_pts += 2
        system_notes.append("Excel")
    if "manual" in systems_text:
        system_pts += 2
        system_notes.append("manual tracking")

    if len(probable_systems) >= 3:
        system_pts += 2
        system_notes.append(f"{len(probable_systems)} fragmented tools listed")

    system_pts = min(system_pts, 10)
    score += system_pts
    if system_notes:
        reason_candidates.append((system_pts, f"System fragmentation confirmed: {', '.join(system_notes)} — clear integration opportunity"))
    else:
        reason_candidates.append((0, "No system fragmentation signals found"))

    # ------------------------------------------------------------------
    # 6. Owner workload signals (max 10 pts)
    # ------------------------------------------------------------------
    owner_keywords = ["owner", "founder", "hands-on", "wearing many hats", "small team", "office manager"]
    found_owner_kw = _count_keywords(_text_lower(description), owner_keywords)
    owner_pts = min(len(found_owner_kw) * 2, 10)
    score += owner_pts
    if found_owner_kw:
        reason_candidates.append((owner_pts, f"Owner workload signals present: {', '.join(found_owner_kw)} — decision maker is likely buried in operations"))

    # ------------------------------------------------------------------
    # 7. Multi-location (max 5 pts)
    # ------------------------------------------------------------------
    multiloc_keywords = ["locations", "franchise", "branches", "multiple"]
    found_multiloc = _count_keywords(_text_lower(description, company.get("notes") or ""), multiloc_keywords)
    if found_multiloc:
        pts = 5
        score += pts
        reason_candidates.append((pts, f"Multi-location signals found: {', '.join(found_multiloc)} — coordination overhead amplifies AI value"))

    # ------------------------------------------------------------------
    # 8. Customer-facing volume (max 10 pts)
    # ------------------------------------------------------------------
    customer_keywords = ["clients", "patients", "customers", "appointments", "recurring", "bookings"]
    found_customer_kw = _count_keywords(scan_text, customer_keywords)
    customer_pts = min(len(found_customer_kw) * 2, 10)
    score += customer_pts
    if found_customer_kw:
        reason_candidates.append((customer_pts, f"Customer-facing volume signals: {', '.join(found_customer_kw)} — high transaction frequency supports automation ROI"))

    # ------------------------------------------------------------------
    # Cap total score and select top 5 reasons
    # ------------------------------------------------------------------
    score = min(score, 100)
    reason_candidates.sort(key=lambda x: x[0], reverse=True)
    top_5_reasons = [r for _, r in reason_candidates[:5]]

    return score, top_5_reasons


# ---------------------------------------------------------------------------
# score_offer_conversion
# ---------------------------------------------------------------------------

def score_offer_conversion(company: dict) -> tuple[int, list[str]]:
    """
    Predicts likelihood this company would purchase the AI Systems Audit.
    Rule-based score 0-100.

    Returns
    -------
    (score, top_3_reasons)
    """
    score = 0
    reason_candidates: list[tuple[int, str]] = []

    industry = (company.get("industry") or "").lower()
    description = (company.get("description") or "").lower()
    ownership_style = (company.get("ownership_style") or "").lower()
    pain_points = company.get("pain_points") or []
    probable_systems = company.get("probable_systems") or []

    employees_raw = company.get("employees") or company.get("employee_count") or 0
    try:
        employees = int(employees_raw)
    except (TypeError, ValueError):
        employees = 0

    # ------------------------------------------------------------------
    # 1. Owner-operated signal (max 25 pts)
    # ------------------------------------------------------------------
    owner_kw = ["owner", "founder", "family"]
    owner_text = _text_lower(ownership_style, description)
    found_owner = _count_keywords(owner_text, owner_kw)
    owner_pts = min(len(found_owner) * 9, 25)
    score += owner_pts
    if found_owner:
        reason_candidates.append((owner_pts, f"Owner-operated signals ({', '.join(found_owner)}) mean the decision maker feels the pain directly and can say yes on the spot"))
    else:
        reason_candidates.append((0, "No clear owner-operated signal — decision process may involve multiple stakeholders"))

    # ------------------------------------------------------------------
    # 2. Pain severity (max 25 pts)
    # ------------------------------------------------------------------
    pain_count = len(pain_points) if isinstance(pain_points, list) else 0
    pain_pts = min(pain_count * 5, 25)
    score += pain_pts
    if pain_count > 0:
        reason_candidates.append((pain_pts, f"{pain_count} documented pain point(s) — more articulated pain means higher urgency to act"))
    else:
        reason_candidates.append((0, "No pain points documented — harder to establish urgency in outreach"))

    # ------------------------------------------------------------------
    # 3. Company size fit (max 20 pts)
    # ------------------------------------------------------------------
    if 5 <= employees <= 20:
        pts = 20
        score += pts
        reason_candidates.append((pts, f"{employees} employees puts this squarely in the owner-operator zone where one person is doing too much"))
    elif 21 <= employees <= 50:
        pts = 12
        score += pts
        reason_candidates.append((pts, f"{employees} employees — slightly beyond core target but still has SMB buying behavior"))
    elif 1 <= employees <= 4:
        pts = 10
        score += pts
        reason_candidates.append((pts, f"{employees} employees — very small, owner may be budget-constrained but highly motivated"))
    elif employees > 50:
        pts = 6
        score += pts
        reason_candidates.append((pts, f"{employees} employees — larger company may have longer sales cycle or existing ops team"))
    else:
        reason_candidates.append((0, "Employee count unknown"))

    # ------------------------------------------------------------------
    # 4. Industry receptiveness (max 15 pts)
    # ------------------------------------------------------------------
    prof_services_kw = ["accounting", "law", "legal", "consulting", "marketing", "staffing",
                        "recruiting", "insurance", "financial", "cpa"]
    healthcare_kw = ["healthcare", "medical", "dental", "chiropractic", "therapy", "clinic", "practice"]
    trades_kw = ["construction", "trades", "contractor", "plumbing", "electrical", "hvac",
                 "roofing", "landscaping", "painting"]
    franchise_kw = ["franchise", "franchisee"]

    if any(kw in industry for kw in prof_services_kw) or any(kw in industry for kw in healthcare_kw):
        pts = 15
        score += pts
        reason_candidates.append((pts, "Professional services and healthcare buyers routinely purchase consulting — lower resistance to advisory spend"))
    elif any(kw in industry for kw in trades_kw):
        pts = 12
        score += pts
        reason_candidates.append((pts, "Trades companies are receptive when framed around cost savings and job efficiency — ROI message lands well"))
    elif any(kw in industry for kw in franchise_kw):
        pts = 10
        score += pts
        reason_candidates.append((pts, "Franchise operators understand investing in systems — familiar with consulting and process improvement spend"))
    else:
        pts = 7
        score += pts
        reason_candidates.append((pts, f"Industry ({industry.title() if industry else 'Unknown'}) has moderate consulting receptiveness"))

    # ------------------------------------------------------------------
    # 5. Digital sophistication gap (max 15 pts)
    # ------------------------------------------------------------------
    systems_text = _text_lower(probable_systems)
    gap_pts = 0
    gap_notes = []

    if "quickbooks" in systems_text:
        gap_pts += 5
        gap_notes.append("has QuickBooks (has budget, not fully digital)")
    if any(kw in systems_text for kw in ["paper", "spreadsheet", "excel", "google sheets"]):
        gap_pts += 5
        gap_notes.append("relying on manual/spreadsheet tools (clear upgrade gap)")
    if len(probable_systems) >= 3:
        gap_pts += 5
        gap_notes.append(f"using {len(probable_systems)} disconnected tools (fragmentation pain point)")

    gap_pts = min(gap_pts, 15)
    score += gap_pts
    if gap_notes:
        reason_candidates.append((gap_pts, f"Digital sophistication gap: {'; '.join(gap_notes)} — positioned to buy help, not build it themselves"))
    else:
        reason_candidates.append((0, "No clear digital sophistication gap detected"))

    # ------------------------------------------------------------------
    # Cap and return top 3 reasons
    # ------------------------------------------------------------------
    score = min(score, 100)
    reason_candidates.sort(key=lambda x: x[0], reverse=True)
    top_3_reasons = [r for _, r in reason_candidates[:3]]

    return score, top_3_reasons


# ---------------------------------------------------------------------------
# score_company
# ---------------------------------------------------------------------------

def score_company(company_dict: dict) -> dict:
    """
    Runs both scoring models against a single company dict.

    Returns
    -------
    {
        "ai_fit_score": int,
        "ai_fit_reasons": list[str],
        "offer_conversion_score": int,
        "offer_conversion_reasons": list[str]
    }
    """
    ai_fit_score, ai_fit_reasons = score_ai_fit(company_dict)
    offer_conversion_score, offer_conversion_reasons = score_offer_conversion(company_dict)

    return {
        "ai_fit_score": ai_fit_score,
        "ai_fit_reasons": ai_fit_reasons,
        "offer_conversion_score": offer_conversion_score,
        "offer_conversion_reasons": offer_conversion_reasons,
    }


# ---------------------------------------------------------------------------
# batch_score
# ---------------------------------------------------------------------------

def batch_score(session, company_ids: list[int] = None):
    """
    Scores all companies (or a specific list by ID) in the database.
    Updates ai_fit_score and offer_conversion_score fields on each Company record.

    Parameters
    ----------
    session      : SQLAlchemy session
    company_ids  : optional list of Company IDs to score; if None, scores all
    """
    from database.models import Company

    query = session.query(Company)
    if company_ids:
        query = query.filter(Company.id.in_(company_ids))

    companies = query.all()
    updated = 0

    for company in companies:
        company_dict = {
            "id": company.id,
            "name": getattr(company, "name", ""),
            "industry": getattr(company, "industry", ""),
            "description": getattr(company, "description", ""),
            "employees": getattr(company, "employees", None) or getattr(company, "employee_count", None),
            "revenue": getattr(company, "revenue", None) or getattr(company, "annual_revenue", None),
            "pain_points": getattr(company, "pain_points", []) or [],
            "probable_systems": getattr(company, "probable_systems", []) or [],
            "ownership_style": getattr(company, "ownership_style", ""),
            "notes": getattr(company, "notes", ""),
        }

        results = score_company(company_dict)

        if hasattr(company, "ai_fit_score"):
            company.ai_fit_score = results["ai_fit_score"]
        if hasattr(company, "ai_fit_reasons"):
            company.ai_fit_reasons = results["ai_fit_reasons"]
        if hasattr(company, "offer_conversion_score"):
            company.offer_conversion_score = results["offer_conversion_score"]
        if hasattr(company, "offer_conversion_reasons"):
            company.offer_conversion_reasons = results["offer_conversion_reasons"]

        updated += 1

    session.commit()
    return {"updated": updated, "total": len(companies)}

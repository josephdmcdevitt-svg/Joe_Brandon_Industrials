"""
Company enrichment module for AI Systems Audit & Deployment Blueprint.
Uses Claude API when available, falls back to rule-based templates.
"""

from __future__ import annotations
import json
from datetime import datetime


# ---------------------------------------------------------------------------
# Industry templates for fallback enrichment
# ---------------------------------------------------------------------------

_INDUSTRY_TEMPLATES = {
    "construction_trades": {
        "operational_bottlenecks": [
            "[Inferred] Job costing tracked in spreadsheets or not tracked at all",
            "[Inferred] Subcontractor invoices and change orders managed manually via text or email",
            "[Inferred] Scheduling and dispatch done via phone calls or group texts",
            "[Inferred] Material purchasing and vendor management done by memory or paper",
            "[Inferred] Estimates built from scratch each time with no standardized templates",
        ],
        "likely_current_tools": [
            "QuickBooks (or QuickBooks Online)",
            "Excel or Google Sheets for job tracking",
            "Paper-based forms for field crew",
            "Text/phone for scheduling",
            "Email for subcontractor coordination",
        ],
        "ai_opportunities": [
            "[Inferred] Automated job cost tracking linked to QuickBooks — saves 3-5 hrs/week on reconciliation",
            "[Inferred] AI-assisted estimate builder using past jobs as templates — saves 2-3 hrs per estimate",
            "[Inferred] Automated subcontractor invoice processing and approval workflow — reduces billing delays by 50%",
            "[Inferred] Scheduling assistant that auto-assigns crews based on location and availability — saves 1-2 hrs/day",
            "[Inferred] Field form digitization with auto-sync to QuickBooks — eliminates manual data entry",
        ],
        "outreach_framing": "[Inferred] Frame around job profitability visibility — most contractors don't know which jobs actually made money until months later. Position the audit as a way to find out where time and money are leaking.",
        "best_decision_maker": "Owner / General Contractor",
    },
    "healthcare": {
        "operational_bottlenecks": [
            "[Inferred] Scheduling done primarily by phone with high no-show rates",
            "[Inferred] Patient intake uses paper forms that get manually transcribed",
            "[Inferred] Billing reconciliation between EHR and QuickBooks is manual",
            "[Inferred] Insurance verification done manually for each patient",
            "[Inferred] Staff spends significant time on appointment reminders",
        ],
        "likely_current_tools": [
            "EHR system (e.g., Athena, Jane App, or similar)",
            "QuickBooks for bookkeeping",
            "Paper intake forms",
            "Phone-based scheduling",
            "Email for patient communications",
        ],
        "ai_opportunities": [
            "[Inferred] Automated appointment reminders via text/email — reduces no-shows by 30-40%",
            "[Inferred] Digital intake forms with auto-population into EHR — saves 10-15 min per patient",
            "[Inferred] AI-assisted insurance eligibility verification — eliminates manual lookups before appointments",
            "[Inferred] Automated billing reconciliation between EHR and QuickBooks — saves 4-6 hrs/week",
            "[Inferred] Patient reactivation campaigns triggered by inactivity — increases recurring revenue",
        ],
        "outreach_framing": "[Inferred] Frame around front-desk efficiency and patient throughput. Most practice owners are losing revenue to no-shows and admin bottlenecks. Position the audit as a way to reclaim clinical capacity without hiring more staff.",
        "best_decision_maker": "Practice Owner / Office Manager",
    },
    "professional_services": {
        "operational_bottlenecks": [
            "[Inferred] Time tracking is inconsistent — billable hours are likely being lost",
            "[Inferred] Client invoicing is delayed and not automated",
            "[Inferred] Project status tracked in email threads and spreadsheets",
            "[Inferred] Proposal and contract creation is manual and time-consuming",
            "[Inferred] Client onboarding requires multiple back-and-forth touchpoints",
        ],
        "likely_current_tools": [
            "QuickBooks or FreshBooks for invoicing",
            "Excel or Google Sheets for project tracking",
            "Email for client communication",
            "Google Drive or Dropbox for file storage",
            "Manual time tracking (or none)",
        ],
        "ai_opportunities": [
            "[Inferred] Automated time tracking integration with billing — recovers 5-10% of lost billable hours",
            "[Inferred] AI-assisted proposal builder using past engagements — cuts proposal time by 60%",
            "[Inferred] Client onboarding automation — intake forms, contract signing, kickoff scheduling in one workflow",
            "[Inferred] Project status dashboards replacing email threads — saves 3-4 hrs/week in status updates",
            "[Inferred] Automated invoice generation and follow-up sequences — reduces average collection time by 30%",
        ],
        "outreach_framing": "[Inferred] Frame around billable hour leakage and proposal efficiency. Professional services owners are often billing less than they should because tracking is manual. Position the audit as finding hidden revenue in their existing client base.",
        "best_decision_maker": "Founder / Managing Partner",
    },
    "franchise": {
        "operational_bottlenecks": [
            "[Inferred] Multi-location reporting requires manual data aggregation from each unit",
            "[Inferred] SOP compliance is enforced through inspection, not automated monitoring",
            "[Inferred] Staff scheduling across locations done in disconnected spreadsheets",
            "[Inferred] Vendor invoices and royalty reporting reconciled manually each period",
            "[Inferred] Marketing performance tracked separately for each location",
        ],
        "likely_current_tools": [
            "Franchisor's required POS system",
            "QuickBooks per location",
            "Excel for cross-location reporting",
            "Email for staff coordination",
            "Paper-based checklists for SOP compliance",
        ],
        "ai_opportunities": [
            "[Inferred] Automated cross-location performance dashboard — eliminates weekly manual reporting",
            "[Inferred] AI-powered labor scheduling optimized by location traffic patterns — reduces overtime costs",
            "[Inferred] Automated royalty and vendor invoice reconciliation — saves 6-8 hrs/month",
            "[Inferred] Digital SOP compliance monitoring with automated follow-up — improves audit scores",
            "[Inferred] Unified customer feedback aggregation across locations — surfaces issues before they escalate",
        ],
        "outreach_framing": "[Inferred] Frame around visibility across locations. Multi-unit operators are often making decisions with incomplete or stale data. Position the audit as building the operating system they need to scale from 3 units to 10.",
        "best_decision_maker": "Owner / Director of Operations",
    },
    "default": {
        "operational_bottlenecks": [
            "[Inferred] Core business data tracked in spreadsheets or disconnected tools",
            "[Inferred] Customer/client follow-up is manual and inconsistent",
            "[Inferred] Financial reporting requires manual data collection each period",
            "[Inferred] Internal communication relies heavily on email and text",
            "[Inferred] Repetitive administrative tasks consume significant owner time",
        ],
        "likely_current_tools": [
            "QuickBooks or similar accounting software",
            "Excel or Google Sheets",
            "Email for internal and external communication",
            "Some form of CRM or contact list",
            "Paper-based processes for field or client work",
        ],
        "ai_opportunities": [
            "[Inferred] Automated data entry and reporting — reclaim 5-10 hrs/week of manual admin",
            "[Inferred] Customer follow-up and nurture sequences — improve retention without added headcount",
            "[Inferred] Integrated financial dashboard replacing manual report builds — save 3-4 hrs/month",
            "[Inferred] Document and template automation — reduce creation time for recurring deliverables",
            "[Inferred] Internal workflow automation connecting existing tools — eliminate manual hand-offs",
        ],
        "outreach_framing": "[Inferred] Frame around time reclaimed by the owner. Most small business owners are doing $20/hr tasks. Position the audit as identifying where their time is being consumed by work that can be automated or delegated with better systems.",
        "best_decision_maker": "Owner / Founder",
    },
}


def _get_industry_template(industry: str) -> dict:
    """Map an industry string to the closest template key."""
    industry_lower = (industry or "").lower()

    construction_kw = ["construction", "trades", "contractor", "plumbing", "electrical",
                       "hvac", "roofing", "landscaping", "painting", "flooring", "remodeling"]
    healthcare_kw = ["healthcare", "medical", "dental", "chiropractic", "therapy",
                     "clinic", "practice", "physician", "mental health", "optometry"]
    professional_kw = ["accounting", "law", "legal", "consulting", "marketing", "staffing",
                       "recruiting", "insurance", "financial", "cpa", "advisory"]
    franchise_kw = ["franchise", "franchisee"]

    if any(kw in industry_lower for kw in construction_kw):
        return _INDUSTRY_TEMPLATES["construction_trades"]
    elif any(kw in industry_lower for kw in healthcare_kw):
        return _INDUSTRY_TEMPLATES["healthcare"]
    elif any(kw in industry_lower for kw in professional_kw):
        return _INDUSTRY_TEMPLATES["professional_services"]
    elif any(kw in industry_lower for kw in franchise_kw):
        return _INDUSTRY_TEMPLATES["franchise"]
    else:
        return _INDUSTRY_TEMPLATES["default"]


# ---------------------------------------------------------------------------
# enrich_company
# ---------------------------------------------------------------------------

def enrich_company(company_dict: dict, api_key: str) -> dict:
    """
    Enriches a company record using Claude claude-sonnet-4-6-20250514.

    Parameters
    ----------
    company_dict : dict   Company fields (name, industry, description, employees, revenue, etc.)
    api_key      : str    Anthropic API key

    Returns
    -------
    dict with keys:
        business_summary, operational_bottlenecks, likely_current_tools,
        ai_opportunities, outreach_framing, best_decision_maker, offer_fit_reasons
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    company_name = company_dict.get("name", "Unknown Company")
    industry = company_dict.get("industry", "Unknown")
    description = company_dict.get("description", "No description provided.")
    employees = company_dict.get("employees") or company_dict.get("employee_count", "Unknown")
    revenue = company_dict.get("revenue") or company_dict.get("annual_revenue", "Unknown")
    pain_points = company_dict.get("pain_points") or []
    pain_points_str = "\n".join(f"- {p}" for p in pain_points) if pain_points else "None documented"
    location = company_dict.get("location") or company_dict.get("city") or "Unknown location"

    prompt = f"""You are an operations consultant who specializes in helping small businesses (5-20 employees, $500K-$5M revenue) identify workflow automation and AI opportunities.

You are analyzing a prospective company for our "AI Systems Audit & Deployment Blueprint" consulting engagement.

COMPANY INFORMATION:
- Name: {company_name}
- Industry: {industry}
- Location: {location}
- Employees: {employees}
- Annual Revenue: {revenue}
- Description: {description}
- Known Pain Points:
{pain_points_str}

TASK:
Based on the company information above, provide a structured analysis. Do NOT fabricate specific facts. You may infer patterns based on industry and company size. Prefix all inferred items with [Inferred].

Respond ONLY with a valid JSON object using exactly these keys:

{{
  "business_summary": "<2-3 sentences describing likely day-to-day operations based on industry and size>",
  "operational_bottlenecks": [
    "<bottleneck 1>",
    "<bottleneck 2>",
    "<bottleneck 3>",
    "<bottleneck 4>",
    "<bottleneck 5>"
  ],
  "likely_current_tools": [
    "<tool 1>",
    "<tool 2>",
    "<tool 3>"
  ],
  "ai_opportunities": [
    "<opportunity with estimated time savings 1>",
    "<opportunity with estimated time savings 2>",
    "<opportunity with estimated time savings 3>",
    "<opportunity with estimated time savings 4>",
    "<opportunity with estimated time savings 5>"
  ],
  "outreach_framing": "<single paragraph on how to frame the outreach for this specific company and owner>",
  "best_decision_maker": "<most likely job title of the person who would buy this audit>",
  "offer_fit_reasons": [
    "<reason 1 this company fits the AI Systems Audit offer>",
    "<reason 2>",
    "<reason 3>"
  ]
}}

Return ONLY the JSON object. No markdown, no explanation, no code fences."""

    message = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = message.content[0].text.strip()

    # Strip any accidental markdown fences
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    enrichment = json.loads(raw_text)
    return enrichment


# ---------------------------------------------------------------------------
# enrich_fallback
# ---------------------------------------------------------------------------

def enrich_fallback(company_dict: dict) -> dict:
    """
    Rule-based enrichment fallback when no API key is available.
    Uses industry-specific templates to generate plausible enrichment data.

    Returns the same structure as enrich_company.
    """
    company_name = company_dict.get("name", "This company")
    industry = company_dict.get("industry", "")
    employees = company_dict.get("employees") or company_dict.get("employee_count", "Unknown")
    revenue = company_dict.get("revenue") or company_dict.get("annual_revenue", "Unknown")

    template = _get_industry_template(industry)

    business_summary = (
        f"[Inferred] {company_name} appears to be an owner-operated {industry or 'small'} business "
        f"with approximately {employees} employees and estimated annual revenue around {revenue}. "
        f"Based on industry patterns, day-to-day operations likely involve significant manual coordination "
        f"across scheduling, billing, and client/project management — common sources of inefficiency at this size."
    )

    offer_fit_reasons = [
        f"[Inferred] Company size ({employees} employees) matches the owner-operator profile where one person is managing too many manual tasks",
        f"[Inferred] Industry ({industry or 'this sector'}) consistently shows high ROI from workflow automation at this revenue level",
        "[Inferred] Likely system fragmentation (multiple disconnected tools) creates immediate audit value by mapping integration opportunities",
    ]

    return {
        "business_summary": business_summary,
        "operational_bottlenecks": template["operational_bottlenecks"],
        "likely_current_tools": template["likely_current_tools"],
        "ai_opportunities": template["ai_opportunities"],
        "outreach_framing": template["outreach_framing"],
        "best_decision_maker": template["best_decision_maker"],
        "offer_fit_reasons": offer_fit_reasons,
    }


# ---------------------------------------------------------------------------
# enrich_and_save
# ---------------------------------------------------------------------------

def enrich_and_save(session, company_id: int, api_key: str = None):
    """
    Enriches a company and saves the results back to the database.

    Sets enriched=True and enriched_at=datetime.utcnow().
    Updates description, pain_points, ai_opportunities, and probable_systems fields.

    Parameters
    ----------
    session     : SQLAlchemy session
    company_id  : int   Primary key of the Company record
    api_key     : str   Optional Anthropic API key; uses fallback if None

    Returns
    -------
    dict with enrichment results
    """
    from database.models import Company

    company = session.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError(f"Company with id={company_id} not found")

    company_dict = {
        "id": company.id,
        "name": getattr(company, "name", ""),
        "industry": getattr(company, "industry", ""),
        "description": getattr(company, "description", ""),
        "employees": getattr(company, "employees", None) or getattr(company, "employee_count", None),
        "revenue": getattr(company, "revenue", None) or getattr(company, "annual_revenue", None),
        "pain_points": getattr(company, "pain_points", []) or [],
        "probable_systems": getattr(company, "probable_systems", []) or [],
        "location": getattr(company, "location", "") or getattr(company, "city", ""),
        "ownership_style": getattr(company, "ownership_style", ""),
    }

    if api_key:
        try:
            enrichment = enrich_company(company_dict, api_key)
        except Exception:
            enrichment = enrich_fallback(company_dict)
    else:
        enrichment = enrich_fallback(company_dict)

    # Update description if currently empty
    if not company_dict.get("description") and enrichment.get("business_summary"):
        if hasattr(company, "description"):
            company.description = enrichment["business_summary"]

    # Update pain_points if currently empty
    existing_pain = company_dict.get("pain_points") or []
    if not existing_pain and enrichment.get("operational_bottlenecks"):
        if hasattr(company, "pain_points"):
            company.pain_points = enrichment["operational_bottlenecks"]

    # Update ai_opportunities
    if enrichment.get("ai_opportunities") and hasattr(company, "ai_opportunities"):
        company.ai_opportunities = enrichment["ai_opportunities"]

    # Update probable_systems
    if enrichment.get("likely_current_tools") and hasattr(company, "probable_systems"):
        company.probable_systems = enrichment["likely_current_tools"]

    # Mark enriched
    if hasattr(company, "enriched"):
        company.enriched = True
    if hasattr(company, "enriched_at"):
        company.enriched_at = datetime.utcnow()

    session.commit()

    return enrichment

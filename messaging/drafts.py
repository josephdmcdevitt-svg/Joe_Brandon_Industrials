"""
Outreach message generation for AI Systems Audit & Deployment Blueprint.
Uses Claude API when available, falls back to industry-specific templates.

The offer being sold:
  "AI Systems Audit & Deployment Blueprint"
  - 60-minute recorded strategy session with the business owner
  - Deep dive into current operations
  - Current-state workflow map
  - AI leverage points ranked by ROI
  - Recommended tool stack
  - 30-60-90 day roadmap
  - Estimated cost savings
  - Written deliverable delivered within 48 hours

Sender: Brandon Rye
Credibility: Citigroup investment banking, FedEx ops analytics ($18M cost reduction), Columbia MBA.
Positioning: Operator and systems thinker — NOT "AI expert."
"""

from __future__ import annotations
import json


# ---------------------------------------------------------------------------
# Industry pain point templates for fallback generation
# ---------------------------------------------------------------------------

_INDUSTRY_PAIN = {
    "hvac_plumbing_electrical": "teams spending 15+ hours a week on dispatch scheduling, job costing, and subcontractor invoices that should take a fraction of that",
    "roofing_painting_remodeling": "crews running on text messages and paper estimates while job costing and change orders fall through the cracks",
    "general_contractor": "project scheduling, subcontractor coordination, and job cost tracking spread across spreadsheets, texts, and email",
    "dental": "front desk staff buried in scheduling, insurance verification, and patient intake paperwork instead of focusing on patient experience",
    "medspa_aesthetic": "appointment booking, client follow-ups, and treatment tracking handled manually when most of it could run on autopilot",
    "chiro_pt_ot": "patient scheduling, intake forms, and billing reconciliation eating up clinical staff time every single week",
    "veterinary": "appointment scheduling, medical records, and client communication managed across disconnected systems",
    "behavioral_health": "intake paperwork, session scheduling, and insurance billing consuming hours that should go to patient care",
    "dermatology_optometry": "patient scheduling, referral tracking, and insurance verification still running on phone calls and paper forms",
    "cpa_accounting": "firms losing billable hours to manual client onboarding, document collection, and reporting workflows that haven't changed in a decade",
    "tax_bookkeeping": "client document collection, data entry, and deliverable tracking still running on email chains and shared drives",
    "law_firm": "attorneys and paralegals spending more time on intake forms, deadline tracking, and document assembly than on actual case work",
    "insurance_brokerage": "quoting, renewal tracking, and client communications managed across spreadsheets and email instead of one connected system",
    "staffing_recruiting": "recruiters spending half their day on candidate tracking, timesheet collection, and invoicing instead of placing people",
    "property_management": "teams drowning in tenant requests, maintenance coordination, and lease tracking across spreadsheets and email threads",
    "real_estate": "lead follow-up, transaction coordination, and closing checklists managed manually when every hour counts",
    "mortgage_brokerage": "document collection, compliance tracking, and pipeline management spread across too many disconnected tools",
    "marketing_agency": "project managers juggling client deliverables, time tracking, and reporting across five different tools instead of one streamlined system",
    "it_msp": "ticket management, client onboarding, and recurring maintenance scheduling handled with manual processes that don't scale",
    "auto_repair": "service advisors manually writing estimates, tracking parts orders, and chasing customer approvals instead of turning bays faster",
    "home_services": "scheduling, dispatching, and invoicing handled by phone and paper when every missed call is a lost job",
    "cleaning_restoration": "route scheduling, supply ordering, and quality tracking managed manually across crews and locations",
    "senior_care_home_health": "coordinators spending hours on caregiver scheduling, compliance documentation, and family communication that should be automated",
    "franchise": "manual cross-location reporting, inconsistent workflows, and scheduling done in separate spreadsheets per unit",
    "fitness_wellness": "class scheduling, member billing, and retention follow-ups running on disconnected systems instead of one automated flow",
    "education_childcare": "enrollment, parent communication, and staff scheduling managed through email and paper sign-up sheets",
    "logistics_freight": "load matching, carrier communication, and invoicing tracked manually when every delay costs margin",
    "manufacturing_fabrication": "quoting, job tracking, and material ordering still running on paper travelers and spreadsheets",
    "catering_events": "event coordination, vendor management, and invoicing handled through email chains instead of a streamlined system",
    "wealth_family_office": "investment tracking, bill pay, and reporting across entities managed in spreadsheets instead of connected systems",
    "architecture_engineering": "project tracking, client billing, and resource allocation spread across email, spreadsheets, and disconnected tools",
    "ecommerce": "order management, inventory tracking, and customer follow-up handled manually instead of through automated workflows",
    "default": "teams spending 15-20 hours a week on processes that should take 2-3 due to manual workflows and lack of automation",
}

_INDUSTRY_VERTICAL_LABEL = {
    "hvac_plumbing_electrical": "the trades",
    "roofing_painting_remodeling": "construction and remodeling",
    "general_contractor": "general contracting",
    "dental": "dental",
    "medspa_aesthetic": "med spas and aesthetics",
    "chiro_pt_ot": "healthcare practices",
    "veterinary": "veterinary care",
    "behavioral_health": "behavioral health",
    "dermatology_optometry": "specialty healthcare",
    "cpa_accounting": "accounting",
    "tax_bookkeeping": "tax and bookkeeping",
    "law_firm": "small law",
    "insurance_brokerage": "insurance",
    "staffing_recruiting": "staffing and recruiting",
    "property_management": "property management",
    "real_estate": "real estate",
    "mortgage_brokerage": "mortgage",
    "marketing_agency": "marketing and creative services",
    "it_msp": "IT services",
    "auto_repair": "automotive",
    "home_services": "home services",
    "cleaning_restoration": "cleaning and restoration",
    "senior_care_home_health": "senior care",
    "franchise": "multi-unit operations",
    "fitness_wellness": "fitness and wellness",
    "education_childcare": "education and childcare",
    "logistics_freight": "logistics",
    "manufacturing_fabrication": "manufacturing",
    "catering_events": "hospitality and events",
    "wealth_family_office": "wealth management and family offices",
    "architecture_engineering": "architecture and engineering",
    "ecommerce": "ecommerce",
    "default": "growing businesses",
}

_INDUSTRY_OPPORTUNITY = {
    "hvac_plumbing_electrical": "Most contractors we work with are losing 8-12% margin on jobs they can't track in real time. That's fixable.",
    "roofing_painting_remodeling": "Most remodeling contractors we work with find 10+ hours a week lost to manual estimating and change order tracking alone.",
    "general_contractor": "Most GCs we work with are leaving margin on the table because job cost data lives in three different places.",
    "dental": "Most practices we work with recover 4-6 hours of front-desk time per week once scheduling and intake are automated.",
    "medspa_aesthetic": "Most med spas we work with are losing 20-30% of rebooking opportunities because follow-up is manual.",
    "chiro_pt_ot": "Most clinics we work with recover 5+ hours of admin time per week once intake and scheduling are streamlined.",
    "veterinary": "Most vet clinics we work with find their front desk is spending half its time on tasks that should be automated.",
    "behavioral_health": "Most behavioral health practices we work with are losing hours to intake and billing that should run automatically.",
    "dermatology_optometry": "Most specialty practices we work with find significant time savings once referral tracking and scheduling are connected.",
    "cpa_accounting": "Most firms we work with are losing 10-15% of billable hours because time tracking and invoicing aren't connected.",
    "tax_bookkeeping": "Most tax firms we work with find that automating document collection alone saves 5+ hours per client during busy season.",
    "law_firm": "Most small firms we work with find 10+ hours a week buried in intake, calendaring, and document prep that should be automated.",
    "insurance_brokerage": "Most brokerages we work with find that automating renewal tracking and quoting workflows cuts admin time by 30-40%.",
    "staffing_recruiting": "Most staffing firms we work with find that half their recruiter time goes to admin instead of candidate engagement.",
    "property_management": "Most property managers we work with find 10-15 hours a week lost to tenant communication and maintenance coordination alone.",
    "real_estate": "Most brokerages we work with find that lead follow-up and transaction coordination eat up time that should close deals.",
    "mortgage_brokerage": "Most mortgage shops we work with find that document collection and compliance tracking add days to every closing.",
    "marketing_agency": "Most agencies we work with are losing 15-20% of billable time to project management overhead that should be automated.",
    "it_msp": "Most MSPs we work with find that ticket routing and client onboarding are their biggest time drains — and most automatable.",
    "auto_repair": "Most shops we work with find that automating estimates and parts ordering cuts front-desk overhead by 30%.",
    "home_services": "Most home service companies we work with find that missed calls and manual scheduling are costing them 5-10 jobs a month.",
    "cleaning_restoration": "Most cleaning companies we work with find that route optimization and automated invoicing save 8-10 hours a week.",
    "senior_care_home_health": "Most agencies we work with find that caregiver scheduling and compliance tracking are their biggest operational bottleneck.",
    "franchise": "Multi-unit operators we work with typically find 6-10 hours a week lost to manual cross-location reporting alone.",
    "fitness_wellness": "Most studios we work with find that automating class booking and member follow-ups increases retention by 15-20%.",
    "education_childcare": "Most centers we work with find that enrollment, billing, and parent communication consume hours that should be automated.",
    "logistics_freight": "Most brokerages we work with find that automating carrier communication and invoicing saves 10+ hours per week.",
    "manufacturing_fabrication": "Most shops we work with find that quoting and job tracking on paper is costing them 10-15% in unbilled work.",
    "catering_events": "Most catering companies we work with find that event coordination and vendor management eat up half the owner's week.",
    "wealth_family_office": "Most family offices we work with find that reporting across entities and bill pay coordination are their biggest time sinks.",
    "architecture_engineering": "Most firms we work with find that project tracking and resource allocation across clients consume 10+ hours a week in manual work.",
    "ecommerce": "Most ecommerce brands we work with find that order management and customer follow-up are their biggest scaling bottlenecks.",
    "default": "Most owners we work with find 10+ hours a week that can be reclaimed once the right systems are mapped and connected.",
}


def _get_industry_key(industry: str) -> str:
    industry_lower = (industry or "").lower()
    # Trades
    if any(kw in industry_lower for kw in ["hvac", "plumbing", "plumber", "electrical", "electrician"]):
        return "hvac_plumbing_electrical"
    if any(kw in industry_lower for kw in ["roofing", "painting", "remodeling", "drywall", "tile", "flooring", "deck", "fence"]):
        return "roofing_painting_remodeling"
    if any(kw in industry_lower for kw in ["general contractor"]):
        return "general_contractor"
    # Healthcare
    if any(kw in industry_lower for kw in ["dental", "orthodontic", "oral surgery"]):
        return "dental"
    if any(kw in industry_lower for kw in ["med spa", "aesthetic", "weight loss", "iv therapy"]):
        return "medspa_aesthetic"
    if any(kw in industry_lower for kw in ["chiropractic", "physical therapy", "occupational therapy", "speech therapy"]):
        return "chiro_pt_ot"
    if any(kw in industry_lower for kw in ["veterinary", "animal hospital"]):
        return "veterinary"
    if any(kw in industry_lower for kw in ["behavioral", "psychology", "psychiatry", "substance abuse"]):
        return "behavioral_health"
    if any(kw in industry_lower for kw in ["dermatology", "optometry", "ophthalmology", "fertility", "sleep clinic"]):
        return "dermatology_optometry"
    # Finance / Professional
    if any(kw in industry_lower for kw in ["cpa", "accounting", "fractional cfo"]):
        return "cpa_accounting"
    if any(kw in industry_lower for kw in ["tax preparation", "bookkeeping", "payroll service"]):
        return "tax_bookkeeping"
    if any(kw in industry_lower for kw in ["law firm", "law ", "legal", "attorney"]):
        return "law_firm"
    if any(kw in industry_lower for kw in ["insurance"]):
        return "insurance_brokerage"
    if any(kw in industry_lower for kw in ["staffing", "recruiting", "executive search"]):
        return "staffing_recruiting"
    # Real Estate
    if any(kw in industry_lower for kw in ["property management", "hoa management"]):
        return "property_management"
    if any(kw in industry_lower for kw in ["real estate"]):
        return "real_estate"
    if any(kw in industry_lower for kw in ["mortgage"]):
        return "mortgage_brokerage"
    # Services
    if any(kw in industry_lower for kw in ["marketing", "seo", "branding", "creative", "public relations", "video production", "paid media", "social media"]):
        return "marketing_agency"
    if any(kw in industry_lower for kw in ["it managed", "cybersecurity", "cloud consulting", "it support", "technology consulting"]):
        return "it_msp"
    if any(kw in industry_lower for kw in ["auto repair", "collision", "auto body", "transmission", "tire shop", "mechanic", "auto detailing", "car wash", "fleet maintenance"]):
        return "auto_repair"
    if any(kw in industry_lower for kw in ["pest control", "garage door", "appliance repair", "pool service", "irrigation", "window cleaning", "pressure washing"]):
        return "home_services"
    if any(kw in industry_lower for kw in ["landscaping", "tree service", "lawn care"]):
        return "home_services"
    if any(kw in industry_lower for kw in ["cleaning", "restoration", "mold remediation", "fire", "water damage"]):
        return "cleaning_restoration"
    if any(kw in industry_lower for kw in ["home health", "senior", "non-medical care", "adult day care"]):
        return "senior_care_home_health"
    if any(kw in industry_lower for kw in ["franchise"]):
        return "franchise"
    if any(kw in industry_lower for kw in ["gym", "fitness", "yoga", "pilates", "crossfit", "martial arts", "personal training"]):
        return "fitness_wellness"
    if any(kw in industry_lower for kw in ["tutoring", "test prep", "music school", "dance studio", "language school", "stem education", "daycare", "preschool", "after school", "childcare"]):
        return "education_childcare"
    if any(kw in industry_lower for kw in ["freight", "trucking", "courier", "last mile", "logistics"]):
        return "logistics_freight"
    if any(kw in industry_lower for kw in ["machine shop", "metal fabrication", "plastic fabrication", "woodworking", "cabinet", "sign manufacturing", "printing", "packaging"]):
        return "manufacturing_fabrication"
    if any(kw in industry_lower for kw in ["catering", "event planning", "wedding planner", "event production"]):
        return "catering_events"
    if any(kw in industry_lower for kw in ["family office", "wealth management", "financial advisory"]):
        return "wealth_family_office"
    if any(kw in industry_lower for kw in ["architecture", "engineering", "interior design", "surveying"]):
        return "architecture_engineering"
    if any(kw in industry_lower for kw in ["ecommerce", "amazon seller", "shopify", "subscription product"]):
        return "ecommerce"
    return "default"


def _call_claude(prompt: str, api_key: str, max_tokens: int = 800) -> str:
    """Helper to call Claude API and return the text response."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return raw


# ---------------------------------------------------------------------------
# generate_email_draft
# ---------------------------------------------------------------------------

def generate_email_draft(
    company_dict: dict,
    contact_dict: dict,
    api_key: str,
    tone: str = "practical",
) -> dict:
    """
    Generates an initial cold outreach email for the AI Systems Audit offer.

    Parameters
    ----------
    company_dict  : dict   Company data (name, industry, description, pain_points, etc.)
    contact_dict  : dict   Contact data (first_name, last_name, title, email, etc.)
    api_key       : str    Anthropic API key
    tone          : str    "practical" | "warm" | "direct" (default: practical)

    Returns
    -------
    {"subject": str, "body": str}
    """
    company_name = company_dict.get("name", "your company")
    industry = company_dict.get("industry", "")
    pain_points = company_dict.get("pain_points") or []
    description = company_dict.get("description", "")
    ai_opps = company_dict.get("ai_opportunities") or []

    contact_first = contact_dict.get("first_name") or contact_dict.get("name", "there").split()[0]
    contact_title = contact_dict.get("title", "")

    pain_str = "; ".join(str(p) for p in pain_points[:3]) if pain_points else "operational complexity at your scale"
    ai_opp_str = str(ai_opps[0]).replace("[Inferred] ", "") if ai_opps else "workflow automation that pays for itself quickly"

    prompt = f"""You are writing a cold outreach email on behalf of Brandon Rye.

ABOUT BRANDON RYE:
- Former Citigroup investment banker and FedEx operations analyst (led projects that reduced costs by $18M)
- Columbia MBA
- Now helps owner-operated small businesses clean up messy operational systems and identify automation opportunities
- He is NOT positioned as an "AI expert" — he is an operator and systems thinker

THE OFFER:
"AI Systems Audit & Deployment Blueprint" — A 60-minute recorded strategy session with the business owner. Deliverables within 48 hours: current-state workflow map, AI leverage points ranked by ROI, recommended tool stack, 30-60-90 day roadmap, estimated cost savings.

PROSPECT INFORMATION:
- Company: {company_name}
- Industry: {industry}
- Contact: {contact_first} ({contact_title})
- Key pain points: {pain_str}
- Top automation opportunity: {ai_opp_str}
- Description: {description[:300] if description else "Not provided"}

WRITING RULES:
1. Tone must be {tone}, owner-focused, and ROI-oriented — no jargon, no hype
2. Do NOT say "AI expert" — say "we help owners clean up messy operational systems and identify automation opportunities"
3. Reference the specific industry pain points of this company
4. Include this exact soft CTA (adjusted with company name): "Would it make sense to spend 15 minutes talking through what this would look like for {company_name}?"
5. Keep the body under 150 words
6. Personalize with company name, industry context, and a specific pain point
7. Subject line should be specific and curiosity-driven — not generic
8. Sign off as Brandon Rye

Respond ONLY with a valid JSON object:
{{
  "subject": "<email subject line>",
  "body": "<full email body including greeting and sign-off>"
}}

Return ONLY the JSON. No markdown, no explanation."""

    raw = _call_claude(prompt, api_key)
    result = json.loads(raw)
    return {"subject": result.get("subject", ""), "body": result.get("body", "")}


# ---------------------------------------------------------------------------
# generate_followup
# ---------------------------------------------------------------------------

def generate_followup(
    company_dict: dict,
    contact_dict: dict,
    api_key: str,
    followup_number: int = 1,
) -> dict:
    """
    Generates a follow-up email. Shorter than the initial, references prior outreach,
    adds a new angle or proof point.

    Parameters
    ----------
    followup_number : int   1 = first follow-up, 2 = second, etc.

    Returns
    -------
    {"subject": str, "body": str}
    """
    company_name = company_dict.get("name", "your company")
    industry = company_dict.get("industry", "")
    pain_points = company_dict.get("pain_points") or []
    ai_opps = company_dict.get("ai_opportunities") or []

    contact_first = contact_dict.get("first_name") or contact_dict.get("name", "there").split()[0]

    pain_str = "; ".join(str(p) for p in pain_points[:2]) if pain_points else "operational complexity"
    second_opp = str(ai_opps[1]).replace("[Inferred] ", "") if len(ai_opps) > 1 else "a second area of automation opportunity"

    new_angle_map = {
        1: "a short example of what a past audit surfaced for a similar business",
        2: "a specific cost savings estimate typical for this industry",
        3: "a direct question about one operational pain point to re-engage",
    }
    new_angle = new_angle_map.get(followup_number, new_angle_map[1])

    prompt = f"""You are writing follow-up email #{followup_number} on behalf of Brandon Rye.

CONTEXT:
- Brandon already sent an initial email to {contact_first} at {company_name} about the AI Systems Audit offer
- This is follow-up #{followup_number}
- The initial email introduced the offer and asked for 15 minutes

ABOUT BRANDON RYE:
- Former Citigroup investment banker and FedEx operations analyst ($18M cost reduction)
- Columbia MBA
- Helps owner-operated businesses clean up messy systems and find automation opportunities

THE OFFER:
"AI Systems Audit & Deployment Blueprint" — 60-min recorded strategy session, workflow map, AI leverage points, tool stack, 30-60-90 roadmap, cost savings estimate. Written deliverable in 48 hrs.

PROSPECT:
- Company: {company_name}
- Industry: {industry}
- Contact: {contact_first}
- Pain points: {pain_str}
- New angle to add: {new_angle}
- Second automation opportunity: {second_opp}

WRITING RULES:
1. Under 100 words in the body
2. Reference the earlier email briefly ("Following up on my note last week...")
3. Add a new angle — don't just repeat the same pitch
4. End with the same soft CTA: "Would it make sense to spend 15 minutes talking through what this would look like for {company_name}?"
5. Practical, direct tone — no fluff
6. Sign off as Brandon Rye

Respond ONLY with a valid JSON object:
{{
  "subject": "<follow-up subject — use RE: or a fresh subject>",
  "body": "<full email body>"
}}

Return ONLY the JSON. No markdown."""

    raw = _call_claude(prompt, api_key)
    result = json.loads(raw)
    return {"subject": result.get("subject", ""), "body": result.get("body", "")}


# ---------------------------------------------------------------------------
# generate_linkedin_message
# ---------------------------------------------------------------------------

def generate_linkedin_message(
    company_dict: dict,
    contact_dict: dict,
    api_key: str,
) -> dict:
    """
    Generates a LinkedIn connection request message.
    Must be under 300 characters.

    Returns
    -------
    {"body": str}
    """
    company_name = company_dict.get("name", "your company")
    industry = company_dict.get("industry", "")
    contact_first = contact_dict.get("first_name") or contact_dict.get("name", "there").split()[0]
    pain_points = company_dict.get("pain_points") or []
    pain_str = str(pain_points[0]).replace("[Inferred] ", "") if pain_points else "operational complexity"

    prompt = f"""Write a LinkedIn connection request message from Brandon Rye (ex-Citigroup/FedEx, Columbia MBA) to {contact_first}, owner/operator at {company_name} ({industry}).

Brandon helps small business owners identify automation opportunities in their operations.

Reference one specific pain point relevant to their industry: {pain_str}

RULES:
- Under 300 characters TOTAL (this is a hard LinkedIn limit)
- Conversational, not salesy
- No pitch, just an intro and a reason to connect
- Do not mention "AI" — just "systems" or "operations"

Respond ONLY with a valid JSON object:
{{"body": "<the message text>"}}

Return ONLY the JSON."""

    raw = _call_claude(prompt, api_key, max_tokens=300)
    result = json.loads(raw)
    body = result.get("body", "")
    # Hard enforce character limit
    if len(body) > 300:
        body = body[:297] + "..."
    return {"body": body}


# ---------------------------------------------------------------------------
# generate_call_script
# ---------------------------------------------------------------------------

def generate_call_script(
    company_dict: dict,
    contact_dict: dict,
    api_key: str,
) -> dict:
    """
    Generates a brief cold call script for Brandon to use.
    Includes opening line, 3 talking points, 2 objection handlers, and a close.

    Returns
    -------
    {"script": str}
    """
    company_name = company_dict.get("name", "your company")
    industry = company_dict.get("industry", "")
    pain_points = company_dict.get("pain_points") or []
    ai_opps = company_dict.get("ai_opportunities") or []

    contact_first = contact_dict.get("first_name") or contact_dict.get("name", "there").split()[0]
    contact_title = contact_dict.get("title", "owner")

    pain_str = "; ".join(str(p) for p in pain_points[:3]) if pain_points else "manual process burden and disconnected tools"
    top_opp = str(ai_opps[0]).replace("[Inferred] ", "") if ai_opps else "automation opportunities in their operations"

    prompt = f"""Write a short cold call script for Brandon Rye to call {contact_first} ({contact_title}) at {company_name} ({industry}).

ABOUT BRANDON:
- Ex-Citigroup investment banker, ex-FedEx ops analyst ($18M cost reduction), Columbia MBA
- Now helps owner-operated businesses fix messy operational systems and identify automation wins
- NOT an "AI expert" — an operator and systems thinker

THE OFFER:
"AI Systems Audit & Deployment Blueprint" — 60-min recorded session. Deliverables: workflow map, AI leverage points, tool stack, 30-60-90 roadmap, cost savings estimates. Written deliverable in 48 hours. $[price not disclosed on call].

COMPANY CONTEXT:
- Pain points: {pain_str}
- Top opportunity: {top_opp}

FORMAT THE SCRIPT with these sections:
1. OPENING LINE (one sentence that earns 30 more seconds)
2. TALKING POINTS (3 bullet points — concise, ROI-focused, no jargon)
3. OBJECTION HANDLERS (2 — cover "not interested" and "too busy/bad time")
4. CLOSE (soft ask for a 15-min call or permission to send a short email)

Keep the whole script under 300 words. Conversational, operator-to-operator tone. No corporate speak.

Respond ONLY with a valid JSON object:
{{"script": "<the full formatted script as a string with newlines>"}}

Return ONLY the JSON."""

    raw = _call_claude(prompt, api_key, max_tokens=800)
    result = json.loads(raw)
    return {"script": result.get("script", "")}


# ---------------------------------------------------------------------------
# generate_draft_fallback
# ---------------------------------------------------------------------------

def generate_draft_fallback(
    company_dict: dict,
    contact_dict: dict,
    draft_type: str = "email_initial",
) -> dict:
    """
    Template-based fallback when no API key is available.
    Generates outreach drafts using industry-specific templates with variable substitution.

    Parameters
    ----------
    draft_type : str
        One of: "email_initial", "email_followup", "linkedin", "call_script"

    Returns
    -------
    dict with keys matching the corresponding generate_* function output
    """
    company_name = company_dict.get("name", "your company")
    industry = company_dict.get("industry", "")
    contact_first_raw = contact_dict.get("first_name") or (contact_dict.get("name") or "").split()[0] if contact_dict.get("first_name") or contact_dict.get("name") else ""
    # Determine greeting: use real name if available, otherwise "Hi [Company] team"
    generic_names = {"there", "owner", "principal", "managing partner", "practice owner", "n/a", ""}
    if contact_first_raw.lower().strip() in generic_names:
        greeting_name = f"{company_name} team"
    else:
        greeting_name = contact_first_raw

    industry_key = _get_industry_key(industry)
    industry_pain = _INDUSTRY_PAIN[industry_key]
    industry_opportunity = _INDUSTRY_OPPORTUNITY[industry_key]
    industry_label = industry or "your industry"

    # Get the vertical label for the industry
    vertical_label = _INDUSTRY_VERTICAL_LABEL.get(industry_key, industry_label)

    if draft_type == "email_initial":
        subject = f"Streamlining operations at {company_name}"
        body = (
            f"Hi {greeting_name},\n\n"
            f"I'm a Columbia MBA and former Citi investment banking VP who now helps "
            f"growing businesses cut operational waste and streamline workflows. Before "
            f"banking, I spent years in FP&A and systems implementation — including "
            f"driving $18M in recurring cost reductions at FedEx.\n\n"
            f"Across {vertical_label}, I'm seeing the same pattern — {industry_pain}.\n\n"
            f"I offer what I call an Operations Blueprint: a 60-minute deep dive where "
            f"we map your current workflows, identify the highest-ROI automation "
            f"opportunities, and outline exactly how to implement them — with a full "
            f"written roadmap delivered within 48 hours.\n\n"
            f"If this sounds useful, happy to start with a quick intro call to see if it's a fit.\n\n"
            f"Best,\n"
            f"Brandon Rye"
        )
        return {"subject": subject, "body": body}

    elif draft_type == "email_followup":
        subject = f"Re: Operational systems for {company_name}"
        body = (
            f"Hi {contact_first},\n\n"
            f"Following up on my note from last week. Wanted to add one more thought — "
            f"most {industry_label} owners we work with find the biggest leverage point is "
            f"something they didn't realize was costing them time until we mapped it out.\n\n"
            f"Would it make sense to spend 15 minutes talking through what this would look like for {company_name}?\n\n"
            f"Brandon Rye"
        )
        return {"subject": subject, "body": body}

    elif draft_type == "linkedin":
        body = (
            f"Hi {contact_first} — I work with {industry_label} owners on operational systems. "
            f"Saw {company_name} and thought there might be some overlap. Happy to connect."
        )
        if len(body) > 300:
            body = body[:297] + "..."
        return {"body": body}

    elif draft_type == "call_script":
        script = (
            f"OPENING LINE:\n"
            f"\"Hi {contact_first}, my name is Brandon Rye — I help {industry_label} owners "
            f"identify where their operations are leaking time and money, and build a plan to fix it. "
            f"Do you have 30 seconds?\"\n\n"
            f"TALKING POINTS:\n"
            f"- We work specifically with {industry_label} businesses at your size — we know the pain points cold\n"
            f"- Common issues: {industry_pain}\n"
            f"- {industry_opportunity}\n\n"
            f"OBJECTION HANDLERS:\n"
            f"\"Not interested\" — \"Totally fair. Can I ask — is it that the timing isn't right, "
            f"or that this isn't on your radar at all? Even 5 minutes could be worth it.\"\n"
            f"\"Too busy\" — \"I get it — that's actually why people call us. "
            f"Can I send you a two-paragraph email instead? Takes 30 seconds to read.\"\n\n"
            f"CLOSE:\n"
            f"\"All I'm asking for is 15 minutes on a call to see if what we do maps to what you're dealing with. "
            f"If it doesn't fit, I'll tell you straight. Does [day/time] work?\""
        )
        return {"script": script}

    else:
        return {"body": f"[Template fallback] Draft type '{draft_type}' not recognized. Valid types: email_initial, email_followup, linkedin, call_script."}

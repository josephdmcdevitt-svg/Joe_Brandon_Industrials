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
    "construction_trades": "job costing tracked in spreadsheets, scheduling done by text, and subcontractor invoices piling up without a clear system",
    "healthcare": "phone-based scheduling, paper intake forms, and billing reconciliation eating up staff time every week",
    "professional_services": "manual time tracking, delayed invoicing, and project status living in disconnected email threads",
    "franchise": "manual cross-location reporting, inconsistent SOP compliance, and scheduling done in separate spreadsheets per unit",
    "default": "manual processes, disconnected tools, and owner time spent on tasks that should run without them",
}

_INDUSTRY_OPPORTUNITY = {
    "construction_trades": "Most contractors we work with are losing 8-12% margin on jobs they can't track in real time. That's fixable.",
    "healthcare": "Most practices we work with recover 4-6 hours of front-desk time per week once scheduling and intake are automated.",
    "professional_services": "Most firms we work with are losing 10-15% of billable hours because time tracking and invoicing aren't connected.",
    "franchise": "Multi-unit operators we work with typically find 6-10 hours a week lost to manual cross-location reporting alone.",
    "default": "Most owners we work with find 10+ hours a week that can be reclaimed once the right systems are mapped and connected.",
}


def _get_industry_key(industry: str) -> str:
    industry_lower = (industry or "").lower()
    if any(kw in industry_lower for kw in ["construction", "trades", "contractor", "hvac", "roofing", "plumbing", "electrical", "landscaping"]):
        return "construction_trades"
    elif any(kw in industry_lower for kw in ["healthcare", "medical", "dental", "therapy", "clinic", "practice", "chiropractic"]):
        return "healthcare"
    elif any(kw in industry_lower for kw in ["accounting", "law", "legal", "consulting", "marketing", "staffing", "insurance", "financial", "cpa"]):
        return "professional_services"
    elif any(kw in industry_lower for kw in ["franchise", "franchisee"]):
        return "franchise"
    else:
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
    contact_first = contact_dict.get("first_name") or (contact_dict.get("name") or "there").split()[0]

    industry_key = _get_industry_key(industry)
    industry_pain = _INDUSTRY_PAIN[industry_key]
    industry_opportunity = _INDUSTRY_OPPORTUNITY[industry_key]
    industry_label = industry or "your industry"

    if draft_type == "email_initial":
        subject = f"Operational systems for {company_name}"
        body = (
            f"Hi {contact_first},\n\n"
            f"I work with owner-operated {industry_label} businesses to clean up messy operational systems "
            f"and find automation opportunities — things like {industry_pain}.\n\n"
            f"{industry_opportunity}\n\n"
            f"We do a 60-minute recorded session with the owner, then deliver a full workflow map, "
            f"a prioritized list of automation opportunities, and a 30-60-90 day roadmap within 48 hours.\n\n"
            f"Would it make sense to spend 15 minutes talking through what this would look like for {company_name}?\n\n"
            f"Brandon Rye\n"
            f"(Ex-Citigroup / FedEx Ops / Columbia MBA)"
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

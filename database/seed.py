"""
Seed 25 realistic sample companies (and their contacts) into the database.
Safe to run multiple times — existing seed records are skipped.
"""

import json
import sys
from pathlib import Path

# Allow running this file directly from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from database.db import get_session, init_db
from database.models import Company, Contact


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
COMPANIES = [
    # -----------------------------------------------------------------------
    # Professional Services — Marketing Agencies
    # -----------------------------------------------------------------------
    {
        "name": "Summit Marketing Group",
        "website": "https://summitmarketinggroup.com",
        "city": "Chicago",
        "state": "IL",
        "metro_area": "Chicago",
        "industry": "Professional Services",
        "sub_industry": "Marketing Agency",
        "employee_count_min": 8,
        "employee_count_max": 14,
        "estimated_revenue_min": 1_200_000,
        "estimated_revenue_max": 2_000_000,
        "description": (
            "Full-service digital marketing agency serving mid-market B2B clients. "
            "Handles paid search, SEO, and content strategy. Team of 10 runs client "
            "reporting manually in Google Sheets every month end."
        ),
        "probable_systems": json.dumps(["Google Workspace", "Google Sheets", "HubSpot Free", "Slack"]),
        "pain_points": json.dumps([
            "Monthly client reports take 15+ hours to compile manually",
            "No automated alert when ad spend deviates from budget",
            "Onboarding new clients requires manually duplicating Sheets templates",
        ]),
        "ai_opportunities": json.dumps([
            "Automated monthly report generation from ad platform APIs",
            "Budget anomaly detection and client alerts",
            "AI-drafted client onboarding emails and intake summaries",
        ]),
        "ai_fit_score": 82,
        "ai_fit_reasons": json.dumps([
            "High volume of repetitive reporting work ripe for automation",
            "Owner expressed frustration with manual processes in public LinkedIn post",
            "Already using Google Workspace — low integration friction",
        ]),
        "offer_conversion_score": 74,
        "offer_conversion_reasons": json.dumps([
            "Clear ROI story: save 15 hrs/month at $75/hr billable rate",
            "Owner is technical enough to appreciate AI tooling",
        ]),
        "contacts": [
            {"first_name": "Derek", "last_name": "Holloway", "title": "Owner", "is_decision_maker": True},
            {"first_name": "Priya", "last_name": "Shah", "title": "Operations Manager", "is_decision_maker": False},
        ],
    },
    {
        "name": "Coastal Creative Agency",
        "website": "https://coastalcreativeagency.com",
        "city": "Miami",
        "state": "FL",
        "metro_area": "Miami",
        "industry": "Professional Services",
        "sub_industry": "Marketing Agency",
        "employee_count_min": 5,
        "employee_count_max": 9,
        "estimated_revenue_min": 700_000,
        "estimated_revenue_max": 1_400_000,
        "description": (
            "Boutique branding and social media agency focused on hospitality and "
            "real estate clients in South Florida. Small team juggles 30+ active "
            "accounts with no project management software."
        ),
        "probable_systems": json.dumps(["Google Sheets", "Canva", "Meta Business Suite", "WhatsApp"]),
        "pain_points": json.dumps([
            "No centralized project tracker — status lives in group chats",
            "Content calendar built manually every month per client",
            "Proposal writing takes owner 4-6 hours per deal",
        ]),
        "ai_opportunities": json.dumps([
            "AI-generated first-draft proposals from intake form answers",
            "Automated monthly content calendar creation",
            "Centralized project status assistant via Slack bot",
        ]),
        "ai_fit_score": 76,
        "ai_fit_reasons": json.dumps([
            "Owner-operated with obvious time bottlenecks",
            "Content creation workflows are highly templatable",
        ]),
        "offer_conversion_score": 68,
        "offer_conversion_reasons": json.dumps([
            "Budget-conscious but revenue growth is a clear motivator",
            "Has expressed interest in AI tools on Instagram",
        ]),
        "contacts": [
            {"first_name": "Sofia", "last_name": "Delgado", "title": "Owner / Creative Director", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Professional Services — Law Firms
    # -----------------------------------------------------------------------
    {
        "name": "Hargrove & Wills Law",
        "website": "https://hargrovewills.com",
        "city": "Nashville",
        "state": "TN",
        "metro_area": "Nashville",
        "industry": "Professional Services",
        "sub_industry": "Law Firm",
        "employee_count_min": 6,
        "employee_count_max": 12,
        "estimated_revenue_min": 1_500_000,
        "estimated_revenue_max": 3_000_000,
        "description": (
            "General practice law firm specializing in estate planning, real estate "
            "transactions, and small-business formation. Intake and client follow-up "
            "still managed via paper forms and phone calls."
        ),
        "probable_systems": json.dumps(["Clio (partial use)", "Microsoft Office", "Paper forms", "Outlook"]),
        "pain_points": json.dumps([
            "Client intake takes 45 min per call; data entry done twice",
            "Document drafting for wills and LLCs is highly repetitive",
            "Follow-up reminders tracked in a personal Outlook calendar",
        ]),
        "ai_opportunities": json.dumps([
            "Automated client intake form with AI summary for attorney review",
            "Template-driven document assembly for standard legal forms",
            "AI follow-up drip sequence for estate planning prospects",
        ]),
        "ai_fit_score": 85,
        "ai_fit_reasons": json.dumps([
            "High-value, repetitive document work is ideal for AI automation",
            "Clio integration available — existing data foothold",
            "Partner explicitly cited 'admin overload' in a state bar interview",
        ]),
        "offer_conversion_score": 80,
        "offer_conversion_reasons": json.dumps([
            "Clear billable hour recovery story",
            "Partners are used to paying for software (Clio, Westlaw)",
        ]),
        "contacts": [
            {"first_name": "Robert", "last_name": "Hargrove", "title": "Managing Partner", "is_decision_maker": True},
            {"first_name": "Linda", "last_name": "Cho", "title": "Office Manager", "is_decision_maker": False},
        ],
    },
    {
        "name": "Moreno Legal Group",
        "website": "https://morenolegalgroup.com",
        "city": "Dallas",
        "state": "TX",
        "metro_area": "Dallas",
        "industry": "Professional Services",
        "sub_industry": "Law Firm",
        "employee_count_min": 4,
        "employee_count_max": 8,
        "estimated_revenue_min": 900_000,
        "estimated_revenue_max": 1_800_000,
        "description": (
            "Immigration and family law boutique firm in Dallas. Handles high volume "
            "of similar case types, yet every client communication is crafted from "
            "scratch by the principal attorney."
        ),
        "probable_systems": json.dumps(["MyCase", "Google Docs", "QuickBooks", "Calendly"]),
        "pain_points": json.dumps([
            "Status update emails written manually for every case milestone",
            "Appointment no-shows cost ~8 hrs/month in rescheduling",
            "Intake questionnaires scanned and re-entered into MyCase",
        ]),
        "ai_opportunities": json.dumps([
            "Automated case status email updates triggered by MyCase events",
            "AI reminder and rescheduling workflow for appointments",
            "OCR + auto-populate intake data into MyCase",
        ]),
        "ai_fit_score": 79,
        "ai_fit_reasons": json.dumps([
            "Very repetitive case communication patterns",
            "MyCase has an API for integration",
        ]),
        "offer_conversion_score": 71,
        "offer_conversion_reasons": json.dumps([
            "Principal is the sole bottleneck — strong pain-to-solution fit",
        ]),
        "contacts": [
            {"first_name": "Carlos", "last_name": "Moreno", "title": "Principal Attorney", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Professional Services — Consulting
    # -----------------------------------------------------------------------
    {
        "name": "Apex Operations Consulting",
        "website": "https://apexopsconsulting.com",
        "city": "Atlanta",
        "state": "GA",
        "metro_area": "Atlanta",
        "industry": "Professional Services",
        "sub_industry": "Consulting Firm",
        "employee_count_min": 7,
        "employee_count_max": 15,
        "estimated_revenue_min": 2_000_000,
        "estimated_revenue_max": 4_000_000,
        "description": (
            "Supply chain and operations consultancy serving manufacturing SMBs in the "
            "Southeast. Delivers process audits and SOPs. Deliverables are Word docs "
            "assembled manually from prior engagement templates."
        ),
        "probable_systems": json.dumps(["Microsoft 365", "SharePoint", "Excel", "Zoom"]),
        "pain_points": json.dumps([
            "Deliverable creation takes 40% of a senior consultant's billable week",
            "No standardized knowledge base — institutional knowledge lives in email threads",
            "Proposal win rate tracking is a personal spreadsheet",
        ]),
        "ai_opportunities": json.dumps([
            "AI-assisted SOP and deliverable drafting from audit notes",
            "Internal knowledge base with AI search across past engagements",
            "Automated pipeline tracking dashboard with win-rate analytics",
        ]),
        "ai_fit_score": 88,
        "ai_fit_reasons": json.dumps([
            "Knowledge-intensive firm with highly reusable content patterns",
            "Senior staff time is expensive — automation ROI is immediate",
            "Microsoft 365 stack makes Copilot integration natural",
        ]),
        "offer_conversion_score": 83,
        "offer_conversion_reasons": json.dumps([
            "COO is actively researching AI tools (LinkedIn activity)",
            "Firm already charges premium rates — willing to invest in efficiency",
        ]),
        "contacts": [
            {"first_name": "Marcus", "last_name": "Webb", "title": "COO", "is_decision_maker": True},
            {"first_name": "Tanya", "last_name": "Osei", "title": "Senior Consultant", "is_decision_maker": False},
        ],
    },
    # -----------------------------------------------------------------------
    # Professional Services — Architecture
    # -----------------------------------------------------------------------
    {
        "name": "Morrow Architectural Studio",
        "website": "https://morrowarchstudio.com",
        "city": "Denver",
        "state": "CO",
        "metro_area": "Denver",
        "industry": "Professional Services",
        "sub_industry": "Architecture Firm",
        "employee_count_min": 5,
        "employee_count_max": 10,
        "estimated_revenue_min": 1_000_000,
        "estimated_revenue_max": 2_000_000,
        "description": (
            "Residential and light-commercial architecture firm with projects across "
            "Colorado. Project updates to clients are infrequent and unstructured. "
            "Permit submittal packages assembled manually from AutoCAD exports."
        ),
        "probable_systems": json.dumps(["AutoCAD", "Dropbox", "QuickBooks", "Google Sheets"]),
        "pain_points": json.dumps([
            "Client communication gaps lead to 'where are we?' calls every week",
            "Permit package assembly takes a draftsman 2 full days per project",
            "Invoice schedules tied to milestones tracked in a personal spreadsheet",
        ]),
        "ai_opportunities": json.dumps([
            "Automated project milestone update emails to clients",
            "AI-assisted permit checklist and document assembly workflow",
            "Invoice trigger automation tied to project milestone completion",
        ]),
        "ai_fit_score": 72,
        "ai_fit_reasons": json.dumps([
            "Project-based workflow has clear automation trigger points",
            "Small team means owner is heavily involved in admin",
        ]),
        "offer_conversion_score": 65,
        "offer_conversion_reasons": json.dumps([
            "Architects can be skeptical of non-design software",
            "Strong ROI story on permit package time savings",
        ]),
        "contacts": [
            {"first_name": "Ellen", "last_name": "Morrow", "title": "Principal Architect", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Construction / Trades — Electrical
    # -----------------------------------------------------------------------
    {
        "name": "Precision Electric LLC",
        "website": "https://precisionelectricllc.com",
        "city": "Charlotte",
        "state": "NC",
        "metro_area": "Charlotte",
        "industry": "Construction & Trades",
        "sub_industry": "Electrical Contractor",
        "employee_count_min": 8,
        "employee_count_max": 16,
        "estimated_revenue_min": 1_800_000,
        "estimated_revenue_max": 3_500_000,
        "description": (
            "Commercial and residential electrical contractor serving the greater "
            "Charlotte metro. Runs 4-6 active crews simultaneously. Job costing and "
            "scheduling are done in a combination of paper and text messages."
        ),
        "probable_systems": json.dumps(["QuickBooks", "Paper timesheets", "Text messages", "Google Calendar"]),
        "pain_points": json.dumps([
            "Crew scheduling conflicts discovered the morning of the job",
            "Change orders scribbled on paper — billing discrepancies every month",
            "Estimating new jobs takes owner 3+ hours per bid",
        ]),
        "ai_opportunities": json.dumps([
            "AI-assisted job estimating from scope descriptions",
            "Digital change order workflow with automatic billing update",
            "Crew scheduling assistant that flags conflicts 48 hrs in advance",
        ]),
        "ai_fit_score": 80,
        "ai_fit_reasons": json.dumps([
            "Paper-based ops with multiple crews = high automation upside",
            "Estimating is a repeatable, data-rich task ideal for AI",
        ]),
        "offer_conversion_score": 75,
        "offer_conversion_reasons": json.dumps([
            "Owner is cost-conscious but change order losses are a documented pain",
            "Competitor just adopted field service software — creates urgency",
        ]),
        "contacts": [
            {"first_name": "Tony", "last_name": "Raines", "title": "Owner", "is_decision_maker": True},
            {"first_name": "Gina", "last_name": "Raines", "title": "Office Manager", "is_decision_maker": False},
        ],
    },
    # -----------------------------------------------------------------------
    # Construction / Trades — Plumbing
    # -----------------------------------------------------------------------
    {
        "name": "Blue Ridge Plumbing Co.",
        "website": "https://blueridgeplumbing.com",
        "city": "Asheville",
        "state": "NC",
        "metro_area": "Charlotte",
        "industry": "Construction & Trades",
        "sub_industry": "Plumbing Contractor",
        "employee_count_min": 6,
        "employee_count_max": 12,
        "estimated_revenue_min": 1_100_000,
        "estimated_revenue_max": 2_200_000,
        "description": (
            "Residential service and new-construction plumbing company. High volume "
            "of repeat service calls with no CRM. Customer follow-up after service "
            "is non-existent — leaving review and referral revenue on the table."
        ),
        "probable_systems": json.dumps(["QuickBooks", "Paper invoices", "Phone calls", "Google Maps"]),
        "pain_points": json.dumps([
            "No follow-up after service calls — zero review generation process",
            "Job history stored in technician memory, not a system",
            "Dispatch coordination done entirely by phone between owner and techs",
        ]),
        "ai_opportunities": json.dumps([
            "Automated post-service review request via SMS",
            "AI-assisted dispatch routing and job assignment",
            "Digital job history capture with AI search",
        ]),
        "ai_fit_score": 75,
        "ai_fit_reasons": json.dumps([
            "Service-call business model is highly automatable",
            "Review generation alone has clear, fast ROI",
        ]),
        "offer_conversion_score": 70,
        "offer_conversion_reasons": json.dumps([
            "Owner understands lost review revenue intuitively",
        ]),
        "contacts": [
            {"first_name": "Wade", "last_name": "Simmons", "title": "Owner", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Construction / Trades — General Contractor
    # -----------------------------------------------------------------------
    {
        "name": "Keystone Build Group",
        "website": "https://keystonebuildgroup.com",
        "city": "Philadelphia",
        "state": "PA",
        "metro_area": "Philadelphia",
        "industry": "Construction & Trades",
        "sub_industry": "General Contractor",
        "employee_count_min": 12,
        "employee_count_max": 20,
        "estimated_revenue_min": 3_500_000,
        "estimated_revenue_max": 5_000_000,
        "description": (
            "Mid-size GC handling commercial tenant improvements and institutional "
            "renovations across the Philadelphia area. Subcontractor coordination and "
            "submittal tracking are managed in email threads and a shared Excel file."
        ),
        "probable_systems": json.dumps(["Procore (basic tier)", "Excel", "Email", "Dropbox"]),
        "pain_points": json.dumps([
            "Submittal log managed in Excel — version conflicts weekly",
            "Subcontractor daily reports collected via email and not centralized",
            "RFI response tracking handled in a personal inbox folder",
        ]),
        "ai_opportunities": json.dumps([
            "AI-assisted RFI log summarization and response drafting",
            "Automated submittal status tracking from email threads",
            "Daily report consolidation and anomaly flagging",
        ]),
        "ai_fit_score": 83,
        "ai_fit_reasons": json.dumps([
            "High document volume and coordination complexity",
            "Already using Procore — AI layer can sit on top",
        ]),
        "offer_conversion_score": 78,
        "offer_conversion_reasons": json.dumps([
            "Project manager explicitly cited document management pain in industry forum",
            "Revenue scale supports investment in workflow tooling",
        ]),
        "contacts": [
            {"first_name": "Jim", "last_name": "Donnelly", "title": "Project Manager", "is_decision_maker": True},
            {"first_name": "Karen", "last_name": "Lenz", "title": "Owner", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Construction / Trades — HVAC
    # -----------------------------------------------------------------------
    {
        "name": "TempRight HVAC Services",
        "website": "https://temprighthvac.com",
        "city": "Houston",
        "state": "TX",
        "metro_area": "Houston",
        "industry": "Construction & Trades",
        "sub_industry": "HVAC Contractor",
        "employee_count_min": 9,
        "employee_count_max": 18,
        "estimated_revenue_min": 2_000_000,
        "estimated_revenue_max": 4_000_000,
        "description": (
            "Residential and light-commercial HVAC installation and service company. "
            "Maintenance agreement renewals tracked in a paper binder. Technician "
            "upsell conversion is low because there is no follow-up process."
        ),
        "probable_systems": json.dumps(["ServiceTitan (entry tier)", "QuickBooks", "Paper binders"]),
        "pain_points": json.dumps([
            "Maintenance agreement renewals missed — estimated $80K/yr in lapsed revenue",
            "Technician recommendations for repairs rarely followed up on",
            "No automated seasonal tune-up campaign to past customers",
        ]),
        "ai_opportunities": json.dumps([
            "Automated maintenance renewal reminder sequences",
            "Post-visit AI follow-up on technician repair recommendations",
            "Seasonal campaign automation for AC and heating tune-ups",
        ]),
        "ai_fit_score": 87,
        "ai_fit_reasons": json.dumps([
            "ServiceTitan integration available for workflow triggers",
            "Maintenance agreement revenue recovery is quantifiable and immediate",
            "Seasonal demand patterns make automation highly predictable",
        ]),
        "offer_conversion_score": 85,
        "offer_conversion_reasons": json.dumps([
            "Owner can see the $80K lapse figure clearly",
            "Already paying for ServiceTitan — understands software ROI",
        ]),
        "contacts": [
            {"first_name": "Ray", "last_name": "Nguyen", "title": "Owner", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Healthcare — Dental
    # -----------------------------------------------------------------------
    {
        "name": "Bright Smile Dental",
        "website": "https://brightsmile-dental.com",
        "city": "Scottsdale",
        "state": "AZ",
        "metro_area": "Phoenix",
        "industry": "Healthcare",
        "sub_industry": "Dental Practice",
        "employee_count_min": 6,
        "employee_count_max": 10,
        "estimated_revenue_min": 1_200_000,
        "estimated_revenue_max": 2_500_000,
        "description": (
            "General dentistry practice with two treatment rooms and one hygienist. "
            "Appointment recall is handled by front desk calling patients manually "
            "from a printed list every Monday. Reappointment rate is below industry average."
        ),
        "probable_systems": json.dumps(["Dentrix", "Paper recall lists", "Phone calls", "Google Reviews"]),
        "pain_points": json.dumps([
            "Manual recall calling takes front desk 4 hrs/week",
            "Insurance verification done manually day-before — frequent delays",
            "No automated post-visit review request process",
        ]),
        "ai_opportunities": json.dumps([
            "Automated recall and reactivation SMS/email sequences from Dentrix",
            "AI-assisted insurance pre-verification workflow",
            "Post-visit review generation automation",
        ]),
        "ai_fit_score": 84,
        "ai_fit_reasons": json.dumps([
            "Dentrix has open API for integration",
            "Recall automation alone recovers measurable lost chair time",
        ]),
        "offer_conversion_score": 81,
        "offer_conversion_reasons": json.dumps([
            "Doctor understands revenue per chair and will respond to ROI math",
            "Front desk pain is visible and complained about openly",
        ]),
        "contacts": [
            {"first_name": "Amanda", "last_name": "Torres", "title": "Office Manager", "is_decision_maker": True},
            {"first_name": "Dr. Kevin", "last_name": "Park", "title": "Owner / DDS", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Healthcare — Physical Therapy
    # -----------------------------------------------------------------------
    {
        "name": "MoveBetter Physical Therapy",
        "website": "https://movebetterpt.com",
        "city": "Minneapolis",
        "state": "MN",
        "metro_area": "Minneapolis",
        "industry": "Healthcare",
        "sub_industry": "Physical Therapy Clinic",
        "employee_count_min": 5,
        "employee_count_max": 9,
        "estimated_revenue_min": 800_000,
        "estimated_revenue_max": 1_600_000,
        "description": (
            "Outpatient physical therapy clinic focused on orthopedic and sports rehab. "
            "Home exercise programs printed and handed to patients. Attendance drops "
            "sharply after week 3 of care with no intervention system."
        ),
        "probable_systems": json.dumps(["WebPT", "Paper HEP sheets", "Phone calls", "Google Calendar"]),
        "pain_points": json.dumps([
            "Patient drop-off after week 3 — no re-engagement workflow",
            "Home exercise program delivery is paper-based",
            "Intake paperwork completed on paper and re-entered into WebPT",
        ]),
        "ai_opportunities": json.dumps([
            "AI-driven patient engagement check-ins via SMS",
            "Digital HEP delivery with exercise video links and progress tracking",
            "Automated intake digital form with WebPT integration",
        ]),
        "ai_fit_score": 78,
        "ai_fit_reasons": json.dumps([
            "Patient retention improvement has direct revenue impact",
            "WebPT has developer tools for integration",
        ]),
        "offer_conversion_score": 72,
        "offer_conversion_reasons": json.dumps([
            "Clinic director is outcomes-focused and will respond to retention data",
        ]),
        "contacts": [
            {"first_name": "Sarah", "last_name": "Lindqvist", "title": "Clinic Director / PT", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Healthcare — Med Spa
    # -----------------------------------------------------------------------
    {
        "name": "Glow Aesthetic Studio",
        "website": "https://glowaestheticstudio.com",
        "city": "Boca Raton",
        "state": "FL",
        "metro_area": "Miami",
        "industry": "Healthcare",
        "sub_industry": "Med Spa",
        "employee_count_min": 5,
        "employee_count_max": 10,
        "estimated_revenue_min": 1_000_000,
        "estimated_revenue_max": 2_200_000,
        "description": (
            "Medical aesthetics practice offering Botox, fillers, laser treatments, "
            "and IV therapy. Rebooking and package upsells are pitch-dependent on "
            "individual staff — no systematic follow-up process exists."
        ),
        "probable_systems": json.dumps(["Vagaro", "Square", "Instagram DMs", "Paper intake forms"]),
        "pain_points": json.dumps([
            "Botox clients due for touch-up at 3 months are not systematically recalled",
            "Package upsell happens only if the injector remembers to mention it",
            "Before/after photos stored in personal phone — no organized portfolio",
        ]),
        "ai_opportunities": json.dumps([
            "Automated Botox recall sequences at treatment-appropriate intervals",
            "Post-visit AI upsell recommendation based on treatment history",
            "AI-assisted before/after photo organization and consent tracking",
        ]),
        "ai_fit_score": 81,
        "ai_fit_reasons": json.dumps([
            "High LTV clients with predictable rebooking cycles",
            "Vagaro supports automation integrations",
        ]),
        "offer_conversion_score": 77,
        "offer_conversion_reasons": json.dumps([
            "Owner is active on social media and is AI-curious",
            "Revenue per visit is high — retention ROI is obvious",
        ]),
        "contacts": [
            {"first_name": "Nicole", "last_name": "Barros", "title": "Owner / NP", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Additional Professional Services
    # -----------------------------------------------------------------------
    {
        "name": "Harbor View Financial Advisors",
        "website": "https://harborviewfa.com",
        "city": "Boston",
        "state": "MA",
        "metro_area": "Boston",
        "industry": "Professional Services",
        "sub_industry": "Financial Advisory",
        "employee_count_min": 4,
        "employee_count_max": 8,
        "estimated_revenue_min": 900_000,
        "estimated_revenue_max": 1_800_000,
        "description": (
            "Fee-only RIA serving mass-affluent clients with $500K-$5M in investable "
            "assets. Quarterly review preparation is done manually by pulling Orion "
            "reports and adding commentary in Word. Prospect follow-up is inconsistent."
        ),
        "probable_systems": json.dumps(["Orion", "Microsoft Word", "Outlook", "Redtail CRM (underused)"]),
        "pain_points": json.dumps([
            "Quarterly client review prep takes 2 hrs per client",
            "Prospect pipeline follow-up drops off after initial meeting",
            "Meeting notes not systematically captured or actioned",
        ]),
        "ai_opportunities": json.dumps([
            "AI-generated quarterly review narrative from portfolio data",
            "Automated prospect follow-up sequence post-meeting",
            "AI meeting note summarizer with action item extraction",
        ]),
        "ai_fit_score": 86,
        "ai_fit_reasons": json.dumps([
            "High per-client revenue justifies significant time investment",
            "Redtail CRM integration available",
        ]),
        "offer_conversion_score": 79,
        "offer_conversion_reasons": json.dumps([
            "Advisors are under compliance pressure and value defensible documentation",
        ]),
        "contacts": [
            {"first_name": "Paul", "last_name": "Renner", "title": "Principal Advisor", "is_decision_maker": True},
        ],
    },
    {
        "name": "NextStep HR Consulting",
        "website": "https://nextstephr.com",
        "city": "Washington",
        "state": "DC",
        "metro_area": "DC",
        "industry": "Professional Services",
        "sub_industry": "HR Consulting",
        "employee_count_min": 5,
        "employee_count_max": 10,
        "estimated_revenue_min": 800_000,
        "estimated_revenue_max": 1_600_000,
        "description": (
            "HR fractional advisory firm supporting 30 SMB clients with recruiting, "
            "compliance, and people ops. Job description drafting and employee handbook "
            "updates are done from scratch for every client engagement."
        ),
        "probable_systems": json.dumps(["Google Workspace", "BambooHR (some clients)", "Notion", "Zoom"]),
        "pain_points": json.dumps([
            "Job description writing is 3-4 hrs per role — fully manual",
            "Employee handbook updates require reading entire document to find sections",
            "No system to track which clients are due for compliance reviews",
        ]),
        "ai_opportunities": json.dumps([
            "AI job description generator from intake form",
            "AI-assisted handbook section search and drafting",
            "Automated compliance review scheduling based on client calendar",
        ]),
        "ai_fit_score": 83,
        "ai_fit_reasons": json.dumps([
            "Content-heavy deliverables with high repeatability",
            "Google Workspace is a low-friction integration base",
        ]),
        "offer_conversion_score": 76,
        "offer_conversion_reasons": json.dumps([
            "Owner tracks deliverable time carefully — AI ROI is immediately visible",
        ]),
        "contacts": [
            {"first_name": "Diane", "last_name": "Foster", "title": "Founder", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # More Construction
    # -----------------------------------------------------------------------
    {
        "name": "Ironwood Roofing & Exteriors",
        "website": "https://ironwoodroofing.com",
        "city": "Kansas City",
        "state": "MO",
        "metro_area": "Kansas City",
        "industry": "Construction & Trades",
        "sub_industry": "Roofing Contractor",
        "employee_count_min": 10,
        "employee_count_max": 18,
        "estimated_revenue_min": 2_500_000,
        "estimated_revenue_max": 4_500_000,
        "description": (
            "Storm restoration and residential re-roofing company. High lead volume "
            "after weather events with no CRM. Sales reps manage their own leads "
            "in individual spreadsheets — no pipeline visibility for the owner."
        ),
        "probable_systems": json.dumps(["Excel (per rep)", "QuickBooks", "EagleView", "Text messages"]),
        "pain_points": json.dumps([
            "No shared pipeline — owner has no real-time visibility into sales",
            "Follow-up after inspection is rep-dependent — leads go cold",
            "Insurance supplement documentation assembled manually per claim",
        ]),
        "ai_opportunities": json.dumps([
            "Shared CRM with AI-automated follow-up sequences post-inspection",
            "AI-assisted insurance supplement letter generation",
            "Pipeline dashboard with AI-flagged at-risk deals",
        ]),
        "ai_fit_score": 79,
        "ai_fit_reasons": json.dumps([
            "Storm restoration has very templatable sales and documentation flows",
            "Owner motivated by lack of visibility — clear system need",
        ]),
        "offer_conversion_score": 73,
        "offer_conversion_reasons": json.dumps([
            "High revenue but owner is conservative about software spending",
        ]),
        "contacts": [
            {"first_name": "Brett", "last_name": "Caldwell", "title": "Owner", "is_decision_maker": True},
            {"first_name": "Kim", "last_name": "Trujillo", "title": "Office Manager", "is_decision_maker": False},
        ],
    },
    {
        "name": "Clearwater Concrete & Masonry",
        "website": "https://clearwaterconcrete.com",
        "city": "Tampa",
        "state": "FL",
        "metro_area": "Tampa",
        "industry": "Construction & Trades",
        "sub_industry": "Concrete & Masonry",
        "employee_count_min": 8,
        "employee_count_max": 14,
        "estimated_revenue_min": 1_800_000,
        "estimated_revenue_max": 3_200_000,
        "description": (
            "Commercial and residential concrete flatwork and block masonry company. "
            "Bids submitted by fax or email from handwritten take-offs. Owner estimates "
            "they lose 20% of bids due to slow turnaround on proposals."
        ),
        "probable_systems": json.dumps(["Pen & paper take-offs", "QuickBooks", "Email", "Fax"]),
        "pain_points": json.dumps([
            "Estimate turnaround is 3-5 days — losing bids to faster competitors",
            "No tracking of which bid results came back — no win/loss analysis",
            "Material cost lookups done manually from supplier PDFs",
        ]),
        "ai_opportunities": json.dumps([
            "AI-assisted estimating tool from digital take-off data",
            "Bid outcome tracking with win/loss analytics",
            "Automated material cost database with supplier price import",
        ]),
        "ai_fit_score": 74,
        "ai_fit_reasons": json.dumps([
            "Estimating is the core business bottleneck",
        ]),
        "offer_conversion_score": 69,
        "offer_conversion_reasons": json.dumps([
            "Owner acknowledges losing bids but is skeptical of software",
            "ROI story needs to be tied to bid win rate improvement",
        ]),
        "contacts": [
            {"first_name": "Frank", "last_name": "Mancuso", "title": "Owner / Estimator", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Franchise Operators
    # -----------------------------------------------------------------------
    {
        "name": "Coastal Fitness Partners LLC",
        "website": "https://coastalfitnesspartners.com",
        "city": "San Diego",
        "state": "CA",
        "metro_area": "San Diego",
        "industry": "Franchise",
        "sub_industry": "Fitness Franchise",
        "employee_count_min": 12,
        "employee_count_max": 20,
        "estimated_revenue_min": 1_500_000,
        "estimated_revenue_max": 3_000_000,
        "description": (
            "Multi-unit operator of 3 boutique fitness franchise locations in San Diego. "
            "Member churn is above franchisor benchmark. Manager reporting across "
            "locations is consolidated manually in a shared Google Sheet each Monday."
        ),
        "probable_systems": json.dumps(["Mindbody", "Google Sheets", "Gusto", "Slack"]),
        "pain_points": json.dumps([
            "Weekly consolidated report takes 3 hrs — data pulled from 3 separate Mindbody accounts",
            "At-risk member detection happens too late — churn already occurred",
            "Manager one-on-ones lack structured data — run from memory",
        ]),
        "ai_opportunities": json.dumps([
            "Automated multi-location weekly reporting from Mindbody data",
            "AI-driven at-risk member detection and re-engagement sequence",
            "Manager scorecard automation with trend flagging",
        ]),
        "ai_fit_score": 85,
        "ai_fit_reasons": json.dumps([
            "Multi-location creates compounding reporting pain",
            "Mindbody has robust API",
        ]),
        "offer_conversion_score": 82,
        "offer_conversion_reasons": json.dumps([
            "Operator mindset — tracks unit economics closely",
            "Churn pain is financial and directly measurable",
        ]),
        "contacts": [
            {"first_name": "Jason", "last_name": "Park", "title": "Owner / Operator", "is_decision_maker": True},
        ],
    },
    {
        "name": "Lakeview Restoration Services",
        "website": "https://lakeviewrestoration.com",
        "city": "Orlando",
        "state": "FL",
        "metro_area": "Orlando",
        "industry": "Franchise",
        "sub_industry": "Restoration Franchise",
        "employee_count_min": 10,
        "employee_count_max": 18,
        "estimated_revenue_min": 2_200_000,
        "estimated_revenue_max": 4_000_000,
        "description": (
            "Water and fire damage restoration franchise operator with two territories "
            "in Central Florida. Job documentation for insurance claims is a major "
            "bottleneck — each file requires 30-50 photos, narrative, and scope."
        ),
        "probable_systems": json.dumps(["Xactimate", "Dropbox", "QuickBooks", "Phone calls"]),
        "pain_points": json.dumps([
            "Insurance claim documentation takes 6-8 hrs per job",
            "Supplement writing handled by owner personally — cannot scale",
            "No proactive lead follow-up from past water damage customers",
        ]),
        "ai_opportunities": json.dumps([
            "AI-assisted Xactimate narrative and scope generation from field notes",
            "Supplement recommendation engine based on line-item patterns",
            "Automated 6-month follow-up to past clients for proactive inspections",
        ]),
        "ai_fit_score": 91,
        "ai_fit_reasons": json.dumps([
            "Claim documentation is highly templated with clear AI upside",
            "Owner bottleneck on supplements is a direct revenue constraint",
            "Industry has growing AI tooling — high receptivity",
        ]),
        "offer_conversion_score": 88,
        "offer_conversion_reasons": json.dumps([
            "Owner tracks per-job profitability precisely",
            "Documentation savings of 3-4 hrs/job at $125/hr equivalent is compelling",
        ]),
        "contacts": [
            {"first_name": "Mike", "last_name": "Deluca", "title": "Owner / Operator", "is_decision_maker": True},
            {"first_name": "Carla", "last_name": "Vega", "title": "Operations Coordinator", "is_decision_maker": False},
        ],
    },
    {
        "name": "Magnolia Home Services Group",
        "website": "https://magnoliahomeservicesgroup.com",
        "city": "Charlotte",
        "state": "NC",
        "metro_area": "Charlotte",
        "industry": "Franchise",
        "sub_industry": "Home Services Franchise",
        "employee_count_min": 8,
        "employee_count_max": 16,
        "estimated_revenue_min": 1_400_000,
        "estimated_revenue_max": 2_800_000,
        "description": (
            "Multi-service home franchise operator (cleaning + window washing) with "
            "2 units in the Charlotte metro. Recurring service route optimization "
            "is done manually by the office manager each Sunday evening."
        ),
        "probable_systems": json.dumps(["Jobber", "QuickBooks", "Google Maps", "Paper timesheets"]),
        "pain_points": json.dumps([
            "Route planning takes office manager 3 hrs every Sunday",
            "No win-back sequence for lapsed recurring customers",
            "Upsell from cleaning to window washing is purely ad hoc",
        ]),
        "ai_opportunities": json.dumps([
            "AI-optimized weekly route planning from Jobber schedule data",
            "Automated win-back email sequence for lapsed recurring clients",
            "Cross-service upsell triggers based on service history",
        ]),
        "ai_fit_score": 77,
        "ai_fit_reasons": json.dumps([
            "Jobber API supports integration",
            "Route optimization and churn recovery are measurable wins",
        ]),
        "offer_conversion_score": 72,
        "offer_conversion_reasons": json.dumps([
            "Operator is numbers-focused — will respond to Sunday-hours-recovered pitch",
        ]),
        "contacts": [
            {"first_name": "Lisa", "last_name": "Truong", "title": "Owner / Operator", "is_decision_maker": True},
        ],
    },
    # -----------------------------------------------------------------------
    # Remaining companies — geographic diversity
    # -----------------------------------------------------------------------
    {
        "name": "Redwood Digital Solutions",
        "website": "https://redwooddigitalsolutions.com",
        "city": "San Jose",
        "state": "CA",
        "metro_area": "SF Bay Area",
        "industry": "Professional Services",
        "sub_industry": "IT Managed Services",
        "employee_count_min": 7,
        "employee_count_max": 13,
        "estimated_revenue_min": 1_600_000,
        "estimated_revenue_max": 3_000_000,
        "description": (
            "Managed service provider serving 50 SMB clients in the Bay Area. "
            "Monthly client billing reconciliation takes 2 full days. Ticket "
            "escalation paths are undocumented and handled ad hoc."
        ),
        "probable_systems": json.dumps(["ConnectWise", "QuickBooks", "Slack", "Excel"]),
        "pain_points": json.dumps([
            "Billing reconciliation is 2 days of manual ConnectWise exports and Excel work",
            "Ticket escalation not documented — senior engineers interrupted constantly",
            "Client QBR prep takes 4 hrs per account",
        ]),
        "ai_opportunities": json.dumps([
            "Automated billing reconciliation from ConnectWise data",
            "AI escalation routing based on ticket keywords and history",
            "AI-generated QBR summary from ticket and uptime data",
        ]),
        "ai_fit_score": 89,
        "ai_fit_reasons": json.dumps([
            "MSP workflows are extremely repetitive and data-rich",
            "ConnectWise has deep API",
        ]),
        "offer_conversion_score": 86,
        "offer_conversion_reasons": json.dumps([
            "MSP owners think in systems — high AI receptivity",
            "Billing automation alone recovers 2 days of labor per month",
        ]),
        "contacts": [
            {"first_name": "Kevin", "last_name": "Yamamoto", "title": "Owner / CTO", "is_decision_maker": True},
        ],
    },
    {
        "name": "Goldleaf Tax & Accounting",
        "website": "https://goldleaftax.com",
        "city": "Phoenix",
        "state": "AZ",
        "metro_area": "Phoenix",
        "industry": "Professional Services",
        "sub_industry": "Accounting & Tax",
        "employee_count_min": 5,
        "employee_count_max": 10,
        "estimated_revenue_min": 700_000,
        "estimated_revenue_max": 1_400_000,
        "description": (
            "CPA firm serving small business owners with tax prep, bookkeeping, and "
            "advisory. Document collection from clients at tax time is chaotic — "
            "emails, texts, and physical drop-offs all arrive simultaneously."
        ),
        "probable_systems": json.dumps(["Drake Tax", "QuickBooks Online", "Email", "Dropbox"]),
        "pain_points": json.dumps([
            "Document collection at tax season requires constant client chasing",
            "Engagement letters sent manually by email with manual tracking",
            "No systematic advisory upsell to tax-only clients",
        ]),
        "ai_opportunities": json.dumps([
            "Automated document request portal with reminder sequences",
            "AI-drafted engagement letter generator from client profile",
            "Advisory service upsell identification from tax return data patterns",
        ]),
        "ai_fit_score": 80,
        "ai_fit_reasons": json.dumps([
            "Tax season crunch is a recurring, highly automatable pain",
        ]),
        "offer_conversion_score": 74,
        "offer_conversion_reasons": json.dumps([
            "CPAs are methodical — need clear ROI and compliance safety",
        ]),
        "contacts": [
            {"first_name": "Susan", "last_name": "Meier", "title": "Managing CPA", "is_decision_maker": True},
        ],
    },
    {
        "name": "Lakeside Landscape & Design",
        "website": "https://lakesidelandscapedesign.com",
        "city": "Minneapolis",
        "state": "MN",
        "metro_area": "Minneapolis",
        "industry": "Construction & Trades",
        "sub_industry": "Landscaping",
        "employee_count_min": 8,
        "employee_count_max": 15,
        "estimated_revenue_min": 1_200_000,
        "estimated_revenue_max": 2_400_000,
        "description": (
            "Full-service landscaping and snow removal company with residential and "
            "commercial accounts. Seasonal service renewal outreach is done by the "
            "owner making personal phone calls in March and October."
        ),
        "probable_systems": json.dumps(["LMN", "QuickBooks", "Paper crew sheets", "Phone"]),
        "pain_points": json.dumps([
            "Seasonal renewal calls take owner 2 weeks every spring and fall",
            "Crew hours vs. job estimate tracked in paper — margin leakage unknown",
            "No upsell for landscape enhancements to existing maintenance clients",
        ]),
        "ai_opportunities": json.dumps([
            "Automated seasonal renewal and upsell email sequences",
            "Digital crew time tracking with AI margin analysis",
            "Enhancement upsell triggers based on service history and visit frequency",
        ]),
        "ai_fit_score": 73,
        "ai_fit_reasons": json.dumps([
            "Seasonal business model creates predictable automation windows",
        ]),
        "offer_conversion_score": 67,
        "offer_conversion_reasons": json.dumps([
            "Owner is traditional — personal touch is a stated value",
            "Framing as augmentation not replacement is important for this account",
        ]),
        "contacts": [
            {"first_name": "Tom", "last_name": "Erikson", "title": "Owner", "is_decision_maker": True},
        ],
    },
    {
        "name": "Capitol Hill Insurance Advisors",
        "website": "https://capitolhillinsurance.com",
        "city": "Washington",
        "state": "DC",
        "metro_area": "DC",
        "industry": "Professional Services",
        "sub_industry": "Insurance Agency",
        "employee_count_min": 5,
        "employee_count_max": 9,
        "estimated_revenue_min": 900_000,
        "estimated_revenue_max": 1_800_000,
        "description": (
            "Independent commercial insurance agency specializing in professional "
            "liability and cyber coverage for government contractors. Renewals tracked "
            "in an Outlook task list; quote comparisons assembled manually in Word."
        ),
        "probable_systems": json.dumps(["Applied Epic (partial)", "Outlook tasks", "Word", "Email"]),
        "pain_points": json.dumps([
            "Renewal tracking via Outlook tasks — items regularly fall through the cracks",
            "Quote comparison documents built manually for every renewal",
            "Cross-sell of cyber coverage not systematically offered to all clients",
        ]),
        "ai_opportunities": json.dumps([
            "Automated renewal pipeline with 90/60/30-day alert sequences",
            "AI-generated quote comparison summary from carrier data",
            "Cross-sell opportunity identification from policy gap analysis",
        ]),
        "ai_fit_score": 82,
        "ai_fit_reasons": json.dumps([
            "Applied Epic integration available",
            "Renewal cycle is 100% predictable — ideal for automation",
        ]),
        "offer_conversion_score": 78,
        "offer_conversion_reasons": json.dumps([
            "E&O risk from missed renewals is a strong compliance motivator",
        ]),
        "contacts": [
            {"first_name": "George", "last_name": "Patton", "title": "Owner / Agent", "is_decision_maker": True},
            {"first_name": "Maria", "last_name": "Santos", "title": "Account Manager", "is_decision_maker": False},
        ],
    },
    {
        "name": "Solano Property Management",
        "website": "https://solanopropertymgmt.com",
        "city": "Los Angeles",
        "state": "CA",
        "metro_area": "Los Angeles",
        "industry": "Professional Services",
        "sub_industry": "Property Management",
        "employee_count_min": 6,
        "employee_count_max": 12,
        "estimated_revenue_min": 1_100_000,
        "estimated_revenue_max": 2_200_000,
        "description": (
            "Residential property management firm managing 180 units across 14 "
            "buildings in LA County. Maintenance request routing is handled via "
            "text message to an on-call coordinator. Owner communications go out "
            "monthly via manually formatted PDF reports."
        ),
        "probable_systems": json.dumps(["Buildium", "Excel", "Text messages", "Word"]),
        "pain_points": json.dumps([
            "Maintenance request triage is entirely manual and often delayed overnight",
            "Monthly owner reports formatted manually — 1 hr per property owner",
            "Lease renewal outreach starts too late — units sit vacant",
        ]),
        "ai_opportunities": json.dumps([
            "AI maintenance request triage and vendor dispatch from Buildium",
            "Automated owner report generation from Buildium financial data",
            "Lease renewal early-warning and outreach automation",
        ]),
        "ai_fit_score": 84,
        "ai_fit_reasons": json.dumps([
            "Buildium API supports deep integration",
            "Repetitive reporting and triage across large unit count",
        ]),
        "offer_conversion_score": 80,
        "offer_conversion_reasons": json.dumps([
            "Owner is managing growth and explicitly seeking operational leverage",
        ]),
        "contacts": [
            {"first_name": "Ana", "last_name": "Solano", "title": "Owner / Principal PM", "is_decision_maker": True},
        ],
    },
    {
        "name": "Veritas Accounting Services",
        "website": "https://veritasaccounting.com",
        "city": "New York",
        "state": "NY",
        "metro_area": "NYC",
        "industry": "Professional Services",
        "sub_industry": "Bookkeeping & Accounting",
        "employee_count_min": 4,
        "employee_count_max": 8,
        "estimated_revenue_min": 600_000,
        "estimated_revenue_max": 1_200_000,
        "description": (
            "Outsourced bookkeeping firm serving 40 small business clients in NYC. "
            "Month-end close procedures are checklisted on paper per client. "
            "Variance commentary in client financials written from scratch monthly."
        ),
        "probable_systems": json.dumps(["QuickBooks Online", "Google Sheets", "Email", "Paper checklists"]),
        "pain_points": json.dumps([
            "Month-end close variance commentary takes 30-45 min per client",
            "Paper checklists create compliance risk — no audit trail",
            "New client onboarding involves manually recreating chart of accounts",
        ]),
        "ai_opportunities": json.dumps([
            "AI-generated variance commentary from QBO data",
            "Digital close checklist with completion tracking and audit trail",
            "Automated chart of accounts setup recommendations for new clients",
        ]),
        "ai_fit_score": 81,
        "ai_fit_reasons": json.dumps([
            "Highly repetitive monthly output across 40 clients",
            "QBO API is well-documented and robust",
        ]),
        "offer_conversion_score": 75,
        "offer_conversion_reasons": json.dumps([
            "Owner is a spreadsheet native — will appreciate systematic tooling",
        ]),
        "contacts": [
            {"first_name": "Rachel", "last_name": "Goldstein", "title": "Owner / Controller", "is_decision_maker": True},
        ],
    },
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------
def seed_sample_data(session: Session) -> int:
    """Insert sample companies and contacts. Returns count of new records added."""
    existing_names = {name for (name,) in session.query(Company.name).all()}
    added = 0

    for data in COMPANIES:
        if data["name"] in existing_names:
            continue

        contacts_data = data.pop("contacts", [])

        company = Company(
            source="seed_data",
            pipeline_stage="new_lead",
            revenue_is_estimated=True,
            ownership_style="owner-operated",
            enriched=False,
            **data,
        )
        session.add(company)
        session.flush()  # populate company.id before adding contacts

        for c in contacts_data:
            contact = Contact(
                company_id=company.id,
                first_name=c.get("first_name"),
                last_name=c.get("last_name"),
                title=c.get("title"),
                is_decision_maker=c.get("is_decision_maker", False),
                email_source="seed_data",
                do_not_contact=False,
            )
            session.add(contact)

        added += 1

    session.commit()
    return added


# ---------------------------------------------------------------------------
# Convenience initializer
# ---------------------------------------------------------------------------
def init_db_and_seed():
    """Create all tables (if needed) then seed sample data."""
    init_db()
    session = get_session()
    try:
        added = seed_sample_data(session)
        print(f"Seed complete: {added} new companies added.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db_and_seed()

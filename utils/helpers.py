import json

METRO_AREAS = [
    "New York City",
    "Miami",
    "Northern New Jersey",
    "Nashville",
    "Chicago",
    "Dallas",
    "Houston",
    "Atlanta",
    "Charlotte",
    "Tampa",
    "Orlando",
    "Phoenix",
    "Los Angeles",
    "Orange County",
    "San Diego",
    "San Francisco Bay Area",
    "Boston",
    "Philadelphia",
    "Washington DC",
    "Denver",
    "Minneapolis",
]

INDUSTRIES = {
    "Healthcare Practices": [
        "Dental Practice",
        "Orthodontic Clinic",
        "Oral Surgery Practice",
        "Chiropractic Clinic",
        "Physical Therapy Clinic",
        "Occupational Therapy Clinic",
        "Speech Therapy Clinic",
        "Behavioral Health Clinic",
        "Psychology Practice",
        "Psychiatry Practice",
        "Substance Abuse Treatment Clinic",
        "Dermatology Clinic",
        "Optometry Practice",
        "Ophthalmology Clinic",
        "Veterinary Clinic",
        "Animal Hospital",
        "Med Spa",
        "Aesthetic Clinic",
        "Weight Loss Clinic",
        "IV Therapy Clinic",
        "Fertility Clinic",
        "Sleep Clinic",
    ],
    "Accounting & Finance": [
        "CPA Firm",
        "Tax Preparation Firm",
        "Bookkeeping Firm",
        "Fractional CFO Firm",
        "Payroll Service Firm",
    ],
    "Law Firms": [
        "Family Law Firm",
        "Estate Planning Firm",
        "Immigration Law Firm",
        "Personal Injury Firm",
        "Employment Law Firm",
        "Real Estate Law Firm",
        "Bankruptcy Law Firm",
    ],
    "Marketing & Creative": [
        "Digital Marketing Agency",
        "SEO Agency",
        "Social Media Agency",
        "Paid Media Agency",
        "Branding Agency",
        "Creative Agency",
        "Public Relations Firm",
        "Video Production Agency",
    ],
    "IT & Technology Services": [
        "IT Managed Service Provider",
        "Cybersecurity Service Firm",
        "Cloud Consulting Firm",
        "IT Support Company",
        "Technology Consulting Firm",
    ],
    "Architecture & Engineering": [
        "Architecture Firm",
        "Engineering Firm",
        "Interior Design Firm",
        "Surveying Firm",
    ],
    "Real Estate & Property Management": [
        "Property Management Company",
        "HOA Management Firm",
        "Commercial Property Manager",
        "Residential Property Manager",
        "Real Estate Brokerage",
        "Commercial Real Estate Brokerage",
        "Real Estate Investment Firm",
    ],
    "Home Services": [
        "HVAC Contractor",
        "Plumbing Contractor",
        "Electrical Contractor",
        "Roofing Contractor",
        "Pest Control Company",
        "Garage Door Service Company",
        "Appliance Repair Company",
        "Pool Service Company",
        "Landscaping Company",
        "Tree Service Company",
        "Lawn Care Company",
        "Irrigation Service Company",
        "Window Cleaning Company",
        "Pressure Washing Company",
        "Residential Cleaning Company",
        "Commercial Cleaning Company",
        "Restoration Company",
        "Fire & Water Damage Restoration Firm",
        "Mold Remediation Company",
    ],
    "Construction & Remodeling": [
        "General Contractor",
        "Remodeling Contractor",
        "Kitchen Remodeling Company",
        "Bathroom Remodeling Company",
        "Flooring Contractor",
        "Painting Contractor",
        "Drywall Contractor",
        "Tile Contractor",
        "Fence Installation Company",
        "Deck Builder",
        "Concrete Contractor",
    ],
    "Automotive Services": [
        "Auto Repair Shop",
        "Collision Repair Shop",
        "Auto Body Shop",
        "Transmission Shop",
        "Tire Shop",
        "Mobile Mechanic Service",
        "Auto Detailing Company",
        "Car Wash Operator",
        "Fleet Maintenance Provider",
    ],
    "Franchise Operators": [
        "Multi-Unit Restaurant Franchisee",
        "Fitness Franchise Operator",
        "Childcare Franchise Operator",
        "Senior Care Franchise Operator",
        "Home Service Franchise Operator",
        "Retail Franchise Operator",
    ],
    "Fitness & Wellness": [
        "Gym",
        "Boutique Fitness Studio",
        "Yoga Studio",
        "Pilates Studio",
        "CrossFit Gym",
        "Martial Arts School",
        "Personal Training Studio",
    ],
    "Education Services": [
        "Tutoring Center",
        "Test Prep Company",
        "Music School",
        "Dance Studio",
        "Language School",
        "Private Learning Center",
        "STEM Education Center",
    ],
    "Childcare Services": [
        "Daycare Center",
        "Preschool",
        "After School Program",
    ],
    "Senior Care": [
        "Home Health Agency",
        "Senior Home Care Service",
        "Non-Medical Care Provider",
        "Adult Day Care Center",
    ],
    "Hospitality & Events": [
        "Event Planning Company",
        "Wedding Planner",
        "Corporate Event Planner",
        "Event Production Company",
        "Catering Company",
    ],
    "Logistics & Transportation": [
        "Freight Brokerage",
        "Small Freight Forwarder",
        "Trucking Dispatch Company",
        "Courier Company",
        "Last Mile Delivery Operator",
    ],
    "Manufacturing & Fabrication": [
        "Machine Shop",
        "Metal Fabrication Company",
        "Plastic Fabrication Shop",
        "Woodworking Shop",
        "Cabinet Manufacturer",
        "Sign Manufacturing Company",
        "Custom Printing Company",
        "Packaging Company",
    ],
    "Business Services": [
        "Document Management Company",
        "Printing Company",
        "Mailing Service",
        "Office Support Service",
        "Call Center",
        "Appointment Scheduling Service",
        "Virtual Assistant Agency",
    ],
    "Professional Services": [
        "Business Consulting Firm",
        "Operations Consulting Firm",
        "HR Consulting Firm",
        "Recruiting Agency",
        "Executive Search Firm",
        "Staffing Agency",
        "Insurance Brokerage",
        "Financial Advisory Firm",
        "Mortgage Brokerage",
    ],
    "Wealth & Family Office": [
        "Single Family Office",
        "Multi-Family Office",
        "Wealth Management Firm",
    ],
    "Ecommerce Operations": [
        "Small Ecommerce Brand",
        "Third-Party Amazon Seller",
        "Shopify-Based Retail Brand",
        "Subscription Product Company",
    ],
    "Media & Content": [
        "Podcast Production Studio",
        "Content Marketing Firm",
        "Newsletter Media Company",
        "Creator Management Agency",
    ],
}

PIPELINE_STAGES = [
    ("new_lead", "New Lead"),
    ("enriched", "Enriched"),
    ("draft_ready", "Draft Ready"),
    ("contacted", "Contacted"),
    ("replied", "Replied"),
    ("call_scheduled", "Call Scheduled"),
    ("audit_sold", "Audit Sold"),
    ("audit_delivered", "Audit Delivered"),
    ("implementation_opportunity", "Implementation Opportunity"),
    ("closed_lost", "Closed Lost"),
]

REVENUE_BANDS = [
    (0, 500000, "Under $500K"),
    (500000, 1000000, "$500K\u2013$1M"),
    (1000000, 2000000, "$1M\u2013$2M"),
    (2000000, 5000000, "$2M\u2013$5M"),
    (5000000, 10000000, "$5M\u2013$10M"),
    (10000000, 30000000, "$10M\u2013$30M"),
]

_STAGE_COLORS = {
    "new_lead": "#A8C5DA",
    "enriched": "#7EB8D4",
    "draft_ready": "#F5C842",
    "contacted": "#F5A623",
    "replied": "#7ED321",
    "call_scheduled": "#4A90E2",
    "audit_sold": "#BD10E0",
    "audit_delivered": "#9B9B9B",
    "implementation_opportunity": "#50E3C2",
    "closed_lost": "#D0021B",
}


def format_revenue(min_val: int, max_val: int, is_estimated: bool) -> str:
    """Returns a human-readable revenue range string, e.g. '$1M – $2M (est.)'"""

    def _fmt(val: int) -> str:
        if val == 0:
            return "$0"
        if val >= 1_000_000:
            millions = val / 1_000_000
            return f"${millions:g}M"
        if val >= 1_000:
            thousands = val / 1_000
            return f"${thousands:g}K"
        return f"${val:,}"

    label = f"{_fmt(min_val)} \u2013 {_fmt(max_val)}"
    if is_estimated:
        label += " (est.)"
    return label


def format_employees(min_val: int, max_val: int) -> str:
    """Returns a human-readable employee range string, e.g. '5–12 employees'"""
    return f"{min_val}\u2013{max_val} employees"


def get_stage_label(stage_key: str) -> str:
    """Returns the display label for a pipeline stage key."""
    for key, label in PIPELINE_STAGES:
        if key == stage_key:
            return label
    return stage_key


def get_stage_color(stage_key: str) -> str:
    """Returns a hex color string for the given pipeline stage, for UI display."""
    return _STAGE_COLORS.get(stage_key, "#CCCCCC")


def compliance_warning() -> str:
    """Returns the standard compliance notice string for display in the UI."""
    return (
        "\u26a0\ufe0f Compliance Notice: Every email requires manual review and approval "
        "before sending. This system does not support bulk or automated email sending."
    )


def truncate(text: str, max_len: int = 150) -> str:
    """Truncates text to max_len characters, appending '...' if truncated."""
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def parse_json_field(value) -> list:
    """
    Safely parses a JSON string field into a Python list.
    Returns an empty list on any failure.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return result
        return []
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def brandon_bio() -> str:
    """
    Returns a short professional bio paragraph for Brandon Rye.
    """
    return (
        "Brandon Rye brings experience from Citigroup investment banking, FedEx operational "
        "analytics ($18M cost reduction), and FP&A leadership. Columbia MBA. He focuses on "
        "helping business owners clean up operational systems and identify practical automation "
        "opportunities."
    )


def founder_credibility_block() -> str:
    """
    Returns a longer credibility block suitable for email footers or about pages,
    covering Brandon's background across Future Legend, Preface Global, Citigroup,
    Van Wagner, and FedEx.
    """
    return (
        "Brandon Rye is the founder of Future Legend, an operational systems consultancy "
        "helping growing businesses eliminate inefficiency and find practical automation wins. "
        "His background spans investment banking at Citigroup, sponsorship analytics at "
        "Van Wagner, and global operations at FedEx, where he led cross-functional initiatives "
        "that reduced costs by $18M. He holds an MBA from Columbia Business School and has "
        "served in FP&A and strategic planning roles at Preface Global. Brandon takes an "
        "operator-first approach: before recommending any technology, he maps the underlying "
        "process, identifies where time and money are leaking, and designs the simplest "
        "solution that actually gets used. He works directly with business owners — not "
        "through layers of project managers — and focuses on delivering clear, actionable "
        "findings rather than lengthy decks."
    )

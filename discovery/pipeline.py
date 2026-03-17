"""
Modular company discovery pipeline for finding SMB companies.

Provides data sources (manual entry, CSV import, Claude AI research) and
top-level helpers for deduplication, export, and duplicate checking.
"""

from __future__ import annotations

import io
import json
import re
import string
from abc import ABC, abstractmethod
from typing import Optional

import anthropic
import pandas as pd
from sqlalchemy.orm import Session

from database.models import Company, Contact


# ---------------------------------------------------------------------------
# Normalization helper
# ---------------------------------------------------------------------------

_STRIP_SUFFIXES = re.compile(
    r"\b(llc|inc|corp|co|ltd)\b\.?$",
    re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    """Lowercase, strip legal suffixes and trailing punctuation for dedup."""
    if not name:
        return ""
    normalized = name.strip().lower()
    normalized = _STRIP_SUFFIXES.sub("", normalized).strip()
    normalized = normalized.rstrip(string.punctuation).strip()
    return normalized


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class DataSource(ABC):
    """Base class for all company discovery data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this source."""

    @abstractmethod
    def search(
        self,
        query: Optional[str] = None,
        metro_area: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> list[dict]:
        """Return a list of company dicts matching the given criteria."""


# ---------------------------------------------------------------------------
# ManualEntrySource
# ---------------------------------------------------------------------------

class ManualEntrySource(DataSource):
    """Handles companies entered manually through the UI."""

    @property
    def name(self) -> str:
        return "manual_entry"

    def search(
        self,
        query: Optional[str] = None,
        metro_area: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> list[dict]:
        # Manual entries go through the UI; nothing to return here.
        return []

    def add_company(self, session: Session, company_data: dict) -> Company:
        """
        Create and persist a Company from a dict of field values.

        Required fields: name, city, state.
        Raises ValueError if any required field is missing or blank.
        """
        required = ("name", "city", "state")
        for field in required:
            if not company_data.get(field, "").strip():
                raise ValueError(
                    f"Missing required field for manual entry: '{field}'"
                )

        company = Company(
            name=company_data["name"].strip(),
            city=company_data["city"].strip(),
            state=company_data["state"].strip(),
            source="manual_entry",
            website=company_data.get("website"),
            metro_area=company_data.get("metro_area"),
            industry=company_data.get("industry"),
            sub_industry=company_data.get("sub_industry"),
            employee_count_min=company_data.get("employee_count_min"),
            employee_count_max=company_data.get("employee_count_max"),
            estimated_revenue_min=company_data.get("estimated_revenue_min"),
            estimated_revenue_max=company_data.get("estimated_revenue_max"),
            description=company_data.get("description"),
            notes=company_data.get("notes"),
            tags=company_data.get("tags"),
            pipeline_stage=company_data.get("pipeline_stage", "new_lead"),
        )
        session.add(company)
        session.flush()
        return company


# ---------------------------------------------------------------------------
# CSVImportSource
# ---------------------------------------------------------------------------

class CSVImportSource(DataSource):
    """Imports companies from a CSV file."""

    COLUMN_MAP: dict[str, str] = {
        # Company name
        "Company Name": "name",
        "company_name": "name",
        "Business Name": "name",
        "Name": "name",
        # Website
        "Website": "website",
        "URL": "website",
        "website": "website",
        # City
        "City": "city",
        "city": "city",
        # State
        "State": "state",
        "state": "state",
        # Industry
        "Industry": "industry",
        "industry": "industry",
        "Sector": "industry",
        # Employees
        "Employees": "employee_count_min",
        "Employee Count": "employee_count_min",
        "employees": "employee_count_min",
        "Headcount": "employee_count_min",
        # Revenue
        "Revenue": "estimated_revenue_min",
        "Annual Revenue": "estimated_revenue_min",
        "revenue": "estimated_revenue_min",
        # Description
        "Description": "description",
        "About": "description",
        "description": "description",
        # Contact — these map to Contact fields, handled separately
        "Contact Name": "_contact_name",
        "Owner Name": "_contact_name",
        "contact_name": "_contact_name",
        "Contact Email": "_contact_email",
        "Email": "_contact_email",
        "email": "_contact_email",
        "Contact Title": "_contact_title",
        "Title": "_contact_title",
        "title": "_contact_title",
        "Phone": "_contact_phone",
        "phone": "_contact_phone",
    }

    @property
    def name(self) -> str:
        return "csv_import"

    def search(
        self,
        query: Optional[str] = None,
        metro_area: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> list[dict]:
        return []

    def _auto_map_columns(self, csv_columns: list[str]) -> dict[str, str]:
        """
        Build a {csv_column -> model_field} mapping automatically by matching
        CSV headers against COLUMN_MAP keys (case-insensitive).
        """
        mapping: dict[str, str] = {}
        lower_map = {k.lower(): v for k, v in self.COLUMN_MAP.items()}
        for col in csv_columns:
            target = lower_map.get(col.strip().lower())
            if target:
                mapping[col] = target
        return mapping

    def import_csv(
        self,
        session: Session,
        file_buffer,
        column_mapping: Optional[dict] = None,
    ) -> dict:
        """
        Read a CSV, create Company + Contact records, skip duplicates.

        Returns {"imported": int, "skipped": int, "errors": list[str]}.
        """
        imported = 0
        skipped = 0
        errors: list[str] = []

        try:
            df = pd.read_csv(file_buffer, dtype=str).fillna("")
        except Exception as exc:
            return {"imported": 0, "skipped": 0, "errors": [f"Failed to read CSV: {exc}"]}

        mapping = column_mapping or self._auto_map_columns(list(df.columns))

        for row_idx, row in df.iterrows():
            try:
                # Map raw row to model fields
                fields: dict[str, str] = {}
                for csv_col, model_field in mapping.items():
                    if csv_col in row:
                        fields[model_field] = str(row[csv_col]).strip()

                company_name = fields.get("name", "")
                if not company_name:
                    skipped += 1
                    continue

                city = fields.get("city", "")

                # Duplicate check
                if check_duplicate(session, company_name, city):
                    skipped += 1
                    continue

                # Build Company
                def _int_or_none(val: str) -> Optional[int]:
                    try:
                        cleaned = re.sub(r"[^\d]", "", val)
                        return int(cleaned) if cleaned else None
                    except (ValueError, TypeError):
                        return None

                company = Company(
                    name=company_name,
                    city=city or None,
                    state=fields.get("state") or None,
                    website=fields.get("website") or None,
                    industry=fields.get("industry") or None,
                    employee_count_min=_int_or_none(fields.get("employee_count_min", "")),
                    estimated_revenue_min=_int_or_none(fields.get("estimated_revenue_min", "")),
                    description=fields.get("description") or None,
                    source="csv_import",
                    pipeline_stage="new_lead",
                )
                session.add(company)
                session.flush()  # get company.id

                # Build Contact if contact fields present
                contact_name = fields.get("_contact_name", "")
                contact_email = fields.get("_contact_email", "")
                contact_title = fields.get("_contact_title", "")
                contact_phone = fields.get("_contact_phone", "")

                if any([contact_name, contact_email, contact_title, contact_phone]):
                    first_name: Optional[str] = None
                    last_name: Optional[str] = None
                    if contact_name:
                        parts = contact_name.split(maxsplit=1)
                        first_name = parts[0] if parts else None
                        last_name = parts[1] if len(parts) > 1 else None

                    contact = Contact(
                        company_id=company.id,
                        first_name=first_name,
                        last_name=last_name,
                        title=contact_title or None,
                        email=contact_email or None,
                        phone=contact_phone or None,
                        is_decision_maker=False,
                    )
                    session.add(contact)

                imported += 1

            except Exception as exc:
                errors.append(f"Row {row_idx + 2}: {exc}")

        session.flush()
        return {"imported": imported, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# ClaudeResearchSource
# ---------------------------------------------------------------------------

class ClaudeResearchSource(DataSource):
    """Uses the Anthropic Claude API to surface real companies matching criteria."""

    @property
    def name(self) -> str:
        return "claude_research"

    def search(
        self,
        query: Optional[str] = None,
        metro_area: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> list[dict]:
        return []

    def research_companies(
        self,
        api_key: str,
        query: str,
        metro_area: str,
        industry: str,
        count: int = 10,
    ) -> list[dict]:
        """
        Ask Claude to identify real companies matching the given criteria.

        NOTE: This is a research-assist tool, not a web scraper. Results
        represent Claude's training-data knowledge and should be verified
        by the user before outreach.

        Returns a list of dicts with keys:
          name, city, state, industry, sub_industry,
          estimated_employees, description, probable_decision_maker_title
        """
        prompt = (
            f"List real companies you are aware of that match these criteria. "
            f"Only include companies you have genuine knowledge of. "
            f"Do NOT fabricate company names or details. "
            f"If you are unsure about a company, omit it. "
            f"Return JSON array.\n\n"
            f"Criteria:\n"
            f"- Metro area: {metro_area}\n"
            f"- Industry: {industry}\n"
            f"- Additional query: {query}\n"
            f"- Number of companies requested: {count}\n\n"
            f"Return a JSON array of objects with these fields:\n"
            f"  name, city, state, industry, sub_industry, "
            f"estimated_employees, description, probable_decision_maker_title\n\n"
            f"Respond with ONLY the JSON array, no explanation or markdown fencing."
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            results = json.loads(raw)
            if not isinstance(results, list):
                return []
            return results
        except json.JSONDecodeError:
            return []


# ---------------------------------------------------------------------------
# Top-level pipeline functions
# ---------------------------------------------------------------------------

def discover(
    session: Session,
    sources: list[DataSource],
    metro_area: Optional[str] = None,
    industry: Optional[str] = None,
    query: Optional[str] = None,
) -> list[dict]:
    """
    Run search across all provided sources and return a deduplicated list
    of company dicts.

    Deduplication key: normalized(name) + normalized(city).
    """
    seen: set[tuple[str, str]] = set()
    combined: list[dict] = []

    for source in sources:
        results = source.search(query=query, metro_area=metro_area, industry=industry)
        for company_dict in results:
            norm_name = _normalize_name(company_dict.get("name", ""))
            norm_city = (company_dict.get("city") or "").strip().lower()
            key = (norm_name, norm_city)
            if key in seen or not norm_name:
                continue
            seen.add(key)
            combined.append(company_dict)

    return combined


def export_companies_csv(
    session: Session,
    company_ids: Optional[list[int]] = None,
    filters: Optional[dict] = None,
) -> bytes:
    """
    Export companies (and their primary contact) to CSV bytes suitable for
    st.download_button.

    Pass company_ids to export specific records, or filters dict with any of:
      metro_area, industry, pipeline_stage, min_score
    """
    query = session.query(Company)

    if company_ids is not None:
        query = query.filter(Company.id.in_(company_ids))
    elif filters:
        if filters.get("metro_area"):
            query = query.filter(Company.metro_area == filters["metro_area"])
        if filters.get("industry"):
            query = query.filter(Company.industry == filters["industry"])
        if filters.get("pipeline_stage"):
            query = query.filter(Company.pipeline_stage == filters["pipeline_stage"])
        if filters.get("min_score") is not None:
            query = query.filter(Company.ai_fit_score >= filters["min_score"])

    companies: list[Company] = query.all()

    rows: list[dict] = []
    for c in companies:
        # Find primary contact: prefer decision maker, otherwise first contact
        primary: Optional[Contact] = None
        for contact in c.contacts:
            if contact.is_decision_maker:
                primary = contact
                break
        if primary is None and c.contacts:
            primary = c.contacts[0]

        contact_name = ""
        if primary:
            parts = filter(None, [primary.first_name, primary.last_name])
            contact_name = " ".join(parts)

        rows.append(
            {
                "name": c.name,
                "website": c.website or "",
                "city": c.city or "",
                "state": c.state or "",
                "metro_area": c.metro_area or "",
                "industry": c.industry or "",
                "sub_industry": c.sub_industry or "",
                "employee_count_min": c.employee_count_min if c.employee_count_min is not None else "",
                "employee_count_max": c.employee_count_max if c.employee_count_max is not None else "",
                "estimated_revenue_min": c.estimated_revenue_min if c.estimated_revenue_min is not None else "",
                "estimated_revenue_max": c.estimated_revenue_max if c.estimated_revenue_max is not None else "",
                "ai_fit_score": c.ai_fit_score if c.ai_fit_score is not None else "",
                "offer_conversion_score": c.offer_conversion_score if c.offer_conversion_score is not None else "",
                "pipeline_stage": c.pipeline_stage or "",
                "description": c.description or "",
                "notes": c.notes or "",
                "tags": c.tags or "",
                "contact_name": contact_name,
                "contact_title": primary.title if primary else "",
                "contact_email": primary.email if primary else "",
                "contact_phone": primary.phone if primary else "",
            }
        )

    df = pd.DataFrame(rows)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()


def check_duplicate(
    session: Session,
    name: str,
    city: str,
) -> Optional[Company]:
    """
    Return the existing Company if a duplicate is found, otherwise None.

    Comparison uses normalized names (strips legal suffixes, lowercases) and
    exact city match (case-insensitive).
    """
    norm_input = _normalize_name(name)
    if not norm_input:
        return None

    norm_city = (city or "").strip().lower()

    # Pull candidates with the same first character to limit in-memory work
    # on large datasets; fall back to full scan if needed.
    candidates: list[Company] = session.query(Company).filter(
        Company.name.ilike(f"{name[0]}%") if name else True
    ).all()

    for candidate in candidates:
        if _normalize_name(candidate.name) == norm_input:
            candidate_city = (candidate.city or "").strip().lower()
            if candidate_city == norm_city:
                return candidate

    return None

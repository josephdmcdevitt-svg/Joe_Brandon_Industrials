"""
Generate personalized email drafts for all leads with email addresses.
Uses the fallback template (no API key needed) with industry-specific pain points.

Output: data/email_drafts.csv with personalized subject + body for each lead.
"""
import csv
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from messaging.drafts import generate_draft_fallback


def main():
    input_file = "data/master_leads_enriched.csv"
    output_file = "data/email_drafts.csv"

    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Filter to leads with emails
    leads_with_email = [
        r for r in rows
        if r.get("email", "").strip() not in ("", "N/A")
    ]

    print(f"Total leads: {len(rows)}")
    print(f"Leads with email: {len(leads_with_email)}")
    print(f"Generating drafts...")

    drafts = []
    for row in leads_with_email:
        company_name = row["company_name"].strip()
        city = row["city"].strip()
        state = row["state"].strip()
        industry = row["industry"].strip()
        email = row["email"].strip()

        # Parse contact name
        contact_raw = row.get("owner_or_contact", "").strip()
        if contact_raw and contact_raw not in ("Owner", "Principal", "Managing Partner", "Practice Owner", "N/A"):
            # Try to get first name
            parts = contact_raw.split()
            first_name = parts[0] if parts else "there"
            # Skip titles like "Dr."
            if first_name.endswith(".") and len(parts) > 1:
                first_name = parts[1]
        else:
            first_name = "there"

        contact_title = row.get("contact_title", "Owner").strip()

        company_dict = {
            "name": company_name,
            "industry": industry,
        }
        contact_dict = {
            "first_name": first_name,
            "title": contact_title,
            "email": email,
        }

        result = generate_draft_fallback(company_dict, contact_dict, "email_initial")

        drafts.append({
            "company_name": company_name,
            "city": city,
            "state": state,
            "industry": industry,
            "contact_name": contact_raw,
            "contact_title": contact_title,
            "contact_email": email,
            "subject": result["subject"],
            "body": result["body"],
        })

    # Write drafts CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company_name", "city", "state", "industry",
            "contact_name", "contact_title", "contact_email",
            "subject", "body"
        ])
        writer.writeheader()
        writer.writerows(drafts)

    print(f"Generated {len(drafts)} personalized email drafts")
    print(f"Written to: {output_file}")

    # Show a few examples
    print(f"\n--- SAMPLE DRAFTS ---\n")
    for i, d in enumerate(drafts[:3]):
        print(f"=== Draft {i+1}: {d['company_name']} ({d['industry']}) ===")
        print(f"To: {d['contact_name']} <{d['contact_email']}>")
        print(f"Subject: {d['subject']}")
        print(f"\n{d['body']}")
        print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()

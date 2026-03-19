"""
Email Scraper Worker — runs continuously on your Mac, scrapes business websites
for email addresses using the local Ollama/Qwen API on the Golf Sim PC.

Usage:
    python3 email_scraper_worker.py

What it does:
1. Reads master_leads_enriched.csv
2. Finds leads with a website but no email
3. Skips any already-scraped leads
4. Fetches each website and uses Qwen to extract emails
5. Updates master_leads_enriched.csv with found emails
6. Regenerates email_drafts.csv and outreach_export.csv
7. Logs everything to data/scraper_log.csv
8. Sleeps and repeats (catches new leads added to the CSV)

Runs forever until you Ctrl+C it.
"""

import csv
import json
import re
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_URL = "http://192.168.1.123:11434/api/generate"
OLLAMA_MODEL = "qwen3.5:9b"
DATA_DIR = Path(__file__).parent / "data"
MASTER_CSV = DATA_DIR / "master_leads_enriched.csv"  # read-only source
STAGING_CSV = DATA_DIR / "qwen_found_emails.csv"    # Qwen writes here, validated before merging
DRAFTS_CSV = DATA_DIR / "email_drafts.csv"
EXPORT_CSV = DATA_DIR / "outreach_export.csv"
LOG_CSV = DATA_DIR / "scraper_log.csv"
SCRAPED_TRACKER = DATA_DIR / "scraped_tracker.txt"

# How long to wait between full passes
SLEEP_BETWEEN_PASSES = 300  # 5 minutes
# How long to wait between individual site fetches (be nice)
SLEEP_BETWEEN_SITES = 0.5

# SSL context that doesn't verify (some small biz sites have bad certs)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_scraped_tracker():
    """Load set of already-scraped company keys."""
    if not SCRAPED_TRACKER.exists():
        return set()
    with open(SCRAPED_TRACKER, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_scraped_key(key):
    """Append a scraped key to the tracker file."""
    with open(SCRAPED_TRACKER, "a") as f:
        f.write(key + "\n")


def fetch_page(url, timeout=5):
    """Fetch a webpage and return its text content."""
    if not url.startswith("http"):
        url = "https://" + url
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.read().decode("utf-8", errors="replace")[:50000]  # Cap at 50KB
    except Exception:
        return None


def ask_qwen(prompt, max_retries=2):
    """Send a prompt to Qwen via Ollama API."""
    data = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "").strip()
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(2)
    return None


def extract_emails_with_regex(html):
    """Quick regex pass to find obvious emails."""
    if not html:
        return []
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    found = re.findall(pattern, html)
    # Filter out common false positives
    blacklist_domains = {"example.com", "domain.com", "email.com", "yoursite.com",
                 "sentry.io", "wixpress.com", "wordpress.com", "googleapis.com",
                 "w3.org", "schema.org", "googleusercontent.com", "gstatic.com",
                 "squarespace.com", "wix.com", "godaddy.com", "shopify.com",
                 "mailchimp.com", "hubspot.com", "zendesk.com", "intercom.io",
                 "crisp.chat", "tawk.to", "livechat.com", "drift.com",
                 "dentalmarketer.ca", "dentalmarketer.com", "webdesign.com"}
    # Blacklist usernames commonly belonging to web devs, not the business
    blacklist_prefixes = {"noreply", "no-reply", "mailer-daemon", "postmaster",
                          "webmaster", "developer", "dev", "support@wix",
                          "support@squarespace", "lukas", "developer"}
    cleaned = []
    for email in found:
        email_lower = email.lower()
        domain = email_lower.split("@")[1]
        prefix = email_lower.split("@")[0]
        if (domain not in blacklist_domains
                and prefix not in blacklist_prefixes
                and not email_lower.endswith(".png")
                and not email_lower.endswith(".jpg")
                and not email_lower.endswith(".svg")
                and "unsubscribe" not in email_lower
                and "privacy" not in email_lower):
            cleaned.append(email_lower)
    return list(set(cleaned))


def extract_emails_with_qwen(html, company_name):
    """Use Qwen to extract business email from page content."""
    # Truncate HTML for Qwen
    text = html[:8000]
    prompt = f"""Extract the business contact email address for {company_name} from this webpage content.
Return ONLY the email address. If multiple emails found, return the best business contact email (info@, office@, contact@, or owner's personal email).
If no email is found, return exactly: NONE

Webpage content:
{text}"""

    result = ask_qwen(prompt)
    if not result or "NONE" in result.upper():
        return None
    # Extract email from response
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', result)
    return emails[0].lower() if emails else None


def validate_email_with_qwen(emails, company_name, website):
    """Ask Qwen to pick the best business email from a list, filtering out web dev junk."""
    if not emails:
        return None
    if len(emails) == 1:
        # Quick check — does domain match the website?
        email_domain = emails[0].split("@")[1]
        website_clean = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        if email_domain == website_clean or "info@" in emails[0] or "office@" in emails[0] or "contact@" in emails[0] or "hello@" in emails[0]:
            return emails[0]

    email_list = "\n".join(emails[:10])
    prompt = f"""I found these email addresses on the website for {company_name} ({website}):

{email_list}

Which one is the actual business contact email for {company_name}?
Ignore emails belonging to web designers, marketing agencies, software companies, or third-party services.
Return ONLY the single best business email. If none of them belong to {company_name}, return NONE."""

    result = ask_qwen(prompt)
    if not result or "NONE" in result.upper():
        return None
    found = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', result)
    if found and found[0].lower() in [e.lower() for e in emails]:
        return found[0].lower()
    return None


def log_result(company_name, city, website, email, method):
    """Append to scraper log."""
    file_exists = LOG_CSV.exists()
    with open(LOG_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "company_name", "city", "website", "email_found", "method"])
        writer.writerow([datetime.now().isoformat(), company_name, city, website, email or "N/A", method])


def get_targets():
    """Find leads with website but no email that haven't been scraped yet."""
    scraped = load_scraped_tracker()

    with open(MASTER_CSV, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    targets = []
    for r in rows:
        website = r.get("website", "").strip()
        email = r.get("email", "").strip()
        key = f"{r['company_name'].strip().lower()}|{r['city'].strip().lower()}"

        if website not in ("", "N/A") and email in ("", "N/A") and key not in scraped:
            targets.append(r)

    return targets


def update_master_email(company_name, city, email):
    """Write found email to staging CSV (not master). Must be validated before merging."""
    file_exists = STAGING_CSV.exists()
    with open(STAGING_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["company_name", "city", "email_found", "timestamp"])
        writer.writerow([company_name, city, email, datetime.now().isoformat()])
    return True


# ---------------------------------------------------------------------------
# Main scraping loop
# ---------------------------------------------------------------------------
def scrape_one(lead):
    """Scrape a single lead. Returns email or None."""
    company = lead["company_name"].strip()
    city = lead["city"].strip()
    website = lead["website"].strip()
    key = f"{company.lower()}|{city.lower()}"

    # Fetch homepage
    html = fetch_page(website)
    if not html:
        save_scraped_key(key)
        log_result(company, city, website, None, "fetch_failed")
        return None

    # Try regex first (fast)
    emails = extract_emails_with_regex(html)
    if emails:
        email = validate_email_with_qwen(emails, company, website)
        if email:
            save_scraped_key(key)
            log_result(company, city, website, email, "regex_homepage")
            return email

    # Try /contact page (just one, fastest)
    base = website.rstrip("/")
    contact_html = fetch_page(base + "/contact", timeout=5)
    if contact_html:
        emails = extract_emails_with_regex(contact_html)
        if emails:
            email = validate_email_with_qwen(emails, company, website)
            if email:
                save_scraped_key(key)
                log_result(company, city, website, email, "regex_contact")
                return email

    # Skip Qwen fallback — regex is fast and sufficient.
    # Qwen was too slow (30s per site) and rarely found emails regex missed.

    save_scraped_key(key)
    log_result(company, city, website, None, "not_found")
    return None


def run_pass():
    """Run one full pass through all unscraped leads."""
    targets = get_targets()
    if not targets:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No new targets. Sleeping...")
        return 0

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting pass: {len(targets)} websites to check")

    found = 0
    for i, lead in enumerate(targets):
        company = lead["company_name"].strip()
        city = lead["city"].strip()

        email = scrape_one(lead)
        if email:
            update_master_email(company, city, email)
            found += 1
            print(f"  [{i+1}/{len(targets)}] FOUND: {company} ({city}) -> {email}")
        else:
            if (i + 1) % 25 == 0:
                print(f"  [{i+1}/{len(targets)}] Progress... ({found} emails found so far)")

        time.sleep(SLEEP_BETWEEN_SITES)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pass complete. Found {found} new emails.")
    return found


def main():
    print("=" * 60)
    print("Email Scraper Worker")
    print(f"Ollama API: {OLLAMA_URL}")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Master CSV: {MASTER_CSV}")
    print("=" * 60)

    # Verify Ollama is reachable
    test = ask_qwen("Say OK")
    if test is None:
        print("ERROR: Cannot reach Ollama API. Is the Golf Sim PC running?")
        return
    print(f"Ollama connected. Test response: {test[:50]}")
    print()

    total_found = 0
    pass_num = 0

    while True:
        try:
            pass_num += 1
            print(f"\n--- Pass #{pass_num} ---")
            found = run_pass()
            total_found += found

            # Count current stats
            with open(MASTER_CSV, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            has_email = sum(1 for r in rows if r.get("email", "").strip() not in ("", "N/A"))
            print(f"Total emails in database: {has_email}")
            print(f"Total found this session: {total_found}")

            if found == 0:
                print(f"Sleeping {SLEEP_BETWEEN_PASSES}s before next pass...")
                time.sleep(SLEEP_BETWEEN_PASSES)
            else:
                print("Starting next pass immediately...")

        except KeyboardInterrupt:
            print(f"\nStopped. Found {total_found} emails this session.")
            break
        except Exception as e:
            print(f"Error: {e}. Retrying in 60s...")
            time.sleep(60)


if __name__ == "__main__":
    main()

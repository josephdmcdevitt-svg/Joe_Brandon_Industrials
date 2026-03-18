import streamlit as st
import pandas as pd
import sqlite3
import os
import csv
from pathlib import Path

st.set_page_config(
    page_title="AI Systems Audit Pipeline",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Database setup (raw sqlite3 — no SQLAlchemy needed)
# ---------------------------------------------------------------------------
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "outreach.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            city TEXT,
            state TEXT,
            metro_area TEXT,
            industry TEXT,
            estimated_employees TEXT,
            estimated_revenue_range TEXT,
            owner_or_contact TEXT,
            contact_title TEXT,
            phone TEXT DEFAULT 'N/A',
            email TEXT DEFAULT 'N/A',
            website TEXT DEFAULT 'N/A',
            ai_fit_score INTEGER DEFAULT 0,
            pipeline_stage TEXT DEFAULT 'new_lead',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS email_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            city TEXT,
            state TEXT,
            industry TEXT,
            contact_name TEXT,
            contact_title TEXT,
            contact_email TEXT,
            subject TEXT,
            body TEXT,
            status TEXT DEFAULT 'draft',
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS suppression_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            reason TEXT DEFAULT 'do_not_contact',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def load_leads_from_csv():
    """Import master_leads_enriched.csv into the database if not already loaded."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    if count > 0:
        conn.close()
        return count

    csv_path = DB_DIR / "master_leads_enriched.csv"
    if not csv_path.exists():
        conn.close()
        return 0

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        conn.execute(
            """INSERT INTO companies (company_name, city, state, metro_area, industry,
               estimated_employees, estimated_revenue_range, owner_or_contact,
               contact_title, phone, email, website)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row.get("company_name", ""),
                row.get("city", ""),
                row.get("state", ""),
                row.get("metro_area", ""),
                row.get("industry", ""),
                row.get("estimated_employees", ""),
                row.get("estimated_revenue_range", ""),
                row.get("owner_or_contact", ""),
                row.get("contact_title", ""),
                row.get("phone", "N/A"),
                row.get("email", "N/A"),
                row.get("website", "N/A"),
            ),
        )
    conn.commit()
    conn.close()
    return len(rows)


def load_drafts_from_csv():
    """Import email_drafts.csv into the database if not already loaded."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM email_drafts").fetchone()[0]
    if count > 0:
        conn.close()
        return count

    csv_path = DB_DIR / "email_drafts.csv"
    if not csv_path.exists():
        conn.close()
        return 0

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        conn.execute(
            """INSERT INTO email_drafts (company_name, city, state, industry,
               contact_name, contact_title, contact_email, subject, body)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row.get("company_name", ""),
                row.get("city", ""),
                row.get("state", ""),
                row.get("industry", ""),
                row.get("contact_name", ""),
                row.get("contact_title", ""),
                row.get("contact_email", ""),
                row.get("subject", ""),
                row.get("body", ""),
            ),
        )
    conn.commit()
    conn.close()
    return len(rows)


# Initialize
init_db()
leads_count = load_leads_from_csv()
drafts_count = load_drafts_from_csv()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### AI Systems Audit Pipeline")
    st.caption("Brandon Rye | Columbia MBA | Ex-Citi")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "Dashboard",
            "Email Leads",
            "All Leads",
            "Draft Review",
            "Sent History",
            "Suppression List",
            "Settings",
        ],
        index=0,
    )

    st.divider()
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    with_email = conn.execute("SELECT COUNT(*) FROM companies WHERE email != 'N/A' AND email != ''").fetchone()[0]
    drafts = conn.execute("SELECT COUNT(*) FROM email_drafts WHERE status = 'draft'").fetchone()[0]
    sent = conn.execute("SELECT COUNT(*) FROM email_drafts WHERE status = 'sent'").fetchone()[0]
    conn.close()

    st.metric("Total Leads", f"{total:,}")
    st.metric("With Email", f"{with_email:,}")
    st.metric("Drafts Ready", f"{drafts:,}")
    st.metric("Emails Sent", f"{sent:,}")

    st.divider()
    st.caption(
        "⚠️ Every email requires manual review and approval. "
        "No bulk or automated sending."
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
if page == "Dashboard":
    st.title("Dashboard")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Leads", f"{total:,}")
    col2.metric("With Email", f"{with_email:,}")
    col3.metric("Drafts Ready", f"{drafts:,}")
    col4.metric("Emails Sent", f"{sent:,}")

    st.divider()

    # Industry breakdown
    conn = get_db()
    df = pd.read_sql("SELECT industry, COUNT(*) as count FROM companies GROUP BY industry ORDER BY count DESC LIMIT 15", conn)
    conn.close()

    if not df.empty:
        st.subheader("Top Industries")
        st.bar_chart(df.set_index("industry"))

    # Metro breakdown
    conn = get_db()
    df_metro = pd.read_sql("SELECT metro_area, COUNT(*) as count FROM companies GROUP BY metro_area ORDER BY count DESC", conn)
    conn.close()

    if not df_metro.empty:
        st.subheader("Leads by Metro")
        st.bar_chart(df_metro.set_index("metro_area"))


# ---------------------------------------------------------------------------
# Email Leads (actionable — have email)
# ---------------------------------------------------------------------------
elif page == "Email Leads":
    st.title("Email Leads — Ready for Outreach")
    st.caption("⚠️ Every email requires manual review and approval before sending.")

    conn = get_db()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        industries = pd.read_sql("SELECT DISTINCT industry FROM companies WHERE email != 'N/A' ORDER BY industry", conn)
        industry_filter = st.multiselect("Industry", industries["industry"].tolist())
    with col2:
        metros = pd.read_sql("SELECT DISTINCT metro_area FROM companies WHERE email != 'N/A' ORDER BY metro_area", conn)
        metro_filter = st.multiselect("Metro", metros["metro_area"].tolist())
    with col3:
        search = st.text_input("Search company name")

    query = "SELECT * FROM companies WHERE email != 'N/A' AND email != ''"
    params = []
    if industry_filter:
        placeholders = ",".join(["?"] * len(industry_filter))
        query += f" AND industry IN ({placeholders})"
        params.extend(industry_filter)
    if metro_filter:
        placeholders = ",".join(["?"] * len(metro_filter))
        query += f" AND metro_area IN ({placeholders})"
        params.extend(metro_filter)
    if search:
        query += " AND company_name LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY company_name"

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    st.write(f"**{len(df)} actionable leads**")

    if not df.empty:
        display_df = df[["company_name", "city", "state", "metro_area", "industry",
                         "estimated_employees", "email", "owner_or_contact", "contact_title"]].copy()
        display_df.columns = ["Company", "City", "State", "Metro", "Industry",
                              "Size", "Email", "Contact", "Title"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv_data = display_df.to_csv(index=False)
        st.download_button("Export to CSV", csv_data, "email_leads.csv", "text/csv")


# ---------------------------------------------------------------------------
# All Leads
# ---------------------------------------------------------------------------
elif page == "All Leads":
    st.title("All Leads")

    conn = get_db()

    col1, col2 = st.columns(2)
    with col1:
        industries = pd.read_sql("SELECT DISTINCT industry FROM companies ORDER BY industry", conn)
        industry_filter = st.multiselect("Industry", industries["industry"].tolist(), key="all_ind")
    with col2:
        metros = pd.read_sql("SELECT DISTINCT metro_area FROM companies ORDER BY metro_area", conn)
        metro_filter = st.multiselect("Metro", metros["metro_area"].tolist(), key="all_metro")

    query = "SELECT * FROM companies WHERE 1=1"
    params = []
    if industry_filter:
        placeholders = ",".join(["?"] * len(industry_filter))
        query += f" AND industry IN ({placeholders})"
        params.extend(industry_filter)
    if metro_filter:
        placeholders = ",".join(["?"] * len(metro_filter))
        query += f" AND metro_area IN ({placeholders})"
        params.extend(metro_filter)
    query += " ORDER BY company_name"

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    st.write(f"**{len(df)} total leads**")

    if not df.empty:
        display_df = df[["company_name", "city", "state", "metro_area", "industry",
                         "estimated_employees", "email", "phone", "website"]].copy()
        display_df.columns = ["Company", "City", "State", "Metro", "Industry",
                              "Size", "Email", "Phone", "Website"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv_data = display_df.to_csv(index=False)
        st.download_button("Export All to CSV", csv_data, "all_leads.csv", "text/csv")


# ---------------------------------------------------------------------------
# Draft Review
# ---------------------------------------------------------------------------
elif page == "Draft Review":
    st.title("Draft Review & Approval")
    st.caption("⚠️ Review each email carefully before approving. No automated sending.")

    conn = get_db()

    # Filter by status
    status_filter = st.selectbox("Show", ["Drafts (pending review)", "Approved", "Sent", "All"])
    status_map = {
        "Drafts (pending review)": "draft",
        "Approved": "approved",
        "Sent": "sent",
    }

    if status_filter == "All":
        df = pd.read_sql("SELECT * FROM email_drafts ORDER BY id", conn)
    else:
        status = status_map[status_filter]
        df = pd.read_sql("SELECT * FROM email_drafts WHERE status = ? ORDER BY id", conn, params=[status])

    st.write(f"**{len(df)} emails**")

    if not df.empty:
        # Industry filter
        industries = df["industry"].unique().tolist()
        ind_filter = st.multiselect("Filter by industry", industries, key="draft_ind")
        if ind_filter:
            df = df[df["industry"].isin(ind_filter)]

        for idx, row in df.iterrows():
            with st.expander(f"**{row['company_name']}** — {row['industry']} | {row['contact_email']} | Status: {row['status'].upper()}"):
                st.markdown(f"**To:** {row['contact_name']} ({row['contact_title']}) — {row['contact_email']}")
                st.markdown(f"**Subject:** {row['subject']}")
                st.divider()
                st.text(row["body"])
                st.divider()

                col1, col2, col3 = st.columns(3)

                # Check suppression
                suppressed = conn.execute(
                    "SELECT COUNT(*) FROM suppression_list WHERE email = ?",
                    (row["contact_email"].lower(),)
                ).fetchone()[0] > 0

                if suppressed:
                    st.error("This contact is on the suppression list. Cannot send.")
                elif row["status"] == "draft":
                    if col1.button("Approve", key=f"approve_{row['id']}"):
                        conn.execute("UPDATE email_drafts SET status = 'approved' WHERE id = ?", (row["id"],))
                        conn.commit()
                        st.success("Approved!")
                        st.rerun()
                    if col2.button("Suppress Contact", key=f"suppress_{row['id']}"):
                        try:
                            conn.execute(
                                "INSERT OR IGNORE INTO suppression_list (email) VALUES (?)",
                                (row["contact_email"].lower(),)
                            )
                            conn.commit()
                            st.warning("Contact added to suppression list.")
                            st.rerun()
                        except Exception:
                            st.info("Already suppressed.")
                elif row["status"] == "approved":
                    st.info("Ready to send. Connect Gmail in Settings to enable sending.")

    conn.close()


# ---------------------------------------------------------------------------
# Sent History
# ---------------------------------------------------------------------------
elif page == "Sent History":
    st.title("Sent History")

    conn = get_db()
    df = pd.read_sql("SELECT * FROM email_drafts WHERE status = 'sent' ORDER BY sent_at DESC", conn)
    conn.close()

    if df.empty:
        st.info("No emails sent yet. Review and approve drafts first.")
    else:
        st.write(f"**{len(df)} emails sent**")
        for idx, row in df.iterrows():
            with st.expander(f"{row['company_name']} — {row['contact_email']} — {row['sent_at']}"):
                st.markdown(f"**Subject:** {row['subject']}")
                st.text(row["body"])


# ---------------------------------------------------------------------------
# Suppression List
# ---------------------------------------------------------------------------
elif page == "Suppression List":
    st.title("Suppression List")
    st.caption("Contacts on this list will never receive outreach.")

    conn = get_db()

    # Add to suppression
    with st.expander("Add email to suppression list"):
        new_email = st.text_input("Email address")
        new_reason = st.selectbox("Reason", ["do_not_contact", "unsubscribed", "bounced", "complaint"])
        if st.button("Add to Suppression List"):
            if new_email:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO suppression_list (email, reason) VALUES (?, ?)",
                        (new_email.lower().strip(), new_reason)
                    )
                    conn.commit()
                    st.success(f"Added {new_email} to suppression list.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Show list
    df = pd.read_sql("SELECT * FROM suppression_list ORDER BY created_at DESC", conn)
    conn.close()

    if df.empty:
        st.info("Suppression list is empty.")
    else:
        st.write(f"**{len(df)} suppressed contacts**")
        st.dataframe(df[["email", "reason", "created_at"]], use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
elif page == "Settings":
    st.title("Settings")

    st.subheader("About")
    st.markdown(
        """
        **AI Systems Audit Pipeline**

        Built for Brandon Rye — Columbia MBA, former Citi investment banking VP,
        former FedEx operations analyst ($18M cost reduction).

        This platform identifies small owner-operated businesses (5-20 employees),
        scores them for AI consulting fit, and manages personalized outreach for the
        **Operations Blueprint** offer.

        The Operations Blueprint is a 60-minute deep dive with the business owner,
        delivering a full workflow map, automation opportunities ranked by ROI,
        recommended tool stack, and 30-60-90 day roadmap within 48 hours.
        """
    )

    st.divider()

    st.subheader("Data Management")
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    with_email = conn.execute("SELECT COUNT(*) FROM companies WHERE email != 'N/A'").fetchone()[0]
    draft_count = conn.execute("SELECT COUNT(*) FROM email_drafts").fetchone()[0]
    conn.close()

    st.write(f"**{total:,}** total leads loaded")
    st.write(f"**{with_email:,}** leads with email addresses")
    st.write(f"**{draft_count:,}** email drafts generated")

    st.divider()
    st.subheader("Gmail Integration")
    st.info(
        "Gmail integration is not yet configured. To enable manual email sending, "
        "set up Google OAuth credentials and connect your Gmail account."
    )

    st.divider()
    st.caption(
        "⚠️ Compliance: Every email requires manual review and approval. "
        "No bulk sending. No automated sequences. No randomized timing."
    )

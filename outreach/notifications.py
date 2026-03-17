"""
Internal Notification System

Uses the SECONDARY Gmail account stored in notification_accounts ONLY to
send reminder emails TO THE USER.  This module NEVER contacts prospects.

Compliance rules:
  - The notification account's credentials are used exclusively for
    sending messages from the user to themselves.
  - Prospect email addresses are never passed to this module.
  - All sends are best-effort (failures are logged, not raised to the UI).
"""

import base64
import json
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gmail helper (notification account only)
# ---------------------------------------------------------------------------

def _build_notification_gmail_service(refresh_token: str):
    """
    Build and return an authenticated Gmail API service using the notification
    account's stored refresh token.

    Returns None if credentials cannot be refreshed (logs the error).
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import os

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.error(
                "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set — "
                "cannot build notification Gmail service"
            )
            return None

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )
        creds.refresh(Request())
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return service

    except Exception:
        logger.exception("Failed to build notification Gmail service")
        return None


def _send_via_notification_account(
    service,
    from_email: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> bool:
    """
    Send a single email using the notification Gmail service.
    Returns True on success.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info("Notification email sent to %s, subject=%r", to_email, subject)
        return True

    except Exception:
        logger.exception("Failed to send notification email to %s", to_email)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_followup_reminder(
    session: Session,
    user_id: int,
    companies_due: list[dict],
) -> bool:
    """
    Send an internal reminder email to the user listing companies that need
    follow-up attention.

    The email is sent FROM the user's notification account (secondary Gmail)
    TO the user's primary email address.

    Parameters
    ----------
    session : Session
        Active SQLAlchemy session.
    user_id : int
        The user to notify.
    companies_due : list[dict]
        Output of OutreachTracker.get_followups_due() — each dict must
        contain at minimum: company_name, contact_name, contact_email,
        stage_label, days_overdue, next_followup_due.

    Returns True if the email was sent successfully, False otherwise.
    """
    if not companies_due:
        logger.debug("send_followup_reminder: no companies due, skipping send")
        return False

    from database.models import User
    from outreach.models import NotificationAccount

    user = session.get(User, user_id)
    if user is None:
        logger.error("send_followup_reminder: user_id=%s not found", user_id)
        return False

    notif_account = (
        session.query(NotificationAccount)
        .filter_by(user_id=user_id, is_active=True)
        .first()
    )
    if notif_account is None or not notif_account.gmail_refresh_token:
        logger.info(
            "send_followup_reminder: no active notification account for user_id=%s", user_id
        )
        return False

    gmail_service = _build_notification_gmail_service(notif_account.gmail_refresh_token)
    if gmail_service is None:
        return False

    # --- Build the email content ------------------------------------
    today_str = datetime.utcnow().strftime("%A, %B %-d, %Y")
    count = len(companies_due)
    subject = f"[AI Systems Audit] {count} Follow-Up{'s' if count != 1 else ''} Due — {today_str}"

    # Plain-text version
    text_lines = [
        f"Follow-Up Reminders — {today_str}",
        f"You have {count} outreach thread{'s' if count != 1 else ''} that need attention.",
        "",
    ]
    for i, co in enumerate(companies_due, start=1):
        overdue_str = (
            f"{co['days_overdue']} day{'s' if co['days_overdue'] != 1 else ''} overdue"
            if co.get("days_overdue", 0) > 0
            else "due today"
        )
        contact_display = co.get("contact_name") or co.get("contact_email") or "Unknown contact"
        text_lines.append(
            f"{i}. {co['company_name']} — {contact_display}\n"
            f"   Stage: {co.get('stage_label', 'N/A')}  |  {overdue_str}\n"
            f"   Action: Open the AI Systems Audit app and review this thread.\n"
        )

    text_lines += [
        "",
        "Open your AI Systems Audit app to review and approve each follow-up.",
        "No emails have been sent automatically — your approval is required.",
    ]
    text_body = "\n".join(text_lines)

    # HTML version
    rows_html = ""
    for co in companies_due:
        overdue_str = (
            f"<span style='color:#c0392b;font-weight:bold;'>"
            f"{co['days_overdue']} day{'s' if co.get('days_overdue',0) != 1 else ''} overdue"
            f"</span>"
            if co.get("days_overdue", 0) > 0
            else "<span style='color:#27ae60;'>Due today</span>"
        )
        contact_display = co.get("contact_name") or co.get("contact_email") or "Unknown contact"
        rows_html += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">
            <strong>{co['company_name']}</strong><br>
            <span style="color:#555;font-size:13px;">{contact_display}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;font-size:13px;">
            {co.get('stage_label', 'N/A')}
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;font-size:13px;">
            {overdue_str}
          </td>
        </tr>"""

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;max-width:640px;margin:auto;">
      <h2 style="color:#1a1a2e;">AI Systems Audit — Follow-Up Reminders</h2>
      <p style="color:#555;">{today_str}</p>
      <p>You have <strong>{count} outreach thread{'s' if count != 1 else ''}</strong>
         that need your attention.</p>

      <table style="width:100%;border-collapse:collapse;margin:16px 0;">
        <thead>
          <tr style="background:#f0f4ff;">
            <th style="padding:10px 8px;text-align:left;font-size:13px;">Company / Contact</th>
            <th style="padding:10px 8px;text-align:left;font-size:13px;">Stage</th>
            <th style="padding:10px 8px;text-align:left;font-size:13px;">Status</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>

      <p style="margin-top:24px;padding:12px;background:#fff8e1;border-left:4px solid #f39c12;
                font-size:13px;">
        <strong>No emails have been sent automatically.</strong><br>
        Open your AI Systems Audit app to review each follow-up and click
        <em>Approve &amp; Send</em> for any you want to send.
      </p>

      <p style="color:#aaa;font-size:12px;margin-top:32px;">
        This is an internal reminder from your AI Systems Audit outreach tool.
        It was sent to you, not to any prospect.
      </p>
    </body></html>"""

    return _send_via_notification_account(
        service=gmail_service,
        from_email=notif_account.email,
        to_email=user.email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


# ---------------------------------------------------------------------------

def get_daily_digest(session: Session, user_id: int) -> dict:
    """
    Build a summary dict of today's outreach activity for the user.

    The dict can be used to display a dashboard panel in Streamlit OR
    passed to send_followup_reminder() to trigger an email digest.

    Returns
    -------
    {
        "generated_at": datetime,
        "followups_due_today": list[dict],   # from get_followups_due()
        "new_replies_since_yesterday": list[dict],
        "pipeline_summary": dict,            # from get_pipeline_counts()
        "total_due": int,
        "total_new_replies": int,
    }
    """
    from outreach.followup_engine import OutreachTracker
    from outreach.models import OutreachState

    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    tracker = OutreachTracker(session)

    # Follow-ups due
    followups_due = tracker.get_followups_due(user_id)

    # Replies detected since yesterday
    recent_replies_raw = (
        session.query(OutreachState)
        .filter(
            OutreachState.user_id == user_id,
            OutreachState.reply_detected == True,  # noqa: E712
            OutreachState.reply_detected_at >= yesterday,
        )
        .all()
    )

    from database.models import Company, Contact

    new_replies = []
    for state in recent_replies_raw:
        company = session.get(Company, state.company_id)
        contact = session.get(Contact, state.contact_id)
        new_replies.append({
            "company_id": state.company_id,
            "company_name": company.name if company else f"company_id={state.company_id}",
            "contact_name": (
                f"{contact.first_name or ''} {contact.last_name or ''}".strip()
                if contact else "Unknown"
            ),
            "reply_detected_at": state.reply_detected_at,
        })

    # Pipeline counts
    pipeline_summary = tracker.get_pipeline_counts(user_id)

    digest = {
        "generated_at": now,
        "followups_due_today": followups_due,
        "new_replies_since_yesterday": new_replies,
        "pipeline_summary": pipeline_summary,
        "total_due": len(followups_due),
        "total_new_replies": len(new_replies),
    }

    logger.info(
        "Daily digest for user_id=%s: %d due, %d new replies",
        user_id, digest["total_due"], digest["total_new_replies"],
    )
    return digest

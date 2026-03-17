"""
Gmail integration for human-supervised, single-email sending only.
No bulk or automated sending.
"""

import base64
import os
import urllib.parse
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from database.models import SentEmail, SuppressionEntry, User

load_dotenv()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_gmail_auth_url(user_email: str) -> str:
    """
    Builds the Gmail OAuth URL for the given user email.
    Requests scopes for send, compose, readonly, and modify.
    """
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    redirect_uri = os.environ.get("GMAIL_REDIRECT_URI", "http://localhost:8501/gmail/callback")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "login_hint": user_email,
    }

    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def connect_gmail(code: str) -> str:
    """
    Exchanges the OAuth code for Gmail credentials.
    Returns the refresh_token to store on the User record.
    """
    import requests

    client_id = os.environ["GOOGLE_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
    redirect_uri = os.environ.get("GMAIL_REDIRECT_URI", "http://localhost:8501/gmail/callback")

    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_response.raise_for_status()
    token_data = token_response.json()

    refresh_token = token_data.get("refresh_token", "")
    return refresh_token


def get_gmail_service(refresh_token: str):
    """
    Builds and returns an authorized Gmail API service object
    using the stored refresh token.
    """
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_CLIENT_SECRET"]

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        scopes=GMAIL_SCOPES,
    )

    if creds.expired or not creds.token:
        creds.refresh(Request())

    service = build("gmail", "v1", credentials=creds)
    return service


def create_gmail_draft(
    service,
    to_email: str,
    subject: str,
    body: str,
    reply_to_thread_id: str = None,
) -> str:
    """
    Creates a draft in Gmail. Returns the draft ID.
    Uses base64url encoding for the message as required by Gmail API.
    """
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))

    raw_bytes = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    draft_body: dict = {"message": {"raw": raw_bytes}}

    if reply_to_thread_id:
        draft_body["message"]["threadId"] = reply_to_thread_id

    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    return draft["id"]


def send_single_email(service, draft_id: str) -> dict:
    """
    Sends ONE previously created Gmail draft. This is the ONLY send function — by design.
    No bulk sending. No automated sending. Human must explicitly trigger this call.

    Returns dict with message_id and thread_id.
    """
    result = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()

    return {
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
    }


def check_daily_sends(session, user_id: int) -> tuple:
    """
    Counts SentEmail records created today for the given user.
    Returns (sent_count, remaining) based on User.daily_send_cap.
    """
    today = date.today()
    user = session.query(User).filter_by(id=user_id).first()
    daily_cap = user.daily_send_cap if user and hasattr(user, "daily_send_cap") else 50

    sent_today = (
        session.query(SentEmail)
        .filter(
            SentEmail.user_id == user_id,
            SentEmail.sent_at >= today,
        )
        .count()
    )

    remaining = max(0, daily_cap - sent_today)
    return (sent_today, remaining)


def is_suppressed(session, email: str) -> bool:
    """
    Checks the SuppressionEntry table for the given email address (case-insensitive).
    Returns True if the email is suppressed and should not be contacted.
    """
    entry = (
        session.query(SuppressionEntry)
        .filter(SuppressionEntry.email.ilike(email.strip()))
        .first()
    )
    return entry is not None


def get_thread_replies(service, thread_id: str) -> list:
    """
    Fetches all messages in a Gmail thread.
    Returns a list of dicts: {from, date, snippet, body}.
    """
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
    messages = thread.get("messages", [])

    results = []
    for msg in messages:
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        snippet = msg.get("snippet", "")

        body_text = ""
        payload = msg.get("payload", {})

        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                body_text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        else:
            for part in payload.get("parts", []):
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body_text = base64.urlsafe_b64decode(data + "==").decode(
                            "utf-8", errors="replace"
                        )
                        break

        results.append(
            {
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": snippet,
                "body": body_text,
            }
        )

    return results

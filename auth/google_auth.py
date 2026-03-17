import os
import urllib.parse

import requests
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from database.models import User

load_dotenv()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = [
    "openid",
    "email",
    "profile",
]


def get_google_auth_url() -> str:
    """Builds and returns the Google OAuth2 authorization URL."""
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501/oauth/callback")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }

    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def handle_oauth_callback(code: str) -> dict:
    """
    Exchanges the OAuth authorization code for tokens, then fetches user info.

    Returns:
        dict with keys: google_id, email, name, picture_url, access_token, refresh_token
    """
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501/oauth/callback")

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

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")

    userinfo_response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    userinfo_response.raise_for_status()
    userinfo = userinfo_response.json()

    return {
        "google_id": userinfo["sub"],
        "email": userinfo["email"],
        "name": userinfo.get("name", ""),
        "picture_url": userinfo.get("picture", ""),
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def get_or_create_user(session, user_info: dict) -> User:
    """
    Finds an existing user by google_id or creates a new one.

    Returns the User ORM object.
    """
    user = session.query(User).filter_by(google_id=user_info["google_id"]).first()

    if user is None:
        user = User(
            google_id=user_info["google_id"],
            email=user_info["email"],
            name=user_info["name"],
            picture_url=user_info["picture_url"],
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        user.name = user_info["name"]
        user.picture_url = user_info["picture_url"]
        session.commit()
        session.refresh(user)

    return user

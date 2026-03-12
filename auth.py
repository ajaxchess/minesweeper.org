"""
auth.py — Google OAuth 2.0 login via Authlib + signed cookie sessions.
"""
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.requests import Request

# ── Load config ───────────────────────────────────────────────────────────────
# Store these in a .env file or as environment variables — never hard-code them.
config = Config(".env")

GOOGLE_CLIENT_ID     = config("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET")
SECRET_KEY           = config("SECRET_KEY")   # random string for signing sessions

# ── OAuth client ──────────────────────────────────────────────────────────────
oauth = OAuth(config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ── Session helpers ───────────────────────────────────────────────────────────
def get_current_user(request: Request) -> dict | None:
    """Returns the logged-in user dict or None."""
    return request.session.get("user")

def set_session_user(request: Request, user: dict, display_name: str | None = None):
    request.session["user"] = {
        "name":         user.get("name", ""),
        "email":        user.get("email", ""),
        "picture":      user.get("picture", ""),
        "display_name": display_name or user.get("name", ""),
    }

def clear_session(request: Request):
    request.session.clear()

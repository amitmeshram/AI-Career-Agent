from paths import (
    CAREER_OPS_ROOT,
    BROWSER_PROFILES_DIR,
    DATA_DIR,
    DAILY_REPORTS_DIR,
    JD_FILES_DIR,
    GMAIL_CREDENTIALS_FILE,
    GMAIL_TOKEN_FILE,
    LINKEDIN_BROWSER_PROFILE_DIR,
)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def check_gmail_connection():
    credentials_path = GMAIL_CREDENTIALS_FILE
    token_path = GMAIL_TOKEN_FILE

    if not credentials_path.exists() or not token_path.exists():
        return {
            "status": "RECONNECT_REQUIRED",
            "message": "Gmail authorization is missing.",
        }

    try:
        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
            except RefreshError:
                return {
                    "status": "RECONNECT_REQUIRED",
                    "message": "Gmail token expired or revoked.",
                }

        if not creds or not creds.valid:
            return {
                "status": "RECONNECT_REQUIRED",
                "message": "Gmail authorization is not valid.",
            }

        service = build("gmail", "v1", credentials=creds)
        service.users().getProfile(userId="me").execute()
        return {"status": "OK", "message": "Gmail is connected."}
    except Exception:
        return {
            "status": "RECONNECT_REQUIRED",
            "message": "Gmail connection needs attention.",
        }


def reconnect_gmail():
    credentials_path = GMAIL_CREDENTIALS_FILE
    token_path = GMAIL_TOKEN_FILE

    if not credentials_path.exists():
        return {
            "status": "RECONNECT_REQUIRED",
            "message": "credentials.json is missing.",
        }

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        if token_path.exists():
            token_path.unlink()
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return {"status": "OK", "message": "Gmail reconnected."}
    except Exception:
        return {
            "status": "RECONNECT_REQUIRED",
            "message": "Gmail reconnection was not completed.",
        }


def check_linkedin_session():
    profile_dir = LINKEDIN_BROWSER_PROFILE_DIR

    if not profile_dir.exists():
        return {
            "status": "LOGIN_REQUIRED",
            "message": "LinkedIn browser profile is missing.",
        }

    browser = None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=True,
            )
            page = browser.new_page()
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            current_url = page.url.lower()
            browser.close()
            browser = None

        login_markers = ("login", "authwall", "checkpoint", "uas/login")
        if any(marker in current_url for marker in login_markers):
            return {
                "status": "LOGIN_REQUIRED",
                "message": "LinkedIn login is required.",
            }
        return {"status": "OK", "message": "LinkedIn session is active."}
    except Exception:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        return {
            "status": "LOGIN_REQUIRED",
            "message": "LinkedIn session could not be verified.",
        }


def reconnect_linkedin():
    profile_dir = LINKEDIN_BROWSER_PROFILE_DIR
    profile_dir.mkdir(parents=True, exist_ok=True)

    browser = None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
            )
            page = browser.new_page()
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            input("Complete LinkedIn login in browser and press ENTER.")
            browser.close()
            browser = None
        return check_linkedin_session()
    except Exception:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        return {
            "status": "LOGIN_REQUIRED",
            "message": "LinkedIn reconnection was not completed.",
        }


def check_career_ops_files():
    required_files = [
        CAREER_OPS_ROOT / "cv.md",
        CAREER_OPS_ROOT / "config" / "profile.yml",
        CAREER_OPS_ROOT / "openrouter-eval.mjs",
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        return {"status": "MISSING", "missing": missing}
    return {"status": "OK", "missing": []}


def read_env_file(path):
    values = {}
    if not path.exists():
        return values

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def check_ai_model_connection():
    env_path = CAREER_OPS_ROOT / ".env"

    if not env_path.exists():
        return {
            "status": "MISSING",
            "message": "career-ops .env file is missing.",
        }

    values = read_env_file(env_path)
    api_key_names = [
        "AI_API_KEY",
        "OPENROUTER_API_KEY",
        "ANTHROPIC_API_KEY",
        "CLAUDE_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_GENERATIVE_AI_API_KEY",
    ]
    has_api_key = any(values.get(name, "") for name in api_key_names)
    models = [
        values.get("PRIMARY_MODEL", ""),
        values.get("FALLBACK_MODEL", ""),
        values.get("SECOND_FALLBACK_MODEL", "") or values.get("SECOND_FALLBACK", ""),
    ]

    if not has_api_key:
        return {
            "status": "MISSING",
            "message": "No AI provider API key is configured.",
        }

    if not values.get("AI_PROVIDER_NAME", "") and values.get("AI_API_KEY", ""):
        return {
            "status": "MISSING",
            "message": "AI_PROVIDER_NAME is required when using AI_API_KEY.",
        }

    if not all(model for model in models):
        return {
            "status": "MISSING",
            "message": "Primary, fallback, and second fallback models must be configured.",
        }

    return {"status": "OK", "message": "AI model settings are configured."}


def ensure_output_folders():
    folders = [
        DATA_DIR,
        JD_FILES_DIR,
        DAILY_REPORTS_DIR,
        BROWSER_PROFILES_DIR,
    ]

    try:
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
        return {"status": "OK", "folders": [str(folder) for folder in folders]}
    except Exception:
        return {
            "status": "MISSING",
            "folders": [str(folder) for folder in folders],
        }


def run_startup_health_check():
    return {
        "gmail": check_gmail_connection(),
        "linkedin": check_linkedin_session(),
        "career_ops": check_career_ops_files(),
        "ai_model": check_ai_model_connection(),
        "output_folders": ensure_output_folders(),
    }

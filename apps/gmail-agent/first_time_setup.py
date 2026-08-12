import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SETUP_STATE_KEYS = (
    "first_time_setup_completed",
    "cv_setup_completed",
    "profile_setup_completed",
    "credentials_setup_completed",
    "google_credentials_setup_completed",
    "gmail_setup_completed",
    "linkedin_setup_completed",
    "ai_model_setup_completed",
    "setup_completed_at",
)

REQUIRED_COMPLETION_FLAGS = tuple(key for key in SETUP_STATE_KEYS if key != "setup_completed_at")

ENV_FIELDS = (
    "AI_PROVIDER_NAME",
    "AI_API_KEY",
    "AI_BASE_URL",
    "PRIMARY_MODEL",
    "FALLBACK_MODEL",
    "SECOND_FALLBACK_MODEL",
    "GOOGLE_OAUTH_CREDENTIALS_JSON",
    "GMAIL_TOKEN_PATH",
)

SECRET_ENV_FIELDS = {
    "AI_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
}

LEGACY_AI_KEY_PROVIDERS = (
    ("OPENROUTER_API_KEY", "openrouter"),
    ("OPENAI_API_KEY", "openai"),
    ("ANTHROPIC_API_KEY", "anthropic"),
    ("CLAUDE_API_KEY", "anthropic"),
    ("GEMINI_API_KEY", "gemini"),
)

LEGACY_AI_ENV_FIELDS = {
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
    "GEMINI_API_KEY",
    "SECOND_FALLBACK",
    "SECONDARY_FALLBACK_MODEL",
}

PROVIDER_ALIASES = {
    "1": "openai",
    "open ai": "openai",
    "openai": "openai",
    "chatgpt": "openai",
    "2": "anthropic",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "3": "gemini",
    "gemini": "gemini",
    "google": "gemini",
    "4": "openrouter",
    "open router": "openrouter",
    "openrouter": "openrouter",
    "5": "custom",
    "custom": "custom",
}

BLOCKED_ENV_KEY_MARKERS = (
    "GMAIL_PASSWORD",
    "GOOGLE_PASSWORD",
    "LINKEDIN_PASSWORD",
)

PLACEHOLDER_VALUES = {
    "",
    "YOUR_GOOGLE_CLIENT_ID",
    "YOUR_GOOGLE_CLIENT_SECRET",
    "YOUR_GOOGLE_PROJECT_ID",
    "your_google_client_id",
    "your_google_client_secret",
}


def clean_path_input(value):
    return str(value or "").strip().strip("\"'")


def supports_ansi_color(stream=None):
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.name != "nt":
        return os.environ.get("TERM", "").lower() != "dumb"
    return bool(
        os.environ.get("WT_SESSION")
        or os.environ.get("ANSICON")
        or os.environ.get("ConEmuANSI", "").upper() == "ON"
        or os.environ.get("TERM_PROGRAM")
        or os.environ.get("TERM", "").lower() not in {"", "dumb"}
    )


def format_hint(text, stream=None):
    hint = f"Hint: {text}"
    if supports_ansi_color(stream=stream):
        return f"\033[90m{hint}\033[0m"
    return hint


def print_hint(text):
    print(format_hint(text))


@dataclass
class SetupPaths:
    project_root: Path
    app_root: Path
    data_dir: Path
    jd_files_dir: Path
    daily_reports_dir: Path
    browser_profiles_dir: Path
    state_file: Path
    drafts_dir: Path
    root_env_file: Path
    root_env_example: Path
    credentials_file: Path
    token_file: Path
    linkedin_profile_dir: Path


def get_setup_paths(project_root=None, app_root=None):
    if app_root is None:
        app_root = Path(__file__).resolve().parent
    else:
        app_root = Path(app_root).resolve()
    if project_root is None:
        project_root = app_root.parent.parent
    else:
        project_root = Path(project_root).resolve()
    data_dir = project_root / "data" / "gmail-agent"
    jd_files_dir = project_root / "jds"
    daily_reports_dir = project_root / "reports" / "daily"
    browser_profiles_dir = data_dir / "browser_profiles"
    return SetupPaths(
        project_root=project_root,
        app_root=app_root,
        data_dir=data_dir,
        jd_files_dir=jd_files_dir,
        daily_reports_dir=daily_reports_dir,
        browser_profiles_dir=browser_profiles_dir,
        state_file=data_dir / "setup_state.json",
        drafts_dir=data_dir / "setup_drafts",
        root_env_file=project_root / ".env",
        root_env_example=project_root / ".env.example",
        credentials_file=app_root / "credentials.json",
        token_file=app_root / "token.json",
        linkedin_profile_dir=browser_profiles_dir / "linkedin",
    )


def default_setup_state():
    state = {key: False for key in SETUP_STATE_KEYS}
    state["setup_completed_at"] = ""
    return state


def load_setup_state(paths):
    if not paths.state_file.exists():
        return default_setup_state()
    try:
        loaded = json.loads(paths.state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_setup_state()
    state = default_setup_state()
    state.update({key: loaded.get(key, state[key]) for key in SETUP_STATE_KEYS})
    return state


def save_setup_state(paths, state):
    paths.state_file.parent.mkdir(parents=True, exist_ok=True)
    normalized = default_setup_state()
    normalized.update({key: state.get(key, normalized[key]) for key in SETUP_STATE_KEYS})
    paths.state_file.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")


def is_setup_complete(paths):
    state = load_setup_state(paths)
    return all(bool(state.get(key)) for key in REQUIRED_COMPLETION_FLAGS)


def python_version_check(version_info=None):
    version_info = version_info or sys.version_info
    ok = tuple(version_info[:2]) >= (3, 10)
    version = ".".join(str(part) for part in version_info[:3])
    return {
        "status": "PASS" if ok else "FAIL",
        "message": f"Python {version}",
    }


def mask_secret(value):
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def read_env_file(path):
    values = {}
    if not Path(path).exists():
        return values
    for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def write_env_file(path, values):
    lines = [
        "# AI Career Agent local configuration",
        "# Secrets stay on this machine. Do not commit this file.",
        "",
    ]
    for key in ENV_FIELDS:
        value = values.get(key, "")
        lines.append(f"{key}={value}")
    extra_keys = sorted(
        key
        for key in values
        if key not in ENV_FIELDS and key not in LEGACY_AI_ENV_FIELDS and is_allowed_env_key(key)
    )
    if extra_keys:
        lines.append("")
        lines.append("# Existing non-onboarding settings preserved")
        for key in extra_keys:
            lines.append(f"{key}={values.get(key, '')}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def sanitized_env_preview(values):
    preview = {}
    for key in ENV_FIELDS:
        value = values.get(key, "")
        preview[key] = mask_secret(value) if key in SECRET_ENV_FIELDS else value
    return preview


def build_env_values(existing_values, answers, paths):
    values = {
        key: value
        for key, value in existing_values.items()
        if is_allowed_env_key(key)
    }
    for key in ENV_FIELDS:
        values.setdefault(key, "")
    if not values.get("AI_API_KEY"):
        for legacy_key, provider in LEGACY_AI_KEY_PROVIDERS:
            if values.get(legacy_key):
                values["AI_API_KEY"] = values[legacy_key]
                values["AI_PROVIDER_NAME"] = values.get("AI_PROVIDER_NAME") or provider
                break
    if not values.get("SECOND_FALLBACK_MODEL"):
        values["SECOND_FALLBACK_MODEL"] = (
            values.get("SECOND_FALLBACK") or values.get("SECONDARY_FALLBACK_MODEL") or ""
        )
    values.update({key: answers.get(key, values.get(key, "")) for key in ENV_FIELDS})
    if not values.get("GOOGLE_OAUTH_CREDENTIALS_JSON"):
        values["GOOGLE_OAUTH_CREDENTIALS_JSON"] = str(paths.credentials_file)
    if not values.get("GMAIL_TOKEN_PATH"):
        values["GMAIL_TOKEN_PATH"] = str(paths.token_file)
    return values


def is_allowed_env_key(key):
    upper_key = str(key or "").upper()
    return not any(marker in upper_key for marker in BLOCKED_ENV_KEY_MARKERS)


def normalize_provider_name(value):
    return PROVIDER_ALIASES.get(str(value or "").strip().lower(), str(value or "").strip().lower())


def prompt_env_setup(paths, input_func=input):
    print("\nC. .env setup")
    print("AI Career Agent needs one AI provider API key to evaluate job descriptions.")
    print("Use models from the same provider for primary, fallback, and second fallback.")
    existing = read_env_file(paths.root_env_file)
    if not existing and paths.root_env_example.exists():
        existing = read_env_file(paths.root_env_example)
    answers = {}
    defaults = {
        "AI_PROVIDER_NAME": existing.get("AI_PROVIDER_NAME", ""),
        "AI_API_KEY": existing.get("AI_API_KEY", ""),
        "AI_BASE_URL": existing.get("AI_BASE_URL", ""),
        "PRIMARY_MODEL": existing.get("PRIMARY_MODEL", ""),
        "FALLBACK_MODEL": existing.get("FALLBACK_MODEL", ""),
        "SECOND_FALLBACK_MODEL": (
            existing.get("SECOND_FALLBACK_MODEL")
            or existing.get("SECOND_FALLBACK")
            or existing.get("SECONDARY_FALLBACK_MODEL")
            or ""
        ),
        "GOOGLE_OAUTH_CREDENTIALS_JSON": existing.get(
            "GOOGLE_OAUTH_CREDENTIALS_JSON", str(paths.credentials_file)
        ),
        "GMAIL_TOKEN_PATH": existing.get("GMAIL_TOKEN_PATH", str(paths.token_file)),
    }

    if not defaults["AI_API_KEY"]:
        for legacy_key, provider in LEGACY_AI_KEY_PROVIDERS:
            if existing.get(legacy_key):
                defaults["AI_API_KEY"] = existing[legacy_key]
                defaults["AI_PROVIDER_NAME"] = defaults["AI_PROVIDER_NAME"] or provider
                break

    print("")
    print("Choose one provider:")
    print("1. OpenAI")
    print("2. Anthropic / Claude")
    print("3. Gemini")
    print("4. OpenRouter")
    print("5. Custom OpenAI-compatible provider")
    print_hint("Type one option number, for example: 1.")
    current_provider = defaults["AI_PROVIDER_NAME"]
    provider_prompt = f"Provider [{current_provider}]: " if current_provider else "Provider: "
    provider = normalize_provider_name(input_func(provider_prompt).strip() or current_provider)
    while provider not in {"openai", "anthropic", "gemini", "openrouter", "custom"}:
        print("Please choose 1, 2, 3, 4, or 5.")
        provider = normalize_provider_name(input_func("Provider: ").strip())
    answers["AI_PROVIDER_NAME"] = provider

    print("")
    print("AI API key")
    current_key = defaults["AI_API_KEY"]
    shown = mask_secret(current_key)
    print_hint("Paste the API key for the selected provider, or press Enter to keep the saved value.")
    key_prompt = f"Press Enter to keep existing value: {shown}\n> " if shown else "Paste your API key.\n> "
    api_key = input_func(key_prompt).strip()
    answers["AI_API_KEY"] = api_key or current_key

    if provider == "custom":
        print("")
        print("Custom provider base URL")
        print_hint("Required for custom OpenAI-compatible providers, for example: https://api.example.com/v1")
        base_url = input_func(f"AI_BASE_URL [{defaults['AI_BASE_URL']}]: ").strip()
        answers["AI_BASE_URL"] = base_url or defaults["AI_BASE_URL"]
    else:
        answers["AI_BASE_URL"] = ""

    model_prompts = (
        (
            "PRIMARY_MODEL",
            "Primary AI model",
            "Use a model name supported by the selected provider.",
        ),
        (
            "FALLBACK_MODEL",
            "Fallback AI model",
            "Use another model from the same provider.",
        ),
        (
            "SECOND_FALLBACK_MODEL",
            "Second fallback AI model",
            "Use another model from the same provider.",
        ),
    )
    for key, label, recommendation in model_prompts:
        current = existing.get(key) or defaults.get(key, "")
        prompt_lines = [f"\n{label}", f"Current: {current}", "Press Enter to keep this model."]
        if recommendation:
            prompt_lines.append(recommendation)
        prompt_lines.append("> ")
        print_hint("Type your answer in plain English, then press Enter.")
        value = input_func("\n".join(prompt_lines)).strip()
        answers[key] = value or current

    for key in ("GOOGLE_OAUTH_CREDENTIALS_JSON", "GMAIL_TOKEN_PATH"):
        current = existing.get(key) or defaults.get(key, "")
        answers[key] = current
    values = build_env_values(existing, answers, paths)
    print("\n.env preview:")
    for key, value in sanitized_env_preview(values).items():
        print(f"{key}={value}")
    if prompt_yes_no("Write .env now?", default=True, input_func=input_func):
        write_env_file(paths.root_env_file, values)
    return values


def prompt_yes_no(prompt, default=False, input_func=input):
    suffix = " [Y/n]: " if default else " [y/N]: "
    print_hint("Type Y for yes or N for no, then press Enter.")
    answer = input_func(prompt + suffix).strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def validate_google_oauth_data(data):
    if not isinstance(data, dict):
        return False, "Credentials JSON must be an object."
    installed = data.get("installed")
    if not isinstance(installed, dict):
        return False, "Credentials JSON must contain an installed object."
    required = ("client_id", "client_secret", "auth_uri", "token_uri")
    for key in required:
        value = str(installed.get(key, "")).strip()
        if not value:
            return False, f"installed.{key} is missing."
        if value in PLACEHOLDER_VALUES or value.startswith("YOUR_"):
            return False, f"installed.{key} still contains a placeholder."
    return True, "Google OAuth credentials JSON is valid."


def validate_google_oauth_file(path):
    path = Path(clean_path_input(path))
    if not path.exists():
        return False, "File not found. Please check the path and try again."
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "This file is not valid JSON. Please choose the downloaded Google credentials JSON file."
    return validate_google_oauth_data(data)


def build_google_oauth_credentials(client_id, client_secret, project_id, redirect_uri="http://localhost"):
    return {
        "installed": {
            "client_id": client_id.strip(),
            "project_id": project_id.strip(),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret.strip(),
            "redirect_uris": [redirect_uri.strip() or "http://localhost"],
        }
    }


def save_google_oauth_credentials(data, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return validate_google_oauth_file(destination)


def copy_google_credentials(source, destination):
    source = Path(clean_path_input(source)).expanduser()
    destination = Path(destination)
    ok, message = validate_google_oauth_file(source)
    if not ok:
        return False, message
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
    return validate_google_oauth_file(destination)


def prompt_google_oauth_setup(paths, input_func=input):
    print("\nD. Gmail connection file setup")
    print("Gmail access uses a Google OAuth credentials JSON file.")
    print("This is downloaded from Google Cloud. It is not your Gmail password.")
    print("\nChoose Gmail connection setup:")
    print("1. I have a downloaded Google credentials JSON file")
    print("2. I want to enter Client ID and Client Secret manually")
    print("3. Skip Gmail setup for now")
    print_hint("Type one option number, for example 1, then press Enter.")
    print_hint("This is the Google credentials JSON file downloaded from Google Cloud. It is not your Gmail password.")
    choice = input_func("> ").strip() or "1"
    if choice == "2":
        print_hint("Type your answer in plain English, then press Enter.")
        client_id = input_func("Google Client ID: ").strip()
        print_hint("Paste the key, or press Enter to keep the existing saved value.")
        client_secret = input_func("Google Client Secret: ").strip()
        print_hint("Type your answer in plain English, then press Enter.")
        project_id = input_func("Google Project ID: ").strip()
        print_hint("Type your answer in plain English, then press Enter.")
        redirect_uri = input_func("Redirect URI [http://localhost]: ").strip() or "http://localhost"
        data = build_google_oauth_credentials(client_id, client_secret, project_id, redirect_uri)
        print(f"Client ID: {mask_secret(client_id)}")
        print(f"Client Secret: {mask_secret(client_secret)}")
        ok, message = save_google_oauth_credentials(data, paths.credentials_file)
        print(message)
    elif choice == "1":
        existing_source = paths.credentials_file if paths.credentials_file.exists() else None
        while True:
            if existing_source:
                print_hint("Paste the full file path. Quotes are okay. Example: D:\\Resume\\John_Doe_CV.txt")
                source = input_func(
                    "\nExisting file found:\n"
                    f"{existing_source}\n"
                    "Press Enter to keep it, or paste a new path.\n> "
                )
                source = clean_path_input(source) or str(existing_source)
            else:
                print_hint("Paste the full file path. Quotes are okay. Example: D:\\Resume\\John_Doe_CV.txt")
                source = input_func(
                    "\nPaste the full path to your Google credentials JSON file.\n"
                    r"Example: C:\Users\JohnDoe\Downloads\credentials.json"
                    "\n> "
                )
                source = clean_path_input(source)
            if not source:
                return False, "Skipped Gmail connection setup."
            ok, message = copy_google_credentials(source, paths.credentials_file)
            print(message)
            if ok:
                break
            print_hint("Type Y for yes or N for no, then press Enter.")
            retry = input_func("Enter another file path? [Y/n]: ").strip().lower()
            if retry in {"n", "no"}:
                return False, message
            existing_source = None
    else:
        return False, "Skipped Gmail connection setup."
    if ok:
        print("Keep credentials.json and token.json private. Do not commit them.")
    return ok, message


def print_welcome():
    print("================================")
    print("AI Career Agent First-Time Setup")
    print("================================")
    print("")
    print("This setup will take around 5-10 minutes.")
    print("")
    print("You will be asked for:")
    print("1. AI model API key")
    print("2. Gmail connection file")
    print("3. LinkedIn session readiness")
    print("4. CV/profile details")
    print("")
    print("You can press Enter to keep existing values.")
    print("No Gmail, Google, or LinkedIn password will be collected.")


def run_system_check(paths):
    checks = {
        "Python version": python_version_check(),
        "Project folder": {"status": "PASS" if paths.project_root.exists() else "FAIL", "message": str(paths.project_root)},
        "Gmail agent folder": {"status": "PASS" if paths.app_root.exists() else "FAIL", "message": str(paths.app_root)},
        ".venv": {"status": "PASS" if (paths.project_root / ".venv").exists() else "WARN", "message": "Recommended for isolated dependencies."},
        "Data folder": {"status": "PASS", "message": str(paths.data_dir)},
        "Output folders": {"status": "PASS", "message": "Created if missing."},
    }
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.drafts_dir.mkdir(parents=True, exist_ok=True)
    paths.jd_files_dir.mkdir(parents=True, exist_ok=True)
    paths.daily_reports_dir.mkdir(parents=True, exist_ok=True)
    paths.browser_profiles_dir.mkdir(parents=True, exist_ok=True)
    paths.linkedin_profile_dir.mkdir(parents=True, exist_ok=True)
    print("\nB. System check")
    for name, result in checks.items():
        print(f"{result['status']:4} {name}: {result['message']}")
    return checks


def print_gmail_guidance():
    print("\nE. Gmail guidance")
    print("Gmail uses Google OAuth credentials JSON.")
    print("OAuth browser authorization will generate token.json locally.")
    print("Gmail username/password is not required and must not be collected.")


def print_linkedin_guidance(paths):
    print("\nF. LinkedIn guidance")
    print("LinkedIn uses a local browser session/profile login.")
    print("Do not store a LinkedIn password.")
    if paths.linkedin_profile_dir.exists():
        print("LinkedIn browser profile folder exists.")
        return True
    print("WARN LinkedIn session is missing. You can reconnect later from the startup menu.")
    return False


def has_target_roles(profile_text):
    return "target_roles:" in profile_text and "primary:" in profile_text and "- " in profile_text


def validate_setup(paths):
    root = paths.project_root
    cv_path = root / "cv.md"
    profile_path = root / "config" / "profile.yml"
    mode_profile_path = root / "modes" / "_profile.md"
    env_values = read_env_file(paths.root_env_file)
    google_ok, google_message = validate_google_oauth_file(paths.credentials_file)
    profile_text = profile_path.read_text(encoding="utf-8", errors="ignore") if profile_path.exists() else ""
    output_dirs = [
        paths.data_dir,
        paths.jd_files_dir,
        paths.daily_reports_dir,
        paths.browser_profiles_dir,
    ]

    return {
        "cv.md exists and is not empty": {
            "status": "PASS" if cv_path.exists() and cv_path.read_text(encoding="utf-8", errors="ignore").strip() else "FAIL",
            "message": str(cv_path),
        },
        "config/profile.yml exists": {
            "status": "PASS" if profile_path.exists() else "FAIL",
            "message": str(profile_path),
        },
        "modes/_profile.md exists": {
            "status": "PASS" if mode_profile_path.exists() else "FAIL",
            "message": str(mode_profile_path),
        },
        "target roles present": {
            "status": "PASS" if has_target_roles(profile_text) else "FAIL",
            "message": "target_roles.primary",
        },
        "location present": {
            "status": "PASS" if "location:" in profile_text else "FAIL",
            "message": "candidate/location",
        },
        "work preference present": {
            "status": "PASS" if "work_preference:" in profile_text else "FAIL",
            "message": "work_preference",
        },
        "AI provider and key present": {
            "status": "PASS" if env_values.get("AI_PROVIDER_NAME") and env_values.get("AI_API_KEY") else "WARN",
            "message": "Configure one AI provider and API key before evaluation.",
        },
        "AI evaluation models configured": {
            "status": "PASS"
            if env_values.get("PRIMARY_MODEL")
            and env_values.get("FALLBACK_MODEL")
            and env_values.get("SECOND_FALLBACK_MODEL")
            else "WARN",
            "message": "Configure primary, fallback, and second fallback models from the same provider.",
        },
        "Google OAuth credentials JSON exists": {
            "status": "PASS" if paths.credentials_file.exists() else "WARN",
            "message": str(paths.credentials_file),
        },
        "Google OAuth credentials JSON is valid and not placeholder-only": {
            "status": "PASS" if google_ok else "WARN",
            "message": google_message,
        },
        "Gmail token path configured": {
            "status": "PASS" if env_values.get("GMAIL_TOKEN_PATH") else "FAIL",
            "message": env_values.get("GMAIL_TOKEN_PATH", "GMAIL_TOKEN_PATH"),
        },
        "Gmail token exists": {
            "status": "PASS" if paths.token_file.exists() else "WARN",
            "message": "OAuth authorization is pending." if not paths.token_file.exists() else str(paths.token_file),
        },
        "LinkedIn browser profile exists": {
            "status": "PASS" if paths.linkedin_profile_dir.exists() else "WARN",
            "message": "Reconnect may be needed." if not paths.linkedin_profile_dir.exists() else str(paths.linkedin_profile_dir),
        },
        "output folders exist": {
            "status": "PASS" if all(path.exists() for path in output_dirs) else "FAIL",
            "message": ", ".join(str(path) for path in output_dirs),
        },
    }


def print_validation(results):
    print("\nSetup validation")
    for name, result in results.items():
        print(f"{result['status']:4} {name}: {result['message']}")


def state_from_validation(results):
    state = default_setup_state()
    statuses = {name: result["status"] for name, result in results.items()}
    state["cv_setup_completed"] = statuses["cv.md exists and is not empty"] == "PASS"
    state["profile_setup_completed"] = (
        statuses["config/profile.yml exists"] == "PASS"
        and statuses["modes/_profile.md exists"] == "PASS"
        and statuses["target roles present"] == "PASS"
    )
    state["credentials_setup_completed"] = statuses["Google OAuth credentials JSON is valid and not placeholder-only"] == "PASS"
    state["google_credentials_setup_completed"] = state["credentials_setup_completed"]
    state["gmail_setup_completed"] = statuses["Gmail token path configured"] == "PASS"
    state["linkedin_setup_completed"] = statuses["LinkedIn browser profile exists"] == "PASS"
    state["ai_model_setup_completed"] = (
        statuses["AI provider and key present"] == "PASS"
        and statuses["AI evaluation models configured"] == "PASS"
    )
    state["first_time_setup_completed"] = all(
        bool(state.get(key)) for key in REQUIRED_COMPLETION_FLAGS if key != "first_time_setup_completed"
    )
    if state["first_time_setup_completed"]:
        state["setup_completed_at"] = datetime.now(timezone.utc).isoformat()
    return state


def run_profile_setup(paths, input_func=input):
    from setup_user_profile import run_profile_setup as run_user_profile_setup

    return run_user_profile_setup(paths.project_root, paths.app_root, input_func=input_func)


def main(input_func=input):
    paths = get_setup_paths()
    print_welcome()
    run_system_check(paths)
    prompt_env_setup(paths, input_func=input_func)
    prompt_google_oauth_setup(paths, input_func=input_func)
    print_gmail_guidance()
    print_linkedin_guidance(paths)
    print("\nG. CV/profile setup")
    if prompt_yes_no("Create or review CV/profile setup now?", default=True, input_func=input_func):
        run_profile_setup(paths, input_func=input_func)
    results = validate_setup(paths)
    print_validation(results)
    state = state_from_validation(results)
    save_setup_state(paths, state)
    print("\nSetup finished. Returning to the AI Career Agent startup menu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

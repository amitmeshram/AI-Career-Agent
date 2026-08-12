import os
from pathlib import Path


AI_AGENT_ROOT = Path(__file__).resolve().parent


def resolve_career_ops_root():
    configured_root = os.getenv("CAREER_OPS_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    if AI_AGENT_ROOT.name == "gmail-agent" and AI_AGENT_ROOT.parent.name == "apps":
        return AI_AGENT_ROOT.parent.parent.resolve()

    return (AI_AGENT_ROOT.parent / "career-ops").resolve()


CAREER_OPS_ROOT = resolve_career_ops_root()

DATA_DIR = CAREER_OPS_ROOT / "data" / "gmail-agent"
JD_FILES_DIR = CAREER_OPS_ROOT / "jds"
DAILY_REPORTS_DIR = CAREER_OPS_ROOT / "reports" / "daily"
BROWSER_PROFILES_DIR = DATA_DIR / "browser_profiles"
LINKEDIN_BROWSER_PROFILE_DIR = BROWSER_PROFILES_DIR / "linkedin"

SCRAPED_JOBS_FILE = DATA_DIR / "scraped_jobs.json"
PROCESSED_JOBS_FILE = DATA_DIR / "processed_jobs.json"
PROCESSED_LINKS_FILE = DATA_DIR / "processed_links.json"
CURRENT_RUN_JOBS_FILE = DATA_DIR / "current_run_jobs.json"
CURRENT_RUN_REPORTS_FILE = DATA_DIR / "current_run_reports.json"

ENV_FILE = AI_AGENT_ROOT / ".env"
GMAIL_CREDENTIALS_FILE = AI_AGENT_ROOT / "credentials.json"
GMAIL_TOKEN_FILE = AI_AGENT_ROOT / "token.json"

for folder in (
    DATA_DIR,
    JD_FILES_DIR,
    DAILY_REPORTS_DIR,
    BROWSER_PROFILES_DIR,
    LINKEDIN_BROWSER_PROFILE_DIR,
):
    folder.mkdir(parents=True, exist_ok=True)

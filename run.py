import json
import platform
import re
import subprocess
import sys
from pathlib import Path


MIN_PYTHON = (3, 10)
REQUIRED_SETUP_FLAGS = (
    "first_time_setup_completed",
    "cv_setup_completed",
    "profile_setup_completed",
    "credentials_setup_completed",
    "google_credentials_setup_completed",
    "gmail_setup_completed",
    "linkedin_setup_completed",
    "ai_model_setup_completed",
)
REQUIRED_STARTUP_FLAGS = (
    "cv_setup_completed",
    "profile_setup_completed",
    "ai_model_setup_completed",
)


def is_python_supported(version_info=None):
    version_info = version_info or sys.version_info
    return tuple(version_info[:2]) >= MIN_PYTHON


def print_python_guidance():
    required = ".".join(str(part) for part in MIN_PYTHON)
    print(f"Python {required}+ is required to run AI Career Agent.")
    print("Install a current Python release, then run: python run.py")
    if platform.system() == "Windows":
        print("Windows option: winget install Python.Python.3.12")


def get_venv_python_path(project_root, system_name=None):
    system_name = system_name or platform.system()
    project_root = Path(project_root)
    if system_name == "Windows":
        return project_root / ".venv" / "Scripts" / "python.exe"
    return project_root / ".venv" / "bin" / "python"


def prompt_yes_no(prompt, default=False, input_func=input):
    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input_func(prompt + suffix).strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def ensure_venv(project_root, input_func=input, run_func=subprocess.run):
    project_root = Path(project_root)
    venv_dir = project_root / ".venv"
    venv_python = get_venv_python_path(project_root)

    if venv_python.exists():
        return venv_python

    if venv_dir.exists():
        return Path(sys.executable)

    print("No .venv was found for this project.")
    if prompt_yes_no("Create one now with python -m venv .venv?", default=True, input_func=input_func):
        result = run_func([sys.executable, "-m", "venv", ".venv"], cwd=str(project_root))
        if getattr(result, "returncode", 0) != 0:
            print("Virtual environment creation failed. Continuing with the current Python.")
            return Path(sys.executable)
        return venv_python

    print("Continuing with the current Python.")
    return Path(sys.executable)


def setup_state_path(project_root):
    return Path(project_root) / "data" / "gmail-agent" / "setup_state.json"


def load_setup_state(project_root):
    path = setup_state_path(project_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def is_setup_state_complete(project_root):
    state = load_setup_state(project_root)
    return all(bool(state.get(flag)) for flag in REQUIRED_SETUP_FLAGS)


def is_startup_setup_complete(project_root):
    state = load_setup_state(project_root)
    return all(bool(state.get(flag)) for flag in REQUIRED_STARTUP_FLAGS)


def is_first_time_setup_complete(project_root):
    return is_setup_state_complete(project_root)


def load_first_time_setup(app_root):
    app_root = Path(app_root)
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    import first_time_setup

    return first_time_setup


def resolve_configured_path(value, project_root):
    value = str(value or "").strip().strip("\"'")
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(project_root) / path
    return path


def relative_label(path, project_root):
    try:
        return str(Path(path).resolve().relative_to(Path(project_root).resolve()))
    except ValueError:
        return str(path)


def command_guidance(system_name=None):
    system_name = system_name or platform.system()
    if system_name == "Windows":
        return [
            r".\.venv\Scripts\python.exe run.py",
            "py run.py",
        ]
    return [
        "./.venv/bin/python run.py",
        "python3 run.py",
    ]


def check_sections_a_to_f(project_root, python_path=None, first_time_setup_module=None):
    project_root = Path(project_root)
    app_root = project_root / "apps" / "gmail-agent"
    first_time_setup_module = first_time_setup_module or load_first_time_setup(app_root)
    paths = first_time_setup_module.get_setup_paths(project_root=project_root, app_root=app_root)
    state = first_time_setup_module.load_setup_state(paths)
    env_values = first_time_setup_module.read_env_file(paths.root_env_file)

    configured_credentials = resolve_configured_path(
        env_values.get("GOOGLE_OAUTH_CREDENTIALS_JSON") or str(paths.credentials_file),
        project_root,
    )
    configured_token = resolve_configured_path(
        env_values.get("GMAIL_TOKEN_PATH"),
        project_root,
    )
    google_ok, google_message = (
        first_time_setup_module.validate_google_oauth_file(configured_credentials)
        if configured_credentials
        else (False, "Google OAuth credentials JSON path is not configured.")
    )
    linkedin_ready = paths.linkedin_profile_dir.exists() or bool(state.get("linkedin_setup_completed"))
    required_folders = (
        paths.data_dir,
        project_root / "reports",
        project_root / "jds",
    )

    checks = [
        {
            "name": "Python version",
            "ready": is_python_supported(),
            "critical": True,
            "detail": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        {
            "name": "Virtual environment",
            "ready": bool(python_path and Path(python_path).exists())
            or get_venv_python_path(project_root).exists()
            or (project_root / ".venv").exists(),
            "critical": True,
            "detail": str(get_venv_python_path(project_root)),
        },
        {
            "name": ".env file",
            "ready": paths.root_env_file.exists(),
            "critical": True,
            "detail": str(paths.root_env_file),
        },
        {
            "name": "AI provider",
            "ready": bool(env_values.get("AI_PROVIDER_NAME")),
            "critical": False,
            "section": "Needed later for job evaluation",
            "detail": "AI_PROVIDER_NAME",
        },
        {
            "name": "AI API key",
            "ready": bool(env_values.get("AI_API_KEY")),
            "critical": False,
            "section": "Needed later for job evaluation",
            "detail": "AI_API_KEY",
        },
        {
            "name": "Primary AI model",
            "ready": bool(env_values.get("PRIMARY_MODEL")),
            "critical": False,
            "section": "Needed later for job evaluation",
            "detail": "PRIMARY_MODEL",
        },
        {
            "name": "Fallback AI model",
            "ready": bool(env_values.get("FALLBACK_MODEL")),
            "critical": False,
            "section": "Needed later for job evaluation",
            "detail": "FALLBACK_MODEL",
        },
        {
            "name": "Second fallback AI model",
            "ready": bool(env_values.get("SECOND_FALLBACK_MODEL")),
            "critical": False,
            "section": "Needed later for job evaluation",
            "detail": "SECOND_FALLBACK_MODEL",
        },
        {
            "name": "Google OAuth credentials JSON",
            "ready": bool(configured_credentials and configured_credentials.exists()),
            "critical": False,
            "section": "Optional for Gmail scanning",
            "detail": str(configured_credentials) if configured_credentials else "GOOGLE_OAUTH_CREDENTIALS_JSON",
        },
        {
            "name": "Google OAuth credentials JSON is not placeholder-only",
            "ready": google_ok,
            "critical": False,
            "section": "Optional for Gmail scanning",
            "detail": google_message,
        },
        {
            "name": "Gmail token path",
            "ready": bool(configured_token),
            "critical": False,
            "section": "Optional for Gmail scanning",
            "detail": str(configured_token) if configured_token else "GMAIL_TOKEN_PATH",
        },
        {
            "name": "Gmail token file",
            "ready": bool(configured_token and configured_token.exists()),
            "critical": False,
            "section": "Optional for Gmail scanning",
            "detail": "OAuth authorization will create it." if configured_token and not configured_token.exists() else str(configured_token),
        },
        {
            "name": "LinkedIn browser session",
            "ready": linkedin_ready,
            "critical": False,
            "section": "Optional for LinkedIn scraping",
            "detail": str(paths.linkedin_profile_dir),
        },
    ]
    for folder in required_folders:
        checks.append(
            {
                "name": f"Required folder: {relative_label(folder, project_root)}",
                "ready": folder.exists(),
                "critical": True,
                "section": "Required for onboarding",
                "detail": str(folder),
            }
        )
    return checks


def critical_missing_items(checks):
    return [check for check in checks if check.get("critical") and not check.get("ready")]


def print_readiness_summary(checks, system_name=None):
    print("AI Career Agent Setup Check")

    section_names = (
        "Required for onboarding",
        "Needed later for job evaluation",
        "Optional for Gmail scanning",
        "Optional for LinkedIn scraping",
    )
    default_sections = {
        "Python version": "Required for onboarding",
        "Virtual environment": "Required for onboarding",
        ".env file": "Required for onboarding",
    }

    for section_name in section_names:
        section_checks = [
            check
            for check in checks
            if check.get("section") == section_name or default_sections.get(check["name"]) == section_name
        ]
        if not section_checks:
            continue
        print("")
        print(f"{section_name}:")
        for check in section_checks:
            marker = "OK" if check.get("ready") else "MISSING"
            print(f"- [{marker}] {check['name']}")

    if critical_missing_items(checks):
        print("")
        print("Action:")
        print("Please fill the missing onboarding information, then enter command:")
        for command in command_guidance(system_name=system_name):
            print(command)
        return

    print("")
    print("Some optional integrations are not ready yet.")
    print("Starting guided CV/profile setup first.")
    print("You can add API keys, Gmail, and LinkedIn access later.")


def reset_setup_state(project_root, input_func=input):
    path = setup_state_path(project_root)
    print("This will delete only data/gmail-agent/setup_state.json.")
    if not prompt_yes_no("Reset setup state?", default=False, input_func=input_func):
        print("Setup reset cancelled.")
        return False
    if path.exists():
        path.chmod(0o666)
        path.unlink()
        print("Deleted data/gmail-agent/setup_state.json.")
    else:
        print("No setup_state.json found.")
    return True


def is_section_g_complete(project_root):
    state = load_setup_state(project_root)
    return bool(state.get("cv_setup_completed") and state.get("profile_setup_completed"))


def run_python(python_path, script_path):
    return subprocess.run([str(python_path), str(script_path)])


def patch_mandatory_question_totals(setup_user_profile_module):
    total = len(setup_user_profile_module.MANDATORY_QUESTIONS)
    patched = []
    for index, item in enumerate(setup_user_profile_module.MANDATORY_QUESTIONS, start=1):
        item = dict(item)
        item["question"] = item["question"].replace(f"Question {index} of 8:", f"Question {index} of {total}:")
        patched.append(item)
    setup_user_profile_module.MANDATORY_QUESTIONS = tuple(patched)


def patch_optional_questions(setup_user_profile_module):
    removed_keys = {
        "visa_notes",
        "management_experience",
        "salary_flexibility",
        "deal_breakers",
        "preferred_sources",
        "reporting_line",
        "preferred_company",
        "leadership_preference",
    }
    patched = []
    for key, label, example in setup_user_profile_module.OPTIONAL_QUESTIONS:
        if key in removed_keys:
            continue
        if key == "extra_achievements":
            example = "Example: Led a turnaround program that saved USD 2 Mn"
        patched.append((key, label, example))
    setup_user_profile_module.OPTIONAL_QUESTIONS = tuple(patched)


def collect_profile_answers(setup_user_profile_module, input_func=input):
    answers = {}
    raw_user_input = {}
    print("\nNow I need a few career preferences that are usually not clear from the CV.")
    print("These are required because they affect job scoring.")
    for item in setup_user_profile_module.MANDATORY_QUESTIONS:
        key = item["key"]
        print("")
        print(item["question"])
        if item.get("why"):
            print(item["why"])
        choices = item.get("choices")
        if choices:
            print(item.get("choice_intro", "Choose one:"))
            choice_numbers = item.get("choice_numbers") or tuple(str(index) for index in range(1, len(choices) + 1))
            for number, choice in zip(choice_numbers, choices):
                print(f"{number}. {choice}")
        setup_user_profile_module.print_hint(item["hint"])
        raw = input_func("Answer: ").strip()
        raw = setup_user_profile_module.normalize_choice(raw, choices, item.get("choice_numbers")) if choices else raw
        if key == "expected_salary":
            raw = prompt_valid_salary(raw, setup_user_profile_module, input_func=input_func)
        if key == "max_job_alerts_to_process":
            raw = prompt_positive_integer(raw, setup_user_profile_module, input_func=input_func, default_value=5)
        if key == "max_job_links_to_process":
            raw = prompt_positive_integer(raw, setup_user_profile_module, input_func=input_func, default_value=50)
        raw_user_input[key] = raw
        value = (
            raw
            if key in {"max_job_alerts_to_process", "max_job_links_to_process"}
            else setup_user_profile_module.approve_normalized_value(key, raw, input_func=input_func)
        )
        answers[key] = setup_user_profile_module.normalize_work_preference(value) if key == "work_preference" else value

    print("\nOptional questions can improve scoring and recommendations, but you can skip them.")
    print("Choose:")
    print("1. Answer all optional questions")
    print("2. Skip all optional questions")
    setup_user_profile_module.print_hint("Type one option number, for example 1, then press Enter.")
    optional_mode = input_func("Answer: ").strip() or "2"
    if optional_mode == "1":
        for key, label, example in setup_user_profile_module.OPTIONAL_QUESTIONS:
            print("")
            print(f"{label} (optional)")
            print(example)
            setup_user_profile_module.print_hint("Press Enter to skip this optional question.")
            raw = input_func("Answer: ").strip()
            raw_user_input[key] = raw
            answers[key] = (
                setup_user_profile_module.approve_normalized_value(key, raw, input_func=input_func)
                if raw
                else ""
            )
    return answers, raw_user_input


def prompt_valid_salary(raw, setup_user_profile_module, input_func=input):
    value = str(raw or "").strip()
    while not is_valid_salary_answer(value):
        print("Please enter the salary target as text, not an option number.")
        setup_user_profile_module.print_hint("Include currency and period, for example: SAR 25,000/month.")
        value = input_func("Answer: ").strip()
    return value


def prompt_positive_integer(raw, setup_user_profile_module, input_func=input, default_value=25):
    value = str(raw or "").strip()
    if not value:
        return str(default_value)
    while not re.fullmatch(r"[1-9]\d*", value):
        print("Please enter a whole number greater than zero.")
        setup_user_profile_module.print_hint("Type digits only, for example: 25.")
        value = input_func("Answer: ").strip()
        if not value:
            value = str(default_value)
    return value


def is_valid_salary_answer(value):
    text = str(value or "").strip()
    if not text:
        return False
    if re.fullmatch(r"\d", text):
        return False
    has_digit = bool(re.search(r"\d", text))
    has_currency_or_period = bool(
        re.search(
            r"\b(SAR|USD|EUR|GBP|INR|AED|KWD|QAR|OMR|BHD|per|month|monthly|year|yearly|annual|annually|/)\b",
            text,
            flags=re.I,
        )
    )
    return has_digit and has_currency_or_period


def unique_nonempty(items):
    seen = set()
    result = []
    for item in items:
        text = str(item or "").strip().strip(",")
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


SECTION_ALIASES = {
    "professional_summary": (
        "summary",
        "profile",
        "profile summary",
        "executive summary",
        "career summary",
        "professional summary",
    ),
    "work_experience": (
        "experience",
        "employment",
        "professional experience",
        "employment history",
        "career history",
        "work experience",
    ),
    "skills": (
        "skills",
        "technical skills",
        "core competencies",
        "key skills",
        "tools",
        "functional skills",
    ),
    "education": (
        "education",
        "academic background",
        "qualifications",
    ),
    "certifications": (
        "certifications",
        "certificates",
        "certification",
        "professional certifications",
    ),
    "languages": (
        "languages",
        "language",
    ),
    "projects": (
        "projects",
        "selected projects",
        "portfolio",
    ),
}

KNOWN_SECTION_HEADINGS = {
    alias
    for aliases in SECTION_ALIASES.values()
    for alias in aliases
}


def normalize_heading(value):
    value = re.sub(r"^[#\s>*\-•–—*]+", "", str(value or ""))
    value = re.sub(r"[:：]+$", "", value)
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def normalize_cv_text(text):
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u2022\u00b7\u25aa\u25e6\u2043\uf0a7\u00a7]", "-", text)
    text = re.sub(r"(?m)^[?\ufffd]\s+", "- ", text)
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    normalized_lines = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        normalized_cells = {re.sub(r"\s+", " ", cell).strip().lower() for cell in cells}
        if len(cells) > 1 and len(normalized_cells) == 1:
            line = cells[0]
        normalized_lines.append(line)
    return "\n".join(normalized_lines)


def is_section_heading(line, allowed=None):
    raw = str(line or "").strip()
    if not raw:
        return False
    if len(raw.split()) > 6:
        return False
    normalized = normalize_heading(raw)
    headings = set(allowed or KNOWN_SECTION_HEADINGS)
    if normalized in headings:
        return True
    if any(re.match(rf"^\s*{re.escape(alias)}\s*[:：]\s*\S+", raw, flags=re.I) for alias in headings):
        return True
    return raw.endswith(":") and normalized in headings


def extract_inline_section_value(line, aliases):
    raw = str(line or "").strip()
    for alias in aliases:
        match = re.match(rf"^\s*{re.escape(alias)}\s*[:：]\s*(.+)$", raw, flags=re.I)
        if match:
            return match.group(1).strip()
    return ""


def extract_section_text(text, aliases):
    lines = normalize_cv_text(text).splitlines()
    wanted = {normalize_heading(alias) for alias in aliases}
    start = None
    inline = ""
    for index, line in enumerate(lines):
        inline = extract_inline_section_value(line, aliases)
        if inline:
            start = index + 1
            break
        if is_section_heading(line, wanted):
            start = index + 1
            break
    if start is None:
        return ""

    collected = [inline] if inline else []
    for line in lines[start:]:
        if is_section_heading(line):
            break
        collected.append(line.rstrip())
    return "\n".join(item for item in collected if item.strip()).strip()


def split_cv_list(value, max_words=None):
    parts = re.split(r"[,;|/]\s*|\n+", str(value or ""))
    cleaned = []
    for part in parts:
        part = re.sub(r"^\s*[-*]\s*", "", part).strip()
        if not part:
            continue
        if max_words and len(part.split()) > max_words:
            continue
        cleaned.append(part)
    return unique_nonempty(cleaned)


def extract_labeled_value(lines, labels):
    for line in lines:
        for label in labels:
            match = re.match(rf"^\s*{re.escape(label)}\s*[:：]\s*(.+)$", line, flags=re.I)
            if match:
                return match.group(1).strip()
    return ""


def extract_url(text, keyword):
    url_match = re.search(rf"(?:(?:https?://|www\.)[^\s<>)]*|){keyword}[^\s<>)]*", text, flags=re.I)
    return url_match.group(0).rstrip(".,;") if url_match else ""


def extract_contact_details(text):
    normalized = normalize_cv_text(text)
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", normalized)
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", normalized)
    urls = re.findall(r"(?:https?://|www\.)[^\s<>)]+|(?:linkedin|github)\.com/[^\s<>)]+", normalized, flags=re.I)
    linkedin = extract_url(normalized, "linkedin.com")
    github = extract_url(normalized, "github.com")
    portfolio = next((url.rstrip(".,;") for url in urls if url.rstrip(".,;") not in {linkedin, github}), "")
    location = extract_labeled_value(lines[:20], ("location", "based in", "address", "current location"))
    if not location:
        header_lines = []
        for line in normalized.splitlines()[:12]:
            if not line.strip():
                break
            header_lines.append(line.strip())
        for line in header_lines:
            for part in re.split(r"\s*[|•]\s*", line):
                if "@" in part or re.search(r"https?://|www\.|linkedin\.com|github\.com|\d{4,}", part, flags=re.I):
                    continue
                if re.fullmatch(r"[A-Za-z .'-]+,\s*[A-Za-z .'-]+", part.strip()):
                    location = part.strip()
                    break
            if location:
                break
    return {
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0).strip() if phone_match else "",
        "location": location,
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio,
    }


def parse_experience_blocks(text):
    if not str(text or "").strip():
        return ""
    lines = [line for line in clean_work_experience_text(text).splitlines() if line.strip()]
    if lines == ["Not provided"]:
        return ""
    if not lines:
        return ""
    expanded_lines = []
    embedded_header_pattern = re.compile(
        r"\s+(?:-|\|)\s+([A-Z][A-Za-z0-9&. ]{2,60})\s*(?:-|–|—)\s*"
        r"([^|\n]+?\|\s*[A-Za-z .'-]+,\s*[A-Za-z .'-]+\s*\|\s*"
        r"(?:.*(?:present|\d{4}|'\d{2}).*))",
        flags=re.I,
    )
    for line in lines:
        embedded = embedded_header_pattern.search(line)
        if embedded and embedded.start() > 20:
            before = line[: embedded.start()].strip()
            if before:
                expanded_lines.append(before)
            expanded_lines.append(f"{embedded.group(1).strip()} - {embedded.group(2).strip()}")
        else:
            expanded_lines.append(line)
    lines = expanded_lines
    parsed = []
    seen_headers = set()
    skipping_duplicate = False
    header_pattern = re.compile(
        r"(?i)(.+?)\s*(?:\||-|–|—)\s*(.+?)"
        r"(?:\s*(?:\||-|–|—)\s*([A-Za-z .'-]+,\s*[A-Za-z .'-]+))?"
        r"\s*(?:\||-|–|—)\s*"
        r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|present|\d{4}|'\d{2}).*)"
    )
    for line in lines:
        match = header_pattern.match(line)
        if match and not line.startswith("- "):
            if parsed:
                parsed.append("")
            company, role, location, dates = (part.strip() if part else "" for part in match.groups())
            header = f"{company} - {role}"
            if location:
                header += f" | {location}"
            if dates:
                header += f" | {dates}"
            header_key = re.sub(r"\s+", " ", header).strip().lower()
            if header_key in seen_headers:
                skipping_duplicate = True
                continue
            seen_headers.add(header_key)
            skipping_duplicate = False
            parsed.append(header)
            continue
        if skipping_duplicate:
            continue
        if line.startswith(("- ", "* ", "– ")):
            parsed.append(re.sub(r"^[-*–]\s*", "- ", line))
        elif is_experience_bullet_line(line):
            parsed.append(f"- {line}")
        else:
            parsed.append(line)
    return "\n".join(parsed).strip()


def is_experience_bullet_line(line):
    action_verbs = (
        "achieved",
        "automated",
        "bagged",
        "boosted",
        "built",
        "delivered",
        "deployed",
        "designed",
        "developed",
        "eliminated",
        "executed",
        "expanded",
        "formulated",
        "identified",
        "implemented",
        "improved",
        "increased",
        "introduced",
        "managed",
        "manage",
        "partnered",
        "prepared",
        "received",
        "redesigned",
        "reduced",
        "successfully",
        "trained",
    )
    normalized = str(line or "").strip().lower()
    return normalized.startswith(tuple(f"{verb} " for verb in action_verbs))


def parse_cv_text(setup_user_profile_module, text):
    normalized = normalize_cv_text(text)
    contact = extract_contact_details(normalized)
    summary = extract_section_text(normalized, SECTION_ALIASES["professional_summary"])
    skills_text = extract_section_text(normalized, SECTION_ALIASES["skills"])
    certifications_text = extract_section_text(normalized, SECTION_ALIASES["certifications"])
    languages_text = extract_section_text(normalized, SECTION_ALIASES["languages"])
    work_text = extract_section_text(normalized, SECTION_ALIASES["work_experience"])
    return {
        "full_name": setup_user_profile_module.first_nonempty_line(normalized),
        "email": contact["email"],
        "phone": contact["phone"],
        "location": contact["location"],
        "linkedin": contact["linkedin"],
        "github": contact["github"],
        "portfolio": contact["portfolio"],
        "professional_summary": summary,
        "skills": split_cv_list(skills_text, max_words=6),
        "work_experience": parse_experience_blocks(work_text),
        "projects": extract_section_text(normalized, SECTION_ALIASES["projects"]),
        "education": extract_section_text(normalized, SECTION_ALIASES["education"]),
        "certifications": split_cv_list(certifications_text, max_words=8),
        "languages": split_cv_list(languages_text, max_words=4),
        "raw_text": text,
    }


def improve_pdf_text(text):
    text = normalize_cv_text(text)
    text = re.sub(r"(?<![.!?:])\n(?=[a-z])", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_docx_cv(setup_user_profile_module, path):
    try:
        docx = setup_user_profile_module.import_module("docx")
    except ImportError:
        setup_user_profile_module.print_missing_dependency("python-docx")
        return None
    print("Reading Word CV...")
    document = docx.Document(str(path))
    chunks = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            paragraph = docx.text.paragraph.Paragraph(child, document)
            text = paragraph.text.strip()
            if text:
                chunks.append(text)
        elif tag == "tbl":
            table = docx.table.Table(child, document)
            for row in table.rows:
                cells = [
                    "\n".join(paragraph.text.strip() for paragraph in cell.paragraphs if paragraph.text.strip())
                    for cell in row.cells
                ]
                cells = [cell for cell in cells if cell]
                if cells:
                    chunks.append(" | ".join(cells))
    text = normalize_cv_text("\n".join(chunks).strip())
    if text:
        print("Text extracted successfully.")
    return text


def read_pdf_cv(setup_user_profile_module, path):
    try:
        pypdf = setup_user_profile_module.import_module("pypdf")
    except ImportError:
        setup_user_profile_module.print_missing_dependency("pypdf")
        return None
    print("Reading PDF CV...")
    reader = pypdf.PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = improve_pdf_text("\n".join(page.strip() for page in pages if page.strip()))
    if len(text) < setup_user_profile_module.MIN_EXTRACTED_PDF_CHARS:
        print("This PDF may be scanned or image-based. Please provide a Word/.docx version or paste the CV text.")
        return None
    print("Text extracted successfully.")
    return text


def clean_work_experience_text(text):
    cleaned = []
    for line in str(text or "").splitlines():
        line = line.strip()
        line = re.sub(r"^[\u2022\u00b7\u25aa\u25e6\u2043\uf0a7\u00a7]+", "-", line)
        line = re.sub(r"^[?\ufffd]\s+", "- ", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line in {"?", "\ufffd"}:
            continue
        if line in {"", "-", "*"}:
            continue
        if re.match(r"^[-*]\s*$", line):
            continue
        bullet_match = re.match(r"^[-*]\s*(.+)$", line)
        if bullet_match:
            line = f"- {bullet_match.group(1).strip()}"
        cleaned.append(line)
    return "\n".join(cleaned) or "Not provided"


def build_cv_markdown(setup_user_profile_module, parsed, answers):
    target_roles = setup_user_profile_module.split_list(answers.get("target_roles", ""))
    skills = unique_nonempty(
        list(parsed.get("skills", []))
        + setup_user_profile_module.split_list(answers.get("extra_tools", ""))
    )
    certifications = parsed.get("certifications", []) or setup_user_profile_module.split_list(
        answers.get("certifications", "")
    )
    languages = parsed.get("languages", []) or setup_user_profile_module.split_list(answers.get("languages", ""))
    key_achievements = setup_user_profile_module.split_list(answers.get("extra_achievements", ""))
    summary = parsed.get("professional_summary") or answers.get("career_direction") or "Professional summary not provided."
    lines = [
        f"# {parsed.get('full_name') or 'Candidate'}",
        "",
        "## Contact",
        f"- Email: {parsed.get('email') or 'Not provided'}",
        f"- Phone: {parsed.get('phone') or 'Not provided'}",
        f"- Location: {parsed.get('location') or answers.get('target_locations') or 'Not provided'}",
        f"- LinkedIn: {parsed.get('linkedin') or 'Not provided'}",
        f"- GitHub: {parsed.get('github') or 'Not provided'}",
        f"- Portfolio: {parsed.get('portfolio') or answers.get('portfolio_links') or 'Not provided'}",
        "",
        "## Target Roles",
        setup_user_profile_module.markdown_list(target_roles),
        "",
        "## Professional Summary",
        summary,
        "",
        "## Skills",
        setup_user_profile_module.markdown_list(skills),
        "",
        "## Work Experience",
        clean_work_experience_text(parsed.get("work_experience")),
        "",
    ]
    if key_achievements:
        lines.extend(
            [
                "## Key Achievements",
                setup_user_profile_module.markdown_list(key_achievements),
                "",
            ]
        )
    lines.extend(
        [
            "## Projects",
            parsed.get("projects") or answers.get("portfolio_links") or "Not provided",
            "",
            "## Education",
            parsed.get("education") or "Not provided",
            "",
            "## Certifications",
            setup_user_profile_module.markdown_list(certifications),
            "",
            "## Languages",
            setup_user_profile_module.markdown_list(languages),
            "",
        ]
    )
    return "\n".join(lines)


def approve_cv_draft_after_questionnaire(setup_user_profile_module, cv_path, parsed, input_func=input):
    cv_path = Path(cv_path).resolve()
    print("\nCV draft created successfully.")
    print("")
    print("Please review this file before continuing:")
    print(cv_path)
    print("")
    print("This file is important because it becomes the source for job scoring.")
    setup_user_profile_module.print_hint("Type Y for yes or N for no, then press Enter.")
    if input_func("Open cv.md now for review? [Y/n]: ").strip().lower() in {"", "y", "yes"}:
        try:
            setup_user_profile_module.open_path_default(cv_path)
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"Could not open cv.md automatically: {exc}")
            print(cv_path)

    while True:
        print("")
        print("After reviewing cv.md, choose:")
        print("1. Approve and continue to final review")
        print("2. I edited cv.md and want to continue")
        print("3. Provide another CV file")
        print("4. Exit setup for now")
        setup_user_profile_module.print_hint("Type one option number, for example: 1.")
        choice = input_func("Answer: ").strip()
        if choice in {"1", "2"}:
            cv_text = cv_path.read_text(encoding="utf-8", errors="ignore")
            if (
                setup_user_profile_module.cv_has_missing_work_experience_marker(cv_text)
                and not parsed.get("_work_experience_continue_anyway")
            ):
                print("Work Experience is still marked as Not provided in cv.md.")
                setup_user_profile_module.print_hint("Type Y only if you explicitly want to continue anyway.")
                if input_func("Continue anyway? [y/N]: ").strip().lower() not in {"y", "yes"}:
                    continue
                parsed["_work_experience_continue_anyway"] = True
            if choice == "2":
                parsed = setup_user_profile_module.parse_cv_text(cv_text)
            return "continue", parsed
        if choice == "3":
            return "retry", parsed
        if choice == "4":
            return "exit", parsed
        print("Please choose 1, 2, 3, or 4.")


def run_profile_setup(project_root, app_root, input_func=input):
    app_root = Path(app_root)
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    import setup_user_profile

    original_mandatory_questions = setup_user_profile.MANDATORY_QUESTIONS
    original_optional_questions = setup_user_profile.OPTIONAL_QUESTIONS
    original_collect_profile_answers = setup_user_profile.collect_profile_answers
    original_build_cv_markdown = setup_user_profile.build_cv_markdown
    original_parse_cv_text = setup_user_profile.parse_cv_text
    original_read_docx_cv = setup_user_profile.read_docx_cv
    original_read_pdf_cv = setup_user_profile.read_pdf_cv
    project_root = Path(project_root)

    try:
        patch_mandatory_question_totals(setup_user_profile)
        patch_optional_questions(setup_user_profile)
        setup_user_profile.collect_profile_answers = (
            lambda input_func=input: collect_profile_answers(setup_user_profile, input_func=input_func)
        )
        setup_user_profile.build_cv_markdown = (
            lambda parsed, answers: build_cv_markdown(setup_user_profile, parsed, answers)
        )
        setup_user_profile.parse_cv_text = lambda text: parse_cv_text(setup_user_profile, text)
        setup_user_profile.read_docx_cv = lambda path: read_docx_cv(setup_user_profile, path)
        setup_user_profile.read_pdf_cv = lambda path: read_pdf_cv(setup_user_profile, path)
        resume_result = setup_user_profile.resume_from_existing_drafts(project_root, app_root, input_func=input_func)
        if resume_result is not None:
            return resume_result

        while True:
            cv_text = setup_user_profile.read_cv_interactively(input_func=input_func)
            parsed = setup_user_profile.parse_cv_text(cv_text)
            parsed = setup_user_profile.handle_missing_work_experience(parsed, input_func=input_func)
            cv_path = setup_user_profile.write_cv_draft(app_root, parsed)
            answers, raw_user_input = setup_user_profile.collect_profile_answers(input_func=input_func)
            cv_path.write_text(setup_user_profile.build_cv_markdown(parsed, answers), encoding="utf-8")
            action, parsed = approve_cv_draft_after_questionnaire(setup_user_profile, cv_path, parsed, input_func=input_func)
            if action == "continue":
                break
            if action == "exit":
                print("Setup exited before final review. Draft cv.md remains for review.")
                return False

        print("\nNext, I will create review drafts. Your final files will not be changed yet.")
        draft_paths = setup_user_profile.write_profile_drafts(app_root, parsed, answers, raw_user_input)
        print("\nDraft files created:")
        print(f"- {draft_paths.cv}")
        print(f"- {draft_paths.profile}")
        print(f"- {draft_paths.mode_profile}")
        print("You already reviewed cv.md. You can review the profile drafts first.")
        setup_user_profile.print_hint("Type Y for yes or N for no, then press Enter.")
        if input_func("Do you want to open the profile drafts for final review? [Y/n]: ").strip().lower() in {"", "y", "yes"}:
            setup_user_profile.open_files_for_review([draft_paths.profile, draft_paths.mode_profile])
        return setup_user_profile.approve_final_draft_files(project_root, draft_paths, input_func=input_func)
    finally:
        setup_user_profile.MANDATORY_QUESTIONS = original_mandatory_questions
        setup_user_profile.OPTIONAL_QUESTIONS = original_optional_questions
        setup_user_profile.collect_profile_answers = original_collect_profile_answers
        setup_user_profile.build_cv_markdown = original_build_cv_markdown
        setup_user_profile.parse_cv_text = original_parse_cv_text
        setup_user_profile.read_docx_cv = original_read_docx_cv
        setup_user_profile.read_pdf_cv = original_read_pdf_cv


def install_run_py_profile_setup(first_time_setup_module, project_root, app_root):
    current_runner = first_time_setup_module.run_profile_setup
    runner_type_module = type(current_runner).__module__
    if runner_type_module.startswith("unittest.mock"):
        return
    is_original_runner = getattr(current_runner, "__module__", "") == "first_time_setup"
    is_run_py_runner = bool(getattr(current_runner, "_run_py_profile_setup_wrapper", False))
    if not is_original_runner and not is_run_py_runner:
        return

    def run_profile_setup_from_run_py(paths, input_func=input):
        return run_profile_setup(project_root, app_root, input_func=input_func)

    run_profile_setup_from_run_py._run_py_profile_setup_wrapper = True
    first_time_setup_module.run_profile_setup = run_profile_setup_from_run_py


def main(argv=None, input_func=input):
    argv = list(sys.argv[1:] if argv is None else argv)
    project_root = Path(__file__).resolve().parent

    if any(arg in {"-h", "--help"} for arg in argv):
        print("AI Career Agent launcher")
        print("")
        print("Usage:")
        for command in command_guidance():
            print(f"  {command}")
        print("")
        print("Options:")
        print("  -h, --help      Show this help message")
        print("  --reset-setup   Delete only data/gmail-agent/setup_state.json")
        return 0

    if "--reset-setup" in argv:
        return 0 if reset_setup_state(project_root, input_func=input_func) else 1

    if not is_python_supported():
        print_python_guidance()
        return 1

    python_path = ensure_venv(project_root, input_func=input_func)
    app_root = project_root / "apps" / "gmail-agent"
    first_time_setup = load_first_time_setup(app_root)
    install_run_py_profile_setup(first_time_setup, project_root, app_root)
    readiness = check_sections_a_to_f(
        project_root,
        python_path=python_path,
        first_time_setup_module=first_time_setup,
    )
    if critical_missing_items(readiness):
        print_readiness_summary(readiness)
        return 1

    if not is_section_g_complete(project_root):
        paths = first_time_setup.get_setup_paths(project_root=project_root, app_root=app_root)
        if any(not check.get("ready") for check in readiness):
            print_readiness_summary(readiness)
            print("")
        print("Starting Section G CV/profile setup...")
        ok = first_time_setup.run_profile_setup(paths, input_func=input_func)
        results = first_time_setup.validate_setup(paths)
        state = first_time_setup.state_from_validation(results)
        first_time_setup.save_setup_state(paths, state)
        return 0 if ok else 1

    paths = first_time_setup.get_setup_paths(project_root=project_root, app_root=app_root)
    if not is_startup_setup_complete(project_root):
        results = first_time_setup.validate_setup(paths)
        state = first_time_setup.state_from_validation(results)
        first_time_setup.save_setup_state(paths, state)

    if not is_startup_setup_complete(project_root):
        print("CV/profile setup is complete.")
        print("")
        print("AI setup is required before AI-Career Agent can evaluate jobs.")
        print("")
        print("Please update .env file with one provider name, one API key, and three models from the same provider:")
        print("")
        print("AI_PROVIDER_NAME=")
        print("AI_API_KEY=")
        print("")
        print("")
        print("PRIMARY_MODEL=")
        print("FALLBACK_MODEL=")
        print("SECOND_FALLBACK_MODEL=")
        print("")
        print("Then run:")
        print(r".\.venv\Scripts\python.exe run.py")
        return 1

    print("First-time setup already completed. Starting AI Career Agent...")
    main_script = app_root / "main.py"
    return run_python(python_path, main_script).returncode


if __name__ == "__main__":
    raise SystemExit(main())

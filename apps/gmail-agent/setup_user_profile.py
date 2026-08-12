import os
import platform
import re
import shutil
import subprocess
import sys
from importlib import import_module
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


MANDATORY_QUESTIONS = (
    {
        "key": "target_roles",
        "question": "Question 1 of 9: What job roles are you targeting?",
        "why": "Why: The tool uses this to score whether a job matches your goals.",
        "hint": "Type roles separated by commas, for example: Strategy Manager, PMO Manager, Program Manager.",
    },
    {
        "key": "target_locations",
        "question": "Question 2 of 9: Which countries or cities are you targeting?",
        "hint": "Type countries or cities separated by commas, for example: New York, Australia, Mumbai.",
    },
    {
        "key": "work_preference",
        "question": "Question 3 of 9: What work mode do you prefer?",
        "choices": ("Onsite", "Remote", "Hybrid"),
        "hint": "Type one option number, for example: 1.",
    },
    {
        "key": "relocation_preference",
        "question": "Question 4 of 9: Are you open to relocation?",
        "choices": ("Yes", "No", "Case by case"),
        "hint": "Type one option number, for example: 1.",
    },
    {
        "key": "expected_salary",
        "question": "Question 5 of 9: What salary range are you targeting?",
        "hint": "Include currency and period, for example: USD 15,000/month or INR 20,00,000/year.",
    },
    {
        "key": "contract_preference",
        "question": "Question 6 of 9: What employment type do you prefer?",
        "choices": ("Permanent only", "Contract only", "Open to both"),
        "hint": "Type one option number, for example: 1.",
    },
    {
        "key": "availability",
        "question": "Question 7 of 9: What is your notice period or availability?",
        "choices": ("Immediate", "30 days", "60 days", "90 days"),
        "choice_numbers": ("1", "2", "3", "5"),
        "choice_intro": "Choose or type:",
        "hint": "Type one option number, for example: 1, or type your own answer such as 45 days.",
    },
    {
        "key": "max_job_alerts_to_process",
        "question": "Question 8 of 9: How many job alerts should each scan process?",
        "hint": "Type a whole number, for example: 5. Default: 5.",
    },
    {
        "key": "max_job_links_to_process",
        "question": "Question 9 of 9: How many job links should each scan process?",
        "hint": "Type a whole number, for example: 50. Default recommendation: 50.",
    },
)

OPTIONAL_QUESTIONS = (
    ("preferred_industries", "Preferred industries", "Example: Consulting, technology, government transformation"),
    ("industries_to_avoid", "Industries to avoid", "Example: Crypto, gambling, tobacco"),
    ("roles_to_avoid", "Roles to avoid", "Example: Pure sales roles, junior analyst roles"),
    ("preferred_company", "Preferred company size/stage/culture", "Example: Established companies with mature program teams"),
    ("reporting_line", "Reporting line preference", "Example: Reporting to COO, Strategy Director, or Transformation VP"),
    ("leadership_preference", "Leadership preference", "Example: Individual contributor now, people leadership later"),
    ("travel_willingness", "Travel willingness", "Example: Up to 25% travel"),
    ("visa_notes", "Visa/work authorization notes", "Example: Saudi transferable Iqama, UAE work authorization needed"),
    ("languages", "Languages", "Example: English, Arabic"),
    ("certifications", "Certifications", "Example: PMP, Scrum Master, Lean Six Sigma"),
    ("portfolio_links", "Portfolio/demo links", "Example: LinkedIn featured posts, portfolio URL"),
    ("extra_achievements", "Achievements not visible in CV", "Example: Led a turnaround program that saved SAR 2M"),
    ("extra_tools", "Tools/platforms not visible in CV", "Example: Jira, Power BI, SAP, Salesforce"),
    ("management_experience", "Management/team-size experience", "Example: Managed 6 direct reports and 20 project contributors"),
    ("domain_expertise", "Domain expertise", "Example: Healthcare operations, fintech, public sector"),
    ("salary_flexibility", "Salary flexibility", "Example: Flexible for equity or strong leadership scope"),
    ("deal_breakers", "Deal breakers", "Example: No unpaid take-home assignments, no 6-day work week"),
    ("preferred_sources", "Preferred job alert sources", "Example: LinkedIn, Bayt, company career pages"),
)

IMPORTANT_OPTIONAL_KEYS = {
    "preferred_industries",
    "industries_to_avoid",
    "roles_to_avoid",
    "visa_notes",
    "extra_achievements",
    "extra_tools",
    "deal_breakers",
    "preferred_sources",
}

SUPPORTED_CV_EXTENSIONS = {".md", ".txt", ".docx", ".pdf"}
MIN_EXTRACTED_PDF_CHARS = 40
CV_EXTRACTION_PACKAGES = ("python-docx", "pypdf")

JARGON_MAPPINGS = {
    "PM": "Product Manager",
    "SWE": "Software Engineer",
    "FE": "Frontend Engineer",
    "BE": "Backend Engineer",
    "QA": "Quality Assurance",
    "BA": "Business Analyst",
    "UAE": "United Arab Emirates",
    "USA": "United States",
    "UK": "United Kingdom",
    "KSA": "Saudi Arabia",
}


@dataclass
class DraftPaths:
    drafts_dir: Path
    cv: Path
    profile: Path
    mode_profile: Path


def split_list(value):
    return [item.strip() for item in re.split(r"[,;\n]+", value or "") if item.strip()]


def clean_path_input(value):
    return str(value or "").strip().strip("\"'")


def supported_cv_formats_text():
    return ".txt, .md, .docx, .pdf"


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


def detect_os():
    return platform.system()


def venv_python_path(system_name=None):
    system_name = system_name or detect_os()
    if system_name == "Windows":
        return r".venv\Scripts\python.exe"
    return ".venv/bin/python"


def package_install_command(system_name=None, packages=CV_EXTRACTION_PACKAGES):
    python_path = venv_python_path(system_name)
    prefix = ".\\" if str(python_path).startswith(".venv\\") else "./"
    return f"{prefix}{python_path} -m pip install {' '.join(packages)}"


def python_install_guidance(system_name=None, homebrew_exists=None):
    system_name = system_name or detect_os()
    if system_name == "Windows":
        return [
            "Preferred command:",
            "winget install Python.Python.3.12",
            "After install, reopen PowerShell and run:",
            "py run.py",
            "or",
            "python run.py",
        ]
    if system_name == "Darwin":
        if homebrew_exists is None:
            homebrew_exists = shutil.which("brew") is not None
        if homebrew_exists:
            return [
                "Preferred command:",
                "brew install python@3.12",
                "After install, reopen Terminal and run:",
                "python3 run.py",
            ]
        return [
            "Install Python from https://www.python.org/downloads/macos/",
            "or install Homebrew first.",
            "After install, reopen Terminal and run:",
            "python3 run.py",
        ]
    return [
        "Ubuntu/Debian guidance:",
        "sudo apt update",
        "sudo apt install python3 python3-venv python3-pip",
        "Then run:",
        "python3 run.py",
    ]


def print_python_install_guidance(system_name=None):
    for line in python_install_guidance(system_name):
        print(line)


def create_venv_command(system_name=None):
    system_name = system_name or detect_os()
    if system_name == "Windows":
        return "py -m venv .venv"
    return "python3 -m venv .venv"


def install_cv_dependencies(project_root=None, input_func=input, run_func=subprocess.run, system_name=None):
    project_root = Path(project_root or Path(__file__).resolve().parents[2])
    venv_path = project_root / ".venv"
    if not venv_path.exists():
        command = create_venv_command(system_name)
        print(".venv is missing.")
        print("Create it first with:")
        print(command)
        print_hint("Type Y for yes or N for no, then press Enter.")
        if input_func("Create .venv now? [y/N]: ").strip().lower() in {"y", "yes"}:
            run_func(command, shell=True, cwd=str(project_root), check=False)
        else:
            print("Manual setup:")
            print(command)
            return False
    command = package_install_command(system_name)
    print("Install CV file reading packages with:")
    print(command)
    print_hint("Type Y for yes or N for no, then press Enter.")
    if input_func("Install packages now? [y/N]: ").strip().lower() in {"y", "yes"}:
        run_func(command, shell=True, cwd=str(project_root), check=False)
        return True
    print("Manual setup:")
    print(command)
    return False


def print_missing_dependency(package_name, system_name=None):
    print(f"Missing dependency: {package_name}")
    print("Install it with:")
    print(package_install_command(system_name))


def read_text_cv(path):
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def read_docx_cv(path):
    try:
        docx = import_module("docx")
    except ImportError:
        print_missing_dependency("python-docx")
        return None
    print("Reading Word CV...")
    document = docx.Document(str(path))
    chunks = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            chunks.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = []
            for cell in row.cells:
                cell_text = "\n".join(
                    paragraph.text.strip()
                    for paragraph in cell.paragraphs
                    if paragraph.text.strip()
                )
                if cell_text:
                    cells.append(cell_text)
            if cells:
                chunks.append(" | ".join(cells))
    text = "\n".join(chunks).strip()
    if text:
        print("Text extracted successfully.")
    return text


def read_pdf_cv(path):
    try:
        pypdf = import_module("pypdf")
    except ImportError:
        print_missing_dependency("pypdf")
        return None
    print("Reading PDF CV...")
    reader = pypdf.PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n".join(page.strip() for page in pages if page.strip()).strip()
    if len(text) < MIN_EXTRACTED_PDF_CHARS:
        print("This PDF may be scanned or image-based. Please provide a Word/.docx version or paste the CV text.")
        return None
    print("Text extracted successfully.")
    return text


def read_cv_file(path):
    path = Path(path)
    extension = path.suffix.lower()
    if extension in {".txt", ".md"}:
        return read_text_cv(path)
    if extension == ".docx":
        return read_docx_cv(path)
    if extension == ".pdf":
        return read_pdf_cv(path)
    print(f"Unsupported CV file type. Supported formats: {supported_cv_formats_text()}")
    return None


def normalize_choice(raw, choices, choice_numbers=None):
    value = str(raw or "").strip()
    if choice_numbers:
        choice_map = {str(number): choice for number, choice in zip(choice_numbers, choices)}
        if value in choice_map:
            return choice_map[value]
    if value.isdigit():
        index = int(value) - 1
        if 0 <= index < len(choices):
            return choices[index]
    return value


def prompt_positive_integer(raw, field, default_value, input_func=input):
    value = str(raw or "").strip()
    if not value:
        return str(default_value)
    while not re.fullmatch(r"[1-9]\d*", value):
        print("Please enter a whole number greater than zero.")
        print_hint("Type digits only, for example: 25.")
        value = input_func("Answer: ").strip()
        if not value:
            value = str(default_value)
    return value


def normalize_work_preference(value):
    normalized = re.sub(r"[^a-z]+", " ", str(value or "").lower()).strip()
    if normalized in {"1", "remote"} or "remote" in normalized:
        return "remote"
    if normalized in {"2", "hybrid"} or "hybrid" in normalized:
        return "hybrid"
    if normalized in {"3", "onsite", "on site", "office"} or any(
        token in normalized for token in ("onsite", "on site", "office")
    ):
        return "onsite"
    if normalized in {"4", "flexible"} or "flexible" in normalized:
        return "flexible"
    return str(value or "").strip().lower()


def yaml_quote(value):
    text = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def markdown_list(items):
    if not items:
        return "- Not provided"
    return "\n".join(f"- {item}" for item in items)


def first_nonempty_line(text):
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and "@" not in stripped and not stripped.startswith(("http://", "https://")):
            if len(stripped.split()) <= 6 and not stripped.endswith(":"):
                return stripped
    return ""


def extract_section(text, names):
    lines = text.splitlines()
    start = None
    section_pattern = re.compile(r"^\s{0,3}#{0,3}\s*([A-Za-z][A-Za-z /&+-]{1,40})\s*:?\s*$")
    wanted = {name.lower() for name in names}
    for index, line in enumerate(lines):
        normalized = line.strip().strip("#").strip(":").lower()
        if normalized in wanted:
            start = index + 1
            break
    if start is None:
        return ""
    collected = []
    for line in lines[start:]:
        match = section_pattern.match(line)
        if match and match.group(1).strip().lower() not in wanted:
            break
        collected.append(line.rstrip())
    return "\n".join(collected).strip()


def parse_cv_text(text):
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
    urls = re.findall(r"https?://[^\s)>\]]+", text)
    linkedin = next((url for url in urls if "linkedin.com" in url.lower()), "")
    github = next((url for url in urls if "github.com" in url.lower()), "")
    portfolio = next((url for url in urls if url not in {linkedin, github}), "")
    location = ""
    for line in text.splitlines()[:12]:
        if re.search(r"\b(location|based in|address)\b", line, re.I):
            location = re.sub(r"(?i)location|based in|address|:", "", line).strip(" -")
            break
    return {
        "full_name": first_nonempty_line(text),
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0).strip() if phone_match else "",
        "location": location,
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio,
        "professional_summary": extract_section(text, ("summary", "profile", "professional summary")),
        "skills": split_list(extract_section(text, ("skills", "technical skills"))),
        "work_experience": extract_section(text, ("experience", "work experience", "employment")),
        "projects": extract_section(text, ("projects", "selected projects")),
        "education": extract_section(text, ("education",)),
        "certifications": split_list(extract_section(text, ("certifications", "certificates"))),
        "languages": split_list(extract_section(text, ("languages",))),
        "raw_text": text,
    }


def apply_jargon_mappings(value):
    result = value or ""
    for raw, replacement in JARGON_MAPPINGS.items():
        result = re.sub(rf"\b{re.escape(raw)}\b", replacement, result)
    return result


def approve_normalized_value(field, raw_value, input_func=input):
    suggested = apply_jargon_mappings(raw_value)
    if suggested == raw_value:
        return raw_value
    print(f"\nSuggested wording for {field}:")
    print(f"Raw: {raw_value}")
    print(f"Suggested: {suggested}")
    print_hint("Type your answer in plain English, then press Enter.")
    answer = input_func("Accept, Edit, or Keep original? [A/e/k]: ").strip().lower() or "a"
    if answer.startswith("e"):
        print_hint("Type your answer in plain English, then press Enter.")
        return input_func("Enter edited wording: ").strip()
    if answer.startswith("k"):
        return raw_value
    return suggested


def build_cv_markdown(parsed, answers):
    target_roles = split_list(answers.get("target_roles", ""))
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
        markdown_list(target_roles),
        "",
        "## Professional Summary",
        summary,
        "",
        "## Skills",
        markdown_list(parsed.get("skills", [])),
        "",
        "## Work Experience",
        parsed.get("work_experience") or "Not provided",
        "",
        "## Projects",
        parsed.get("projects") or answers.get("portfolio_links") or "Not provided",
        "",
        "## Education",
        parsed.get("education") or "Not provided",
        "",
        "## Certifications",
        markdown_list(parsed.get("certifications", []) or split_list(answers.get("certifications", ""))),
        "",
        "## Languages",
        markdown_list(parsed.get("languages", []) or split_list(answers.get("languages", ""))),
        "",
    ]
    return "\n".join(lines)


def build_profile_yml(parsed, answers, raw_user_input):
    target_roles = split_list(answers.get("target_roles", ""))
    target_locations = split_list(answers.get("target_locations", ""))
    primary_location = target_locations[0] if target_locations else parsed.get("location", "")
    lines = [
        "# Career-Ops Profile Configuration",
        "# Generated by first-time setup. Review and edit as your goals change.",
        "",
        "candidate:",
        f"  full_name: {yaml_quote(parsed.get('full_name'))}",
        f"  email: {yaml_quote(parsed.get('email'))}",
        f"  phone: {yaml_quote(parsed.get('phone'))}",
        f"  location: {yaml_quote(primary_location)}",
        f"  linkedin: {yaml_quote(parsed.get('linkedin'))}",
        f"  portfolio_url: {yaml_quote(parsed.get('portfolio') or answers.get('portfolio_links', ''))}",
        f"  github: {yaml_quote(parsed.get('github'))}",
        "",
        "target_roles:",
        "  primary:",
    ]
    lines.extend(f"    - {yaml_quote(role)}" for role in (target_roles or ["Not provided"]))
    lines.extend([
        "  archetypes:",
    ])
    lines.extend(
        [
            f"    - name: {yaml_quote(role)}",
            "      level: \"Target\"",
            "      fit: \"primary\"",
        ]
        for role in (target_roles or ["Not provided"])
    )
    lines.extend([
        "",
        "work_preference:",
        f"  arrangement: {yaml_quote(normalize_work_preference(answers.get('work_preference')))}",
        f"  relocation: {yaml_quote(answers.get('relocation_preference'))}",
        f"  contract_type: {yaml_quote(answers.get('contract_preference'))}",
        f"  availability: {yaml_quote(answers.get('availability'))}",
        "",
        "compensation:",
        f"  target_range: {yaml_quote(answers.get('expected_salary'))}",
        f"  flexibility: {yaml_quote(answers.get('salary_flexibility', ''))}",
        "",
        "location:",
        f"  preferred: {yaml_quote(', '.join(target_locations))}",
        f"  visa_status: {yaml_quote(answers.get('visa_notes', ''))}",
        "",
        "narrative:",
        f"  headline: {yaml_quote(answers.get('career_direction'))}",
        f"  preferred_industries: {yaml_quote(answers.get('preferred_industries', ''))}",
        f"  industries_to_avoid: {yaml_quote(answers.get('industries_to_avoid', ''))}",
        f"  roles_to_avoid: {yaml_quote(answers.get('roles_to_avoid', ''))}",
        f"  deal_breakers: {yaml_quote(answers.get('deal_breakers', ''))}",
        f"  domain_expertise: {yaml_quote(answers.get('domain_expertise', ''))}",
        "",
        "raw_user_input:",
    ])
    for key, value in raw_user_input.items():
        lines.append(f"  {key}: {yaml_quote(value)}")
    lines.extend([
        "",
        "gmail_scan:",
        f"  max_job_alerts_to_process: {answers.get('max_job_alerts_to_process') or 5}",
        f"  max_job_links_to_process: {answers.get('max_job_links_to_process') or 50}",
        "",
        "cv:",
        "  output_format: \"html\"",
        "",
    ])
    flattened = []
    for item in lines:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)
    return "\n".join(flattened)


def build_mode_profile_md(answers):
    target_roles = split_list(answers.get("target_roles", ""))
    lines = [
        "# User Profile Context -- AI-Career Agent",
        "",
        "## Your Target Roles",
        "",
        markdown_list(target_roles),
        "",
        "## Your Adaptive Framing",
        "",
        answers.get("career_direction") or "Use the candidate profile and CV to adapt framing to each role.",
        "",
        "## Your Location Policy",
        "",
        f"- Target locations: {answers.get('target_locations') or 'Not provided'}",
        f"- Work preference: {answers.get('work_preference') or 'Not provided'}",
        f"- Relocation: {answers.get('relocation_preference') or 'Not provided'}",
        "",
        "## Your Comp Targets",
        "",
        f"- Expected salary: {answers.get('expected_salary') or 'Not provided'}",
        f"- Flexibility: {answers.get('salary_flexibility') or 'Not provided'}",
        "",
        "## Deal Breakers",
        "",
        answers.get("deal_breakers") or "Not provided",
        "",
    ]
    return "\n".join(lines)


def get_draft_paths(app_root):
    project_root = Path(app_root).resolve().parent.parent
    drafts_dir = project_root / "data" / "gmail-agent" / "setup_drafts"
    return DraftPaths(
        drafts_dir=drafts_dir,
        cv=drafts_dir / "cv.md",
        profile=drafts_dir / "profile.yml",
        mode_profile=drafts_dir / "_profile.md",
    )


def draft_paths_are_complete(draft_paths):
    return all(
        path.exists() and path.stat().st_size > 0
        for path in (draft_paths.cv, draft_paths.profile, draft_paths.mode_profile)
    )


def write_drafts(project_root, app_root, parsed, answers, raw_user_input):
    draft_paths = get_draft_paths(app_root)
    draft_paths.drafts_dir.mkdir(parents=True, exist_ok=True)
    draft_paths.cv.write_text(build_cv_markdown(parsed, answers), encoding="utf-8")
    draft_paths.profile.write_text(build_profile_yml(parsed, answers, raw_user_input), encoding="utf-8")
    draft_paths.mode_profile.write_text(build_mode_profile_md(answers), encoding="utf-8")
    return draft_paths


def write_cv_draft(app_root, parsed):
    draft_paths = get_draft_paths(app_root)
    draft_paths.drafts_dir.mkdir(parents=True, exist_ok=True)
    draft_paths.cv.write_text(build_cv_markdown(parsed, {}), encoding="utf-8")
    return draft_paths.cv


def write_profile_drafts(app_root, parsed, answers, raw_user_input):
    draft_paths = get_draft_paths(app_root)
    draft_paths.drafts_dir.mkdir(parents=True, exist_ok=True)
    draft_paths.profile.write_text(build_profile_yml(parsed, answers, raw_user_input), encoding="utf-8")
    draft_paths.mode_profile.write_text(build_mode_profile_md(answers), encoding="utf-8")
    return draft_paths


def available_editor():
    code = shutil.which("code")
    if code:
        return code
    if shutil.which("notepad"):
        return "notepad"
    return None


def open_files_for_review(files, popen_func=subprocess.Popen):
    editor = available_editor()
    if not editor:
        print("No VS Code or Notepad command was found. Review the draft files manually.")
        return False
    for file_path in files:
        popen_func([editor, str(file_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def open_path_default(path, system_name=None, startfile_func=None, run_func=subprocess.run):
    path = Path(path)
    system_name = system_name or detect_os()
    try:
        if system_name == "Windows":
            editor = available_editor()
            if editor:
                subprocess.Popen([editor, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            startfile = startfile_func or os.startfile
            startfile(str(path))
        elif system_name == "Darwin":
            run_func(["open", str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            run_func(["xdg-open", str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (AttributeError, OSError, subprocess.SubprocessError) as exc:
        print(f"Could not open cv.md automatically: {exc}")
        print(path)
        return False


def backup_existing(path, timestamp):
    path = Path(path)
    if not path.exists():
        return None
    if path.name == "cv.md":
        backup_name = f"cv.backup.{timestamp}.md"
    elif path.name == "profile.yml":
        backup_name = f"profile.backup.{timestamp}.yml"
    elif path.name == "_profile.md":
        backup_name = f"_profile.backup.{timestamp}.md"
    else:
        backup_name = f"{path.stem}.backup.{timestamp}{path.suffix}"
    backup_path = path.with_name(backup_name)
    shutil.copyfile(path, backup_path)
    return backup_path


def write_final_files(project_root, draft_paths, timestamp=None):
    project_root = Path(project_root)
    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    targets = {
        draft_paths.cv: project_root / "cv.md",
        draft_paths.profile: project_root / "config" / "profile.yml",
        draft_paths.mode_profile: project_root / "modes" / "_profile.md",
    }
    backups = []
    for target in targets.values():
        target.parent.mkdir(parents=True, exist_ok=True)
        backup = backup_existing(target, timestamp)
        if backup:
            backups.append(backup)
    for draft, target in targets.items():
        shutil.copyfile(draft, target)
    return backups


def approve_final_draft_files(project_root, draft_paths, input_func=input):
    project_root = Path(project_root)
    print("\nApprove writing final files?")
    print("This will update:")
    print(f"- {project_root / 'cv.md'}")
    print(f"- {project_root / 'config' / 'profile.yml'}")
    print(f"- {project_root / 'modes' / '_profile.md'}")
    print("")
    print("Existing files will be backed up first.")
    print_hint("Type Y for yes or N for no, then press Enter.")
    if input_func("Approve writing final files now? [y/N]: ").strip().lower() in {"y", "yes"}:
        backups = write_final_files(project_root, draft_paths)
        if backups:
            print("Backups created:")
            for backup in backups:
                print(backup)
        print("Final CV/profile files written.")
        return True
    print("Final files were not modified. Drafts remain in setup_drafts.")
    print("Run python run.py again to resume from saved drafts.")
    return False


def resume_from_existing_drafts(project_root, app_root, input_func=input):
    draft_paths = get_draft_paths(app_root)
    if not draft_paths_are_complete(draft_paths):
        return None

    print("Existing setup drafts found:")
    print(f"- {draft_paths.cv}")
    print(f"- {draft_paths.profile}")
    print(f"- {draft_paths.mode_profile}")
    print_hint("Type Y to resume from these drafts, or N to restart setup.")
    if input_func("Resume from saved drafts? [Y/n]: ").strip().lower() not in {"", "y", "yes"}:
        return None

    print_hint("Type Y for yes or N for no, then press Enter.")
    if input_func("Do you want to open the saved drafts for review? [Y/n]: ").strip().lower() in {"", "y", "yes"}:
        open_files_for_review([draft_paths.cv, draft_paths.profile, draft_paths.mode_profile])
    return approve_final_draft_files(project_root, draft_paths, input_func=input_func)


def read_pasted_cv(input_func=input):
    print("Paste plain-text CV. End with a single line containing END.")
    print_hint("Paste the text, then finish using the tool's displayed instruction.")
    lines = []
    while True:
        line = input_func("")
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def read_cv_interactively(input_func=input):
    print("Provide your CV as a file path or paste plain text.")
    print_hint("Type P to paste your CV, or paste a .txt/.md/.docx/.pdf file path.")
    print_hint("Paste the full file path. Quotes are okay. Example: D:\\Resume\\John_Doe_CV.txt")
    choice = clean_path_input(input_func("Type P to paste, or enter a CV file path: "))
    while choice:
        if choice.lower() == "p":
            return read_pasted_cv(input_func=input_func)
        path = Path(choice).expanduser()
        if path.exists():
            text = read_cv_file(path)
            if text:
                return text
            print("1. Enter another file path")
            print("2. Paste CV text now")
            print("3. Skip CV setup")
            print_hint("Type one option number, for example 1, then press Enter.")
            next_step = input_func("Answer: ").strip()
            if next_step == "2":
                return read_pasted_cv(input_func=input_func)
            if next_step == "3":
                return ""
            print_hint("Paste the full file path. Quotes are okay. Example: D:\\Resume\\John_Doe_CV.txt")
            choice = clean_path_input(input_func("Enter another CV file path: "))
            continue
        print("File not found. Please check the path and try again.")
        print("1. Enter another file path")
        print("2. Paste CV text now")
        print("3. Skip CV setup")
        print_hint("Type one option number, for example 1, then press Enter.")
        next_step = input_func("Answer: ").strip()
        if next_step == "2":
            return read_pasted_cv(input_func=input_func)
        if next_step == "3":
            return ""
        print_hint("Paste the full file path. Quotes are okay. Example: D:\\Resume\\John_Doe_CV.txt")
        choice = clean_path_input(input_func("Enter another CV file path: "))
    return ""


def handle_missing_work_experience(parsed, input_func=input):
    while not str(parsed.get("work_experience", "")).strip():
        print("Work Experience was not detected. This will reduce job scoring quality.")
        print("1. Paste work experience now")
        print("2. Provide another CV file")
        print("3. Continue anyway")
        print_hint("Type one option number, for example 1, then press Enter.")
        choice = input_func("Answer: ").strip()
        if choice == "1":
            print("Paste work experience.")
            print_hint("Paste the text and press Enter, then type END and press Enter.")
            lines = []
            while True:
                line = input_func("")
                if line.strip() == "END":
                    break
                lines.append(line)
            work_experience = "\n".join(lines).strip()
            parsed["work_experience"] = work_experience
            parsed["raw_text"] = "\n\n".join(
                part for part in (parsed.get("raw_text", ""), "Experience", work_experience) if part
            )
            return parsed
        if choice == "2":
            cv_text = read_cv_interactively(input_func=input_func)
            parsed = parse_cv_text(cv_text)
            continue
        if choice == "3":
            parsed["_work_experience_continue_anyway"] = True
            return parsed
        print("Please choose 1, 2, or 3.")
    return parsed


def cv_has_missing_work_experience_marker(text):
    return bool(re.search(r"(?is)##\s*Work Experience\s*\n\s*Not provided\b", text or ""))


def approve_cv_draft(cv_path, parsed, input_func=input, open_func=open_path_default):
    cv_path = Path(cv_path).resolve()
    print("\nCV draft created successfully.")
    print("")
    print("Please review this file before continuing:")
    print(cv_path)
    print("")
    print("This file is important because it becomes the source for job scoring.")
    print_hint("Type Y for yes or N for no, then press Enter.")
    if input_func("Open cv.md now for review? [Y/n]: ").strip().lower() in {"", "y", "yes"}:
        try:
            open_func(cv_path)
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"Could not open cv.md automatically: {exc}")
            print(cv_path)

    while True:
        print("")
        print("After reviewing cv.md, choose:")
        print("1. Approve and continue to career preferences")
        print("2. I edited cv.md and want to continue")
        print("3. Provide another CV file")
        print("4. Exit setup for now")
        print_hint("Type one option number, for example: 1.")
        choice = input_func("Answer: ").strip()
        if choice in {"1", "2"}:
            cv_text = cv_path.read_text(encoding="utf-8", errors="ignore")
            if (
                cv_has_missing_work_experience_marker(cv_text)
                and not parsed.get("_work_experience_continue_anyway")
            ):
                print("Work Experience is still marked as Not provided in cv.md.")
                print_hint("Type Y only if you explicitly want to continue anyway.")
                if input_func("Continue anyway? [y/N]: ").strip().lower() not in {"y", "yes"}:
                    continue
                parsed["_work_experience_continue_anyway"] = True
            if choice == "2":
                parsed = parse_cv_text(cv_text)
            return "continue", parsed
        if choice == "3":
            return "retry", parsed
        if choice == "4":
            return "exit", parsed
        print("Please choose 1, 2, 3, or 4.")


def collect_profile_answers(input_func=input):
    answers = {}
    raw_user_input = {}
    print("\nNow I need a few career preferences that are usually not clear from the CV.")
    print("These are required because they affect job scoring.")
    for item in MANDATORY_QUESTIONS:
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
        print_hint(item["hint"])
        raw = input_func("Answer: ").strip()
        raw = normalize_choice(raw, choices, item.get("choice_numbers")) if choices else raw
        if key == "max_job_alerts_to_process":
            raw = prompt_positive_integer(raw, key, 5, input_func=input_func)
        if key == "max_job_links_to_process":
            raw = prompt_positive_integer(raw, key, 50, input_func=input_func)
        raw_user_input[key] = raw
        value = raw if key in {"max_job_alerts_to_process", "max_job_links_to_process"} else approve_normalized_value(key, raw, input_func=input_func)
        answers[key] = normalize_work_preference(value) if key == "work_preference" else value

    print("\nOptional questions can improve scoring and recommendations, but you can skip them.")
    print("Choose:")
    print("1. Skip all optional questions")
    print("2. Answer important optional questions only")
    print("3. Answer all optional questions")
    print_hint("Type one option number, for example 1, then press Enter.")
    optional_mode = input_func("Answer: ").strip() or "1"
    if optional_mode in {"2", "3"}:
        questions = OPTIONAL_QUESTIONS
        if optional_mode == "2":
            questions = tuple(item for item in OPTIONAL_QUESTIONS if item[0] in IMPORTANT_OPTIONAL_KEYS)
        for key, label, example in questions:
            print("")
            print(f"{label} (optional)")
            print(example)
            print("Press Enter to skip.")
            print_hint("Press Enter to skip this optional question.")
            raw = input_func("Answer: ").strip()
            raw_user_input[key] = raw
            answers[key] = approve_normalized_value(key, raw, input_func=input_func) if raw else ""
    return answers, raw_user_input


def run_profile_setup(project_root, app_root, input_func=input):
    project_root = Path(project_root)
    app_root = Path(app_root)
    resume_result = resume_from_existing_drafts(project_root, app_root, input_func=input_func)
    if resume_result is not None:
        return resume_result

    while True:
        cv_text = read_cv_interactively(input_func=input_func)
        parsed = parse_cv_text(cv_text)
        parsed = handle_missing_work_experience(parsed, input_func=input_func)
        cv_path = write_cv_draft(app_root, parsed)
        action, parsed = approve_cv_draft(cv_path, parsed, input_func=input_func)
        if action == "continue":
            break
        if action == "exit":
            print("Setup exited before career preferences. Draft cv.md remains for review.")
            return False
    answers, raw_user_input = collect_profile_answers(input_func=input_func)
    print("\nNext, I will create review drafts. Your final files will not be changed yet.")
    draft_paths = write_profile_drafts(app_root, parsed, answers, raw_user_input)
    print("\nDraft files created:")
    print(f"- {draft_paths.cv}")
    print(f"- {draft_paths.profile}")
    print(f"- {draft_paths.mode_profile}")
    print("You already reviewed cv.md. You can review the profile drafts first.")
    print_hint("Type Y for yes or N for no, then press Enter.")
    if input_func("Do you want to open the profile drafts for final review? [Y/n]: ").strip().lower() in {"", "y", "yes"}:
        open_files_for_review([draft_paths.profile, draft_paths.mode_profile])
    return approve_final_draft_files(project_root, draft_paths, input_func=input_func)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    raise SystemExit(0 if run_profile_setup(here.parent.parent, here) else 1)

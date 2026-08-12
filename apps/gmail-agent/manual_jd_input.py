import re
from datetime import datetime

from career_ops_runner import (
    JD_OUTPUT_FOLDER,
    create_jd_markdown,
    generate_single_executive_report,
    load_processed_state,
    run_career_ops_evaluation,
    save_current_run_reports,
    save_processed_state,
)

MIN_JD_LENGTH = 200
MAX_FILENAME_LENGTH = 120
MAX_SLUG_LENGTH = 60
WINDOWS_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def read_jd_text():
    print("Paste the job description below.")
    print("Type END on a line by itself when finished.")

    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)

    return "\n".join(lines).strip()


def find_labeled_value(text, labels):
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?im)^\s*(?:{label_pattern})\s*[:\-]\s*(.+?)\s*$",
        text,
    )
    return match.group(1).strip() if match else ""


def identify_details(text):
    role = find_labeled_value(
        text,
        ["job title", "position title", "position", "role", "title"],
    )
    company = find_labeled_value(
        text,
        ["company name", "company", "organization", "organisation", "employer"],
    )
    location = find_labeled_value(
        text,
        ["job location", "location", "city"],
    )

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not role and lines:
        first_line = re.sub(r"^(job description|job opening)\s*[:\-]\s*", "", lines[0], flags=re.I)
        if 2 <= len(first_line.split()) <= 15:
            role = first_line

    title_match = re.search(
        r"(?im)^\s*(.+?)\s+(?:at|@)\s+(.+?)(?:\s*[-|]\s*(.+))?\s*$",
        "\n".join(lines[:8]),
    )
    if title_match:
        role = role or title_match.group(1).strip()
        company = company or title_match.group(2).strip()
        location = location or (title_match.group(3) or "").strip()

    return company, role, location


def prompt_if_missing(value, label):
    if value:
        return value
    return input(f"{label}: ").strip()


def safe_filename_slug(value, max_length=MAX_SLUG_LENGTH):
    value = str(value or "").lower()
    value = re.sub(r"['\u2018\u2019\u201a\u201b\u2032\u2035`]", "", value)
    value = re.sub(r'["\u201c\u201d\u201e\u201f\u2033\u2036]', "", value)
    value = re.sub(f"[{re.escape(WINDOWS_INVALID_FILENAME_CHARS)}]", " ", value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:max_length].strip("_")


def build_manual_jd_filename(timestamp, company="", role="", location=""):
    company_slug = safe_filename_slug(company)
    role_slug = safe_filename_slug(role)
    location_slug = safe_filename_slug(location)

    if not company_slug and not role_slug:
        base = f"manual_{timestamp}_job_description"
    else:
        parts = [part for part in (company_slug, role_slug, location_slug) if part]
        detail_slug = "_".join(parts)
        detail_slug = re.sub(r"_+", "_", detail_slug).strip("_")
        max_detail_length = max(
            1,
            MAX_FILENAME_LENGTH - len(f"manual_{timestamp}_.md"),
        )
        detail_slug = detail_slug[:max_detail_length].strip("_")
        base = f"manual_{timestamp}_{detail_slug or 'job_description'}"

    filename = f"{base}.md"
    if len(filename) > MAX_FILENAME_LENGTH:
        filename = f"{base[:MAX_FILENAME_LENGTH - 3].rstrip('_')}.md"
    return filename


def save_manual_jd_file(markdown, filename, output_folder=JD_OUTPUT_FOLDER):
    file_path = output_folder / filename
    try:
        output_folder.mkdir(parents=True, exist_ok=True)
        file_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        print("Could not save the manual job description file.")
        print(f"Reason: {exc}")
        print("Please retry with a shorter company, role, or location.")
        return None
    return file_path


def run_existing_pipeline(file_path):
    result = run_career_ops_evaluation(file_path)
    if result["return_code"] != 0:
        print("Career-Ops evaluation failed.")
        return

    report_match = re.search(r"Report saved:\s*(.+\.md)", result["stdout"])
    report_paths = []
    if report_match:
        report_path = report_match.group(1).strip()
        report_paths.append(report_path)
        generate_single_executive_report(report_path)

    state = load_processed_state()
    evaluated_files = set(state.get("evaluated_jd_files", []))
    evaluated_files.add(file_path.name)
    state["evaluated_jd_files"] = sorted(evaluated_files)
    save_processed_state(state)
    save_current_run_reports(report_paths)


def main():
    jd_text = read_jd_text()
    if len(jd_text) < MIN_JD_LENGTH:
        print(
            f"Error: job description must be at least {MIN_JD_LENGTH} "
            f"characters; received {len(jd_text)}."
        )
        return

    company, role, location = identify_details(jd_text)
    company = prompt_if_missing(company, "Company")
    role = prompt_if_missing(role, "Role")
    location = prompt_if_missing(location, "Location (City)")
    source_url = input("Source URL (optional): ").strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = build_manual_jd_filename(timestamp, company, role, location)
    job = {
        "job_title": role,
        "company": company,
        "location": location,
        "url": source_url,
        "content": jd_text,
        "status": "manual",
        "needs_manual_review": False,
        "source_status": {
            "source": "manual",
            "capture_status": "manual_paste",
            "scrape_status": "manual",
            "login_status": "not_required",
            "jd_quality": "full",
        },
    }
    _, markdown = create_jd_markdown(job, 0)
    file_path = save_manual_jd_file(markdown, filename)
    if not file_path:
        return

    print(file_path.resolve())
    run_existing_pipeline(file_path)


if __name__ == "__main__":
    main()

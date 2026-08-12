import os
import csv
import json
import re
from datetime import datetime
from pathlib import Path

from paths import (
    CAREER_OPS_ROOT,
    CURRENT_RUN_JOBS_FILE,
    CURRENT_RUN_REPORTS_FILE,
    DAILY_REPORTS_DIR,
    JD_FILES_DIR,
    SCRAPED_JOBS_FILE,
)

CAREER_OPS_REPORTS = CAREER_OPS_ROOT / "reports"
DAILY_REPORTS_FOLDER = DAILY_REPORTS_DIR
VALID_RECOMMENDATIONS = {
    "Apply",
    "Consider",
    "Deprioritize",
    "Reject"
}

VALID_FIT_TYPES = {
    "PMO",
    "Strategy",
    "Analytics",
    "Transformation",
    "Finance",
    "Sales",
    "Technical",
    "Other"
}

VALID_SENIORITY_MATCH = {
    "Good",
    "Stretch",
    "Under"
}

LOCATION_KEYS = {
    "location",
    "job_location",
    "job location",
    "work_location",
    "work location",
}

MISSING_LOCATION_VALUES = {
    "",
    "unknown",
    "not mentioned",
    "not available",
    "n/a",
    "na",
    "none",
    "null",
}

WEAK_METADATA_VALUES = {
    "seek",
    "linkedin",
    "indeed",
    "naukri",
    "naukrigulf",
    "glassdoor",
    "bayt",
    "gulftalent",
    "iimjobs",
    "ziprecruiter",
    "foundit",
    "job alert",
    "jobs near you",
    "new jobs",
    "recommended jobs",
}

def extract_metadata_json(text):

    pattern = r"```json\s*([\s\S]*?)\s*```"

    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return {}

    try:
        return json.loads(match.group(1))
    except Exception:
        return {}

def validate_metadata(metadata):

    if not isinstance(metadata, dict):
        return False
    
    if metadata.get("schema_version") != "1.0":
        return False

    if not isinstance(metadata.get("score"), (int, float)):
        return False
    
    if metadata["score"] < 0 or metadata["score"] > 5:
        return False
    
    if metadata.get("recommendation") not in VALID_RECOMMENDATIONS:
        return False

    if metadata.get("fit_type") not in VALID_FIT_TYPES:
        return False

    if metadata.get("seniority_match") not in VALID_SENIORITY_MATCH:
        return False

    required_fields = [
        "company",
        "role",
        "score",
        "recommendation",
        "fit_type",
        "seniority_match",
        "why_apply",
        "main_gap"
    ]

    for field in required_fields:
        if field not in metadata:
            return False

    return True


def read_markdown_reports():
    if not CURRENT_RUN_REPORTS_FILE.exists():
        print("No current run reports found.")
        return []

    try:
        report_paths = json.loads(
            CURRENT_RUN_REPORTS_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        print("Could not read current_run_reports.json")
        return []

    reports = []

    for path in report_paths:
        file = Path(path)

        if not file.exists():
            continue

        text = file.read_text(encoding="utf-8", errors="ignore")

        reports.append({
            "file_name": file.name,
            "file_path": str(file),
            "text": text
        })

    return reports

def extract_summary(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    useful_points = []

    keywords = [
        "align",
        "fit",
        "experience",
        "gap",
        "strength",
        "competitive",
        "stakeholder",
        "transformation",
        "analytics",
        "strategy",
        "pmo",
        "consulting",
        "leadership",
    ]

    for line in lines:

        lower = line.lower()

        if any(keyword in lower for keyword in keywords):

            # Remove markdown formatting
            cleaned = re.sub(r"\*\*", "", line)

            # Remove numbering
            cleaned = re.sub(r"^\d+\.\s*", "", cleaned)

            # Remove extra spaces
            cleaned = cleaned.strip()

            if len(cleaned) > 40:
                useful_points.append(cleaned)

    if useful_points:

        summary = " ".join(useful_points[:3])

        summary = summary.replace("Sell senior without lying", "")
        summary = summary.replace("Candidate natural level", "Candidate profile fit")
        summary = summary.replace("Level detected in JD", "Role seniority")

        return summary[:500]

    return "Good alignment with strategy, PMO, and transformation-oriented responsibilities."

def clean_line(text):
    text = text.strip()
    text = text.replace("|", "").strip()
    return text


def classify_priority(score):
    if score is None:
        return "Manual Review"

    if score >= 4.3:
        return "High Priority"

    if score >= 3.5:
        return "Medium Priority"

    if score >= 2.5:
        return "Low Priority"

    return "Reject / Ignore"

def load_scraped_jobs():
    if not SCRAPED_JOBS_FILE.exists():
        return []

    try:
        text = SCRAPED_JOBS_FILE.read_text(encoding="utf-8").strip()
        if not text:
            return []
        return json.loads(text)
    except Exception:
        return []


def save_current_run_jobs(jobs):
    CURRENT_RUN_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_JOBS_FILE.write_text(
        json.dumps(jobs, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )


def load_current_run_jobs():
    if not CURRENT_RUN_JOBS_FILE.exists():
        return []

    try:
        text = CURRENT_RUN_JOBS_FILE.read_text(encoding="utf-8").strip()
        if not text:
            return []
        jobs = json.loads(text)
        return jobs if isinstance(jobs, list) else []
    except Exception:
        return []


def extract_url(text):
    match = re.search(r"https?://[^\s\)\]\}]+", text)
    if match:
        return match.group(0).strip()
    return ""


def normalize_url_for_match(url):
    return url.strip().rstrip("/")


def normalize_text_for_match(value):
    value = (value or "").lower()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = value.replace("&", " and ")
    value = re.sub(r"[\u2010-\u2015]", "-", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def text_matches(left, right):
    left = normalize_text_for_match(left)
    right = normalize_text_for_match(right)

    if not left or not right:
        return False

    return left == right or left in right or right in left


def report_matches_job(report, job):
    return (
        text_matches(report.get("company", ""), job.get("company", ""))
        and text_matches(report.get("job_title", ""), job.get("job_title", ""))
    )


def has_usable_report_metadata(report):
    return (
        report
        and report.get("metadata_can_override")
        and is_usable_metadata_value(report.get("raw_company", ""))
        and is_usable_metadata_value(report.get("raw_job_title", ""))
        and not is_missing_score_value(report.get("score", ""))
    )


def is_weak_summary_value(value):
    normalized = normalize_text_for_match(value)

    if is_missing_summary_value(value):
        return True

    if normalized in WEAK_METADATA_VALUES:
        return True

    return len(normalized) <= 1


def first_usable_unmatched_value(*values):
    for value in values:
        cleaned = clean_output_text(str(value or ""))
        if not is_weak_summary_value(cleaned):
            return cleaned
    return "Not Available"


def is_exportable_current_run_job(job):
    source_status = job.get("source_status") or {}
    return (
        (job.get("status") or "").lower() == "success"
        and bool((job.get("job_title") or "").strip())
        and bool((job.get("company") or "").strip())
        and len((job.get("content") or "").strip()) >= 200
        and source_status.get("jd_quality", "") != "unusable"
    )


def report_url_keys(report):
    keys = []
    for key in ("raw_report_url", "job_link", "jd_source_url"):
        normalized = normalize_url_for_match(report.get(key, ""))
        if normalized:
            keys.append(normalized)
    return keys


def find_job_from_scraped_jobs(url, company, job_title, scraped_jobs):

    # First try URL match
    if url:
        normalized_report_url = normalize_url_for_match(url)

        for job in scraped_jobs:
            job_url = normalize_url_for_match(job.get("url", ""))

            if job_url == normalized_report_url:
                return job

    # Fallback match by company + title
    for job in scraped_jobs:

        job_company = job.get("company", "").lower().strip()
        job_title_saved = job.get("job_title", "").lower().strip()

        if (
            job_company == company.lower().strip()
            and job_title_saved == job_title.lower().strip()
        ):
            return job

    return None


def extract_bold_field(text, field_name):
    match = re.search(
        rf"^\*\*{re.escape(field_name)}:\*\*[ \t]*(.*)$",
        text or "",
        flags=re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def read_jd_markdown_files():
    if not JD_FILES_DIR.exists():
        return []

    jd_files = []

    for file in sorted(JD_FILES_DIR.glob("*.md")):
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        jd_files.append({
            "file_name": file.name,
            "text": text,
            "source_url": extract_bold_field(text, "Source URL"),
            "company": extract_bold_field(text, "Company"),
            "job_title": extract_bold_field(text, "Job Title"),
            "location": extract_location_from_markdown(text),
        })

    return jd_files


def find_jd_markdown_location(url, company, job_title):
    jd_files = read_jd_markdown_files()

    if url:
        normalized_url = normalize_url_for_match(url)
        for jd_file in jd_files:
            jd_url = normalize_url_for_match(jd_file.get("source_url", ""))
            if jd_url and jd_url == normalized_url:
                return jd_file.get("location", "")
        return ""

    for jd_file in jd_files:
        if (
            text_matches(jd_file.get("company", ""), company)
            and text_matches(jd_file.get("job_title", ""), job_title)
        ):
            return jd_file.get("location", "")

    return ""


def clean_output_text(value):
    if not value:
        return ""

    value = re.sub(r"\*\*", "", value)
    value = value.replace("|", " ")
    value = re.sub(r"\s+", " ", value).strip()

    return value


def normalize_location_value(value):
    value = clean_output_text(str(value or ""))
    value = value.strip("`'\" ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def is_usable_location(value):
    normalized = normalize_location_value(value).lower()
    return normalized not in MISSING_LOCATION_VALUES


def is_missing_summary_value(value):
    normalized = clean_output_text(str(value or "")).strip().lower()
    return normalized in {
        "",
        "unknown",
        "unknown company",
        "unknown role",
        "not available",
        "not mentioned",
        "n/a",
        "na",
        "none",
        "null",
    }


def is_missing_score_value(value):
    if is_missing_summary_value(value):
        return True

    return re.search(
        r"\d+(?:\.\d+)?\s*(?:/\s*5)?",
        clean_output_text(str(value or ""))
    ) is None


def first_usable_summary_value(*values):
    for value in values:
        cleaned = clean_output_text(str(value or ""))
        if not is_missing_summary_value(cleaned):
            return cleaned
    return ""


def first_usable_score(*values):
    for value in values:
        if not is_missing_score_value(value):
            return value
    return ""


def first_usable_location(*values):
    for value in values:
        normalized = normalize_location_value(value)
        if is_usable_location(normalized):
            return normalized
    return "Not Mentioned"


def location_from_mapping(data):
    if not isinstance(data, dict):
        return ""

    for key, value in data.items():
        normalized_key = str(key or "").strip().lower().replace("-", "_")
        key_variants = {
            normalized_key,
            normalized_key.replace("_", " "),
        }

        if key_variants & LOCATION_KEYS:
            if isinstance(value, (str, int, float)):
                location = normalize_location_value(value)
                if is_usable_location(location):
                    return location

        if isinstance(value, dict):
            location = location_from_mapping(value)
            if is_usable_location(location):
                return location

    return ""


def extract_frontmatter_location(text):
    match = re.match(r"\A---\s*\n([\s\S]*?)\n---", text or "")
    if not match:
        return ""

    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace("-", "_")
        if {normalized_key, normalized_key.replace("_", " ")} & LOCATION_KEYS:
            location = normalize_location_value(value)
            if is_usable_location(location):
                return location

    return ""


def extract_labeled_location(text):
    label_pattern = r"(?:Job Location|Work Location|Location)"

    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        bold_match = re.match(
            rf"^\*\*{label_pattern}:\*\*[ \t]*(.+)$",
            stripped,
            flags=re.IGNORECASE,
        )
        if bold_match:
            location = normalize_location_value(bold_match.group(1))
            if is_usable_location(location):
                return location

        plain_match = re.match(
            rf"^{label_pattern}\s*:\s*(.+)$",
            stripped,
            flags=re.IGNORECASE,
        )
        if plain_match:
            location = normalize_location_value(plain_match.group(1))
            if is_usable_location(location):
                return location

        table_match = re.match(
            rf"^\|\s*{label_pattern}\s*\|\s*([^|]+)\|",
            stripped,
            flags=re.IGNORECASE,
        )
        if table_match:
            location = normalize_location_value(table_match.group(1))
            if is_usable_location(location):
                return location

    return ""


def extract_location_from_markdown(text, metadata=None):
    return first_usable_location(
        location_from_mapping(metadata or {}),
        extract_frontmatter_location(text),
        extract_labeled_location(text),
        "",
    )


def is_usable_metadata_value(value):
    normalized = str(value or "").strip().lower()
    return bool(normalized) and normalized not in {
        "unknown",
        "unknown company",
        "unknown-company",
        "unknown role",
        "unknown-role",
    }


def format_scrape_status(value):
    return "Success" if (value or "").lower() == "success" else "Fail"


def get_job_board(job):
    source_status = job.get("source_status") or {}
    source = source_status.get("source") or job.get("source") or ""
    display_names = {
        "linkedin": "LinkedIn",
        "indeed": "Indeed",
        "naukri": "Naukri",
        "naukrigulf": "NaukriGulf",
        "glassdoor": "Glassdoor",
        "bayt": "Bayt",
        "gulftalent": "GulfTalent",
        "iimjobs": "IIMJobs",
        "ziprecruiter": "ZipRecruiter",
        "foundit": "Foundit",
    }
    return display_names.get(source, source.title() if source else "")


def resolve_location(report_location="", jd_location="", scraped_location=""):
    return first_usable_location(
        report_location,
        jd_location,
        scraped_location,
    )


def csv_table_value(value):
    return clean_output_text(str(value or "")) or "Not Available"


def markdown_value(value):
    return clean_output_text(str(value or "")) or "Not Available"


def format_score(value):
    if isinstance(value, (int, float)):
        return f"{value}/5"
    return clean_output_text(str(value or ""))


def report_table_headers():
    return [
        "Sr. No.",
        "Company",
        "Role",
        "Location",
        "Score",
        "Scrape Status",
        "Recommendation",
        "Job Link"
    ]


def build_processed_job_rows(parsed_reports):
    rows = []
    current_run_jobs = load_current_run_jobs()
    used_reports = set()
    report_by_url = {}

    for index, report in enumerate(parsed_reports):
        report["_order_index"] = index
        for url_key in report_url_keys(report):
            report_by_url.setdefault(url_key, report)

    evaluable_jobs = [
        job for job in current_run_jobs
        if is_exportable_current_run_job(job)
    ]
    allow_order_match = len(evaluable_jobs) == len(parsed_reports)
    order_index_by_job_id = {
        id(job): index
        for index, job in enumerate(evaluable_jobs)
    }

    for job in current_run_jobs:
        job_url = job.get("url", "")
        job_company = job.get("company", "")
        job_role = job.get("job_title", "")
        job_location = job.get("location", "")
        job_score = job.get("score", "")
        matched_report = None

        # Matching order: exact report URL, JD markdown source URL, current-run
        # order, then fuzzy company+role as the last resort.
        normalized_job_url = normalize_url_for_match(job_url)
        if normalized_job_url:
            matched_report = report_by_url.get(normalized_job_url)
            if matched_report and matched_report.get("_order_index") in used_reports:
                matched_report = None

        if not matched_report:
            jd_source_url = ""
            if job_url:
                for jd_file in read_jd_markdown_files():
                    candidate_url = normalize_url_for_match(jd_file.get("source_url", ""))
                    if candidate_url and candidate_url == normalized_job_url:
                        jd_source_url = candidate_url
                        break
            if jd_source_url:
                matched_report = report_by_url.get(jd_source_url)
                if matched_report and matched_report.get("_order_index") in used_reports:
                    matched_report = None

        if not matched_report and allow_order_match:
            order_index = order_index_by_job_id.get(id(job))
            if order_index is not None and order_index < len(parsed_reports):
                candidate = parsed_reports[order_index]
                if candidate.get("_order_index") not in used_reports:
                    matched_report = candidate

        if not matched_report:
            matched_report = next(
                (
                    report
                    for report in parsed_reports
                    if report.get("_order_index") not in used_reports
                    and report_matches_job(report, job)
                ),
                None
            )

        report_can_override = has_usable_report_metadata(matched_report)
        if matched_report:
            used_reports.add(matched_report.get("_order_index"))

        source_status = job.get("source_status") or {}
        scrape_status = source_status.get("scrape_status") or job.get("status", "")
        matched_report_location = matched_report.get("raw_report_location", "") if matched_report else ""

        if report_can_override:
            row_company = clean_output_text(matched_report.get("raw_company", ""))
            row_role = clean_output_text(matched_report.get("raw_job_title", ""))
            row_score = matched_report.get("score", "")
            row_recommendation = matched_report.get("recommendation", "")
        else:
            row_company = first_usable_unmatched_value(job_company)
            row_role = first_usable_unmatched_value(job_role)
            row_score = first_usable_score(job_score) or "Not Available"
            row_recommendation = ""

        jd_location = find_jd_markdown_location(
            job_url,
            row_company,
            row_role,
        )
        if report_can_override:
            row_location = first_usable_location(
                matched_report_location,
                jd_location,
                job_location,
            )
        else:
            row_location = first_usable_location(
                jd_location,
                job_location,
            )

        rows.append({
            "company": row_company,
            "role": row_role,
            "location": row_location,
            "score": row_score,
            "recommendation": row_recommendation,
            "job_board": get_job_board(job),
            "scrape_status": format_scrape_status(scrape_status),
            "job_link": job_url,
            "report_file": matched_report.get("file_name") if matched_report else "",
        })

    if rows:
        return rows

    return [
        {
            "company": report.get("company", ""),
            "role": report.get("job_title", ""),
            "location": resolve_location(report.get("location", "")),
            "score": report.get("score", ""),
            "recommendation": report.get("recommendation", ""),
            "job_board": report.get("source", ""),
            "scrape_status": format_scrape_status(report.get("scrape_status", "")),
            "job_link": report.get("job_link", ""),
            "report_file": report.get("file_name", ""),
        }
        for report in parsed_reports
    ]


def is_scraped_row(row):
    return (row.get("scrape_status") or "").lower() == "success"


def build_job_heading(index, row):
    return f"### {index}. {markdown_value(row.get('role'))} - {markdown_value(row.get('company'))}"


def build_scraped_jobs_section(rows):
    if not rows:
        return "No scraped jobs in this run.\n"

    markdown = ""
    for index, row in enumerate(rows, start=1):
        markdown += f"""{build_job_heading(index, row)}
Score: {markdown_value(format_score(row.get("score")))}
Recommendation: {markdown_value(row.get("recommendation"))}
Scrape Status: {markdown_value(row.get("scrape_status"))}
Location: {markdown_value(row.get("location"))}
Job Link: {markdown_value(row.get("job_link"))}
Report File: {markdown_value(row.get("report_file"))}

"""
    return markdown


def build_unscraped_jobs_section(rows):
    if not rows:
        return "No unscraped jobs in this run.\n"

    markdown = ""
    for index, row in enumerate(rows, start=1):
        markdown += f"""{build_job_heading(index, row)}
Scrape Status: {markdown_value(row.get("scrape_status"))}
Location: {markdown_value(row.get("location"))}
Job Link: {markdown_value(row.get("job_link"))}

"""
    return markdown

def parse_reports():
    reports = read_markdown_reports()
    scraped_jobs = load_scraped_jobs()
    parsed = []

    for report in reports:
        text = report["text"]

        metadata = extract_metadata_json(text)
        if not validate_metadata(metadata):
            print(f"Invalid metadata in: {report['file_name']}")
            continue

        score = metadata.get("score")
        company = metadata.get("company", "Unknown Company")
        job_title = metadata.get("role", "Unknown Role")
        report_url = extract_url(text)

        matched_job = find_job_from_scraped_jobs(
            report_url,
            company,
            job_title,
            scraped_jobs
        )

        if not matched_job:
            for job in scraped_jobs:
                if (
                    job.get("company", "").lower().strip() == company.lower().strip()
                    and job.get("job_title", "").lower().strip() == job_title.lower().strip()
                ):
                    matched_job = job
                    break

        source_status = metadata.get("source_status", {})
        resolved_company = (
            company
            if is_usable_metadata_value(company)
            else (matched_job or {}).get("company", "Unknown Company")
        )
        resolved_job_title = (
            job_title
            if is_usable_metadata_value(job_title)
            else (matched_job or {}).get("job_title", "Unknown Role")
        )
        matched_job_url = (matched_job or {}).get("url", "")
        report_location = extract_location_from_markdown(text, metadata)
        metadata_can_override = (
            is_usable_metadata_value(company)
            and is_usable_metadata_value(job_title)
            and not is_missing_score_value(score)
        )
        resolved_location = first_usable_location(
            report_location,
            (matched_job or {}).get("location", ""),
        )
        if is_missing_summary_value(resolved_location):
            jd_location = find_jd_markdown_location(
                matched_job_url or report_url,
                resolved_company,
                resolved_job_title,
            )
            resolved_location = first_usable_location(jd_location, resolved_location)

        parsed.append({
            "file_name": report["file_name"],
            "file_path": report["file_path"],
            "job_title": resolved_job_title,
            "company": resolved_company,
            "raw_job_title": job_title,
            "raw_company": company,
            "raw_report_url": report_url,
            "raw_report_location": report_location,
            "metadata_can_override": metadata_can_override,
            "score": score,
            "priority": classify_priority(score),

            "fit_type": metadata.get("fit_type", "Other"),

            "seniority_match": metadata.get("seniority_match", "Good"),
            "why_apply": metadata.get("why_apply", ""),
            "main_gap": metadata.get("main_gap", ""),

            # NEW SOURCE STATUS FIELDS
            "source": source_status.get("source", ""),
            "scrape_status": source_status.get("scrape_status", ""),
            "jd_quality": source_status.get("jd_quality", ""),

            "summary": extract_summary(text),

            "date": matched_job.get(
                "date",
                datetime.now().strftime("%Y-%m-%d")
            ) if matched_job else datetime.now().strftime("%Y-%m-%d"),

            "location": resolved_location,

            "job_link": matched_job.get(
                "url",
                report_url
            ) if matched_job else report_url,

            "recommendation": metadata.get(
                "recommendation",
                "Consider"
            ),
        })

    return parsed

def build_daily_summary(parsed_reports):
    today = datetime.now().strftime("%Y-%m-%d")
    report_rows = build_processed_job_rows(parsed_reports)
    scraped_rows = [row for row in report_rows if is_scraped_row(row)]
    unscraped_rows = [row for row in report_rows if not is_scraped_row(row)]

    return f"""# AI Career Agent Daily Summary

Date: {today}

## Executive Summary

Total reports reviewed: {len(report_rows)}

## Scraped Jobs
{build_scraped_jobs_section(scraped_rows)}
## Unscraped Jobs
{build_unscraped_jobs_section(unscraped_rows)}

"""

def save_daily_summary(markdown):
    DAILY_REPORTS_FOLDER.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y_%m_%d_%H-%M")
    output_file = DAILY_REPORTS_FOLDER / f"daily_summary_{timestamp}.md"

    with open(output_file, "x", encoding="utf-8") as file:
        file.write(markdown)

    print(f"Daily summary created: {output_file}")

    return output_file

def parse_markdown_jobs(markdown):
    rows = []
    section = None
    current = None

    for line in markdown.splitlines():
        stripped = line.strip()

        if stripped == "## Scraped Jobs":
            section = "scraped"
            continue
        if stripped == "## Unscraped Jobs":
            section = "unscraped"
            continue
        if not section:
            continue

        heading = re.match(r"^###\s+\d+\.\s+(.+)$", stripped)
        if heading:
            heading_text = heading.group(1)
            if " - " in heading_text:
                role, company = heading_text.rsplit(" - ", 1)
            else:
                role, company = heading_text, ""

            current = {
                "role": clean_output_text(role),
                "company": clean_output_text(company),
                "location": "",
                "score": "",
                "scrape_status": "",
                "recommendation": "",
                "job_link": "",
            }
            rows.append(current)
            continue

        if not current or ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = clean_output_text(value)
        if key == "Score":
            current["score"] = value
        elif key == "Recommendation":
            current["recommendation"] = value
        elif key == "Scrape Status":
            current["scrape_status"] = value
        elif key == "Location":
            current["location"] = value
        elif key == "Job Link":
            current["job_link"] = value

    return rows


def save_daily_csv(markdown_file, output_dir):
    csv_path = Path(output_dir) / f"{markdown_file.stem}.csv"

    headers = report_table_headers()
    report_rows = parse_markdown_jobs(markdown_file.read_text(encoding="utf-8"))

    with open(csv_path, "x", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow(headers)

        for idx, report in enumerate(report_rows, start=1):
            score = report.get("score", "")

            writer.writerow([
                idx,
                csv_table_value(report.get("company")),
                csv_table_value(report.get("role")),
                csv_table_value(report.get("location")),
                csv_table_value(score),
                csv_table_value(report.get("scrape_status")),
                csv_table_value(report.get("recommendation")),
                csv_table_value(report.get("job_link"))
            ])

    print(f"\nCSV summary created: {csv_path}")

def deduplicate_reports(reports):
    unique_jobs = {}

    for report in reports:

        key = (
            report.get("company", "").lower().strip(),
            report.get("job_title", "").lower().strip()
        )

        current_score = float(report.get("score") or 0)

        if key not in unique_jobs:
            unique_jobs[key] = report

        else:
            existing_score = float(
                unique_jobs[key].get("score") or 0
            )

            if current_score > existing_score:
                unique_jobs[key] = report

    return list(unique_jobs.values())

def main():
    print("Starting report builder...")

    parsed_reports = parse_reports()
    print(f"Parsed reports found: {len(parsed_reports)}")

    parsed_reports = deduplicate_reports(parsed_reports)
    print(f"Reports after deduplication: {len(parsed_reports)}")

    if not parsed_reports and not load_current_run_jobs():
        print("No career-ops reports found.")
        return

    daily_summary = build_daily_summary(parsed_reports)

    daily_summary_file = save_daily_summary(daily_summary)
    save_daily_csv(daily_summary_file, DAILY_REPORTS_FOLDER)

    print("Report builder completed.")


if __name__ == "__main__":
    main()

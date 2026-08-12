import os
import csv
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

from paths import DAILY_REPORTS_DIR, ENV_FILE

load_dotenv(ENV_FILE)


DAILY_REPORTS_FOLDER = DAILY_REPORTS_DIR
def get_latest_file(extension):
    files = sorted(
        DAILY_REPORTS_FOLDER.glob(f"*.{extension}"),
        key=lambda file: file.stat().st_mtime,
        reverse=True
    )

    if not files:
        return None

    return files[0]


def extract_date_from_report_file(file_path):
    parts = file_path.stem.replace("daily_summary_", "").split("_")
    if len(parts) >= 3:
        return "-".join(parts[:3])
    return "Unknown"


def clean_cell(value, scrape_status="", header=""):
    value = (value or "").strip()
    is_unscraped = bool(scrape_status.strip()) and scrape_status.strip().lower() != "success"

    if header == "Recommendation" and is_unscraped:
        return ""

    return value or "Unknown"


def parse_score(value):
    try:
        return float((value or "").replace("/5", "").strip())
    except ValueError:
        return -1


def job_line(row, include_link=False):
    role = clean_cell(row.get("Role", ""))
    company = clean_cell(row.get("Company", ""))
    location = clean_cell(row.get("Location", ""))
    score = clean_cell(row.get("Score", ""))

    if include_link:
        link = clean_cell(row.get("Job Link", ""))
        return f"- {role} - {company} - {location} - {link}"

    return f"- {role} - {company} - {location} ({score})"


def recommendation_section(title, rows):
    if not rows:
        return ""

    lines = [f"{title}:"]
    for row in sorted(rows, key=lambda item: parse_score(item.get("Score", "")), reverse=True):
        lines.append(job_line(row))
    return "\n".join(lines) + "\n\n"


def is_unscraped(row):
    return (row.get("Scrape Status", "") or "").strip().lower() != "success"


def build_email_body(csv_file):
    with open(csv_file, "r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    scraped_rows = [row for row in rows if not is_unscraped(row)]
    unscraped_rows = [row for row in rows if is_unscraped(row)]
    manual_review_count = sum(
        1
        for row in rows
        if clean_cell(row.get("Recommendation", "")).lower() in {"unknown", "not available", "manual review"}
    )

    sections = ""
    for recommendation in ("Apply", "Consider", "Deprioritize"):
        matching_rows = [
            row
            for row in scraped_rows
            if (row.get("Recommendation", "") or "").strip().lower() == recommendation.lower()
        ]
        sections += recommendation_section(recommendation, matching_rows)

    if not sections:
        sections = "None\n\n"

    if unscraped_rows:
        unscraped_lines = "\n".join(job_line(row, include_link=True) for row in unscraped_rows)
    else:
        unscraped_lines = "None"

    return f"""AI Career Agent Daily Summary
Date: {extract_date_from_report_file(csv_file)}

Executive Summary
-----------------
Total Reports Reviewed: {len(rows)}
Manual Review: {manual_review_count}

{sections}Unscraped jobs: {len(unscraped_rows)}
{unscraped_lines}

Attachments:
- daily_summary.csv
"""


def send_email_summary():
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_APP_PASSWORD")
    receiver_email = os.getenv("EMAIL_RECEIVER")

    if not sender_email or not sender_password or not receiver_email:
        print("Email credentials missing.")
        return

    latest_csv = get_latest_file("csv")

    if not latest_csv:
        print("No CSV report found for email.")
        return

    body = build_email_body(latest_csv)

    msg = EmailMessage()
    msg["Subject"] = "AI Career Agent Daily Summary"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content(body)
    msg.add_attachment(
        latest_csv.read_bytes(),
        maintype="text",
        subtype="csv",
        filename="daily_summary.csv",
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)

    print("Email summary sent successfully.")


if __name__ == "__main__":
    send_email_summary()

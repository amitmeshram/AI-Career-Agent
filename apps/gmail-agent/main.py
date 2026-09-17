from gmail_reader import get_recent_job_alert_candidates
from jd_scraper import scrape_job_description, save_job_result
from link_extractor import normalize_url
from career_ops_runner import (
    export_jobs_to_markdown,
    evaluate_all_jd_files,
)
from report_builder import main as build_daily_report, save_current_run_jobs
import json
import os
import platform
import re
import sys
from paths import CAREER_OPS_ROOT, SCRAPED_JOBS_FILE
from email_sender import send_email_summary
from startup_health_check import (
    reconnect_gmail,
    reconnect_linkedin,
    run_startup_health_check,
)


DEFAULT_MAX_JOB_ALERTS_TO_PROCESS = 5
DEFAULT_MAX_JOB_LINKS_TO_PROCESS = 50
PROFILE_FILE = CAREER_OPS_ROOT / "config" / "profile.yml"

if platform.system() == "Windows":
    import msvcrt

    def read_key():
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            arrow_key = msvcrt.getwch()
            return {
                "H": "UP",
                "P": "DOWN",
            }.get(arrow_key)
        if key == "\r":
            return "ENTER"
        return None
else:
    import termios
    import tty

    def read_key():
        if not sys.stdin.isatty():
            value = input("> ").strip()
            return "ENTER" if value == "" else value

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
            if key == "\x1b":
                sequence = sys.stdin.read(2)
                return {
                    "[A": "UP",
                    "[B": "DOWN",
                }.get(sequence)
            if key in ("\r", "\n"):
                return "ENTER"
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def parse_positive_int(value, default_value):
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default_value
    return parsed if parsed > 0 else default_value


def load_scan_settings(profile_path=PROFILE_FILE):
    settings = {
        "max_job_alerts_to_process": DEFAULT_MAX_JOB_ALERTS_TO_PROCESS,
        "max_job_links_to_process": DEFAULT_MAX_JOB_LINKS_TO_PROCESS,
    }
    try:
        text = profile_path.read_text(encoding="utf-8")
    except OSError:
        return settings

    block_match = re.search(
        r"(?m)^gmail_scan:\s*\n(?P<body>(?:^[ \t]+[^\n]*\n?)*)",
        text,
    )
    if not block_match:
        return settings

    for key in settings:
        value_match = re.search(rf"(?m)^[ \t]+{re.escape(key)}:\s*\"?([^\"\n#]+)", block_match.group("body"))
        if value_match:
            settings[key] = parse_positive_int(value_match.group(1), settings[key])
    return settings


def scan_settings_block(settings):
    return "\n".join(
        [
            "gmail_scan:",
            f"  max_job_alerts_to_process: {settings['max_job_alerts_to_process']}",
            f"  max_job_links_to_process: {settings['max_job_links_to_process']}",
        ]
    )


def save_scan_settings(settings, profile_path=PROFILE_FILE):
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = profile_path.read_text(encoding="utf-8")
    except OSError:
        text = "# Career-Ops Profile Configuration\n"

    block = scan_settings_block(settings)
    existing = re.search(r"(?m)^gmail_scan:\s*\n(?:^[ \t]+[^\n]*\n?)*", text)
    if existing:
        updated = text[: existing.start()] + block + "\n" + text[existing.end():].lstrip("\n")
    else:
        cv_match = re.search(r"(?m)^cv:\s*$", text)
        if cv_match:
            updated = text[: cv_match.start()].rstrip() + "\n\n" + block + "\n\n" + text[cv_match.start():]
        else:
            updated = text.rstrip() + "\n\n" + block + "\n"

    profile_path.write_text(updated, encoding="utf-8")


def prompt_scan_limit(label, current, input_func=input):
    while True:
        raw = input_func(f"{label} [{current}]: ").strip()
        if not raw:
            return current
        value = parse_positive_int(raw, 0)
        if value > 0:
            return value
        print("Please enter a whole number greater than zero.")


def configure_scan_settings(input_func=input):
    settings = load_scan_settings()
    print("Gmail Scan Settings")
    print("===================")
    print(f"Current max job alerts to process: {settings['max_job_alerts_to_process']}")
    print(f"Current max job links to process: {settings['max_job_links_to_process']}")
    print("")
    settings["max_job_alerts_to_process"] = prompt_scan_limit(
        "How many job alerts to process",
        settings["max_job_alerts_to_process"],
        input_func=input_func,
    )
    settings["max_job_links_to_process"] = prompt_scan_limit(
        "Max job links to process",
        settings["max_job_links_to_process"],
        input_func=input_func,
    )
    save_scan_settings(settings)
    print("Scan settings saved to config/profile.yml.")

def is_already_scraped(url):
    if not SCRAPED_JOBS_FILE.exists():
        return False

    try:
        with open(SCRAPED_JOBS_FILE, "r", encoding="utf-8") as file:
            jobs = json.load(file)

        normalized_url = normalize_url(url)

        for job in jobs:
            if normalize_url(job.get("url", "")) != normalized_url:
                continue

            return True

        return False

    except (OSError, json.JSONDecodeError):
        return False


def merge_email_candidate_metadata(result, candidate):
    merged = dict(result)
    candidate_metadata = {
        "portal": candidate.get("portal", ""),
        "email_sender": candidate.get("email_sender", ""),
        "email_subject": candidate.get("email_subject", ""),
        "email_date": candidate.get("email_date", ""),
        "anchor_text": candidate.get("anchor_text", ""),
        "email_card_text": candidate.get("email_card_text", ""),
        "job_title": candidate.get("job_title", ""),
        "company": candidate.get("company", ""),
        "location": candidate.get("location", ""),
        "metadata_source": candidate.get("metadata_source", ""),
    }

    bad_values = {
        "",
        "apply now",
        "blocked",
        "indeed.com",
        "not available",
        "not mentioned",
        "view details",
    }

    for field in ("job_title", "company", "location"):
        current = (merged.get(field) or "").strip()
        if current.lower() in bad_values and candidate.get(field):
            merged[field] = candidate[field]

    merged["email_candidate"] = candidate_metadata
    if any(candidate.get(field) for field in ("job_title", "company", "location")):
        merged["needs_manual_review"] = bool(
            merged.get("needs_manual_review")
            or merged.get("status") != "success"
        )

    return merged


def run_automatic_workflow():
    print("AI Career Agent started")
    print("=======================")
    scan_settings = load_scan_settings()

    print("\nStep 1: Reading Gmail job alerts...")
    print(
        "Scan limits: "
        f"job_alerts={scan_settings['max_job_alerts_to_process']}, "
        f"job_links={scan_settings['max_job_links_to_process']}"
    )
    job_candidates = get_recent_job_alert_candidates(max_results=scan_settings["max_job_alerts_to_process"])

    print("\nStep 2: Job candidates extracted")
    print(f"Total candidates found: {len(job_candidates)}")

    if not job_candidates:
        print("No job candidates found. Stopping.")
        return

    print("\nStep 3: Scraping job descriptions...")

    new_candidates = [
        candidate
        for candidate in job_candidates
        if not is_already_scraped(candidate.get("url", ""))
    ]
    test_candidates = new_candidates[:scan_settings["max_job_links_to_process"]]
    test_links = [candidate.get("url", "") for candidate in test_candidates]

    print("\n====================")
    print(f"New candidates detected: {len(new_candidates)}")
    print(f"Candidates selected for scraping: {len(test_candidates)}")

    current_run_jobs = []

    for index, candidate in enumerate(test_candidates, start=1):
        link = candidate.get("url", "")
        print("\n----------------------------")
        print(f"Processing job {index} of {len(test_candidates)}")
        print(link)
        if candidate.get("job_title") or candidate.get("company") or candidate.get("location"):
            print(
                "Email metadata: "
                f"{candidate.get('job_title') or 'Not Available'} | "
                f"{candidate.get('company') or 'Not Available'} | "
                f"{candidate.get('location') or 'Not Mentioned'}"
            )

        if is_already_scraped(link):
            print("Job already scraped. Skipping browser open.")
            continue

        result = scrape_job_description(link)
        result = merge_email_candidate_metadata(result, candidate)
        save_job_result(result)
        current_run_jobs.append(result)

        print(f"Status: {result.get('status')}")

    save_current_run_jobs(current_run_jobs)

    print("\nStep 4: Exporting scraped jobs to JD markdown files...")
    created_jd_files = export_jobs_to_markdown(
        current_run_urls=set(test_links)
    )

    print("\nStep 5: Running career-ops evaluations...")
    evaluation_results = evaluate_all_jd_files(created_jd_files)

    if not evaluation_results:
        print("\nNo new job evaluations were created.")
        if not current_run_jobs:
            print("Report delivery skipped.")
            print("\n=======================")
            print("AI Career Agent finished")
            return

    print("\nStep 6: Building daily summary report...")
    build_daily_report()

    print("\nStep 7: Sending email summary...")
    send_email_summary()

    print("\n=======================")
    print("AI Career Agent finished")

def get_menu_options(health):
    first_option = (
        "Run Gmail Job Scan"
        if health["gmail"]["status"] == "OK"
        else "Reconnect Gmail"
    )
    options = [
        first_option,
        "Manual JD Scan",
    ]
    if health["linkedin"]["status"] != "OK":
        options.append("Reconnect LinkedIn")
    options.append("Scan Settings")
    options.append("Exit")
    return tuple(options)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def display_health_check(health):
    print("================================")
    print("AI Career Agent Startup Check")
    print("================================")
    print()
    print(f"Gmail Connection      [{health['gmail']['status']}]")
    print(f"LinkedIn Session      [{health['linkedin']['status']}]")
    print(f"Career-Ops Files      [{health['career_ops']['status']}]")
    print(f"AI Model Connection   [{health['ai_model']['status']}]")
    print(f"Output Folders        [{health['output_folders']['status']}]")


def display_startup_menu(selected_index, health, options):
    clear_screen()
    display_health_check(health)
    print("\nSelect option:\n")

    for index, option in enumerate(options, start=1):
        cursor = ">" if index - 1 == selected_index else " "
        print(f"{cursor} {index}. {option}")


def get_menu_selection(health):
    options = get_menu_options(health)
    selected_index = 0

    while True:
        display_startup_menu(selected_index, health, options)
        key = read_key()

        if key == "UP":
            selected_index = (selected_index - 1) % len(options)
        elif key == "DOWN":
            selected_index = (selected_index + 1) % len(options)
        elif key == "ENTER":
            return selected_index + 1
        elif isinstance(key, str) and key.isdigit():
            selected_number = int(key)
            if 1 <= selected_number <= len(options):
                return selected_number


def run_manual_jd_scan():
    import manual_jd_input

    manual_jd_input.main()


def main():
    while True:
        health = run_startup_health_check()

        try:
            selection = get_menu_selection(health)
        except KeyboardInterrupt:
            print("\nExiting.")
            return

        options = get_menu_options(health)
        selected_option = options[selection - 1]
        clear_screen()

        if selected_option == "Run Gmail Job Scan":
            run_automatic_workflow()
            return
        if selected_option == "Reconnect Gmail":
            if health["gmail"]["status"] == "OK":
                run_automatic_workflow()
                return
            print("Starting Gmail reconnect...")
            reconnect_gmail()
            print("Refreshing startup checks. Wait a moment....")
        elif selected_option == "Manual JD Scan":
            run_manual_jd_scan()
            return
        elif selected_option == "Reconnect LinkedIn":
            reconnect_linkedin()
            print("Refreshing startup checks. Wait a moment....")
        elif selected_option == "Scan Settings":
            configure_scan_settings()
        elif selected_option == "Exit":
            return


if __name__ == "__main__":
    main()

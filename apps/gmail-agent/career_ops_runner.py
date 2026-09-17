import json
import os
import re
import subprocess
import sys
from pathlib import Path

from paths import (
    CAREER_OPS_ROOT,
    CURRENT_RUN_REPORTS_FILE,
    JD_FILES_DIR,
    PROCESSED_JOBS_FILE,
    SCRAPED_JOBS_FILE,
)
from link_extractor import normalize_url

JD_OUTPUT_FOLDER = JD_FILES_DIR
CAREER_OPS_REPORTS = CAREER_OPS_ROOT / "reports"
PROCESSED_STATE_FILE = PROCESSED_JOBS_FILE
EVALUATION_FAILURES_DIR = CAREER_OPS_ROOT / "data" / "gmail-agent" / "evaluation_failures"
MAX_EVALUATION_FAILURES = 3

GEMINI_MODEL = "gemini-2.5-flash"
PROVIDER_ALIASES = {
    "claude": "anthropic",
    "moonshot": "kimi",
    "zhipu": "glm",
    "bigmodel": "glm",
}
OPENROUTER_EVALUATOR_PROVIDERS = {
    "openrouter",
    "openai",
    "custom",
    "anthropic",
    "deepseek",
    "kimi",
    "glm",
}
SUPPORTED_EVALUATOR_PROVIDERS = OPENROUTER_EVALUATOR_PROVIDERS | {"gemini"}


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


def configured_ai_provider():
    values = read_env_file(CAREER_OPS_ROOT / ".env")
    provider = str(values.get("AI_PROVIDER_NAME") or "").strip().lower()
    return PROVIDER_ALIASES.get(provider, provider)


def evaluation_command_for_provider(provider, jd_file):
    normalized_provider = PROVIDER_ALIASES.get(str(provider or "").strip().lower(), str(provider or "").strip().lower())

    if normalized_provider in OPENROUTER_EVALUATOR_PROVIDERS:
        return ["node", "openrouter-eval.mjs", "--file", str(jd_file)]

    if normalized_provider == "gemini":
        return ["node", "gemini-eval.mjs", "--file", str(jd_file)]

    return None

def save_current_run_reports(report_paths):
    CURRENT_RUN_REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(CURRENT_RUN_REPORTS_FILE, "w", encoding="utf-8") as file:
        json.dump(report_paths, file, indent=4)

def load_processed_state():
    if not PROCESSED_STATE_FILE.exists():
        return {
            "exported_urls": [],
            "evaluated_jd_files": []
        }

    try:
        with open(PROCESSED_STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return {
            "exported_urls": [],
            "evaluated_jd_files": []
        }

def save_processed_state(state):
    PROCESSED_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(PROCESSED_STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=4)

def clean_filename(text):
    text = text.strip()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text)
    text = text.strip("_")
    return text[:80]


def text_tail(value, limit=2000):
    text = value or ""
    return text[-limit:]


def record_evaluation_failure(state, jd_file, result, report_path=""):
    failures = state.setdefault("evaluation_failures", {})
    entry = failures.get(jd_file.name, {})
    failure_count = int(entry.get("count", 0)) + 1

    failures[jd_file.name] = {
        "count": failure_count,
        "last_return_code": result.get("return_code"),
        "last_report_path": report_path,
        "last_stdout_tail": text_tail(result.get("stdout", "")),
        "last_stderr_tail": text_tail(result.get("stderr", "")),
    }

    if failure_count >= MAX_EVALUATION_FAILURES:
        EVALUATION_FAILURES_DIR.mkdir(parents=True, exist_ok=True)
        failure_path = EVALUATION_FAILURES_DIR / f"{clean_filename(jd_file.stem)}.json"
        failure_path.write_text(
            json.dumps(
                {
                    "jd_file": jd_file.name,
                    "failure_count": failure_count,
                    "reason": "No valid evaluation report was produced after repeated attempts.",
                    "return_code": result.get("return_code"),
                    "report_path": report_path,
                    "stdout_tail": text_tail(result.get("stdout", "")),
                    "stderr_tail": text_tail(result.get("stderr", "")),
                },
                indent=4,
            ),
            encoding="utf-8",
        )
        return failure_count, failure_path

    return failure_count, None


def load_scraped_jobs():
    if not SCRAPED_JOBS_FILE.exists():
        print("scraped_jobs.json not found.")
        return []

    with open(SCRAPED_JOBS_FILE, "r", encoding="utf-8") as file:
        content = file.read().strip()

        if not content:
            return []

        return json.loads(content)


def create_jd_markdown(job, index):
    job_title = job.get("job_title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    url = job.get("url", "")
    content = job.get("content", "")
    status = job.get("status", "")
    needs_manual_review = job.get("needs_manual_review", "")
    source_status = job.get("source_status", {})

    
    markdown = f"""# Job Description

## Basic Details

**Job Title:** {job_title}

**Company:** {company}

**Location:** {location}

**Source URL:** {url}

**Scrape Status:** {status}

**Needs Manual Review:** {needs_manual_review}

---
## Source Status

```json
{json.dumps(source_status, indent=2)}
```
## Job Description Content

{content}
"""
    safe_title = clean_filename(job_title or "unknown_job")
    safe_company = clean_filename(company or "unknown_company")

    filename = f"{index:02d}_{safe_title}_{safe_company}.md"
    file_path = JD_OUTPUT_FOLDER / filename

    return file_path, markdown


def is_exportable_job(job):
    job_title = (job.get("job_title") or "").strip()
    company = (job.get("company") or "").strip()
    content = (job.get("content") or "").strip()
    status = (job.get("status") or "").lower()
    jd_quality = (job.get("source_status") or {}).get("jd_quality", "")

    return (
        status == "success"
        and bool(job_title)
        and bool(company)
        and len(content) >= 200
        and jd_quality != "unusable"
    )


def normalized_job_url(url):
    return normalize_url(url or "")


def extract_saved_report_path(stdout):
    report_line = re.compile(
        r"^(?:[^\w*`]*\s*)?Report saved:\s*(?P<path>.+?\.md)\s*$",
        flags=re.IGNORECASE,
    )

    for line in (stdout or "").splitlines():
        match = report_line.match(line.strip())
        if not match:
            continue

        report_path = match.group("path").strip()
        if report_path.lower().endswith(".md"):
            return report_path

    return ""


def export_jobs_to_markdown(current_run_urls=None):
    JD_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    jobs = load_scraped_jobs()

    if not jobs:
        print("No scraped jobs found.")
        return []

    state = load_processed_state()

    exported_urls = {
        normalized_job_url(url)
        for url in state.get("exported_urls", [])
        if normalized_job_url(url)
    }
    current_run_url_keys = None
    if current_run_urls is not None:
        current_run_url_keys = {
            normalized_job_url(url)
            for url in current_run_urls
            if normalized_job_url(url)
        }

    created_files = []
    already_exported_count = 0
    not_exportable_count = 0

    next_index = len(list(JD_OUTPUT_FOLDER.glob("*.md"))) + 1

    for job in jobs:

        job_url = job.get("url", "")
        job_url_key = normalized_job_url(job_url)

        if current_run_url_keys is not None and job_url_key not in current_run_url_keys:
            continue

        if not job_url_key:
            continue

        if job_url_key in exported_urls:
            already_exported_count += 1
            continue

        if not is_exportable_job(job):
            not_exportable_count += 1
            continue

        file_path, markdown = create_jd_markdown(job, next_index)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(markdown)

        created_files.append(file_path)

        exported_urls.add(job_url_key)

        next_index += 1

    state["exported_urls"] = list(exported_urls)
    save_processed_state(state)

    print(f"New JD markdown files created: {len(created_files)}")
    if already_exported_count:
        print(f"Previously exported jobs skipped: {already_exported_count}")
    if not_exportable_count:
        print(f"Blocked or unusable jobs skipped: {not_exportable_count}")

    for file_path in created_files:
        print(f"- {file_path}")

    return created_files

def get_jd_files():
    if not JD_OUTPUT_FOLDER.exists():
        print(f"JD folder not found: {JD_OUTPUT_FOLDER}")
        return []

    return sorted(JD_OUTPUT_FOLDER.glob("*.md"))


def is_evaluable_jd_file(jd_file):
    text = jd_file.read_text(encoding="utf-8")

    def field(name):
        match = re.search(
            rf"^\*\*{re.escape(name)}:\*\*[ \t]*([^\r\n]*)$",
            text,
            flags=re.MULTILINE
        )
        return match.group(1).strip() if match else ""

    job_title = field("Job Title")
    company = field("Company")
    scrape_status = field("Scrape Status").lower()
    content_marker = "## Job Description Content"
    content = text.split(content_marker, 1)[1].strip() if content_marker in text else ""
    challenge_signals = (
        "humans only",
        "just a moment",
        "ray id:",
        "access denied",
        "blocked - indeed.com",
    )

    return (
        scrape_status == "success"
        and bool(job_title)
        and bool(company)
        and len(content) >= 200
        and not any(signal in content.lower() for signal in challenge_signals)
    )


def run_career_ops_evaluation(jd_file):
    print("\n--------------------------------")
    print(f"Evaluating JD file: {jd_file.name}")

    provider = configured_ai_provider()
    command = evaluation_command_for_provider(provider, jd_file)

    if not command:
        supported = ", ".join(sorted(SUPPORTED_EVALUATOR_PROVIDERS))
        message = (
            f"AI_PROVIDER_NAME={provider or '(missing)'} is not supported by the current evaluator workflow.\n"
            f"Supported providers: {supported}.\n"
            "Aliases are accepted for claude, moonshot, zhipu, and bigmodel."
        )
        print("ERROR OUTPUT:")
        print(message)
        return {
            "jd_file": str(jd_file),
            "return_code": 1,
            "stdout": "",
            "stderr": message
        }

    result = subprocess.run(
        command,
        cwd=str(CAREER_OPS_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    print(result.stdout)

    if result.stderr:
        print("ERROR OUTPUT:")
        print(result.stderr)

    return {
        "jd_file": str(jd_file),
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def run_tracker_merge():
    command = [
        "node",
        "merge-tracker.mjs",
    ]

    result = subprocess.run(
        command,
        cwd=str(CAREER_OPS_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print("TRACKER MERGE ERROR OUTPUT:")
        print(result.stderr)

    if result.returncode != 0:
        print("Tracker merge failed.")
    else:
        print("Tracker merge completed.")

    return result.returncode

def generate_single_executive_report(report_path, cv_path=None, force=False):
    report_path = Path(report_path)

    if not report_path.is_absolute():
        report_path = CAREER_OPS_ROOT / report_path

    if cv_path is None:
        cv_path = CAREER_OPS_ROOT / "cv.md"

    output_path = (
        CAREER_OPS_ROOT
        / "data"
        / "cv_optimization"
        / "reports"
        / f"{report_path.stem}-executive-report.docx"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "tools/generate_executive_report_from_evaluation.py",
        "--report",
        str(report_path),
        "--cv",
        str(cv_path),
        "--output",
        str(output_path)
    ]

    if force:
        command.append("--force")

    result = subprocess.run(
        command,
        cwd=str(CAREER_OPS_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        error = result.stderr or result.stdout or "Unknown DOCX generation error."
        raise RuntimeError(error.strip())

    output_match = re.search(
        r"Executive DOCX path:\s*(.+)",
        result.stdout
    )
    output_path = output_match.group(1).strip() if output_match else ""

    print("executive report generation completed.")
    if output_path:
        print(f"Executive DOCX path: {output_path}")

    return output_path


def evaluate_all_jd_files(jd_files=None):
    if jd_files is None:
        jd_files = get_jd_files()
    else:
        jd_files = list(jd_files)

    if not jd_files:
        print("No JD markdown files found.")
        return []

    state = load_processed_state()
    evaluated_files = set(state.get("evaluated_jd_files", []))
    rejected_files = set(state.get("rejected_jd_files", []))

    files_to_evaluate = []
    already_evaluated_count = 0
    unusable_count = 0

    for jd_file in jd_files:

        if jd_file.name in evaluated_files:
            already_evaluated_count += 1
            continue

        if jd_file.name in rejected_files:
            unusable_count += 1
            continue

        if not is_evaluable_jd_file(jd_file):
            rejected_files.add(jd_file.name)
            unusable_count += 1
            continue

        files_to_evaluate.append(jd_file)

    state["rejected_jd_files"] = list(rejected_files)
    save_processed_state(state)

    print(f"New JD files to evaluate: {len(files_to_evaluate)}")
    if already_evaluated_count:
        print(f"Previously evaluated JD files skipped: {already_evaluated_count}")
    if unusable_count:
        print(f"Blocked or unusable JD files skipped: {unusable_count}")

    results = []
    current_run_reports = []

    for jd_file in files_to_evaluate:

        try:
            result = run_career_ops_evaluation(jd_file)

            results.append(result)
            report_path = extract_saved_report_path(result.get("stdout", ""))

            if result.get("return_code") != 0 or not report_path:
                print(f"Evaluation did not produce a valid report for: {jd_file.name}")
                failure_count, failure_path = record_evaluation_failure(
                    state,
                    jd_file,
                    result,
                    report_path,
                )
                print(
                    f"Evaluation failure count for {jd_file.name}: "
                    f"{failure_count}/{MAX_EVALUATION_FAILURES}"
                )
                if failure_path:
                    rejected_files.add(jd_file.name)
                    state["rejected_jd_files"] = list(rejected_files)
                    print(f"Evaluation failure logged for manual review: {failure_path}")
                save_processed_state(state)
                continue

            current_run_reports.append(report_path)

            try:
                generate_single_executive_report(report_path)
            except Exception as e:
                print(f"Executive DOCX generation failed for: {report_path}")
                print(str(e))

            state.setdefault("evaluation_failures", {}).pop(jd_file.name, None)
            evaluated_files.add(jd_file.name)

            state["evaluated_jd_files"] = list(evaluated_files)

            save_processed_state(state)

            print(f"Saved evaluation state: {jd_file.name}")
        except Exception as e:

            print(f"Evaluation failed for {jd_file.name}")
            print(str(e))

        print("\n================================")
    print("Career-ops evaluation completed.")
    print(f"New JD files evaluated: {len(results)}")
    print(f"Reports saved in: {CAREER_OPS_REPORTS}")
    save_current_run_reports(current_run_reports)
    if current_run_reports:
        run_tracker_merge()
    return results

if __name__ == "__main__":
    export_jobs_to_markdown()
    evaluate_all_jd_files()

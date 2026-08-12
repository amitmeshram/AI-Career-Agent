from pathlib import Path
import yaml
import re

ROOT = Path(__file__).resolve().parents[1]

REPORTS_DIR = ROOT / "reports"

OUTPUT_DIR = ROOT / "data" / "tailoring_intelligence"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def read_text(path):
    return path.read_text(encoding="utf-8", errors="ignore")

def extract_metadata(report_text):

    metadata = {}

    company_match = re.search(r'"company":\s*"(.*?)"', report_text)
    role_match = re.search(r'"role":\s*"(.*?)"', report_text)
    score_match = re.search(r'"score":\s*(.*?),', report_text)
    recommendation_match = re.search(r'"recommendation":\s*"(.*?)"', report_text)

    metadata["company"] = company_match.group(1) if company_match else ""
    metadata["role"] = role_match.group(1) if role_match else ""
    metadata["score"] = score_match.group(1) if score_match else ""
    metadata["recommendation"] = (
        recommendation_match.group(1)
        if recommendation_match else ""
    )

    return metadata

def extract_personalization_changes(report_text):

    changes = []

    capture = False

    for line in report_text.splitlines():

        if "## E) Personalization Plan" in line:
            capture = True
            continue

        if capture and line.startswith("## "):
            break

        if capture and "|" in line:

            clean_line = line.strip()

            if "Proposed change" in clean_line:
                continue

            if "---" in clean_line:
                continue

            changes.append(clean_line)

    return changes

def parse_personalization_rows(rows):
    parsed_changes = []

    for row in rows:
        parts = [part.strip() for part in row.strip("|").split("|")]

        if len(parts) >= 5:
            parsed_changes.append({
                "number": parts[0],
                "section": parts[1],
                "current_state": parts[2],
                "proposed_change": parts[3],
                "reason": parts[4]
            })

    return parsed_changes

def build_tailoring_intelligence(report_text):

    metadata = extract_metadata(report_text)

    personalization_changes = extract_personalization_changes(report_text)

    intelligence = {

        "target_role": metadata.get("role"),

        "company": metadata.get("company"),

        "score": metadata.get("score"),

        "recommendation": metadata.get("recommendation"),

        "personalization_changes": parse_personalization_rows(personalization_changes)
    }

    return intelligence

def save_output(intelligence, source_report):

    output_path = OUTPUT_DIR / f"{source_report.stem}.yml"

    with open(output_path, "w", encoding="utf-8") as file:
        yaml.safe_dump(intelligence, file, sort_keys=False, allow_unicode=True)

    print(f"Tailoring intelligence created: {output_path}")

def main():

    report_files = sorted(REPORTS_DIR.glob("*.md"))

    if not report_files:
        print("No reports found.")
        return

    latest_report = report_files[-1]

    print(f"Using report: {latest_report.name}")

    report_text = read_text(latest_report)

    intelligence = build_tailoring_intelligence(report_text)

    save_output(intelligence, latest_report)

if __name__ == "__main__":
    main()
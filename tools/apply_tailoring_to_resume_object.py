from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

RESUME_OBJECT_PATH = ROOT / "data" / "resume_objects" / "resume_object.yml"
TAILORING_DIR = ROOT / "data" / "tailoring_intelligence"
OUTPUT_PATH = ROOT / "data" / "resume_objects" / "tailored_resume_object.yml"

def read_yaml(path):
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}

def get_latest_tailoring_file():
    files = sorted(TAILORING_DIR.glob("*.yml"))

    if not files:
        raise FileNotFoundError("No tailoring intelligence files found.")

    return files[-1]

def split_changes(changes):
    cv_changes = []
    linkedin_changes = []
    cover_letter_changes = []
    other_changes = []

    for change in changes:
        section = str(change.get("section", "")).lower()

        if "linkedin" in section:
            linkedin_changes.append(change)
        elif "cover letter" in section:
            cover_letter_changes.append(change)
        elif section in [
            "professional summary",
            "core positioning",
            "experience – landmark arabia",
            "experience - landmark arabia",
            "skills",
            "certifications"
        ]:
            cv_changes.append(change)
        else:
            other_changes.append(change)

    return cv_changes, linkedin_changes, cover_letter_changes, other_changes

def build_tailored_resume_object(resume_object, tailoring_intelligence):
    changes = tailoring_intelligence.get("personalization_changes", [])

    cv_changes, linkedin_changes, cover_letter_changes, other_changes = split_changes(changes)

    resume_object["tailoring_context"] = {
        "company": tailoring_intelligence.get("company"),
        "target_role": tailoring_intelligence.get("target_role"),
        "score": tailoring_intelligence.get("score"),
        "recommendation": tailoring_intelligence.get("recommendation"),
    }

    resume_object["tailoring_instructions"] = {
        "cv_changes": cv_changes,
        "linkedin_changes": linkedin_changes,
        "cover_letter_changes": cover_letter_changes,
        "other_changes": other_changes,
    }

    return resume_object

def save_yaml(data, path):
    with open(path, "w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, sort_keys=False, allow_unicode=True)

def main():
    resume_object = read_yaml(RESUME_OBJECT_PATH)

    latest_tailoring_file = get_latest_tailoring_file()

    print(f"Using tailoring file: {latest_tailoring_file.name}")

    tailoring_intelligence = read_yaml(latest_tailoring_file)

    tailored_resume_object = build_tailored_resume_object(
        resume_object,
        tailoring_intelligence
    )

    save_yaml(tailored_resume_object, OUTPUT_PATH)

    print(f"Tailored resume object created: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
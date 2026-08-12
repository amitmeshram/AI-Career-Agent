from pathlib import Path
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]

MASTER_PROFILE_PATH = ROOT / "config" / "master_profile.yml"
TEMP_SECTION_DIR = ROOT / "data" / "profile_reviews" / "temp_sections"

def load_master_profile():
    with open(MASTER_PROFILE_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def save_master_profile(profile):
    with open(MASTER_PROFILE_PATH, "w", encoding="utf-8") as file:
        yaml.safe_dump(profile, file, sort_keys=False, allow_unicode=True)

def get_next_pending_section(profile):
    for section_name, section_data in profile.items():

        if isinstance(section_data, dict):

            if section_data.get("review_status") == "pending":
                return section_name

    return None

def show_section(profile, section_name):

    print("\n====================")
    print(f"SECTION: {section_name}")
    print("====================\n")

    section_data = profile[section_name].copy()

    if section_name == "career_history":

        if "data" in section_data:
            section_data["data"] = section_data["data"].copy()

            section_data["data"].pop("raw_extracted_text", None)

    print(yaml.dump(section_data, sort_keys=False, allow_unicode=True))

def approve_section(profile, section_name):

    profile[section_name]["review_status"] = "approved"

    save_master_profile(profile)

    print(f"\nSection '{section_name}' approved.\n")

def get_editing_guide(section_name):

    templates = {

        "certifications": """
# Replace values only
# Do NOT remove ':' or '-'

items:
  - name: Enter certification name
    provider: Enter provider
    status: Completed
    year: 2025

review_status: pending
""",

        "major_projects": """
# Replace values only
# Do NOT remove ':' or '-'

items:
  - name: Enter project name
    domain: Enter domain
    technologies:
      - Technology 1
      - Technology 2
    impact:
      - Impact 1
      - Impact 2

review_status: pending
""",

        "achievements": """
# Replace values only
# Do NOT remove ':' or '-'

items:
  - title: Enter achievement title
    impact: Enter measurable impact
    metric: Enter metric

review_status: pending
""",

        "default": """
# Replace values only
# Do NOT remove ':' or '-'

items:
  - name:

review_status: pending
"""
    }

    return templates.get(section_name, templates["default"])

def edit_section(profile, section_name):
    TEMP_SECTION_DIR.mkdir(parents=True, exist_ok=True)

    temp_file = TEMP_SECTION_DIR / f"{section_name}.yml"

    with open(temp_file, "w", encoding="utf-8") as file:

        section_data = profile[section_name].copy()

        if section_name == "career_history":
            if "data" in section_data:
                section_data["data"] = section_data["data"].copy()
                section_data["data"].pop("raw_extracted_text", None)

        is_empty = (
            isinstance(section_data, dict)
            and section_data.get("items") == []
        )

        if is_empty:
            file.write(get_editing_guide(section_name))
        else:
            yaml.safe_dump(section_data, file, sort_keys=False, allow_unicode=True)

    print(f"\nOpening section in Notepad: {temp_file}")
    print("Edit, save, and close Notepad to continue.\n")

    subprocess.run(["notepad.exe", str(temp_file)])

    with open(temp_file, "r", encoding="utf-8") as file:
        edited_section = yaml.safe_load(file)

    if edited_section is None:
        print("\nNo valid YAML data found. Section was not updated.\n")
        return
    
    if section_name == "career_history":
        original_raw_text = profile[section_name].get("data", {}).get("raw_extracted_text")

        if original_raw_text:
            edited_section.setdefault("data", {})
            edited_section["data"]["raw_extracted_text"] = original_raw_text

    edited_section["review_status"] = "pending"
    profile[section_name] = edited_section

    save_master_profile(profile)

    print(f"\nSection '{section_name}' updated and saved back to master_profile.yml.\n")

def main():

    profile = load_master_profile()

    while True:

        next_section = get_next_pending_section(profile)

        if not next_section:
            print("\nAll sections reviewed.\n")
            break

        show_section(profile, next_section)

        action = input("\nApprove this section? (yes/no/exit): ")

        if action.lower() == "yes":

            approve_section(profile, next_section)

            profile = load_master_profile()

        elif action.lower() == "exit":

            print("\nReview session ended.\n")

            break

        else:
            edit_section(profile, next_section)
            profile = load_master_profile()

if __name__ == "__main__":
    main()
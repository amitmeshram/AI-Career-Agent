from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

TAILORED_RESUME_OBJECT_PATH = (
    ROOT / "data" / "resume_objects" / "tailored_resume_object.yml"
)

OUTPUT_DIR = ROOT / "data" / "tailored_cvs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def read_yaml(path):
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}

def get_summary_tailoring_phrases(resume_object):

    changes = (
        resume_object
        .get("tailoring_instructions", {})
        .get("cv_changes", [])
    )

    phrases = []

    for change in changes:

        section = str(change.get("section", "")).lower()

        if "professional summary" in section:

            proposed_change = change.get(
                "proposed_change",
                ""
            )

            phrases.append(
                clean_tailoring_phrase(proposed_change)
            )

    return phrases

def clean_tailoring_phrase(text):

    text = str(text)

    replacements = [
        "Add ",
        "Insert ",
        "phrase",
        '"',
        "“",
        "”"
    ]

    for item in replacements:
        text = text.replace(item, "")

    return text.strip()

def get_skill_tailoring_phrases(resume_object):

    changes = (
        resume_object
        .get("tailoring_instructions", {})
        .get("cv_changes", [])
    )

    skills = []

    for change in changes:

        section = str(change.get("section", "")).lower()

        if "skills" in section:

            proposed_change = change.get(
                "proposed_change",
                ""
            )

            cleaned = clean_tailoring_phrase(
                proposed_change
            )

            skills.append(cleaned)

    return skills

def build_professional_summary(resume_object):

    target_role = (
        resume_object
        .get("tailoring_context", {})
        .get("target_role", "")
    )

    profile = resume_object.get("profile", {})
    total_experience = profile.get("total_experience", "10+ years")

    tailoring_phrases = get_summary_tailoring_phrases(resume_object)

    tailoring_text = ""

    if tailoring_phrases:
        tailoring_text = " ".join(tailoring_phrases)

    return (
        f"{target_role} candidate with {total_experience} of experience across "
        f"strategy execution, business transformation, retail analytics, "
        f"digital adoption, stakeholder management, and performance improvement. "
        f"{tailoring_text}"
    )


def build_skills_section(resume_object):
    
    tailored_skills = get_skill_tailoring_phrases(
    resume_object
    )
    skills = resume_object.get("skills", {})

    lines = []

    for category, items in skills.items():

        if items:
            lines.append(
                f"- {category.title()}: {', '.join(items)}"
            )

    if tailored_skills:

        lines.append(
            "- Tailored Skills: "
            + ", ".join(tailored_skills)
        )

    return "\n".join(lines)

def build_experience_section(resume_object):

    career_history = resume_object.get("career_history", [])

    lines = []

    for role in career_history:

        lines.append(
            f"## {role.get('company')} — {role.get('title')}"
        )

        lines.append(
            f"**{role.get('location')} | {role.get('duration')}**\n"
        )

        achievements = role.get("achievements", [])

        responsibilities = role.get("responsibilities", [])

        for bullet in achievements[:4]:
            lines.append(f"- {bullet}")

        for bullet in responsibilities[:2]:
            lines.append(f"- {bullet}")

        lines.append("")

    return "\n".join(lines)

def build_projects_section(resume_object):

    projects = resume_object.get("major_projects", [])

    if not projects:
        return ""

    lines = ["# Major Projects\n"]

    for project in projects[:5]:

        lines.append(
            f"- **{project.get('name')}** "
            f"({project.get('source_company')})"
        )

    return "\n".join(lines)

def build_achievements_section(resume_object):

    achievements = resume_object.get("achievements", [])

    if not achievements:
        return ""

    lines = ["# Key Achievements\n"]

    for achievement in achievements[:8]:

        lines.append(
            f"- {achievement.get('title')}"
        )

    return "\n".join(lines)

def build_tailoring_notes(resume_object):

    tailoring = (
        resume_object
        .get("tailoring_instructions", {})
        .get("cv_changes", [])
    )

    if not tailoring:
        return ""

    lines = ["# Tailoring Notes\n"]

    for item in tailoring:

        lines.append(
            f"- [{item.get('section')}] "
            f"{item.get('proposed_change')}"
        )

    return "\n".join(lines)

def generate_cv_markdown(resume_object):

    profile = resume_object.get("profile", {})

    name = profile.get("name", "Candidate")

    target_role = (
        resume_object
        .get("tailoring_context", {})
        .get("target_role", "")
    )

    sections = [

        f"# {name}\n",

        f"## Target Role\n{target_role}\n",

        "## Professional Summary\n",
        build_professional_summary(resume_object),
        "",

        "## Skills\n",
        build_skills_section(resume_object),
        "",

        "## Professional Experience\n",
        build_experience_section(resume_object),
        "",

        build_projects_section(resume_object),
        "",

        build_achievements_section(resume_object),
        "",

        #build_tailoring_notes(resume_object)
    ]

    return "\n".join(sections)

def save_cv(content, resume_object):

    company = (
        resume_object
        .get("tailoring_context", {})
        .get("company", "company")
    )

    target_role = (
        resume_object
        .get("tailoring_context", {})
        .get("target_role", "role")
    )

    safe_name = (
        f"{company}_{target_role}"
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
    )

    output_path = OUTPUT_DIR / f"{safe_name}_tailored_cv.md"

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(content)

    print(f"Tailored CV created: {output_path}")

def main():

    resume_object = read_yaml(TAILORED_RESUME_OBJECT_PATH)

    markdown_content = generate_cv_markdown(resume_object)

    save_cv(markdown_content, resume_object)

if __name__ == "__main__":
    main()
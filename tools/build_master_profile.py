from pathlib import Path
import yaml
import re

ROOT = Path(__file__).resolve().parents[1]

CV_PATH = ROOT / "cv.md"
PROFILE_PATH = ROOT / "config" / "profile.yml"
MASTER_PROFILE_PATH = ROOT / "config" / "master_profile.yml"
SKILL_TAXONOMY_PATH = ROOT / "config" / "skill_taxonomy.yml"

def read_text(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")

def read_yaml(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}

def get_existing_review_status(section_name, default="pending"):
    existing_profile = read_yaml(MASTER_PROFILE_PATH)

    section = existing_profile.get(section_name, {})

    if isinstance(section, dict):
        return section.get("review_status", default)

    return default

def extract_tools(cv_text):
    known_tools = [
        "Power BI",
        "SQL",
        "Python",
        "R",
        "Excel",
        "Oracle BI",
        "n8n",
        "Playwright",
        "FastAPI",
        "React",
        "Laravel",
        "Git",
        "Docker",
        "ChatGPT",
        "DALL-E"
    ]

    found_tools = []

    for tool in known_tools:
        if tool.lower() in cv_text.lower():
            found_tools.append(tool)

    return sorted(list(set(found_tools)))

def extract_skills(cv_text):
    skill_map = read_yaml(SKILL_TAXONOMY_PATH)

    extracted_skills = {}

    for category, skills in skill_map.items():
        found = []

        for skill in skills:
            if skill.lower() in cv_text.lower():
                found.append(skill)

        extracted_skills[category] = sorted(list(set(found)))

    return extracted_skills


def structure_roles_from_experience(experience_text):
    roles = []

    pattern = r"##\s+(.*?)\s+—\s+(.*?)\s*\n\*\*(.*?)\s+\|\s+(.*?)\*\*"
    matches = list(re.finditer(pattern, experience_text))

    for index, match in enumerate(matches):
        company = match.group(1).strip()
        title = match.group(2).strip()
        location = match.group(3).strip()
        duration = match.group(4).strip()

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(experience_text)

        role_block = experience_text[start:end]

        bullets = []
        for line in role_block.splitlines():
            clean_line = line.strip()
            if clean_line.startswith("- "):
                bullets.append(clean_line[2:].strip())

        achievements = []
        responsibilities = []

        achievement_keywords = [
            "achieved",
            "reduced",
            "increased",
            "improved",
            "secured",
            "delivered",
            "%",
            "approval",
            "contribution"
        ]

        for bullet in bullets:
            if any(keyword.lower() in bullet.lower() for keyword in achievement_keywords):
                achievements.append(bullet)
            else:
                responsibilities.append(bullet)

        roles.append({
            "company": company,
            "title": title,
            "duration": duration,
            "location": location,
            "responsibilities": responsibilities,
            "achievements": achievements
        })

    return roles


def extract_career_history(cv_text):

    lines = cv_text.splitlines()

    extracted_lines = []

    capture = False

    stop_keywords = [
        "## Selected Business Impact",
        "## Strategy, PMO, and Transformation Capabilities",
        "## Analytics and Technical Skills",
        "## Functional Skills",
        "## Education"
    ]

    for line in lines:

        clean_line = line.strip()

        if "## Professional Experience" in clean_line:
            capture = True
            continue

        if capture:

            if any(keyword in clean_line for keyword in stop_keywords):
                break

            extracted_lines.append(line)
    experience_text = "\n".join(extracted_lines).strip()
    structured_roles = structure_roles_from_experience(experience_text)
    return {
        "raw_extracted_text": experience_text,

        "structured_items": structured_roles
    }

def generate_short_title(text):
    separators = [
        " through ",
        " by ",
        " using ",
        " with "
    ]

    for separator in separators:
        if separator in text.lower():
            split_text = text.split(separator, 1)[0]
            return split_text.strip()

    return text.strip()

def extract_major_projects(career_history_data):
    projects = []

    for role in career_history_data.get("structured_items", []):
        for achievement in role.get("achievements", []):
            projects.append({
                "name": generate_short_title(achievement),
                "source_company": role.get("company"),
                "source_role": role.get("title"),
                "evidence": achievement,
                "review_status": "pending"
            })

    return projects

def extract_achievements(career_history_data):
    achievements = []

    for role in career_history_data.get("structured_items", []):
        for achievement in role.get("achievements", []):
            achievements.append({
                "title": generate_short_title(achievement),
                "source_company": role.get("company"),
                "source_role": role.get("title"),
                "evidence": achievement,
                "review_status": "pending"
            })

    return achievements

def build_master_profile():
    cv_text = read_text(CV_PATH)
    profile_data = read_yaml(PROFILE_PATH)
    skills_data = extract_skills(cv_text)
    existing_master_profile = read_yaml(MASTER_PROFILE_PATH)

    def review_status(section_name):
        section = existing_master_profile.get(section_name, {})
        if isinstance(section, dict):
            return section.get("review_status", "pending")
        return "pending"
    career_history_data = extract_career_history(cv_text)
    major_projects_data = extract_major_projects(career_history_data)
    achievements_data = extract_achievements(career_history_data)

    master_profile = {
        "schema_version": "1.0",

        "profile": {
            "source": "profile.yml",
            "data": profile_data,
            "review_status": review_status("profile")
        },

        "extracted_skills": {
            "source": "cv.md",
            "extraction_method": "deterministic_taxonomy_match",
            "confidence": "medium",

            "data": {
                "business": skills_data["business"],
                "analytics": skills_data["analytics"],
                "ai": skills_data["ai"],
                "strategy": skills_data["strategy"],
                "operations": skills_data["operations"],
            },

            "review_status": review_status("extracted_skills")
        },

        "career_history": {
            "source": "cv.md",
            "extraction_method": "keyword_section_capture",
            "confidence": "low",
            "data": career_history_data,
            "review_status": review_status("career_history")
        },

        "major_projects": {
            "source": "career_history.achievements",
            "extraction_method": "achievement_to_project_candidate",
            "confidence": "medium",
            "items": major_projects_data,
            "review_status": review_status("major_projects")
        },

        "achievements": {
            "source": "career_history.achievements",
            "extraction_method": "achievement_bullet_extraction",
            "confidence": "medium",
            "items": achievements_data,
            "review_status": review_status("achievements")
        },

        "tools": {
            "items": extract_tools(cv_text),
            "review_status": review_status("tools")
        },

        "certifications": {
            "items": [],
            "review_status": review_status("certifications")
        },

        "domains": {
            "items": [],
            "review_status": review_status("domains")
        },

        "leadership_examples": {
            "items": [],
            "review_status": review_status("leadership_examples")
        },

        "source_documents": {
            "cv_md": str(CV_PATH),
            "profile_yml": str(PROFILE_PATH)
        },

        "raw_cv_text": cv_text,

        "extraction_status": {
            "status": "draft",
            "reviewed_by_user": False,
            "finalized": False
        }
    }

    with open(MASTER_PROFILE_PATH, "w", encoding="utf-8") as file:
        yaml.safe_dump(master_profile, file, sort_keys=False, allow_unicode=True)

    print(f"Structured draft master profile created: {MASTER_PROFILE_PATH}")

if __name__ == "__main__":
    build_master_profile()
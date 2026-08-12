from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

MASTER_PROFILE_PATH = ROOT / "config" / "master_profile.yml"
OUTPUT_DIR = ROOT / "data" / "resume_objects"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_master_profile():
    with open(MASTER_PROFILE_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def build_resume_object(master_profile, target_role, final_keywords_input):

    profile = master_profile.get("profile", {}).get("data", {})

    extracted_skills = master_profile.get("extracted_skills", {}).get("data", {})

    career_history = (
        master_profile
        .get("career_history", {})
        .get("data", {})
        .get("structured_items", [])
    )

    achievements = master_profile.get("achievements", {}).get("items", [])

    major_projects = master_profile.get("major_projects", {}).get("items", [])

    tools = master_profile.get("tools", {}).get("items", [])
    role_keywords = extract_keywords_from_target_role(target_role)

    additional_keywords = extract_keywords_from_user_input(final_keywords_input)

    target_keywords = sorted(
        list(set(role_keywords + additional_keywords))
    )

    filtered_achievements = filter_items_by_role(achievements, target_keywords, top_n=8)
    filtered_projects = filter_items_by_role(major_projects, target_keywords, top_n=5)
    filtered_career_history = filter_items_by_role(career_history, target_keywords, top_n=3)

    resume_object = {

        "target_role": target_role,
        "target_keywords": target_keywords,

        "profile": {
            "name": profile.get("candidate", {}).get("full_name"),
            "email": profile.get("candidate", {}).get("email"),
            "phone": profile.get("candidate", {}).get("phone"),
            "location": profile.get("candidate", {}).get("location"),
            "linkedin": profile.get("candidate", {}).get("linkedin"),
            "current_title": profile.get("narrative", {}).get("headline"),
            "total_experience": "10+ years"
        },

        "skills": extracted_skills,

        "career_history": filtered_career_history,
        "major_projects": filtered_projects,
        "achievements": filtered_achievements,

        "tools": tools
    }

    return resume_object


def save_resume_object(resume_object):

    output_path = OUTPUT_DIR / "resume_object.yml"

    with open(output_path, "w", encoding="utf-8") as file:
        yaml.safe_dump(resume_object, file, sort_keys=False, allow_unicode=True)

    print(f"Resume object created: {output_path}")

def extract_keywords_from_target_role(target_role):
    stop_words = {
        "and", "or", "of", "the", "for", "to", "in", "with",
        "manager", "lead", "senior", "executive", "specialist"
    }

    words = target_role.replace("/", " ").replace("-", " ").split()

    keywords = []

    for word in words:
        clean_word = word.strip().lower()

        if clean_word and clean_word not in stop_words:
            keywords.append(clean_word)

    return sorted(list(set(keywords)))

def extract_keywords_from_user_input(user_input):

    separators = [",", "/", "|"]

    cleaned_input = user_input

    for separator in separators:
        cleaned_input = cleaned_input.replace(separator, " ")

    keywords = []

    for word in cleaned_input.split():

        clean_word = word.strip().lower()

        if clean_word:
            keywords.append(clean_word)

    return sorted(list(set(keywords)))


def suggest_keywords_from_profile(profile_data, target_role):
    keywords = extract_keywords_from_target_role(target_role)

    preferred_functions = (
        profile_data
        .get("role_preferences", {})
        .get("preferred_functions", [])
    )

    functional_skills = (
        profile_data
        .get("skills", {})
        .get("functional", [])
    )

    technical_skills = (
        profile_data
        .get("skills", {})
        .get("technical", [])
    )

    for item in preferred_functions + functional_skills + technical_skills:
        for word in str(item).replace("/", " ").replace("-", " ").split():
            clean_word = word.strip().lower()
            if clean_word:
                keywords.append(clean_word)

    return sorted(list(set(keywords)))

def relevance_score(text, keywords):
    text = str(text).lower()
    score = 0

    for keyword in keywords:
        if keyword in text:
            score += 1

    return score

def filter_items_by_role(items, keywords, top_n=8):
    scored_items = []

    for item in items:
        item_text = yaml.safe_dump(item, sort_keys=False, allow_unicode=True)
        score = relevance_score(item_text, keywords)

        scored_items.append({
            "score": score,
            "item": item
        })

    scored_items = sorted(scored_items, key=lambda x: x["score"], reverse=True)

    return [entry["item"] for entry in scored_items[:top_n]]

def main():

    master_profile = load_master_profile()

    target_role = input("Enter target role: ")

    profile_data = master_profile.get("profile", {}).get("data", {})

    suggested_keywords = suggest_keywords_from_profile(profile_data, target_role)

    print("\nSuggested keywords:")
    print(", ".join(suggested_keywords))

    extra_keywords = input(
        "\nPress Enter to accept, or type modified/additional keywords: "
    )

    if extra_keywords.strip():
        final_keywords_input = extra_keywords
    else:
        final_keywords_input = ", ".join(suggested_keywords)

    resume_object = build_resume_object(
        master_profile,
        target_role,
        final_keywords_input
    )

    save_resume_object(resume_object)

if __name__ == "__main__":
    main()
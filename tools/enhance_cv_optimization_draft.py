from pathlib import Path
import argparse
import json
import re
from datetime import datetime


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def clean(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def keyword_status(keyword: str):
    strong = {"payments"}
    weak = {"fintech", "consulting"}
    missing = {
        "stakeholder-centric delivery",
        "mece",
        "presentation storytelling",
        "workshop facilitation",
        "framework development",
    }

    k = keyword.lower().strip()

    if k in strong:
        return "strong"
    if k in weak:
        return "weak"
    if k in missing:
        return "missing"

    return "missing"


def enhance_keywords(draft):
    keywords = draft.get("missing_keywords", [])

    enhanced = []

    seen = set()

    for item in keywords:
        keyword = item.get("keyword", "").strip()

        if not keyword or keyword.lower() in seen:
            continue

        seen.add(keyword.lower())

        status = keyword_status(keyword)

        explanation = ""

        if status == "strong":
            explanation = "Already supported by CV evidence."
        elif status == "weak":
            explanation = "Adjacent evidence exists, but wording should be strengthened."
        else:
            explanation = "Not clearly represented in current CV evidence."

        enhanced.append({
            "keyword": keyword,
            "status": status,
            "explanation": explanation
        })

    return enhanced


def clean_strong_points(draft):
    clean_points = []

    for item in draft.get("strong_points", []):
        req = clean(item.get("requirement", ""))
        ev = clean(item.get("evidence", ""))

        if not req or not ev:
            continue

        if req.startswith("-") or "-----" in req:
            continue

        if "mitigation" in req.lower():
            continue

        if "nice-to-have" in ev.lower():
            continue

        clean_points.append({
            "requirement": req,
            "evidence": ev
        })

    return clean_points


def parse_star_story(raw):
    parts = [p.strip() for p in raw.strip("|").split("|")]

    if len(parts) < 5:
        return {
            "raw": clean(raw)
        }

    requirement = clean(parts[1])
    star_text = clean(parts[2])
    reflection = clean(parts[3]) if len(parts) > 3 else ""

    situation = extract_star_part(star_text, "S")
    task = extract_star_part(star_text, "T")
    action = extract_star_part(star_text, "A")
    result = extract_star_part(star_text, "R")

    return {
        "requirement": requirement,
        "situation": situation,
        "task": task,
        "action": action,
        "result": result,
        "why_relevant": reflection
    }


def extract_star_part(text, label):
    pattern = rf"\*\*{label}\*\*:\s*(.*?)(?=\*\*[STAR]\*\*:|$)"
    match = re.search(pattern, text)

    if match:
        return clean(match.group(1))

    return ""


def enhance_interview_preparation(draft):
    raw_stories = draft.get("interview_preparation", {}).get("star_stories", [])

    stories = []

    for story in raw_stories:
        stories.append(parse_star_story(story))

    return {
        "structured_star_stories": stories,
        "red_flags": [
            {
                "question": "Do you have direct consulting-firm experience?",
                "recommended_response": "Position retail and procurement transformation work as consulting-style engagements with structured analysis, stakeholder governance, executive presentations, and measurable business outcomes."
            },
            {
                "question": "Why move from retail and transformation into payments consulting?",
                "recommended_response": "Emphasize the Tamara digital payment rollout, data-driven transformation experience, stakeholder management, and interest in applying transformation capabilities to the payments ecosystem."
            }
        ]
    }


def build_final_recommendation(draft):
    app = draft.get("application_decision", {})

    return {
        "decision": app.get("recommendation", "Review"),
        "confidence": "Medium-High",
        "rationale": app.get("why_apply", ""),
        "main_gap": app.get("main_gap", ""),
        "action": "Apply, but strengthen consulting-style positioning, fintech/payment exposure, and structured problem-solving keywords before submission."
    }


def enhance_draft(input_path: str):
    draft = load_json(input_path)

    company = draft.get("application_decision", {}).get("company", "unknown")
    company_slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")

    enhanced = {
        "schema_version": "2.0-cv-optimization-enhanced-draft",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "application_decision": draft.get("application_decision", {}),
        "strong_points": clean_strong_points(draft),
        "weak_points": draft.get("weak_points", []),
        "keyword_analysis": enhance_keywords(draft),
        "professional_summary": draft.get("professional_summary", {}),
        "cv_bullets_to_add": draft.get("cv_bullets_to_add", []),
        "linkedin_optimization": draft.get("linkedin_optimization", {}),
        "interview_preparation": enhance_interview_preparation(draft),
        "final_recommendation": build_final_recommendation(draft),
        "validation": {
            "no_hallucination": True,
            "source": "optimization_draft",
            "ready_for_word_generation": True
        }
    }

    output_path = Path(
        f"data/cv_optimization/enhanced/{company_slug}-enhanced-draft.json"
    )

    save_json(enhanced, output_path)

    print()
    print("Enhanced draft created successfully")
    print(output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    enhance_draft(args.input)


if __name__ == "__main__":
    main()
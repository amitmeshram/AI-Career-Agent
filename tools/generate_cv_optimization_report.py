from pathlib import Path
import argparse
import json
import re
from datetime import datetime


# ============================================================
# Utility Functions
# ============================================================

def read_text_file(path: str) -> str:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return file_path.read_text(encoding="utf-8", errors="ignore")


def clean_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.strip())


def safe_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:120]


def is_usable_metadata_value(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(normalized) and normalized not in {
        "unknown",
        "unknown company",
        "unknown-company",
        "unknown role",
        "unknown-role",
    }


# ============================================================
# Metadata Extraction
# ============================================================

def extract_json_metadata(report_text: str) -> dict:
    """
    Tries to extract JSON metadata from the evaluation report.
    Supports reports where metadata is inside ```json blocks or where
    the report starts with a raw JSON metadata object.
    """

    decoder = json.JSONDecoder()
    stripped = report_text.lstrip()
    if stripped.startswith("{"):
        try:
            data, _ = decoder.raw_decode(stripped)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    json_blocks = re.findall(
        r"```json\s*(\{.*?\})\s*```",
        report_text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for block in json_blocks:
        try:
            data = json.loads(block)

            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            continue

    return {}


def extract_markdown_field(report_text: str, field_name: str) -> str:
    """
    Extracts simple markdown fields like:
    **Company:** Mastercard
    **Score:** 4.2/5
    """

    pattern = rf"\*\*{re.escape(field_name)}:\*\*\s*(.+)"
    match = re.search(pattern, report_text, flags=re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return ""


def extract_basic_metadata(report_text: str) -> dict:
    """
    Combines JSON metadata and markdown field fallback.
    """

    metadata = extract_json_metadata(report_text)

    fallback = {
        "company": extract_markdown_field(report_text, "Company"),
        "role": extract_markdown_field(report_text, "Role"),
        "score": extract_markdown_field(report_text, "Score"),
        "recommendation": extract_markdown_field(report_text, "Recommendation"),
        "fit_type": extract_markdown_field(report_text, "Fit Type"),
        "seniority_match": extract_markdown_field(report_text, "Seniority Match"),
        "why_apply": extract_markdown_field(report_text, "Why Apply"),
        "main_gap": extract_markdown_field(report_text, "Main Gap"),
        "job_link": extract_markdown_field(report_text, "Job Link"),
        "location": extract_markdown_field(report_text, "Location"),
    }

    for key, value in fallback.items():
        if not is_usable_metadata_value(metadata.get(key)) and is_usable_metadata_value(value):
            metadata[key] = value

    return metadata


# ============================================================
# Markdown Section Extraction
# ============================================================

def normalize_heading_text(heading_text: str) -> str:
    heading_text = heading_text.strip()
    heading_text = re.sub(
        r"^(?:block|section)?\s*[A-Z]\s*(?:\)|[-–—:])\s*",
        "",
        heading_text,
        flags=re.IGNORECASE,
    )
    return heading_text.lower().strip()


def markdown_heading_level(line: str) -> int | None:
    match = re.match(r"^(#{1,6})\s+\S", line.strip())
    return len(match.group(1)) if match else None


def extract_section(report_text: str, possible_headings: list[str]) -> str:
    """
    Extracts content under markdown headings safely.
    Supports:
    ## B) Match with CV
    ## Match With CV
    # Gaps & Mitigation
    """

    headings = [normalize_heading_text(h) for h in possible_headings]

    lines = report_text.splitlines()
    start_index = None
    start_level = None

    for i, line in enumerate(lines):
        clean_line = line.strip()

        level = markdown_heading_level(clean_line)
        if level is None:
            continue

        heading_text = clean_line.lstrip("#").strip()

        heading_text_lower = normalize_heading_text(heading_text)

        if heading_text_lower in headings:
            start_index = i + 1
            start_level = level
            break

    if start_index is None:
        return ""

    end_index = len(lines)

    for j in range(start_index, len(lines)):
        level = markdown_heading_level(lines[j])
        if level is not None and level <= start_level:
            end_index = j
            break

    section_text = "\n".join(lines[start_index:end_index])

    return clean_text(section_text)

def extract_embedded_subsection(text: str, heading: str) -> str:
    """
    Extracts embedded bold subsection like:
    **Gaps & Mitigation**
    """

    pattern = rf"\*\*{re.escape(heading)}\*\*\s*(.*?)(?=\n\s*\*\*[A-Za-z].*?\*\*|\Z)"

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        return clean_text(match.group(1))

    return ""

def extract_evaluation_sections(report_text: str) -> dict:
    match_with_cv = extract_section(
        report_text,
        [
            "Match with CV",
            "Match With CV",
            "CV Match",
            "Fit With CV",
        ],
    )

    gaps_and_mitigation = extract_section(
        report_text,
        [
            "Gaps & Mitigation",
            "Gaps and Mitigation",
            "Weaknesses",
            "Gaps",
        ],
    )

    if not gaps_and_mitigation and match_with_cv:
        gaps_and_mitigation = extract_embedded_subsection(
            match_with_cv,
            "Gaps & Mitigation",
        )

    return {
        "role_summary": extract_section(
            report_text,
            [
                "Role Summary",
                "Resumen del Rol",
                "Job Summary",
                "Role Overview",
            ],
        ),
        "match_with_cv": match_with_cv,
        "gaps_and_mitigation": gaps_and_mitigation,
        "personalization_plan": extract_section(
            report_text,
            [
                "Personalization Plan",
                "Plan de Personalización",
                "Tailoring Plan",
                "CV Personalization Plan",
            ],
        ),
        "interview_plan": extract_section(
            report_text,
            [
                "Interview Plan",
                "Plan de Entrevistas",
                "Interview Preparation",
            ],
        ),
        "posting_legitimacy": extract_section(
            report_text,
            [
                "Posting Legitimacy",
                "Legitimacy Assessment",
                "Job Legitimacy",
            ],
        ),
        "ats_keywords": extract_section(
            report_text,
            [
                "Missing Keywords",
            ],
        ),
    }


# ============================================================
# CV Evidence Extraction
# ============================================================

def extract_cv_sections(cv_text: str) -> dict:
    """
    Extracts major sections from cv.md.
    """

    sections = {}

    matches = list(re.finditer(r"^##\s+(.+?)\s*$", cv_text, flags=re.MULTILINE))

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cv_text)

        sections[title] = clean_text(cv_text[start:end])

    return sections


def extract_professional_experience(cv_text: str) -> str:
    """Extracts the candidate's main experience section from common CV headings."""

    cv_sections = extract_cv_sections(cv_text)
    aliases = (
        "Professional Experience",
        "Work Experience",
        "Experience",
        "Employment History",
        "Career History",
    )
    normalized_sections = {
        normalize_heading_text(title): content
        for title, content in cv_sections.items()
    }
    for alias in aliases:
        content = normalized_sections.get(normalize_heading_text(alias))
        if content:
            return content

    return ""

def extract_cv_bullets(cv_text: str) -> list[str]:
    bullets = []

    for line in cv_text.splitlines():
        stripped = line.strip()

        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())

    return bullets


def extract_cv_skills(cv_sections: dict) -> dict:
    return {
        "analytics_and_technical_skills": cv_sections.get("Analytics and Technical Skills", ""),
        "functional_skills": cv_sections.get("Functional Skills", ""),
        "strategy_pmo_transformation_capabilities": cv_sections.get(
            "Strategy, PMO, and Transformation Capabilities", ""
        ),
        "core_positioning": cv_sections.get("Core Positioning", ""),
    }


def build_cv_evidence(cv_text: str) -> dict:
    cv_sections = extract_cv_sections(cv_text)

    return {
        "professional_summary": cv_sections.get("Professional Summary", ""),
        "core_positioning": cv_sections.get("Core Positioning", ""),
        "professional_experience": extract_professional_experience(cv_text),
        "selected_business_impact": cv_sections.get("Selected Business Impact", ""),
        "skills": extract_cv_skills(cv_sections),
        "education": cv_sections.get("Education", ""),
        "target_roles": cv_sections.get("Target Roles", ""),
        "career_narrative": cv_sections.get("Career Narrative", ""),
        "all_bullets": extract_cv_bullets(cv_text),
    }


# ============================================================
# Validation Guardrails
# ============================================================

def validate_inputs(metadata: dict, sections: dict, cv_evidence: dict) -> list[str]:
    warnings = []

    if not metadata.get("company"):
        warnings.append("Company missing from evaluation report metadata.")

    if not metadata.get("role"):
        warnings.append("Role missing from evaluation report metadata.")

    if not metadata.get("score"):
        warnings.append("Score missing from evaluation report metadata.")

    if not sections.get("match_with_cv"):
        warnings.append("Match with CV section not found.")

    if not sections.get("gaps_and_mitigation"):
        warnings.append("Gaps & Mitigation section not found.")

    if not sections.get("personalization_plan"):
        warnings.append("Personalization Plan section not found.")

    if not sections.get("interview_plan"):
        warnings.append("Interview Plan section not found.")

    if not cv_evidence.get("professional_summary"):
        warnings.append("Professional Summary missing from cv.md.")

    if not cv_evidence.get("professional_experience"):
        warnings.append("Professional Experience missing from cv.md.")

    return warnings


# ============================================================
# Main Build Function
# ============================================================

def build_optimization_input(report_path: str, cv_path: str, output_dir: str) -> Path:
    report_text = read_text_file(report_path)
    cv_text = read_text_file(cv_path)

    metadata = extract_basic_metadata(report_text)
    evaluation_sections = extract_evaluation_sections(report_text)
    cv_evidence = build_cv_evidence(cv_text)

    warnings = validate_inputs(metadata, evaluation_sections, cv_evidence)

    company = metadata.get("company") if is_usable_metadata_value(metadata.get("company")) else "unknown-company"
    role = metadata.get("role") if is_usable_metadata_value(metadata.get("role")) else "unknown-role"

    output_name = f"{safe_slug(company)}-{safe_slug(role)}-optimization-input.json"
    output_path = Path(output_dir) / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "2.0-cv-optimization-input",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_files": {
            "evaluation_report": str(Path(report_path)),
            "cv": str(Path(cv_path)),
        },
        "metadata": metadata,
        "evaluation_sections": evaluation_sections,
        "cv_evidence": cv_evidence,
        "guardrail_rules": [
            "Do not invent experience.",
            "Do not invent certifications.",
            "Do not invent tools.",
            "Do not claim domain experience unless supported by CV evidence.",
            "Certifications can only be suggested, not claimed.",
            "All ready-to-paste bullets must be grounded in CV evidence.",
        ],
        "warnings": warnings,
    }

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate structured input for job-specific CV optimization report."
    )

    parser.add_argument(
        "--report",
        required=True,
        help="Path to Phase 1 evaluation report markdown file.",
    )

    parser.add_argument(
        "--cv",
        required=True,
        help="Path to current cv.md file.",
    )

    parser.add_argument(
        "--output-dir",
        default="data/cv_optimization/inputs",
        help="Output directory for structured optimization JSON.",
    )

    args = parser.parse_args()

    output_path = build_optimization_input(
        report_path=args.report,
        cv_path=args.cv,
        output_dir=args.output_dir,
    )

    print("\nCV Optimization input created successfully.")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()

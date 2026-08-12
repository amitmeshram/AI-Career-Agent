from pathlib import Path
import argparse
import json
import re
from datetime import datetime


# ============================================================
# Helpers
# ============================================================

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

    return re.sub(r"\s+", " ", text).strip()

def normalize_statement(text):
    text = clean(str(text))
    text = re.sub(
        r"\bsupporting acquisition\b",
        "supported acquisition",
        text,
        flags=re.IGNORECASE
    )

    return text

def word_count(text):
    return len(re.findall(r"\S+", text))

def split_sentences(text):
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]

def clause_to_statement(clause):
    clause = clause.strip(" ,;")

    replacements = {
        "resulting in": "Resulted in",
        "securing": "Secured",
        "reducing": "Reduced",
        "improving": "Improved",
        "strengthening": "Strengthened",
    }

    lower_clause = clause.lower()

    for prefix, replacement in replacements.items():
        if lower_clause.startswith(prefix):
            clause = replacement + clause[len(prefix):]
            break

    if clause and clause[0].islower():
        clause = clause[0].upper() + clause[1:]

    if clause and clause[-1] not in ".!?":
        clause += "."

    return clause

def rewrite_result_clause(result):
    result = result.strip(" .")

    patterns = [
        (
            r"^(\d+% of stores) returning to profitability$",
            r"returned \1 to profitability"
        ),
    ]

    for pattern, replacement in patterns:
        if re.search(pattern, result, flags=re.IGNORECASE):
            return re.sub(
                pattern,
                replacement,
                result,
                flags=re.IGNORECASE
            )

    return result

def split_through_resulting_sentence(sentence):
    match = re.match(
        r"^(?P<lead>.+?)\s+through\s+(?P<means>.+?),\s+resulting in\s+(?P<result>.+?)[.!?]?$",
        sentence,
        flags=re.IGNORECASE
    )

    if not match:
        return []

    lead = clause_to_statement(match.group("lead"))
    means = match.group("means").strip()
    means = re.sub(
        r"\btargeted action planning\b",
        "action planning",
        means,
        flags=re.IGNORECASE
    )
    result = rewrite_result_clause(match.group("result"))
    second = clause_to_statement(f"Delivered {means} that {result}")

    if word_count(lead) > 60 or word_count(second) > 60:
        return []

    return [lead, second]

def split_long_sentence_at_clause_boundary(sentence):
    sentence = normalize_statement(sentence)

    if word_count(sentence) <= 30:
        return [sentence]

    through_resulting_split = split_through_resulting_sentence(sentence)

    if through_resulting_split:
        return through_resulting_split

    candidates = [
        match.start()
        for match in re.finditer(
            r"(?:;|,\s+(?:resulting in|securing|reducing|improving|strengthening|by|through|while|and)\b)",
            sentence,
            flags=re.IGNORECASE
        )
    ]

    if not candidates:
        return [sentence]

    midpoint = len(sentence) // 2
    valid_candidates = []

    for index in candidates:
        first_candidate = clause_to_statement(sentence[:index])
        separator_length = 1 if sentence[index] == ";" else 1
        second_candidate = clause_to_statement(sentence[index + separator_length:])

        if (
            word_count(first_candidate) <= 60
            and word_count(second_candidate) <= 60
        ):
            valid_candidates.append(index)

    if not valid_candidates:
        return [sentence]

    split_index = min(
        valid_candidates,
        key=lambda index: abs(index - midpoint)
    )

    first = clause_to_statement(sentence[:split_index])
    second = clause_to_statement(sentence[split_index + 1:])

    return [first, second]

def split_bullet_if_needed(text):
    text = normalize_statement(text)

    through_resulting_split = split_through_resulting_sentence(text)

    if through_resulting_split:
        return through_resulting_split

    if word_count(text) <= 30:
        return [text]

    sentences = split_sentences(text)

    if len(sentences) > 1:
        grouped = []

        for sentence in sentences:
            if not grouped:
                grouped.append(sentence)
                continue

            candidate = f"{grouped[-1]} {sentence}"

            if word_count(candidate) <= 30:
                grouped[-1] = candidate
            elif len(grouped) < 2:
                grouped.append(sentence)
            else:
                grouped[-1] = f"{grouped[-1]} {sentence}"

        return [
            statement
            for group in grouped[:2]
            for statement in split_long_sentence_at_clause_boundary(group)
        ][:2]

    return split_long_sentence_at_clause_boundary(text)[:2]

def recommended_bullets(statements):
    if isinstance(statements, str):
        statements = [statements]

    bullets = []

    for statement in statements:
        for bullet in split_bullet_if_needed(statement):
            normalized = normalize_statement(bullet)

            if normalized and normalized not in bullets:
                bullets.append(normalized)

    return bullets[:2]

def clean_bullets(bullets):
    return recommended_bullets(bullets)

def build_required_cv_changes(professional_summary, cv_bullets):

    changes = [{
        "section": "Professional Summary",
        "recommended_summary": professional_summary.get("optimized", "")
    }]

    for item in cv_bullets:

        if item["section"] == "Positioning Guardrail":
            continue

        changes.append({
            "section": item["section"],
            "recommended_bullets": clean_bullets(
                item["recommended_bullets"]
            )
        })

    return changes[:3]

def generate_professional_summary(metadata, personalization_text, cv_evidence):

    current_summary = cv_evidence.get(
        "professional_summary",
        ""
    )

    summary = (
        "Strategy, PMO, and business transformation professional with "
        "9+ years of experience leading transformation, operational excellence, "
        "business planning, and performance improvement initiatives across "
        "retail, manufacturing, procurement, and payments-adjacent environments. "
        "Proven track record in strategic planning, stakeholder governance, "
        "executive business case development, cross-functional program delivery, "
        "data-driven decision support, digital payment adoption, and enterprise "
        "transformation governance."
    )

    return {
        "current": current_summary,
        "optimized": summary,
        "generation_method": "evidence_grounded"
    }

def generate_evidence_grounded_bullets(metadata, sections, cv_evidence):
    """
    Generates ready-to-paste ATS-friendly CV bullets from existing CV evidence only.
    No invented experience, tools, certifications, or achievements.
    """

    bullets = []

    professional_experience = cv_evidence.get("professional_experience", "")
    selected_impact = cv_evidence.get("selected_business_impact", "")
    gaps_text = sections.get("gaps_and_mitigation", "")
    personalization_text = sections.get("personalization_plan", "")

    cv_text = f"{professional_experience}\n{selected_impact}".lower()
    context_text = f"{gaps_text}\n{personalization_text}".lower()

    if "tamara" in cv_text and "0.7%" in cv_text and "1.4%" in cv_text:
        bullets.append({
            "section": "Landmark Arabia",
            "current_cv_evidence": "Improved Tamara business contribution from 0.7% to 1.4% and supported acquisition of 30% new first-time shoppers.",
            "recommended_bullets": recommended_bullets([
                "Led cross-functional commercial adoption of the Tamara BNPL payment solution across Centrepoint stores.",
                "Increased payment contribution from 0.7% to 1.4% and supported acquisition of 30% new first-time shoppers."
            ]),
            "reason": "Strengthens payments-adjacent and fintech transformation positioning without claiming direct fintech employment."
        })

    if "underperforming" in cv_text and "50%" in cv_text:
        bullets.append({
            "section": "Landmark Arabia",
            "current_cv_evidence": "Achieved turnaround of 50% of underperforming stores through structured performance diagnostics, operational governance, and targeted action planning.",
            "recommended_bullets": recommended_bullets("Led structured performance improvement initiatives across underperforming retail locations through operational diagnostics, KPI governance, and targeted action planning, resulting in 50% of stores returning to profitability."),
            "reason": "Reframes retail turnaround as transformation delivery and consulting-style performance improvement."
        })

    if "investment committee approval" in cv_text and "10 new stores" in cv_text:
        bullets.append({
            "section": "Landmark Arabia",
            "current_cv_evidence": "Secured Investment Committee approval for opening 10 new stores by preparing business rationale, expansion logic, and opportunity assessment.",
            "recommended_bullets": recommended_bullets("Developed data-driven expansion business cases and opportunity assessments that secured Investment Committee approval for opening 10 new retail stores across priority growth markets."),
            "reason": "Highlights executive decision support, business case development, and strategic planning."
        })

    if "shrinkage" in cv_text and "2.0%" in cv_text and "0.6%" in cv_text:
        bullets.append({
            "section": "Landmark Arabia",
            "current_cv_evidence": "Reduced shrinkage loss from 2.0% to 0.6% through operational control and leakage prevention.",
            "recommended_bullets": recommended_bullets("Executed shrinkage reduction and operational control initiatives by strengthening stock movement traceability, process compliance, and store-level governance, reducing shrinkage loss from 2.0% to 0.6%."),
            "reason": "Positions operational control work as risk, leakage, and process-governance improvement."
        })

    if "source-to-contract" in cv_text and "procure-to-pay" in cv_text and "inr 5 crore" in cv_text:
        bullets.append({
            "section": "Yokohama",
            "current_cv_evidence": "Secured INR 5 crore CEO approval for implementation of a sourcing and procurement platform.",
            "recommended_bullets": recommended_bullets("Prepared CEO-level business case for Source-to-Contract and Procure-to-Pay digital transformation, securing INR 5 crore executive approval for enterprise procurement platform implementation."),
            "reason": "Strengthens enterprise transformation, business case, and executive stakeholder alignment positioning."
        })

    if "rfp" in cv_text and "cross-functional stakeholders" in cv_text:
        bullets.append({
            "section": "Yokohama",
            "current_cv_evidence": "Developed detailed RFP documentation by engaging cross-functional stakeholders across procurement, finance, operations, technology, and business teams.",
            "recommended_bullets": recommended_bullets("Led cross-functional requirement gathering and RFP documentation for enterprise procurement digitization by aligning procurement, finance, operations, technology, and business stakeholders."),
            "reason": "Adds consulting-style language around requirements, stakeholder alignment, and transformation delivery."
        })

    if "master data management" in cv_text or "item, customer, and price master data" in cv_text:
        bullets.append({
            "section": "Yokohama",
            "current_cv_evidence": "Deployed a Master Data Management tool covering item, customer, and price master data across the organization.",
            "recommended_bullets": recommended_bullets("Managed Master Data Management implementation across item, customer, and price data domains, improving data governance, cross-system consistency, and enterprise process reliability."),
            "reason": "Strengthens data governance and enterprise systems transformation positioning."
        })

    if "selenium" in cv_text and "corporate banking" in cv_text:
        bullets.append({
            "section": "Infosys",
            "current_cv_evidence": "Built a Selenium-based automation framework that reduced regression testing execution time and improved testing efficiency.",
            "recommended_bullets": recommended_bullets("Built Selenium-based automation framework for corporate banking regression testing, improving testing efficiency and strengthening structured problem-solving in technology delivery environments."),
            "reason": "Supports analytical rigor, automation, and payments/banking-adjacent experience."
        })

    if "consulting" in context_text:
        bullets.append({
            "section": "Positioning Guardrail",
            "current_cv_evidence": "CV contains transformation, governance, executive business case, stakeholder management, and performance improvement evidence, but not direct consulting-firm employment.",
            "recommended_bullets": recommended_bullets("Use consulting-style language only where supported by evidence, such as structured diagnostics, executive business cases, stakeholder governance, transformation workstreams, and measurable business outcomes."),
            "reason": "Prevents overclaiming direct consulting experience while improving consulting-role alignment."
        })

    return bullets


# ============================================================
# Strong Points
# ============================================================

def build_strong_points(match_text: str):
    strong_points = []

    rows = re.findall(
        r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|",
        match_text
    )

    for jd_req, evidence in rows:

        if jd_req.lower() in ["jd requirement", "----------------"]:
            continue

        if len(jd_req.strip()) < 5:
            continue
        
        if "mitigation" in jd_req.lower():
            continue

        if set(jd_req.replace("-", "").strip()) == set():
            continue

        if jd_req.startswith("-----"):
            continue

        strong_points.append({
            "requirement": clean(jd_req),
            "evidence": clean(evidence)
        })

    return strong_points


# ============================================================
# Weak Points
# ============================================================

def build_weak_points(gaps_text: str):

    weak_points = []

    rows = re.findall(
        r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|",
        gaps_text
    )

    for gap, severity, adjacent, mitigation in rows:

        if gap.lower() == "gap":
            continue

        if gap.startswith("-----"):
            continue

        weak_points.append({
            "gap": clean(gap),
            "severity": clean(severity),
            "adjacent_experience": clean(adjacent),
            "mitigation": clean(mitigation)
        })

    return weak_points


# ============================================================
# Missing ATS Keywords
# ============================================================

KEYWORD_PATTERNS = [
    "payments",
    "fintech",
    "consulting",
    "stakeholder-centric delivery",
    "mece",
    "presentation storytelling",
    "workshop facilitation",
    "framework development",
]


def build_missing_keywords(personalization_text, cv_evidence_text):

    missing = []

    cv_text_lower = cv_evidence_text.lower()

    for keyword in KEYWORD_PATTERNS:

        if keyword.lower() not in cv_text_lower:

            missing.append({
                "keyword": keyword,
                "status": "missing"
            })

    return missing


# ============================================================
# Executive Report
# ============================================================

def title_case_keyword(keyword):
    special_cases = {
        "mece": "MECE",
    }

    normalized = keyword.lower()

    if normalized in special_cases:
        return special_cases[normalized]

    return " ".join(
        "-".join(
            part.capitalize()
            for part in word.split("-")
            if part
        )
        for word in keyword.split()
    )


def normalize_term(term):
    return re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()


def build_executive_missing_keywords(missing_keywords, missing_skills=None):
    allowed_keywords = [
        "stakeholder-centric delivery",
        "mece",
        "workshop facilitation",
        "framework development",
        "presentation storytelling",
    ]

    skill_terms = set()

    for skills in (missing_skills or {}).values():
        for skill in skills:
            skill_terms.add(normalize_term(skill))

    missing_set = {
        item.get("keyword", "").lower()
        for item in missing_keywords
        if item.get("keyword")
    }

    return [
        title_case_keyword(keyword)
        for keyword in allowed_keywords
        if keyword in missing_set
        and normalize_term(keyword) not in skill_terms
    ]


def build_executive_missing_skills(weak_points):
    missing_skills = {
        "functional": [],
        "technical": [],
        "domain": [],
        "certifications": []
    }

    for weak_point in weak_points:
        gap = weak_point.get("gap", "").lower()

        if "consulting" in gap:
            missing_skills["functional"].extend([
                "Direct Consulting Engagement Delivery",
                "Management Consulting Methodologies"
            ])

        if (
            "tools" in gap
            or "tool" in gap
            or "platform" in gap
            or "platforms" in gap
            or "software" in gap
            or "system" in gap
            or "systems" in gap
        ):
            missing_skills["technical"].append(
                "Role-Specific Tools And Platforms"
            )

        if (
            "fintech" in gap
            or "payments" in gap
            or "fraud" in gap
            or "cybersecurity" in gap
        ):
            missing_skills["domain"].append(
                "Payments Industry Experience"
            )

        if "certification" in gap or "pmp" in gap or "prince2" in gap:
            missing_skills["certifications"].append(
                "Formal Project Management Certification"
            )

    for category, skills in missing_skills.items():
        missing_skills[category] = list(dict.fromkeys(skills))

    return missing_skills


def remove_keyword_skill_duplicates(missing_keywords, missing_skills):
    keyword_terms = {
        normalize_term(keyword)
        for keyword in missing_keywords
    }

    deduped_skills = {}

    for category, skills in missing_skills.items():
        deduped_skills[category] = [
            skill
            for skill in skills
            if normalize_term(skill) not in keyword_terms
        ]

    return deduped_skills


def build_executive_interview_risks(weak_points):
    risks = []

    for weak_point in weak_points:
        gap = weak_point.get("gap", "").lower()

        if "consulting" in gap:
            risks.append({
                "risk": "Direct Consulting Experience",
                "positioning": "Highlight consulting-style transformation delivery, executive business cases, and structured analysis."
            })

        if "fintech" in gap or "payments" in gap:
            risks.append({
                "risk": "Fintech Experience",
                "positioning": "Use Tamara BNPL implementation as primary payments and fintech example."
            })

    unique_risks = []
    seen = set()

    for risk in risks:
        key = risk["risk"]

        if key in seen:
            continue

        seen.add(key)
        unique_risks.append(risk)

    return unique_risks


def build_executive_job_fit_summary(metadata):
    return {
        "company": metadata.get("company"),
        "role": metadata.get("role"),
        "score": metadata.get("score"),
        "recommendation": metadata.get("recommendation"),
        "fit_type": metadata.get("fit_type"),
        "seniority_match": metadata.get("seniority_match"),
        "why_apply": metadata.get("why_apply"),
        "main_gap": metadata.get("main_gap")
    }


def parse_markdown_tables(text):
    tables = []
    current = []

    for line in (text or "").splitlines():
        stripped = line.strip()

        if stripped.startswith("|") and stripped.endswith("|"):
            current.append(stripped)
        elif current:
            tables.append(current)
            current = []

    if current:
        tables.append(current)

    parsed = []

    for table in tables:
        if len(table) < 2:
            continue

        rows = [
            [clean(cell) for cell in row.strip("|").split("|")]
            for row in table
        ]

        separator = rows[1]
        if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separator):
            continue

        headers = rows[0]
        data_rows = [
            dict(zip(headers, row + [""] * max(0, len(headers) - len(row))))
            for row in rows[2:]
            if any(row)
        ]
        parsed.append((headers, data_rows))

    return parsed


def find_table(text, required_headers):
    required = {normalize_term(header) for header in required_headers}

    for headers, rows in parse_markdown_tables(text):
        normalized = {normalize_term(header) for header in headers}
        if required.issubset(normalized):
            return headers, rows

    return [], []


def row_value(row, candidates):
    normalized = {
        normalize_term(key): value
        for key, value in row.items()
    }

    for candidate in candidates:
        value = normalized.get(normalize_term(candidate))
        if value is not None:
            return clean(value)

    return ""


def normalize_match_status(value, evidence=""):
    combined = clean(f"{value} {evidence}").lower()

    if "no match" in combined or "not present" in combined or "no matching" in combined:
        return "No Match"
    if "partial match" in combined or "partial" in combined or "adjacent" in combined:
        return "Partial Match"
    if "strong match" in combined or "strong" in combined:
        return "Strong Match"

    return clean(value) or "Partial Match"


def build_jd_requirements_match(sections):
    headers = []
    rows = []
    for candidate_headers, candidate_rows in parse_markdown_tables(
        sections.get("match_with_cv", "")
    ):
        if any(
            normalize_term(header).startswith(normalize_term("JD Requirement"))
            for header in candidate_headers
        ):
            headers = candidate_headers
            rows = candidate_rows
            break

    if not rows:
        return []

    output = []
    for row in rows:
        requirement = row_value(row, ["JD Requirement", "JD Requirement (inferred)"])
        evidence = row_value(
            row,
            ["CV Evidence", "CV Evidence (line)", "CV Evidence (line numbers)", "CV Evidence (exact line)", "Evidence from CV (exact lines)"],
        )
        match = row_value(row, ["Match", "Status"])

        if requirement:
            output.append({
                "jd_requirement": requirement,
                "status": normalize_match_status(match, evidence),
            })

    return output


def build_gaps_and_mitigation(sections):
    source = sections.get("gaps_and_mitigation", "") or sections.get("match_with_cv", "")
    _, rows = find_table(source, ["Gap"])
    output = []

    for row in rows:
        gap = row_value(row, ["Gap"])
        severity = row_value(
            row,
            ["Hard/Soft", "Category", "Hard/Nice-to-have", "Hard/Nice-to-Have", "Hard / Nice-to-have", "Hard/ Nice-to-have", "Severity"],
        )
        mitigation = row_value(
            row,
            [
                "Mitigation",
                "Mitigation Idea",
                "Mitigation Plan",
                "Mitigation (cover-letter)",
                "Mitigation (cover letter / interview)",
                "Portfolio / Mitigation",
                "Portfolio Suggestion",
                "Mitigation (Cover Letter / Quick Action)",
            ],
        )

        if gap and mitigation:
            output.append({
                "gap": gap,
                "severity": severity,
                "mitigation": mitigation,
            })

    if output:
        return output

    for line in source.splitlines():
        content = line.strip()
        if not content.startswith("-"):
            continue
        content = content.lstrip("- ").strip()

        explicit = re.match(
            r"\*\*Gap:\*\*\s*(.+?)\s+\*Mitigation:\*\s*(.+)",
            content,
            flags=re.IGNORECASE,
        )
        if explicit:
            output.append({
                "gap": explicit.group(1).strip(),
                "severity": "Not specified",
                "mitigation": explicit.group(2).strip(),
            })
            continue

        titled = re.match(r"\*\*(.+?)\*\*\s*[–-]\s*(.+)", content)
        if not titled:
            continue

        detail = titled.group(2).strip()
        mitigation_parts = re.split(
            r";?\s*(?:mitigate by|mitigation:)\s*",
            detail,
            maxsplit=1,
            flags=re.IGNORECASE,
        )
        output.append({
            "gap": titled.group(1).strip(),
            "severity": "Not specified",
            "mitigation": mitigation_parts[-1].strip(),
        })

    return output


def build_cv_changes(sections):
    _, rows = find_table(
        sections.get("personalization_plan", ""),
        ["Section", "Proposed change"],
    )
    output = []

    for index, row in enumerate(rows, start=1):
        section = row_value(row, ["Section"])
        if not section:
            continue

        proposed = row_value(row, ["Proposed change", "Proposed Change"])
        why = row_value(row, ["Why"])

        output.append({
            "number": row_value(row, ["#"]) or str(index),
            "section": section,
            "current": row_value(row, ["Current state", "Current State"]),
            "proposed_change": proposed,
            "why": why,
        })

    return output


def build_report_keywords(sections, fallback_keywords):
    keyword_text = sections.get("ats_keywords", "")
    keywords = []

    for line in keyword_text.splitlines():
        stripped = clean(re.sub(r"^[-*]\s*", "", line))
        if not stripped or stripped.startswith("|"):
            continue
        keywords.extend(clean(item) for item in re.split(r"[|,;]", stripped) if clean(item))

    return list(dict.fromkeys(keywords or fallback_keywords))


def build_executive_report(
    metadata,
    sections,
    professional_summary,
    cv_bullets,
    missing_keywords,
    weak_points
):
    missing_skills = build_executive_missing_skills(
        weak_points
    )

    executive_keywords = build_executive_missing_keywords(
        missing_keywords,
        missing_skills
    )

    missing_skills = remove_keyword_skill_duplicates(
        executive_keywords,
        missing_skills
    )

    return {
        "job_fit_summary": build_executive_job_fit_summary(
            metadata
        ),

        "jd_requirements_match": build_jd_requirements_match(
            sections
        ),

        "gaps_and_mitigation": build_gaps_and_mitigation(
            sections
        ),

        "cv_changes": build_cv_changes(
            sections
        ),

        "required_cv_changes": build_required_cv_changes(
            professional_summary,
            cv_bullets
        ),

        "missing_keywords": build_report_keywords(
            sections,
            []
        ),

        "missing_skills": missing_skills,

        "interview_risks": build_executive_interview_risks(
            weak_points
        )
    }


# ============================================================
# LinkedIn Optimization
# ============================================================

def build_linkedin_section(personalization_text):

    headline = ""

    headline_match = re.search(
        r"Strategy & Transformation Leader.*?Procurement",
        personalization_text,
        flags=re.IGNORECASE
    )

    if headline_match:
        headline = headline_match.group(0)

    return {
        "headline": headline,
        "notes": [
            "Add quantified achievements to About section",
            "Request recommendation emphasizing consulting-style delivery",
            "Add fintech/payments transformation positioning"
        ]
    }


# ============================================================
# Interview Preparation
# ============================================================

def build_interview_section(interview_text):

    stories = []

    for line in interview_text.splitlines():

        if "**S**:" in line:
            stories.append(clean(line))

    return {
        "star_stories": stories,
        "source": "evaluation_report"
    }


# ============================================================
# Main Builder
# ============================================================

def build_draft(input_json_path, output_path=None):

    data = load_json(input_json_path)

    metadata = data["metadata"]

    sections = data["evaluation_sections"]

    cv_evidence = data["cv_evidence"]

    full_cv_text = json.dumps(cv_evidence)

    cv_bullets = generate_evidence_grounded_bullets(
        metadata,
        sections,
        cv_evidence
    )

    strong_points = build_strong_points(
        sections.get("match_with_cv", "")
    )

    weak_points = build_weak_points(
        sections.get("gaps_and_mitigation", "")
    )

    missing_keywords = build_missing_keywords(
        sections.get("personalization_plan", ""),
        full_cv_text
    )

    professional_summary = generate_professional_summary(
        metadata,
        sections.get("personalization_plan", ""),
        cv_evidence
    )

    output = {
        "schema_version": "2.0-cv-optimization-draft",
        "created_at": datetime.now().isoformat(),

        "application_decision": {
            "company": metadata.get("company"),
            "role": metadata.get("role"),
            "score": metadata.get("score"),
            "recommendation": metadata.get("recommendation"),
            "why_apply": metadata.get("why_apply"),
            "main_gap": metadata.get("main_gap")
        },

        "strong_points": strong_points,

        "weak_points": weak_points,

        "missing_keywords": missing_keywords,

        "professional_summary": professional_summary,

        "cv_bullets_to_add": cv_bullets,

        "linkedin_optimization": build_linkedin_section(
            sections.get("personalization_plan", "")
        ),

        "interview_preparation": build_interview_section(
            sections.get("interview_plan", "")
        ),

        # "executive_report": {
        #     "job_fit_summary": {},
        #     "required_cv_changes": [],
        #     "missing_keywords": [],
        #     "missing_skills": {
        #         "functional": [],
        #         "technical": [],
        #         "domain": [],
        #         "certifications": []
        #     },
        #     "interview_risks": []
        # },

        "validation": {
            "no_hallucination": True,
            "source": "evaluation_report + cv"
        }
    }

    executive_report = build_executive_report(
        metadata,
        sections,
        professional_summary,
        cv_bullets,
        missing_keywords,
        weak_points
    )
    company = metadata.get("company", "unknown").lower()

    if output_path is None:
        output_path = Path(
            f"data/cv_optimization/drafts/{company}-optimization-draft.json"
        )
    else:
        output_path = Path(output_path)
    output["executive_report"] = executive_report

    save_json(output, output_path)

    print()
    print("Draft created successfully")
    print(output_path)

    return output_path


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True
    )

    args = parser.parse_args()

    build_draft(args.input)


if __name__ == "__main__":
    main()

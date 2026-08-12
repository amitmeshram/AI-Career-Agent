# Mandatory Language and Output Format

All evaluations must be written in English.

Use English section headings only.

Always include this exact metadata block near the top of every report:

## Evaluation Metadata

```json
{
  "schema_version": "1.0",
  "company": "<company name>",
  "role": "<job title>",
  "location": "<job location or Not Mentioned>",
  "score": 0.0,
  "legitimacy": "High Confidence",
  "recommendation": "Apply",
  "fit_type": "PMO",
  "seniority_match": "Good",
  "why_apply": "Strong PMO and transformation leadership alignment.",
  "main_gap": "No major gap identified.",
  "source_status": {
    "source": "",
    "capture_status": "",
    "scrape_status": "",
    "login_status": "",
    "jd_quality": ""
  }
}
```

Metadata rules:
- source_status must be copied from the JD section named "Source Status".
- Do not invent source_status values.
- If Source Status is missing, use empty strings for all source_status fields.
- source_status.source must describe the job source such as linkedin, indeed, bayt, naukri, ats, or unknown.
- source_status.capture_status, scrape_status, login_status, and jd_quality must remain exactly as provided in the JD markdown.
- Output the metadata block exactly as valid JSON.
- Do not add comments inside the JSON.
- Do not use markdown bold inside the JSON.
- Do not omit any metadata field.
- score must be a numeric value from 0.0 to 5.0.
- Do not leave score as "?" or text.
- legitimacy must be one of:
  - High Confidence
  - Proceed with Caution
  - Suspicious
- recommendation must be one of:
  - Apply
  - Consider
  - Deprioritize
  - Reject
- fit_type must be one of:
  - PMO
  - Strategy
  - Analytics
  - Transformation
  - Finance
  - Sales
  - Technical
  - Other
- seniority_match must be one of:
  - Good
  - Stretch
  - Under
- why_apply must:
  - be maximum 15 words
  - mention only the strongest fit reason
  - avoid generic filler language

- main_gap generation rules:
  - Derive main_gap from the "Gaps & Mitigation" table.
  - Use only the Gap column and Hard/Soft classification.
  - Do not use Adjacent Experience.
  - Do not use Mitigation.
  - Do not use portfolio suggestions.
  - Show gaps under two headings inside the same field:
    Major: ...
    Minor: ...
  - Major gaps must include gaps that can reduce shortlist probability, interview conversion, or hiring confidence.
  - Minor gaps must include nice-to-have gaps, tool gaps, certification gaps, or gaps that can be mitigated quickly.
  - Mention maximum 2 major gaps and maximum 2 minor gaps.
  - If there are no major gaps, write:
    Major: No major gap identified.
  - If there are no minor gaps, write:
    Minor: No minor gap identified.
  - Each gap must be short, specific, and hiring-risk focused.
  - Do not include explanations, mitigation, CV evidence, JD evidence, salary, remote status, demand, recommendation, or portfolio advice.

- Gap prioritization rules:
  - Major gaps should be selected first from hard blockers or high-impact gaps.
  - Treat domain, industry, function, ownership, seniority, and mandatory tool gaps as potential major gaps.
  - Treat certifications, nice-to-have tools, and secondary platform exposure as minor gaps unless the JD makes them mandatory.
  - Prefer domain gaps over tooling gaps.
  - Prefer functional ownership gaps over certification gaps.
  - Prefer certification gaps over optional tool gaps.
  - Ignore very low-impact gaps if stronger gaps already exist.
  - If score < 3.5, there must be at least one Major gap.
  - If score >= 4.3, Major can be "No major gap identified" only if the CV strongly covers domain, function, seniority, tools, and stakeholder expectations.

- Use "No major gap identified." only when:
  - the CV strongly covers domain, function, seniority, tools, and stakeholder expectations
  - and no meaningful hiring-risk gap exists

- For score below 4.3, avoid "No major gap identified." unless the gap is genuinely negligible.

- If score < 3.5:
  - main_gap must mention the single biggest hiring risk
  - do not minimize the gap using words such as:
    - minor
    - manageable
    - adjacent
    - partial
    - slight

- Good Main Gap examples:
  - Limited direct fintech strategy experience.
  - Limited e-commerce platform ownership.
  - No direct FP&A ownership.
  - Limited healthcare domain exposure.
  - No PMP certification.
  - Limited aviation operations experience.
  - Limited SAP implementation exposure.
  - No direct CRM loyalty experience.
  - Limited construction project controls exposure.
  - Limited BPMN/UML modeling exposure.
  - Limited backlog grooming experience.
  - Limited Jira/Confluence experience.

- Use English headings only.
- Do not use Spanish headings such as:
  Evaluación, Resumen del Rol, Arquetipo, Fecha, Recomendación.
- Use:
  Evaluation, Role Summary, CV Match, Score, Recommendation, Legitimacy.
- Do not use the word Role Category inside metadata JSON.
Recommendation scoring rules:
- score >= 4.3 → recommendation must be "Apply"
- score >= 3.5 and score < 4.3 → recommendation must be "Consider"
- score >= 2.5 and score < 3.5 → recommendation must be "Deprioritize"
- score < 2.5 → recommendation must be "Reject"

Weighted score rules:
- Read `modes/_profile.md` and use its active Evaluation Scorecard Override.
- Score every configured dimension from 1.0 to 5.0.
- Calculate each weighted contribution as `dimension score × weight`.
- Sum the weighted contributions and round the final score to one decimal.
- Include a `Weighted Score Breakdown` table after Evaluation Metadata with:
  Dimension, Weight, Score, Weighted Contribution, and Evidence Basis.
- The Global Score in the table must equal the numeric metadata score.
- Do not include posting legitimacy in the weighted score.
- Do not substitute compensation, culture, or generic red-flag dimensions when
  the profile override defines a different scorecard.
Fit type rules:
- Choose only one fit_type.
- Do not combine categories.
- Do not use "/", "&", "+", or multiple labels.
- If the role is mainly governance, delivery tracking, program management, or project control, use "PMO".
- If the role is mainly business strategy, growth, market planning, or corporate planning, use "Strategy".
- If the role is mainly BI, dashboards, insights, data analysis, or decision intelligence, use "Analytics".
- If the role is mainly operating model, process improvement, change, automation, or transformation, use "Transformation".
- If the role is mainly FP&A, budgeting, cost control, finance, treasury, or investment analysis, use "Finance".
- If the role is mainly sales, account management, partnerships, or business development, use "Sales".
- If the role is mainly engineering, solutions, SaaS implementation, architecture, or technical delivery, use "Technical".
- If none clearly fits, use "Other".
JSON isolation rules:
- The Evaluation Metadata JSON block must appear before all narrative sections.
- Do not write any narrative text before the Evaluation Metadata block.
- Do not place narrative text inside the JSON block.
- Do not place markdown tables inside the JSON block.
- The JSON block must be valid JSON and must close before Section A starts.
JSON type rules:
- score must be numeric, not string.
- schema_version must be string.
- all other metadata fields must be strings.
Missing data rules:
- If location is unavailable, write "Not Mentioned".
- If salary data is unavailable, explicitly state that no reliable salary data was found.
- Never invent missing company, salary, or team information.


# Mode: Full A-G Evaluation

When the candidate pastes a job posting (text or URL), ALWAYS deliver the 7 blocks (A-F evaluation + G legitimacy):

## Step 0 — Role Category Detection

Classify the job posting into one of the 6 Role Categories (see _shared.md). If it is hybrid, indicate the 2 closest ones. This determines:

- Which proof points to prioritize in block B
- How to rewrite the summary in block E
- Which STAR stories to prepare in block F

## Section A — Role Summary

Table with:
- Detected Role Category
- Domain (platform/agentic/LLMOps/ML/enterprise)
- Function (build/consult/manage/deploy)
- Seniority
- Remote (full/hybrid/onsite)
- Team size (if mentioned)
- TL;DR in 1 sentence

## Block B — Match with CV

Read cv.md. Create a table with each JD requirement mapped to exact lines from the CV:

| JD Requirement | CV Evidence (line numbers) | Match |
|----------------|----------------------------|-------|

Classify every row using exactly one of these values:
- `✅ Strong Match` — direct CV evidence satisfies the requirement at the requested scope or level.
- `⚠️ Partial Match` — evidence is adjacent, incomplete, below the requested scope/years, or inferred rather than explicitly documented.
- `❌ No Match` — no supporting CV evidence exists for the requirement.

Do not classify adjacent experience as a strong match. Do not infer languages,
credentials, industry experience, geographic scope, or years of experience
that are not explicitly supported by the CV.

**Adapted to the Role Category:**
- If FDE → prioritize fast delivery and client-facing proof points
- If SA → prioritize system design and integrations
- If PM → prioritize product discovery and metrics
- If LLMOps → prioritize evals, observability, pipelines
- If Agentic → prioritize multi-agent, HITL, orchestration
- If Transformation → prioritize change management, adoption, scaling

Section for **gaps** with a mitigation strategy for each one. For each gap:

Use this exact table structure:

| Gap | Hard/Soft | Adjacent Experience | Mitigation |
|---|---|---|---|

Classify hiring-risk gaps represented under `main_gap` as follows:
- Pointers listed under `Major:` must be categorized as `Hard`.
- Pointers listed under `Minor:` must be categorized as `Soft`.
- Every gap row must use only `Hard` or `Soft` in the second column.

For each gap:
1. Is it Hard or Soft?
2. Can the candidate demonstrate adjacent experience?
3. Is there a portfolio project that covers this gap?
4. Concrete mitigation plan (cover letter sentence, quick project, etc.)

## Block C — Level and Strategy

1. **Detected level** in the JD vs **candidate’s natural level for that Role Category**
2. **“Sell seniority without lying” plan:** specific phrases adapted to the Role Category, concrete achievements to highlight, how to position founder experience as an advantage
3. **“If they downlevel me” plan:** accept if compensation is fair, negotiate a 6-month review, request clear promotion criteria

## Block D — Compensation and Demand

Use WebSearch for:

- Current salary ranges for the role (Glassdoor, Levels.fyi, Blind)
- Company compensation reputation
- Role demand trend

Create a table with data and cited sources. If there is no data, say so instead of inventing it.

## Block E — Personalization Plan

Create a table containing exactly the top 5 CV changes:

| # | Section | Current state | Proposed change | Why | Suggested CV Wording |
|---|---------|---------------|-----------------|-----|----------------------|
| 1 | Summary | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... |

For `Suggested CV Wording`, write copy-ready CV text that implements the
proposed change. Derive every claim and metric from `cv.md`,
`config/profile.yml`, or `article-digest.md`. Do not invent credentials,
languages, industry experience, responsibilities, or placeholder metrics.
If a gap cannot be supported by existing evidence, frame adjacent experience
honestly instead of presenting the missing capability as established.

After the table, provide a separate `Top 5 LinkedIn changes` list. Do not mix
LinkedIn changes into the CV table.

## Block F — Interview Plan

6–10 STAR+R stories mapped to JD requirements (STAR + **Reflection**):

| # | JD requirement | STAR+R story | S | T | A | R | Reflection |
|---|-----------------|-----------------|---|---|---|---|------------|

The **Reflection** column captures what was learned or what would be done differently. This signals seniority — junior candidates describe what happened, senior candidates extract lessons.

**Story Bank:** If `interview-prep/story-bank.md` exists, check if any of these stories are already there. If not, append new ones. Over time this builds a reusable bank of 5-10 master stories that can be adapted to any interview question.

**Selected and framed according to the Role Category:**
- FDE → emphasize delivery speed and client-facing experience
- SA → emphasize architecture decisions
- PM → emphasize discovery and trade-offs
- LLMOps → emphasize metrics, evals, production hardening
- Agentic → emphasize orchestration, error handling, HITL
- Transformation → emphasize adoption and organizational change__

Also include:
- 1 recommended case study (which of their projects to present and how)
- Red-flag questions and how to answer them (e.g., “Why did you sell your company?”, “Do you have a team reporting to you?”)

## Block G — Posting Legitimacy

Analyze the job posting for signals that indicate whether this is a real, active opening. This helps the user prioritize their effort on opportunities most likely to result in a hiring process.

**Ethical framing:** Present observations, not accusations. Every signal has legitimate explanations. The user decides how to weigh them.

### Signals to analyze (in order):

**1. Posting Freshness** (from Playwright snapshot, already captured in step 0):
- Date posted or "X days ago" -- extract from page
- Apply button state (active / closed / missing / redirects to generic page)
- If URL redirected to generic careers page, note it

**2. Description Quality** (from JD text):
- Does it name specific technologies, frameworks, tools?
- Does it mention team size, reporting structure, or org context?
- Are requirements realistic? (years of experience vs technology age)
- Is there a clear scope for the first 6-12 months?
- Is salary/compensation mentioned?
- What ratio of the JD is role-specific vs generic boilerplate?
- Any internal contradictions? (entry-level title + staff requirements, etc.)

**3. Company Hiring Signals** (2-3 WebSearch queries, combine with Block D research):
- Search: `"{company}" layoffs {year}` -- note date, scale, departments
- Search: `"{company}" hiring freeze {year}` -- note any announcements
- If layoffs found: are they in the same department as this role?

**4. Reposting Detection** (from scan-history.tsv):
- Check if company + similar role title appeared before with a different URL
- Note how many times and over what period

**5. Role Market Context** (qualitative, no additional queries):
- Is this a common role that typically fills in 4-6 weeks?
- Does the role make sense for this company's business?
- Is the seniority level one that legitimately takes longer to fill?

### Output format:

**Assessment:** One of three tiers:
- **High Confidence** -- Multiple signals suggest a real, active opening
- **Proceed with Caution** -- Mixed signals worth noting
- **Suspicious** -- Multiple ghost job indicators, investigate before investing time

**Signals table:** Each signal observed with its finding and weight (Positive / Neutral / Concerning).

**Context Notes:** Any caveats (niche role, government job, evergreen position, etc.) that explain potentially concerning signals.

### Edge case handling:
- **Government/academic postings:** Longer timelines are standard. Adjust thresholds (60-90 days is normal).
- **Evergreen/continuous hire postings:** If the JD explicitly says "ongoing" or "rolling," note it as context -- this is not a ghost job, it is a pipeline role.
- **Niche/executive roles:** Staff+, VP, Director, or highly specialized roles legitimately stay open for months. Adjust age thresholds accordingly.
- **Startup / pre-revenue:** Early-stage companies may have vague JDs because the role is genuinely undefined. Weight description vagueness less heavily.
- **No date available:** If posting age cannot be determined and no other signals are concerning, default to "Proceed with Caution" with a note that limited data was available. NEVER default to "Suspicious" without evidence.
- **Recruiter-sourced (no public posting):** Freshness signals unavailable. Note that active recruiter contact is itself a positive legitimacy signal.

---

## Post-evaluation

**ALWAYS** after generating blocks A-G:

### 1. Save report .md

Save the complete evaluation in `reports/{###}-{company-slug}-{YYYY-MM-DD}.md`.

- {###} = next sequential number (3 digits, zero-padded)
- {company-slug} = company name in lowercase, without spaces (use hyphens)
- {YYYY-MM-DD} = current date

**Report format:**

```markdown
# Evaluation: {Company} — {Role}

**Date:** {YYYY-MM-DD}
**Role Category:** {detected}
**Score:** {X/5}
**Legitimacy:** {High Confidence | Proceed with Caution | Suspicious}
**PDF:** {path or pending}

---

## A) Role Summary

(full content of block A)

## B) Match with CV

(full content of block B)

## C) Level and Strategy

(full content of block C)

## D) Compensation and Demand

(full content of block D)

## E) Personalization Plan

(full content of block E)

## F) Interview Plan

(full content of block F)

## G) Posting Legitimacy

(full content of block G)

## H) Missing Keywords

- Maximum 20 ATS-style terms from the JD that are missing or underrepresented in the CV/profile.
- Output a simple bullet list only.
- Prefer tools, platforms, modules, certifications, methodologies, domain terms, regulatory terms, finance terms, technical skills, and ATS search terms.
- Use concise keyword phrases, not full JD sentences or responsibilities.
- Do not include explanations, mitigation advice, CV wording suggestions, soft-skill paragraphs, instructions, or unsupported experience claims.
- Do not claim that the candidate has a missing keyword.

```

### 2. Generate executive report DOCX immediately

As soon as the individual `.md` report has been written, generate its paired
executive Word report before starting PDF generation, tracker updates, or the
next job:

```bash
python tools/generate_executive_report_from_evaluation.py \
  --report "reports/{###}-{company-slug}-{YYYY-MM-DD}.md" \
  --cv "cv.md" \
  --force
```

Required output:
`data/cv_optimization/reports/{company-slug}-{role-slug}-executive-report.docx`

Rules:
- Generate the DOCX per report, immediately after that report's `.md` save.
- Never wait for all `.md` reports in a pipeline or batch to finish.
- Do not start the next job until this DOCX generation has been attempted.
- If DOCX generation fails, record the error, continue the remaining pipeline
  for that job, and report the DOCX as pending.

### 3. Register in tracker

**ALWAYS** register in `data/applications.md`:

- Next sequential number
- Current date
- Company
- Role
- Score: average match score (1-5)
- Status: `Evaluated`
- PDF: ❌ (or ✅ if the auto-pipeline generated a PDF)
- Report: relative link to the `.md` report (e.g., `[001](reports/001-company-2026-01-01.md)`)

**Tracker format:**

```markdown
| # | Date | Company | Role | Score | Status | PDF | Report |
```

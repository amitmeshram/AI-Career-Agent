# Phase 2 - CV Optimization Report Engine

## Objective

Generate a job-specific CV Optimization Report using:

* Phase 1 Evaluation Report
* Current CV

The output is an advisory report that improves application quality while preventing hallucinated experience, certifications, tools, or achievements.

---

## Architecture

Phase 1 Evaluation Report

*

Current CV

↓

Optimization Input JSON

↓

Optimization Draft JSON

↓

Enhanced Draft JSON

↓

DOCX CV Optimization Report

---

## Inputs

### Evaluation Report

Source:

```text
reports/*.md
```

Contains:

* Role Summary
* Match with CV
* Gaps & Mitigation
* Personalization Plan
* Interview Plan
* ATS Keywords

### Current CV

Source:

```text
cv.md
```

---

## Outputs

### Optimization Input

```text
data/cv_optimization/inputs/
```

### Optimization Draft

```text
data/cv_optimization/drafts/
```

### Enhanced Draft

```text
data/cv_optimization/enhanced/
```

### DOCX Report

```text
data/cv_optimization/reports/
```

---

## Generated Report Sections

1. Application Assessment
2. Strengths
3. Weaknesses & Gaps
4. ATS Keyword Analysis
5. Optimized Professional Summary
6. ATS-Ready CV Improvements
7. LinkedIn Optimization
8. Interview Preparation
9. Final Recommendation

---

## Guardrails

Never invent:

* Experience
* Certifications
* Education
* Projects
* Achievements
* Tools

All recommendations must be grounded in:

* Evaluation Report evidence
* CV evidence

---

## Current Status

Phase 2 V1 Complete

---

## Future Enhancements

### Phase 2 V2

* Dynamic ATS Bullet Generation
* Structured STAR Story Extraction
* Automatic Keyword Scoring
* Multi-Role Optimization

### Phase 2 V3

* Batch Optimization Reports
* Tailored Cover Letter Generator
* LinkedIn Rewrite Assistant
* Application Package Generator

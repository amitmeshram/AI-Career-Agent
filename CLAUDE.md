# AI Career Agent -- Agent Instructions

AI Career Agent is a local job-search automation tool. It scans Gmail job-alert emails, supports manual job-description scans, uses LinkedIn browser sessions when needed, evaluates jobs against the user's CV/profile, generates Markdown evaluation reports, generates executive DOCX CV optimization reports, and maintains local tracker data.

AI Career Agent never submits applications automatically.

## Upstream Attribution

AI Career Agent was originally adapted from the open-source Career-Ops project and has been significantly modified.

## Current Workflow

Use these commands as the current workflow:

```powershell
python run.py
python run.py --help
npm run doctor
npm run verify
npm run release:audit
npm run release:package
```

Legacy command files may exist from the upstream project. Do not present them as the recommended workflow. The recommended workflow is `python run.py`.

For AI model/API key setup and Gmail OAuth screenshots, see [AI Model Connection Guidebook.docx](<AI Model Connection Guidebook.docx>).

## Data Contract

User layer, never auto-updated and never committed:

- `cv.md`
- `config/profile.yml`
- `modes/_profile.md`
- `article-digest.md`
- `portals.yml`
- `data/*`
- `reports/*`
- `output/*`
- `interview-prep/*`

System layer, reusable project logic:

- `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`
- `*.mjs` scripts
- `run.py`
- `apps/gmail-agent/*.py`
- `dashboard/*`
- `templates/*`
- `batch/*`
- shared mode files under `modes/`

Personalization rule: write user-specific targeting, archetypes, narrative, deal-breakers, compensation, location policy, proof points, and preferences to `config/profile.yml`, `modes/_profile.md`, or `article-digest.md`. Do not write user-specific content to `modes/_shared.md`.

## Update Check

On the first message of a session, run silently:

```bash
node update-system.mjs check
```

If it reports an available update, tell the user that a system update is available and that user data will not be touched. Ask before applying. If it reports `up-to-date`, `dismissed`, `offline`, or `no-remote-version`, say nothing.

## What Is AI Career Agent

AI Career Agent supports Gmail job-alert scanning, LinkedIn browser sessions, Manual JD Scan, AI evaluation against `cv.md` and `config/profile.yml`, Markdown reports, executive DOCX CV optimization reports, tracker integrity, and optional email summaries.

Email summary variables, if referenced, must be only:

```env
EMAIL_SENDER=
EMAIL_APP_PASSWORD=
EMAIL_RECEIVER=
```

Do not add Telegram back.

## AI Provider Configuration

Root `.env` uses one provider/API key and three model names:

```env
AI_PROVIDER_NAME=openrouter
AI_API_KEY=your-provider-key
AI_BASE_URL=
PRIMARY_MODEL=provider/model-one
FALLBACK_MODEL=provider/model-two
SECOND_FALLBACK_MODEL=provider/model-three
```

`AI_PROVIDER_NAME` means provider name, for example `openrouter`, `openai`, `gemini`, `kimi`, `glm`, or `custom`. It does not mean API key name.

Reject malformed AI model output. If model output contains fake tool-call JSON such as `{"tool":"read"}`, raw prompt chatter, invalid report structure, or missing required report sections, do not save it as a valid report. Rerun or ask for manual review.

## First Run -- Onboarding

Before evaluations or scans, verify these files exist:

1. `cv.md`
2. `config/profile.yml`
3. `modes/_profile.md`
4. `portals.yml`
5. `data/applications.md`

If `modes/_profile.md` is missing, copy from `modes/_profile.template.md`.

If `data/applications.md` is missing, create:

```markdown
# Applications Tracker

| # | Date | Company | Role | Score | Status | PDF | Report | Notes |
|---|------|---------|------|-------|--------|-----|--------|-------|
```

If required user files are missing, guide the user through setup before running scans or evaluations.

## Gmail, LinkedIn, and Manual JD Setup

Gmail uses OAuth, not Gmail passwords. Expected files are `apps/gmail-agent/credentials.json` and `apps/gmail-agent/token.json`.

LinkedIn scraping uses a local browser profile under `data/gmail-agent/browser_profiles/`.

Use Manual JD Scan when a job page is blocked, expired, behind a challenge, or available only as pasted text.

Gmail scan limits live in `config/profile.yml`:

```yaml
gmail_scan:
  max_job_alerts_to_process: 5
  max_job_links_to_process: 45
```

## Skill Modes

Route user intent to the existing checked-in mode files without creating parallel logic.

| User intent | Mode file |
|---|---|
| Raw JD text or job URL | `modes/auto-pipeline.md` |
| Single evaluation | `modes/oferta.md` |
| Multiple jobs comparison | `modes/ofertas.md` |
| Portal or Gmail scan | `modes/scan.md` |
| Manual application assistance | `modes/apply.md` |
| Tracker status | `modes/tracker.md` |
| Deep company research | `modes/deep.md` |
| Interview prep | `modes/interview-prep.md` |

Do not rewrite old mode/command files unless the user explicitly asks.

## CV Source of Truth

- `cv.md` is the canonical CV.
- `article-digest.md` can store proof points.
- `config/profile.yml` and `modes/_profile.md` store targeting and preferences.

Never invent CV facts, tools, certifications, metrics, domain experience, employers, awards, education, or achievements. If a fact is not present in source material, mark it as unknown or ask the user.

## Ethical Use -- CRITICAL

AI Career Agent is designed for quality, not mass applications.

- Never submit an application without user review.
- Stop before clicking Submit, Send, Apply, or any equivalent final action.
- Strongly discourage low-fit applications.
- Draft answers and documents for review only.

## Offer Verification -- MANDATORY

Do not trust generic web fetch alone to verify if a job is active. Use Playwright when available:

1. Navigate to the URL.
2. Read visible page content.
3. Treat footer/navbar-only pages, login walls, security challenges, expired banners, or missing JD content as blocked/expired/unconfirmed.

If Playwright is unavailable or the site blocks automation, use Manual JD Scan and mark the source as manual or unconfirmed.

## Report Generation Rules

After each evaluation report is written, generate the executive DOCX report immediately:

```bash
python tools/generate_executive_report_from_evaluation.py --report <report.md> --cv cv.md --force
```

Output location: `data/cv_optimization/reports/`.

## Pipeline Integrity

1. Never add new application rows directly to `data/applications.md`.
2. Write one TSV file per evaluation under `batch/tracker-additions/`.
3. Run `node merge-tracker.mjs` after batches.
4. Do not create duplicate company+role entries.
5. Existing tracker rows can be updated for status/notes.
6. Reports must include source URL and legitimacy/verification status where applicable.

Health checks:

```bash
node verify-pipeline.mjs
node normalize-statuses.mjs
node dedup-tracker.mjs
```

## TSV Format

Write one line with 9 tab-separated columns:

```text
{num}\t{date}\t{company}\t{role}\t{status}\t{score}/5\t{pdf_emoji}\t[{num}](reports/{num}-{slug}-{date}.md)\t{note}
```

Column order: `num`, `date`, `company`, `role`, `status`, `score`, `pdf`, `report`, `notes`.

## Canonical States

Use only statuses from `templates/states.yml`:

- `Evaluated`
- `Applied`
- `Responded`
- `Interview`
- `Offer`
- `Rejected`
- `Discarded`
- `SKIP`

No markdown bold, dates, or extra prose in the status field.

## Private File Safety

Never commit `.env`, `credentials.json`, `token.json`, `cv.md`, `config/profile.yml`, `modes/_profile.md`, `reports/`, `output/`, `jds/`, runtime data, browser sessions, or backup files.

Do not paste secrets into prompts, reports, commits, issues, or documentation.

## Git Rules

Use scoped staging only. Never use `git add .` in dirty repositories. Never revert user changes unless explicitly requested.
# Codex Setup for AI Career Agent

AI Career Agent supports Codex through the root `AGENTS.md` file. Codex should reuse the checked-in mode files, templates, tracker flow, Gmail-agent code, and scripts that power the local workflow.

The recommended workflow is `python run.py`, not legacy slash commands.

## Install

```bash
npm install
npx playwright install chromium
python -m pip install -r requirements.txt
python -m pip install -r apps/gmail-agent/requirements.txt
```

For provider/API key examples and Gmail OAuth setup, see [AI Career Agent Setup Connection Guidebook PDF](<../AI_Career_Agent_Setup_Connection_Guidebook.pdf>).

## Recommended Commands

```powershell
python run.py
python run.py --help
npm run doctor
npm run verify
npm run release:audit
npm run release:package
```

## Routing Map

| User intent | Files Codex should read |
|---|---|
| Raw JD text or job URL | `modes/_shared.md` + `modes/auto-pipeline.md` |
| Single evaluation | `modes/_shared.md` + `modes/oferta.md` |
| Gmail or portal scan | `modes/_shared.md` + `modes/scan.md` |
| Manual JD Scan | `apps/gmail-agent/SETUP.md` + `modes/oferta.md` |
| Tracker status | `modes/tracker.md` |
| Deep company research | `modes/deep.md` |

## Behavioral Rules

- Never submit applications automatically.
- Never invent CV facts, tools, certifications, metrics, domain experience, employers, or achievements.
- Reject malformed AI model output.
- If model output contains fake tool-call JSON such as `{"tool":"read"}`, do not save it as a valid report.
- Keep personalization in `config/profile.yml`, `modes/_profile.md`, `article-digest.md`, or `portals.yml`.
- Use Playwright for live job verification when available.
- Use Manual JD Scan when pages are blocked.
- Never add new tracker rows directly to `data/applications.md`; use TSV additions and `merge-tracker.mjs`.
- Use scoped `git add <specific-files>` only. Never use `git add .` in dirty repos.

## Private File Safety

Never commit `.env`, credentials, tokens, `cv.md`, `config/profile.yml`, `modes/_profile.md`, reports, output, runtime data, browser sessions, or backup files.
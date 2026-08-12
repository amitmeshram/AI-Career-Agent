# Production Runbook

## 1. Overview

The consolidated AI Career Agent runs inside Career-Ops and supports daily job discovery, Gmail-based job scanning, manual job description evaluation, report generation, daily CSV summaries, and email summaries.

Production root:

```powershell
D:\Artificial Intelligence\career-ops
```

Production app path:

```powershell
D:\Artificial Intelligence\career-ops\apps\gmail-agent
```

The old `ai-career-agent` repository is a legacy backup only. Daily production usage should happen from the Career-Ops production root.

## 2. Daily Run Procedure

Start PowerShell and run:

```powershell
cd "D:\Artificial Intelligence\career-ops"
.\.venv\Scripts\activate
python apps\gmail-agent\main.py
```

In the app menu, choose **Gmail Job Scan**.

Expected behavior:

- The app checks Gmail for job-related messages.
- Matching jobs are evaluated through the Career-Ops evaluation flow.
- Career-Ops reports are generated under `reports\`.
- Executive DOCX reports are generated under `data\cv_optimization\reports\`.
- A daily CSV summary is written by the Gmail agent under `reports\daily\`.
- If email delivery is configured and available, the app sends a summary email for the run.

The daily CSV is the operational summary for that run. Use the generated Career-Ops reports for the detailed recommendation, score, and rationale.

## 3. Manual JD Scan Procedure

Use **Manual JD Scan** when:

- A job came from LinkedIn, Indeed, a recruiter, or another source outside Gmail.
- A job page is blocked, expired, or hard to scrape.
- You want to evaluate a pasted job description before deciding whether to apply.

Run the app:

```powershell
cd "D:\Artificial Intelligence\career-ops"
.\.venv\Scripts\activate
python apps\gmail-agent\main.py
```

Choose **Manual JD Scan**, paste the full job description when prompted, then submit it according to the app instructions.

Expected output:

- A Career-Ops evaluation report with score, recommendation, fit analysis, and risks.
- An executive DOCX report when the Career-Ops evaluation path completes.
- Tracker/report artifacts using the normal Career-Ops conventions.

Manual JD scan feeds the same Career-Ops evaluation logic as the daily scan. Do not create a separate scoring process for pasted JDs.

## 4. Startup Health Check

At startup, review the health check before running scans.

| Status | Meaning | Action |
|---|---|---|
| `Gmail Connection OK` | Gmail credentials and token are usable. | Continue. |
| `Gmail Connection RECONNECT_REQUIRED` | Gmail token is missing, expired, or revoked. | Run **Reconnect Gmail**. |
| `LinkedIn Session OK` | Local browser profile is logged in and usable. | Continue. |
| `LinkedIn Session LOGIN_REQUIRED` | LinkedIn needs a fresh browser login. | Run **Reconnect LinkedIn**. |
| `Career-Ops Files OK` | Required Career-Ops files are present. | Continue. |
| `AI Model Connection OK` | AI provider configuration is available. | Continue. |
| `Output Folders OK` | Runtime output folders exist and are writable. | Continue. |

If any status is not OK, fix it before treating the run as production-valid.

## 5. Gmail Reconnect Procedure

Use this when startup reports `Gmail Connection RECONNECT_REQUIRED` or Gmail scanning fails due to authentication.

```powershell
cd "D:\Artificial Intelligence\career-ops"
.\.venv\Scripts\activate
python apps\gmail-agent\main.py
```

Choose **Reconnect Gmail**.

Expected behavior:

- A browser login opens.
- Sign in to the intended Gmail account.
- Complete the OAuth consent flow.
- `apps\gmail-agent\token.json` is created or refreshed locally.

`token.json` is a local secret/runtime file. It must not be committed.

## 6. LinkedIn Reconnect Procedure

Use this when startup reports `LinkedIn Session LOGIN_REQUIRED` or LinkedIn pages cannot be accessed as expected.

```powershell
cd "D:\Artificial Intelligence\career-ops"
.\.venv\Scripts\activate
python apps\gmail-agent\main.py
```

Choose **Reconnect LinkedIn**.

Expected behavior:

- A browser opens using the app-managed local profile.
- Log in to LinkedIn manually.
- Complete any required verification.
- A local browser profile is created or refreshed under `data\gmail-agent\browser_profiles\`.

Browser profiles are local runtime data. They must not be committed.

## 7. Local Secrets and User Files

These files and folders are local only and must not be committed unless the project explicitly tracks a sanitized template:

- `apps\gmail-agent\.env`
- `apps\gmail-agent\credentials.json`
- `apps\gmail-agent\token.json`
- `data\gmail-agent\`
- `data\gmail-agent\browser_profiles\`
- `reports\daily\`
- `jds\`
- `cv.md`
- `config\profile.yml`
- `modes\_profile.md`
- `portals.yml`

Do not paste real secrets into documentation, prompts, reports, commits, or issue comments.

## 8. Troubleshooting

| Issue | Likely cause | Fix |
|---|---|---|
| Gmail token expired or revoked | OAuth token is no longer valid. | Run **Reconnect Gmail** and confirm `apps\gmail-agent\token.json` is recreated locally. |
| LinkedIn login required | Browser profile is missing, expired, or logged out. | Run **Reconnect LinkedIn** and complete browser login. |
| OpenRouter/API key missing | AI provider key is absent from local config. | Check `.env` and add the required local setting. Do not commit it. |
| Playwright browser missing | Browser binaries were not installed in this environment. | Run `npx playwright install chromium` from the production root. |
| Email not sent | SMTP/API settings missing, token issue, or provider rejected send. | Check local `.env`, confirm network/provider access, then rerun the scan. |
| No jobs found | No matching Gmail messages or filters are too narrow. | Confirm Gmail query/filter settings and verify relevant messages exist. |
| Job blocked by LinkedIn, Indeed, or Cloudflare | Site blocks automation or requires login. | Use **Manual JD Scan** with pasted JD text, or reconnect LinkedIn when appropriate. |
| Daily report missing score or recommendation | Career-Ops evaluation did not complete cleanly. | Review the generated report, rerun the scan for that job, and check AI model connectivity. |
| Virtual environment not activated | Python dependencies are unavailable. | Run `.\.venv\Scripts\activate` before `python apps\gmail-agent\main.py`. |

## 9. Production Validation Checklist

Before calling the consolidated setup production-ready, verify:

- [ ] Startup check all OK.
- [ ] Manual JD scan works.
- [ ] Gmail scan works.
- [ ] Career-Ops reports generated.
- [ ] Executive DOCX generated.
- [ ] CSV daily summary generated.
- [ ] Email sent.
- [ ] Git status clean except ignored local files.

Use:

```powershell
git status --short
```

## 10. Rollback Plan

Legacy rollback locations:

```powershell
D:\Artificial Intelligence\ai-career-agent
D:\Artificial Intelligence\ai-career-agent-legacy-source.zip
```

If the production app fails and cannot be fixed quickly, run the old repo temporarily from `D:\Artificial Intelligence\ai-career-agent` while the Career-Ops production app is repaired.

Do not delete the old repo or legacy archive until the consolidated production app has completed several successful production runs.

## 11. Git Checkpoint Rules

Before any change:

```powershell
git status --short
```

After an accepted fix:

```powershell
git add RUNBOOK.md
git commit -m "docs: add production runbook"
```

For stable production milestones:

```powershell
git tag production-milestone-6
```

Rules:

- Never commit secrets or runtime data.
- Never commit `apps\gmail-agent\.env`, `credentials.json`, `token.json`, browser profiles, generated JDs, reports, or runtime data.
- Commit documentation and accepted code fixes only after reviewing `git status --short`.
- Tag stable milestones only after validation passes.

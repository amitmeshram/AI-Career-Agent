# AI Career Agent Runbook

## 1. Overview

AI Career Agent is a local job-search automation tool for Gmail job-alert scanning, manual job-description evaluation, Markdown report generation, executive DOCX CV optimization reporting, and optional email summaries.

Production root:

```powershell
D:\Artificial Intelligence\First-tool-dry-run\final-tool
```

For AI model/API key setup and Gmail OAuth screenshots, see [AI Model Connection Guidebook.docx](<AI Model Connection Guidebook.docx>).

## 2. Daily Run

```powershell
cd "D:\Artificial Intelligence\First-tool-dry-run\final-tool"
.\.venv\Scripts\activate
python run.py
```

Choose Gmail Job Scan.

Expected behavior:

- Gmail job-alert emails are read through OAuth.
- Job links and email-card metadata are extracted.
- Accessible job pages are scraped.
- Blocked pages can be handled through Manual JD Scan.
- Markdown reports are generated under `reports\`.
- Executive DOCX reports are generated under `data\cv_optimization\reports\`.
- Daily summaries are written under `reports\daily\`.

## 3. Manual JD Scan

Use Manual JD Scan when a portal blocks automation or a JD is available only as pasted text.

```powershell
python run.py
```

Choose Manual JD Scan and paste the full job description.

## 4. Startup Health Check

| Status | Meaning | Action |
|---|---|---|
| `Gmail Connection OK` | Gmail OAuth files are valid. | Continue. |
| `Gmail Connection RECONNECT_REQUIRED` | Gmail token is missing, expired, or revoked. | Reconnect Gmail. |
| `LinkedIn Session OK` | Browser profile is logged in. | Continue. |
| `LinkedIn Session LOGIN_REQUIRED` | LinkedIn login is required. | Reconnect LinkedIn. |
| `Project Files OK` | Local project files are present. | Continue. |`r`n| `AI Model Connection OK` | AI provider settings are present. | Continue. |
| `Output Folders OK` | Runtime folders are writable. | Continue. |
`r`n
## 5. AI Provider Configuration

```env
AI_PROVIDER_NAME=openrouter
AI_API_KEY=your-provider-key
AI_BASE_URL=
PRIMARY_MODEL=provider/model-one
FALLBACK_MODEL=provider/model-two
SECOND_FALLBACK_MODEL=provider/model-three
```

`AI_PROVIDER_NAME` means provider name, for example `openrouter`, `openai`, `gemini`, `kimi`, `glm`, or `custom`. It does not mean API key name.

## 6. Gmail and LinkedIn Reconnect

Run `python run.py`, then choose Reconnect Gmail or Reconnect LinkedIn from the menu. Gmail uses OAuth and LinkedIn uses a local browser profile.

## 7. Gmail Scan Limits

`config/profile.yml`:

```yaml
gmail_scan:
  max_job_alerts_to_process: 5
  max_job_links_to_process: 45
```

## 8. Optional Email Summary

Use only these variable names if email summaries are configured:

```env
EMAIL_SENDER=
EMAIL_APP_PASSWORD=
EMAIL_RECEIVER=
```

Do not add Telegram configuration.

## 9. Troubleshooting

| Issue | Fix |
|---|---|
| Gmail disconnected | Reconnect Gmail from `python run.py`. |
| LinkedIn login required | Reconnect LinkedIn from `python run.py`. |
| AI model missing | Check root `.env`. |
| Job board blocked | Use Manual JD Scan. |
| Report malformed | Reject it and rerun or review manually. |
| Tracker issue | Run `npm run verify`. |

## 10. Private File Safety

Never commit `.env`, `credentials.json`, `token.json`, `cv.md`, `config/profile.yml`, `modes/_profile.md`, `reports/`, `output/`, runtime data, browser sessions, or backup files.

## 11. Git Rules

Use scoped staging only. Never use `git add .` in dirty repos.
# Gmail Agent Setup for AI Career Agent

Run these steps from the AI Career Agent project root, not from `apps/gmail-agent`.

## Install Dependencies

```powershell
python -m pip install -r requirements.txt
python -m pip install -r apps\gmail-agent\requirements.txt
npx playwright install chromium
```

## AI Provider Setup

The root `.env` must include one provider/API key and three model names:

```env
AI_PROVIDER_NAME=openrouter
AI_API_KEY=your-provider-key
AI_BASE_URL=
PRIMARY_MODEL=provider/model-one
FALLBACK_MODEL=provider/model-two
SECOND_FALLBACK_MODEL=provider/model-three
```

`AI_PROVIDER_NAME` means provider name, for example `openrouter`, `openai`, `gemini`, `kimi`, `glm`, or `custom`. It does not mean API key name.

For screenshots and provider examples, see [AI Model Connection Guidebook.docx](<../../AI Model Connection Guidebook.docx>).

## Gmail OAuth

Expected files:

- `apps/gmail-agent/credentials.json`
- `apps/gmail-agent/token.json`

AI Career Agent uses OAuth and never needs your Gmail password. Run `python run.py` and choose Reconnect Gmail when needed.

## LinkedIn Browser Session

Run `python run.py` and choose Reconnect LinkedIn if startup reports LinkedIn login required. The browser session is stored under `data/gmail-agent/browser_profiles/`.

## Gmail Job Scan

Run:

```powershell
python run.py
```

Choose Gmail Job Scan. The app reads job alerts, extracts job links, scrapes accessible pages, exports JD Markdown files, runs evaluations, generates Markdown reports, generates executive DOCX reports, builds daily summaries, and optionally sends an email summary.

## Gmail Scan Limits

```yaml
gmail_scan:
  max_job_alerts_to_process: 5
  max_job_links_to_process: 45
```

## Manual JD Scan

Use Manual JD Scan when a portal blocks automation or a job description is available only as pasted text.

## Optional Email Summary Variables

Use only these variable names if email summaries are configured:

```env
EMAIL_SENDER=
EMAIL_APP_PASSWORD=
EMAIL_RECEIVER=
```

Do not add Telegram configuration.

## Private File Safety

Never commit `.env`, `credentials.json`, `token.json`, `cv.md`, `config/profile.yml`, `modes/_profile.md`, reports, output, runtime data, browser sessions, or backup files.
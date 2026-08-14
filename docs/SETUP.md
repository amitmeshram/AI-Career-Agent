# AI Career Agent Setup Guide

## Prerequisites

- Node.js 18+
- Python 3.10+
- Playwright Chromium
- Optional: Go 1.21+ for the dashboard

## Quick Start

Windows:

```powershell
.\setup_windows.ps1
python run.py
```

macOS:

```bash
bash setup_macos.sh
python run.py
```

For command help:

```bash
python run.py --help
```

## Configure Local Files

```bash
cp config/profile.example.yml config/profile.yml
cp templates/portals.example.yml portals.yml
cp .env.example .env
cp modes/_profile.template.md modes/_profile.md
cp apps/gmail-agent/.env.example apps/gmail-agent/.env
```

Create `cv.md` in the project root with your full CV in Markdown.

For AI model/API key setup and Gmail OAuth screenshots, see [AI Model Connection Guidebook.docx](<../AI Model Connection Guidebook.docx>).

## AI Provider Setup

```env
AI_PROVIDER_NAME=openrouter
AI_API_KEY=your-provider-key
AI_BASE_URL=
PRIMARY_MODEL=provider/model-one
FALLBACK_MODEL=provider/model-two
SECOND_FALLBACK_MODEL=provider/model-three
```

`AI_PROVIDER_NAME` means provider name, for example `openrouter`, `openai`, `gemini`, `kimi`, `glm`, or `custom`. It does not mean API key name.

## Gmail OAuth Setup

AI Career Agent uses Gmail OAuth to read job-alert emails.

1. Create or select a Google Cloud project.
2. Enable the Gmail API.
3. Configure an OAuth consent screen.
4. Create a Desktop OAuth client.
5. Download the JSON file as `apps/gmail-agent/credentials.json`.
6. Run `python run.py` and choose Reconnect Gmail when prompted.

The generated `apps/gmail-agent/token.json` is private and must not be committed.

## LinkedIn Browser Login

Run `python run.py` and choose Reconnect LinkedIn when startup reports login required. Browser sessions are stored under `data/gmail-agent/browser_profiles/`.

## Gmail Scan Limits

```yaml
gmail_scan:
  max_job_alerts_to_process: 5
  max_job_links_to_process: 45
```

## Manual JD Scan

Use Manual JD Scan for blocked sites, recruiter emails, copied job descriptions, or job boards that do not scrape reliably.

## Validate

```bash
npm run doctor
npm run verify
python run.py --help
```

## Private File Safety

Never commit `.env`, `credentials.json`, `token.json`, `cv.md`, `config/profile.yml`, `modes/_profile.md`, `reports/`, `output/`, runtime data, browser sessions, or backup files.
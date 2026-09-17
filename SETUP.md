# AI Career Agent Setup

Run these commands from the folder that contains `package.json` and `run.py`.

## 1. Install Prerequisites

- Node.js 18+
- Python 3.10+
- PowerShell on Windows or Terminal on macOS
- Playwright Chromium
- Optional: Go 1.21+ for the dashboard

On Windows, first-time users who do not already have Node.js or Python can let setup ask before installing them with `winget`. Manual install commands:

```powershell
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
```

On macOS, first-time users who have Homebrew can let setup ask before installing missing prerequisites with `brew`. Manual install commands:

```bash
brew install node python
```

Close and reopen the terminal after manually installing Node.js or Python if the commands are not available immediately.

## 2. Run One-Command Setup

Windows:

```powershell
.\setup_windows.cmd
```

The Windows setup wrapper runs `setup_windows.ps1` with a temporary execution-policy bypass for that one run only. It does not permanently change the system policy.

Manual Windows fallback:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_windows.ps1
```

macOS:

```bash
bash setup_macos.sh
```

These scripts create `.venv`, install dependencies, install Playwright Chromium, create missing local files from templates, and run basic validation.

## 3. Manual Install

```bash
npm install
npx playwright install chromium
python -m pip install -r requirements.txt
python -m pip install -r apps/gmail-agent/requirements.txt
```

## 4. Create Private Files

```powershell
Copy-Item config\profile.example.yml config\profile.yml
Copy-Item templates\portals.example.yml portals.yml
Copy-Item .env.example .env
Copy-Item modes\_profile.template.md modes\_profile.md
Copy-Item apps\gmail-agent\.env.example apps\gmail-agent\.env
```

Then create `cv.md` with your CV in Markdown.

## 5. AI Provider Setup

Root `.env` should contain:

```env
AI_PROVIDER_NAME=openrouter
AI_API_KEY=your-provider-key
AI_BASE_URL=
PRIMARY_MODEL=provider/model-one
FALLBACK_MODEL=provider/model-two
SECOND_FALLBACK_MODEL=provider/model-three
```

`AI_PROVIDER_NAME` means provider name. Supported values are `openrouter`, `openai`, `anthropic`, `claude`, `gemini`, `deepseek`, `kimi`, `moonshot`, `glm`, `zhipu`, or `custom`. It does not mean API key name.

For provider examples and Gmail OAuth screenshots, see [AI Career Agent Setup Connection Guidebook PDF](<AI_Career_Agent_Setup_Connection_Guidebook.pdf>).

## 6. Gmail OAuth

AI Career Agent reads Gmail job alerts through Google OAuth. It does not use your Gmail password.

Expected files:

- `apps/gmail-agent/credentials.json`
- `apps/gmail-agent/token.json`

Run `python run.py` and choose Reconnect Gmail if the startup check reports Gmail needs attention.

## 7. LinkedIn Browser Login

LinkedIn uses a local browser profile under `data/gmail-agent/browser_profiles/`. Run `python run.py` and choose Reconnect LinkedIn if startup reports login required.

## 8. Manual JD Scan

Use Manual JD Scan when a job page is blocked, expired, behind a challenge, or available only as pasted text.

```powershell
python run.py
```

## 9. Gmail Scan Limits

Configure limits in `config/profile.yml`:

```yaml
gmail_scan:
  max_job_alerts_to_process: 5
  max_job_links_to_process: 45
```

## 10. Validate

```bash
npm run doctor
npm run verify
python run.py --help
```

Release-package checks:

```bash
npm run release:audit
npm run release:package
```

## 11. Private File Safety

Never commit `.env`, `credentials.json`, `token.json`, `cv.md`, `config/profile.yml`, `modes/_profile.md`, `reports/`, `output/`, runtime data, browser sessions, or backup files.

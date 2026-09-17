# AI Career Agent

AI Career Agent is a local job-search automation tool for controlled, review-first job search work from your own machine.

It can:

- scan Gmail job-alert emails through Gmail OAuth,
- use a local LinkedIn browser session for LinkedIn job pages,
- support Manual JD Scan when a portal blocks automation,
- evaluate job descriptions against `cv.md` and `config/profile.yml`,
- generate Markdown evaluation reports under `reports/`,
- generate executive DOCX CV optimization reports under `data/cv_optimization/reports/`,
- maintain a local application tracker,
- use one AI provider key with three model names,
- send optional email summaries when configured.

AI Career Agent never submits applications automatically. The user always makes the final application decision.

## Recommended Workflow

Run the local app from the project root:

```powershell
python run.py
```

Help and validation:

```powershell
python run.py --help
npm run doctor
npm run verify
```

Setup:

```powershell
.\setup_windows.cmd
```

The Windows setup wrapper runs the PowerShell setup script with a temporary execution-policy bypass for that one run only. If Node.js or Python is missing, the setup script can ask before installing them with `winget`.

Manual Windows fallback:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_windows.ps1
```

macOS:

```bash
bash setup_macos.sh
```

On macOS, if Node.js or Python is missing and Homebrew is installed, the setup script can ask before installing the missing prerequisite with `brew`.

Release-package checks:

```bash
npm run release:audit
npm run release:package
```

Legacy command files may exist from the upstream project, but the recommended AI Career Agent workflow is `python run.py`.

## Main Capabilities

| Capability | Description |
|---|---|
| Gmail Job Scan | Reads Gmail job-alert emails through OAuth and extracts job links. |
| Manual JD Scan | Evaluates pasted job descriptions when scraping is blocked or unavailable. |
| LinkedIn Session | Uses a local browser profile for authenticated LinkedIn pages. |
| AI Evaluation | Compares job descriptions against your CV, profile, preferences, and constraints. |
| Markdown Reports | Saves detailed evaluation reports under `reports/`. |
| Executive DOCX Reports | Saves CV optimization reports under `data/cv_optimization/reports/`. |
| Tracker | Maintains `data/applications.md` using the TSV merge flow. |

## Required Local Files

Create these private files locally:

- `cv.md` - canonical CV in Markdown.
- `config/profile.yml` - target roles, location, compensation, preferences, and Gmail scan limits.
- `modes/_profile.md` - long-form user-specific context.
- `portals.yml` - portal and company scanning configuration.
- `.env` - AI provider configuration.
- `apps/gmail-agent/credentials.json` - Google OAuth desktop-client credentials.
- `apps/gmail-agent/token.json` - generated after Gmail OAuth authorization.

For AI provider/API key setup and Gmail OAuth screenshots, see [AI Career Agent Setup Connection Guidebook PDF](<AI_Career_Agent_Setup_Connection_Guidebook.pdf>).

## AI Provider Setup

Configure one provider/API key and three model names in `.env`:

```env
AI_PROVIDER_NAME=openrouter
AI_API_KEY=your-provider-key
AI_BASE_URL=
PRIMARY_MODEL=provider/model-one
FALLBACK_MODEL=provider/model-two
SECOND_FALLBACK_MODEL=provider/model-three
```

`AI_PROVIDER_NAME` means provider name. Supported values are `openrouter`, `openai`, `anthropic`, `claude`, `gemini`, `deepseek`, `kimi`, `moonshot`, `glm`, `zhipu`, or `custom`. It does not mean API key name.

The three model names must belong to the same configured provider/API key.

## Gmail, LinkedIn, and Manual JD Flow

Gmail uses OAuth, not your Gmail password. If startup reports Gmail needs attention, run `python run.py` and choose Reconnect Gmail.

LinkedIn uses a local browser profile under `data/gmail-agent/browser_profiles/`. If startup reports LinkedIn login required, run `python run.py` and choose Reconnect LinkedIn.

Use Manual JD Scan when a job page is blocked, expired, behind a challenge, or available only as pasted text.

## Gmail Scan Limits

Scan limits live in `config/profile.yml`:

```yaml
gmail_scan:
  max_job_alerts_to_process: 5
  max_job_links_to_process: 45
```

## Outputs

- Markdown evaluation reports: `reports/`
- Executive DOCX reports: `data/cv_optimization/reports/`
- Daily summaries: `reports/daily/`
- Saved job descriptions: `jds/`
- Runtime Gmail-agent data: `data/gmail-agent/`

## Private File Safety

Never commit:

- `.env`
- `credentials.json`
- `token.json`
- `cv.md`
- `config/profile.yml`
- `modes/_profile.md`
- `reports/`
- `output/`
- `jds/`
- runtime data
- browser sessions
- backup files

## Validation

```powershell
npm run doctor
npm run verify
npm run release:audit
node test-all.mjs --quick
```

## Upstream Attribution

AI Career Agent was originally adapted from the open-source Career-Ops project and has been significantly modified.

## Disclaimer

AI Career Agent is a local tool. You are responsible for reviewing generated reports, CV changes, and application answers before using them, and for complying with third-party site terms.

See [LEGAL_DISCLAIMER.md](LEGAL_DISCLAIMER.md) for details.

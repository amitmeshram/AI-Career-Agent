# AI Career Agent Architecture

AI Career Agent is a local job-search automation system. It combines Gmail job-alert ingestion, browser-based job-page scraping, manual JD capture, AI evaluation, report generation, executive DOCX CV optimization reporting, and tracker integrity checks.

## Runtime Entry Point

The recommended entrypoint is:

```powershell
python run.py
```

`python run.py --help` shows available local actions.

## Main Components

| Component | Responsibility |
|---|---|
| `run.py` | Guided local entrypoint for setup, scans, manual input, and app workflows. |
| `apps/gmail-agent/` | Gmail OAuth, job-alert parsing, job-link extraction, scraping orchestration, daily summaries. |
| `cv.md` | Canonical CV source. |
| `config/profile.yml` | User profile, target roles, compensation, preferences, and Gmail scan limits. |
| `modes/_profile.md` | Long-form user-specific context. |
| `modes/` | Evaluation and workflow instructions reused by agents. |
| `tools/` | CV optimization and executive DOCX report generation helpers. |
| `reports/` | Markdown evaluation outputs. |
| `data/cv_optimization/reports/` | Executive DOCX reports. |
| `data/gmail-agent/` | Runtime Gmail-agent state, browser profiles, and caches. |
| `templates/` | CV, portal, and status templates. |

## Data Flow

```text
Gmail OAuth or Manual JD
        |
        v
Job links and metadata
        |
        v
Playwright scrape or manual JD fallback
        |
        v
JD Markdown export
        |
        v
AI evaluation against cv.md + config/profile.yml
        |
        v
Markdown report + executive DOCX report
        |
        v
Tracker TSV merge and daily summary
```

## AI Provider Layer

AI Career Agent uses one provider/API key and three model names from `.env`:

```env
AI_PROVIDER_NAME=openrouter
AI_API_KEY=your-provider-key
AI_BASE_URL=
PRIMARY_MODEL=provider/model-one
FALLBACK_MODEL=provider/model-two
SECOND_FALLBACK_MODEL=provider/model-three
```

`AI_PROVIDER_NAME` means provider name. Supported values are `openrouter`, `openai`, `anthropic`, `claude`, `gemini`, `deepseek`, `kimi`, `moonshot`, `glm`, `zhipu`, or `custom`. It does not mean API key name.

Malformed model output must be rejected. Fake tool-call JSON such as `{"tool":"read"}` is not a valid report.

## Gmail and Browser Layer

Gmail uses OAuth files under `apps/gmail-agent/`:

- `credentials.json`
- `token.json`

LinkedIn and other browser sessions use local profiles under `data/gmail-agent/browser_profiles/`.

## Manual JD Fallback

Some portals block automation or return protocol/security errors. Manual JD Scan is the supported fallback: paste the full JD and evaluate from that captured text.

## Tracker Integrity

New tracker rows should flow through TSV additions and `merge-tracker.mjs`. Do not add new entries directly to `data/applications.md`.

## Private Data Boundary

Never commit `.env`, credentials, tokens, `cv.md`, `config/profile.yml`, `modes/_profile.md`, reports, output, runtime data, browser sessions, or backup files.

## Upstream Attribution

AI Career Agent was originally adapted from the open-source Career-Ops project and has been significantly modified.

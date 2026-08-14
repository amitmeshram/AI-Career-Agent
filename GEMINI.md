# AI Career Agent -- Gemini CLI Context

AI Career Agent is the local job-search automation tool in this folder. It scans Gmail job-alert emails, supports manual JD scans, uses LinkedIn browser sessions, evaluates jobs against `cv.md` and `config/profile.yml`, generates Markdown reports, generates executive DOCX CV optimization reports, and never submits applications automatically.

For complete agent rules, follow `CLAUDE.md` and `AGENTS.md`.

## Current Workflow

```powershell
python run.py
python run.py --help
npm run doctor
npm run verify
npm run release:audit
npm run release:package
```

Legacy command files may exist from the upstream project, but the recommended AI Career Agent workflow is `python run.py`.

For AI model/API key setup and Gmail OAuth screenshots, see [AI Model Connection Guidebook.docx](<AI Model Connection Guidebook.docx>).

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

## Safety Rules

- Never submit applications automatically.
- Stop before Submit, Send, Apply, or equivalent final actions.
- Never invent CV facts, tools, certifications, metrics, domain experience, employers, or achievements.
- Reject malformed AI model output.
- If model output contains fake tool-call JSON such as `{"tool":"read"}`, do not save it as a valid report.
- Keep user-specific customization in `config/profile.yml`, `modes/_profile.md`, or `article-digest.md`.
- Never commit `.env`, credentials, tokens, CV/profile files, reports, output, runtime data, browser sessions, or backup files.
- Use scoped `git add <specific-files>` only. Never use `git add .` in dirty repos.

## Routing

Use the existing mode files when relevant:

| Intent | Mode file |
|---|---|
| Raw JD text or job URL | `modes/auto-pipeline.md` |
| Single evaluation | `modes/oferta.md` |
| Compare jobs | `modes/ofertas.md` |
| Gmail/portal scan | `modes/scan.md` |
| Manual application assistance | `modes/apply.md` |
| Tracker status | `modes/tracker.md` |
| Deep research | `modes/deep.md` |
| Interview prep | `modes/interview-prep.md` |

Do not rewrite mode files unless explicitly asked.

## Upstream Attribution

AI Career Agent was originally adapted from the open-source Career-Ops project and has been significantly modified.
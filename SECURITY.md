# Security Policy

AI Career Agent is a local tool that handles sensitive job-search data. Treat the local folder as private.

## Sensitive Files

Never commit or share `.env`, `credentials.json`, `token.json`, `cv.md`, `config/profile.yml`, `modes/_profile.md`, `reports/`, `output/`, `jds/`, `data/gmail-agent/`, browser sessions, or backup files.

## Gmail OAuth

AI Career Agent uses Gmail OAuth. It should never ask for or store your Gmail password. `credentials.json` and `token.json` are local secrets.

## AI Provider Keys

Store provider keys only in local `.env` files. `AI_PROVIDER_NAME` is the provider name, for example `openrouter`, `openai`, `gemini`, `kimi`, `glm`, or `custom`; it is not the API key name.

## Browser Sessions

LinkedIn and other browser sessions may store cookies or login state under `data/gmail-agent/browser_profiles/`. Treat these folders as secrets.

## Reporting a Security Issue

Report security issues to the current repository owner or maintainer through the private channel used for this local project. Do not include live secrets, tokens, CVs, or Gmail data in public messages.

## Safe Git Practice

Use scoped staging only. Never use `git add .` in a dirty repo.
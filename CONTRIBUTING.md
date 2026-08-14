# Contributing to AI Career Agent

AI Career Agent is a local customized job-search automation tool. Contributions should preserve the current user-reviewed workflow and private-data boundaries.

## Current Workflow

```powershell
python run.py
python run.py --help
npm run doctor
npm run verify
npm run release:audit
npm run release:package
```

## Contribution Rules

- Do not add automatic application submission.
- Do not invent CV facts, tools, certifications, metrics, or domain experience.
- Do not change source code or package scripts unless the issue explicitly requires it.
- Do not add Telegram configuration.
- Do not commit `.env`, credentials, tokens, CV/profile files, reports, output, runtime data, browser sessions, or backup files.
- Use scoped `git add <specific-files>` only. Never use `git add .` in dirty repos.

## Documentation Changes

User-facing docs should describe the tool as AI Career Agent. Keep upstream attribution short and separate where needed.
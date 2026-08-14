# AI Career Agent Instructions for Codex

Read `CLAUDE.md` for the full project instructions, routing, data-contract rules, and safety requirements. They apply equally to Codex.

AI Career Agent is the current local job-search automation tool in this folder.

Key rules:

- Use the current workflow: `python run.py`, `python run.py --help`, `npm run doctor`, and `npm run verify`.
- Do not submit applications automatically. Stop before any final Submit, Send, or Apply action.
- Do not invent CV facts, tools, certifications, metrics, domain experience, employers, or achievements.
- Evaluate jobs only against `cv.md`, `config/profile.yml`, `modes/_profile.md`, and provided job content.
- Reject malformed AI model output. If model output contains fake tool-call JSON such as `{"tool":"read"}`, do not save it as a valid report.
- Keep user customization in `config/profile.yml`, `modes/_profile.md`, or `article-digest.md`; do not put user-specific data in shared mode files.
- Never commit `.env`, credentials, tokens, CV/profile files, reports, output, runtime data, browser sessions, or backup files.
- Use scoped `git add <specific-files>` only. Never use `git add .` in dirty repos.

For AI provider and Gmail OAuth setup, see [AI Model Connection Guidebook.docx](<AI Model Connection Guidebook.docx>).
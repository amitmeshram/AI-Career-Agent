# AI Career Agent Support

AI Career Agent is a local customized job-search automation tool. Support should focus on this repository's current workflow and local files.

## Where to Start

1. Read [README.md](README.md).
2. Follow [SETUP.md](SETUP.md).
3. Review [RUNBOOK.md](RUNBOOK.md) for daily operation.
4. Use [AI Model Connection Guidebook.docx](<AI Model Connection Guidebook.docx>) for AI provider and Gmail OAuth setup.

## Common Commands

```powershell
python run.py
python run.py --help
npm run doctor
npm run verify
npm run release:audit
npm run release:package
```

## Common Issues

| Issue | First check |
|---|---|
| Gmail disconnected | Reconnect Gmail from `python run.py`. |
| LinkedIn login required | Reconnect LinkedIn from `python run.py`. |
| AI model missing | Check root `.env` provider/key/model settings. |
| Job board blocked | Use Manual JD Scan with pasted JD text. |
| Report malformed | Reject it, rerun, or use manual review. |
| Tracker issue | Run `npm run verify`. |

## Private Data Reminder

Do not paste secrets, tokens, CV content, private reports, or browser-session data into public support channels. Never commit `.env`, credentials, tokens, `cv.md`, `config/profile.yml`, `modes/_profile.md`, reports, output, runtime data, browser sessions, or backup files.

## Upstream Attribution

AI Career Agent was originally adapted from the open-source Career-Ops project and has been significantly modified. Upstream community links should not be treated as current support channels for this modified tool.
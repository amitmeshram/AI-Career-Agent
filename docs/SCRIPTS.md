# AI Career Agent Scripts

Use these scripts from the project root.

## User Workflow

```powershell
python run.py
python run.py --help
```

## Setup and Validation

```powershell
.\setup_windows.cmd
npm run doctor
npm run verify
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

## Release Checks

```bash
npm run release:audit
npm run release:package
node test-all.mjs --quick
```

## Tracker Maintenance

```bash
node verify-pipeline.mjs
node normalize-statuses.mjs
node dedup-tracker.mjs
node merge-tracker.mjs
```

New application rows should flow through TSV additions and `merge-tracker.mjs`, not direct manual row creation.

## Report Generation

Executive DOCX reports are generated with:

```bash
python tools/generate_executive_report_from_evaluation.py --report <report.md> --cv cv.md --force
```

## Private File Safety

Never commit `.env`, credentials, tokens, CV/profile files, reports, output, runtime data, browser sessions, or backup files.

# AI Career Agent Scripts

Use these scripts from the project root.

## User Workflow

```powershell
python run.py
python run.py --help
```

## Setup and Validation

```powershell
.\setup_windows.ps1
npm run doctor
npm run verify
```

macOS:

```bash
bash setup_macos.sh
```

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
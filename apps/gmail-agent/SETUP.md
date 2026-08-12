# Gmail Agent Setup

Run these steps from the Career-Ops root folder, not from this subfolder.

## 1. Create private Gmail-agent files

Windows PowerShell:

```powershell
Copy-Item apps\gmail-agent\.env.example apps\gmail-agent\.env
```

macOS Terminal:

```bash
cp apps/gmail-agent/.env.example apps/gmail-agent/.env
```

Fill in local values in `apps/gmail-agent/.env`.

## 2. Add Google OAuth credentials

Create a Google OAuth desktop client and save it as:

```text
apps/gmail-agent/credentials.json
```

This file is private and must not be shared.

## 3. Install dependencies

The root setup scripts install these dependencies automatically:

Windows PowerShell:

```powershell
.\setup_windows.ps1
```

macOS Terminal:

```bash
bash setup_macos.sh
```

Manual install:

```bash
python -m pip install -r apps/gmail-agent/requirements.txt
python -m playwright install chromium
```

If a root `wheels/` folder is included:

```bash
python -m pip install --no-index --find-links wheels -r apps/gmail-agent/requirements.txt
```

## 4. Run

```bash
python apps/gmail-agent/main.py
```

Use the startup health-check menu to reconnect Gmail or LinkedIn when needed.
Gmail tokens and LinkedIn browser profiles are created locally under ignored
runtime paths and must not be shared.

# Setup

Run these commands from the folder that contains `package.json` and `run.py`.

## 1. Install prerequisites

- Node.js 18+
- Python 3.10+
- PowerShell on Windows or Terminal on macOS
- Optional: Go 1.21+ for the dashboard

## 2. Run one-command setup

Windows PowerShell:

```powershell
.\setup_windows.ps1
```

macOS Terminal:

```bash
bash setup_macos.sh
```

These scripts create `.venv`, install Python and Node dependencies, install
Playwright Chromium, create missing local config files from templates, and run
basic validation.

## 3. Manual dependency install

```bash
npm install
npx playwright install chromium
python -m pip install -r requirements.txt
python -m pip install -r apps/gmail-agent/requirements.txt
```

If a `wheels/` folder is included, Python packages can be installed offline:

```bash
python -m pip install --no-index --find-links wheels -r requirements.txt
```

## 4. Create private local files

Windows PowerShell:

```powershell
Copy-Item config\profile.example.yml config\profile.yml
Copy-Item templates\portals.example.yml portals.yml
Copy-Item .env.example .env
Copy-Item modes\_profile.template.md modes\_profile.md
Copy-Item apps\gmail-agent\.env.example apps\gmail-agent\.env
```

macOS Terminal:

```bash
cp config/profile.example.yml config/profile.yml
cp templates/portals.example.yml portals.yml
cp .env.example .env
cp modes/_profile.template.md modes/_profile.md
cp apps/gmail-agent/.env.example apps/gmail-agent/.env
```

Then create `cv.md` with your CV in Markdown.

## 5. Validate

```bash
npm run doctor
python run.py --help
```

## 6. Start

```bash
python run.py
```

Never share `.env`, `cv.md`, `config/profile.yml`, `portals.yml`, Gmail tokens,
LinkedIn browser profiles, generated job descriptions under `jds/`, Gmail scanner state under `data/gmail-agent/`, reports, or outputs.

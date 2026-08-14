# AI Career Agent Governance

AI Career Agent is maintained as a local customized tool in this repository.

## Decision Model

The current owner decides product direction, local workflow, supported portals, documentation standards, and release readiness.

## Maintainer Responsibilities

- Protect private files and runtime data.
- Keep setup documentation aligned with `python run.py` workflow.
- Keep AI provider wording consistent.
- Preserve the no-auto-submit rule.
- Validate changes before release packaging.

## Contribution Review

Before accepting changes, verify:

```powershell
npm run verify
npm run release:audit
node test-all.mjs --quick
```

Use scoped staging only. Never use `git add .` in dirty repos.
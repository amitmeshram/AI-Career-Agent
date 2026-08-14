# AI Career Agent Customization

Customize AI Career Agent through user-layer files, not shared system defaults.

## User-Layer Files

- `cv.md` - canonical CV.
- `config/profile.yml` - target roles, compensation, location, preferences, and Gmail scan limits.
- `modes/_profile.md` - long-form user-specific context and scoring preferences.
- `article-digest.md` - proof points from projects, articles, or achievements.
- `portals.yml` - portal and company scanning configuration.

## Common Customizations

| Request | Where to edit |
|---|---|
| Target roles | `config/profile.yml`, `modes/_profile.md` |
| Salary range | `config/profile.yml` |
| Deal-breakers | `config/profile.yml`, `modes/_profile.md` |
| Proof points | `article-digest.md` |
| Gmail scan limits | `config/profile.yml` |
| Portal/company filters | `portals.yml` |

## AI Provider

Root `.env` uses one provider/API key and three model names:

```env
AI_PROVIDER_NAME=openrouter
AI_API_KEY=your-provider-key
PRIMARY_MODEL=provider/model-one
FALLBACK_MODEL=provider/model-two
SECOND_FALLBACK_MODEL=provider/model-three
```

`AI_PROVIDER_NAME` means provider name, not API key name.

## Rules

- Do not put user-specific content in `modes/_shared.md`.
- Do not invent CV facts, tools, certifications, metrics, or domain experience.
- Do not submit applications automatically.
- Do not commit private files, reports, output, runtime data, browser sessions, or backup files.
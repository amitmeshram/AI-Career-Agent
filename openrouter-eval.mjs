#!/usr/bin/env node

import {
  readFileSync,
  existsSync,
  writeFileSync,
  mkdirSync,
  readdirSync
} from 'fs';
import { join } from 'path';
import dotenv from 'dotenv';
import OpenAI from 'openai';
import { CV_PATH, ENV_PATH, PROFILE_PATH, REPORTS_DIR, ROOT, TRACKER_PATH } from './paths.mjs';

dotenv.config({ path: ENV_PATH });

const PATHS = {
  shared: join(ROOT, 'modes', '_shared.md'),
  oferta: join(ROOT, 'modes', 'oferta.md'),
  profileMode: join(ROOT, 'modes', '_profile.md'),
  articleDigest: join(ROOT, 'article-digest.md'),
  cv: CV_PATH,
  profile: PROFILE_PATH,
  reports: REPORTS_DIR,
  tracker: TRACKER_PATH,
  trackerAdditions: join(ROOT, 'batch', 'tracker-additions')
};

const providerAliases = {
  claude: 'anthropic',
  moonshot: 'kimi',
  zhipu: 'glm',
  bigmodel: 'glm'
};

function normalizeProviderName(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return providerAliases[normalized] || normalized;
}

const provider = normalizeProviderName(
  process.env.AI_PROVIDER_NAME
  || (process.env.OPENROUTER_API_KEY ? 'openrouter' : '')
  || (process.env.OPENAI_API_KEY ? 'openai' : '')
  || (process.env.ANTHROPIC_API_KEY || process.env.CLAUDE_API_KEY ? 'anthropic' : '')
  || (process.env.DEEPSEEK_API_KEY ? 'deepseek' : '')
  || (process.env.KIMI_API_KEY || process.env.MOONSHOT_API_KEY ? 'kimi' : '')
  || (process.env.GLM_API_KEY || process.env.ZHIPU_API_KEY ? 'glm' : '')
);

const providerApiKeys = {
  openrouter: process.env.OPENROUTER_API_KEY,
  openai: process.env.OPENAI_API_KEY,
  anthropic: process.env.ANTHROPIC_API_KEY || process.env.CLAUDE_API_KEY,
  deepseek: process.env.DEEPSEEK_API_KEY,
  kimi: process.env.KIMI_API_KEY || process.env.MOONSHOT_API_KEY,
  glm: process.env.GLM_API_KEY || process.env.ZHIPU_API_KEY,
  custom: process.env.AI_API_KEY
};

const apiKey = process.env.AI_API_KEY || providerApiKeys[provider];

const providerBaseURLs = {
  openrouter: 'https://openrouter.ai/api/v1',
  deepseek: 'https://api.deepseek.com',
  kimi: 'https://api.moonshot.ai/v1',
  glm: 'https://open.bigmodel.cn/api/paas/v4',
  custom: process.env.AI_BASE_URL
};

const baseURL = process.env.AI_BASE_URL || providerBaseURLs[provider];
const openAICompatibleProviders = new Set(['openrouter', 'openai', 'custom', 'deepseek', 'kimi', 'glm']);
const nativeAnthropicProviders = new Set(['anthropic']);
const supportedProviders = new Set([...openAICompatibleProviders, ...nativeAnthropicProviders]);

if (!apiKey) {
  console.error(`AI_API_KEY missing in .env for AI_PROVIDER_NAME=${provider || '(missing)'}`);
  console.error('Set AI_API_KEY, or the provider-specific key such as OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, KIMI_API_KEY, MOONSHOT_API_KEY, GLM_API_KEY, or ZHIPU_API_KEY.');
  process.exit(1);
}

if (!provider) {
  console.error('AI_PROVIDER_NAME missing in .env');
  process.exit(1);
}

if (provider === 'gemini') {
  console.error('For Gemini, use gemini-eval.mjs.');
  process.exit(1);
}

if (provider && !supportedProviders.has(provider)) {
  console.error(`AI_PROVIDER_NAME=${provider} is not supported by openrouter-eval.mjs.`);
  console.error(`Use one of: ${Array.from(supportedProviders).sort().join(', ')}.`);
  process.exit(1);
}

if (provider === 'custom' && !baseURL) {
  console.error('AI_BASE_URL is required when AI_PROVIDER_NAME=custom');
  process.exit(1);
}

const clientOptions = openAICompatibleProviders.has(provider) ? {
  apiKey,
  defaultHeaders: provider === 'openrouter' || !provider ? {
    'HTTP-Referer': 'http://localhost',
    'X-Title': 'AI Career Agent'
  } : undefined
} : null;

if (clientOptions && baseURL) {
  clientOptions.baseURL = baseURL;
}

const client = clientOptions ? new OpenAI(clientOptions) : null;

const modelAttempts = [
  { name: process.env.PRIMARY_MODEL, timeoutMs: 240_000 },
  { name: process.env.FALLBACK_MODEL, timeoutMs: 240_000 },
  { name: process.env.SECOND_FALLBACK_MODEL || process.env.SECOND_FALLBACK || process.env.SECONDARY_FALLBACK_MODEL, timeoutMs: 240_000 }
].filter(model => Boolean(model.name));

const args = process.argv.slice(2);

if (args.length < 2 || args[0] !== '--file') {
  console.log('Usage: node openrouter-eval.mjs --file path/to/jd.md');
  process.exit(1);
}

const filePath = args[1];

if (!existsSync(filePath)) {
  console.error(`File not found: ${filePath}`);
  process.exit(1);
}

function readRequiredFile(path, description, setupHint = 'Complete first-time setup before evaluating jobs.') {
  if (!existsSync(path)) {
    console.error(`${description} not found: ${path}`);
    console.error(setupHint);
    process.exit(1);
  }
  return readFileSync(path, 'utf-8');
}

const jdText = readFileSync(filePath, 'utf-8');
const cvText = readRequiredFile(PATHS.cv, 'cv.md', 'Add your CV to cv.md before evaluating jobs.');
const profileText = readRequiredFile(PATHS.profile, 'config/profile.yml');
const profileModeText = readRequiredFile(PATHS.profileMode, 'modes/_profile.md');
const articleDigestText = existsSync(PATHS.articleDigest)
  ? readFileSync(PATHS.articleDigest, 'utf-8')
  : 'article-digest.md is not present in this project. Do not invent proof points from it.';
const ofertaText = readRequiredFile(PATHS.oferta, 'modes/oferta.md', 'The evaluator mode file is missing. Restore the project files before evaluating jobs.');
const sharedText = readRequiredFile(PATHS.shared, 'modes/_shared.md', 'The shared mode file is missing. Restore the project files before evaluating jobs.');

const VALID_RECOMMENDATIONS = new Set([
  'Apply',
  'Consider',
  'Deprioritize',
  'Reject'
]);

const VALID_FIT_TYPES = new Set([
  'PMO',
  'Strategy',
  'Analytics',
  'Transformation',
  'Finance',
  'Sales',
  'Technical',
  'Other'
]);

const VALID_SENIORITY_MATCHES = new Set([
  'Good',
  'Stretch',
  'Under',
  'Overqualified'
]);

function extractMetadataJson(text) {
  const value = String(text || '');
  const match = value.match(/```json\s*([\s\S]*?)\s*```/);

  if (match) {
    try {
      return JSON.parse(match[1]);
    } catch (error) {
      return {};
    }
  }

  const trimmed = value.trimStart();
  if (!trimmed.startsWith('{')) {
    return {};
  }

  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let index = 0; index < trimmed.length; index += 1) {
    const char = trimmed[index];

    if (escaped) {
      escaped = false;
      continue;
    }

    if (char === '\\') {
      escaped = true;
      continue;
    }

    if (char === '"') {
      inString = !inString;
      continue;
    }

    if (inString) {
      continue;
    }

    if (char === '{') {
      depth += 1;
    }

    if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        const candidate = trimmed.slice(0, index + 1);
        try {
          return JSON.parse(candidate);
        } catch (error) {
          return {};
        }
      }
    }
  }

  return {};
}

function normalizeMetadata(metadata) {
  const normalized = {
    ...(metadata || {})
  };

  if (normalized.seniority_match === 'Overqualified') {
    normalized.seniority_match = 'Stretch';
  }

  return normalized;
}

function replaceLeadingMetadataJson(output, metadata) {
  const leadingWhitespace = String(output || '').match(/^\s*/)[0];
  const trimmed = String(output || '').slice(leadingWhitespace.length);

  if (!trimmed.startsWith('{')) {
    return output;
  }

  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let index = 0; index < trimmed.length; index += 1) {
    const char = trimmed[index];

    if (escaped) {
      escaped = false;
      continue;
    }

    if (char === '\\') {
      escaped = true;
      continue;
    }

    if (char === '"') {
      inString = !inString;
      continue;
    }

    if (inString) {
      continue;
    }

    if (char === '{') {
      depth += 1;
    }

    if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        return `${leadingWhitespace}${JSON.stringify(metadata, null, 2)}${trimmed.slice(index + 1)}`;
      }
    }
  }

  return output;
}

function hasMetadataEnvelope(text) {
  const output = String(text || '');
  return /^## Evaluation Metadata\b/m.test(output)
    || /^\s*\{/.test(output);
}

function parseReportMetadata(text) {
  return normalizeMetadata(extractMetadataJson(text));
}

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch (error) {
    return {};
  }
}

function containsFakeToolCall(text) {
  const normalized = String(text || '').trim();

  if (/^\s*\{\s*"tool"\s*:/im.test(normalized)) {
    return true;
  }

  return normalized
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .some(line => {
      if (!line.startsWith('{') || !line.endsWith('}')) {
        return false;
      }

      try {
        const parsed = parseJson(line);
        return parsed
          && typeof parsed === 'object'
          && typeof parsed.tool === 'string'
          && !Object.prototype.hasOwnProperty.call(parsed, 'schema_version');
      } catch (error) {
        return false;
      }
    });
}

function validateMetadata(metadata) {
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) {
    return 'missing valid Evaluation Metadata JSON block';
  }

  if (metadata.schema_version !== '1.0') {
    return 'metadata schema_version must be "1.0"';
  }

  if (typeof metadata.score !== 'number' || metadata.score < 0 || metadata.score > 5) {
    return 'metadata score must be a number from 0 to 5';
  }

  if (!VALID_RECOMMENDATIONS.has(metadata.recommendation)) {
    return 'metadata recommendation is invalid';
  }

  if (!VALID_FIT_TYPES.has(metadata.fit_type)) {
    return 'metadata fit_type is invalid';
  }

  if (!VALID_SENIORITY_MATCHES.has(metadata.seniority_match)) {
    return 'metadata seniority_match is invalid';
  }

  const requiredFields = [
    'company',
    'role',
    'location',
    'score',
    'legitimacy',
    'recommendation',
    'fit_type',
    'seniority_match',
    'why_apply',
    'main_gap'
  ];

  for (const field of requiredFields) {
    if (!Object.prototype.hasOwnProperty.call(metadata, field)) {
      return `metadata field missing: ${field}`;
    }
  }

  return '';
}

function validateReportOutput(text) {
  const output = String(text || '').trim();

  if (!output) {
    return 'model returned empty output';
  }

  if (containsFakeToolCall(output)) {
    return 'model returned fake tool-call JSON instead of a report';
  }

  if (!hasMetadataEnvelope(output)) {
    return 'report is missing Evaluation Metadata';
  }

  const metadataError = validateMetadata(parseReportMetadata(output));
  if (metadataError) {
    return metadataError;
  }

  const requiredPatterns = [
    [/^#{1,2}\s*A\)\s*Role Summary\b/mi, 'Block A - Role Summary'],
    [/^#{1,2}\s*B\)\s*Match with CV\b/mi, 'Block B - Match with CV'],
    [/^#{1,2}\s*G\)\s*Posting Legitimacy\b/mi, 'Block G - Posting Legitimacy']
  ];

  for (const [pattern, label] of requiredPatterns) {
    if (!pattern.test(output)) {
      return `report is missing required section: ${label}`;
    }
  }

  return '';
}

const prompt = `
=============================
EVALUATOR RUNTIME CONSTRAINTS
=============================

This OpenRouter evaluator cannot call WebSearch, WebFetch, Playwright, Read,
Write, Edit, Bash, or any external tool. Do not output tool-call JSON.
Do not ask to read files. The required local files are already included below.
Use only the provided context. For compensation, company hiring signals, posting
freshness, or legitimacy details that require live external research, mark the
signal as unavailable or unverified unless it is present in the job description
or provided context.

If article-digest.md is unavailable, do not invent additional proof points.

=============================
SHARED MODE RULES
=============================

${sharedText}

=============================
USER PROFILE OVERRIDES
=============================

${profileModeText}

=============================
USER PROFILE CONFIG
=============================

${profileText}

=============================
ARTICLE DIGEST
=============================

${articleDigestText}

=============================
EVALUATION MODE RULES
=============================

${ofertaText}

=============================
CANDIDATE CV
=============================

${cvText}

=============================
JOB DESCRIPTION
=============================

${jdText}
`;

console.log('📂 Loading context files...');

async function tryModel(modelName, prompt, timeoutMs) {
  console.log(`🤖 Trying model: ${modelName}`);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    if (nativeAnthropicProviders.has(provider)) {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify({
          model: modelName,
          max_tokens: Number(process.env.ANTHROPIC_MAX_TOKENS || 8192),
          temperature: 0.3,
          system: 'You are an expert AI career evaluator and recruiter. You cannot call tools in this runtime. Never output tool-call JSON; produce the report directly from the provided context.',
          messages: [
            {
              role: 'user',
              content: prompt
            }
          ]
        }),
        signal: controller.signal
      });

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        const message = payload?.error?.message || payload?.message || response.statusText;
        throw new Error(`Anthropic API error (${response.status}): ${message}`);
      }

      const text = Array.isArray(payload.content)
        ? payload.content
          .filter(part => part && part.type === 'text')
          .map(part => part.text || '')
          .join('\n')
        : '';

      return {
        choices: [
          {
            message: {
              content: text
            }
          }
        ]
      };
    }

    const response = await client.chat.completions.create({
    model: modelName,
    messages: [
      {
        role: 'system',
        content: 'You are an expert AI career evaluator and recruiter. You cannot call tools in this runtime. Never output tool-call JSON; produce the report directly from the provided context.'
      },
      {
        role: 'user',
        content: prompt
      }
    ],
      temperature: 0.3
    }, {
      signal: controller.signal
    });

    return response;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`Model timed out after ${timeoutMs / 1000} seconds`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}


async function runEvaluation() {

  for (const modelAttempt of modelAttempts) {
    const { name: modelName, timeoutMs } = modelAttempt;

    try {

      const response = await tryModel(modelName, prompt, timeoutMs);

      const output = response.choices[0].message.content;

      console.log('\n══════════════════════════════════════════════════════════════════');
      console.log(`  CAREER-OPS EVALUATION — powered by ${modelName}`);
      console.log('══════════════════════════════════════════════════════════════════\n');

      console.log(output);

      if (!existsSync(PATHS.reports)) {
        mkdirSync(PATHS.reports, { recursive: true });
      }

      const timestamp = new Date().toISOString().split('T')[0];

      function slugify(text) {
        return String(text || 'unknown')
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-+|-+$/g, '')
          .slice(0, 80) || 'unknown';
      }

      function extractMetadataValue(label, text) {
        const regex = new RegExp(`\\*\\*${label}:\\*\\*\\s*(.+)`, 'i');
        const match = text.match(regex);
        return match ? match[1].trim() : '';
      }

      function isUsableMetadataValue(value) {
        const normalized = String(value || '').trim().toLowerCase();
        return Boolean(normalized)
          && !['unknown', 'unknown company', 'unknown-company', 'unknown role', 'unknown-role'].includes(normalized);
      }

      function extractBasicDetail(label, text) {
        return extractMetadataValue(label, text).replace(/^["']|["']$/g, '').trim();
      }

      function parseTitleCompanyFromText(text) {
        const lines = String(text || '')
          .split(/\r?\n/)
          .map(line => line.trim())
          .filter(Boolean)
          .slice(0, 20);

        for (const line of lines) {
          const match = line.match(/^(.+?)\s+(?:at|@)\s+(.+?)(?:\s*[-|]\s*.+)?$/i);
          if (match) {
            return {
              role: match[1].trim(),
              company: match[2].trim()
            };
          }
        }

        return {};
      }

      function resolveCompanyRole(metadata, jdText) {
        const parsed = parseTitleCompanyFromText(jdText);
        return {
          company: isUsableMetadataValue(metadata.company)
            ? metadata.company.trim()
            : (
              extractBasicDetail('Company', jdText)
              || parsed.company
              || 'unknown-company'
            ),
          role: isUsableMetadataValue(metadata.role)
            ? metadata.role.trim()
            : (
              extractBasicDetail('Job Title', jdText)
              || extractBasicDetail('Role', jdText)
              || parsed.role
              || 'unknown-role'
            ),
          location: isUsableMetadataValue(metadata.location)
            ? metadata.location.trim()
            : (
              extractBasicDetail('Location', jdText)
              || 'Not Mentioned'
            )
        };
      }

      function getNextReportNumber() {
        if (!existsSync(PATHS.reports)) {
          mkdirSync(PATHS.reports, { recursive: true });
        }

        const files = readdirSync(PATHS.reports)
        .filter(file => file.endsWith('.md'));

        const numbers = files
          .map(file => {
            const match = file.match(/^(\d+)-/);
            return match ? Number(match[1]) : 0;
          })
          .filter(number => number > 0);

        return numbers.length ? Math.max(...numbers) + 1 : 1;
      }

      function applyResolvedMetadata(output, metadata, resolved) {
        const patchedMetadata = {
          ...metadata,
          company: resolved.company,
          role: resolved.role,
          location: resolved.location
        };

        if (output.match(/```json\s*([\s\S]*?)\s*```/)) {
          return output.replace(
            /```json\s*([\s\S]*?)\s*```/,
            `\`\`\`json\n${JSON.stringify(patchedMetadata, null, 2)}\n\`\`\``
          );
        }

        return replaceLeadingMetadataJson(output, patchedMetadata);
      }


      function sanitizeReportOutput(text) {
        return String(text || '')
          .replace(/\n---\s*\n\*\*Action Taken:\*\*[\s\S]*$/i, '')
          .replace(/\n\*\*Action Taken:\*\*[\s\S]*$/i, '')
          .trimEnd() + '\n';
      }

      function ensureTrackerFile() {
        const dataDir = join(ROOT, 'data');
        if (!existsSync(dataDir)) {
          mkdirSync(dataDir, { recursive: true });
        }
        if (!existsSync(PATHS.tracker)) {
          writeFileSync(
            PATHS.tracker,
            '# Applications Tracker\n\n| # | Date | Company | Role | Score | Status | PDF | Report | Notes |\n|---|------|---------|------|-------|--------|-----|--------|-------|\n',
            'utf-8'
          );
        }
      }

      function normalizeScore(value, text) {
        const raw = String(value || '').trim();
        const fromValue = raw.match(/\d+(?:\.\d+)?/);
        if (fromValue) {
          return `${Number(fromValue[0]).toFixed(1)}/5`;
        }

        const fromText = String(text || '').match(/\*\*Score:\*\*\s*(\d+(?:\.\d+)?)(?:\/5)?/i);
        if (fromText) {
          return `${Number(fromText[1]).toFixed(1)}/5`;
        }

        return 'N/A';
      }

      function tsvValue(value) {
        return String(value || '').replace(/[\t\r\n]+/g, ' ').trim();
      }

      function writeTrackerAddition({ reportNumber, date, company, role, score, reportFileName, companySlug }) {
        ensureTrackerFile();
        if (!existsSync(PATHS.trackerAdditions)) {
          mkdirSync(PATHS.trackerAdditions, { recursive: true });
        }

        const entryNumber = Number(reportNumber);
        const reportLink = `[${reportNumber}](reports/${reportFileName})`;
        const line = [
          entryNumber,
          date,
          tsvValue(company),
          tsvValue(role),
          'Evaluated',
          score,
          '\u274c',
          reportLink,
          'Generated by openrouter-eval.mjs'
        ].join('\t') + '\n';

        const additionPath = join(PATHS.trackerAdditions, `${reportNumber}-${companySlug}.tsv`);
        writeFileSync(additionPath, line, 'utf-8');
        return additionPath;
      }
      const metadata = parseReportMetadata(output);
      const validationError = validateReportOutput(output);
      if (validationError) {
        throw new Error(`Invalid model output rejected: ${validationError}`);
      }

      const resolved = resolveCompanyRole(metadata, jdText);
      const resolvedOutput = sanitizeReportOutput(applyResolvedMetadata(output, metadata, resolved));
      const companySlug = slugify(resolved.company);
      const roleSlug = slugify(resolved.role);
      const reportNumber = getNextReportNumber().toString().padStart(3, '0');

      const reportFileName = `${reportNumber}-${companySlug}-${roleSlug}-${timestamp}.md`;

      const reportPath = join(PATHS.reports, reportFileName);

      writeFileSync(reportPath, resolvedOutput, 'utf-8');

      const score = normalizeScore(metadata.score, resolvedOutput);
      const trackerAdditionPath = writeTrackerAddition({
        reportNumber,
        date: timestamp,
        company: resolved.company,
        role: resolved.role,
        score,
        reportFileName,
        companySlug
      });

      console.log(`\nReport saved: ${reportPath}`);
      console.log(`Tracker addition saved: ${trackerAdditionPath}`);

      return;

    } catch (error) {

      console.log(`\n❌ Model failed: ${modelName}`);
      console.log(error.message);

    }
  }

  console.log('\n❌ All models failed.');
  process.exitCode = 1;
}
runEvaluation();

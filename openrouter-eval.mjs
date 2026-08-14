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
import { CV_PATH, ENV_PATH, REPORTS_DIR, ROOT, TRACKER_PATH } from './paths.mjs';

dotenv.config({ path: ENV_PATH });

const PATHS = {
  shared: join(ROOT, 'modes', '_shared.md'),
  oferta: join(ROOT, 'modes', 'oferta.md'),
  cv: CV_PATH,
  reports: REPORTS_DIR,
  tracker: TRACKER_PATH,
  trackerAdditions: join(ROOT, 'batch', 'tracker-additions')
};

const provider = String(
  process.env.AI_PROVIDER_NAME
  || (process.env.OPENROUTER_API_KEY ? 'openrouter' : '')
  || (process.env.OPENAI_API_KEY ? 'openai' : '')
).trim().toLowerCase();
const apiKey = process.env.AI_API_KEY || process.env.OPENROUTER_API_KEY || process.env.OPENAI_API_KEY;

const providerBaseURLs = {
  openrouter: 'https://openrouter.ai/api/v1',
  custom: process.env.AI_BASE_URL
};

const baseURL = process.env.AI_BASE_URL || providerBaseURLs[provider];

if (!apiKey) {
  console.error('AI_API_KEY missing in .env');
  process.exit(1);
}

if (!provider) {
  console.error('AI_PROVIDER_NAME missing in .env');
  process.exit(1);
}

if (provider && !['openrouter', 'openai', 'custom'].includes(provider)) {
  console.error(`AI_PROVIDER_NAME=${provider} is not supported by openrouter-eval.mjs.`);
  console.error('Use provider openrouter, openai, or custom for this evaluator.');
  console.error('For Gemini, use gemini-eval.mjs.');
  process.exit(1);
}

if (provider === 'custom' && !baseURL) {
  console.error('AI_BASE_URL is required when AI_PROVIDER_NAME=custom');
  process.exit(1);
}

const clientOptions = {
  apiKey,
  defaultHeaders: provider === 'openrouter' || !provider ? {
    'HTTP-Referer': 'http://localhost',
    'X-Title': 'AI Career Agent'
  } : undefined
};

if (baseURL) {
  clientOptions.baseURL = baseURL;
}

const client = new OpenAI(clientOptions);

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

const jdText = readFileSync(filePath, 'utf-8');
const cvText = readFileSync(PATHS.cv, 'utf-8');
const ofertaText = readFileSync(PATHS.oferta, 'utf-8');
const sharedText = readFileSync(PATHS.shared, 'utf-8');

const prompt = `
${sharedText}

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
    const response = await client.chat.completions.create({
    model: modelName,
    messages: [
      {
        role: 'system',
        content: 'You are an expert AI career evaluator and recruiter.'
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

      function extractMetadataJson(text) {
        const match = text.match(/```json\s*([\s\S]*?)\s*```/);

        if (!match) {
          return {};
        }

        try {
          return JSON.parse(match[1]);
        } catch (error) {
          return {};
        }
      }

      function applyResolvedMetadata(output, metadata, resolved) {
        const hasJsonMetadata = output.match(/```json\s*([\s\S]*?)\s*```/);
        if (!hasJsonMetadata) {
          return output;
        }

        const patchedMetadata = {
          ...metadata,
          company: resolved.company,
          role: resolved.role,
          location: resolved.location
        };

        return output.replace(
          /```json\s*([\s\S]*?)\s*```/,
          `\`\`\`json\n${JSON.stringify(patchedMetadata, null, 2)}\n\`\`\``
        );
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
      const metadata = extractMetadataJson(output);
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
}
runEvaluation();

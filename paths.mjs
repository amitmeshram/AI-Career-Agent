import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

export const ROOT = dirname(fileURLToPath(import.meta.url));

export const DATA_DIR = join(ROOT, 'data');
export const REPORTS_DIR = join(ROOT, 'reports');
export const OUTPUT_DIR = join(ROOT, 'output');
export const JDS_DIR = join(ROOT, 'jds');

export const CV_PATH = join(ROOT, 'cv.md');
export const PROFILE_PATH = join(ROOT, 'config', 'profile.yml');
export const PORTALS_PATH = join(ROOT, 'portals.yml');
export const TRACKER_PATH = join(DATA_DIR, 'applications.md');
export const PIPELINE_PATH = join(DATA_DIR, 'pipeline.md');
export const SCAN_HISTORY_PATH = join(DATA_DIR, 'scan-history.tsv');
export const ENV_PATH = join(ROOT, '.env');

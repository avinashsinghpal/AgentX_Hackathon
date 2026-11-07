#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const legalConfigFile = path.join(process.cwd(), 'apps', 'web', 'config', 'legal.config.ts');

if (!fs.existsSync(legalConfigFile)) {
  console.error(`[CHECK FAILED] Legal config not found at: ${legalConfigFile}`);
  process.exit(1);
}

const content = fs.readFileSync(legalConfigFile, 'utf8');
const isProduction = process.env.NODE_ENV === 'production' || process.env.ENV === 'production' || process.argv.includes('--production');

const placeholderMatches = content.match(/\[PLACEHOLDER[^\]]*\]/g) || [];

if (placeholderMatches.length > 0) {
  if (isProduction) {
    console.error(`\n[CHECK FAILED] Found ${placeholderMatches.length} legal placeholder(s) in production build:`);
    placeholderMatches.forEach((ph) => console.error(`  - ${ph}`));
    console.error('All legal details must be finalized prior to production release.');
    process.exit(1);
  } else {
    console.log(`[CHECK WARNING] Found ${placeholderMatches.length} legal placeholders (permitted in development mode).`);
    process.exit(0);
  }
} else {
  console.log('[CHECK PASSED] All legal configuration values are configured.');
  process.exit(0);
}


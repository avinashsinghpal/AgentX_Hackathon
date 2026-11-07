#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const TARGET_DIRS = [
  path.join(process.cwd(), 'apps', 'web', 'app'),
  path.join(process.cwd(), 'apps', 'web', 'components'),
  path.join(process.cwd(), 'apps', 'web', 'lib'),
  path.join(process.cwd(), 'apps', 'web', 'hooks'),
];

const EXTENSIONS = new Set(['.ts', '.tsx', '.js', '.jsx', '.css']);
const URL_REGEX = /https?:\/\/[^\s"'`<>]+/g;

let violations = [];

function scanDir(dir) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      scanDir(fullPath);
    } else if (entry.isFile() && EXTENSIONS.has(path.extname(entry.name))) {
      const content = fs.readFileSync(fullPath, 'utf8');
      const matches = content.match(URL_REGEX);
      if (matches) {
        for (const match of matches) {
          // Allow internal xml namespaces or local schemas if any
          if (match.includes('w3.org')) continue;
          violations.push({
            file: path.relative(process.cwd(), fullPath),
            url: match,
          });
        }
      }
    }
  }
}

for (const dir of TARGET_DIRS) {
  scanDir(dir);
}

if (violations.length > 0) {
  console.error('\n[CHECK FAILED] External asset hosts detected in frontend source:');
  for (const v of violations) {
    console.error(`  - ${v.file}: ${v.url}`);
  }
  process.exit(1);
} else {
  console.log('[CHECK PASSED] Zero external runtime asset URLs found in frontend source.');
  process.exit(0);
}


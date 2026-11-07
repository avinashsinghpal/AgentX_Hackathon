#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const SCAN_DIRS = [
  path.join(process.cwd(), 'apps'),
  path.join(process.cwd(), 'docs'),
  path.join(process.cwd(), 'scripts'),
];

const IGNORE_DIRS = new Set([
  'node_modules',
  '.next',
  '.git',
  '__pycache__',
  '.pytest_cache',
  'dist',
  'build',
  '.venv',
]);

const ALLOWED_CHARS = new Set(['©', '®', '™', '₹', '₹', '€', '£', '$']);

// Regex matching Unicode extended pictographic characters
const EMOJI_REGEX = /\p{Extended_Pictographic}/gu;

let violations = [];

function isExcludedFile(filePath) {
  // Exclude test fixtures that explicitly simulate customer text
  return (
    filePath.includes('customer_emoji_fixture') ||
    filePath.includes('test_emoji_handling') ||
    filePath.includes('customer_text_simulation')
  );
}

function scan(currentPath) {
  if (!fs.existsSync(currentPath)) return;
  const stat = fs.statSync(currentPath);

  if (stat.isDirectory()) {
    const dirName = path.basename(currentPath);
    if (IGNORE_DIRS.has(dirName)) return;

    const entries = fs.readdirSync(currentPath);
    for (const entry of entries) {
      scan(path.join(currentPath, entry));
    }
  } else if (stat.isFile()) {
    if (isExcludedFile(currentPath)) return;

    const ext = path.extname(currentPath).toLowerCase();
    const allowedExtensions = new Set([
      '.ts', '.tsx', '.js', '.jsx', '.json', '.md', '.py', '.yaml', '.yml', '.css', '.html', '.txt'
    ]);
    if (!allowedExtensions.has(ext)) return;

    const content = fs.readFileSync(currentPath, 'utf8');
    const lines = content.split('\n');

    lines.forEach((line, index) => {
      const matches = line.match(EMOJI_REGEX);
      if (matches) {
        for (const match of matches) {
          if (!ALLOWED_CHARS.has(match)) {
            violations.push({
              file: path.relative(process.cwd(), currentPath),
              line: index + 1,
              char: match,
              preview: line.trim(),
            });
          }
        }
      }
    });
  }
}

for (const dir of SCAN_DIRS) {
  scan(dir);
}

if (violations.length > 0) {
  console.error(`\n[CHECK FAILED] Found ${violations.length} forbidden emoji/pictographic glyph(s):`);
  for (const v of violations) {
    console.error(`  - ${v.file}:${v.line} -> "${v.char}" in "${v.preview}"`);
  }
  process.exit(1);
} else {
  console.log('[CHECK PASSED] Zero forbidden emoji found in codebase, copy, or docs.');
  process.exit(0);
}


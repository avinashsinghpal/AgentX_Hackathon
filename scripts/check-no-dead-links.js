#!/usr/bin/env node

/**
 * CI Check: No Dead Links
 * Scans JSX/TSX files in apps/web for internal hrefs and verifies:
 * 1. No empty '#' hrefs.
 * 2. Hash anchors in page.tsx correspond to declared section IDs.
 * 3. Route links (/terms, /privacy, /login, etc.) correspond to actual route directories in apps/web/app.
 */

const fs = require('fs');
const path = require('path');

const WEB_ROOT = path.resolve(__dirname, '../apps/web');
const APP_DIR = path.join(WEB_ROOT, 'app');
const COMPONENTS_DIR = path.join(WEB_ROOT, 'components');

const SCAN_DIRS = [APP_DIR, COMPONENTS_DIR];
const EXTENSIONS = ['.tsx', '.jsx', '.ts', '.js'];

let errors = [];

function collectFiles(dir) {
  let results = [];
  if (!fs.existsSync(dir)) return results;
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      results = results.concat(collectFiles(fullPath));
    } else if (EXTENSIONS.includes(path.extname(file))) {
      results.push(fullPath);
    }
  }
  return results;
}

// 1. Gather all declared section IDs from components and pages
const declaredSectionIds = new Set();
const allFiles = SCAN_DIRS.flatMap(collectFiles);

for (const file of allFiles) {
  const content = fs.readFileSync(file, 'utf8');
  const idMatches = content.matchAll(/id=["']([a-zA-Z0-9_-]+)["']/g);
  for (const m of idMatches) {
    declaredSectionIds.add(m[1]);
  }
}

// 2. Gather all route paths that exist under apps/web/app
function getAvailableRoutes(dir, currentRoute = '') {
  let routes = new Set();
  const list = fs.readdirSync(dir);
  for (const item of list) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      const nextRoute = `${currentRoute}/${item}`;
      // Check if page.tsx or route.ts exists
      if (fs.existsSync(path.join(fullPath, 'page.tsx')) || fs.existsSync(path.join(fullPath, 'page.jsx'))) {
        routes.add(nextRoute);
      }
      const sub = getAvailableRoutes(fullPath, nextRoute);
      for (const r of sub) routes.add(r);
    }
  }
  return routes;
}

const availableRoutes = getAvailableRoutes(APP_DIR);
availableRoutes.add('/'); // Root route

// 3. Scan for href="..."
for (const file of allFiles) {
  const relPath = path.relative(WEB_ROOT, file);
  const content = fs.readFileSync(file, 'utf8');
  
  // Exclude comment blocks if needed, but regex check is straightforward
  const hrefMatches = content.matchAll(/href=["']([^"']+)["']/g);
  for (const m of hrefMatches) {
    const link = m[1].trim();

    // Ignore mailto, tel, javascript
    if (link.startsWith('mailto:') || link.startsWith('tel:') || link.startsWith('javascript:')) {
      continue;
    }

    // Flag empty '#'
    if (link === '#') {
      errors.push(`${relPath}: Found dead link href="#"`);
      continue;
    }

    // Check hash-only links
    if (link.startsWith('#')) {
      const targetId = link.slice(1);
      if (!declaredSectionIds.has(targetId)) {
        errors.push(`${relPath}: Anchor link "${link}" has no matching element id="${targetId}"`);
      }
      continue;
    }

    // Check internal route links
    if (link.startsWith('/')) {
      // Split path and hash if any
      const [routePath, hash] = link.split('#');
      const cleanPath = routePath === '' ? '/' : routePath;

      if (!availableRoutes.has(cleanPath)) {
        errors.push(`${relPath}: Internal link "${cleanPath}" does not match any route in app/`);
      }

      if (hash && !declaredSectionIds.has(hash)) {
        errors.push(`${relPath}: Internal link hash "${link}" has no matching element id="${hash}"`);
      }
    }
  }
}

console.log('--- CI Check: No Dead Links ---');
console.log(`Scanned ${allFiles.length} files across apps/web.`);
console.log(`Found ${declaredSectionIds.size} section IDs:`, Array.from(declaredSectionIds).sort().join(', '));
console.log(`Found ${availableRoutes.size} routes:`, Array.from(availableRoutes).sort().join(', '));

if (errors.length > 0) {
  console.error('\nDead links found:');
  errors.forEach((err) => console.error(`  - ${err}`));
  process.exit(1);
} else {
  console.log('\nSuccess: Zero dead links detected.');
  process.exit(0);
}


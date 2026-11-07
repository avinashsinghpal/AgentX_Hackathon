#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const OUT_DIR = path.resolve(__dirname, '../docs/screenshots');
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function captureScreenshot(url, width, height, outputFile) {
  const args = [
    '--headless=new',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-gpu',
    '--disable-software-rasterizer',
    `--window-size=${width},${height}`,
    '--hide-scrollbars',
    `--screenshot="${outputFile}"`,
    `"${url}"`,
  ];
  execSync(`"${CHROME_PATH}" ${args.join(' ')}`, { stdio: 'ignore' });
}

async function run() {
  console.log('Capturing Seller Console screenshots from port ' + PORT + '...');

  const targets = [
    { name: 'seller-onboarding.png', url: `http://127.0.0.1:${PORT}/seller/onboarding`, w: 1440, h: 900 },
    { name: 'seller-dashboard.png', url: `http://127.0.0.1:${PORT}/seller/dashboard`, w: 1440, h: 900 },
    { name: 'seller-approvals.png', url: `http://127.0.0.1:${PORT}/seller/approvals`, w: 1440, h: 900 },
    { name: 'seller-policies.png', url: `http://127.0.0.1:${PORT}/seller/policies`, w: 1440, h: 900 },
    { name: 'seller-operations.png', url: `http://127.0.0.1:${PORT}/seller/operations`, w: 1440, h: 900 },
    { name: 'seller-customers.png', url: `http://127.0.0.1:${PORT}/seller/customers`, w: 1440, h: 900 },
    { name: 'seller-audit.png', url: `http://127.0.0.1:${PORT}/seller/audit`, w: 1440, h: 900 },
  ];

  for (const target of targets) {
    const outPath = path.join(OUT_DIR, target.name);
    captureScreenshot(target.url, target.w, target.h, outPath);
    const stat = fs.statSync(outPath);
    console.log(`  [CAPTURED] ${target.name} (${target.w}x${target.h}) -> ${stat.size} bytes`);
  }

  console.log('\n[PASS] All seller console screenshots captured successfully.');
}

run();

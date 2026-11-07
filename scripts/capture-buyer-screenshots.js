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
  console.log('Capturing Buyer Portal & Directory screenshots from port ' + PORT + '...');

  const targets = [
    { name: 'sellers-directory.png', url: `http://127.0.0.1:${PORT}/sellers`, w: 1440, h: 900 },
    { name: 'buyer-sellers.png', url: `http://127.0.0.1:${PORT}/buyer/sellers`, w: 1440, h: 900 },
    { name: 'buyer-orders.png', url: `http://127.0.0.1:${PORT}/buyer/orders`, w: 1440, h: 900 },
    { name: 'buyer-complaints-new.png', url: `http://127.0.0.1:${PORT}/buyer/complaints/new`, w: 1440, h: 900 },
    { name: 'buyer-cases.png', url: `http://127.0.0.1:${PORT}/buyer/cases`, w: 1440, h: 900 },
  ];

  for (const target of targets) {
    const outPath = path.join(OUT_DIR, target.name);
    captureScreenshot(target.url, target.w, target.h, outPath);
    const stat = fs.statSync(outPath);
    console.log(`  [CAPTURED] ${target.name} (${target.w}x${target.h}) -> ${stat.size} bytes`);
  }

  console.log('\n[PASS] All buyer flow screenshots captured successfully.');
}

run();

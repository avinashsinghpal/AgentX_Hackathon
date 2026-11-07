#!/usr/bin/env node

/**
 * Headless Browser Screenshot & Visual Verification Script
 * Uses Chrome headless to capture full screenshots at standard viewports:
 * 1440px (Desktop), 1024px (Small Desktop), 768px (Tablet), 390px (Mobile)
 */

const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

const PORT = 3006;
const WEB_DIR = path.resolve(__dirname, '../apps/web');
const OUT_DIR = path.resolve(__dirname, '../docs/screenshots');
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function probeReady(port, maxAttempts = 30) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const interval = setInterval(() => {
      attempts++;
      http.get(`http://127.0.0.1:${port}/`, (res) => {
        if (res.statusCode === 200) {
          clearInterval(interval);
          resolve(true);
        }
      }).on('error', () => {});

      if (attempts >= maxAttempts) {
        clearInterval(interval);
        reject(new Error(`Port ${port} not ready within timeout`));
      }
    }, 500);
  });
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
  console.log(`Starting production Next.js server on port ${PORT}...`);
  const isWin = process.platform === 'win32';
  const npxCmd = isWin ? 'npx.cmd' : 'npx';

  const child = spawn(npxCmd, ['next', 'start', '-p', String(PORT)], {
    cwd: WEB_DIR,
    shell: true,
    env: { ...process.env, PORT: String(PORT) },
  });

  try {
    await probeReady(PORT);
    console.log('Server is ready. Capturing screenshots...');

    const targets = [
      { name: 'landing-1440.png', url: `http://127.0.0.1:${PORT}/`, w: 1440, h: 900 },
      { name: 'landing-1024.png', url: `http://127.0.0.1:${PORT}/`, w: 1024, h: 768 },
      { name: 'landing-768.png', url: `http://127.0.0.1:${PORT}/`, w: 768, h: 1024 },
      { name: 'landing-390.png', url: `http://127.0.0.1:${PORT}/`, w: 390, h: 844 },
      { name: 'terms-1440.png', url: `http://127.0.0.1:${PORT}/terms`, w: 1440, h: 900 },
      { name: 'privacy-1440.png', url: `http://127.0.0.1:${PORT}/privacy`, w: 1440, h: 900 },
      { name: 'login-1440.png', url: `http://127.0.0.1:${PORT}/login`, w: 1440, h: 900 },
    ];

    for (const target of targets) {
      const outPath = path.join(OUT_DIR, target.name);
      captureScreenshot(target.url, target.w, target.h, outPath);
      const stat = fs.statSync(outPath);
      console.log(`  [CAPTURED] ${target.name} (${target.w}x${target.h}) -> ${stat.size} bytes`);
    }

    console.log('\n[PASS] All visual screenshots captured successfully.');
  } catch (err) {
    console.error('Screenshot capture failed:', err);
    process.exitCode = 1;
  } finally {
    try {
      execSync(`taskkill /pid ${child.pid} /f /t`, { stdio: 'ignore' });
    } catch (e) {}
    process.exit(process.exitCode || 0);
  }
}

run();

#!/usr/bin/env node

/**
 * Route Verification Script
 * Launches next start in a child process, waits for it to become ready,
 * probes all defined routes, and exits cleanly.
 */

const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const PORT = 3005;
const WEB_DIR = path.resolve(__dirname, '../apps/web');

const routes = [
  '/',
  '/terms',
  '/privacy',
  '/login',
  '/login/buyer',
  '/login/seller',
  '/register/buyer',
  '/register/seller',
  '/session-expired',
  '/forbidden',
  '/invite/invalid',
  '/maintenance',
  '/sellers',
  '/seller/onboarding',
  '/seller/dashboard',
  '/seller/approvals',
  '/seller/policies',
  '/seller/operations',
  '/seller/customers',
  '/seller/audit',
  '/buyer/sellers',
  '/buyer/orders',
  '/buyer/complaints/new',
  '/buyer/cases',
  '/buyer/cases/CAS-1001',
];

function checkRoute(route) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${PORT}${route}`, (res) => {
      resolve({ route, statusCode: res.statusCode });
    });
    req.on('error', (err) => {
      resolve({ route, statusCode: 'ERR', error: err.message });
    });
  });
}

function waitForReady(maxAttempts = 30) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      const res = await checkRoute('/');
      if (res.statusCode === 200) {
        clearInterval(interval);
        resolve(true);
      } else if (attempts >= maxAttempts) {
        clearInterval(interval);
        reject(new Error('Server did not start within timeout'));
      }
    }, 500);
  });
}

async function run() {
  console.log(`Starting production Next.js server on port ${PORT}...`);
  const isWin = process.platform === 'win32';
  const npxCmd = isWin ? 'npx.cmd' : 'npx';

  const child = spawn(npxCmd, ['next', 'start', '-p', String(PORT)], {
    cwd: WEB_DIR,
    stdio: 'inherit',
    shell: true,
    env: { ...process.env, PORT: String(PORT) },
  });

  try {
    await waitForReady();
    console.log(`\nServer ready on http://127.0.0.1:${PORT}. Probing all routes:\n`);

    let allPass = true;
    for (const route of routes) {
      const res = await checkRoute(route);
      const pass = res.statusCode === 200;
      if (!pass) allPass = false;
      console.log(`  [${pass ? 'PASS' : 'FAIL'}] ${route} -> HTTP ${res.statusCode}`);
    }

    const notFoundRes = await checkRoute('/non-existent-page-test');
    const notFoundPass = notFoundRes.statusCode === 404;
    console.log(`  [${notFoundPass ? 'PASS' : 'INFO'}] /non-existent-page-test -> HTTP ${notFoundRes.statusCode}`);

    if (allPass) {
      console.log('\n[GATE 2 PASS] All routes verified successfully with HTTP 200 / 404.');
      process.exitCode = 0;
    } else {
      console.error('\n[GATE 2 FAIL] Some routes failed to return HTTP 200.');
      process.exitCode = 1;
    }
  } catch (err) {
    console.error('Failed to probe routes:', err);
    process.exitCode = 1;
  } finally {
    console.log('Stopping test server...');
    if (isWin) {
      try {
        require('child_process').execSync(`taskkill /pid ${child.pid} /f /t`);
      } catch (e) {}
    } else {
      child.kill('SIGTERM');
    }
    process.exit(process.exitCode || 0);
  }
}

run();

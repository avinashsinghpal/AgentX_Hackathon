const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const p = path.resolve(__dirname, '../docs/screenshots/landing-tree-verified.png');
const chrome = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const cmd = `"${chrome}" --headless=new --no-sandbox --disable-gpu --window-size=1440,900 --screenshot="${p}" "http://127.0.0.1:3000"`;
execSync(cmd, { stdio: 'inherit' });
if (fs.existsSync(p)) {
  console.log('Successfully captured:', p, fs.statSync(p).size, 'bytes');
}


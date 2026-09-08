import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, '..', 'output', 'map-qa');
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await page.goto('http://localhost:3847/', { waitUntil: 'networkidle', timeout: 30000 });
await page.click('button[data-view="map"]');
await page.waitForTimeout(2000);
const shot = path.join(outDir, 'map-tab.png');
await page.screenshot({ path: shot, fullPage: false });
const notice = await page.locator('#mapNotice').innerText().catch(() => '');
const status = await page.locator('#mapStatus').innerText().catch(() => '');
fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify({ notice, status, shot }, null, 2));
console.log('screenshot:', shot);
console.log('status:', status);
console.log('notice:', notice.slice(0, 160));
await browser.close();

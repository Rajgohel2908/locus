/**
 * frontend/scripts/run_walkthrough.js
 * Automated golden-path screenshot capture script using puppeteer-core & Google Chrome.
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const puppeteer = require('puppeteer-core');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');
const FRONTEND_DIR = path.join(ROOT_DIR, 'frontend');
const SCREENSHOTS_DIR = path.join(FRONTEND_DIR, 'SCREENSHOTS');
const PYTHON_PATH = path.join(ROOT_DIR, 'venv', 'Scripts', 'python.exe');
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function checkUrl(url, timeoutMs = 2000) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForServer(url, name, maxWaitSec = 40) {
  console.log(`Waiting for ${name} at ${url}...`);
  const start = Date.now();
  while (Date.now() - start < maxWaitSec * 1000) {
    if (await checkUrl(url)) {
      console.log(`[OK] ${name} is responding at ${url}`);
      return true;
    }
    await wait(1000);
  }
  throw new Error(`Timeout waiting for ${name} at ${url}`);
}

async function main() {
  console.log('==============================================================');
  console.log('  SIFT FRONTEND GOLDEN PATH WALKTHROUGH & SCREENSHOT CAPTURE');
  console.log('==============================================================');

  let backendProc = null;
  let frontendProc = null;

  // 1. Check / Start Backend
  const backendRunning = await checkUrl('http://127.0.0.1:8000/docs');
  if (!backendRunning) {
    console.log('Starting Sift backend (uvicorn) pointing to ragstudio_demo...');
    backendProc = spawn(PYTHON_PATH, ['-m', 'uvicorn', 'main:app', '--port', '8000', '--host', '127.0.0.1'], {
      cwd: BACKEND_DIR,
      env: {
        ...process.env,
        DATABASE_URL: 'postgresql+psycopg2://postgres:raj1818@localhost:8887/ragstudio_demo',
        LLM_PROVIDER: 'mock',
        WARMUP_MODELS: '0',
      },
      stdio: 'pipe',
    });

    backendProc.stdout.on('data', (d) => {
      const line = d.toString();
      if (line.includes('Uvicorn running') || line.includes('Application startup complete')) {
        console.log(`[Backend Log] ${line.trim()}`);
      }
    });

    backendProc.stderr.on('data', (d) => {
      const line = d.toString();
      if (line.includes('ERROR') || line.includes('WARN')) {
        console.log(`[Backend Stderr] ${line.trim()}`);
      }
    });

    await waitForServer('http://127.0.0.1:8000/docs', 'Backend Server', 30);
  } else {
    console.log('[OK] Backend server already running on port 8000');
  }

  // 2. Check / Start Frontend
  const frontendRunning = await checkUrl('http://127.0.0.1:3000/');
  if (!frontendRunning) {
    console.log('Starting Next.js frontend production server on port 3000...');
    frontendProc = spawn('npx', ['next', 'start', '-p', '3000'], {
      cwd: FRONTEND_DIR,
      shell: true,
      env: {
        ...process.env,
        BACKEND_URL: 'http://127.0.0.1:8000',
      },
      stdio: 'pipe',
    });

    frontendProc.stdout.on('data', (d) => {
      const line = d.toString();
      if (line.includes('Ready in') || line.includes('started server')) {
        console.log(`[Frontend Log] ${line.trim()}`);
      }
    });

    await waitForServer('http://127.0.0.1:3000/', 'Frontend Server', 35);
  } else {
    console.log('[OK] Frontend server already running on port 3000');
  }

  // 3. Launch Chrome with Puppeteer
  console.log(`Launching Chrome from ${CHROME_PATH}...`);
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    defaultViewport: { width: 1440, height: 900, deviceScaleFactor: 1.5 },
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  const page = await browser.newPage();

  // Helper to take screenshot
  async function snap(filename, desc) {
    const filePath = path.join(SCREENSHOTS_DIR, filename);
    await wait(1000); // let UI settle
    await page.screenshot({ path: filePath, fullPage: false });
    const stat = fs.statSync(filePath);
    console.log(`[SAVED] ${filename} (${(stat.size / 1024).toFixed(1)} KB) - ${desc}`);
  }

  try {
    // Step 1: Sources List
    console.log('\n--- Step 1: Sources List ---');
    await page.goto('http://127.0.0.1:3000/sources', { waitUntil: 'networkidle2' });
    await page.waitForSelector('table', { timeout: 10000 });
    await snap('sources.png', 'Sources list table with Trust Strip summaries');

    // Get Sources to find IDs
    const sources = await page.evaluate(async () => {
      const res = await fetch('/api/sources');
      return await res.json();
    });

    console.log(`Found ${sources.length} sources in ragstudio_demo:`);
    sources.forEach((s) => console.log(`  - [${s.id}] ${s.name} (${s.source_type})`));

    const structSource =
      sources.find((s) => s.id === 573) ||
      sources.find((s) => s.name.toLowerCase().includes('employees_messy')) ||
      sources[0];

    const docSource =
      sources.find((s) => s.id === 571) ||
      sources.find((s) => s.name.toLowerCase().includes('leave_policy_2024')) ||
      sources.find((s) => s.name.toLowerCase().includes('leave_policy')) ||
      sources[sources.length - 1];

    console.log(`Using Structured Source ID: ${structSource.id} (${structSource.name})`);
    console.log(`Using Document Source ID:   ${docSource.id} (${docSource.name})`);

    // Step 2: Source Health Tab
    console.log('\n--- Step 2: Source Detail - Health Tab ---');
    await page.goto(`http://127.0.0.1:3000/sources/${structSource.id}?tab=health`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1500);
    await snap('source_health.png', 'Source detail - Health tab with missingness bars, duplicates, and category checks');

    // Step 3: Source Cleaning Tab
    console.log('\n--- Step 3: Source Detail - Cleaning Tab ---');
    await page.goto(`http://127.0.0.1:3000/sources/${structSource.id}?tab=cleaning`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1500);
    await snap('source_cleaning.png', 'Source detail - Cleaning tab with inferred column roles and cleaning proposals');

    // Step 4: Source Versions Tab
    console.log('\n--- Step 4: Source Detail - Versions Tab ---');
    await page.goto(`http://127.0.0.1:3000/sources/${structSource.id}?tab=versions`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1500);
    await snap('source_versions.png', 'Source detail - Versions tab with version history and quarantined rows');

    // Step 5: Source Documents Tab with Override Modal
    console.log('\n--- Step 5: Source Detail - Documents Tab ---');
    await page.goto(`http://127.0.0.1:3000/sources/${docSource.id}?tab=documents`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1000);

    // Click "Edit Override" button to open modal
    const overrideBtn = await page.evaluateHandle(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      return btns.find((b) => b.textContent && b.textContent.includes('Edit Override'));
    });
    if (overrideBtn && overrideBtn.asElement()) {
      await overrideBtn.asElement().click();
      await wait(800);
    }
    await snap('source_documents.png', 'Source detail - Documents tab with freshness status and active metadata override modal');

    // Close modal if open
    await page.keyboard.press('Escape');
    await wait(500);

    // Step 6: Source Indexing Tab with Chunks
    console.log('\n--- Step 6: Source Detail - Indexing Tab ---');
    await page.goto(`http://127.0.0.1:3000/sources/${docSource.id}?tab=index`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1000);

    // Click first index run row if present to inspect chunks
    await page.evaluate(() => {
      const rows = document.querySelectorAll('tr.cursor-pointer');
      if (rows && rows.length > 0) rows[0].click();
    });
    await wait(1500);
    await snap('source_indexing.png', 'Source detail - Indexing tab with run parameters and chunk inspector');

    // Step 7: Ask Page (Query execution, citations drawer, trace timeline)
    console.log('\n--- Step 7: Ask Page ---');
    await page.goto('http://127.0.0.1:3000/ask', { waitUntil: 'networkidle2' });
    await page.waitForSelector('input[type="text"]', { timeout: 10000 });

    // Type query
    const queryInput = await page.$('input[type="text"]');
    await queryInput.click({ clickCount: 3 });
    await queryInput.type('What is the annual leave entitlement under the 2024 policy?');

    // Click Ask button
    const askButton = await page.$('button[type="submit"]');
    await askButton.click();

    // Wait for result card
    console.log('Waiting for query response and citations...');
    await page.waitForFunction(
      () =>
        document.querySelector('.whitespace-pre-wrap') ||
        document.querySelector('.bg-amber\\/10') ||
        document.body.innerText.includes('Answer Output') ||
        document.body.innerText.includes('annual leave days'),
      { timeout: 35000 }
    );
    await wait(1500);

    // Expand trace timeline
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const traceBtn = btns.find((b) => b.textContent && b.textContent.includes('Trace'));
      if (traceBtn) traceBtn.click();
    });
    await wait(1000);

    // Click first citation button to open drawer
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const citBtn = btns.find((b) => b.textContent && b.textContent.includes('['));
      if (citBtn) citBtn.click();
    });
    await wait(1200);

    await snap('ask_query.png', 'Ask page with question answered, mock LLM banner, expanded trace timeline, and citations drawer');

    // Step 8: Compare Page
    console.log('\n--- Step 8: Compare Page ---');
    await page.goto('http://127.0.0.1:3000/compare', { waitUntil: 'networkidle2' });
    await page.waitForSelector('button[type="submit"]', { timeout: 10000 });

    // Click Compare button
    const compareButton = await page.$('button[type="submit"]');
    await compareButton.click();

    console.log('Waiting for 4-strategy comparison grid...');
    await page.waitForFunction(
      () =>
        document.body.innerText.includes('dense') &&
        document.body.innerText.includes('lexical') &&
        (document.body.innerText.includes('Passed') || document.body.innerText.includes('Insufficient')),
      { timeout: 35000 }
    );
    await wait(2000);
    await snap('compare_retrieval.png', 'Compare page with 4-column side-by-side strategy retrieval and evidence gate');

    // Step 9: Pipeline Recommender Page
    console.log('\n--- Step 9: Pipeline Page ---');
    await page.goto('http://127.0.0.1:3000/pipeline', { waitUntil: 'networkidle2' });
    await page.waitForSelector('.font-heading', { timeout: 10000 });

    // Wait for Mermaid SVG and recommendation cards to load
    await page.waitForFunction(
      () =>
        document.querySelector('svg') ||
        document.body.innerText.includes('Architecture Graph') ||
        document.body.innerText.includes('R1') ||
        document.body.innerText.includes('Rules Fired'),
      { timeout: 20000 }
    );
    await wait(3000);
    await snap('pipeline_recommender.png', 'Pipeline page with KB profile cards, rules fired, diff table, and Mermaid architecture diagram');

    console.log('\n==============================================================');
    console.log('  ALL 9 SCREENSHOTS SUCCESSFULLY CAPTURED IN frontend/SCREENSHOTS/');
    console.log('==============================================================');

    const files = fs.readdirSync(SCREENSHOTS_DIR);
    files.forEach((f) => {
      const fp = path.join(SCREENSHOTS_DIR, f);
      const st = fs.statSync(fp);
      console.log(`  - ${f.padEnd(28)} : ${(st.size / 1024).toFixed(1)} KB`);
    });

  } catch (err) {
    console.error('Walkthrough error:', err);
    throw err;
  } finally {
    await browser.close();
    if (frontendProc) {
      console.log('Shutting down frontend child process...');
      try { process.kill(frontendProc.pid); } catch {}
    }
    if (backendProc) {
      console.log('Shutting down backend child process...');
      try { process.kill(backendProc.pid); } catch {}
    }
  }
}

main().catch((e) => {
  console.error('Fatal execution error:', e);
  process.exit(1);
});

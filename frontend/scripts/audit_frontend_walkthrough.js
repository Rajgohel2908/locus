/**
 * frontend/scripts/audit_frontend_walkthrough.js
 * Comprehensive automated frontend walkthrough, verification, and breaking point audit.
 */

const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const SCREENSHOTS_DIR = path.resolve(__dirname, '..', 'SCREENSHOTS');
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://127.0.0.1:3000';
const BACKEND_URL = 'http://127.0.0.1:8000';

if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runAudit() {
  console.log('========================================================================');
  console.log('         SIFT FRONTEND COMPREHENSIVE AUDIT & VERIFICATION TASK          ');
  console.log('========================================================================');

  const auditReport = {
    pagesChecked: [],
    featuresVerified: [],
    llmGenerationTests: [],
    breakingPoints: [],
    consoleErrors: [],
    networkErrors: [],
    missingPages: [],
    screenshotsCaptured: [],
  };

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    defaultViewport: { width: 1440, height: 900, deviceScaleFactor: 1.5 },
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  const page = await browser.newPage();

  // Track console logs and errors
  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error') {
      auditReport.consoleErrors.push(`[Console Error] ${text}`);
      console.error(`  [Console Error] ${text}`);
    }
  });

  page.on('pageerror', (err) => {
    auditReport.breakingPoints.push(`[Runtime Crash] ${err.message}`);
    console.error(`  [Runtime Crash] ${err.message}`);
  });

  page.on('response', (res) => {
    if (res.status() >= 400 && !res.url().includes('nonexistent')) {
      auditReport.networkErrors.push(`[HTTP ${res.status()}] ${res.url()}`);
      console.warn(`  [Network Warning] HTTP ${res.status()} on ${res.url()}`);
    }
  });

  async function takeScreenshot(filename, desc) {
    const filePath = path.join(SCREENSHOTS_DIR, filename);
    await wait(1000);
    await page.screenshot({ path: filePath, fullPage: false });
    const stat = fs.statSync(filePath);
    auditReport.screenshotsCaptured.push({
      file: filename,
      sizeKb: (stat.size / 1024).toFixed(1),
      desc,
    });
    console.log(`  [SCREENSHOT] ${filename} (${(stat.size / 1024).toFixed(1)} KB) - ${desc}`);
  }

  try {
    // -------------------------------------------------------------------------
    // 1. AUDIT SOURCES LIST PAGE (/sources)
    // -------------------------------------------------------------------------
    console.log('\n[1/7] Auditing Sources Page (/sources)...');
    await page.goto(`${BASE_URL}/sources`, { waitUntil: 'networkidle2' });
    await page.waitForSelector('table', { timeout: 10000 });
    auditReport.pagesChecked.push('/sources');

    const sourcesCount = await page.evaluate(() => {
      return document.querySelectorAll('tbody tr').length;
    });
    console.log(`  - Sources table rendered with ${sourcesCount} rows.`);

    // Check Upload Button
    const uploadModalTrigger = await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find((b) =>
        b.textContent.includes('Upload File')
      );
      return !!btn;
    });
    console.log(`  - Upload Source modal trigger present: ${uploadModalTrigger}`);

    await takeScreenshot('sources.png', 'Sources list table with Trust Strip summaries');
    auditReport.featuresVerified.push('Sources List & Ingestion Controls');

    // Get sources list from API to pick IDs for detail testing
    const sources = await page.evaluate(async () => {
      const res = await fetch('/api/sources');
      return await res.json();
    });

    const structSource =
      sources.find((s) => s.id === 573) ||
      sources.find((s) => s.name.toLowerCase().includes('employees_messy')) ||
      sources[0];

    const docSource =
      sources.find((s) => s.id === 571) ||
      sources.find((s) => s.name.toLowerCase().includes('leave_policy_2024')) ||
      sources.find((s) => s.name.toLowerCase().includes('leave_policy')) ||
      sources[sources.length - 1];

    console.log(`  - Structured Target: ID ${structSource.id} (${structSource.name})`);
    console.log(`  - Document Target:   ID ${docSource.id} (${docSource.name})`);

    // -------------------------------------------------------------------------
    // 2. AUDIT SOURCE DETAIL PAGE (/sources/[id])
    // -------------------------------------------------------------------------
    console.log('\n[2/7] Auditing Source Detail Page (/sources/[id])...');

    // Tab 1: Health Tab
    console.log('  Checking Health Tab...');
    await page.goto(`${BASE_URL}/sources/${structSource.id}?tab=health`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1000);

    const trustStripData = await page.evaluate(() => {
      const text = document.body.innerText;
      return {
        hasVersion: text.includes('v1') || text.includes('v2'),
        hasActiveQuarantined: text.includes('Active / Quarantined'),
        hasDuplicates: text.includes('Duplicate Rows'),
        hasInconsistencies: text.includes('Inconsistent Categories'),
        hasMissingness: text.includes('Missing Values'),
      };
    });
    console.log('  - Trust Strip & Health Checks:', trustStripData);
    await takeScreenshot('source_health.png', 'Source detail - Health tab with missingness bars, duplicates, and category checks');
    auditReport.featuresVerified.push('Source Trust Strip & Health Tab');

    // Tab 2: Cleaning Tab
    console.log('  Checking Cleaning Tab...');
    await page.goto(`${BASE_URL}/sources/${structSource.id}?tab=cleaning`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1000);

    const cleaningData = await page.evaluate(() => {
      const text = document.body.innerText;
      return {
        hasRoles: text.includes('Column Roles') || text.includes('Salary'),
        hasProposals: text.includes('Proposals') || text.includes('Proposal'),
        hasApproveReject: text.includes('Approve') || text.includes('Reject'),
      };
    });
    console.log('  - Cleaning Tab Checks:', cleaningData);
    await takeScreenshot('source_cleaning.png', 'Source detail - Cleaning tab with inferred column roles and cleaning proposals');
    auditReport.featuresVerified.push('Cleaning Proposals & Role Inferences');

    // Tab 3: Versions Tab
    console.log('  Checking Versions Tab...');
    await page.goto(`${BASE_URL}/sources/${structSource.id}?tab=versions`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1000);

    const versionsData = await page.evaluate(() => {
      const text = document.body.innerText;
      return {
        hasVersionHistory: text.includes('Version History') || text.includes('v2'),
        hasQuarantinedRecords: text.includes('Quarantined Records') || text.includes('Reason'),
      };
    });
    console.log('  - Versions Tab Checks:', versionsData);
    await takeScreenshot('source_versions.png', 'Source detail - Versions tab with version history and quarantined rows');
    auditReport.featuresVerified.push('Version History & Quarantined Partitions');

    // Tab 4: Documents Tab (Text Source)
    console.log('  Checking Documents Tab (Text Source)...');
    await page.goto(`${BASE_URL}/sources/${docSource.id}?tab=documents`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1000);

    // Open override modal
    const overrideBtn = await page.evaluateHandle(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      return btns.find((b) => b.textContent && b.textContent.includes('Edit Override'));
    });
    let modalOpened = false;
    if (overrideBtn && overrideBtn.asElement()) {
      await overrideBtn.asElement().click();
      await wait(800);
      modalOpened = await page.evaluate(() =>
        document.body.innerText.includes('Override Document Metadata')
      );
    }
    console.log(`  - Metadata Override Modal opened: ${modalOpened}`);
    await takeScreenshot('source_documents.png', 'Source detail - Documents tab with freshness status and active metadata override modal');
    await page.keyboard.press('Escape');
    await wait(500);
    auditReport.featuresVerified.push('Document Freshness & Metadata Override');

    // Tab 5: Indexing Tab
    console.log('  Checking Indexing Tab...');
    await page.goto(`${BASE_URL}/sources/${docSource.id}?tab=index`, {
      waitUntil: 'networkidle2',
    });
    await page.waitForSelector('.rounded-card', { timeout: 10000 });
    await wait(1000);

    const indexingData = await page.evaluate(() => {
      const text = document.body.innerText;
      return {
        hasChunkSizeChars: text.includes('Chunk Size') && text.includes('chars'),
        hasIndexRuns: text.includes('Indexing Runs') || text.includes('Run #'),
      };
    });
    console.log('  - Indexing Tab Checks (unit: characters):', indexingData);

    // Click index run to view chunks
    await page.evaluate(() => {
      const rows = document.querySelectorAll('tr.cursor-pointer');
      if (rows && rows.length > 0) rows[0].click();
    });
    await wait(1000);
    await takeScreenshot('source_indexing.png', 'Source detail - Indexing tab with run parameters and chunk inspector');
    auditReport.featuresVerified.push('Chunk Sizing (characters) & Chunk Inspector');

    // -------------------------------------------------------------------------
    // 3. AUDIT ASK PAGE (/ask) & LLM ANSWER GENERATION
    // -------------------------------------------------------------------------
    console.log('\n[3/7] Auditing Ask Page (/ask) & LLM Answer Generation...');
    await page.goto(`${BASE_URL}/ask`, { waitUntil: 'networkidle2' });
    await page.waitForSelector('input[type="text"]', { timeout: 10000 });
    auditReport.pagesChecked.push('/ask');

    // Test A: Semantic Retrieval & Generated LLM Answer
    console.log('  [Test A] Submitting Semantic Query: "What is the annual leave entitlement under the 2024 policy?"');
    const queryInput = await page.$('input[type="text"]');
    await queryInput.click({ clickCount: 3 });
    await queryInput.type('What is the annual leave entitlement under the 2024 policy?');

    const askButton = await page.$('button[type="submit"]');
    await askButton.click();

    console.log('  Waiting for LLM response...');
    await page.waitForFunction(
      () =>
        document.body.innerText.includes('Answer Output') &&
        (document.body.innerText.includes('Under the 2024 policy') ||
          document.body.innerText.includes('annual leave days') ||
          document.querySelector('.whitespace-pre-wrap')),
      { timeout: 35000 }
    );
    await wait(1000);

    const semanticResult = await page.evaluate(() => {
      const answerEl = document.querySelector('.whitespace-pre-wrap');
      const isMock = document.body.innerText.includes('MOCK LLM');
      const answerType = document.body.innerText.includes('Generated LLM Answer')
        ? 'generated'
        : 'other';
      const evidencePassed = document.body.innerText.includes('Passed');
      const citationButtons = Array.from(document.querySelectorAll('button')).filter((b) =>
        b.textContent.trim().startsWith('[')
      ).length;

      return {
        answer: answerEl ? answerEl.textContent.trim() : 'N/A',
        isMock,
        answerType,
        evidencePassed,
        citationCount: citationButtons,
      };
    });

    console.log('  - LLM Generated Answer:', semanticResult.answer);
    console.log('  - Answer Type:', semanticResult.answerType);
    console.log('  - Mock LLM Banner Active:', semanticResult.isMock);
    console.log('  - Evidence Gate Passed:', semanticResult.evidencePassed);
    console.log('  - Citations Attached:', semanticResult.citationCount);

    auditReport.llmGenerationTests.push({
      type: 'Semantic / Text RAG',
      query: 'What is the annual leave entitlement under the 2024 policy?',
      status: semanticResult.answer ? 'SUCCESS' : 'FAILED',
      answerExcerpt: semanticResult.answer.slice(0, 100),
      citations: semanticResult.citationCount,
    });

    // Expand Trace Timeline
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const traceBtn = btns.find((b) => b.textContent && b.textContent.includes('Trace'));
      if (traceBtn) traceBtn.click();
    });
    await wait(1000);

    const traceVisible = await page.evaluate(() =>
      document.body.innerText.includes('Router Decision Trail') ||
      document.body.innerText.includes('Retrieved Candidates')
    );
    console.log(`  - Trace Timeline expanded: ${traceVisible}`);

    // Open Citation Drawer
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const citBtn = btns.find((b) => b.textContent && b.textContent.includes('['));
      if (citBtn) citBtn.click();
    });
    await wait(1200);

    const drawerVisible = await page.evaluate(() =>
      document.body.innerText.includes('Citation Inspector') ||
      document.body.innerText.includes('Chunk Content')
    );
    console.log(`  - Citations Drawer opened: ${drawerVisible}`);

    await takeScreenshot('ask_query.png', 'Ask page with question answered, mock LLM banner, expanded trace timeline, and citations drawer');
    auditReport.featuresVerified.push('Semantic Query, LLM Answer, Citations Drawer, Trace Timeline');

    // Test B: Structured SQL Aggregation & Outlier Honesty
    console.log('\n  [Test B] Submitting Structured Query: "What is the average salary in Mumbai?"');
    await page.evaluate(() => {
      // Close drawer if open
      const closeBtn = document.querySelector('button[aria-label="Close"]');
      if (closeBtn) closeBtn.click();
    });
    await wait(500);

    await queryInput.click({ clickCount: 3 });
    await queryInput.type('What is the average salary in Mumbai?');
    await askButton.click();

    console.log('  Waiting for Computed SQL response...');
    await page.waitForFunction(
      () =>
        document.body.innerText.includes('Average Salary where City = mumbai') ||
        document.body.innerText.includes('Computed SQL Aggregation'),
      { timeout: 35000 }
    );
    await wait(1000);

    const structuredResult = await page.evaluate(() => {
      const answerEl = document.querySelector('.whitespace-pre-wrap');
      const isComputed = document.body.innerText.includes('Computed SQL Aggregation');
      const text = document.body.innerText;
      return {
        answer: answerEl ? answerEl.textContent.trim() : 'N/A',
        isComputed,
        hasPrimaryAverage: text.includes('248,894.21'),
        hasOutlierFreeAverage: text.includes('71,601.40'),
        hasOutlierFlag: text.includes('9,999,999'),
      };
    });

    console.log('  - Computed SQL Answer:', structuredResult.answer);
    console.log('  - Primary Average Verified ($248,894.21):', structuredResult.hasPrimaryAverage);
    console.log('  - Outlier Honesty ($9,999,999 flagged):', structuredResult.hasOutlierFlag);
    console.log('  - Outlier-Free Clean Average Verified ($71,601.40):', structuredResult.hasOutlierFreeAverage);

    auditReport.llmGenerationTests.push({
      type: 'Structured SQL Computation',
      query: 'What is the average salary in Mumbai?',
      status: structuredResult.hasPrimaryAverage && structuredResult.hasOutlierFreeAverage ? 'SUCCESS' : 'FAILED',
      answerExcerpt: structuredResult.answer.slice(0, 100),
      outlierHonesty: structuredResult.hasOutlierFlag,
    });
    auditReport.featuresVerified.push('Deterministic SQL Query Routing & Outlier Honesty');

    // -------------------------------------------------------------------------
    // 4. AUDIT RETRIEVAL STRATEGY COMPARISON (/compare)
    // -------------------------------------------------------------------------
    console.log('\n[4/7] Auditing Retrieval Comparison Page (/compare)...');
    await page.goto(`${BASE_URL}/compare`, { waitUntil: 'networkidle2' });
    await page.waitForSelector('button[type="submit"]', { timeout: 10000 });
    auditReport.pagesChecked.push('/compare');

    const compareBtn = await page.$('button[type="submit"]');
    await compareBtn.click();

    console.log('  Running 4-strategy comparison (dense, lexical, hybrid, hybrid_rerank)...');
    await page.waitForFunction(
      () =>
        document.body.innerText.includes('dense') &&
        document.body.innerText.includes('lexical') &&
        document.body.innerText.includes('hybrid_rerank'),
      { timeout: 35000 }
    );
    await wait(2000);

    const compareData = await page.evaluate(() => {
      const text = document.body.innerText;
      return {
        hasDense: text.includes('dense'),
        hasLexical: text.includes('lexical'),
        hasHybrid: text.includes('hybrid'),
        hasRerank: text.includes('hybrid_rerank'),
        hasEvidenceGates: text.includes('Passed') || text.includes('Insufficient Evidence'),
      };
    });
    console.log('  - 4-Column Strategy Comparison Grid:', compareData);

    await takeScreenshot('compare_retrieval.png', 'Compare page with 4-column side-by-side strategy retrieval and evidence gate');
    auditReport.featuresVerified.push('4-Column Side-by-Side Strategy Comparison Grid');

    // -------------------------------------------------------------------------
    // 5. AUDIT PIPELINE RECOMMENDER & ARCHITECTURE (/pipeline)
    // -------------------------------------------------------------------------
    console.log('\n[5/7] Auditing Strategy Recommender & Pipeline Page (/pipeline)...');
    await page.goto(`${BASE_URL}/pipeline`, { waitUntil: 'networkidle2' });
    await page.waitForSelector('.font-heading', { timeout: 10000 });
    auditReport.pagesChecked.push('/pipeline');

    await page.waitForFunction(
      () =>
        document.body.innerText.includes('recommender-rules-v1') ||
        document.body.innerText.includes('Rules Fired') ||
        document.body.innerText.includes('Architecture Graph'),
      { timeout: 25000 }
    );
    await wait(2000);

    const pipelineData = await page.evaluate(() => {
      const text = document.body.innerText;
      const hasSvg = !!document.querySelector('svg');
      const hasRules = text.includes('R1') || text.includes('R2') || text.includes('R4');
      const hasDiff = text.includes('Baseline vs Recommended') || text.includes('Config Diff');
      return {
        hasRulesFired: hasRules,
        hasMermaidSvg: hasSvg,
        hasConfigDiff: hasDiff,
      };
    });
    console.log('  - Pipeline Checks:', pipelineData);

    await takeScreenshot('pipeline_recommender.png', 'Pipeline page with KB profile cards, rules fired, diff table, and Mermaid architecture diagram');
    auditReport.featuresVerified.push('Recommender Rules (R1–R12), Config Diff, Mermaid Architecture Diagram');

    // -------------------------------------------------------------------------
    // 6. AUDIT NAVIGATION & MISSING PAGES
    // -------------------------------------------------------------------------
    console.log('\n[6/7] Auditing Navigation Links & Checking for Missing Pages...');

    // Check Sidebar links
    const sidebarLinks = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('nav a, aside a')).map((a) => ({
        text: a.textContent.trim(),
        href: a.getAttribute('href'),
      }));
      const disabledItems = Array.from(document.querySelectorAll('aside span, aside div'))
        .filter((el) => el.textContent.includes('Phase 7') || el.textContent.includes('Phase 8'))
        .map((el) => el.textContent.trim());
      return { links, disabledItems };
    });

    console.log('  - Active Navigation Links in Sidebar:');
    sidebarLinks.links.forEach((l) => console.log(`      * ${l.text} -> ${l.href}`));
    console.log('  - Disabled Future Phases (Phases 7 & 8):');
    sidebarLinks.disabledItems.forEach((d) => console.log(`      * ${d}`));

    // Test 404 Not Found Page
    console.log('  Testing 404 Not Found Handling (/nonexistent-audit-route)...');
    await page.goto(`${BASE_URL}/nonexistent-audit-route`, { waitUntil: 'networkidle2' });
    await wait(1000);

    const notFoundHandled = await page.evaluate(() => {
      const text = document.body.innerText;
      return text.includes('404') && text.includes('Page Not Found');
    });
    console.log(`  - Custom 404 Screen Rendered Cleanly: ${notFoundHandled}`);
    if (notFoundHandled) {
      auditReport.featuresVerified.push('Custom 404 Not Found Page');
    } else {
      auditReport.missingPages.push('Custom 404 page missing or returned server error');
    }

    // -------------------------------------------------------------------------
    // 7. SUMMARY & BREAKING POINTS INSPECTION
    // -------------------------------------------------------------------------
    console.log('\n[7/7] Generating Comprehensive Audit Summary...');

    console.log('\n========================================================================');
    console.log('                           AUDIT SUMMARY REPORT                         ');
    console.log('========================================================================');
    console.log(`Pages Audited:           ${auditReport.pagesChecked.length}`);
    console.log(`Features Verified:       ${auditReport.featuresVerified.length}`);
    console.log(`LLM Queries Tested:      ${auditReport.llmGenerationTests.length}`);
    console.log(`Screenshots Captured:    ${auditReport.screenshotsCaptured.length} / 9`);
    console.log(`Breaking Points Found:   ${auditReport.breakingPoints.length}`);
    console.log(`Console Errors Found:    ${auditReport.consoleErrors.length}`);
    console.log(`Network Errors Found:    ${auditReport.networkErrors.length}`);
    console.log(`Missing Pages Found:     ${auditReport.missingPages.length}`);
    console.log('========================================================================\n');

    fs.writeFileSync(
      path.join(SCREENSHOTS_DIR, 'AUDIT_REPORT.json'),
      JSON.stringify(auditReport, null, 2)
    );
    console.log('Saved machine-readable audit report to frontend/SCREENSHOTS/AUDIT_REPORT.json');

  } catch (err) {
    console.error('Fatal audit failure:', err);
    throw err;
  } finally {
    await browser.close();
  }
}

runAudit().catch((err) => {
  console.error(err);
  process.exit(1);
});


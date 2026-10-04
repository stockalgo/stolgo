const puppeteer = require('puppeteer');

const BASE_URL = 'http://127.0.0.1:8000';

async function runInteractiveUAT() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  const errors = [];
  const warnings = [];

  page.on('pageerror', (err) => {
    errors.push(`[Page Error] ${page.url()}: ${err.message}`);
  });

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Ignore favicon or expected 404 tests
      if (!text.includes('favicon') && !text.includes('404')) {
        errors.push(`[Console Error] ${page.url()}: ${text}`);
      }
    } else if (msg.type() === 'warning') {
      warnings.push(`[Console Warn] ${page.url()}: ${msg.text()}`);
    }
  });

  async function checkNoIllegalStrings(contextName) {
    const bodyText = await page.evaluate(() => document.body.innerText);
    for (const bad of ['NaN', 'undefined', 'Infinity']) {
      const regex = new RegExp(`\\b${bad}\\b`);
      if (regex.test(bodyText) && !page.url().includes('_kit')) {
        errors.push(`[Forbidden String] Found "${bad}" in body text at ${contextName} (${page.url()})`);
      }
    }
    if (bodyText.includes('[object Object]')) {
      errors.push(`[Forbidden String] Found "[object Object]" in body text at ${contextName} (${page.url()})`);
    }
  }

  console.log('--- TEST 1: Library Page Interactions ---');
  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle0' });
    await checkNoIllegalStrings('Library initial load');

    // 1.1 Market chip filter
    console.log('Testing Market chips (NIFTY / SENSEX)...');
    const niftyChip = await page.waitForSelector('button::-p-text(NIFTY)', { timeout: 5000 });
    await niftyChip.click();
    await page.waitForNetworkIdle({ timeout: 2000 }).catch(() => {});
    await checkNoIllegalStrings('Library after clicking NIFTY');

    const sensexChip = await page.waitForSelector('button::-p-text(SENSEX)', { timeout: 5000 });
    await sensexChip.click();
    await page.waitForNetworkIdle({ timeout: 2000 }).catch(() => {});
    await checkNoIllegalStrings('Library after clicking SENSEX');

    // Reset market filter to ALL
    const allMarketChip = await page.waitForSelector('button::-p-text(All)', { timeout: 5000 });
    await allMarketChip.click();

    // 1.2 DTE chips
    console.log('Testing DTE chips (0 / 1 / Any)...');
    const dte0Chip = await page.waitForSelector('button::-p-text(0)', { timeout: 5000 });
    await dte0Chip.click();
    await page.waitForNetworkIdle({ timeout: 2000 }).catch(() => {});
    await checkNoIllegalStrings('Library after clicking DTE 0');

    const dteAnyChip = await page.waitForSelector('button::-p-text(Any)', { timeout: 5000 });
    await dteAnyChip.click();
    await page.waitForNetworkIdle({ timeout: 2000 }).catch(() => {});

    // 1.3 Search input in command palette or filtering
    console.log('Testing Command Palette button in TopBar...');
    const cmdkBtn = await page.$('.cmdk');
    if (cmdkBtn) {
      await cmdkBtn.click();
      await new Promise(r => setTimeout(r, 400));
      const palette = await page.$('.command-palette, [role="dialog"]');
      if (palette) {
        console.log('  Command palette opened successfully');
        // Type into search
        const pInput = await palette.$('input');
        if (pInput) {
          await pInput.type('iron-condor');
          await new Promise(r => setTimeout(r, 300));
          await checkNoIllegalStrings('Command palette search');
        }
        await page.keyboard.press('Escape');
        await new Promise(r => setTimeout(r, 300));
      } else {
        warnings.push('Command palette did not open on .cmdk click');
      }
    }

    // 1.4 Sorting columns
    console.log('Testing Table Column Sorting...');
    const sharpeHeader = await page.$('th::-p-text(Sharpe)') || await page.$('th::-p-text(SHARPE)');
    if (sharpeHeader) {
      await sharpeHeader.click();
      await new Promise(r => setTimeout(r, 300));
      await sharpeHeader.click();
      await new Promise(r => setTimeout(r, 300));
      await checkNoIllegalStrings('Library sorting by Sharpe');
    }
  } catch (err) {
    errors.push(`Library interaction failure: ${err.message}`);
  }

  console.log('--- TEST 2: Run Overview Page Interactions ---');
  try {
    const runId = 'nifty-0dte-strangle-benchmark';
    await page.goto(`${BASE_URL}/runs/${runId}`, { waitUntil: 'networkidle0' });
    await checkNoIllegalStrings('Overview initial load');

    // 2.1 Segment switch: Price · candles vs Equity · drawdown
    console.log('Testing Overview Segment Switch...');
    const equitySeg = await page.$('button::-p-text(Equity · drawdown)') || await page.$('button::-p-text(Equity)');
    if (equitySeg) {
      await equitySeg.click();
      await new Promise(r => setTimeout(r, 500));
      await checkNoIllegalStrings('Overview Equity segment');
    }
    const priceSeg = await page.$('button::-p-text(Price · candles)') || await page.$('button::-p-text(Price)');
    if (priceSeg) {
      await priceSeg.click();
      await new Promise(r => setTimeout(r, 500));
      await checkNoIllegalStrings('Overview Price segment');
    }

    // 2.2 Trade inspector navigation with keyboard [ and ]
    console.log('Testing Trade Inspector keyboard navigation...');
    await page.keyboard.press('[');
    await new Promise(r => setTimeout(r, 300));
    await checkNoIllegalStrings('Overview press [');
    await page.keyboard.press(']');
    await new Promise(r => setTimeout(r, 300));
    await checkNoIllegalStrings('Overview press ]');

    // 2.3 Monthly heatmap cells
    const monthlyCells = await page.$$('.heat__cell');
    console.log(`  Found ${monthlyCells.length} monthly heatmap cells`);
    if (monthlyCells.length === 0) {
      warnings.push('No monthly heatmap cells found on overview page');
    }

    // 2.4 Tab navigation to Trades
    console.log('Testing Tab Navigation in Run view...');
    const tradesTab = await page.waitForSelector('a[href*="/trades"]', { timeout: 3000 });
    await tradesTab.click();
    await page.waitForNetworkIdle({ timeout: 5000 });
    if (!page.url().includes('/trades')) {
      errors.push(`Tab navigation to /trades failed, current URL: ${page.url()}`);
    }
  } catch (err) {
    errors.push(`Overview interaction failure: ${err.message}`);
  }

  console.log('--- TEST 3: Run Trades Page Interactions ---');
  try {
    await checkNoIllegalStrings('Trades tab initial load');

    // 3.1 Exit Reason dropdown
    console.log('Testing Exit Reason dropdown filter...');
    const selectInputs = await page.$$('select');
    if (selectInputs.length > 0) {
      const exitReasonSelect = selectInputs[0];
      const options = await exitReasonSelect.$$eval('option', opts => opts.map(o => o.value));
      console.log(`  Available exit reason options: ${options.join(', ')}`);
      if (options.length > 1) {
        await exitReasonSelect.select(options[1]);
        await new Promise(r => setTimeout(r, 500));
        await checkNoIllegalStrings(`Trades tab after selecting exit reason "${options[1]}"`);
        // Reset to first
        await exitReasonSelect.select(options[0]);
      }
    }

    // 3.2 Row expansion for trade legs
    console.log('Testing Trade row expansion...');
    const tradeRows = await page.$$('tbody tr');
    if (tradeRows.length > 0) {
      await tradeRows[0].click();
      await new Promise(r => setTimeout(r, 500));
      await checkNoIllegalStrings('Trades row expanded');
    }

    // 3.3 Pagination
    console.log('Testing Trades Pagination...');
    const nextBtn = await page.$('button::-p-text(Next)') || await page.$('button[aria-label="Next page"]');
    if (nextBtn && !(await nextBtn.evaluate(b => b.disabled))) {
      await nextBtn.click();
      await new Promise(r => setTimeout(r, 500));
      await checkNoIllegalStrings('Trades page 2');
      const prevBtn = await page.$('button::-p-text(Previous)') || await page.$('button[aria-label="Previous page"]');
      if (prevBtn) {
        await prevBtn.click();
        await new Promise(r => setTimeout(r, 500));
      }
    }

    // 3.4 CSV Export button
    console.log('Testing CSV Export button...');
    const exportBtn = await page.$('button::-p-text(Export CSV)') || await page.$('button::-p-text(CSV)');
    if (exportBtn) {
      await exportBtn.click();
      await new Promise(r => setTimeout(r, 500));
      console.log('  CSV export button clicked successfully');
    }
  } catch (err) {
    errors.push(`Trades interaction failure: ${err.message}`);
  }

  console.log('--- TEST 4: Run Diagnostics Page Interactions ---');
  try {
    const runId = 'nifty-0dte-strangle-benchmark';
    await page.goto(`${BASE_URL}/runs/${runId}/diagnostics`, { waitUntil: 'networkidle0' });
    await checkNoIllegalStrings('Diagnostics initial load');

    // 4.1 Copy config button
    console.log('Testing Copy Config button...');
    const copyBtn = await page.$('button::-p-text(Copy manifest JSON)') || await page.$('button::-p-text(Copy config)') || await page.$('button::-p-text(Copy)');
    if (copyBtn) {
      await copyBtn.click();
      await new Promise(r => setTimeout(r, 300));
      console.log('  Copy config button clicked');
    }

    // 4.2 Check Sections
    const sections = ['DATA COVERAGE', 'EXIT REASONS', 'Where the money went', 'STABILITY', 'EXTREMES'];
    const bodyText = await page.evaluate(() => document.body.innerText.toLowerCase());
    for (const sec of sections) {
      if (!bodyText.includes(sec.toLowerCase())) {
        errors.push(`Diagnostics missing section "${sec}"`);
      }
    }
  } catch (err) {
    errors.push(`Diagnostics interaction failure: ${err.message}`);
  }

  console.log('--- TEST 5: Compare Page Interactions ---');
  try {
    await page.goto(`${BASE_URL}/compare?ids=nifty-0dte-strangle-benchmark,sensex-0dte-strangle-benchmark`, { waitUntil: 'networkidle0' });
    await checkNoIllegalStrings('Compare initial load');

    // 5.1 Copy Link button
    console.log('Testing Copy Link button in Compare...');
    const copyLinkBtn = await page.$('button::-p-text(Copy link)');
    if (copyLinkBtn) {
      await copyLinkBtn.click();
      await new Promise(r => setTimeout(r, 300));
      console.log('  Copy link clicked');
    }

    // 5.2 Add run modal / picker
    console.log('Testing Add Run button in Compare...');
    const addRunBtn = await page.$('button::-p-text(Add run)') || await page.$('button::-p-text(+ Add run)');
    if (addRunBtn) {
      await addRunBtn.click();
      await new Promise(r => setTimeout(r, 500));
      // Modal should appear
      const modal = await page.$('.modal, [role="dialog"], .picker-dialog');
      if (modal) {
        console.log('  Add run modal opened successfully');
        // Close modal
        const closeBtn = await modal.$('button::-p-text(Cancel)') || await modal.$('button::-p-text(Close)') || await modal.$('.modal-close');
        if (closeBtn) {
          await closeBtn.click();
        } else {
          await page.keyboard.press('Escape');
        }
        await new Promise(r => setTimeout(r, 300));
      }
    }

    // 5.3 Remove a run
    console.log('Testing Remove run button (×)...');
    const removeBtns = await page.$$('.remove-run, button[aria-label*="Remove"], button::-p-text(×)');
    if (removeBtns.length > 0) {
      await removeBtns[0].click();
      await new Promise(r => setTimeout(r, 500));
      await checkNoIllegalStrings('Compare after removing a run');
      console.log('  Run removed successfully');
    }
  } catch (err) {
    errors.push(`Compare interaction failure: ${err.message}`);
  }

  console.log('--- TEST 6: Group Heatmap Page Interactions ---');
  try {
    await page.goto(`${BASE_URL}/groups/validated-timing-3y`, { waitUntil: 'networkidle0' });
    await checkNoIllegalStrings('Group Heatmap initial load');

    // 6.1 Matrix cell click
    console.log('Testing Heatmap cell click...');
    const cells = await page.$$('.matrix-cell, .heatmap-cell, td[data-run-id], td.cell, .heat-grid__cell');
    if (cells.length > 0) {
      await cells[0].click();
      await new Promise(r => setTimeout(r, 500));
      await checkNoIllegalStrings('Group Heatmap after clicking cell');
      console.log(`  Found ${cells.length} cells; clicked first cell`);
    }

    // 6.2 Compare top 4 button
    console.log('Testing Compare top 4 button...');
    const compareTopBtn = await page.$('button::-p-text(Compare top 4)');
    if (compareTopBtn) {
      await compareTopBtn.click();
      await page.waitForNetworkIdle({ timeout: 5000 });
      console.log(`  Compare top 4 navigated to: ${page.url()}`);
      if (!page.url().includes('/compare?ids=')) {
        errors.push(`Compare top 4 button did not navigate to /compare?ids=, went to ${page.url()}`);
      }
    }
  } catch (err) {
    errors.push(`Group Heatmap interaction failure: ${err.message}`);
  }

  console.log('--- TEST 7: New Run Page Interactions ---');
  try {
    await page.goto(`${BASE_URL}/new`, { waitUntil: 'networkidle0' });
    await checkNoIllegalStrings('New Run initial load');

    // 7.1 Parameter adjustments & live command update
    console.log('Testing form inputs & live command generation...');
    const numInputs = await page.$$('input[type="number"]');
    if (numInputs.length > 0) {
      const cashInput = numInputs[0]; // Starting cash
      await cashInput.click({ clickCount: 3 });
      await cashInput.type('250000');
      await new Promise(r => setTimeout(r, 300));
      const cmdCode = await page.$eval('.code', el => el.innerText).catch(() => '');
      if (!cmdCode.includes('250000')) {
        warnings.push(`Command code preview did not reflect updated cash: ${cmdCode}`);
      } else {
        console.log('  Command preview updated with new cash: 250000');
      }
    }

    // 7.2 Copy command button
    console.log('Testing Copy Command button...');
    const copyCmdBtn = await page.$('button::-p-text(Copy command)');
    if (copyCmdBtn) {
      await copyCmdBtn.click();
      await new Promise(r => setTimeout(r, 300));
      console.log('  Copy command button clicked');
    }

    // 7.3 Reset button
    console.log('Testing Reset button...');
    const resetBtn = await page.$('button::-p-text(Reset)');
    if (resetBtn) {
      await resetBtn.click();
      await new Promise(r => setTimeout(r, 300));
      console.log('  Reset button clicked');
    }
  } catch (err) {
    errors.push(`New Run interaction failure: ${err.message}`);
  }

  await browser.close();

  console.log('\n========================================');
  console.log(`INTERACTIVE UAT RESULTS:`);
  console.log(`Errors: ${errors.length}`);
  errors.forEach(e => console.error(`  ❌ ${e}`));
  console.log(`Warnings: ${warnings.length}`);
  warnings.forEach(w => console.warn(`  ⚠️  ${w}`));
  console.log('========================================');

  process.exit(errors.length > 0 ? 1 : 0);
}

runInteractiveUAT();

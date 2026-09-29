const puppeteer = require('puppeteer');

const SCREENS = [
  {
    name: 'Library',
    url: 'http://127.0.0.1:8000/',
    expectedTexts: ['122 runs', 'NIFTY', 'SENSEX', 'RETURN VS MAX DRAWDOWN'],
  },
  {
    name: 'Run Overview',
    url: 'http://127.0.0.1:8000/runs/nifty-0dte-strangle-benchmark',
    expectedTexts: ['Net P&L', 'CAGR', 'Sharpe', 'Max drawdown', 'Profit factor', 'Hit rate'],
  },
  {
    name: 'Run Trades',
    url: 'http://127.0.0.1:8000/runs/nifty-0dte-strangle-benchmark/trades',
    expectedTexts: ['Exit reason: any', 'Data flag: any', 'Times in IST', 'Gross − fees − slippage = net ✓'],
  },
  {
    name: 'Run Diagnostics (Benchmark)',
    url: 'http://127.0.0.1:8000/runs/nifty-0dte-strangle-benchmark/diagnostics',
    expectedTexts: ['DATA COVERAGE', 'EXIT REASONS', 'Where the money went', 'STABILITY', 'EXTREMES'],
  },
  {
    name: 'Run Diagnostics (Validated)',
    url: 'http://127.0.0.1:8000/runs/validated-timing-3y-sensex-0dte-static/diagnostics',
    expectedTexts: ['DATA COVERAGE', 'EXIT REASONS', 'Where the money went', 'STABILITY', 'EXTREMES'],
  },
  {
    name: 'Full Chart',
    url: 'http://127.0.0.1:8000/runs/nifty-0dte-strangle-benchmark/chart',
    expectedTexts: ['Back to run', 'Go to date'],
  },
  {
    name: 'Compare',
    url: 'http://127.0.0.1:8000/compare?ids=nifty-0dte-strangle-benchmark,sensex-0dte-strangle-benchmark',
    expectedTexts: ['2 runs, one calendar', 'Copy link', 'Cumulative return on capital'],
  },
  {
    name: 'Groups List',
    url: 'http://127.0.0.1:8000/groups',
    expectedTexts: ['1 groups', '3-year timing sweep', 'validated-timing-3y'],
  },
  {
    name: 'Group Heatmap',
    url: 'http://127.0.0.1:8000/groups/validated-timing-3y',
    expectedTexts: ['3-year timing sweep', 'Compare top 4', 'Mean return', 'Mean Sharpe', 'KNOB EFFECTS'],
  },
  {
    name: 'New Run',
    url: 'http://127.0.0.1:8000/new',
    expectedTexts: ['Build a backtest command', 'Parameters', 'COMMAND', 'Copy command', 'Reset'],
  },
  {
    name: 'UI Kit',
    url: 'http://127.0.0.1:8000/_kit',
    expectedTexts: ['BUTTONS · BUTTON', 'STATUSBADGE · ALL VALUES', 'VERDICTPILL · 5 STATES'],
  },
  {
    name: '404 Page',
    url: 'http://127.0.0.1:8000/not-found-random-page',
    expectedTexts: ['Page not found', 'Go to Library'],
  },
  {
    name: 'Unknown Run 404',
    url: 'http://127.0.0.1:8000/runs/nonexistent-run-xyz',
    expectedTexts: ['not found', 'Go to Library'],
    expect404: true,
  },
];

async function runUAT() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  let totalErrors = 0;

  for (const screen of SCREENS) {
    console.log(`\n========================================`);
    console.log(`Testing screen: ${screen.name} (${screen.url})`);
    console.log(`========================================`);

    const pageErrors = [];
    const consoleErrors = [];

    const onPageError = (err) => pageErrors.push(err.message);
    const onConsole = (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (screen.expect404 && text.includes('404')) {
          return; // Expected 404 error
        }
        consoleErrors.push(text);
      }
    };

    page.on('pageerror', onPageError);
    page.on('console', onConsole);

    try {
      await page.goto(screen.url, { waitUntil: 'networkidle0', timeout: 15000 });

      // Check for raw NaN / undefined in body text
      const bodyText = await page.evaluate(() => document.body.innerText);

      // Check expected texts (case-insensitive to allow CSS uppercase eyebrows)
      for (const exp of screen.expectedTexts) {
        if (!bodyText.toLowerCase().includes(exp.toLowerCase())) {
          console.error(`  ❌ Missing expected text: "${exp}"`);
          totalErrors++;
        } else {
          console.log(`  ✓ Found expected text: "${exp}"`);
        }
      }

      // Check for illegal strings
      const forbidden = ['NaN', 'undefined', 'Infinity'];
      for (const bad of forbidden) {
        const regex = new RegExp(`\\b${bad}\\b`);
        if (regex.test(bodyText) && !screen.url.includes('_kit')) {
          console.error(`  ❌ Found forbidden string: "${bad}" in body text`);
          totalErrors++;
        }
      }

      if (pageErrors.length > 0) {
        console.error(`  ❌ Page errors:`, pageErrors);
        totalErrors += pageErrors.length;
      }
      if (consoleErrors.length > 0) {
        console.error(`  ❌ Console errors:`, consoleErrors);
        totalErrors += consoleErrors.length;
      }

      if (pageErrors.length === 0 && consoleErrors.length === 0) {
        console.log(`  ✓ 0 errors on ${screen.name}`);
      }
    } catch (e) {
      console.error(`  ❌ Navigation / render failed:`, e.message);
      totalErrors++;
    } finally {
      page.off('pageerror', onPageError);
      page.off('console', onConsole);
    }
  }

  await browser.close();

  console.log(`\n========================================`);
  console.log(`UAT SUMMARY: Total Errors = ${totalErrors}`);
  console.log(`========================================`);
  process.exit(totalErrors > 0 ? 1 : 0);
}

runUAT();

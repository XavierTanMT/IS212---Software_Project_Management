const path = require('path');
const fs = require('fs');
const express = require('express');
const { instrumentSync } = require('istanbul-lib-instrument');
const glob = require('glob');
const mkdirp = require('mkdirp');
const { chromium } = require('playwright');
const libCoverage = require('istanbul-lib-coverage');
const libReport = require('istanbul-lib-report');
const reports = require('istanbul-reports');

// Basic config
const ROOT = path.resolve(__dirname, '..');
const FRONTEND_DIR = path.join(ROOT, '..', 'frontend_Xavier');
const PORT = process.env.PORT || 8001;

function instrumentFiles(srcDir, outDir) {
  const files = glob.sync('**/*.js', { cwd: srcDir, nodir: true });
  files.forEach((file) => {
    const srcPath = path.join(srcDir, file);
    const outPath = path.join(outDir, file);
    const code = fs.readFileSync(srcPath, 'utf8');
    const instrumented = instrumentSync(code, { filename: file });
    mkdirp.sync(path.dirname(outPath));
    fs.writeFileSync(outPath, instrumented, 'utf8');
  });
}

async function run() {
  const tmp = path.join(__dirname, 'dist');
  if (fs.existsSync(tmp)) fs.rmSync(tmp, { recursive: true, force: true });
  mkdirp.sync(tmp);

  // Copy frontend files to temp dir, instrument .js files
  const copyFiles = glob.sync('**/*', { cwd: FRONTEND_DIR, dot: true, nodir: true });
  copyFiles.forEach((file) => {
    const src = path.join(FRONTEND_DIR, file);
    const dest = path.join(tmp, file);
    mkdirp.sync(path.dirname(dest));
    fs.copyFileSync(src, dest);
  });

  // Instrument JS in-place in tmp
  instrumentFiles(tmp, tmp);

  // Start express server to serve tmp
  const app = express();
  app.use(express.static(tmp));
  const server = app.listen(PORT, () => console.log('Serving instrumented frontend on', PORT));

  // Use Playwright to navigate several frontend pages capturing window.__coverage__
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const coverage = libCoverage.createCoverageMap({});

  const pagesToVisit = [
    '/frontend_Xavier/login.html',
    '/frontend_Xavier/index.html',
  ];

  for (const p of pagesToVisit) {
    try {
      await page.goto(`http://127.0.0.1:${PORT}${p}`, { waitUntil: 'networkidle' });
      // Give scripts a little time
      await page.waitForTimeout(250);
      const cw = await page.evaluate(() => window.__coverage__ || null);
      if (cw) {
        coverage.merge(cw);
      }
    } catch (err) {
      console.warn('Failed to visit', p, err.message);
    }
  }

  // Write coverage to lcov and html
  const map = coverage;
  const context = libReport.createContext({ dir: path.join(__dirname, 'coverage') });
  const tree = libReport.summarizers.pkg(map);
  const lcovReport = reports.create('lcovonly', {});
  const htmlReport = reports.create('html', {});
  lcovReport.execute(context);
  htmlReport.execute(context);

  // Cleanup
  await browser.close();
  server.close();

  // Also dump coverage.json for debugging
  mkdirp.sync(path.join(__dirname, 'coverage'));
  fs.writeFileSync(path.join(__dirname, 'coverage', 'coverage.json'), JSON.stringify(map), 'utf8');

  console.log('Coverage written to tools/frontend-coverage/coverage');
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});

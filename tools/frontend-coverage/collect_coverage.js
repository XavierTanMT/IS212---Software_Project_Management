const path = require('path');
const fs = require('fs');
const express = require('express');
const glob = require('glob');
const mkdirp = require('mkdirp');
const { chromium } = require('playwright');
const v8ToIstanbul = require('v8-to-istanbul');
const libCoverage = require('istanbul-lib-coverage');
const libReport = require('istanbul-lib-report');
const reports = require('istanbul-reports');

const ROOT = path.resolve(__dirname, '..');
const FRONTEND_DIR = path.join(ROOT, '..', 'frontend_Xavier');
const PORT = process.env.PORT || 8001;

async function convertV8ToIstanbul(rawCoverage) {
  const map = libCoverage.createCoverageMap({});
  for (const entry of rawCoverage) {
    try {
      const url = entry.url;
      if (!url || !url.startsWith('http')) continue;
      // map URL to local file path
      const relPath = url.replace(`http://127.0.0.1:${PORT}/`, '');
      const localPath = path.join(__dirname, 'dist', relPath);
      if (!fs.existsSync(localPath)) continue;

      const converter = v8ToIstanbul(localPath);
      await converter.load();
      converter.applyCoverage(entry.functions);
      const fileCov = converter.toIstanbul();
      map.merge(fileCov);
    } catch (err) {
      console.warn('Failed converting coverage for', entry.url, err.message);
    }
  }
  return map;
}

async function run() {
  const tmp = path.join(__dirname, 'dist');
  if (fs.existsSync(tmp)) fs.rmSync(tmp, { recursive: true, force: true });
  mkdirp.sync(tmp);

  // Copy frontend files to tmp
  const copyFiles = glob.sync('**/*', { cwd: FRONTEND_DIR, dot: true, nodir: true });
  copyFiles.forEach((file) => {
    const src = path.join(FRONTEND_DIR, file);
    const dest = path.join(tmp, file);
    mkdirp.sync(path.dirname(dest));
    fs.copyFileSync(src, dest);
  });

  // Serve tmp
  const app = express();
  app.use(express.static(tmp));
  const server = app.listen(PORT, () => console.log('Serving frontend on', PORT));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Start precise coverage using CDP
  const client = await page.context().newCDPSession(page);
  await client.send('Profiler.enable');
  await client.send('Profiler.startPreciseCoverage', { callCount: false, detailed: true });

  const pagesToVisit = [
    '/frontend_Xavier/login.html',
    '/frontend_Xavier/index.html',
  ];

  for (const p of pagesToVisit) {
    try {
      await page.goto(`http://127.0.0.1:${PORT}${p}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(250);
    } catch (err) {
      console.warn('Failed to visit', p, err.message);
    }
  }

  // Take coverage
  const take = await client.send('Profiler.takePreciseCoverage');
  await client.send('Profiler.stopPreciseCoverage');
  await client.detach();

  // Convert and write reports
  const coverageMap = await convertV8ToIstanbul(take.result || []);
  const outDir = path.join(__dirname, 'coverage');
  mkdirp.sync(outDir);
  const contextReport = libReport.createContext({ dir: outDir, coverageMap });
  const tree = libReport.summarizers.pkg(coverageMap);
  tree.visit(reports.create('lcovonly', {}), contextReport);
  tree.visit(reports.create('html', {}), contextReport);
  fs.writeFileSync(path.join(outDir, 'coverage.json'), JSON.stringify(coverageMap.toJSON ? coverageMap.toJSON() : coverageMap), 'utf8');

  await browser.close();
  server.close();

  console.log('Frontend coverage written to', outDir);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
const path = require('path');
const fs = require('fs');
const express = require('express');
const { createInstrumenter } = require('istanbul-lib-instrument');
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

  // Support different istanbul-lib-instrument shapes
  const instrumentLib = require('istanbul-lib-instrument');
  let instrumentFunc = null;
  if (instrumentLib && typeof instrumentLib.createInstrumenter === 'function') {
    const instr = instrumentLib.createInstrumenter();
    if (typeof instr.instrumentSync === 'function') {
      instrumentFunc = (code, filename) => instr.instrumentSync(code, filename);
    } else if (typeof instr.instrument === 'function') {
      // fallback to sync wrapper around async instrument (rare)
      instrumentFunc = (code, filename) => {
        let result = null;
        instr.instrument(code, filename, (err, res) => {
          if (err) throw err;
          result = res;
        });
        if (result === null) throw new Error('Async instrument not supported in sync mode');
        return result;
      };
    }
  }
  if (!instrumentFunc && typeof instrumentLib.instrumentSync === 'function') {
    instrumentFunc = (code, filename) => instrumentLib.instrumentSync(code, filename);
  }
  if (!instrumentFunc) throw new Error('No available instrument function from istanbul-lib-instrument');

  files.forEach((file) => {
    const srcPath = path.join(srcDir, file);
    const outPath = path.join(outDir, file);
    const code = fs.readFileSync(srcPath, 'utf8');
    const instrumented = instrumentFunc(code, srcPath);
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
  const outDir = path.join(__dirname, 'coverage');
  mkdirp.sync(outDir);
  const context = libReport.createContext({ dir: outDir, coverageMap: map });
  const tree = libReport.summarizers.pkg(map);
  tree.visit(reports.create('lcovonly', {}), context);
  tree.visit(reports.create('html', {}), context);

  // Cleanup
  await browser.close();
  server.close();

  // Also dump coverage.json for debugging
  mkdirp.sync(path.join(__dirname, 'coverage'));
  fs.writeFileSync(path.join(__dirname, 'coverage', 'coverage.json'), JSON.stringify(map.toJSON ? map.toJSON() : map), 'utf8');

  console.log('Coverage written to tools/frontend-coverage/coverage');
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});

// Clean Playwright CDP -> v8-to-istanbul -> istanbul reports collector
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

const FRONTEND_DIR = path.join(__dirname, '..', '..', 'frontend_Xavier');
const PORT = process.env.PORT || 8001;

async function convertV8ToIstanbul(rawCoverage) {
  const map = libCoverage.createCoverageMap({});
  for (const entry of rawCoverage) {
    try {
      const url = entry.url;
      if (!url || !url.startsWith('http')) continue;
      const relPath = url.replace(`http://127.0.0.1:${PORT}/`, '');
      const localPath = path.join(__dirname, 'dist', relPath);
      if (!fs.existsSync(localPath)) continue;

      const converter = v8ToIstanbul(localPath);
      await converter.load();
      converter.applyCoverage(entry.functions || []);
      map.merge(converter.toIstanbul());
    } catch (err) {
      console.warn('Failed converting coverage for', entry.url, err && err.message);
    }
  }
  return map;
}

async function run() {
  const tmp = path.join(__dirname, 'dist');
  if (fs.existsSync(tmp)) fs.rmSync(tmp, { recursive: true, force: true });
  mkdirp.sync(tmp);

  const copyFiles = glob.sync('**/*', { cwd: FRONTEND_DIR, dot: true, nodir: true });
  copyFiles.forEach((file) => {
    const src = path.join(FRONTEND_DIR, file);
    const dest = path.join(tmp, file);
    mkdirp.sync(path.dirname(dest));
    fs.copyFileSync(src, dest);
  });

  const app = express();
  app.use(express.static(tmp));
  const server = app.listen(PORT, () => console.log('Serving frontend on', PORT));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const client = await context.newCDPSession(page);
  await client.send('Profiler.enable');
  await client.send('Profiler.startPreciseCoverage', { callCount: false, detailed: true });

  const pagesToVisit = [
    '/frontend_Xavier/login.html',
    '/frontend_Xavier/index.html',
  ];

  for (const p of pagesToVisit) {
    try {
      await page.goto(`http://127.0.0.1:${PORT}${p}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(300);
    } catch (err) {
      console.warn('Failed to visit', p, err && err.message);
    }
  }

  const take = await client.send('Profiler.takePreciseCoverage');
  await client.send('Profiler.stopPreciseCoverage');
  await client.detach();

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

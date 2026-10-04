/* End-to-end test for the 67 Jumpscare extension.
 *
 *   node tests/e2e.js
 *
 * Loads the real unpacked extension into Chromium, types at it, and checks what
 * happens. Needs Playwright on NODE_PATH; serves its own fixture, no other deps.
 */
const { chromium } = require('playwright');
const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const EXT = path.join(ROOT, 'extension');
const FIXTURE = path.join(__dirname, 'fixture.html');
const PORT = Number(process.env.PORT) || 8731;

// Chrome derives an unpacked extension's id from the SHA-256 of its absolute path.
const unpackedId = (p) =>
  crypto.createHash('sha256').update(p, 'utf8').digest('hex').slice(0, 32)
    .replace(/[0-9a-f]/g, (c) => String.fromCharCode(97 + parseInt(c, 16)));

// Content scripts don't match data: URLs, so the fixture has to be served for real.
function serve() {
  const html = fs.readFileSync(FIXTURE);
  const server = http.createServer((_req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
  });
  return new Promise((resolve) => server.listen(PORT, '127.0.0.1', () => resolve(server)));
}

(async () => {
  const server = await serve();
  const extId = unpackedId(EXT);

  const ctx = await chromium.launchPersistentContext('', {
    channel: 'chromium',
    headless: true,
    args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`, '--no-sandbox'],
  });

  const page = await ctx.newPage();
  await page.setViewportSize({ width: 1000, height: 700 });
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'load' });
  await page.waitForTimeout(900); // let the content script read storage

  const results = [];
  const check = (name, pass, extra = '') =>
    results.push(`${pass ? 'PASS' : 'FAIL'}  ${name}${extra ? '  [' + extra + ']' : ''}`);

  const scared = () =>
    page.evaluate(() => !!document.querySelector('[data-sixty-seven-jumpscare]'));

  async function reset() {
    if (await scared()) await page.keyboard.press('Escape');
    await page.waitForTimeout(2100); // 250ms dismiss grace + 1.5s default cooldown
    await page.fill('#a', '').catch(() => {});
    await page.fill('#t', '').catch(() => {});
  }

  async function typeAndWatch(sel, text, delay = 50) {
    await page.click(sel);
    await page.keyboard.type(text, { delay });
    await page.waitForTimeout(450);
    return scared();
  }

  // --- the headline behaviour --------------------------------------------
  check('typing "67" in an input fires the scare', await typeAndWatch('#a', '67'));

  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
  check('Escape dismisses the overlay', !(await scared()));
  await reset();

  check('"route 67" (67 at the end) fires', await typeAndWatch('#t', 'route 67', 40));
  await reset();

  check('loose match "6-7" in a contenteditable fires', await typeAndWatch('#ce', '6-7', 40));
  await reset();

  // --- things that must NOT fire, each with a positive control ------------
  check('password field is spared', !(await typeAndWatch('#p', '67', 40)));
  check('  control: still armed immediately after', await typeAndWatch('#a', '67', 40));
  await reset();

  // "76543" holds no 6-then-7, loose or strict.
  check('"76543" does not fire', !(await typeAndWatch('#a', '76543', 30)));
  check('  control: still armed immediately after', await typeAndWatch('#a', '67', 40));
  await reset();

  await page.click('#a');
  await page.keyboard.type('hello', { delay: 20 });
  check('keystrokes still reach the page', (await page.inputValue('#a')) === 'hello',
        await page.inputValue('#a'));
  await reset();

  // --- cooldown -----------------------------------------------------------
  const first = await typeAndWatch('#a', '67', 30);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
  const second = await typeAndWatch('#a', '67', 30);
  check('cooldown blocks an immediate repeat', first && !second);
  await reset();

  // --- the overlay itself --------------------------------------------------
  const fired = await typeAndWatch('#a', '67', 30);
  const geom = fired ? await page.evaluate(() => {
    const host = document.querySelector('[data-sixty-seven-jumpscare]');
    const cs = getComputedStyle(host);
    const r = host.getBoundingClientRect();
    return { z: cs.zIndex, pos: cs.position, w: r.width, h: r.height,
             closed: host.shadowRoot === null };
  }) : null;
  check('overlay is fixed, full-viewport, max z-index',
        !!geom && geom.pos === 'fixed' && geom.z === '2147483647' &&
        geom.w >= 1000 && geom.h >= 700,
        geom ? `z=${geom.z} ${geom.w}x${geom.h}` : 'no overlay');
  check('shadow root is closed to page scripts', !!geom && geom.closed);

  await page.waitForTimeout(2600);
  check('overlay auto-dismisses after its duration', !(await scared()));
  await reset();

  // --- the popup drives settings live --------------------------------------
  const popup = await ctx.newPage();
  const popupErrors = [];
  popup.on('pageerror', (e) => popupErrors.push(String(e)));
  await popup.goto(`chrome-extension://${extId}/popup/popup.html`);
  await popup.waitForTimeout(400);
  check('popup renders with no JS errors', popupErrors.length === 0, popupErrors.join('; '));

  await popup.uncheck('#enabled');
  await popup.waitForTimeout(500);
  await page.bringToFront();
  check('master switch OFF stops scares on an open tab', !(await typeAndWatch('#a', '67', 30)));

  await popup.bringToFront();
  await popup.check('#enabled');
  await popup.waitForTimeout(500);
  await page.bringToFront();
  check('master switch ON resumes scares on an open tab', await typeAndWatch('#a', '67', 30));
  await reset();

  await popup.bringToFront();
  await popup.fill('#blocklist', '127.0.0.1');
  await popup.waitForTimeout(900); // input debounce
  await page.bringToFront();
  check('blocklisted host is left alone', !(await typeAndWatch('#a', '67', 30)));

  await popup.bringToFront();
  await popup.fill('#blocklist', '');
  await popup.waitForTimeout(900);
  await page.bringToFront();
  check('  control: fires again once un-blocked', await typeAndWatch('#a', '67', 30));
  await reset();

  await popup.bringToFront();
  await popup.reload();
  await popup.waitForTimeout(400);
  const counter = (await popup.textContent('#count')).trim();
  check('scare counter increments', /^[1-9]\d*\s+scares?\s+so far$/.test(counter), counter);

  check('no uncaught errors on the content page', pageErrors.length === 0, pageErrors.join('; '));

  console.log('\n' + results.join('\n') + '\n');
  const failed = results.filter((r) => r.startsWith('FAIL')).length;
  console.log(failed ? `${failed} FAILING` : 'ALL GREEN');

  await ctx.close();
  server.close();
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error('ERROR', e); process.exit(2); });

#!/usr/bin/env node
/**
 * Drive the local world viewer in a real Chromium browser and capture runtime
 * evidence: readiness, viewer counters, original-startup streaming trace,
 * console errors and a screenshot.
 *
 * This is a verification harness only. It launches an installed Chrome with an
 * isolated temporary profile; it does not modify the page or the game install.
 *
 * Usage:
 *   node scripts/capture-world.mjs --region=__baseline__ --shot=research/screenshots/world-pass3-baseline.jpg
 *   node scripts/capture-world.mjs --region=__startup__ --record=research/world-recovery/browser-validation-pass3.json --timeout=900000
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { once } from 'node:events';

const args = new Map(process.argv.slice(2).map(arg => {
  const index = arg.indexOf('=');
  return index < 0 ? [arg.replace(/^--/, ''), 'true'] : [arg.slice(2, index), arg.slice(index + 1)];
}));
const region = args.get('region') ?? '__baseline__';
const baseUrl = args.get('url') ?? 'http://127.0.0.1:5178/';
const debug = args.get('debug') === '1';
const timeout = Number(args.get('timeout') ?? 420000);
const settle = Number(args.get('settle') ?? 2500);
const shot = args.get('shot') ? path.resolve(args.get('shot')) : null;
const record = args.get('record') ? path.resolve(args.get('record')) : null;
const probe = args.get('probe') ? path.resolve(args.get('probe')) : null;
const width = Number(args.get('width') ?? 1280);
const height = Number(args.get('height') ?? 720);
const chromeCandidates = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].filter(Boolean);
const chromePath = chromeCandidates.find(candidate => fs.existsSync(candidate));
if (!chromePath) throw new Error('No Chrome/Edge executable found; set CHROME_PATH');

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'undefeated-chrome-'));
const chrome = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=0',
  `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows', '--disable-features=CalculateNativeWinOcclusion',
  `--window-size=${width},${height}`, '--force-device-scale-factor=1', '--hide-scrollbars',
  'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
let stderr = '';
chrome.stderr.on('data', chunk => { stderr += chunk.toString(); });
let browserClosed = false;
chrome.on('exit', () => { browserClosed = true; });

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
async function waitFile(file, deadline) {
  while (Date.now() < deadline) {
    if (fs.existsSync(file)) return fs.readFileSync(file, 'utf8');
    if (browserClosed) throw new Error(`Chromium exited before DevTools port was ready\n${stderr}`);
    await delay(100);
  }
  throw new Error(`Timed out waiting for ${file}\n${stderr}`);
}
const portFile = path.join(profile, 'DevToolsActivePort');
const portText = await waitFile(portFile, Date.now() + 30000);
const [port] = portText.split(/\r?\n/);
const httpBase = `http://127.0.0.1:${port}`;
let version = {};
for (let i = 0; i < 100; i++) {
  try { version = await (await fetch(`${httpBase}/json/version`)).json(); break; } catch { await delay(100); }
}
if (!version.webSocketDebuggerUrl) throw new Error('Chromium DevTools endpoint did not become ready');

const targets = await (await fetch(`${httpBase}/json/list`)).json();
const page = targets.find(target => target.type === 'page');
if (!page) throw new Error('No page target');

class CDP {
  constructor(url) { this.next = 0; this.pending = new Map(); this.events = []; this.ws = new WebSocket(url); }
  async open() {
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
    this.ws.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(`${pending.method}: ${message.error.message}`));
        else pending.resolve(message.result);
      } else {
        this.events.push(message);
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.next;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, method });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() { try { this.ws.close(); } catch {} }
}

const cdp = new CDP(page.webSocketDebuggerUrl);
await cdp.open();
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
await cdp.send('Log.enable');
await cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
const url = `${baseUrl}?region=${encodeURIComponent(region)}${debug ? '&debug=1' : ''}`;
await cdp.send('Page.navigate', { url });

const probeExpr = `(() => {
  const canvas = document.querySelector('canvas');
  const data = canvas ? canvas.dataset : {};
  const warning = document.getElementById('world-warning');
  const loading = document.getElementById('loading');
  return JSON.stringify({
    ready: document.body.dataset.ready || '',
    level: document.body.dataset.level || '',
    objects: data.objects || '', terrain: data.terrain || '', failures: data.failures || '',
    textureFailures: data.textureFailures || '', unresolvedMaterials: data.unresolvedMaterials || '',
    ambiguousSlots: data.ambiguousSlots || '', fps: data.fps || '', draws: data.draws || '',
    streaming: data.streaming || '', streamingTrace: data.streamingTrace || '',
    warning: warning && !warning.hidden ? warning.textContent : '',
    loadingHidden: loading ? loading.hidden : null,
    scope: document.getElementById('scope')?.textContent || '',
    size: [innerWidth, innerHeight], devicePixelRatio,
  });
})()`;

const started = Date.now();
const consoleMessages = [];
let data;
for (;;) {
  const result = await cdp.send('Runtime.evaluate', { expression: probeExpr, returnByValue: true });
  if (result.exceptionDetails) throw new Error(`Page probe failed: ${result.exceptionDetails.text}`);
  data = JSON.parse(result.result.value);
  if (data.ready === 'world' || data.ready === 'error') break;
  if (Date.now() - started > timeout) throw new Error(`Timed out waiting for viewer (${data.ready}; ${data.warning})`);
  await delay(500);
}
await delay(settle);
const finalResult = await cdp.send('Runtime.evaluate', { expression: probeExpr, returnByValue: true });
data = JSON.parse(finalResult.result.value);
const consoleErrors = cdp.events
  .filter(event => event.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(event.params.type))
  .map(event => ({ type: event.params.type, text: event.params.args.map(arg => arg.value ?? arg.description ?? '').join(' ') }))
  .slice(-30);

let probeResult = null;
if (probe) {
  const expression = fs.readFileSync(probe, 'utf8');
  const result = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(`Probe failed: ${JSON.stringify(result.exceptionDetails).slice(0, 3000)}`);
  probeResult = result.result.value;
  console.log('PROBE', JSON.stringify(probeResult, null, 1).slice(0, 30000));
}

function parse(value) { try { return value ? JSON.parse(value) : null; } catch { return value; } }
const recordCase = {
  region,
  ready: data.ready,
  level: data.level,
  objects: Number(data.objects) || 0,
  terrain: Number(data.terrain) || 0,
  assetFailures: Number(data.failures) || 0,
  textureFailures: Number(data.textureFailures) || 0,
  unresolvedMaterialCacheKeys: Number(data.unresolvedMaterials) || 0,
  ambiguousSlots: Number(data.ambiguousSlots) || 0,
  fps: Number(data.fps) || 0,
  activeMeshes: Number(data.draws) || 0,
  warning: data.warning,
  scope: data.scope,
  streaming: parse(data.streaming),
  streamingTrace: parse(data.streamingTrace),
  consoleErrors,
  viewport: { width: data.size[0], height: data.size[1], devicePixelRatio: data.devicePixelRatio },
  browser: version.Browser,
  url,
  durationMs: Date.now() - started,
};
if (shot) {
  const image = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 92, captureBeyondViewport: false });
  fs.mkdirSync(path.dirname(shot), { recursive: true });
  fs.writeFileSync(shot, Buffer.from(image.data, 'base64'));
  recordCase.screenshot = path.relative(process.cwd(), shot).replace(/\\/g, '/');
}
if (record) {
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  let document = { schemaVersion: 1, date: today, harness: 'scripts/capture-world.mjs', cases: [] };
  if (fs.existsSync(record)) {
    try { document = { ...document, ...JSON.parse(fs.readFileSync(record, 'utf8')) }; } catch {}
  }
  document.cases = (document.cases ?? []).filter(item => item.region !== region);
  document.cases.push(recordCase);
  document.cases.sort((a, b) => a.region.localeCompare(b.region));
  fs.mkdirSync(path.dirname(record), { recursive: true });
  fs.writeFileSync(record, `${JSON.stringify(document, null, 2)}\n`);
}
console.log(JSON.stringify({ region, ready: recordCase.ready, objects: recordCase.objects, terrain: recordCase.terrain, failures: recordCase.assetFailures, textureFailures: recordCase.textureFailures, fps: recordCase.fps, streamingPhase: recordCase.streaming?.phase, completedCitySteps: recordCase.streaming?.completedCitySteps, traceEvents: recordCase.streamingTrace?.length ?? 0, screenshot: recordCase.screenshot }, null, 1));

try { await cdp.send('Browser.close'); } catch {}
cdp.close();
await Promise.race([once(chrome, 'exit'), delay(5000)]);
if (!browserClosed) {
  try { process.kill(chrome.pid, 'SIGKILL'); } catch {}
}
try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}

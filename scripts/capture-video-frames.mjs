#!/usr/bin/env node
/** Seek a local video in Chromium and capture frames for manual review. */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const args = new Map(process.argv.slice(2).map(arg => {
  const i = arg.indexOf('=');
  return i < 0 ? [arg.replace(/^--/, ''), 'true'] : [arg.slice(2, i), arg.slice(i + 1)];
}));
const video = path.resolve(args.get('video'));
const outDir = path.resolve(args.get('out') ?? 'research/screenshots/video-review');
const count = Number(args.get('count') ?? 24);
const startTime = Number(args.get('start') ?? 0);
const endTime = Number(args.get('end') ?? 0);
const width = Number(args.get('width') ?? 1280);
const height = Number(args.get('height') ?? 720);
const chromeCandidates = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].filter(Boolean);
const chromePath = chromeCandidates.find(candidate => fs.existsSync(candidate));
if (!chromePath) throw new Error('No Chrome/Edge executable');
fs.mkdirSync(outDir, { recursive: true });
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'undefeated-video-'));
const chrome = spawn(chromePath, [
  '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--autoplay-policy=no-user-gesture-required',
  '--allow-file-access-from-files', '--disable-background-timer-throttling',
  `--window-size=${width},${height}`, '--hide-scrollbars', 'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
let stderr = ''; chrome.stderr.on('data', c => { stderr += c; });
const delay = ms => new Promise(r => setTimeout(r, ms));
async function waitFile(file, deadline) {
  while (Date.now() < deadline) {
    if (fs.existsSync(file)) return fs.readFileSync(file, 'utf8');
    await delay(100);
  }
  throw new Error(`timeout ${file}\n${stderr}`);
}
const [port] = (await waitFile(path.join(profile, 'DevToolsActivePort'), Date.now() + 30000)).split(/\r?\n/);
const httpBase = `http://127.0.0.1:${port}`;
let version;
for (let i = 0; i < 100 && !version; i++) { try { version = await (await fetch(`${httpBase}/json/version`)).json(); } catch { await delay(100); } }
const targets = await (await fetch(`${httpBase}/json/list`)).json();
const target = targets.find(t => t.type === 'page');
class CDP {
  constructor(url) { this.id = 0; this.pending = new Map(); this.ws = new WebSocket(url); }
  async open() {
    await new Promise((res, rej) => { this.ws.addEventListener('open', res, { once: true }); this.ws.addEventListener('error', rej, { once: true }); });
    this.ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (!m.id) return; const p = this.pending.get(m.id); if (!p) return; this.pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result); });
  }
  send(method, params = {}) { const id = ++this.id; return new Promise((resolve, reject) => { this.pending.set(id, { resolve, reject }); this.ws.send(JSON.stringify({ id, method, params })); }); }
}
const cdp = new CDP(target.webSocketDebuggerUrl); await cdp.open();
await cdp.send('Page.enable');
await cdp.send('Runtime.enable');
await cdp.send('Page.navigate', { url: pathToFileURL(video).href });
await delay(1500);
let meta;
for (let i = 0; i < 60; i++) {
  const r = await cdp.send('Runtime.evaluate', { expression: `(()=>{const v=document.querySelector('video');return v&&{duration:v.duration,readyState:v.readyState,w:v.videoWidth,h:v.videoHeight}})()`, returnByValue: true });
  meta = r.result.value;
  if (meta?.duration > 0) break;
  await delay(250);
}
if (!meta?.duration) throw new Error(`video metadata unavailable: ${JSON.stringify(meta)}`);
console.log(JSON.stringify(meta));
await cdp.send('Runtime.evaluate', { expression: `(()=>{const v=document.querySelector('video');v.controls=false;v.pause();document.body.style.margin='0';document.body.style.background='#000';v.style.width='100vw';v.style.height='100vh';v.style.objectFit='contain';return true})()` });
const from = Math.max(0, startTime);
const to = endTime > from ? Math.min(meta.duration, endTime) : meta.duration;
const times = Array.from({ length: count }, (_, i) => from + ((to - from) * (i + 0.5)) / count);
for (let i = 0; i < times.length; i++) {
  const t = times[i];
  await cdp.send('Runtime.evaluate', { expression: `new Promise(r=>{const v=document.querySelector('video');v.currentTime=${t};v.onseeked=()=>r(v.currentTime)})`, awaitPromise: true, returnByValue: true });
  await delay(120);
  const shot = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 90 });
  const file = path.join(outDir, `frame-${String(i).padStart(3, '0')}.jpg`);
  fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
  console.log(`${i} ${t.toFixed(2)}s ${file}`);
}
chrome.kill();

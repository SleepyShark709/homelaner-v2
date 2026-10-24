import './style.css';
import { AssetLab } from './assets/AssetLab';
import type { AssetEntry } from './assets/types';

document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
  <aside class="sidebar">
    <a class="brand" href="/" aria-label="UNDEFEATED Web 首页"><span class="brand-mark">U<span>↗</span></span><span>UNDEFEATED<small>WEB RECONSTRUCTION</small></span></a>
    <div class="phase"><span class="dot"></span> PHASE 00 <span>/ 原版资产验证</span></div>
    <h1>原版资产，<br>进入浏览器。</h1>
    <p class="intro">先验证原角色、骨架与动画，再重建城市和玩法。祖国人的外观替换留到最后。</p>
    <div class="section-label">资产目录 <span id="asset-count">—</span></div>
    <nav id="asset-list" aria-label="选择原版资产"><p class="muted">正在读取本地资源…</p></nav>
    <div class="animation-panel">
      <label class="section-label" for="animation">原版动画 <span id="clip-count">—</span></label>
      <select id="animation" disabled><option>等待资产载入</option></select>
      <div class="playback"><button id="play" disabled aria-label="暂停动画">暂停</button><label for="speed">播放速度</label><select id="speed" disabled><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="1.5">1.5×</option></select></div>
      <p id="animation-note" class="micro">仅展示实际导出的动画，不用占位动作替代。</p>
    </div>
    <div class="roadmap"><div class="section-label">实施顺序</div><ol><li class="current"><span>01</span>原版 Web 基线</li><li><span>02</span>按住 E · 热视线</li><li><span>03</span>自由破坏 · 无惩罚</li><li><span>04</span>祖国人外观</li></ol></div>
    <div class="local-note"><span class="dot"></span>LOCAL BUILD <span>独立项目 / Babylon.js</span></div>
  </aside>
  <main>
    <header class="topbar"><div><span class="eyebrow">ASSET LAB</span><span class="separator">/</span><span id="asset-title">加载中</span></div><span class="badge">原版数据 · 本地验证</span></header>
    <section class="viewport" aria-label="三维资产预览">
      <canvas id="viewport" aria-label="拖动旋转视角，滚轮缩放" tabindex="0"></canvas>
      <div class="viewer-tag"><span id="kind">ORIGINAL ASSET</span><small id="source-short">UNDEFEATED / UE 4.27</small></div>
      <div id="load-state" class="load-state" role="status"><span class="loader"></span><p>正在载入原版资产</p></div>
      <div class="viewer-bottom"><span><b>拖动</b> 旋转视角 <i>·</i> <b>滚轮</b> 缩放 <i>·</i> <b>右键拖动</b> 平移</span><span id="fps">— FPS</span></div>
      <div class="toolbar"><button id="reset">重置视角 <span>↗</span></button><button id="skeleton" aria-pressed="false">骨架</button><button id="wireframe" aria-pressed="false">线框</button><button id="rotate" aria-pressed="false">自动旋转</button></div>
    </section>
    <section class="details" aria-label="资产信息">
      <div class="stats"><div><span>骨骼</span><strong id="bones">—</strong></div><div><span>动画片段</span><strong id="animations">—</strong></div><div><span>三角面</span><strong id="triangles">—</strong></div><div><span>模型高度</span><strong id="height">—</strong></div></div>
      <div class="source"><span class="section-label">来源与当前状态</span><p id="asset-note">资产转换验证中。</p><code id="source-package">—</code></div>
    </section>
    <footer>此页用于验证原版资源的 Web 兼容性，尚未实现完整游戏玩法。<span>E:\\undefeated-web</span></footer>
  </main>`;

const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const status = el('load-state');
const animationSelect = el<HTMLSelectElement>('animation');
const playButton = el<HTMLButtonElement>('play');
const speedSelect = el<HTMLSelectElement>('speed');
let lab: AssetLab;
let selection = 0;
let playing = false;

function showError(error: unknown): void {
  status.replaceChildren();
  const label = document.createElement('strong');
  label.textContent = '资源暂时无法载入';
  const message = document.createElement('p');
  message.textContent = error instanceof Error ? error.message : String(error);
  status.append(label, message);
  status.classList.add('error');
  status.hidden = false;
}

async function select(entry: AssetEntry): Promise<void> {
  const current = ++selection;
  delete document.body.dataset.ready;
  status.hidden = false;
  status.classList.remove('error');
  status.innerHTML = '<span class="loader"></span><p>正在载入原版资产</p>';
  document.querySelectorAll<HTMLButtonElement>('.asset-card').forEach(button => {
    button.classList.toggle('active', button.dataset.id === entry.id);
    button.setAttribute('aria-pressed', String(button.dataset.id === entry.id));
  });
  el('asset-title').textContent = entry.label;
  el('kind').textContent = ({ character: 'ORIGINAL CHARACTER', vehicle: 'ORIGINAL VEHICLE', building: 'ORIGINAL BUILDING', prop: 'ORIGINAL PROP' })[entry.kind];
  el('source-package').textContent = entry.sourcePackage;
  el('asset-note').textContent = entry.notes ?? '从本机原游戏提取的资产。';
  animationSelect.disabled = playButton.disabled = speedSelect.disabled = true;
  for (const id of ['bones', 'animations', 'triangles', 'height']) el(id).textContent = '—';
  try {
    const stats = await lab.load(entry);
    if (!stats || current !== selection) return;
    el('bones').textContent = stats.bones.toLocaleString();
    el('animations').textContent = stats.animations.length.toLocaleString();
    el('triangles').textContent = stats.triangles.toLocaleString();
    el('height').textContent = `${stats.height.toFixed(2)} m`;
    el('clip-count').textContent = `${stats.animations.length} CLIPS`;
    animationSelect.replaceChildren();
    if (stats.animations.length) {
      stats.animations.forEach((name, index) => animationSelect.add(new Option(name, String(index))));
      animationSelect.disabled = playButton.disabled = speedSelect.disabled = false;
      playing = true;
      playButton.textContent = '暂停';
      playButton.setAttribute('aria-label', '暂停动画');
      lab.play(0, Number(speedSelect.value));
      el('animation-note').textContent = '原游戏导出的骨骼动画，保持原骨架对应关系。';
    } else {
      animationSelect.add(new Option('此资产无已导入动画'));
      el('animation-note').textContent = entry.kind === 'character' ? '当前仅验证网格与骨架；动画尚未导入。' : '当前展示静态网格。';
    }
    status.hidden = true;
    document.body.dataset.ready = entry.id;
  } catch (error) { if (current === selection) showError(error); }
}

async function start(): Promise<void> {
  try {
    lab = new AssetLab(el<HTMLCanvasElement>('viewport'));
    const response = await fetch('/assets/original/catalog.json');
    if (!response.ok) throw new Error('原版资源目录尚未生成，请先运行资产导出流程。');
    const entries = await response.json() as AssetEntry[];
    if (!Array.isArray(entries) || entries.length === 0) throw new Error('资源目录为空。');
    const list = el('asset-list');
    list.replaceChildren();
    el('asset-count').textContent = `${entries.length} ASSETS`;
    for (const [index, entry] of entries.entries()) {
      const button = document.createElement('button');
      button.className = 'asset-card';
      button.dataset.id = entry.id;
      const number = document.createElement('span'); number.className = 'asset-number'; number.textContent = String(index + 1).padStart(2, '0');
      const text = document.createElement('span'); text.className = 'asset-name'; text.textContent = entry.label;
      const detail = document.createElement('small'); detail.textContent = ({ character: '角色 / 骨架与动画', vehicle: '载具 / 网格与材质', building: '建筑 / 场景资源', prop: '道具 / 场景资源' })[entry.kind]; text.append(detail);
      const arrow = document.createElement('span'); arrow.className = 'asset-arrow'; arrow.textContent = '↗';
      button.append(number, text, arrow);
      button.addEventListener('click', () => void select(entry));
      list.append(button);
    }
    el('reset').onclick = () => lab.resetCamera();
    for (const [id, toggle] of [
      ['skeleton', (enabled: boolean) => lab.setSkeleton(enabled)],
      ['wireframe', (enabled: boolean) => lab.setWireframe(enabled)],
      ['rotate', (enabled: boolean) => lab.setAutoRotate(enabled)],
    ] as const) {
      el(id).onclick = () => {
        const enabled = el(id).getAttribute('aria-pressed') !== 'true';
        el(id).setAttribute('aria-pressed', String(enabled)); toggle(enabled);
      };
    }
    animationSelect.onchange = () => { lab.play(Number(animationSelect.value), Number(speedSelect.value)); playing = true; playButton.textContent = '暂停'; playButton.setAttribute('aria-label', '暂停动画'); };
    playButton.onclick = () => { playing = !playing; lab.setPlaying(playing); playButton.textContent = playing ? '暂停' : '播放'; playButton.setAttribute('aria-label', playing ? '暂停动画' : '播放动画'); };
    speedSelect.onchange = () => lab.setSpeed(Number(speedSelect.value));
    const timer = window.setInterval(() => { el('fps').textContent = `${Math.round(lab.engine.getFps())} FPS`; }, 750);
    window.addEventListener('pagehide', () => { clearInterval(timer); lab.dispose(); }, { once: true });
    await select(entries[0]);
  } catch (error) { showError(error); }
}

void start();

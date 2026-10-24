import './world.css';
import { OriginalWorld } from './world/OriginalWorld';
import { sourceObjectCount } from './world/types';

document.title = 'UNDEFEATED · 原版世界恢复';
document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
  <canvas id="world" tabindex="0" aria-label="原版城市三维场景，拖动鼠标转向，WASD漫游，E上升Q下降"></canvas>
  <header class="world-header"><a href="/" class="world-brand">UNDEFEATED<span>ORIGINAL WORLD</span></a><div class="world-stage"><i></i>原版世界恢复 <small>场景与材质接入中</small></div><a class="world-link" href="/?view=assets">角色与动画 ↗</a></header>
  <aside class="world-panel">
    <span class="world-eyebrow">EXPLORE THE ORIGINAL CITY</span><h1>回到原来的城市。</h1>
    <p class="world-intro">按原关卡坐标装配场景，使用原模型与高度场。当前为场景检查，角色玩法尚未完整恢复。</p>
    <label for="region">选择区域</label><select id="region" disabled><option>正在读取原关卡…</option></select>
    <div class="world-buttons"><button id="overview" disabled>区域全景</button><button id="near" disabled>靠近街区</button></div>
    <label for="speed">漫游速度 <output id="speed-value">4×</output></label><input id="speed" type="range" min="1" max="14" value="4" step="1">
    <div class="world-options"><button id="quality" aria-pressed="false">高清</button><button id="wireframe" aria-pressed="false">线框检查</button></div>
    <div class="world-stats"><div><strong id="object-count">—</strong><span>已装配场景对象</span></div><div><strong id="terrain-count">—</strong><span>原高度场地形块</span></div></div>
    <div class="recovery-note"><span>当前恢复范围</span><p id="scope">正在读取覆盖清单…</p><p>已接入原地表混合与天空 HDR；复杂材质、原光照/雾与后处理仍待还原。新增玩法和换模后置。</p></div>
  </aside>
  <div class="world-crosshair" aria-hidden="true"></div>
  <div class="world-telemetry"><span id="fps">— FPS</span><span id="position">—</span></div>
  <footer class="world-footer"><span><kbd>W A S D</kbd>漫游</span><span><kbd>拖动鼠标</kbd>转向</span><span><kbd>E / SPACE</kbd>上升</span><span><kbd>Q</kbd>下降</span><span><kbd>SHIFT</kbd>加速</span><small>浏览相机控制 · 尚非原角色控制器</small></footer>
  <div class="world-loading" id="loading" role="status"><span class="world-spinner"></span><div><strong id="load-title">恢复原版世界</strong><p id="load-message">读取原关卡与材质清单…</p><progress id="progress" max="1" value="0"></progress></div></div>
  <div id="world-warning" class="world-warning" role="status" hidden></div>`;

const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const canvas = el<HTMLCanvasElement>('world');
const region = el<HTMLSelectElement>('region');
const loading = el('loading');
const warning = el('world-warning');
const viewer = new OriginalWorld(canvas);
// Local verification hook for browser probes. It exposes the already-created
// viewer read-only and does not add gameplay behavior or alter loaded assets.
if (new URLSearchParams(location.search).get('debug') === '1') {
  (window as typeof window & { __undefeatedWorld?: OriginalWorld }).__undefeatedWorld = viewer;
}
const names: Record<string, string> = {
  MainLevel: '主世界 · 道路与地形', ResidentialArea1: '住宅区一', ResidentialArea2: '住宅区二', ResidentialArea3: '住宅区三',
  DownTown: '市中心', Downtown: '市中心', CommercialArea: '商业区', FinancialArea: '金融区', FinancialDistrict: '金融区', IndustrialArea: '工业区',
  Park: '公园', Beach: '海滩', Coast: '海岸', Slam: '贫民区',
  TutorialLevel: '教程场景', DynamicProps: '动态道具 · 静态检查', EnelightMeteor: '陨石场景', LoadLevel: '过渡关卡', TitleMenuLevel: '标题场景',
};
function busy(value: boolean): void {
  loading.hidden = !value; region.disabled = value;
  for (const id of ['overview', 'near', 'quality']) el<HTMLButtonElement>(id).disabled = value;
}
async function select(): Promise<void> {
  busy(true); warning.hidden = true; document.body.dataset.ready = 'loading';
  canvas.dataset.streaming = ''; canvas.dataset.streamingTrace = '[]';
  el('load-title').textContent = '装配原版场景';
  try {
    await viewer.select(region.value);
    if (region.value !== '__startup__') {
      canvas.dataset.streaming = ''; canvas.dataset.streamingTrace = '[]';
      el('scope').textContent = `${viewer.streamingManifest.baseline.packages.length} 份启动关卡已按原加载链识别；全部 ${viewer.manifest.levels.length} 份地图可单独检查。天空 HDR 已接入；当前为静态场景，部分路面材质与角色/事件逻辑待接入。`;
    }
    busy(false); document.body.dataset.ready = 'world'; document.body.dataset.level = region.value;
    const failures = viewer.failuresList;
    if (failures.length) {
      warning.hidden = false; warning.textContent = `${failures.length} 项资源未能加载，当前场景不完整。切换区域可重试。`;
      console.error('World resource failures', failures);
    }
    canvas.focus();
    const url = new URL(location.href); url.searchParams.set('region', region.value); history.replaceState(null, '', url);
  } catch (error) {
    busy(false); document.body.dataset.ready = 'error';
    warning.hidden = false; warning.textContent = error instanceof Error ? error.message : String(error); console.error(error);
  }
}
viewer.onProgress = (message, done, total) => {
  el('load-message').textContent = message;
  el<HTMLProgressElement>('progress').max = Math.max(total, 1); el<HTMLProgressElement>('progress').value = done;
};
viewer.onStreaming = event => {
  if (event.type === 'state') {
    canvas.dataset.streaming = JSON.stringify(event.snapshot);
    if (event.snapshot.phase === 'awaiting-save-state') {
      el('scope').textContent = '原 12 步城区加载链已执行；过渡关卡独立延时卸载。存档条件分支尚未初始化，角色与事件逻辑仍待恢复。';
    } else if (event.snapshot.phase === 'complete' && event.snapshot.overlay === 'complete') {
      el('scope').textContent = '已按原新存档条件执行 12 步城区加载及过渡关卡卸载。角色、剧情与任务仍待恢复；未使用或修改原游戏存档。';
    }
  } else if (event.type === 'request' || event.type === 'completed') {
    const trace = JSON.parse(canvas.dataset.streamingTrace || '[]') as unknown[];
    trace.push({type: event.type, operation: event.operation, level: event.request.levelName, branch: event.request.branch, time: performance.now()});
    canvas.dataset.streamingTrace = JSON.stringify(trace);
  }
};
viewer.onStats = stats => {
  el('object-count').textContent = stats.objects.toLocaleString('zh-CN');
  el('terrain-count').textContent = String(stats.terrain);
  el('fps').textContent = `${Math.round(stats.fps)} FPS`;
  el('position').textContent = stats.position.map(v => `${v.toFixed(0)} m`).join(' / ');
  canvas.dataset.objects = String(stats.objects); canvas.dataset.terrain = String(stats.terrain);
  canvas.dataset.failures = String(stats.failedAssets); canvas.dataset.textureFailures = String(stats.textureFailures);
  canvas.dataset.unresolvedMaterials = String(stats.unknownMaterials); canvas.dataset.ambiguousSlots = String(stats.ambiguousMaterials);
  canvas.dataset.fps = stats.fps.toFixed(1); canvas.dataset.draws = String(stats.draws);
  if (stats.textureFailures) { warning.hidden = false; warning.textContent = `${stats.textureFailures} 张纹理加载失败，当前材质不完整。`; }
  else if (stats.ambiguousMaterials) { warning.hidden = false; warning.textContent = `${stats.ambiguousMaterials} 处原骨骼模型材质槽尚有歧义，以灰色标出；当前是静态场景检查。`; }
};
region.onchange = () => void select();
el('overview').onclick = () => { viewer.frameRegion(); canvas.focus(); };
el('near').onclick = () => { viewer.frameRegion(true); canvas.focus(); };
el<HTMLInputElement>('speed').oninput = event => { const value = Number((event.target as HTMLInputElement).value); viewer.setSpeed(value); el('speed-value').textContent = `${value}×`; };
for (const [id, action] of [['quality', (active: boolean) => viewer.setQuality(active)], ['wireframe', (active: boolean) => viewer.setWireframe(active)]] as const) {
  el(id).onclick = async () => {
    const button = el<HTMLButtonElement>(id); const enabled = button.getAttribute('aria-pressed') !== 'true';
    button.disabled = true;
    if (id === 'quality') { busy(true); el('load-title').textContent = '切换地形精度'; }
    try { await action(enabled); button.setAttribute('aria-pressed', String(enabled)); }
    catch (error) { warning.hidden = false; warning.textContent = String(error); }
    finally { button.disabled = false; if (id === 'quality') busy(false); }
  };
}
window.addEventListener('pagehide', () => viewer.dispose(), { once: true });
try {
  await viewer.load();
  region.replaceChildren();
  const baseline = document.createElement('option'); baseline.value = '__baseline__'; baseline.textContent = '原版启动城市 · 静态恢复'; region.append(baseline);
  const startup = document.createElement('option'); startup.value = '__startup__'; startup.textContent = '原新存档加载顺序 · 执行检查'; region.append(startup);
  const regions = viewer.manifest.levels.filter(level => level.objects.length > 0);
  for (const scope of ['main-world', 'supplemental'] as const) {
    const group = document.createElement('optgroup'); group.label = scope === 'main-world' ? '原主世界区域' : '补充地图 · 运行入口尚未核实';
    for (const level of regions.filter(level => level.scope === scope)) {
      const option = document.createElement('option'); option.value = level.id;
      option.textContent = `${names[level.id] ?? level.id} · ${level.objects.reduce((n, object) => n + sourceObjectCount(object), 0).toLocaleString('zh-CN')} 对象`;
      group.append(option);
    }
    region.append(group);
  }
  const all = document.createElement('option'); all.value = '__all__'; all.textContent = '全部主世界区域 · 静态总览'; region.append(all);
  const requested = new URLSearchParams(location.search).get('region');
  region.value = requested && [...region.options].some(option => option.value === requested) ? requested : '__baseline__';
  el('scope').textContent = `${viewer.streamingManifest.baseline.packages.length} 份启动关卡已按原加载链识别；全部 ${viewer.manifest.levels.length} 份地图可单独检查。天空 HDR 已接入；当前仍是静态场景，部分路面材质与角色/事件逻辑待接入。`;
  await select();
} catch (error) {
  el('load-title').textContent = '原世界资源尚未就绪';
  el('load-message').textContent = error instanceof Error ? error.message : String(error);
  document.body.dataset.ready = 'error'; console.error(error);
}

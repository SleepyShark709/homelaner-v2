import './play.css';
import { Game } from './game/Game';
import type { FrameInfo } from './game/Game';

document.title = 'UNDEFEATED · 原版街区 / Web';
document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
  <canvas id="game" tabindex="0" aria-label="原版街区，WASD移动，拖动鼠标转动视角"></canvas>
  <header class="game-header"><a class="wordmark" href="/">UNDEFEATED<span>WEB RECONSTRUCTION</span></a><div class="district"><span class="live-dot"></span><span id="district-name">RESIDENTIAL DISTRICT</span><small>原版街区 · 自由破坏 02</small></div><div class="header-actions"><a href="/?view=assets">资产实验室 ↗</a><button id="rules" disabled>模式：自由破坏</button><button id="restore" disabled>重置街区</button><button id="quality">画质：流畅</button><button id="pause" disabled>暂停</button><button id="pointer" disabled>锁定鼠标</button></div></header>
  <section class="mission"><span class="overline">YOUR CITY. YOUR RULES.</span><h1>飞越城市，释放力量。</h1><p>原版角色与街区 · 新增自由破坏玩法</p></section>
  <div class="combat-status"><span id="combat-action">待命</span><b id="destruction-count">0 已破坏</b><p id="combat-message" role="status">自由模式：无伤害、无负分、无能力消耗</p></div><div class="crosshair" aria-hidden="true"><i></i><i></i></div>
  <aside class="telemetry"><span id="mode" class="mode">待命</span><div class="speed-line"><strong id="speed">00</strong><span>m/s <small>速度</small></span></div><div class="altitude"><span>离地高度</span><b id="altitude">0 m</b></div><div class="velocity-track"><i id="velocity-bar"></i></div><p id="boost-note">按住 SHIFT 加速</p></aside>
  <aside class="map-panel"><canvas id="minimap" width="180" height="180" aria-label="街区俯视图"></canvas><div><span>RECOVERED BLOCK</span><b id="fps">— FPS</b></div></aside>
  <footer class="game-footer"><div class="controls"><span><kbd>W A S D</kbd>移动</span><span><kbd>拖动鼠标</kbd>视角</span><span><kbd>F</kbd>飞行切换</span><span><kbd>SPACE</kbd>跳跃 / 上升</span><span><kbd>CTRL</kbd>下降</span><span><kbd>SHIFT</kbd>加速</span><span><kbd>左键 / J</kbd>近战</span><span><kbd>右键 / K</kbd>拳波</span><span><kbd>E 按住</kbd>热视线</span><span><kbd>SHIFT + K</kbd>强力拳波</span><span><kbd>R</kbd>回到起点</span></div><div class="build-note"><span>阶段 02 · 战斗与自由破坏</span><span>建筑暂不破坏；Boss、任务与祖国人外观尚未接入</span></div></footer>
  <section id="overlay" class="game-overlay" aria-label="加载与暂停菜单"><div class="start-panel"><span class="overline" id="overlay-kicker">BUILDING THE ORIGINAL WORLD</span><h2 id="overlay-title">恢复原版街区</h2><p id="load-message" role="status">读取地图与资源清单…</p><div id="load-track" class="load-track"><i></i></div><div id="start-actions" hidden><button id="start" class="primary">开始探索 <span>↗</span></button><button id="reset" class="secondary">回到起点</button></div><p class="scope-note">按住 E 从双眼发射热视线，左键近战，右键拳波。<br>自由模式可击倒路人、摧毁车辆与指定道具；建筑不破坏。</p></div></section>`;

const element = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const canvas = element<HTMLCanvasElement>('game');
const overlay = element('overlay');
const game = new Game(canvas);
const map = element<HTMLCanvasElement>('minimap').getContext('2d')!;
let mapBackground: ImageData | undefined;
let mapScale = 1, mapX = 0, mapZ = 0;
let messageUntil = 0;

function setupMap(): void {
  const bounds = game.world.manifest.bounds;
  mapScale = 156 / Math.max(bounds.max[0] - bounds.min[0], bounds.max[2] - bounds.min[2]);
  mapX = (bounds.max[0] + bounds.min[0]) / 2; mapZ = (bounds.max[2] + bounds.min[2]) / 2;
  map.fillStyle = '#14221ee0'; map.fillRect(0, 0, 180, 180);
  map.strokeStyle = '#30443b'; map.lineWidth = 0.5;
  for (let i = 18; i < 180; i += 24) { map.beginPath(); map.moveTo(i, 0); map.lineTo(i, 180); map.moveTo(0, i); map.lineTo(180, i); map.stroke(); }
  map.fillStyle = '#66766a';
  const groundIds = new Set(['district-ground-proxy', ...(game.world.manifest.collisionBoxes ?? []).map(box => box.id)]);
  for (const box of game.world.obstacles.filter(box => !groundIds.has(box.id))) {
    map.fillRect(90 - (box.max[0] - mapX) * mapScale, 90 - (box.max[2] - mapZ) * mapScale, (box.max[0] - box.min[0]) * mapScale, (box.max[2] - box.min[2]) * mapScale);
  }
  mapBackground = map.getImageData(0, 0, 180, 180);
}
function updateHUD(frame: FrameInfo): void {
  element('speed').textContent = Math.round(frame.speed).toString().padStart(2, '0');
  element('altitude').textContent = `${frame.altitude.toFixed(1)} m`;
  element('mode').textContent = frame.mode;
  element('fps').textContent = `${Math.round(frame.fps)} FPS`;
  element('velocity-bar').style.width = `${Math.min(100, frame.speed / 70 * 100)}%`;
  element('boost-note').textContent = frame.speed > 45 ? '高速飞行' : '按住 SHIFT 加速';
  canvas.dataset.position = frame.position.map(value => value.toFixed(3)).join(',');
  canvas.dataset.motion = game.motor.state;
  canvas.dataset.paused = String(frame.paused);
  canvas.dataset.renderMs = frame.renderMs.toFixed(2);
  canvas.dataset.action = game.combat.actionName;
  canvas.dataset.heat = String(game.combat.heatActive);
  canvas.dataset.hits = String(game.combat.hits);
  canvas.dataset.destroyed = String(game.combat.destroyed);
  canvas.dataset.targets = String(game.population.remaining);
  canvas.dataset.heatTarget = game.combat.heatTarget;
  element('combat-action').textContent = game.combat.actionName;
  element('destruction-count').textContent = `${game.combat.destroyed} 已破坏 / 击倒`;
  document.body.classList.toggle('heat-active', game.combat.heatActive);
  if (performance.now() > messageUntil) element('combat-message').textContent = game.combat.mode === 'free' ? '自由模式：无伤害、无负分、无能力消耗' : '基础交互：保护路人；强力攻击可毁车';
  if (mapBackground) {
    map.putImageData(mapBackground, 0, 0);
    for (const actor of game.population.actors.filter(actor => actor.alive)) {
      map.fillStyle = actor.kind === 'citizen' ? '#edcf81' : actor.kind === 'vehicle' ? '#79dcf2' : '#c9b4ee';
      map.beginPath(); map.arc(90 - (actor.position[0] - mapX) * mapScale, 90 - (actor.position[2] - mapZ) * mapScale, 2, 0, Math.PI * 2); map.fill();
    }
    map.save(); map.translate(90 - (frame.position[0] - mapX) * mapScale, 90 - (frame.position[2] - mapZ) * mapScale); map.rotate(-game.input.yaw);
    map.fillStyle = '#c0f577'; map.beginPath(); map.moveTo(0, -7); map.lineTo(-4.5, 5); map.lineTo(0, 2); map.lineTo(4.5, 5); map.closePath(); map.fill(); map.restore();
  }
}
function showMenu(): void {
  overlay.hidden = false;
  element('overlay-title').textContent = '稍作停留。';
  element('overlay-kicker').textContent = 'FLIGHT PAUSED';
  element('load-message').textContent = '移动已暂停，返回后继续探索原版街区。';
  element('start').innerHTML = '继续探索 <span>↗</span>';
  if (document.pointerLockElement) document.exitPointerLock();
}
game.onFrame = updateHUD;
game.onPause = showMenu;
element('start').onclick = () => { overlay.hidden = true; game.start(); canvas.focus(); };
element('pause').onclick = () => game.pause();
element('restore').onclick = () => { game.resetCity(); canvas.focus(); };
element('rules').onclick = () => {
  game.combat.mode = game.combat.mode === 'free' ? 'baseline' : 'free';
  game.resetCity();
  element('rules').textContent = game.combat.mode === 'free' ? '模式：自由破坏' : '模式：基础交互';
  canvas.focus();
};
element('reset').onclick = () => { game.reset(); overlay.hidden = true; game.start(); canvas.focus(); };
element('pointer').onclick = () => { void canvas.requestPointerLock()?.catch(() => { element('pointer').textContent = '可拖动视角'; }); };
let highQuality = false;
element('quality').onclick = () => { highQuality = !highQuality; game.setQuality(highQuality); element('quality').textContent = highQuality ? '画质：高清' : '画质：流畅'; };
window.addEventListener('pagehide', () => game.dispose(), { once: true });
try {
  await game.load(message => { element('load-message').textContent = message; });
  game.combat.onImpact = message => { element('combat-message').textContent = message; messageUntil = performance.now() + 1800; };
  setupMap();
  element('district-name').textContent = game.world.manifest.name ?? 'RESIDENTIAL DISTRICT';
  element('overlay-title').textContent = '准备好起飞。';
  element('load-message').textContent = `${game.world.manifest.objects.length} 个原版场景实例已就绪。按 F 飞行、E 热视线。路人和载具已进入街区。`;
  element('load-track').hidden = true;
  element('start-actions').hidden = false;
  element<HTMLButtonElement>('pause').disabled = element<HTMLButtonElement>('pointer').disabled = false;
  element<HTMLButtonElement>('rules').disabled = element<HTMLButtonElement>('restore').disabled = false;
  document.body.dataset.ready = 'city';
} catch (error) {
  element('overlay-title').textContent = '街区载入未完成';
  element('load-message').textContent = error instanceof Error ? error.message : String(error);
  element('load-track').hidden = true;
  document.body.dataset.error = 'load';
  console.error(error);
}

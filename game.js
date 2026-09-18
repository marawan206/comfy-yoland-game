/* Comfy Org: The Move. An 8-bit isometric story game. */
(() => {
'use strict';

// ---------------------------------------------------------------- audio (all synthesized, 8-bit style)
const Audio8 = {
  ctx: null, muted: false, music: null,
  init() {
    if (this.ctx) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AC();
    this.master = this.ctx.createGain(); this.master.gain.value = 0.35; this.master.connect(this.ctx.destination);
  },
  tone(freq, dur, type = 'square', vol = 0.5, slide = 0, when = 0) {
    if (!this.ctx || this.muted) return;
    const t = this.ctx.currentTime + when;
    const o = this.ctx.createOscillator(), g = this.ctx.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(20, freq + slide), t + dur);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(this.master); o.start(t); o.stop(t + dur + 0.02);
  },
  noise(dur, vol = 0.3) {
    if (!this.ctx || this.muted) return;
    const n = this.ctx.sampleRate * dur, buf = this.ctx.createBuffer(1, n, this.ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const s = this.ctx.createBufferSource(), g = this.ctx.createGain(); s.buffer = buf; g.gain.value = vol;
    s.connect(g); g.connect(this.master); s.start();
  },
  step() { this.tone(160 + Math.random() * 40, 0.06, 'square', 0.12, -60); },
  tick() { this.tone(1100, 0.03, 'square', 0.08); },
  confirm() { this.tone(660, 0.08, 'square', 0.3); this.tone(990, 0.12, 'square', 0.3, 0, 0.08); },
  door() { this.noise(0.25, 0.25); this.tone(120, 0.3, 'triangle', 0.4, -60); },
  knock() { for (let i = 0; i < 3; i++) { this.tone(90, 0.08, 'triangle', 0.6, -40, i * 0.18); } },
  jingle() { [523, 659, 784, 1047].forEach((f, i) => this.tone(f, 0.18, 'square', 0.3, 0, i * 0.11)); this.tone(1319, 0.5, 'square', 0.3, 0, 0.44); },
  found() { [880, 1175].forEach((f, i) => this.tone(f, 0.1, 'square', 0.25, 0, i * 0.09)); },
  // tiny sequencer: lead (square) + bass (triangle), scheduled ahead of time
  play(song) {
    this.stop(); if (!this.ctx) return;
    const bpm = song.bpm, beat = 60 / bpm / 2, m = { song, i: 0, next: this.ctx.currentTime + 0.1 };
    m.timer = setInterval(() => {
      while (m.next < this.ctx.currentTime + 0.3) {
        const n = song.lead[m.i % song.lead.length], b = song.bass[m.i % song.bass.length], when = m.next - this.ctx.currentTime;
        if (n) this.tone(n, beat * 0.9, 'square', 0.09, 0, when);
        if (b) this.tone(b, beat * 1.8, 'triangle', 0.22, 0, when);
        m.next += beat; m.i++;
      }
    }, 100);
    this.music = m;
  },
  stop() { if (this.music) { clearInterval(this.music.timer); this.music = null; } },
};
const N = (s) => { const t = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }; const m = s.match(/([A-G])(#?)(\d)/); if (!m) return 0; const semi = t[m[1]] + (m[2] ? 1 : 0) + (+m[3] - 4) * 12; return 440 * Math.pow(2, (semi - 9) / 12); };
const seq = (str) => str.split(' ').map(s => s === '.' ? 0 : N(s));
const SONGS = {
  old: { bpm: 132,
    lead: seq('E5 . G5 . A5 . G5 E5 D5 . E5 . C5 . . . E5 . G5 . A5 . C6 B5 A5 . G5 . E5 . . . D5 . E5 . G5 . E5 D5 C5 . D5 . E5 . . . G5 . A5 . B5 . A5 G5 E5 . D5 . C5 . . .'),
    bass: seq('C3 . . . C3 . . . A2 . . . A2 . . . F2 . . . F2 . . . G2 . . . G2 . . . C3 . . . C3 . . . A2 . . . A2 . . . F2 . . . G2 . . . C3 . . . C3 . . .') },
  new: { bpm: 150,
    lead: seq('C5 E5 G5 . C6 . G5 . A5 . C6 . E6 . D6 . B5 . D6 . G5 . B5 . C6 . . . . . . . E5 G5 B5 . E6 . B5 . A5 . C6 . E6 . D6 . G5 B5 D6 . F6 . E6 . C6 . . . . . . .'),
    bass: seq('C3 . C3 . G2 . G2 . A2 . A2 . E2 . E2 . F2 . F2 . C3 . C3 . G2 . G2 . G2 . . . C3 . C3 . E2 . E2 . A2 . A2 . E2 . E2 . F2 . F2 . G2 . G2 . C3 . . .') },
};

// ---------------------------------------------------------------- script
const Y = 'YOLAND', D = 'DEEP', NA = 'NARRATOR';
const L = (who, text, sfx) => ({ who, text, sfx: sfx || null });
const SCRIPT = {
  old: {
    title: 'The Victorian house', objective: (n, t) => n < t ? `Say goodbye: ${n}/${t} memories` : 'Leave through the front door',
    intro: [
      L(NA, 'San Francisco. The lavender Victorian house on the hill.\nComfyâ€™s first office.'),
      L(NA, 'It is moving day.'),
      L(Y, 'Okay. Last walk-through before we hand back the keys.'),
      L(Y, 'Letâ€™s say goodbye properly.\n(Find the 4 memories, then leave through the front door.)'),
    ],
    hotspots: [
      { id: 'desk', asset: 'desk_white_ultrawide_2x1', label: 'The corner desk', memory: true, lines: [
        L(Y, 'The corner desk. Where the first ComfyUI nodes got wired up on an ultrawide that barely fit.'),
        L(Y, 'One monitor, three energy drinks, and a Discord that would not stop pinging.'),
        L(Y, 'Noodles connected. Never disconnected.') ] },
      { id: 'board', asset: 'whiteboard_rolling_2x1', label: 'The whiteboard', memory: true, lines: [
        L(Y, 'The roadmap whiteboard. Half of it is a flowchart. The other half is a drawing of a duck.'),
        L(Y, 'Both shipped.') ] },
      { id: 'duck', asset: 'plush_duck_yellow_hat_1x1', label: 'The duck', memory: true, lines: [
        L(Y, 'The rubber duck with the beanie. Chief Debugging Officer.'),
        L(Y, 'Every workflow that ever broke was explained to this duck first.'),
        L(Y, 'Itâ€™s coming with us. Non-negotiable.') ] },
      { id: 'table', asset: 'dining_table_black_chairs_3x2', label: 'The kitchen table', memory: true, lines: [
        L(Y, 'The kitchen table. Standups, lunches, three all-nighters, and one very serious debate about whether a tab counts as a node.'),
        L(Y, 'Team eats together, team ships together.') ] },
      { id: 'yard', asset: 'backyard_tree_2x2', label: 'The backyard', lines: [
        L(Y, 'The gravel yard. Where we took calls whenever the office Wi-Fi was more of a suggestion.') ] },
      { id: 'door', cells: [[10, 0], [11, 0], [10, 1], [11, 1]], label: 'Front door', exit: true, lines: [
        L(Y, 'The front door. The one that locked Deep, Jedrzej and Purz outside the night they went out for booze.'),
        L(Y, 'Deep tried opening it. Then tried again. Then tried a few more times, with feeling.', 'knock'),
        L(Y, 'Then all three of them tried the window. The window won.'),
        L(Y, 'And then, for no reason anyone has ever explained, the garage door opened.', 'door'),
        L(Y, 'Nobody asks how. We just say thank you to the garage.') ],
        notYet: [L(Y, 'I still have a few things to say goodbye to before we go.')],
        finale: [
          L(Y, 'That’s everything. Boxes are in the van. Duck is in my backpack.'),
          L(Y, 'Goodbye, Victorian. You were a weird office and a great home.'),
          L(D, 'Garage door’s open, by the way. Still don’t know why.'),
          L(Y, 'Don’t question it. Let’s go.') ] },
    ],
  },
  new: {
    title: '201 Spear St, STE 1700', objective: (n, t, done) => done.has('doors') ? `Explore the floor: ${n}/${t}  â€¢  Find your desk` : 'Check in at the oak doors',
    intro: [
      L(NA, '201 Spear Street, Suite 1700.\nSeventeen floors above the Embarcadero.'),
      L(Y, 'Oak doors. Glass walls. A view of the Bay Bridge.'),
      L(Y, 'And badge readers on every door.'),
      L(Y, 'Letâ€™s look around. My desk is somewhere in the open area.'),
    ],
    hotspots: [
      { id: 'doors', cells: [[0, 8], [0, 9], [1, 8], [1, 9]], label: 'The oak doors', lines: [
        L(D, 'Yoland! Have you SEEN this? Key cards. Badge readers. A front desk with an actual human.'),
        L(D, 'Nobody is getting locked out of this one. Not me. Not Jedrzej. Not Purz.'),
        L(Y, 'Even on a booze run?'),
        L(D, 'ESPECIALLY on a booze run. The badge goes in the pocket. The pocket comes with me.'),
        L(Y, 'And if the badge stays in the old office?'),
        L(D, '...'),
        L(D, 'Then I would like to formally request that this building also have a garage door.', 'confirm') ] },
      { id: 'portrait', asset: 'portrait_painting_decal', cells: [[3, 7], [4, 7], [5, 7]], label: 'The portrait', lines: [
        L(Y, 'A portrait of a stern man in a suit. He came with the office.'),
        L(Y, 'Nobody knows who he is. The team has named him Legacy Node.'),
        L(Y, 'He is deprecated, but we cannot remove him.') ] },
      { id: 'boxes', asset: 'moving_boxes_stack_1x1', label: 'Moving boxes', lines: [
        L(Y, 'The last moving boxes. Cables, a keyboard, and... the duck.'),
        L(Y, 'Chief Debugging Officer, reporting for duty on floor 17.', 'found') ] },
      { id: 'foosball', asset: 'foosball_table_2x1', label: 'Foosball', lines: [
        L(Y, 'Foosball table. Winner reviews the PR, loser writes the tests.'),
        L(Y, 'The tests always get written.') ] },
      { id: 'meeting', asset: 'conference_table_5x2', label: 'The glass meeting room', lines: [
        L(Y, 'The glass meeting room. Every call is now on a wall the size of a bus.'),
        L(Y, 'The old office had a TV balanced on top of the fridge. Weâ€™ve come a long way.') ] },
      { id: 'kitchen', asset: 'kitchen_island_curved_3x1', label: 'The kitchen', lines: [
        L(Y, 'A real kitchen. A fridge that closes. A microwave that doesnâ€™t trip the breaker.'),
        L(Y, 'Someone already taped a PLEASE LABEL YOUR OAT MILK note to it. We are a real company now.') ] },
      { id: 'sofa', asset: 'sofa_grey_3x1', label: 'The lounge', lines: [
        L(Y, 'The lounge. Sofa, skyline, and the quietest corner on the floor for reading Discord bug reports.') ] },
      { id: 'desk', asset: 'desk_sitstand_dual_monitor_2x1', label: 'Yolandâ€™s desk', final: true, lines: [
        L(Y, 'My desk. Two monitors, a sit-stand, a view of the bay.'),
        L(Y, 'Same job as in the Victorian: make ComfyUI the best place to build with generative AI.'),
        L(Y, 'Just with more floors. And a door that locks the right way.'),
        L(D, '*from the doorway* Badge works. Door opens. Just testing. Every day. Forever.'),
        L(Y, 'Good.'),
        L(NA, 'Comfy Org. 201 Spear Street, Suite 1700, San Francisco.'),
        L(NA, 'New office. Same team. Same duck.', 'jingle') ],
        notYet: [L(Y, 'I should check in at the oak doors first. Deep is waving at me.')] },
    ],
  },
};

// ---------------------------------------------------------------- engine
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const $ = (id) => document.getElementById(id);
const HU = 70, HERO_H = 1.65 * HU;
const keys = {};
let state = 'title', level = null, player = null, cam = { x: 0, y: 0 }, zoom = 0.8, tPrev = 0;
let dlg = null; // { lines, i, shown, done, cb }
const done = new Set();
let levelKey = 'old';

const loadImg = (src) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; });
async function loadLevel(key) {
  const data = await (await fetch(`levels/${key}/level.json`)).json();
  const [floor, atlas] = await Promise.all([loadImg(`levels/${key}/floor.jpg`), loadImg(`levels/${key}/atlas.png`)]);
  data.floorImg = floor; data.atlasImg = atlas;
  data.items.sort((a, b) => a.d - b.d);
  data.propsByAsset = {};
  for (const p of data.props) (data.propsByAsset[p.asset] = data.propsByAsset[p.asset] || []).push(p);
  data.hotspots = SCRIPT[key].hotspots.map(h => {
    const cells = h.cells ? h.cells.slice() : [];
    if (h.asset && !h.cells) for (const p of data.propsByAsset[h.asset] || []) for (let dx = 0; dx < p.footprint[0]; dx++) for (let dy = 0; dy < Math.max(1, p.footprint[1]); dy++) cells.push([p.cell[0] + dx, p.cell[1] + dy]);
    const cx = cells.reduce((s, c) => s + c[0], 0) / cells.length + 0.5, cy = cells.reduce((s, c) => s + c[1], 0) / cells.length + 0.5;
    return { ...h, cells, cx, cy };
  });
  return data;
}
let hero, ANIM;

const TW = 128, TH = 64;
const sx = (c, r) => (c - r) * TW / 2 + level.origin[0];
const sy = (c, r) => (c + r) * TH / 2 + level.origin[1];

function passable(c, r, dc, dr) {
  const [gc, gr] = level.grid, nc = c + dc, nr = r + dr;
  if (nc < 0 || nr < 0 || nc >= gc || nr >= gr) return false;
  if (!level.walk[nr][nc]) return false;
  const b = level.block[r][c];
  if (dc === 1 && (b & 8)) return false; if (dc === -1 && (b & 4)) return false;
  if (dr === 1 && (b & 2)) return false; if (dr === -1 && (b & 1)) return false;
  return true;
}
function tryMove(dc, dr) {
  const { c, r } = player;
  if (dc && dr) {
    if ((passable(c, r, dc, 0) && passable(c + dc, r, 0, dr)) || (passable(c, r, 0, dr) && passable(c, r + dr, dc, 0))) return startMove(dc, dr);
    if (passable(c, r, dc, 0)) return startMove(dc, 0);
    if (passable(c, r, 0, dr)) return startMove(0, dr);
    return false;
  }
  if (passable(c, r, dc, dr)) return startMove(dc, dr);
  return false;
}
function startMove(dc, dr) {
  player.fc = player.c; player.fr = player.r; player.c += dc; player.r += dr; player.t = 0; player.moving = true;
  // pick a walk cycle from the screen direction. Sheet facing: front row faces slightly left,
  // profile row faces LEFT, back row faces slightly right. flip=true mirrors to face right.
  if (dc && dr) { if (dc > 0 && dr > 0) player.dir = 'south', player.flip = false; else if (dc < 0 && dr < 0) player.dir = 'north', player.flip = false; else if (dc > 0) player.dir = 'east', player.flip = true; else player.dir = 'east', player.flip = false; }
  else if (dr > 0) { player.dir = 'south'; player.flip = false; }       // down-left
  else if (dr < 0) { player.dir = 'north'; player.flip = false; }      // up-right
  else if (dc > 0) { player.dir = 'east'; player.flip = true; }        // down-right
  else { player.dir = 'east'; player.flip = false; }                   // up-left
  Audio8.step(); return true;
}

function nearHotspot() {
  if (!level) return null;
  for (const h of level.hotspots) for (const [c, r] of h.cells) if (Math.abs(c - player.c) <= 1 && Math.abs(r - player.r) <= 1) return h;
  return null;
}

// dialogue
const dlgEl = $('dlg'), dname = $('dname'), dtext = $('dtext');
function say(lines, cb) {
  dlg = { lines, i: 0, shown: 0, acc: 0, cb }; state = 'dialogue'; dlgEl.style.display = 'block'; showLine();
}
function showLine() {
  const l = dlg.lines[dlg.i]; dlg.shown = 0; dlg.acc = 0;
  dname.textContent = l.who; dname.className = 'name ' + (l.who === D ? 'deep' : l.who === NA ? 'narr' : '');
  dtext.textContent = '';
  if (l.text === undefined) return;
  const sfx = dlg.lines[dlg.i].sfx; if (sfx && Audio8[sfx]) Audio8[sfx]();
}
function advance() {
  const l = dlg.lines[dlg.i];
  if (dlg.shown < l.text.length) { dlg.shown = l.text.length; dtext.textContent = l.text; return; }
  dlg.i++;
  if (dlg.i >= dlg.lines.length) { dlgEl.style.display = 'none'; const cb = dlg.cb; dlg = null; state = 'play'; if (cb) cb(); }
  else showLine();
}
function updateDialogue(dt) {
  const l = dlg.lines[dlg.i]; if (dlg.shown >= l.text.length) return;
  dlg.acc += dt * 38; const n = Math.min(l.text.length, Math.floor(dlg.acc));
  if (n > dlg.shown) { if ((n >> 1) !== (dlg.shown >> 1) && l.text[n - 1] !== ' ') Audio8.tick(); dlg.shown = n; dtext.textContent = l.text.slice(0, n); }
}
function interact() {
  const h = nearHotspot(); if (!h) return;
  const sc = SCRIPT[levelKey];
  const memories = level.hotspots.filter(x => x.memory), memDone = memories.filter(x => done.has(x.id)).length;
  if (h.exit) {
    if (!done.has(h.id)) { say(h.lines, () => { done.add(h.id); if (memDone < memories.length) say(h.notYet); }); return; }
    if (memDone < memories.length) { say(h.notYet); return; }
    say(h.finale, () => transition()); return;
  }
  if (h.final) {
    if (!done.has('doors')) { say(h.notYet); return; }
    say(h.lines, () => ending()); return;
  }
  const first = !done.has(h.id);
  say(h.lines, () => { if (first) { done.add(h.id); Audio8.found(); } updateHud(); });
}

function updateHud() {
  const sc = SCRIPT[levelKey];
  const tracked = level.hotspots.filter(h => levelKey === 'old' ? h.memory : !h.final);
  const n = tracked.filter(h => done.has(h.id)).length;
  $('lvl').textContent = sc.title;
  $('obj').textContent = sc.objective(n, tracked.length, done);
}

// ---------------------------------------------------------------- flow
const overlay = $('overlay'), fade = $('fade');
async function startLevel(key) {
  levelKey = key; done.clear();
  level = await loadLevel(key);
  player = { c: level.player_start[0], r: level.player_start[1], fc: 0, fr: 0, t: 0, moving: false, flip: false, bob: 0, dir: 'south', anim: 0 };
  cam.x = sx(player.c, player.r); cam.y = sy(player.c, player.r);
  $('hud').classList.remove('hidden'); $('hint').classList.remove('hidden'); overlay.classList.add('hidden');
  updateHud();
  fade.style.opacity = 0;
  Audio8.play(SONGS[key]);
  state = 'play';
  say(SCRIPT[key].intro);
}
function transition() {
  state = 'wait'; fade.style.opacity = 1; Audio8.stop(); Audio8.door();
  setTimeout(() => {
    overlay.innerHTML = `<h1>SOME WEEKS LATER...</h1><p>201 Spear Street, Suite 1700<br>San Francisco, CA<br><br>Seventeen floors up.<br>Glass walls. A front desk. Actual security.</p><div class="press">PRESS ENTER / TAP TO CONTINUE</div>`;
    overlay.classList.remove('hidden'); $('hud').classList.add('hidden'); fade.style.opacity = 0; state = 'transition';
  }, 700);
}
function ending() {
  state = 'wait'; fade.style.opacity = 1; Audio8.stop();
  setTimeout(() => {
    overlay.innerHTML = `<h1>THE END</h1><img src="levels/title.png" alt=""><p>Comfy Org moved from the lavender Victorian house<br>to 201 Spear Street, Suite 1700, San Francisco.<br><br>Starring Yoland.<br>Featuring Deep, Jedrzej and Purz, who are now inside.<br>And the duck.<br><br>Pixel art made with ComfyUI. Made for the Comfy hackathon.</p><div class="press">PRESS ENTER / TAP TO PLAY AGAIN</div>`;
    overlay.classList.remove('hidden'); $('hud').classList.add('hidden'); fade.style.opacity = 0; state = 'end';
  }, 900);
}
function primary() {
  Audio8.init(); if (Audio8.ctx.state === 'suspended') Audio8.ctx.resume();
  if (state === 'title') { Audio8.confirm(); startLevel('old'); }
  else if (state === 'transition') { Audio8.confirm(); startLevel('new'); }
  else if (state === 'end') { location.reload(); }
  else if (state === 'dialogue') advance();
  else if (state === 'play') interact();
}

// ---------------------------------------------------------------- input
window.addEventListener('keydown', (e) => {
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) e.preventDefault();
  if (e.repeat) return;
  keys[e.key.toLowerCase()] = true;
  if (e.key === 'Enter' || e.key === ' ' || e.key.toLowerCase() === 'e') primary();
  if (e.key.toLowerCase() === 'm') { Audio8.muted = !Audio8.muted; if (Audio8.muted) Audio8.stop(); else if (level) Audio8.play(SONGS[levelKey]); }
});
window.addEventListener('keyup', (e) => { keys[e.key.toLowerCase()] = false; });
overlay.addEventListener('click', primary);
dlgEl.addEventListener('click', primary);
$('act').addEventListener('click', primary);
if ('ontouchstart' in window) document.body.classList.add('touch');
for (const b of document.querySelectorAll('#pad button')) {
  const k = b.dataset.k.toLowerCase();
  const on = (e) => { e.preventDefault(); keys[k] = true; }, off = (e) => { e.preventDefault(); keys[k] = false; };
  b.addEventListener('touchstart', on); b.addEventListener('touchend', off); b.addEventListener('touchcancel', off);
  b.addEventListener('mousedown', on); b.addEventListener('mouseup', off); b.addEventListener('mouseleave', off);
}
function resize() { cv.width = innerWidth; cv.height = innerHeight; zoom = Math.min(0.9, Math.max(0.45, innerWidth / 1500)); if (innerWidth < 700) zoom = 0.55; }
window.addEventListener('resize', resize); resize();

// ---------------------------------------------------------------- loop
function update(dt) {
  if (!level) return;
  if (state === 'dialogue') updateDialogue(dt);
  if (player.moving) {
    player.t += dt * 4.2;
    if (player.t >= 1) { player.t = 0; player.moving = false; }
  }
  if (!player.moving && state === 'play') {
    const dc = (keys['arrowright'] || keys['d'] ? 1 : 0) - (keys['arrowleft'] || keys['a'] ? 1 : 0);
    const dr = (keys['arrowdown'] || keys['s'] ? 1 : 0) - (keys['arrowup'] || keys['w'] ? 1 : 0);
    if (dc || dr) tryMove(dc, dr);
  }
  const pc = player.moving ? player.fc + (player.c - player.fc) * player.t : player.c;
  const pr = player.moving ? player.fr + (player.r - player.fr) * player.t : player.r;
  player.px = sx(pc, pr); player.py = sy(pc, pr) + TH / 2; player.depth = pc + pr + 1.05;
  player.bob += dt * (player.moving ? 16 : 2); if (player.moving) player.anim += dt * 14;
  const k = 1 - Math.pow(0.001, dt);
  cam.x += (player.px - cam.x) * k; cam.y += (player.py - 60 - cam.y) * k;
}
function draw(t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#ece8e0'; ctx.fillRect(0, 0, cv.width, cv.height);
  if (!level) return;
  ctx.setTransform(zoom, 0, 0, zoom, cv.width / 2 - cam.x * zoom, cv.height / 2 - cam.y * zoom);
  ctx.imageSmoothingEnabled = true;
  const vx0 = cam.x - cv.width / 2 / zoom, vy0 = cam.y - cv.height / 2 / zoom, vx1 = vx0 + cv.width / zoom, vy1 = vy0 + cv.height / zoom;
  ctx.drawImage(level.floorImg, 0, 0);
  // shadow
  ctx.fillStyle = 'rgba(0,0,0,.25)'; ctx.beginPath(); ctx.ellipse(player.px, player.py - 2, 26, 12, 0, 0, Math.PI * 2); ctx.fill();
  let drawnPlayer = false;
  const A = level.atlasImg;
  for (const it of level.items) {
    if (!drawnPlayer && it.d > player.depth) { drawPlayer(t); drawnPlayer = true; }
    if (it.x + it.w < vx0 || it.x > vx1 || it.y + it.h < vy0 || it.y > vy1) continue;
    ctx.drawImage(A, it.ax, it.ay, it.w, it.h, it.x, it.y, it.w, it.h);
  }
  if (!drawnPlayer) drawPlayer(t);
  // hotspot markers
  const near = state === 'play' ? nearHotspot() : null;
  ctx.font = 'bold 30px "Press Start 2P", monospace'; ctx.textAlign = 'center';
  for (const h of level.hotspots) {
    if (h.final && !done.has('doors')) continue;
    const mx = sx(h.cx, h.cy), my = sy(h.cx, h.cy) - 120 + Math.sin(t / 220) * 6;
    const seen = done.has(h.id) && !(h.exit || h.final);
    if (seen && h !== near) continue;
    ctx.fillStyle = '#000'; ctx.fillText(h === near ? 'E' : '!', mx + 3, my + 3);
    ctx.fillStyle = h === near ? '#7cf5ff' : h.final ? '#9dff7c' : '#ffd23f'; ctx.fillText(h === near ? 'E' : '!', mx, my);
    if (h === near) { ctx.font = '13px "Press Start 2P", monospace'; ctx.fillStyle = '#000'; ctx.fillText(h.label, mx + 2, my + 22); ctx.fillStyle = '#fff'; ctx.fillText(h.label, mx, my + 20); ctx.font = 'bold 30px "Press Start 2P", monospace'; }
  }
}
function drawPlayer(t) {
  let frames, flip = player.flip;
  if (player.moving) frames = ANIM[player.dir];
  else if (player.dir === 'south') { frames = ANIM.idle; flip = false; }
  else frames = ANIM[player.dir + '_idle'];
  const idx = player.moving ? Math.floor(player.anim) % frames.length : Math.floor(t / 260) % frames.length;
  const f = frames[idx], k = HERO_H / 100, w = f.w * k, h = f.h * k;
  ctx.save(); ctx.translate(player.px, player.py + 8);
  if (flip) ctx.scale(-1, 1);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(hero, f.x, f.y, f.w, f.h, -w / 2, -h - f.b * k, w, h);
  ctx.restore();
}
function frame(t) {
  const dt = Math.min(0.05, (t - tPrev) / 1000 || 0); tPrev = t;
  update(dt); draw(t); requestAnimationFrame(frame);
}

window.__game = { startLevel, keys, tryMove, passable, get state() { return state; }, get player() { return player; }, done };
Promise.all([loadImg('levels/yoland_sheet.png'), fetch('levels/yoland.json').then(r => r.json())]).then(([i, a]) => { hero = i; ANIM = a; requestAnimationFrame(frame); });
})();

// =====================================================================
// 공통 게임 엔진
// 모든 스테이지가 이 코드 하나를 같이 쓴다. 스테이지마다 다른 점은
// 전부 stages.js 데이터에서 읽어 온다.
// =====================================================================

const PLAYER_MOVE_MS = 130;    // 플레이어가 한 칸 움직이는 데 걸리는 시간
const GRACE_MS = 1200;         // 시작하자마자 잡히지 않게 적이 잠깐 기다리는 시간
const CORGI_PENALTY_MS = 5000; // 코기블린에게 물리면 줄어드는 시간
const CORGI_REST_MS = 1500;    // 물고 난 뒤 코기블린이 쉬는 시간 (연속으로 물지 않게)
const HECK_HASTE_MS = 2500;    // 해피가 소리치면 WKB가 빨라지는 시간
const RAGE_FACTOR = 0.88;      // rage 기믹: 열쇠 하나마다 WKB 이동 간격에 곱하는 값
const DEFAULT_HAPPY = { moveMs: 800, shoutEveryMs: 8000, pauseMs: 0 };
const SAVE_KEY = '4am-escape-progress';

const renderer = createRenderer(document.getElementById('board'));
const input = createInput();
const el = id => document.getElementById(id);

let state = null;       // 지금 하고 있는 판의 모든 정보 (메뉴에선 null)
let progress = loadProgress();

// ---------------------------------------------------------------------
// 저장 (localStorage) — 망가졌거나 막혀 있어도 게임은 돌아가게
// ---------------------------------------------------------------------
function loadProgress() {
  const fresh = { unlockedStage: 1, bestStage: 0 };
  try {
    const data = JSON.parse(localStorage.getItem(SAVE_KEY));
    const unlocked = Number(data && data.unlockedStage);
    const best = Number(data && data.bestStage);
    if (!Number.isInteger(unlocked) || unlocked < 1 || unlocked > STAGES.length) return fresh;
    return {
      unlockedStage: unlocked,
      bestStage: Number.isInteger(best) && best >= 0 && best <= STAGES.length ? best : 0
    };
  } catch (e) {
    return fresh;
  }
}

function saveProgress() {
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(progress)); } catch (e) { /* 저장 못 해도 계속 플레이 */ }
}

// ---------------------------------------------------------------------
// 스테이지 시작 / 재시작
// ---------------------------------------------------------------------
function loadStage(stageId) {
  const stage = STAGES.find(s => s.id === stageId);
  if (!stage) return showEnding(); // 없는 스테이지는 불러오지 않는다

  showScreen('game'); // 화면이 보여야 게임판 크기를 잴 수 있다
  const portrait = isPortraitView();
  const level = parseStage(portrait ? { ...stage, map: transposeMap(stage.map) } : stage);
  const at = p => ({ x: p.x, y: p.y, rx: p.x, ry: p.y });
  const happyCfg = { ...DEFAULT_HAPPY, ...(stage.happy || {}) };

  // 이전 판의 값은 하나도 재사용하지 않고 state를 통째로 새로 만든다 → 재시작해도 깨끗
  state = {
    stage, level,
    portrait,           // true면 맵을 세로형으로 뒤집어서 쓰는 중
    status: 'playing',  // playing | paused | won | lost
    theme: CHAPTERS[stage.chapter].theme,
    player: at(level.player),
    enemies: [
      { type: 'wkb', ...at(level.wkb), moveMs: stage.enemyMoveMs, timer: GRACE_MS },
      ...level.corgis.map(c => ({ type: 'corgi', ...at(c), moveMs: stage.corgiMoveMs || 450, timer: GRACE_MS, dir: null, restMs: 0 })),
      ...level.happys.map(h => ({ type: 'happy', ...at(h), cfg: happyCfg, moveMs: happyCfg.moveMs, timer: GRACE_MS, shoutTimer: happyCfg.shoutEveryMs, shoutMs: 0, pauseMs: 0 }))
    ],
    keys: level.keys.map(k => ({ ...k, collected: false })),
    collectedKeys: 0,
    requiredKeys: stage.keyCount,
    exit: level.exit,
    exitOpen: stage.keyCount === 0,
    remainingMs: stage.timeLimit * 1000,
    moveCooldown: 0,
    hasteMs: 0,   // > 0 이면 WKB 흥분(빨라짐)
    hurtMs: 0,    // > 0 이면 플레이어 깜빡임
    toastMs: 0
  };

  input.clear();
  closeModal();
  document.body.dataset.chapter = stage.chapter;
  el('hud-stage').textContent = `Stage ${stage.id} · ${stage.name}`;
  el('hud-chapter').textContent = `챕터 ${stage.chapter}. ${CHAPTERS[stage.chapter].name}`;
  if (level.happys.length && stage.id === firstHappyStageId()) toast('Heck💕Heck💕Heeeeeck!!🔥🐶💕 해피 등장!', 2500);
  else toast(`Stage ${stage.id} — ${stage.name}`, 1500);
  updateHud();
}

// 게임판 자리가 세로로 더 길면 세로형 화면 (휴대폰 세로 등)
function isPortraitView() {
  const b = el('board');
  return b.clientHeight > b.clientWidth;
}

// 게임 도중 화면 방향이 바뀌면(휴대폰 회전, 창 크기 변경) 지금 판을 그대로 대각선으로 뒤집는다
function transposeState() {
  const swap = o => {
    [o.x, o.y] = [o.y, o.x];
    if ('rx' in o) [o.rx, o.ry] = [o.ry, o.rx];
  };
  swap(state.player);
  state.enemies.forEach(e => {
    swap(e);
    if (e.dir) e.dir = { x: e.dir.y, y: e.dir.x };
  });
  state.keys.forEach(swap);
  state.exit = { x: state.exit.y, y: state.exit.x };
  const lv = state.level;
  state.level = {
    ...lv,
    width: lv.height,
    height: lv.width,
    walls: Array.from({ length: lv.width }, (_, y) => Array.from({ length: lv.height }, (_, x) => lv.walls[x][y]))
  };
  state.portrait = !state.portrait;
}

function firstHappyStageId() {
  const s = STAGES.find(st => st.map.some(row => row.includes('H')));
  return s ? s.id : -1;
}

// ---------------------------------------------------------------------
// 길찾기 도우미
// ---------------------------------------------------------------------
function isWall(x, y) {
  const lv = state.level;
  return x < 0 || y < 0 || x >= lv.width || y >= lv.height || lv.walls[y][x];
}
const enemyAt = (type, x, y) => state.enemies.find(e => e.type === type && e.x === x && e.y === y);
const anyEnemyAt = (x, y) => state.enemies.some(e => e.x === x && e.y === y);
const isPlayerAt = (x, y) => state.player.x === x && state.player.y === y;

// 벽을 피해서 from → to 로 가는 "첫 한 걸음"을 BFS로 찾는다
function nextStepToward(from, to) {
  const key = (x, y) => y * state.level.width + x;
  const prev = new Map([[key(from.x, from.y), null]]);
  const queue = [{ x: from.x, y: from.y }];
  while (queue.length) {
    const cur = queue.shift();
    if (cur.x === to.x && cur.y === to.y) {
      // 목표에서 거꾸로 따라가서 출발점 바로 다음 칸을 찾는다
      let step = cur;
      let p = prev.get(key(step.x, step.y));
      while (p && !(p.x === from.x && p.y === from.y)) {
        step = p;
        p = prev.get(key(step.x, step.y));
      }
      return p ? step : null; // p가 없으면 이미 같은 칸
    }
    for (const d of Object.values(DIRS)) {
      const nx = cur.x + d.x, ny = cur.y + d.y;
      if (isWall(nx, ny) || prev.has(key(nx, ny))) continue;
      prev.set(key(nx, ny), cur);
      queue.push({ x: nx, y: ny });
    }
  }
  return null; // 갈 수 있는 길이 없음 → 제자리
}

function openDirs(x, y, extraBlocked) {
  return Object.values(DIRS).filter(d => {
    const nx = x + d.x, ny = y + d.y;
    return !isWall(nx, ny) && !(extraBlocked && extraBlocked(nx, ny));
  });
}

// ---------------------------------------------------------------------
// 매 프레임 상태 업데이트 (dt = 지난 프레임부터 흐른 실제 시간, ms)
// ---------------------------------------------------------------------
function update(dt) {
  if (!state || state.status !== 'playing') return; // 멈췄거나 끝났으면 아무것도 안 움직임

  // 1) 시간
  state.remainingMs -= dt;
  state.hasteMs = Math.max(0, state.hasteMs - dt);
  state.hurtMs = Math.max(0, state.hurtMs - dt);
  if (state.toastMs > 0) {
    state.toastMs -= dt;
    if (state.toastMs <= 0) el('toast').hidden = true;
  }
  if (state.remainingMs <= 0) {
    state.remainingMs = 0;
    return lose('시간 초과! 새벽 4시가 끝나 버렸다...');
  }

  // 2) 플레이어 이동 (한 틱에 최대 한 칸, 벽과 해피는 못 지나감)
  state.moveCooldown = Math.max(0, state.moveCooldown - dt);
  if (state.moveCooldown === 0) {
    const dir = input.takeDirection();
    if (dir) {
      const nx = state.player.x + dir.x, ny = state.player.y + dir.y;
      if (!isWall(nx, ny) && !enemyAt('happy', nx, ny)) {
        state.player.x = nx;
        state.player.y = ny;
        state.moveCooldown = PLAYER_MOVE_MS;
        if (afterPlayerMove()) return; // 승부가 났으면 이번 프레임은 여기서 끝
      }
    }
  }

  // 3) 적 이동
  for (const e of state.enemies) {
    if (e.type === 'wkb' && updateWkb(e, dt)) return;
    if (e.type === 'corgi') updateCorgi(e, dt);
    if (e.type === 'happy') updateHappy(e, dt);
  }
}

// WKB: BFS로 플레이어를 쫓는다. 잡으면 true
function updateWkb(e, dt) {
  e.timer -= dt;
  if (e.timer > 0) return false;
  e.timer += state.hasteMs > 0 ? e.moveMs * 0.6 : e.moveMs;
  const step = nextStepToward(e, state.player);
  if (step && !enemyAt('happy', step.x, step.y)) { e.x = step.x; e.y = step.y; } // 해피가 막고 있으면 기다림
  if (isPlayerAt(e.x, e.y)) {
    lose('WKB에게 붙잡혔다! 💍');
    return true;
  }
  return false;
}

// 코기블린: 앞으로 가다가 갈림길에서 가끔 방향을 바꾸며 순찰
function updateCorgi(c, dt) {
  if (c.restMs > 0) { c.restMs -= dt; return; }
  c.timer -= dt;
  if (c.timer > 0) return;
  c.timer += c.moveMs;
  const open = openDirs(c.x, c.y, (x, y) => enemyAt('happy', x, y) || enemyAt('wkb', x, y));
  if (!open.length) return;
  const notBack = open.filter(d => !c.dir || d.x !== -c.dir.x || d.y !== -c.dir.y);
  const choices = notBack.length ? notBack : open; // 막다른 길이면 뒤로 돈다
  const forward = c.dir && choices.find(d => d.x === c.dir.x && d.y === c.dir.y);
  c.dir = forward && Math.random() < 0.7 ? forward : choices[Math.floor(Math.random() * choices.length)];
  c.x += c.dir.x;
  c.y += c.dir.y;
  if (isPlayerAt(c.x, c.y)) corgiBite(c);
}

function corgiBite(c) {
  state.remainingMs -= CORGI_PENALTY_MS;
  state.hurtMs = 600;
  c.restMs = CORGI_REST_MS;
  toast('왈! 코기블린에게 물렸다! -5초', 1500);
}

// 해피: 느릿느릿 돌아다니며 길을 막고, 가끔 HECK! 소리로 WKB를 흥분시킨다
function updateHappy(h, dt) {
  h.shoutMs = Math.max(0, h.shoutMs - dt);
  h.shoutTimer -= dt;
  if (h.shoutTimer <= 0) {
    h.shoutTimer += h.cfg.shoutEveryMs;
    h.shoutMs = 1500;
    h.pauseMs = h.cfg.pauseMs; // 길막 패턴: 소리친 뒤 그 자리에 버티기
    state.hasteMs = HECK_HASTE_MS;
    toast('Heck💕Heck💕Heeeeeck!!🔥🐶💕 WKB가 흥분했다!', 1800);
  }
  if (h.pauseMs > 0) { h.pauseMs -= dt; return; }
  h.timer -= dt;
  if (h.timer > 0) return;
  h.timer += h.moveMs;
  const open = openDirs(h.x, h.y, (x, y) => isPlayerAt(x, y) || anyEnemyAt(x, y));
  if (!open.length) return;
  const d = open[Math.floor(Math.random() * open.length)];
  h.x += d.x;
  h.y += d.y;
}

// 플레이어가 한 칸 움직인 직후의 판정. 결과는 하나만 적용된다:
// WKB와 부딪힘(패배) → 코기블린(시간 감소) → 열쇠 줍기 → 출구 도착(승리) 순서
function afterPlayerMove() {
  const p = state.player;
  if (enemyAt('wkb', p.x, p.y)) {
    lose('WKB에게 정면으로 걸어 들어갔다! 💍');
    return true;
  }
  const corgi = enemyAt('corgi', p.x, p.y);
  if (corgi && corgi.restMs <= 0) corgiBite(corgi);

  const key = state.keys.find(k => !k.collected && k.x === p.x && k.y === p.y);
  if (key) {
    key.collected = true;
    state.collectedKeys++;
    if (state.stage.gimmick && state.stage.gimmick.rage) {
      const wkb = state.enemies.find(e => e.type === 'wkb');
      wkb.moveMs = Math.round(wkb.moveMs * RAGE_FACTOR);
      toast('신부의 베일이 펄럭인다... WKB가 더 빨라졌다!', 1500);
    }
    if (state.collectedKeys >= state.requiredKeys) {
      state.exitOpen = true;
      toast('🔓 출구가 열렸다!', 1500);
    }
  }
  if (state.exitOpen && p.x === state.exit.x && p.y === state.exit.y) {
    win();
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------
// 승리 / 패배 / 일시정지 / 엔딩
// ---------------------------------------------------------------------
function stageIndex() { return STAGES.findIndex(s => s.id === state.stage.id); }

function win() {
  state.status = 'won';
  const idx = stageIndex();
  progress.bestStage = Math.max(progress.bestStage, idx + 1);
  progress.unlockedStage = Math.min(STAGES.length, Math.max(progress.unlockedStage, idx + 2));
  saveProgress();

  if (idx === STAGES.length - 1) return showEnding();
  const secLeft = Math.ceil(state.remainingMs / 1000);
  openModal('🎉 스테이지 클리어!', `「${state.stage.name}」 탈출 성공! 남은 시간 ${secLeft}초`, [
    ['다음 스테이지 ▶', () => loadStage(STAGES[idx + 1].id)],
    ['다시 하기', () => loadStage(state.stage.id)],
    ['메뉴로', showMenu]
  ]);
}

function lose(reason) {
  state.status = 'lost';
  openModal('💀 게임 오버', reason, [
    ['다시 하기', () => loadStage(state.stage.id)],
    ['메뉴로', showMenu]
  ]);
}

function togglePause() {
  if (!state) return;
  if (state.status === 'playing') {
    state.status = 'paused';
    input.clear();
    openModal('⏸ 일시정지', '숨 좀 돌리자. WKB도 잠깐 멈췄다.', [
      ['계속하기', resume],
      ['다시 하기', () => loadStage(state.stage.id)],
      ['메뉴로', showMenu]
    ]);
  } else if (state.status === 'paused') {
    resume();
  }
}

function resume() {
  if (!state || state.status !== 'paused') return;
  state.status = 'playing';
  input.clear();
  closeModal();
}

function showEnding() {
  if (state) state.status = 'won';
  openModal('🌅 새벽 4시의 끝',
    '마지막 문이 열리고, 창밖으로 첫 햇살이 들어온다. WKB는 베일을 벗고 조용히 사라졌다… ' +
    '코기블린은 꼬리를 흔들고, 해피는 마지막으로 외친다. "Heck💕Heck💕Heeeeeck!!🔥🐶💕" — 20개 스테이지 모두 탈출 성공!', [
      ['처음부터 다시', () => loadStage(STAGES[0].id)],
      ['메뉴로', showMenu]
    ]);
}

// ---------------------------------------------------------------------
// 화면 표시 (HUD, 모달, 토스트, 메뉴)
// ---------------------------------------------------------------------
function updateHud() {
  if (!state) return;
  el('hud-keys').textContent = `🔑 ${state.collectedKeys}/${state.requiredKeys}`;
  const sec = Math.ceil(state.remainingMs / 1000);
  el('hud-time').textContent = `⏱ ${sec}초`;
  el('hud-time').classList.toggle('danger', sec <= 10);
}

function openModal(title, text, buttons) {
  el('modal-title').textContent = title;
  el('modal-text').textContent = text;
  const box = el('modal-buttons');
  box.innerHTML = '';
  buttons.forEach(([label, onClick]) => {
    const b = document.createElement('button');
    b.textContent = label;
    b.addEventListener('click', onClick);
    box.appendChild(b);
  });
  el('modal').hidden = false;
  box.firstChild.focus(); // 키보드로 바로 Enter 가능
}

function closeModal() { el('modal').hidden = true; }

function toast(text, ms) {
  el('toast').textContent = text;
  el('toast').hidden = false;
  state.toastMs = ms; // setTimeout 대신 게임 시간으로 숨김 → 재시작해도 꼬이지 않음
}

function showScreen(name) {
  el('menu-screen').hidden = name !== 'menu';
  el('game-screen').hidden = name !== 'game';
}

function showMenu() {
  state = null;
  input.clear();
  closeModal();
  el('toast').hidden = true;
  showScreen('menu');
  delete document.body.dataset.chapter;

  const cont = el('btn-continue');
  cont.hidden = progress.unlockedStage <= 1;
  cont.textContent = `이어하기 (Stage ${progress.unlockedStage})`;
  el('menu-progress').textContent = progress.bestStage
    ? `최고 기록: Stage ${progress.bestStage} 클리어`
    : '아직 탈출한 스테이지가 없습니다.';

  // 스테이지 선택 목록 (챕터별로 묶어서)
  const list = el('stage-list');
  list.innerHTML = '';
  Object.keys(CHAPTERS).forEach(ch => {
    const group = document.createElement('div');
    group.className = 'chapter-group';
    group.dataset.chapter = ch;
    const h = document.createElement('h3');
    h.textContent = `챕터 ${ch}. ${CHAPTERS[ch].name}`;
    group.appendChild(h);
    const grid = document.createElement('div');
    grid.className = 'stage-grid';
    STAGES.filter(s => String(s.chapter) === ch).forEach(s => {
      const idx = STAGES.indexOf(s);
      const locked = idx + 1 > progress.unlockedStage;
      const b = document.createElement('button');
      b.className = 'stage-btn';
      b.disabled = locked;
      b.textContent = locked ? `🔒 ${s.id}` : `${s.id}`;
      b.title = s.name;
      b.setAttribute('aria-label', `Stage ${s.id} ${s.name}${locked ? ' (잠김)' : ''}`);
      b.addEventListener('click', () => loadStage(s.id));
      grid.appendChild(b);
    });
    group.appendChild(grid);
    list.appendChild(group);
  });
}

// ---------------------------------------------------------------------
// 게임 루프 (requestAnimationFrame, 딱 한 번만 시작)
// ---------------------------------------------------------------------
function smooth(e, dt) {
  const k = Math.min(1, dt / 60);
  e.rx += (e.x - e.rx) * k;
  e.ry += (e.y - e.ry) * k;
}

let lastTime = performance.now();
function frame(now) {
  const dt = Math.min(100, now - lastTime); // 탭 전환 후 큰 점프 방지
  lastTime = now;
  if (state) {
    if (isPortraitView() !== state.portrait) transposeState();
    update(dt);
    smooth(state.player, dt);
    state.enemies.forEach(e => smooth(e, dt));
    updateHud();
    renderer.draw(state, now);
  }
  requestAnimationFrame(frame);
}

// ---------------------------------------------------------------------
// 버튼 / 키보드 연결 (페이지가 열릴 때 딱 한 번만)
// ---------------------------------------------------------------------
el('btn-start').addEventListener('click', () => loadStage(STAGES[0].id));
el('btn-continue').addEventListener('click', () => loadStage(STAGES[progress.unlockedStage - 1].id));
el('btn-reset').addEventListener('click', () => {
  if (!confirm('진행도를 초기화할까요?')) return;
  progress = { unlockedStage: 1, bestStage: 0 };
  saveProgress();
  showMenu();
});
el('btn-pause').addEventListener('click', togglePause);
input.attachDpad(el('dpad'));
input.attachSwipe(el('board'));

window.addEventListener('keydown', e => {
  if (!state) return;
  if (e.code === 'KeyP' || e.code === 'Escape') { e.preventDefault(); togglePause(); }
  if (e.code === 'KeyR') loadStage(state.stage.id);
});
// 다른 탭으로 가면 자동 일시정지
document.addEventListener('visibilitychange', () => {
  if (document.hidden && state && state.status === 'playing') togglePause();
});

showMenu();
requestAnimationFrame(frame);

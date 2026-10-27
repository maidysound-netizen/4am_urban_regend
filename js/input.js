// =====================================================================
// 입력 담당 (키보드)
// - 키를 "톡" 누르면: pending에 저장 → 다음 이동 때 꼭 한 칸 움직임
// - 키를 "꾹" 누르면: held에 남아 있음 → 일정 간격마다 계속 움직임
// 한 번의 이동 틱에는 한 방향만 꺼내 쓰기 때문에 연타해도 벽을 뚫지 못한다.
// =====================================================================

const DIRS = {
  up: { x: 0, y: -1 }, down: { x: 0, y: 1 },
  left: { x: -1, y: 0 }, right: { x: 1, y: 0 }
};

const KEY_TO_DIR = {
  ArrowUp: 'up', KeyW: 'up',
  ArrowDown: 'down', KeyS: 'down',
  ArrowLeft: 'left', KeyA: 'left',
  ArrowRight: 'right', KeyD: 'right'
};

function createInput() {
  let pending = null;   // 톡 누른 방향 (한 번 쓰면 사라짐)
  const held = [];      // 지금 누르고 있는 방향들 (마지막 것이 우선)

  function press(dir) {
    pending = dir;
    if (!held.includes(dir)) held.push(dir);
  }
  function release(dir) {
    const i = held.indexOf(dir);
    if (i >= 0) held.splice(i, 1);
  }

  window.addEventListener('keydown', e => {
    const dir = KEY_TO_DIR[e.code];
    if (!dir) return;
    e.preventDefault();          // 방향키로 페이지가 스크롤되지 않게
    if (!e.repeat) press(dir);
  });
  window.addEventListener('keyup', e => {
    const dir = KEY_TO_DIR[e.code];
    if (dir) release(dir);
  });
  // 창 밖으로 포커스가 나가면 "누르고 있음" 상태를 지운다
  window.addEventListener('blur', () => { held.length = 0; pending = null; });

  // 모바일 D-Pad: 버튼마다 data-dir="up" 같은 속성을 달아 둔다
  function attachDpad(root) {
    root.querySelectorAll('[data-dir]').forEach(btn => {
      const dir = btn.dataset.dir;
      btn.addEventListener('pointerdown', e => {
        e.preventDefault();
        btn.setPointerCapture(e.pointerId);
        press(dir);
      });
      const up = () => release(dir);
      btn.addEventListener('pointerup', up);
      btn.addEventListener('pointercancel', up);
      btn.addEventListener('lostpointercapture', up);
    });
  }

  // 캔버스 위에서 손가락으로 쓱 밀면 그 방향으로 한 칸
  function attachSwipe(target) {
    let start = null;
    target.addEventListener('pointerdown', e => { start = { x: e.clientX, y: e.clientY }; });
    target.addEventListener('pointerup', e => {
      if (!start) return;
      const dx = e.clientX - start.x, dy = e.clientY - start.y;
      start = null;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 24) return; // 너무 짧으면 무시
      const dir = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');
      press(dir);
      release(dir); // pending에 한 번만 남겨서 딱 한 칸 이동
    });
  }

  return {
    press, release, attachDpad, attachSwipe,
    // 이번 이동에 쓸 방향 하나를 꺼낸다
    takeDirection() {
      const dir = pending || held[held.length - 1] || null;
      pending = null;
      return dir ? DIRS[dir] : null;
    },
    clear() { pending = null; held.length = 0; }
  };
}

// =====================================================================
// 입력 담당 (키보드 + 모바일 가상 조이스틱)
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

  // 모바일 가상 조이스틱: 게임판 아무 데나 누르면 그 자리에 조이스틱이 나타나고,
  // 끄는 방향으로 계속 움직인다. 살짝 튕기기만 해도 한 칸은 간다.
  function attachJoystick(area, joy) {
    const knob = joy.querySelector('.joy-knob');
    const RADIUS = 50;  // 손잡이가 움직일 수 있는 거리(px)
    const DEAD = 14;    // 이보다 덜 밀면 방향 없음
    let id = null, origin = null, dir = null;

    function setDir(next) {
      if (next === dir) return;
      if (dir) release(dir);
      dir = next;
      if (dir) press(dir);
    }
    function end() {
      id = null;
      setDir(null);
      joy.classList.remove('active');
      joy.style.left = joy.style.top = '';
      knob.style.transform = '';
    }

    area.addEventListener('pointerdown', e => {
      if (id !== null) return;
      e.preventDefault();
      area.setPointerCapture(e.pointerId);
      id = e.pointerId;
      const box = joy.offsetParent.getBoundingClientRect();
      origin = { x: e.clientX, y: e.clientY };
      joy.style.left = `${e.clientX - box.left}px`;
      joy.style.top = `${e.clientY - box.top}px`;
      joy.classList.add('active');
    });
    area.addEventListener('pointermove', e => {
      if (e.pointerId !== id) return;
      const dx = e.clientX - origin.x, dy = e.clientY - origin.y;
      const len = Math.hypot(dx, dy);
      const k = len > RADIUS ? RADIUS / len : 1;
      knob.style.transform = `translate(${dx * k}px, ${dy * k}px)`;
      if (len < DEAD) return setDir(null);
      setDir(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up'));
    });
    area.addEventListener('pointerup', e => { if (e.pointerId === id) end(); });
    area.addEventListener('pointercancel', e => { if (e.pointerId === id) end(); });
  }

  return {
    press, release, attachJoystick,
    // 이번 이동에 쓸 방향 하나를 꺼낸다
    takeDirection() {
      const dir = pending || held[held.length - 1] || null;
      pending = null;
      return dir ? DIRS[dir] : null;
    },
    clear() { pending = null; held.length = 0; }
  };
}

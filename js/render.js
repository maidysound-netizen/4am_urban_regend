// =====================================================================
// Canvas 그리기 담당 (레트로 픽셀아트)
//
// 원리: 한 칸 = 16×16 픽셀짜리 "작은 그림"으로 그린 뒤, 화면 크기만큼
// 크게 늘린다(CSS image-rendering: pixelated). 그래서 옛날 게임기처럼
// 네모난 점이 큼직하게 보인다.
//
// 창을 꽉 채우는 법: 맵이 들어갈 수 있는 가장 큰 칸 크기를 고르고,
// 남는 가장자리는 같은 벽돌로 채운다.
// =====================================================================

const TILE = 16;

// ---------------------------------------------------------------------
// 도트 캐릭터 (16×16). 글자 하나 = 점 하나, '.'은 투명.
// 나중에 진짜 그림 파일로 바꾸고 싶으면 여기만 바꾸면 된다.
// ---------------------------------------------------------------------
const SPRITES = {
  player: {
    palette: { k: '#10121c', B: '#2f7fe0', s: '#ffd2a6', r: '#c4404a', w: '#ffffff', N: '#24305e' },
    rows: [
      '................',
      '.....kkkkkk.....',
      '....kBBBBBBk....',
      '...kBBBBBBBBk...',
      '...kBBssssBBk...',
      '...kBskssksBk...',
      '...kBssssssBk...',
      '...kBBsrrsBBk...',
      '....kBBBBBBk....',
      '...kBBBBBBBBk...',
      '..kBBBwBBwBBBk..',
      '..kskBBBBBBksk..',
      '...kBBBBBBBBk...',
      '....kNNkkNNk....',
      '...kkkk..kkkk...',
      '................'
    ]
  },
  wkb: {
    palette: { r: '#e0283c', k: '#1a1418', W: '#f4f1ea', R: '#ff2040', L: '#cfc6b6', s: '#e8b48a' },
    rows: [
      '...r..r..r..r...',
      '...rrrrrrrrrr...',
      '..kWWWWWWWWWWk..',
      '.kWWWRRWWRRWWWk.',
      '.kWWWWWWWWWWWWk.',
      'kWWWWWkkkkWWWWWk',
      'kWWLLLLLLLLLLWWk',
      'kWLssLLLLLLssLWk',
      'kWssssLLLLssssWk',
      'kWssssLLLLssssWk',
      '.kWssLLLLLLssWk.',
      '.kWWLLLLLLLLWWk.',
      'kWWWWWWWWWWWWWWk',
      'kWLWLWLWLWLWLWLk',
      '.kkkkkkkkkkkkkk.',
      '................'
    ]
  },
  key: {
    palette: { k: '#5a3a00', Y: '#ffd23f' },
    rows: [
      '................',
      '................',
      '................',
      '....kkkk........',
      '...kYYYYk.......',
      '..kYYkkYYk......',
      '..kYk..kYkkkkkk.',
      '..kYk..kYYYYYYYk',
      '..kYYkkYYkkYkYk.',
      '...kYYYYk..k.k..',
      '....kkkk........',
      '................',
      '................',
      '................',
      '................',
      '................'
    ]
  },
  door: {
    palette: { k: '#16161c', D: '#6a6a78', d: '#4a4a56', g: '#ffd23f' },
    rows: [
      '..kkkkkkkkkkkk..',
      '..kDDDDDDDDDDk..',
      '..kDddDDDDddDk..',
      '..kDddDDDDddDk..',
      '..kDddDDDDddDk..',
      '..kDDDDDDDDDDk..',
      '..kDDDDggDDDDk..',
      '..kDDDggggDDDk..',
      '..kDDDggggDDDk..',
      '..kDDDDDDDDDDk..',
      '..kDddDDDDddDk..',
      '..kDddDDDDddDk..',
      '..kDddDDDDddDk..',
      '..kDDDDDDDDDDk..',
      '..kkkkkkkkkkkk..',
      '................'
    ]
  },
  corgi: {
    palette: { k: '#2a1606', O: '#f08a24', w: '#fff3e0' },
    rows: [
      '................',
      '................',
      '...kk......kk...',
      '..kOOk....kOOk..',
      '..kOOOkkkkOOOk..',
      '..kOOOOOOOOOOk..',
      '.kOOkOOOOOOkOOk.',
      '.kOOOOwwwwOOOOk.',
      '.kOOOwwkkwwOOOk.',
      '..kOOwwwwwwOOk..',
      '...kOOOOOOOOk...',
      '..kOOOOOOOOOOk..',
      '..kOwOOOOOOwOk..',
      '..kwwk....kwwk..',
      '...kk......kk...',
      '................'
    ]
  },
  happy: {
    palette: { k: '#4a0f2a', Q: '#ffc2dc', P: '#ff7eb6', p: '#d9508e', H: '#ff4f8a' },
    rows: [
      'kkkkkkkkkkkkkkkk',
      'kQQQQQQQQQQQQQQk',
      'kQQQQQQQQQQQQQQk',
      'kPPPPPPPPPPPPPPk',
      'kPPPPPPPPPPPPPPk',
      'kPPkkPPPPPPkkPPk',
      'kPPkkPPPPPPkkPPk',
      'kPPPPPPPPPPPPPPk',
      'kPHHPPPPPPPPHHPk',
      'kPPPkPPPPPPkPPPk',
      'kPPPPkkkkkkPPPPk',
      'kPPPPPPPPPPPPPPk',
      'kPPPPPPPPPPPPPPk',
      'kppppppppppppppk',
      'kppppppppppppppk',
      'kkkkkkkkkkkkkkkk'
    ]
  }
};
// 열린 문은 색만 바꾼 같은 그림
SPRITES.doorOpen = { palette: { k: '#0b2a16', D: '#2fd36b', d: '#1c9a48', g: '#eafff0' }, rows: SPRITES.door.rows };

// 3×5 미니 글꼴 (HECK! 말풍선용)
const MINI_FONT = {
  H: ['1.1', '1.1', '111', '1.1', '1.1'],
  E: ['111', '1..', '11.', '1..', '111'],
  C: ['.11', '1..', '1..', '1..', '.11'],
  K: ['1.1', '1.1', '11.', '1.1', '1.1'],
  '!': ['.1.', '.1.', '.1.', '...', '.1.']
};

// 글자 그림을 작은 캔버스로 한 번만 만들어 두고 계속 재사용한다
function makeCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

function buildSprite(sprite, colorOverride) {
  const c = makeCanvas(TILE, TILE);
  const g = c.getContext('2d');
  sprite.rows.forEach((row, y) => {
    [...row].forEach((ch, x) => {
      if (ch === '.') return;
      g.fillStyle = colorOverride || sprite.palette[ch];
      g.fillRect(x, y, 1, 1);
    });
  });
  return c;
}

const SPRITE_IMG = {};
for (const name in SPRITES) SPRITE_IMG[name] = buildSprite(SPRITES[name]);
SPRITE_IMG.wkbGlow = buildSprite(SPRITES.wkb, '#ff2040');   // 흥분했을 때 테두리
SPRITE_IMG.playerHurt = buildSprite(SPRITES.player, '#ffffff'); // 물렸을 때 하얗게 번쩍

// ---------------------------------------------------------------------
// 벽돌 / 바닥 타일 (챕터 색으로 한 번만 만들어 둠)
// ---------------------------------------------------------------------
function buildWall(theme, front, topEdge) {
  const c = makeCanvas(TILE, TILE);
  const g = c.getContext('2d');
  const faceTop = front ? 11 : 16; // 앞면이 보이면 아래 5줄은 어두운 벽면
  g.fillStyle = theme.brick;
  g.fillRect(0, 0, TILE, faceTop);
  // 벽돌 4줄: 줄마다 4칸씩 어긋나게 쌓기
  for (let row = 0; row < 4; row++) {
    const y = row * 4;
    if (y >= faceTop) break;
    g.fillStyle = theme.brickLight;               // 벽돌 윗변 하이라이트
    g.fillRect(0, y, TILE, 1);
    g.fillStyle = theme.mortar;                   // 가로 줄눈
    if (y + 3 < faceTop) g.fillRect(0, y + 3, TILE, 1);
    const off = row % 2 ? 4 : 0;
    for (let x = off; x < TILE; x += 8) {         // 세로 줄눈 + 그림자
      g.fillStyle = theme.mortar;
      g.fillRect(x, y, 1, Math.min(3, faceTop - y));
      g.fillStyle = theme.brickDark;
      g.fillRect((x + 7) % TILE, y + 1, 1, Math.min(2, faceTop - y - 1));
    }
  }
  if (front) {
    g.fillStyle = theme.brickDark;
    g.fillRect(0, faceTop, TILE, TILE - faceTop);
    g.fillStyle = theme.mortar;
    g.fillRect(0, faceTop, TILE, 1);
    g.fillRect(0, TILE - 1, TILE, 1);
    for (let x = 3; x < TILE; x += 6) g.fillRect(x, faceTop + 1, 1, TILE - faceTop - 2);
  }
  if (topEdge) {
    g.fillStyle = theme.brickLight;
    g.fillRect(0, 0, TILE, 2);
  }
  return c;
}

function buildFloor(theme, alt, shadow) {
  const c = makeCanvas(TILE, TILE);
  const g = c.getContext('2d');
  g.fillStyle = alt ? theme.floorB : theme.floorA;
  g.fillRect(0, 0, TILE, TILE);
  g.fillStyle = theme.floorDot; // 바닥 얼룩 점
  [[3, 4], [11, 9], [6, 13], [13, 2]].forEach(([x, y]) => g.fillRect(alt ? 15 - x : x, y, 1, 1));
  if (shadow) { // 바로 위가 벽이면 그림자 3줄
    [0.5, 0.35, 0.18].forEach((a, y) => {
      g.fillStyle = `rgba(0,0,0,${a})`;
      g.fillRect(0, y, TILE, 1);
    });
  }
  return c;
}

const tileCache = {};
function tilesFor(chapter) {
  if (tileCache[chapter]) return tileCache[chapter];
  const theme = CHAPTERS[chapter].theme;
  tileCache[chapter] = {
    wall: [buildWall(theme, false, false), buildWall(theme, false, true), buildWall(theme, true, false), buildWall(theme, true, true)],
    floor: [buildFloor(theme, false, false), buildFloor(theme, true, false), buildFloor(theme, false, true), buildFloor(theme, true, true)]
  };
  return tileCache[chapter];
}

// 어둠 기믹용 마스크: 가운데는 뚫려 있고, 바깥으로 갈수록 점점 촘촘한 검은 점(디더링)
let darkMask = null;
function getDarkMask() {
  if (darkMask) return darkMask;
  const R = Math.round(TILE * 3.4);
  const c = makeCanvas(R * 2, R * 2);
  const g = c.getContext('2d');
  g.fillStyle = '#000';
  for (let y = 0; y < R * 2; y += 2) {
    for (let x = 0; x < R * 2; x += 2) {
      const d = Math.hypot(x + 1 - R, y + 1 - R) / TILE;
      const bx = x / 2, by = y / 2;
      let on;
      if (d < 1.8) on = false;
      else if (d < 2.4) on = (bx + by) % 2 === 0 && bx % 2 === 0; // 25%
      else if (d < 2.9) on = (bx + by) % 2 === 0;                 // 50%
      else on = !(bx % 2 === 0 && by % 2 === 0);                  // 75% → 그 너머는 완전히 검정
      if (d >= 3.3) on = true;
      if (on) g.fillRect(x, y, 2, 2);
    }
  }
  darkMask = c;
  return c;
}

// ---------------------------------------------------------------------
// 렌더러
// ---------------------------------------------------------------------
function createRenderer(canvas) {
  const ctx = canvas.getContext('2d');
  let view = null; // 이번 프레임의 화면 배치 정보

  // 캔버스가 화면에서 차지하는 크기에 맞춰 "작은 그림"의 픽셀 수를 정한다
  function layout(level) {
    const cssW = canvas.clientWidth || 1, cssH = canvas.clientHeight || 1;
    const tileCss = Math.min(cssW / level.width, cssH / level.height); // 한 칸이 화면에서 몇 px인지
    const w = Math.max(1, Math.round(cssW / tileCss * TILE));
    const h = Math.max(1, Math.round(cssH / tileCss * TILE));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    ctx.imageSmoothingEnabled = false;
    return {
      w, h,
      ox: Math.floor((w - level.width * TILE) / 2),  // 맵 왼쪽 위 위치 (가운데 정렬)
      oy: Math.floor((h - level.height * TILE) / 2)
    };
  }

  function draw(state, time) {
    const { level } = state;
    view = layout(level);
    const { w, h, ox, oy } = view;
    const tiles = tilesFor(state.stage.chapter);
    // 맵 밖은 전부 벽으로 친다 → 남는 가장자리도 벽돌로 꽉 찬다
    const wallAt = (x, y) => x < 0 || y < 0 || x >= level.width || y >= level.height || level.walls[y][x];

    // 1) 화면 전체를 칸 단위로 채우기
    const x0 = -Math.ceil(ox / TILE), y0 = -Math.ceil(oy / TILE);
    const x1 = Math.ceil((w - ox) / TILE), y1 = Math.ceil((h - oy) / TILE);
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const px = ox + x * TILE, py = oy + y * TILE;
        if (wallAt(x, y)) {
          const front = !wallAt(x, y + 1);
          const top = !wallAt(x, y - 1);
          ctx.drawImage(tiles.wall[(front ? 2 : 0) + (top ? 1 : 0)], px, py);
        } else {
          ctx.drawImage(tiles.floor[((x + y) % 2) + (wallAt(x, y - 1) ? 2 : 0)], px, py);
        }
      }
    }
    // 맵 바깥 벽돌은 살짝 어둡게 → 놀 수 있는 곳이 눈에 띄게
    ctx.fillStyle = 'rgba(0,0,0,0.45)';
    ctx.fillRect(0, 0, w, oy);
    ctx.fillRect(0, oy + level.height * TILE, w, h);
    ctx.fillRect(0, oy, ox, level.height * TILE);
    ctx.fillRect(ox + level.width * TILE, oy, w, level.height * TILE);

    const at = (gx, gy) => [ox + Math.round(gx * TILE), oy + Math.round(gy * TILE)];

    // 2) 출구 (열리면 바닥이 깜빡깜빡)
    const [ex, ey] = at(state.exit.x, state.exit.y);
    if (state.exitOpen && Math.floor(time / 250) % 2 === 0) {
      ctx.fillStyle = '#1c9a48';
      ctx.fillRect(ex, ey, TILE, TILE);
    }
    ctx.drawImage(state.exitOpen ? SPRITE_IMG.doorOpen : SPRITE_IMG.door, ex, ey);

    // 3) 열쇠 (통통 튀기)
    state.keys.forEach((k, i) => {
      if (k.collected) return;
      const [kx, ky] = at(k.x, k.y);
      const bob = Math.floor(time / 200 + i) % 2;
      ctx.drawImage(SPRITE_IMG.key, kx, ky + 1 - bob);
    });

    // 4) 캐릭터: 발밑 그림자 → 코기/해피 → WKB → 플레이어
    const actors = [state.player, ...state.enemies];
    actors.forEach(a => {
      const [ax, ay] = at(a.rx, a.ry);
      ctx.fillStyle = 'rgba(0,0,0,0.4)';
      ctx.fillRect(ax + 4, ay + 14, 8, 2);
    });
    state.enemies.forEach(e => {
      const [x, y] = at(e.rx, e.ry);
      if (e.type === 'corgi') {
        ctx.globalAlpha = e.restMs > 0 ? 0.5 : 1;
        ctx.drawImage(SPRITE_IMG.corgi, x, y - (Math.floor(time / 150) % 2));
        ctx.globalAlpha = 1;
      }
      if (e.type === 'happy') ctx.drawImage(SPRITE_IMG.happy, x, y - (Math.floor(time / 220) % 2));
    });
    state.enemies.forEach(e => {
      if (e.type !== 'wkb') return;
      const [x, y] = at(e.rx, e.ry);
      if (state.hasteMs > 0 && Math.floor(time / 100) % 2 === 0) { // 빨간 테두리 번쩍
        [[-1, 0], [1, 0], [0, -1], [0, 1]].forEach(([dx, dy]) => ctx.drawImage(SPRITE_IMG.wkbGlow, x + dx, y + dy));
      }
      ctx.drawImage(SPRITE_IMG.wkb, x, y - (Math.floor(time / 300) % 2));
    });
    const [px, py] = at(state.player.rx, state.player.ry);
    const hurtFlash = state.hurtMs > 0 && Math.floor(time / 80) % 2 === 0;
    ctx.drawImage(hurtFlash ? SPRITE_IMG.playerHurt : SPRITE_IMG.player, px, py);

    // 5) 어둠 기믹: 플레이어 주변만 보이게 (가장자리는 점점 촘촘한 검은 점)
    if (state.stage.gimmick && state.stage.gimmick.darkness) {
      const mask = getDarkMask();
      const mx = px + TILE / 2 - mask.width / 2, my = py + TILE / 2 - mask.height / 2;
      ctx.drawImage(mask, mx, my);
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, w, Math.max(0, my));
      ctx.fillRect(0, my + mask.height, w, h);
      ctx.fillRect(0, my, Math.max(0, mx), mask.height);
      ctx.fillRect(mx + mask.width, my, w, mask.height);
    }

    // 6) 해피의 HECK! 말풍선 (어둠 위에 그려서 소리가 들리는 느낌)
    state.enemies.forEach(e => {
      if (e.type === 'happy' && e.shoutMs > 0) {
        const [x, y] = at(e.rx, e.ry);
        drawBubble(x + TILE / 2, y - 3, 'HECK!');
      }
    });
  }

  function drawBubble(cx, bottom, text) {
    const tw = text.length * 4 - 1;
    const bw = tw + 6, bh = 11;
    const bx = Math.min(Math.max(Math.round(cx - bw / 2), 1), canvas.width - bw - 1);
    const by = Math.max(bottom - bh, 1);
    ctx.fillStyle = '#000';
    ctx.fillRect(bx - 1, by - 1, bw + 2, bh + 2);
    ctx.fillStyle = '#fff';
    ctx.fillRect(bx, by, bw, bh);
    ctx.fillStyle = '#e0287a';
    [...text].forEach((ch, i) => {
      MINI_FONT[ch].forEach((row, ry) => {
        [...row].forEach((on, rx) => { if (on === '1') ctx.fillRect(bx + 3 + i * 4 + rx, by + 3 + ry, 1, 1); });
      });
    });
  }

  return { draw };
}

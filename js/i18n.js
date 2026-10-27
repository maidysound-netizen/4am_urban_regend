// =====================================================================
// 번역 (한국어 / English / 日本語)
// - 화면 글자는 전부 여기서 꺼내 쓴다: t('키', { 값 })
// - HTML에 고정된 글자는 data-i18n="키" (aria-label은 data-i18n-aria) 로 표시
// - 고른 언어는 저장되고, 처음엔 브라우저 언어를 따른다.
// =====================================================================

const LANGS = ['ko', 'en', 'ja'];
const LANG_KEY = '4am-escape-lang';
const HECK = 'Heck💕Heck💕Heeeeeck!!🔥🐶💕';

const STRINGS = {
  ko: {
    title: '새벽 4시: 괴담 탈출!',
    subtitle: '열쇠를 모아 출구를 열고, 괴담 신부 WKB에게 잡히기 전에 탈출하라.',
    start: '처음부터 시작',
    continue: '이어하기 (Stage {n})',
    best: '최고 기록: Stage {n} 클리어',
    noBest: '아직 탈출한 스테이지가 없습니다.',
    legend: '등장 요소 설명',
    lgMe: '나', lgWkb: 'WKB (잡히면 끝)', lgKey: '열쇠', lgExit: '출구',
    lgCorgi: '코기블린 (-5초)', lgHappy: '해피 (길막·HECK!)',
    selectStage: '스테이지 선택',
    help: '조작: 방향키 / WASD 이동 · P 또는 Esc 일시정지 · R 재시작 · M 소리 켜기/끄기 · 모바일은 화면을 누르고 끌기 (조이스틱)',
    reset: '진행도 초기화',
    resetConfirm: '진행도를 초기화할까요?',
    chapter: '챕터 {n}. {name}',
    locked: ' (잠김)',
    pause: '일시정지', board: '게임 화면',
    soundOn: '소리 켜기', soundOff: '소리 끄기',
    seconds: '{n}초',
    happyAppears: HECK + ' 해피 등장!',
    timeUp: '시간 초과! 새벽 4시가 끝나 버렸다...',
    caught: 'WKB에게 붙잡혔다! 💍',
    walkedInto: 'WKB에게 정면으로 걸어 들어갔다! 💍',
    bitten: '왈! 코기블린에게 물렸다! -5초',
    heckHaste: HECK + ' WKB가 흥분했다!',
    rage: '신부의 베일이 펄럭인다... WKB가 더 빨라졌다!',
    exitOpen: '🔓 출구가 열렸다!',
    clearTitle: '🎉 스테이지 클리어!',
    clearText: '「{name}」 탈출 성공! 남은 시간 {n}초',
    next: '다음 스테이지 ▶', retry: '다시 하기', menu: '메뉴로',
    overTitle: '💀 게임 오버',
    pauseTitle: '⏸ 일시정지', pauseText: '숨 좀 돌리자. WKB도 잠깐 멈췄다.', resume: '계속하기',
    endTitle: '🌅 새벽 4시의 끝',
    endText: '마지막 문이 열리고, 창밖으로 첫 햇살이 들어온다. WKB는 베일을 벗고 조용히 사라졌다… ' +
      '코기블린은 꼬리를 흔들고, 해피는 마지막으로 외친다. "' + HECK + '" — 20개 스테이지 모두 탈출 성공!',
    restart: '처음부터 다시'
  },
  en: {
    title: '4 AM: Urban Legend Escape!',
    subtitle: 'Collect the keys, open the exit, and escape before WKB, the ghost bride, catches you.',
    start: 'New Game',
    continue: 'Continue (Stage {n})',
    best: 'Best: cleared Stage {n}',
    noBest: 'No stages escaped yet.',
    legend: 'Legend',
    lgMe: 'You', lgWkb: 'WKB (caught = game over)', lgKey: 'Key', lgExit: 'Exit',
    lgCorgi: 'Corgoblin (-5 s)', lgHappy: 'Happy (blocks · HECK!)',
    selectStage: 'Select Stage',
    help: 'Controls: Arrows / WASD move · P or Esc pause · R restart · M sound on/off · Mobile: touch & drag anywhere (joystick)',
    reset: 'Reset progress',
    resetConfirm: 'Reset your progress?',
    chapter: 'Chapter {n}. {name}',
    locked: ' (locked)',
    pause: 'Pause', board: 'Game board',
    soundOn: 'Sound on', soundOff: 'Sound off',
    seconds: '{n}s',
    happyAppears: HECK + ' Happy appears!',
    timeUp: 'Time\'s up! 4 AM is over...',
    caught: 'WKB caught you! 💍',
    walkedInto: 'You walked straight into WKB! 💍',
    bitten: 'Woof! The Corgoblin bit you! -5 s',
    heckHaste: HECK + ' WKB is getting excited!',
    rage: 'The bride\'s veil flutters... WKB got faster!',
    exitOpen: '🔓 The exit is open!',
    clearTitle: '🎉 Stage Clear!',
    clearText: 'Escaped "{name}"! {n} s left',
    next: 'Next Stage ▶', retry: 'Retry', menu: 'Menu',
    overTitle: '💀 Game Over',
    pauseTitle: '⏸ Paused', pauseText: 'Catch your breath. WKB is frozen too.', resume: 'Resume',
    endTitle: '🌅 The End of 4 AM',
    endText: 'The last door opens and the first sunlight comes through the window. WKB takes off her veil and quietly fades away… ' +
      'The Corgoblin wags its tail, and Happy shouts one last time: "' + HECK + '" — all 20 stages escaped!',
    restart: 'Play Again'
  },
  ja: {
    title: '午前4時：怪談脱出！',
    subtitle: '鍵を集めて出口を開け、怪談の花嫁WKBに捕まる前に脱出せよ。',
    start: '最初から',
    continue: 'つづきから (Stage {n})',
    best: '最高記録：Stage {n} クリア',
    noBest: 'まだ脱出したステージはありません。',
    legend: '登場キャラクター',
    lgMe: '自分', lgWkb: 'WKB（捕まると終わり）', lgKey: '鍵', lgExit: '出口',
    lgCorgi: 'コーギーブリン（-5秒）', lgHappy: 'ハッピー（通せんぼ・HECK!）',
    selectStage: 'ステージ選択',
    help: '操作：矢印キー / WASD 移動 · P または Esc 一時停止 · R やり直し · M 音のオン/オフ · スマホは画面をタッチしてドラッグ（ジョイスティック）',
    reset: '進行状況をリセット',
    resetConfirm: '進行状況をリセットしますか？',
    chapter: 'チャプター{n}. {name}',
    locked: '（ロック中）',
    pause: '一時停止', board: 'ゲーム画面',
    soundOn: '音をオン', soundOff: '音をオフ',
    seconds: '{n}秒',
    happyAppears: HECK + ' ハッピー登場！',
    timeUp: '時間切れ！午前4時が終わってしまった…',
    caught: 'WKBに捕まった！💍',
    walkedInto: 'WKBに正面から突っ込んだ！💍',
    bitten: 'ワン！コーギーブリンに噛まれた！-5秒',
    heckHaste: HECK + ' WKBが興奮した！',
    rage: '花嫁のベールがはためく…WKBが速くなった！',
    exitOpen: '🔓 出口が開いた！',
    clearTitle: '🎉 ステージクリア！',
    clearText: '「{name}」脱出成功！残り{n}秒',
    next: '次のステージ ▶', retry: 'もう一度', menu: 'メニューへ',
    overTitle: '💀 ゲームオーバー',
    pauseTitle: '⏸ 一時停止', pauseText: 'ひと息つこう。WKBも少し止まっている。', resume: 'つづける',
    endTitle: '🌅 午前4時の終わり',
    endText: '最後の扉が開き、窓から朝日が差し込む。WKBはベールを脱ぎ、静かに消えていった… ' +
      'コーギーブリンはしっぽを振り、ハッピーは最後に叫ぶ。「' + HECK + '」 — 全20ステージ脱出成功！',
    restart: '最初からもう一度'
  }
};

// 챕터·스테이지 이름 (한국어는 stages.js에 있는 원래 이름을 쓴다)
const CHAPTER_NAMES = {
  en: { 1: 'Dawn Visitor', 2: 'Takako\'s Alley', 3: 'Party People Night', 4: 'Haunted Wedding Hall' },
  ja: { 1: '夜明けの訪問者', 2: 'タカコの路地', 3: 'パーリーピーポーの夜', 4: '怪談ウェディングホール' }
};
const STAGE_NAMES = {
  en: {
    1: 'Dark Hallway', 2: 'Locked Front Door', 3: 'Fire Escape', 4: 'Basement at Dawn', 5: 'First Escape',
    6: 'Ramen Shop Back Door', 7: 'Suspicious Alley', 8: 'Night Market', 9: 'Warehouse Key', 10: 'End of the Alley',
    11: 'Neon Street', 12: 'Club Entrance', 13: 'Dance Floor', 14: 'DJ Booth', 15: '4 Minutes to Last Call',
    16: 'Ruined Wedding Hall', 17: 'A Wedding Without Guests', 18: 'The Bride\'s Veil', 19: 'The Last Key', 20: 'The End of 4 AM'
  },
  ja: {
    1: '明かりの消えた廊下', 2: '鍵のかかった玄関', 3: '非常階段', 4: '夜明けの地下室', 5: '最初の脱出',
    6: 'ラーメン屋の裏口', 7: 'あやしい路地', 8: '夜の市場', 9: '倉庫の鍵', 10: '路地の果て',
    11: 'ネオン街', 12: 'クラブの入口', 13: 'ダンスフロア', 14: 'DJブース', 15: 'パーティー終了4分前',
    16: '廃墟のウェディングホール', 17: '参列者のいない式', 18: '花嫁のベール', 19: '最後の鍵', 20: '午前4時の終わり'
  }
};

let lang = 'ko';
try { lang = localStorage.getItem(LANG_KEY) || ''; } catch (e) { /* 무시 */ }
if (!LANGS.includes(lang)) {
  const nav = (navigator.language || 'ko').slice(0, 2);
  lang = LANGS.includes(nav) ? nav : 'en';
}

function t(key, vars = {}) {
  const s = STRINGS[lang][key] ?? STRINGS.ko[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
}
function stageName(s) { return (STAGE_NAMES[lang] || {})[s.id] || s.name; }
function chapterName(ch) { return (CHAPTER_NAMES[lang] || {})[ch] || CHAPTERS[ch].name; }

// HTML에 고정된 글자를 지금 언어로 바꾼다
function applyI18n() {
  document.documentElement.lang = lang;
  document.title = t('title');
  document.querySelectorAll('[data-i18n]').forEach(n => { n.textContent = t(n.dataset.i18n); });
  document.querySelectorAll('[data-i18n-aria]').forEach(n => { n.setAttribute('aria-label', t(n.dataset.i18nAria)); });
  document.querySelectorAll('[data-lang]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.lang === lang)));
}

function setLang(next) {
  if (!LANGS.includes(next)) return;
  lang = next;
  try { localStorage.setItem(LANG_KEY, lang); } catch (e) { /* 무시 */ }
  applyI18n();
}

// =====================================================================
// 배경음악 (BGM)
// - 직접 만든 8비트 재즈 곡을 틀고, 끝나면 처음부터 다시 튼다. (곡을 더 넣으면 순서대로 돈다)
// - 브라우저는 사용자가 한 번 클릭/키 입력을 해야 소리를 허락하므로
//   첫 입력 때 재생을 시작한다.
// - 음소거 버튼(🔊/🔇) 또는 M 키로 끄고 켤 수 있고, 설정은 저장된다.
// =====================================================================

const BGM_TRACKS = ['audio/jazz.m4a'];
const BGM_VOLUME = 0.5;
const BGM_MUTE_KEY = '4am-escape-bgm-muted';

function createBgm(button) {
  const audio = new Audio();
  audio.preload = 'auto';
  audio.volume = BGM_VOLUME;
  audio.loop = BGM_TRACKS.length === 1; // 한 곡뿐이면 끊김 없이 반복
  let index = 0;
  let started = false;
  let muted = false;
  try { muted = localStorage.getItem(BGM_MUTE_KEY) === '1'; } catch (e) { /* 저장이 막혀 있어도 괜찮다 */ }

  function load(i) {
    index = (i + BGM_TRACKS.length) % BGM_TRACKS.length;
    audio.src = BGM_TRACKS[index];
  }
  function play() {
    if (muted) return;
    audio.play().catch(() => { started = false; }); // 아직 허락이 안 났으면 다음 입력 때 다시
  }

  // 곡이 끝나면 다음 곡, 파일을 못 읽으면 건너뛴다
  // (모든 곡이 다 실패하면 무한 반복하지 않게 멈춘다)
  let failures = 0;
  audio.addEventListener('playing', () => { failures = 0; });
  audio.addEventListener('ended', () => { load(index + 1); play(); });
  audio.addEventListener('error', () => {
    if (!started || ++failures >= BGM_TRACKS.length) return;
    load(index + 1);
    play();
  });

  function updateButton() {
    button.textContent = muted ? '🔇' : '🔊';
    button.setAttribute('aria-label', muted ? '배경음악 켜기' : '배경음악 끄기');
    button.setAttribute('aria-pressed', String(muted));
  }

  function toggleMute() {
    muted = !muted;
    try { localStorage.setItem(BGM_MUTE_KEY, muted ? '1' : '0'); } catch (e) { /* 무시 */ }
    if (muted) audio.pause();
    else { started = true; play(); }
    updateButton();
  }

  // 첫 사용자 입력에서 재생 시작
  function unlock() {
    if (started) return;
    started = true;
    play();
  }
  window.addEventListener('pointerdown', unlock);
  window.addEventListener('keydown', unlock);

  button.addEventListener('click', toggleMute);
  window.addEventListener('keydown', e => {
    if (e.code === 'KeyM' && !e.repeat) toggleMute();
  });

  load(0);
  updateButton();
  return { toggleMute };
}

// =====================================================================
// 배경음악 (BGM)
// - 직접 만든 8비트 재즈 곡을 틀고, 끝나면 처음부터 다시 튼다. (곡을 더 넣으면 순서대로 돈다)
// - 브라우저는 사용자가 한 번 클릭/키 입력을 해야 소리를 허락하므로
//   첫 입력 때 재생을 시작한다.
// - 음소거 버튼(🔊/🔇) 또는 M 키로 끄고 켤 수 있고, 설정은 저장된다. (효과음도 같이 꺼진다)
// - <audio> 대신 Web Audio 버퍼로 튼다. <audio>는 재생 속도를 자주 바꾸면 소리가 끊기지만
//   버퍼 재생은 속도가 부드럽게 미끄러진다. 볼륨도 아이폰에서 확실히 줄어든다.
// =====================================================================

const BGM_TRACKS = ['audio/jazz.m4a'];
const BGM_VOLUME = 0.22;
const BGM_MUTE_KEY = '4am-escape-bgm-muted';

function createBgm(button) {
  let index = 0;
  let started = false;
  let muted = false;
  try { muted = localStorage.getItem(BGM_MUTE_KEY) === '1'; } catch (e) { /* 저장이 막혀 있어도 괜찮다 */ }

  // 파일은 미리 받아 두고, 소리 허락이 나면 디코딩한다
  const files = BGM_TRACKS.map(url => fetch(url).then(r => r.arrayBuffer()).catch(() => null));
  const buffers = [];
  let gain = null;
  let src = null;
  let rate = 1;

  async function buffer(i) {
    if (!buffers[i]) {
      const data = await files[i];
      buffers[i] = data ? sfxCtx.decodeAudioData(data.slice(0)).catch(() => null) : Promise.resolve(null);
    }
    return buffers[i];
  }

  let loading = false;
  async function startTrack(i) {
    if (loading || src) return;
    loading = true;
    index = (i + BGM_TRACKS.length) % BGM_TRACKS.length;
    const buf = await buffer(index);
    loading = false;
    if (!buf || src) return;
    src = sfxCtx.createBufferSource();
    src.buffer = buf;
    src.loop = BGM_TRACKS.length === 1; // 한 곡뿐이면 끊김 없이 반복
    src.playbackRate.value = rate;
    src.connect(gain);
    src.onended = () => { src = null; startTrack(index + 1); };
    src.start();
  }

  function play() {
    if (muted) return;
    const ctx = getAudioCtx();
    if (!ctx) return;
    if (ctx.state === 'suspended') ctx.resume();
    if (!gain) {
      gain = ctx.createGain();
      gain.gain.value = BGM_VOLUME;
      gain.connect(ctx.destination);
    }
    startTrack(index);
  }

  function updateButton() {
    button.textContent = muted ? '🔇' : '🔊';
    button.setAttribute('aria-label', t(muted ? 'soundOn' : 'soundOff'));
    button.setAttribute('aria-pressed', String(muted));
  }

  // 음소거 = 오디오 전체를 잠깐 멈춤 → 다시 켜면 멈춘 자리부터 이어서
  function toggleMute() {
    muted = !muted;
    try { localStorage.setItem(BGM_MUTE_KEY, muted ? '1' : '0'); } catch (e) { /* 무시 */ }
    if (muted) { if (sfxCtx) sfxCtx.suspend(); }
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

  // WKB가 가까우면 빨라진다 (음도 같이 올라감). 0.05 단위로만 바꾸고 0.4초에 걸쳐 미끄러지게
  function setTempo(target) {
    target = Math.round(target * 20) / 20;
    if (target === rate) return;
    rate = target;
    if (src) src.playbackRate.setTargetAtTime(rate, sfxCtx.currentTime, 0.4);
  }

  updateButton();
  return { toggleMute, setTempo, isMuted: () => muted, refresh: updateButton };
}

// =====================================================================
// 효과음 (SFX)
// - 파일 없이 Web Audio로 8비트 소리를 그 자리에서 만든다.
// - 배경음악도 같은 AudioContext를 지나가게 해서 볼륨을 확실히 줄인다
//   (아이폰 사파리는 audio.volume을 무시하기 때문).
// - 음소거(🔇 / M 키)는 배경음악과 효과음을 같이 끈다.
// =====================================================================

const SFX_VOLUME = 0.35;

let sfxCtx = null;
// 첫 사용자 입력 때 불러야 소리가 허락된다
function getAudioCtx() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  if (!sfxCtx) sfxCtx = new Ctx();
  if (sfxCtx.state === 'suspended') sfxCtx.resume();
  return sfxCtx;
}

function createSfx(isMuted) {
  let master = null;
  let noiseBuf = null;

  function ready() {
    if (isMuted() || !sfxCtx || sfxCtx.state !== 'running') return null;
    if (!master) {
      master = sfxCtx.createGain();
      master.gain.value = SFX_VOLUME;
      master.connect(sfxCtx.destination);
      // 8비트 드럼처럼 거친 화이트 노이즈 0.5초
      noiseBuf = sfxCtx.createBuffer(1, sfxCtx.sampleRate / 2, sfxCtx.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    return sfxCtx;
  }

  // 음 하나: from → to Hz로 미끄러지며 dur초 동안
  function tone(at, from, to, dur, { type = 'square', vol = 0.5 } = {}) {
    const ctx = ready();
    if (!ctx) return;
    const t = ctx.currentTime + at;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(from, t);
    if (to !== from) osc.frequency.exponentialRampToValueAtTime(to, t + dur);
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    osc.connect(g).connect(master);
    osc.start(t);
    osc.stop(t + dur + 0.02);
  }

  function noise(at, dur, vol = 0.4, cutoff = 3000) {
    const ctx = ready();
    if (!ctx) return;
    const t = ctx.currentTime + at;
    const src = ctx.createBufferSource();
    const f = ctx.createBiquadFilter();
    const g = ctx.createGain();
    src.buffer = noiseBuf;
    f.type = 'lowpass';
    f.frequency.value = cutoff;
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    src.connect(f).connect(g).connect(master);
    src.start(t);
    src.stop(t + dur + 0.02);
  }

  const notes = (list, step, opts) => list.forEach((f, i) => tone(i * step, f, f, step * 1.6, opts));

  return {
    step()  { tone(0, 220, 180, 0.03, { type: 'triangle', vol: 0.25 }); },          // 발소리
    key()   { notes([988, 1319], 0.07, { vol: 0.35 }); },                            // 열쇠 (띠링)
    open()  { notes([523, 659, 784, 1047, 1319], 0.07, { vol: 0.3 }); },             // 출구 열림
    bite()  { noise(0, 0.12, 0.5, 2000); tone(0, 600, 150, 0.18, { vol: 0.4 }); },   // 코기 "왈!"
    heck()  {                                                                         // 해피 "Heck Heck Heeeck"
      tone(0, 900, 1300, 0.08, { vol: 0.3 });
      tone(0.13, 900, 1300, 0.08, { vol: 0.3 });
      tone(0.26, 900, 1700, 0.3, { vol: 0.3 });
    },
    rage()  { tone(0, 110, 70, 0.4, { type: 'sawtooth', vol: 0.35 }); },             // WKB가 빨라짐
    tick()  { tone(0, 1760, 1760, 0.04, { vol: 0.2 }); },                             // 남은 10초 째깍
    start() { notes([392, 784], 0.08, { vol: 0.3 }); },                               // 스테이지 시작
    pause() { tone(0, 660, 660, 0.06, { vol: 0.25 }); },
    win()   { notes([523, 659, 784, 1047], 0.1, { vol: 0.35 }); tone(0.4, 1047, 1047, 0.5, { vol: 0.3 }); },
    lose()  {                                                                         // 반음씩 떨어지는 게임오버
      [494, 466, 440, 415].forEach((f, i) => tone(i * 0.16, f, f * 0.97, 0.2, { vol: 0.35 }));
      tone(0.64, 392, 196, 0.6, { type: 'triangle', vol: 0.5 });
    }
  };
}

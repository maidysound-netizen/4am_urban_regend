"""Turn a song (mix + Demucs stems) into an NES-style 8-bit version that follows it note for note.

usage: python cover8bit.py MIX.wav STEMDIR OUT.wav [--lead vocals|other|auto]
"""
import os, sys, numpy as np, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiptune as c

SR_A = 22050
HOP = 256
NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def load(p):
    y, _ = librosa.load(p, sr=SR_A, mono=True)
    return y


def grid_from_beats(y):
    tempo, beats = librosa.beat.beat_track(y=y, sr=SR_A, units='time', tightness=200)
    beats = np.asarray(beats)
    ib = np.median(np.diff(beats))
    dur = len(y) / SR_A
    pre = np.arange(beats[0] - ib, -ib, -ib)[::-1]
    post = np.arange(beats[-1] + ib, dur + ib, ib)
    b = np.concatenate([pre, beats, post])
    g = []
    for i in range(len(b) - 1):
        g.extend(b[i] + (b[i + 1] - b[i]) * np.arange(4) / 4)
    g.append(b[-1])
    return float(np.atleast_1d(tempo)[0]), np.array(g), b


def f0_track(y, fmin, fmax):
    f0, vf, vp = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=SR_A, frame_length=2048, hop_length=HOP)
    t = librosa.times_like(f0, sr=SR_A, hop_length=HOP)
    m = librosa.hz_to_midi(np.where(vf, f0, np.nan))
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0][: len(t)]
    return t, m, vp, rms


def cells_to_notes(grid, t, m, rms, onsets, min_rms, smooth=3):
    n = len(grid) - 1
    pitch = np.full(n, np.nan)
    vel = np.zeros(n)
    idx = np.searchsorted(t, grid)
    for i in range(n):
        a, b = idx[i], max(idx[i] + 1, idx[i + 1])
        mm = m[a:b]
        ok = ~np.isnan(mm)
        if ok.mean() >= 0.5 and rms[a:b].mean() > min_rms:
            pitch[i] = np.round(np.median(mm[ok]))
            vel[i] = rms[a:b].mean()
    # 1-셀짜리 튀는 음 정리 (앞뒤가 같은 음이면 맞춰 준다)
    for i in range(1, n - 1):
        if not np.isnan(pitch[i - 1]) and pitch[i - 1] == pitch[i + 1] and pitch[i] != pitch[i - 1]:
            pitch[i] = pitch[i - 1]
    on = np.zeros(n, bool)
    for o in onsets:
        k = int(np.argmin(np.abs(grid[:-1] - o)))
        on[k] = True
    notes = []
    for i in range(n):
        if np.isnan(pitch[i]):
            continue
        if notes and notes[-1]['end'] == i and notes[-1]['m'] == pitch[i] and not on[i]:
            notes[-1]['end'] = i + 1
            notes[-1]['v'] = max(notes[-1]['v'], vel[i])
        else:
            notes.append(dict(start=i, end=i + 1, m=int(pitch[i]), v=vel[i]))
    # 너무 짧은 잡음 음 제거 (16분음표 1개짜리가 고립돼 있으면)
    out = []
    for k, nt in enumerate(notes):
        L = nt['end'] - nt['start']
        alone = (k == 0 or notes[k - 1]['end'] < nt['start']) and (k == len(notes) - 1 or notes[k + 1]['start'] > nt['end'])
        if L == 1 and alone:
            continue
        out.append(nt)
    return out


def chord_per_beat(y, beats):
    chroma = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(y), sr=SR_A, hop_length=HOP)
    fr = librosa.time_to_frames(beats, sr=SR_A, hop_length=HOP)
    fr = np.clip(fr, 0, chroma.shape[1] - 1)
    sync = librosa.util.sync(chroma, fr, aggregate=np.median)
    names, T = [], []
    for r in range(12):
        for q, iv in (('', (0, 4, 7)), ('m', (0, 3, 7))):
            v = np.zeros(12)
            v[[(r + i) % 12 for i in iv]] = 1
            names.append((r, iv))
            T.append(v / np.linalg.norm(v))
    T = np.array(T)
    sc = T @ (sync / (np.linalg.norm(sync, axis=0) + 1e-9))
    # 화음이 너무 자주 바뀌지 않게: 이전 화음에 약간 가산점
    out = []
    prev = None
    for j in range(sc.shape[1]):
        s = sc[:, j].copy()
        if prev is not None:
            s[prev] += 0.04
        k = int(np.argmax(s))
        out.append(names[k] if sync[:, j].max() > 0 else None)
        prev = k
    return out


def drum_hits(y, grid):
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=HOP))
    f = librosa.fft_frequencies(sr=SR_A, n_fft=1024)
    res = {}
    for name, lo, hi in (('k', 30, 130), ('s', 1000, 4500), ('h', 6000, 11000)):
        band = S[(f >= lo) & (f < hi)]
        env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(band), sr=SR_A, hop_length=HOP)
        on = librosa.onset.onset_detect(onset_envelope=env, sr=SR_A, hop_length=HOP, units='time',
                                        delta=dict(k=0.3, s=0.35, h=0.3)[name])
        strength = env[librosa.time_to_frames(on, sr=SR_A, hop_length=HOP)] if len(on) else []
        cells = set()
        top = np.percentile(env, 99) if len(env) else 1
        for o, st in zip(on, strength):
            k = int(np.argmin(np.abs(grid[:-1] - o)))
            if abs(grid[k] - o) < 0.06:
                cells.add((k, min(1.0, st / top)))
        res[name] = sorted(cells)
    return res


def octave_fix(notes, target):
    if not notes:
        return notes
    med = np.median([n['m'] for n in notes])
    sh = int(round((target - med) / 12)) * 12
    for n in notes:
        n['m'] += sh
    return notes


def main():
    mix_p, stem_dir, out_p = sys.argv[1:4]
    lead_src = sys.argv[5] if len(sys.argv) > 5 else 'auto'
    mix = load(mix_p)
    cache = out_p + '.pkl'
    if os.path.exists(cache):
        import pickle
        lead, inst, bass, chords, drums, grid, beats, loud = pickle.load(open(cache, 'rb'))
        drums = drum_hits(load(f'{stem_dir}/drums.wav'), grid)
        print('kick', len(drums['k']), 'snare', len(drums['s']), 'hat', len(drums['h']))
    else:
        lead, inst, bass, chords, drums, grid, beats, loud = analyse(mix, stem_dir, lead_src)
        import pickle
        pickle.dump((lead, inst, bass, chords, drums, grid, beats, loud), open(cache, 'wb'))
    render_all(mix, lead, inst, bass, chords, drums, grid, beats, loud, out_p)


def analyse(mix, stem_dir, lead_src):
    tempo, grid, beats = grid_from_beats(mix)
    stems = {k: load(f'{stem_dir}/{k}.wav') for k in ('vocals', 'bass', 'drums', 'other')}
    e = {k: float(np.sqrt(np.mean(v ** 2))) for k, v in stems.items()}
    print('tempo', round(tempo, 1), 'stem rms', {k: round(v, 3) for k, v in e.items()})

    # --- 멜로디: 보컬(있으면) + 보컬이 쉬는 동안은 악기 멜로디
    tv, mv, pv, rv = f0_track(stems['vocals'], 100, 1100)
    ov = librosa.onset.onset_detect(y=stems['vocals'], sr=SR_A, hop_length=HOP, units='time', backtrack=True)
    voc = cells_to_notes(grid, tv, mv, rv, ov, min_rms=max(0.01, e['vocals'] * 0.35))
    to, mo, po, ro = f0_track(stems['other'], 180, 1500)
    oo = librosa.onset.onset_detect(y=stems['other'], sr=SR_A, hop_length=HOP, units='time', backtrack=True)
    oth = cells_to_notes(grid, to, mo, ro, oo, min_rms=e['other'] * 0.5)
    if lead_src == 'other' or (lead_src == 'auto' and e['vocals'] < 0.02):
        lead = oth
        inst = []
    else:
        lead = voc
        busy = np.zeros(len(grid), bool)
        for n in voc:
            busy[max(0, n['start'] - 8): n['end'] + 8] = True
        inst = [n for n in oth if not busy[n['start']:n['end']].any()]
    lead = octave_fix(lead, 74)   # 레트로 리드 음역 (D5 근처)
    inst = octave_fix(inst, 76)

    # --- 베이스
    tb, mb, pb, rb = f0_track(stems['bass'], 30, 330)
    ob = librosa.onset.onset_detect(y=stems['bass'], sr=SR_A, hop_length=HOP, units='time', backtrack=True)
    bass = octave_fix(cells_to_notes(grid, tb, mb, rb, ob, min_rms=e['bass'] * 0.3), 41)

    chords = chord_per_beat(stems['other'] + stems['bass'] * 0.3, beats)
    drums = drum_hits(stems['drums'], grid)

    # 마디별 세기 (원곡의 조용한 부분/센 부분 따라가기)
    mrms = librosa.feature.rms(y=mix, hop_length=HOP)[0]
    mt = librosa.times_like(mrms, sr=SR_A, hop_length=HOP)
    beat_db = np.array([mrms[(mt >= beats[i]) & (mt < beats[i + 1])].mean() if i + 1 < len(beats) else mrms[-1]
                        for i in range(len(beats))])
    loud = np.clip(beat_db / np.percentile(beat_db, 90), 0.25, 1.0)
    print(f'lead notes {len(lead)}  inst notes {len(inst)}  bass notes {len(bass)}  '
          f'kick {len(drums["k"])} snare {len(drums["s"])} hat {len(drums["h"])}')
    return lead, inst, bass, chords, drums, grid, beats, loud


def render_all(mix, lead, inst, bass, chords, drums, grid, beats, loud, out_p):

    def loud_at(t):
        i = np.clip(np.searchsorted(beats, t) - 1, 0, len(loud) - 1)
        return float(loud[i])

    # ------------------------------------------------ render
    SR = c.SR
    dur = len(mix) / SR_A
    tr = c.Track(dur)

    def gt(i):
        return grid[min(i, len(grid) - 1)]

    def lead_voice(notes, bus, layers, vib, envp, tail=0.12):
        for n in notes:
            st, en = gt(n['start']), gt(n['end'])
            d = en - st
            N = int((d + tail) * SR)
            gate = int(d * 0.95 * SR)
            v = loud_at(st)
            for osc, duty, o, vol in layers:
                f = c.mtof(n['m'] + 12 * o)
                w = c.pulse(f, N, duty, vib=vib, vib_delay=0.15) if osc == 'pulse' else c.triangle(f, N, vib=vib, vib_delay=0.15)
                tr.add(bus, st, w * c.env(N, gate=gate, **envp) * vol * v)

    lead_voice(lead, 'lead', [('pulse', 0.25, 0, 0.2), ('pulse', 0.125, 1, 0.035)], 0.25,
               dict(a=0.004, d=0.15, s=0.7, r=0.06))
    lead_voice(inst, 'lead', [('pulse', 0.5, 0, 0.13)], 0.15, dict(a=0.003, d=0.1, s=0.5, r=0.05))

    for n in bass:
        st, en = gt(n['start']), gt(n['end'])
        N = int((en - st) * SR)
        w = c.triangle(c.mtof(n['m']), N) * c.env(N, a=0.003, d=0.2, s=0.85, r=0.02, gate=int(N * 0.92))
        tr.add('bass', st, w * 0.32 * max(0.6, loud_at(st)))

    # 화음 → 16분 아르페지오 (12.5% 펄스) + 아주 작은 패드
    pat = [0, 1, 2, 3, 2, 1, 2, 1]
    for j, ch in enumerate(chords):
        if ch is None or j + 1 >= len(beats):
            continue
        root, iv = ch
        base = 12 * 5 + root
        tones = [base + iv[0], base + iv[1], base + iv[2], base + 12]
        b0, b1 = beats[j], beats[j + 1]
        v = loud_at(b0)
        for s in range(4):
            st = b0 + (b1 - b0) * s / 4
            N = int((b1 - b0) / 4 * SR * 0.9)
            m = tones[pat[(j * 4 + s) % len(pat)]]
            tr.add('arp', st, c.pulse(c.mtof(m), N, 0.125) * c.env(N, a=0.002, d=0.05, s=0.35, gate=N) * 0.07 * v)
        N = int((b1 - b0) * SR)
        for i in iv:
            tr.add('pad', b0, c.pulse(c.mtof(12 * 4 + root + i), N, 0.5) * c.env(N, a=0.05, d=0.3, s=0.8, r=0.05, gate=int(N * 0.97)) * 0.022 * v)

    K, Sn, H = c.kick(), c.snare(), c.hat()
    for k, s in drums['k']:
        tr.add('drums', grid[k], K * 0.6 * (0.5 + 0.5 * s))
    for k, s in drums['s']:
        tr.add('drums', grid[k], Sn * 0.3 * (0.4 + 0.6 * s))
    for k, s in drums['h']:
        tr.add('drums', grid[k], H * 0.7 * (0.4 + 0.6 * s))

    song = dict(echo=0.3)
    st = c.mix(tr, song, (beats[1] - beats[0]) * 4)
    c.write_wav(out_p, st)
    print('wrote', out_p, f'{len(st) / SR:.1f}s')


if __name__ == "__main__":
    main()

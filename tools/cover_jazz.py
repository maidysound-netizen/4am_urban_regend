"""8-bit jazz version: keeps the transcribed melody, rebuilds the band as a jazz combo.

- 7th chords (maj7 / m7 / 7 / m7b5) detected per beat with smoothing, root guided by the original bass
- walking bass: one note per beat, pitch taken from the original bass line
- jazz drums: ride cymbal (swing or straight, measured from the original), hi-hat on 2 & 4,
  soft feathered kick, snare comping where the original drummer hits
- comping: rootless 7th-chord voicings on the rhythm of the original backing instruments

usage: python cover_jazz.py N   (uses src/oN.wav, stems/htdemucs/oN, cover/cN.wav.pkl → jazz/jN.wav)
"""
import os, sys, pickle, numpy as np, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiptune as c
from cover8bit import load, SR_A, HOP

QUALS = {'maj7': (0, 4, 7, 11), 'm7': (0, 3, 7, 10), '7': (0, 4, 7, 10), 'm7b5': (0, 3, 6, 10)}
NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def onset_phases(y, beats, lo=0):
    if lo:
        S = np.abs(librosa.stft(y, hop_length=128))
        fr = librosa.fft_frequencies(sr=SR_A)
        env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[fr > lo]), sr=SR_A, hop_length=128)
        on = librosa.onset.onset_detect(onset_envelope=env, sr=SR_A, hop_length=128, units='time')
    else:
        on = librosa.onset.onset_detect(y=y, sr=SR_A, hop_length=128, units='time')
    i = np.searchsorted(beats, on) - 1
    ok = (i >= 0) & (i < len(beats) - 1)
    return on[ok], i[ok], (on[ok] - beats[i[ok]]) / (beats[i[ok] + 1] - beats[i[ok]])


def main():
    f = sys.argv[1]
    lead, inst, bass_n, _, _, grid, beats, loud = pickle.load(open(f'cover/c{f}.wav.pkl', 'rb'))
    mix = load(f'src/o{f}.wav')
    st = {k: load(f'stems/htdemucs/o{f}/{k}.wav') for k in ('drums', 'other', 'bass')}

    # ---- 1. 박자 보정 + 스윙 비율 (원곡 드럼/반주에서 측정)
    _, _, ph = onset_phases(st['drums'], beats, lo=5000)
    late = ph[ph > 0.85] - 1
    shift = float(np.median(late)) if len(late) > 20 else 0.0      # 박 단위 (음수 = 원래 박이 더 앞)
    ib = np.median(np.diff(beats))
    beats = beats + shift * ib
    grid = grid + shift * ib
    _, _, ph = onset_phases(st['drums'], beats, lo=5000)
    mid = ph[(ph > 0.4) & (ph < 0.85)]
    ratio = float(np.median(mid)) if len(mid) > 30 else 0.5
    swing = ratio > 0.58
    r = min(ratio, 0.69) if swing else 0.5
    print(f'track {f}: beat shift {shift * ib * 1000:.0f} ms, off-beat at {ratio:.2f} → {"SWING" if swing else "straight"} r={r:.2f}')

    nb = len(beats) - 1

    def T(bi, frac):
        """박 bi 안의 위치 frac(0~1, 정박 기준)을 스윙을 반영한 실제 시간으로."""
        bi = int(np.clip(bi, 0, nb - 1))
        g = frac * 2 * r if frac <= 0.5 else r + (frac - 0.5) * 2 * (1 - r)
        return beats[bi] + g * (beats[bi + 1] - beats[bi])

    # ---- 2. 원곡 베이스 음 (박마다)
    cell_pitch = {}
    for n in bass_n:
        for k in range(n['start'], n['end']):
            cell_pitch[k] = n['m']
    gi = np.searchsorted(grid, beats[:-1] - 0.03)   # 각 박이 시작하는 grid 셀

    def bass_pc(bi):
        for k in range(gi[bi], gi[bi] + 2):
            if k in cell_pitch:
                return cell_pitch[k] % 12
        return None

    # ---- 3. 7th 코드 (박마다, Viterbi로 부드럽게)
    harm = librosa.effects.harmonic(st['other'] + 0.5 * st['bass'])
    chroma = librosa.feature.chroma_cqt(y=harm, sr=SR_A, hop_length=HOP)
    fr = np.clip(librosa.time_to_frames(beats, sr=SR_A, hop_length=HOP), 0, chroma.shape[1] - 1)
    sync = librosa.util.sync(chroma, fr, aggregate=np.median)[:, :nb]
    labels, T_ = [], []
    for root in range(12):
        for q, iv in QUALS.items():
            v = np.zeros(12)
            for k, i in enumerate(iv):
                v[(root + i) % 12] = (1.3, 1.0, 0.8, 0.6)[k]
            labels.append((root, q))
            T_.append(v / np.linalg.norm(v))
    T_ = np.array(T_)
    em = T_ @ (sync / (np.linalg.norm(sync, axis=0) + 1e-9))
    for bi in range(nb):
        pc = bass_pc(bi)
        if pc is not None:
            em[[k for k, (rt, _) in enumerate(labels) if rt == pc], bi] += 0.12
    L = len(labels)
    change = 0.18
    score = em[:, 0].copy()
    back = np.zeros((nb, L), int)
    for bi in range(1, nb):
        best = int(np.argmax(score))
        stay = score
        move = score[best] - change
        back[bi] = np.where(stay >= move, np.arange(L), best)
        score = np.maximum(stay, move) + em[:, bi]
    path = [int(np.argmax(score))]
    for bi in range(nb - 1, 0, -1):
        path.append(back[bi, path[-1]])
    path = path[::-1]
    chords = [labels[k] for k in path]

    # 마디 시작(1박) 찾기: 코드가 바뀌는 위치가 가장 많이 몰리는 위상
    ch_idx = [bi for bi in range(1, nb) if chords[bi] != chords[bi - 1]]
    phase = int(np.argmax([sum(1 for b in ch_idx if b % 4 == p) for p in range(4)]))
    beat_in_bar = [(bi - phase) % 4 for bi in range(nb)]

    seq = []
    for bi in range(0, nb, 4):
        lab = chords[bi]
        s = f'{NAMES[lab[0]]}{lab[1]}'
        if not seq or seq[-1] != s:
            seq.append(s)
    print('  chords:', ' '.join(seq[:28]), '...')

    # 각 박의 세기 (드럼/반주가 원곡에서 쉬는 곳은 쉬게)
    def stem_beat_rms(y):
        rm = librosa.feature.rms(y=y, hop_length=HOP)[0]
        t = librosa.times_like(rm, sr=SR_A, hop_length=HOP)
        v = np.array([rm[(t >= beats[i]) & (t < beats[i + 1])].mean() if np.any((t >= beats[i]) & (t < beats[i + 1])) else 0
                      for i in range(nb)])
        return v / (np.percentile(v, 90) + 1e-9)
    drum_on = stem_beat_rms(st['drums'])
    comp_on = stem_beat_rms(st['other'])
    bass_on = stem_beat_rms(st['bass'])
    loud_b = np.asarray(loud)[:nb]

    SR = c.SR
    tr = c.Track(len(mix) / SR_A)
    beat_len = lambda bi: beats[min(bi + 1, nb)] - beats[bi]

    # ---- 멜로디: melody.py가 보컬에서 뽑은 음 (초 단위). 박자 칸에 가까우면 살짝 맞춘다
    snaps = []
    for bi in range(nb):
        snaps += [T(bi, q) for q in (0, 0.25, 0.5, 0.75)]
        if swing:
            snaps += [beats[bi] + beat_len(bi) * q for q in (1 / 3, 2 / 3)]
    snaps = np.sort(np.array(snaps + [beats[-1]]))

    def snap(t):
        k = np.clip(np.searchsorted(snaps, t), 1, len(snaps) - 1)
        near = snaps[k] if abs(snaps[k] - t) < abs(snaps[k - 1] - t) else snaps[k - 1]
        return near if abs(near - t) < 0.035 else t

    mel = pickle.load(open(f'mel/m{f}.pkl', 'rb'))
    lead = []
    for n in mel:
        s0, e0 = snap(n['t0']), snap(n['t1'])
        if e0 - s0 > 0.05:
            lead.append(dict(s0=s0, e0=e0, m=n['m']))
    inst = []

    def lead_voice(notes, layers, vib, envp, tail=0.1):
        for n in notes:
            s0, e0 = n['s0'], n['e0']
            d = e0 - s0
            N = int((d + tail) * SR)
            bi = int(np.clip(np.searchsorted(beats, s0) - 1, 0, nb - 1))
            for osc, duty, o, vol in layers:
                fq = c.mtof(n['m'] + 12 * o)
                w = c.pulse(fq, N, duty, vib=vib, vib_delay=0.15) if osc == 'pulse' else c.triangle(fq, N, vib=vib, vib_delay=0.15)
                tr.add('lead', s0, w * c.env(N, gate=int(d * 0.95 * SR), **envp) * vol * loud_b[bi])

    lead_voice(lead, [('pulse', 0.25, 0, 0.2), ('pulse', 0.125, 1, 0.03)], 0.3, dict(a=0.004, d=0.15, s=0.7, r=0.06))
    lead_voice(inst, [('pulse', 0.5, 0, 0.12)], 0.2, dict(a=0.003, d=0.12, s=0.45, r=0.05))

    # ---- 워킹 베이스
    prev = 40
    for bi in range(nb):
        if bass_on[bi] < 0.12:
            continue
        root, q = chords[bi]
        iv = QUALS[q]
        pc = bass_pc(bi)
        if pc is None:
            # 원곡 음을 못 잡았으면: 다음 박 코드로 반음 접근, 아니면 코드 톤을 차례로
            nxt = chords[min(bi + 1, nb - 1)][0]
            if beat_in_bar[bi] == 3 and nxt != root:
                pc = (nxt + (1 if (bi % 2) else -1)) % 12
            else:
                pc = (root + iv[beat_in_bar[bi] % 4]) % 12
        cands = [pc + 12 * o for o in range(2, 5)]
        cands = [m for m in cands if 31 <= m <= 52] or cands
        m = min(cands, key=lambda x: abs(x - prev))
        prev = m
        d = beat_len(bi)
        N = int(d * SR)
        acc = 1.0 if beat_in_bar[bi] in (0, 2) else 0.85
        has_off = any(k in cell_pitch and (k - 1 not in cell_pitch or cell_pitch[k - 1] != cell_pitch[k]) for k in (gi[bi] + 2, gi[bi] + 3))
        gate = int((T(bi, 0.5) - beats[bi]) * SR * 0.9) if has_off else int(N * 0.8)
        w = c.triangle(c.mtof(m), N) * c.env(N, a=0.004, d=0.18, s=0.6, r=0.03, gate=gate)
        tr.add('bass', beats[bi], w * 0.34 * acc)
        # 원곡 베이스가 뒷박에 다른 음을 치면 그 음도 친다 (스윙이면 스윙 위치에)
        off = next((cell_pitch[k] % 12 for k in (gi[bi] + 2, gi[bi] + 3) if k in cell_pitch
                    and (k - 1 not in cell_pitch or cell_pitch[k - 1] != cell_pitch[k])), None)
        if off is not None and off != m % 12:
            t0 = T(bi, 0.5)
            m2 = min([off + 12 * o for o in range(2, 5)], key=lambda x: abs(x - m))
            N2 = int((beats[bi + 1] - t0) * SR)
            tr.add('bass', t0, c.triangle(c.mtof(m2), N2) * c.env(N2, a=0.003, d=0.1, s=0.5, gate=int(N2 * 0.8)) * 0.27)
            prev = m2

    # ---- 재즈 드럼
    rng = np.random.default_rng(7)
    seq93 = rng.choice([-1.0, 1.0], 93)

    def metal(n, hold, decay):
        x = np.tile(seq93, n // 93 + 2)
        x = np.repeat(x, hold)[:n]
        x = np.diff(np.concatenate([[0], x]))
        t = np.arange(n) / SR
        return x * np.exp(-t * decay)

    ride = metal(int(0.45 * SR), 1, 9) * 0.16
    ride_bell = metal(int(0.3 * SR), 1, 14) * 0.11
    chick = np.diff(np.concatenate([[0], c.noise(int(0.05 * SR))])) * np.exp(-np.arange(int(0.05 * SR)) / SR * 70) * 0.16
    kick = c.kick()
    snare = c.snare()

    _, k_bi, k_ph = onset_phases(st['drums'], beats, lo=0)
    hits = {}
    for bi_, p in zip(k_bi, k_ph):
        hits.setdefault(int(bi_), []).append(p)
    S = np.abs(librosa.stft(st['drums'], n_fft=1024, hop_length=HOP))
    frq = librosa.fft_frequencies(sr=SR_A, n_fft=1024)
    sn_env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[(frq > 150) & (frq < 400)] + S[(frq > 1500) & (frq < 4000)].mean(0)), sr=SR_A, hop_length=HOP)
    kk_env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[frq < 110]), sr=SR_A, hop_length=HOP)
    sn_on = librosa.onset.onset_detect(onset_envelope=sn_env, sr=SR_A, hop_length=HOP, units='time', delta=0.35)
    kk_on = librosa.onset.onset_detect(onset_envelope=kk_env, sr=SR_A, hop_length=HOP, units='time', delta=0.4)

    def snap8(t):
        bi = int(np.clip(np.searchsorted(beats, t) - 1, 0, nb - 1))
        p = (t - beats[bi]) / beat_len(bi)
        # 가장 가까운 8분 위치: 정박(0) / 뒷박(스윙이면 r) / 다음 정박(1)
        best = min(((0, 0.0), (r, 0.5), (1, 1.0)), key=lambda o: abs(o[0] - p))[1]
        return (bi + 1, 0.0) if best == 1.0 else (bi, best)

    for bi in range(nb):
        if drum_on[bi] < 0.15:
            continue
        v = 0.6 + 0.4 * min(1, drum_on[bi])
        bb = beat_in_bar[bi]
        tr.add('drums', beats[bi], (ride_bell if bb == 0 else ride) * v)
        if swing:
            if bb in (1, 3):
                tr.add('drums', T(bi, 0.5), ride * 0.7 * v)
        else:
            tr.add('drums', T(bi, 0.5), ride * 0.6 * v)
        if bb in (1, 3):
            tr.add('drums', beats[bi], chick * v)
        tr.add('drums', beats[bi], kick * 0.12)  # feathering
    for t in kk_on:
        bi, p = snap8(t)
        if bi < nb and drum_on[bi] >= 0.15:
            tr.add('drums', T(bi, p), kick * 0.42)
    for t in sn_on:
        bi, p = snap8(t)
        if bi < nb and drum_on[bi] >= 0.15:
            tr.add('drums', T(bi, p), snare * (0.22 if beat_in_bar[bi] in (1, 3) and p == 0 else 0.12))

    # ---- 컴핑 (루트 없는 7th 보이싱, 원곡 반주 리듬 따라)
    def voicing(root, q):
        iv = QUALS[q]
        tones = [(root + iv[1]) % 12, (root + iv[2]) % 12, (root + iv[3]) % 12]  # 3, 5, 7
        out = []
        for pc in tones:
            m = 52 + ((pc - 52) % 12)   # E3~D#4 구간
            out.append(m)
        return sorted(out)

    on_t, o_bi, o_ph = onset_phases(st['other'], beats)
    comp_hits = []
    for bi_, p in zip(o_bi, o_ph):
        bi_ = int(bi_)
        if p < 0.2:
            comp_hits.append((bi_, 0.0))
        elif abs(p - r) < 0.15 or abs(p - 0.5) < 0.12:
            comp_hits.append((bi_, 0.5))
        elif p > 0.85:
            comp_hits.append((bi_ + 1, 0.0))
    comp_hits = sorted(set(h for h in comp_hits if h[0] < nb))
    # 너무 촘촘하면 덜어낸다 (마디당 최대 4번)
    keep, per_bar = [], {}
    for h in comp_hits:
        bar = (h[0] - phase) // 4
        if per_bar.get(bar, 0) < 4:
            keep.append(h)
            per_bar[bar] = per_bar.get(bar, 0) + 1
    for i, (bi, p) in enumerate(keep):
        if comp_on[bi] < 0.15:
            continue
        t0 = T(bi, p)
        nxt = T(*keep[i + 1]) if i + 1 < len(keep) else t0 + beat_len(bi)
        d = min(nxt - t0, beat_len(bi) * 1.5)
        N = int(d * SR)
        # 4박 뒷박에서 치면 다음 마디 코드를 미리 친다 (재즈식 앞당김)
        anticip = p == 0.5 and beat_in_bar[bi] == 3
        root, q = chords[min(bi + 1, nb - 1)] if anticip else chords[bi]
        for m in voicing(root, q):
            w = c.pulse(c.mtof(m), N, 0.5) * c.env(N, a=0.003, d=0.22, s=0.35, r=0.04, gate=int(N * 0.85))
            tr.add('arp', t0, w * 0.035 * min(1, comp_on[bi] + 0.3))

    st_ = c.mix(tr, dict(echo=0.22), ib * 4)
    os.makedirs('jazz', exist_ok=True)
    c.write_wav(f'jazz/j{f}.wav', st_)
    print(f'  wrote jazz/j{f}.wav {len(st_) / SR:.1f}s')


main()

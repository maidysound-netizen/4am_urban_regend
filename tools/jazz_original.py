"""'4 A.M. Jazz Club' — an original 8-bit jazz tune for 4 A.M. Urban Legend.

F minor, medium swing. Form: intro (4) / head AABA (32) / solo chorus (32) / head out with
horn harmony (32) / ending (3).
Band: pulse-wave lead, triangle walking bass, rootless 7th-chord comping, swing drums.

usage: python jazz_original.py OUT.wav
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiptune as c

BPM = 132
SWING = 0.66          # 뒷박 위치 (0.5 = 정박, 0.67 = 셋잇단 스윙)
BT = 60 / BPM         # 한 박 길이(초)
SR = c.SR
rng = np.random.default_rng(404)

QUAL = {'m7': (0, 3, 7, 10), 'maj7': (0, 4, 7, 11), '7': (0, 4, 7, 10), 'm7b5': (0, 3, 6, 10), 'm6': (0, 3, 7, 9)}
F_MINOR = {5, 7, 8, 10, 0, 1, 3}
C_PHRYG_DOM = {0, 1, 4, 5, 7, 8, 10}


def parse_chord(name):
    pc = c.PC[name[0]]
    i = 1
    if len(name) > 1 and name[1] in 'b#':
        pc += -1 if name[1] == 'b' else 1
        i = 2
    return pc % 12, name[i:]


def scale_of(ch):
    root, q = parse_chord(ch)
    return C_PHRYG_DOM if (root == 0 and q == '7') else F_MINOR


# ------------------------------------------------------------------ form
# 마디마다 [(코드, 박수), ...]
def bars(*spec):
    out = []
    for b in spec:
        if isinstance(b, str):
            out.append([(b, 4)])
        else:
            out.append([(b[0], 2), (b[1], 2)])
    return out


A1 = bars('Fm7', 'Fm7', 'Dbmaj7', 'C7', 'Fm7', ('Bbm7', 'Eb7'), 'Abmaj7', ('Gm7b5', 'C7'))
A2 = bars('Fm7', 'Fm7', 'Dbmaj7', 'C7', 'Fm7', ('Bbm7', 'Eb7'), 'Abmaj7', 'Fm7')
B = bars('Bbm7', 'Eb7', 'Abmaj7', 'Dbmaj7', 'Gm7b5', 'C7', 'Fm7', ('Gm7b5', 'C7'))
A3 = A2[:7] + bars(('Gm7b5', 'C7'))     # 다음 코러스로 넘어가는 A
CHORUS = A1 + A2 + B + A3
CHORUS_LAST = A1 + A2 + B + A2
INTRO = bars('Fm7', 'Fm7', ('Gm7b5', 'C7'), ('Gm7b5', 'C7'))
ENDING = bars('Fm6', 'Fm6', 'Fm6')

# 멜로디 (16분음표 단위 길이, 스윙은 렌더링할 때 적용)
MEL_A = ('r:2 C5:2 Eb5:2 F5:2 Ab5:4 G5:2 F5:2 '
         'Eb5:2 C5:2 r:4 r:2 Ab4:2 Bb4:2 C5:2 '
         'Db5:6 F5:2 Ab5:2 C6:4 Ab5:2 '
         'G5:4 E5:2 Db5:2 Bb4:4 G4:4 '
         'r:2 C5:2 Eb5:2 F5:2 Ab5:2 Bb5:2 C6:4 '
         'Db6:4 C6:2 Bb5:2 G5:4 Eb5:4 '
         'C6:6 Bb5:2 Ab5:2 G5:2 Eb5:4 ')
MEL_A1 = MEL_A + 'F5:4 Db5:4 E5:4 r:4'
MEL_A2 = MEL_A + 'F5:12 r:4'
MEL_B = ('r:2 F5:2 Ab5:2 Bb5:2 Db6:6 C6:2 '
         'Bb5:4 G5:2 Eb5:2 Db5:8 '
         'r:2 Eb5:2 G5:2 Bb5:2 C6:6 Bb5:2 '
         'Ab5:4 F5:2 C5:2 F5:8 '
         'r:2 G5:2 Bb5:2 Db6:2 F6:4 Eb6:2 Db6:2 '
         'C6:2 Bb5:2 G5:2 E5:2 Db5:4 E5:4 '
         'F5:4 Ab5:4 C6:4 Eb6:4 '
         'Db6:4 C6:2 Bb5:2 G5:4 E5:4')
HEAD = MEL_A1 + ' ' + MEL_A2 + ' ' + MEL_B + ' ' + MEL_A1
HEAD_LAST = MEL_A1 + ' ' + MEL_A2 + ' ' + MEL_B + ' ' + MEL_A2


def parse_mel(s, start_beat):
    out, pos = [], 0
    for tok in s.split():
        name, ln = tok.split(':')
        ln = int(ln)
        if name != 'r':
            out.append(dict(b0=start_beat + pos / 4, b1=start_beat + (pos + ln) / 4, m=c.note_midi(name)))
        pos += ln
    return out, pos / 4


# ------------------------------------------------------------------ time
def t_of(b, straight=False):
    """박 위치 b(0부터) → 초. 8분 뒷박은 스윙 위치로 민다."""
    bi = np.floor(b + 1e-9)
    fr = b - bi
    if not straight:
        fr = fr * 2 * SWING if fr <= 0.5 else SWING + (fr - 0.5) * 2 * (1 - SWING)
    return float((bi + fr) * BT)


# ------------------------------------------------------------------ parts
def chord_timeline(sections):
    tl, b = [], 0.0
    for sec in sections:
        for bar in sec:
            for ch, n in bar:
                tl.append((b, n, ch))
                b += n
    return tl, b


def walking_bass(tl):
    """박마다 한 음. 1박은 근음, 마지막 박은 다음 근음으로 반음 접근, 가운데는 그 사이를 걸어간다."""
    lo, hi = 28, 52
    notes, prev = [], 41

    def near(pc, ref):
        return min((pc + 12 * o for o in range(1, 6) if lo <= pc + 12 * o <= hi), key=lambda x: abs(x - ref))

    for i, (b0, n, ch) in enumerate(tl):
        root, q = parse_chord(ch)
        chord_pcs = {(root + x) % 12 for x in QUAL[q]}
        pool = chord_pcs | scale_of(ch)
        r = near(root, prev)
        if i + 1 < len(tl):
            nr = near(parse_chord(tl[i + 1][2])[0], r)
            if nr == r:                       # 같은 코드가 이어지면 한 옥타브를 걸어 올라가거나 내려간다
                nr = r + 12 if r + 12 <= hi else r - 12
            a = nr + (1 if nr < r else -1)
            if a == r:                        # 접근음이 지금 근음과 같으면 반대쪽에서 접근
                a = nr - (1 if nr < r else -1)
        else:
            a = r + 2
        line = [r]
        if n == 4:
            used = {r, a, nr if i + 1 < len(tl) else -1}
            for frac in (1 / 3, 2 / 3):
                goal = r + (a - r) * frac
                cands = [m for m in range(lo, hi + 1) if m % 12 in pool and m not in used and m != line[-1]]
                # 2박째는 코드 톤 우선
                cands.sort(key=lambda m: abs(m - goal) - (0.6 if (frac < 0.5 and m % 12 in chord_pcs) else 0))
                line.append(cands[0])
                used.add(cands[0])
        if n >= 2:
            line.append(a if a != line[-1] else a + 2)
        for k, m in enumerate(line):
            notes.append(dict(b0=b0 + k, b1=b0 + k + 1, m=m))
        prev = line[-1]
        # 가끔 스윙 '스킵' 8분음표 (마지막 박을 둘로)
        if n >= 2 and rng.random() < 0.12:
            notes[-1]['b1'] = b0 + n - 0.5
            notes.append(dict(b0=b0 + n - 0.5, b1=b0 + n, m=notes[-1]['m']))
    return notes


VOICE = {'m7': (3, 7, 10, 14), '7': (4, 9, 10, 14), 'maj7': (4, 7, 11, 14), 'm7b5': (3, 6, 10, 12), 'm6': (3, 7, 9, 14)}


def voicing(ch):
    root, q = parse_chord(ch)
    ms = sorted(53 + ((root + i - 53) % 12) for i in VOICE[q])
    return ms


COMP_RHYTHMS = [[0, 1.5], [1.5, 3.5], [0.5, 2.5], [0, 2.5], [1.5], [2.5, 3.5], [0]]


def comping(sections_bars, start_beat=0.0, busy=1.0):
    hits, b = [], start_beat
    for bar in sections_bars:
        bar_chords = []
        x = 0
        for ch, n in bar:
            bar_chords.append((x, x + n, ch))
            x += n
        rhythm = COMP_RHYTHMS[rng.integers(0, len(COMP_RHYTHMS))]
        if busy < 1 and rng.random() > busy:
            rhythm = rhythm[:1]
        for p in rhythm:
            ch = next(cc for s, e, cc in bar_chords if s <= p < e)
            dur = 0.45 if p % 1 else 0.9
            hits.append(dict(b=b + p, d=dur, ch=ch))
        b += 4
    return hits


def solo(tl_bars, start_beat):
    """한 코러스 즉흥 솔로: 2마디 프레이즈, 8분음표 위주, 강박엔 코드 톤."""
    notes, b, cur = [], start_beat, 72
    flat = []  # (beat, chord) per 8th
    for bar in tl_bars:
        for ch, n in bar:
            for k in range(n * 2):
                flat.append((b + k / 2, ch))
            b += n
    i = 0
    direction = 1
    while i < len(flat):
        phrase_len = int(rng.integers(7, 13))
        start_gap = int(rng.integers(0, 3))
        i += start_gap
        end = min(i + phrase_len, len(flat))
        while i < end:
            beat, ch = flat[i]
            root, q = parse_chord(ch)
            chord_pcs = {(root + x) % 12 for x in QUAL[q]}
            sc = scale_of(ch)
            strong = (i % 2 == 0)
            step = direction * (1 if rng.random() < 0.7 else 3)
            target = cur + step
            pool = chord_pcs if strong else sc
            m = target
            for d in range(0, 6):
                for s in (direction, -direction):
                    cand = target + s * d
                    if cand % 12 in pool:
                        m = cand
                        break
                else:
                    continue
                break
            if m == cur:                         # 같은 음 반복은 피하고 한 칸 더 간다
                m += direction
                while m % 12 not in pool:
                    m += direction
            if m > 86 or m < 64:
                direction *= -1
                m = cur - 2 if m > 86 else cur + 2
                while m % 12 not in sc:
                    m += -1 if m > 75 else 1
            if rng.random() < 0.15:
                direction *= -1
            last = (i == end - 1)
            ln = 1.0 if (last or rng.random() < 0.12) else 0.5
            if last:
                while m % 12 not in chord_pcs:
                    m += -direction
            notes.append(dict(b0=beat, b1=beat + ln, m=m))
            cur = m
            i += 2 if ln == 1.0 else 1
        # 프레이즈 사이 쉼 (2마디 단위로 맞춘다)
        i = ((i // 16) + 1) * 16 if i % 16 > 10 else i + int(rng.integers(2, 5))
    return notes


def harmony_line(mel, tl):
    out = []
    for n in mel:
        ch = next(ch for b0, ln, ch in tl if b0 <= n['b0'] < b0 + ln)
        root, q = parse_chord(ch)
        chord_pcs = {(root + x) % 12 for x in QUAL[q]}
        sc = scale_of(ch)
        h = None
        for d in (3, 4, 5):
            if (n['m'] - d) % 12 in chord_pcs:
                h = n['m'] - d
                break
        if h is None:
            for d in (3, 4):
                if (n['m'] - d) % 12 in sc:
                    h = n['m'] - d
                    break
        if h is not None:
            out.append(dict(b0=n['b0'], b1=n['b1'], m=h))
    return out


# ------------------------------------------------------------------ drums
seq93 = np.random.default_rng(93).choice([-1.0, 1.0], 93)


def metal(n, hold, decay):
    x = np.repeat(np.tile(seq93, n // 93 + 2), hold)[:n]
    x = np.diff(np.concatenate([[0], x]))
    return x * np.exp(-np.arange(n) / SR * decay)


RIDE = metal(int(0.5 * SR), 1, 8) * 0.15
CRASH = metal(int(1.6 * SR), 2, 2.2) * 0.2
CHICK = np.diff(np.concatenate([[0], c.noise(int(0.05 * SR))])) * np.exp(-np.arange(int(0.05 * SR)) / SR * 70) * 0.15
KICK = c.kick()
SNARE = c.snare()


def drums(tr, n_bars, start_beat, fills_every=8, crash_at=(), sparse=False):
    for bar in range(n_bars):
        b = start_beat + bar * 4
        fill = (bar % fills_every == fills_every - 1)
        for k in range(4):
            if fill and k >= 2:
                continue
            tr.add('drums', t_of(b + k), RIDE * (1.0 if k in (0, 2) else 0.85))
            if k in (1, 3):
                tr.add('drums', t_of(b + k + 0.5), RIDE * 0.6)
                tr.add('drums', t_of(b + k), CHICK)
            tr.add('drums', t_of(b + k), KICK * 0.1)           # 깃털처럼 가볍게
        if not sparse:
            for k in range(8):                                  # 스네어 고스트 노트
                if k % 2 == 1 and rng.random() < 0.18:
                    tr.add('drums', t_of(b + k / 2), SNARE * 0.07)
            if rng.random() < 0.25:                              # 가끔 '폭탄' 킥
                tr.add('drums', t_of(b + 3.5), KICK * 0.4)
        if fill:                                                 # 셋잇단 스네어 필
            for j in range(6):
                tr.add('drums', t_of(b + 2 + j / 3, straight=True), SNARE * (0.1 + 0.035 * j))
            tr.add('drums', t_of(b + 4), KICK * 0.45)
    for cb in crash_at:
        tr.add('drums', t_of(cb), CRASH)
        tr.add('drums', t_of(cb), KICK * 0.5)


# ------------------------------------------------------------------ render
def play_notes(tr, bus, notes, layers, vib, envp, vol=1.0, tail=0.1, legato=0.92):
    for n in notes:
        s0, e0 = t_of(n['b0']), t_of(n['b1'])
        d = e0 - s0
        N = int((d + tail) * SR)
        for osc, duty, o, v in layers:
            f = c.mtof(n['m'] + 12 * o)
            w = c.pulse(f, N, duty, vib=vib, vib_delay=0.18) if osc == 'pulse' else c.triangle(f, N, vib=vib, vib_delay=0.18)
            tr.add(bus, s0, w * c.env(N, gate=int(d * legato * SR), **envp) * v * vol * n.get('v', 1))


def main(out):
    sections = [INTRO, CHORUS, CHORUS, CHORUS_LAST, ENDING]
    tl, total_beats = chord_timeline(sections)
    tr = c.Track(t_of(total_beats) + 3)

    b_head1 = 16
    b_solo = b_head1 + 128
    b_head2 = b_solo + 128
    b_end = b_head2 + 128

    head1, _ = parse_mel(HEAD, b_head1)
    head2, _ = parse_mel(HEAD_LAST, b_head2)
    sol = solo(CHORUS, b_solo)
    harm = harmony_line(head2, tl)

    lead_layers = [('pulse', 0.25, 0, 0.19), ('pulse', 0.125, 1, 0.03)]
    lead_env = dict(a=0.006, d=0.2, s=0.65, r=0.07)
    play_notes(tr, 'lead', head1, lead_layers, 0.3, lead_env)
    play_notes(tr, 'lead', sol, [('pulse', 0.125, 0, 0.2)], 0.15, dict(a=0.003, d=0.1, s=0.55, r=0.05), legato=0.85)
    play_notes(tr, 'lead', head2, lead_layers, 0.3, lead_env)
    play_notes(tr, 'harm', harm, [('pulse', 0.5, 0, 0.11)], 0.25, lead_env)

    # 엔딩: Fm6/9 화음을 아래에서 위로 펼쳐 치고 길게
    end_notes = [c.note_midi(x) for x in ('F4', 'Ab4', 'C5', 'D5', 'G5', 'C6')]
    for k, m in enumerate(end_notes):
        b0 = b_end + k * 0.25
        play_notes(tr, 'lead', [dict(b0=b0, b1=b_end + 10, m=m, v=0.8)], [('pulse', 0.25, 0, 0.12)], 0.35,
                   dict(a=0.01, d=1.2, s=0.4, r=1.0), tail=1.2)

    bass = walking_bass([x for x in tl if x[0] < b_end])
    for n in bass:
        s0, e0 = t_of(n['b0']), t_of(n['b1'])
        N = int((e0 - s0) * SR)
        w = c.triangle(c.mtof(n['m']), N) * c.env(N, a=0.004, d=0.2, s=0.6, r=0.03, gate=int(N * 0.85))
        tr.add('bass', s0, w * 0.33)
    N = int(t_of(10) * SR)  # 엔딩 베이스 F 길게
    tr.add('bass', t_of(b_end), c.triangle(c.mtof(29), N) * c.env(N, a=0.004, d=1.5, s=0.3, r=1.0, gate=N // 2) * 0.33)

    comp = (comping(INTRO, 0, busy=0.6) + comping(CHORUS, b_head1, busy=0.7)
            + comping(CHORUS, b_solo, busy=1.0) + comping(CHORUS_LAST, b_head2, busy=0.8))
    for h in comp:
        s0 = t_of(h['b'])
        d = h['d'] * BT
        N = int(d * SR)
        for m in voicing(h['ch']):
            w = c.pulse(c.mtof(m), N, 0.5) * c.env(N, a=0.003, d=0.15, s=0.3, r=0.05, gate=int(N * 0.8))
            tr.add('arp', s0, w * 0.04)

    drums(tr, 4, 0, fills_every=4, sparse=True)
    drums(tr, 32, b_head1, crash_at=[b_head1])
    drums(tr, 32, b_solo, crash_at=[b_solo])
    drums(tr, 32, b_head2, crash_at=[b_head2, b_end])

    st = c.mix(tr, dict(echo=0.18), BT * 4)
    c.write_wav(out, st)
    print(f'wrote {out}: {len(st) / SR:.1f}s, {len(head1)} head notes, {len(sol)} solo notes, {len(bass)} bass notes, {len(comp)} comp hits')


main(sys.argv[1])

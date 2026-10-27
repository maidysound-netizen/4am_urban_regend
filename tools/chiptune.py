"""Tiny NES-style chiptune renderer + three original songs for 4 A.M. Urban Legend.

Moods/keys/tempos are taken from the reference tracks; every melody here is newly written.
Usage: python chiptune.py OUTDIR
"""
import sys, wave, numpy as np

SR = 44100
PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def note_midi(s):
    pc = PC[s[0]]
    i = 1
    while i < len(s) and s[i] in '#b':
        pc += 1 if s[i] == '#' else -1
        i += 1
    return pc + 12 * (int(s[i:]) + 1)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def chord_tones(name):
    pc = PC[name[0]]
    i = 1
    if len(name) > 1 and name[1] in '#b':
        pc += 1 if name[1] == '#' else -1
        i = 2
    minor = name[i:] == 'm'
    return pc % 12, [0, 3 if minor else 4, 7]


# ---------------------------------------------------------------- oscillators
def polyblep(t, dt):
    out = np.zeros_like(t)
    a = t < dt
    x = t[a] / dt[a]
    out[a] = x + x - x * x - 1
    b = t > 1 - dt
    x = (t[b] - 1) / dt[b]
    out[b] = x * x + x + x + 1
    return out


def phase_of(freq, n, vib=0.0, vib_delay=0.0):
    f = np.full(n, freq)
    if vib:
        t = np.arange(n) / SR
        depth = np.clip((t - vib_delay) / 0.25, 0, 1) * vib
        f = f * 2 ** (depth * np.sin(2 * np.pi * 5.5 * t) / 12)
    return np.cumsum(f) / SR % 1.0, f / SR


def pulse(freq, n, duty=0.5, **kw):
    p, dt = phase_of(freq, n, **kw)
    v = np.where(p < duty, 1.0, -1.0)
    v += polyblep(p, dt)
    v -= polyblep((p + 1 - duty) % 1.0, dt)
    return v - (2 * duty - 1)  # remove DC


def triangle(freq, n, **kw):
    p, _ = phase_of(freq, n, **kw)
    tri = 2 * np.abs(2 * p - 1) - 1
    return np.round(tri * 7.5) / 7.5  # 4-bit stepped like the NES


def env(n, a=0.005, d=0.08, s=0.6, r=0.05, gate=None):
    gate = n if gate is None else min(gate, n)
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    if gate < n:
        rel = np.exp(-(t[gate:] - t[gate]) / max(r, 1e-6))
        e[gate:] = e[gate - 1] * rel
    return e


rng = np.random.default_rng(4)


def noise(n, hold=1):
    v = rng.choice([-1.0, 1.0], size=n // hold + 1)
    return np.repeat(v, hold)[:n]


# ---------------------------------------------------------------- drums
def kick(n=None):
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30)
    ph = np.cumsum(f) / SR
    return np.sin(2 * np.pi * ph) * np.exp(-t * 14)


def snare():
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    body = triangle(190, n) * np.exp(-t * 30) * 0.5
    return body + noise(n, 2) * np.exp(-t * 22) * 0.7


def hat(open_=False):
    n = int((0.12 if open_ else 0.04) * SR)
    t = np.arange(n) / SR
    x = noise(n, 1)
    x = np.diff(np.concatenate([[0], x]))  # crude high-pass
    return x * np.exp(-t * (25 if open_ else 90)) * 0.35


# ---------------------------------------------------------------- song rendering
class Track:
    def __init__(self, seconds):
        self.n = int(seconds * SR) + SR * 3
        self.buf = {}

    def add(self, bus, start, sig):
        b = self.buf.setdefault(bus, np.zeros(self.n))
        i = int(start * SR)
        if i < 0:
            sig, i = sig[-i:], 0
        j = min(self.n, i + len(sig))
        if i < self.n:
            b[i:j] += sig[: j - i]


def parse_mel(s):
    out = []  # (step, len, midi or None)
    pos = 0
    for tok in s.split():
        name, ln = tok.split(':')
        ln = int(ln)
        out.append((pos, ln, None if name == 'r' else note_midi(name)))
        pos += ln
    return out, pos


def third_below(m, scale):
    for d in (3, 4):
        if (m - d) % 12 in scale:
            return m - d
    return m - 3


def render(song):
    bpm = song['bpm']
    step = 60 / bpm / 4  # 16th note
    bar = step * 16
    total_bars = sum(len(sec['chords']) for sec in song['sections'])
    tr = Track(total_bars * bar)
    scale = {(song['tonic'] + i) % 12 for i in (0, 2, 3, 5, 7, 8, 10)}
    lead = song['lead']
    b0 = 0
    for sec in song['sections']:
        chords = sec['chords']
        t0 = b0 * bar
        # --- lead melody
        if sec.get('mel'):
            notes, length = parse_mel(song['mel'][sec['mel']])
            assert length == 16 * len(chords), (sec['mel'], length)
            for pos, ln, m in notes:
                if m is None:
                    continue
                st = t0 + pos * step
                dur = ln * step
                n = int((dur + lead.get('tail', 0.15)) * SR)
                gate = int(dur * 0.92 * SR)
                for k, (osc, duty, oct_, vol) in enumerate(lead['layers']):
                    f = mtof(m + 12 * oct_)
                    w = (pulse(f, n, duty, vib=lead['vib'], vib_delay=0.18) if osc == 'pulse'
                         else triangle(f, n, vib=lead['vib'], vib_delay=0.18))
                    tr.add('lead', st, w * env(n, gate=gate, **lead['env']) * vol)
                if sec.get('harm'):
                    hm = third_below(m, scale)
                    w = pulse(mtof(hm), n, 0.25) * env(n, gate=gate, **lead['env']) * 0.11
                    tr.add('harm', st, w)
        for ci, ch in enumerate(chords):
            cb = t0 + ci * bar
            root, iv = chord_tones(ch)
            # --- arpeggio
            if sec.get('arp', True):
                pat = song['arp']
                base = 12 * (song['arp_oct'] + 1) + root
                tones = [base + iv[0], base + iv[1], base + iv[2], base + 12]
                rate = song.get('arp_rate', 1)
                for s in range(0, 16, rate):
                    m = tones[pat[(s // rate) % len(pat)]]
                    n = int(step * rate * SR * 0.9)
                    w = pulse(mtof(m), n, 0.125) * env(n, a=0.002, d=0.05, s=0.35, gate=n) * song['arp_vol']
                    tr.add('arp', cb + s * step, w)
            # --- bass
            if sec.get('bass', True):
                for s, off in enumerate(song['bass']):
                    if off is None:
                        continue
                    m = 12 * 3 + root + off  # octave 2
                    ln = song.get('bass_len', 2)
                    n = int(step * ln * SR)
                    w = triangle(mtof(m), n) * env(n, a=0.003, d=0.2, s=0.8, r=0.02, gate=int(n * 0.85)) * 0.3
                    tr.add('bass', cb + s * step * ln, w)
            # --- pad (soft sustained chord)
            if sec.get('pad'):
                n = int(bar * SR)
                for k, i in enumerate(iv):
                    f = mtof(12 * 5 + root + i)
                    w = pulse(f, n, 0.5, vib=0.08, vib_delay=0.0) * env(n, a=0.4, d=0.5, s=0.7, r=0.3, gate=int(n * 0.9))
                    tr.add('pad', cb, w * 0.035)
            # --- drums
            if sec.get('drums', True):
                fill = sec.get('fill') and ci == len(chords) - 1
                pat = song['drums_fill'] if fill else song['drums']
                for s in range(16):
                    t = cb + s * step
                    k, sn, hh = pat[0][s], pat[1][s], pat[2][s]
                    if k == 'x':
                        tr.add('drums', t, kick() * 0.6)
                    if sn == 'x':
                        tr.add('drums', t, snare() * 0.3)
                    elif sn == 'o':
                        tr.add('drums', t, snare() * 0.12)
                    if hh in 'xo':
                        tr.add('drums', t, hat(hh == 'o') * 0.7)
        b0 += len(chords)
    return tr, bar


def one_pole_lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    # vectorised one-pole: y[n] = (1-a) x[n] + a y[n-1]
    from itertools import accumulate
    return np.fromiter(accumulate(x * (1 - a), lambda y, v: v + a * y), float, len(x))


def echo(x, delay, fb, taps=6):
    d = int(delay * SR)
    out = np.zeros_like(x)
    for k in range(1, taps + 1):
        if k * d >= len(x):
            break
        out[k * d:] += x[: len(x) - k * d] * fb ** k
    return out


def mix(tr, song, bar):
    B = tr.buf
    z = np.zeros(tr.n)
    g = lambda k: B.get(k, z)
    beat = bar / 4
    lead = g('lead')
    e1 = one_pole_lp(echo(lead, beat * 0.75, song.get('echo', 0.35)), 3500)
    e2 = one_pole_lp(echo(lead, beat * 1.0, song.get('echo', 0.35)), 3500)
    arp = g('arp')
    L = lead * 0.9 + e1 * 0.55 + g('harm') * 1.1 + arp * 1.0 + g('pad') + g('bass') + g('drums') * 0.9
    R = lead * 0.9 + e2 * 0.55 + g('harm') * 0.7 + echo(arp, beat * 0.5, 0.3, 2) * 0.6 + arp * 0.6 + g('pad') + g('bass') + g('drums') * 0.9
    st = np.stack([L, R], 1)
    # trim trailing silence, gentle fades
    nz = np.nonzero(np.abs(st).max(1) > 1e-4)[0]
    st = st[: nz[-1] + 1]
    st = np.tanh(st * 1.2) / np.tanh(1.2)
    st /= np.abs(st).max() / 0.89
    fo = int(0.02 * SR)
    st[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return st


def write_wav(path, st):
    pcm = (st * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ================================================================ songs
FM_P1 = ['Fm', 'Db', 'Bbm', 'C']
FM_P2 = ['Fm', 'Ab', 'Db', 'C']

SONG1 = dict(  # 자정의 복도 — F minor, 123 BPM (ref track 1)
    name='retro1', bpm=123, tonic=5,
    lead=dict(layers=[('pulse', 0.25, 0, 0.22), ('pulse', 0.125, 1, 0.04)], vib=0.25,
              env=dict(a=0.004, d=0.15, s=0.65, r=0.08)),
    arp=[0, 1, 2, 3, 2, 1, 2, 1], arp_oct=4, arp_vol=0.09,
    bass=[0, None, 12, 0, None, 0, 12, 7], bass_len=2,
    drums=['x.....x.x.......', '....x.......x...', 'x.x.x.x.x.x.x.xo'],
    drums_fill=['x.....x.x.......', '....x.......xxxx', 'x.x.x.x.x.x.....'],
    mel=dict(
        A='C5:4 Ab4:2 F4:2 G4:2 Ab4:2 C5:4 '
          'Db5:6 C5:2 Bb4:4 Ab4:4 '
          'Bb4:4 Db5:2 F5:6 Eb5:2 Db5:2 '
          'E4:2 G4:2 Bb4:4 C5:8 '
          'F5:4 Eb5:2 C5:2 Ab4:4 C5:4 '
          'Eb5:6 Db5:2 C5:4 Ab4:4 '
          'Ab5:4 F5:4 Db5:4 F5:2 Eb5:2 '
          'E5:6 Db5:2 C5:4 Bb4:2 G4:2',
        B='F5:8 Ab5:4 F5:4 '
          'G5:8 Bb5:4 G5:4 '
          'Eb5:4 G5:4 C6:6 Bb5:2 '
          'Ab5:12 G5:2 F5:2 '
          'Db6:4 C6:2 Bb5:2 F5:8 '
          'Ab5:4 F5:2 Db5:2 F5:4 Ab5:4 '
          'G5:4 E5:4 C5:4 E5:4 '
          'G5:12 r:4',
        END='F5:16 r:16'),
    sections=[
        dict(chords=FM_P1, drums=False, pad=True),
        dict(chords=FM_P1 + FM_P2, mel='A', fill=True),
        dict(chords=FM_P1 + FM_P2, mel='A', harm=True, fill=True),
        dict(chords=['Db', 'Eb', 'Cm', 'Fm', 'Bbm', 'Db', 'C', 'C'], mel='B', pad=True, fill=True),
        dict(chords=FM_P1 + FM_P2, mel='A', harm=True, fill=True),
        dict(chords=['Db', 'Eb', 'Cm', 'Fm', 'Bbm', 'Db', 'C', 'C'], mel='B', pad=True, harm=True, fill=True),
        dict(chords=['Fm', 'Fm'], mel='END', drums=False, pad=True),
    ])

SONG2 = dict(  # 신부의 추격 — Bb minor, 144 BPM (ref track 2)
    name='retro2', bpm=144, tonic=10,
    lead=dict(layers=[('pulse', 0.5, 0, 0.2), ('pulse', 0.25, 1, 0.04)], vib=0.2,
              env=dict(a=0.003, d=0.09, s=0.55, r=0.05)),
    arp=[0, 2, 3, 2], arp_oct=4, arp_vol=0.08,
    bass=[0, 12, 0, 12, 0, 12, 7, 12], bass_len=2,
    drums=['x.....x...x.....', '....x.......x..o', 'x.xxx.xxx.xxx.xx'],
    drums_fill=['x.....x...x.....', '....x...x.xxxxxx', 'x.xxx.xx........'],
    mel=dict(
        A='F5:2 F5:2 Db5:2 Bb4:2 Db5:2 F5:2 Bb5:4 '
          'Ab5:2 Gb5:2 F5:2 Db5:2 Bb4:4 Db5:4 '
          'C5:2 Eb5:2 Ab5:4 Gb5:2 F5:2 Eb5:4 '
          'F5:2 E5:2 C5:2 A4:2 C5:4 E5:4 '
          'Bb5:4 Ab5:2 F5:2 Db5:4 F5:4 '
          'Gb5:2 F5:2 Db5:2 Bb4:2 Gb5:4 F5:4 '
          'Ab5:2 F5:2 Db5:2 F5:2 Ab5:2 Bb5:2 Ab5:4 '
          'A5:4 C6:4 A5:2 F5:2 E5:4',
        B='Bb5:6 Db6:2 Bb5:4 Gb5:4 '
          'C6:6 Eb6:2 C6:4 Ab5:4 '
          'Ab5:4 C6:4 F6:4 Eb6:2 C6:2 '
          'Db6:12 C6:2 Bb5:2 '
          'Gb5:4 Bb5:4 Eb6:4 Db6:4 '
          'Db6:4 Bb5:4 Gb5:4 Bb5:4 '
          'C6:4 A5:4 F5:4 A5:4 '
          'C6:8 E6:4 F6:4',
        END='Bb5:2 F5:2 Db5:2 Bb4:10 r:16'),
    sections=[
        dict(chords=['Bbm', 'Gb', 'Ab', 'F'], drums=True, pad=False),
        dict(chords=['Bbm', 'Gb', 'Ab', 'F', 'Bbm', 'Gb', 'Db', 'F'], mel='A', fill=True),
        dict(chords=['Bbm', 'Gb', 'Ab', 'F', 'Bbm', 'Gb', 'Db', 'F'], mel='A', harm=True, fill=True),
        dict(chords=['Gb', 'Ab', 'Fm', 'Bbm', 'Ebm', 'Gb', 'F', 'F'], mel='B', pad=True, fill=True),
        dict(chords=['Bbm', 'Gb', 'Ab', 'F', 'Bbm', 'Gb', 'Db', 'F'], mel='A', harm=True, fill=True),
        dict(chords=['Gb', 'Ab', 'Fm', 'Bbm', 'Ebm', 'Gb', 'F', 'F'], mel='B', pad=True, harm=True, fill=True),
        dict(chords=['Bbm', 'Gb', 'Ab', 'F', 'Bbm', 'Gb', 'Db', 'F'], mel='A', harm=True, fill=True),
        dict(chords=['Bbm', 'Bbm'], mel='END', drums=False, pad=True),
    ])

SONG3 = dict(  # 새벽 4시 — F minor, 103 BPM, music-box (ref track 5)
    name='retro3', bpm=103, tonic=5, echo=0.45,
    lead=dict(layers=[('tri', 0, 0, 0.38), ('pulse', 0.125, 1, 0.06)], vib=0.12, tail=0.6,
              env=dict(a=0.002, d=0.35, s=0.25, r=0.4)),
    arp=[0, 2, 1, 2, 3, 2, 1, 2], arp_oct=4, arp_vol=0.08, arp_rate=2,
    bass=[0, None, None, None, 7, None, 0, None], bass_len=2,
    drums=['x.......x.x.....', '....o.......x...', '..x...x...x...x.'],
    drums_fill=['x.......x.x.....', '....o.......x.xx', '..x...x...x.....'],
    mel=dict(
        A='Ab5:6 G5:2 F5:4 C5:4 '
          'Db5:4 F5:4 Ab5:8 '
          'G5:6 F5:2 E5:4 C5:4 '
          'F5:12 r:4 '
          'C6:6 Bb5:2 Ab5:4 F5:4 '
          'Ab5:4 Db6:4 C6:4 Ab5:4 '
          'Bb5:6 Ab5:2 F5:4 Db5:4 '
          'E5:4 G5:4 C6:8',
        B='F6:8 Eb6:4 Db6:4 '
          'Eb6:8 Db6:4 Bb5:4 '
          'C6:12 Ab5:4 '
          'F5:16 '
          'Db6:8 C6:4 Bb5:4 '
          'Ab5:8 F5:4 Ab5:4 '
          'G5:8 Bb5:4 E5:4 '
          'C6:16',
        END='Ab5:4 G5:4 F5:8 r:16'),
    sections=[
        dict(chords=['Fm', 'Db', 'C', 'Fm'], drums=False, pad=True),
        dict(chords=['Fm', 'Db', 'C', 'Fm', 'Fm', 'Db', 'Bbm', 'C'], mel='A', pad=True, drums=False),
        dict(chords=['Fm', 'Db', 'C', 'Fm', 'Fm', 'Db', 'Bbm', 'C'], mel='A', harm=True, fill=True),
        dict(chords=['Db', 'Eb', 'Fm', 'Fm', 'Bbm', 'Db', 'C', 'C'], mel='B', pad=True, fill=True),
        dict(chords=['Fm', 'Db', 'C', 'Fm', 'Fm', 'Db', 'Bbm', 'C'], mel='A', harm=True, fill=True),
        dict(chords=['Db', 'Eb', 'Fm', 'Fm', 'Bbm', 'Db', 'C', 'C'], mel='B', pad=True, harm=True),
        dict(chords=['Fm', 'Fm'], mel='END', drums=False, pad=True),
    ])

if __name__ == '__main__':
    out = sys.argv[1]
    for song in (SONG1, SONG2, SONG3):
        tr, bar = render(song)
        st = mix(tr, song, bar)
        write_wav(f"{out}/{song['name']}.wav", st)
        print(song['name'], f'{len(st) / SR:.1f}s')

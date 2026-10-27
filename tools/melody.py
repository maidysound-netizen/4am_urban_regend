"""Vocal stem → clean note list (seconds), ignoring vibrato, scoops and slides.

usage: python melody.py N   → mel/mN.pkl  [list of dict(t0, t1, m)]
"""
import os, sys, pickle, numpy as np, librosa

SR = 22050
HOP = 256
FT = HOP / SR


def track_f0(f):
    cache = f'mel/f0_{f}.npz'
    if os.path.exists(cache):
        d = np.load(cache)
        return d['m'], d['vp'], d['rms'], d['on']
    y, _ = librosa.load(f'stems/htdemucs/o{f}/vocals.wav', sr=SR)
    f0, vf, vp = librosa.pyin(y, fmin=70, fmax=1100, sr=SR, frame_length=2048, hop_length=HOP)
    m = librosa.hz_to_midi(np.where(vf, f0, np.nan))
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0][: len(m)]
    on = librosa.onset.onset_detect(y=y, sr=SR, hop_length=HOP, backtrack=True)
    np.savez(cache, m=m, vp=vp, rms=rms, on=on)
    return m, vp, rms, on


def fix_octaves(m):
    """프레임 단위: 주변 0.7초 흐름보다 한 옥타브 튄 음을 제자리로."""
    m = m.copy()
    ok = ~np.isnan(m)
    idx = np.nonzero(ok)[0]
    vals = m[idx]
    for _ in range(2):
        for j in range(len(idx)):
            lo = np.searchsorted(idx, idx[j] - 30)
            hi = np.searchsorted(idx, idx[j] + 30)
            ref = np.median(vals[lo:hi])
            d = vals[j] - ref
            if abs(d) > 8:
                vals[j] -= 12 * np.round(d / 12)
    m[idx] = vals
    return m


def segment(m, vp, rms, on):
    m = fix_octaves(m)
    voiced = (~np.isnan(m)) & (vp > 0.35) & (rms > np.percentile(rms[~np.isnan(m)], 25) * 0.6)
    onset = np.zeros(len(m), bool)
    onset[on[on < len(m)]] = True
    notes = []
    cur = None          # [start, frames list]
    pending = 0         # 다른 음으로 바뀐 프레임 수
    gap = 0

    def close():
        if cur is None:
            return
        fr = np.array(cur[1])
        if len(fr) * FT < 0.06:
            return
        # 앞뒤 20%는 꺾기/미끄러짐이라 버리고 가운데 음높이로
        a, b = int(len(fr) * 0.2), max(int(len(fr) * 0.8), int(len(fr) * 0.2) + 1)
        notes.append(dict(f0=cur[0], f1=int(fr[-1]) + 1, m=int(np.round(np.median(m[fr[a:b]])))))

    for i in range(len(m)):
        if not voiced[i]:
            gap += 1
            if cur is not None and gap >= 3:
                close()
                cur = None
            continue
        gap = 0
        if cur is None:
            cur = [i, [i]]
            pending = 0
            continue
        ref = np.median(m[cur[1][-12:]])
        if abs(m[i] - ref) > 0.75:
            pending += 1
        else:
            pending = 0
        split = pending >= 4 or (onset[i] and (i - cur[0]) * FT > 0.08)
        if split:
            start = i - pending + 1 if pending >= 4 else i
            cur[1] = [k for k in cur[1] if k < start]
            close()
            cur = [start, list(range(start, i + 1))]
            pending = 0
        else:
            cur[1].append(i)
    close()
    out = [dict(t0=n['f0'] * FT, t1=n['f1'] * FT, m=n['m']) for n in notes]

    # 같은 음이 아주 짧게 끊기면 이어 붙인다
    merged = []
    for n in out:
        if merged and merged[-1]['m'] == n['m'] and n['t0'] - merged[-1]['t1'] < 0.04:
            merged[-1]['t1'] = n['t1']
        else:
            merged.append(n)
    # 옥타브 튐 보정: 앞뒤 음과 10반음 이상 떨어졌는데 옥타브를 옮기면 가까워지면
    for i in range(len(merged)):
        nb = [merged[j]['m'] for j in (i - 1, i + 1) if 0 <= j < len(merged)]
        if not nb:
            continue
        ref = np.median(nb)
        d = merged[i]['m'] - ref
        if abs(d) >= 10:
            cand = merged[i]['m'] - 12 * np.round(d / 12)
            if abs(cand - ref) < abs(d):
                merged[i]['m'] = int(cand)
    # 미끄러지는 음(아주 짧고 양옆 음 사이에 끼인 음) 제거
    clean = []
    for i, n in enumerate(merged):
        dur = n['t1'] - n['t0']
        if dur < 0.09 and 0 < i < len(merged) - 1:
            a, b = merged[i - 1]['m'], merged[i + 1]['m']
            if min(a, b) <= n['m'] <= max(a, b) and merged[i + 1]['t0'] - n['t1'] < 0.03:
                continue
        clean.append(n)
    # 음 단위: 앞뒤 4음 흐름에서 8반음 넘게 벗어나면 옥타브를 옮겨 넣는다
    for i in range(len(clean)):
        ctx = [clean[j]['m'] for j in range(max(0, i - 4), min(len(clean), i + 5)) if j != i]
        if ctx:
            ref = np.median(ctx)
            d = clean[i]['m'] - ref
            if abs(d) > 8:
                clean[i]['m'] = int(clean[i]['m'] - 12 * np.round(d / 12))
    return clean, voiced


def accuracy(notes, m, voiced, shift):
    """보컬이 확실히 노래하는 프레임 중, 리드가 같은 음(옥타브 무시, ±0.5반음)을 내는 비율"""
    t = np.arange(len(m)) * FT
    lead = np.full(len(m), np.nan)
    for n in notes:
        lead[(t >= n['t0']) & (t < n['t1'])] = n['m'] - shift
    ok = voiced & ~np.isnan(m)
    has = ok & ~np.isnan(lead)
    d = np.abs(((m[has] - lead[has]) + 6) % 12 - 6)
    return (d <= 0.5).sum() / ok.sum(), has.sum() / ok.sum()


def main():
    f = sys.argv[1]
    os.makedirs('mel', exist_ok=True)
    m, vp, rms, on = track_f0(f)
    notes, voiced = segment(m, vp, rms, on)
    m = fix_octaves(m)
    shift = int(np.round((72 - np.median([n['m'] for n in notes])) / 12)) * 12
    for n in notes:
        n['m'] += shift
    # 예전 방식(16분음표 칸) 비교
    old = pickle.load(open(f'cover/c{f}.wav.pkl', 'rb'))
    lead_old, grid = old[0], old[5]
    oldn = [dict(t0=grid[n['start']], t1=grid[min(n['end'], len(grid) - 1)], m=n['m']) for n in lead_old]
    old_shift = int(np.round((np.median([n['m'] for n in lead_old]) - np.nanmedian(m)) / 12)) * 12
    a_new, c_new = accuracy(notes, m, voiced, shift)
    a_old, c_old = accuracy(oldn, m, voiced, old_shift)
    print(f'track {f}: notes old {len(oldn)} → new {len(notes)} | pitch match old {a_old:.0%} → new {a_new:.0%} '
          f'(covered {c_old:.0%} → {c_new:.0%})')
    pickle.dump(notes, open(f'mel/m{f}.pkl', 'wb'))


main()

"""Young Sephiroth's voice from Sephiroth's: each line pitched up and its formants moved up (a shorter vocal tract),
its length and timing kept, its loudness matched to the original's.
  praat: Praat's Change Gender (PSOLA pitch + formant shift by resampling) through parselmouth;
  world: the WORLD vocoder (pyworld): F0 scaled, spectral envelope and aperiodicity warped along frequency."""
import numpy as np
import soundfile as sf
import parselmouth
from parselmouth.praat import call
import pyworld as pw


def praat_young(x, sr, semitones, formant):
    snd = parselmouth.Sound(x.astype(np.float64), sr)
    pitch = snd.to_pitch(time_step=0.005, pitch_floor=70, pitch_ceiling=700)
    med = call(pitch, 'Get quantile', 0, 0, 0.5, 'Hertz')
    if not np.isfinite(med) or med <= 0:
        med = 150.0
    out = call(snd, 'Change gender', 70, 700, formant, med * 2 ** (semitones / 12.0), 1.0, 1.0)
    y = np.asarray(out.values[0], np.float64)
    return y


def world_young(x, sr, semitones, formant):
    x = x.astype(np.float64)
    f0, t = pw.harvest(x, sr, f0_floor=60.0, f0_ceil=800.0, frame_period=5.0)
    sp = pw.cheaptrick(x, f0, t, sr)
    ap = pw.d4c(x, f0, t, sr)
    k = np.arange(sp.shape[1], dtype=np.float64)
    src = k / formant
    sp2 = np.array([np.interp(src, k, r) for r in sp])
    ap2 = np.array([np.interp(src, k, r) for r in ap])
    return pw.synthesize(f0 * 2 ** (semitones / 12.0), sp2, ap2, sr, 5.0)


def match(y, x):
    y = np.asarray(y, np.float64)
    if len(y) < len(x):
        y = np.pad(y, (0, len(x) - len(y)))
    y = y[:len(x)]
    rx, ry = np.sqrt(np.mean(x ** 2)), np.sqrt(np.mean(y ** 2))
    if ry > 0:
        y = y * (rx / ry)
    peak = np.abs(y).max()
    limit = max(np.abs(x).max(), 0.5)
    if peak > limit:
        y = y * (limit / peak)
    return y


def young(x, sr, engine='praat', semitones=3.0, formant=1.09):
    f = praat_young if engine == 'praat' else world_young
    return match(f(x, sr, semitones, formant), np.asarray(x, np.float64))

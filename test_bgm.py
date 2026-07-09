"""Test BGM WAV generation independently of Streamlit."""
import math
import wave
import io
import base64
import random
from array import array

EMOTION_BGM = {
    "快乐": {"scale": [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.25],
             "bpm": 88, "wave": "triangle", "name": "阳光小调"},
    "悲伤": {"scale": [220.00, 261.63, 293.66, 329.63, 392.00, 440.00, 523.25],
             "bpm": 52, "wave": "sine", "name": "雨夜轻吟"},
    "愤怒": {"scale": [329.63, 349.23, 392.00, 440.00, 493.88, 523.25, 587.33],
             "bpm": 115, "wave": "sawtooth", "name": "烈焰律动"},
    "恐惧": {"scale": [261.63, 311.13, 369.99, 415.30, 466.16, 523.25, 622.25],
             "bpm": 42, "wave": "sine", "name": "暗影迷雾"},
    "惊讶": {"scale": [261.63, 293.66, 329.63, 369.99, 415.30, 466.16, 523.25],
             "bpm": 100, "wave": "triangle", "name": "星光奇迹"},
    "厌恶": {"scale": [261.63, 369.99, 392.00, 554.37, 587.33, 830.61],
             "bpm": 62, "wave": "square", "name": "疏离迴响"},
    "期待": {"scale": [349.23, 392.00, 440.00, 523.25, 587.33, 659.25, 698.46],
             "bpm": 76, "wave": "triangle", "name": "晨曦序曲"},
    "信任": {"scale": [196.00, 220.00, 246.94, 293.66, 329.63, 392.00, 440.00],
             "bpm": 64, "wave": "sine", "name": "绿荫和鸣"},
}


def _generate_wav_audio(top_emotion: str) -> str:
    """Generate emotion-adaptive ambient WAV audio, return base64 data URI."""
    bgm = EMOTION_BGM.get(top_emotion, EMOTION_BGM["快乐"])
    scale = bgm["scale"]
    bpm = bgm["bpm"]
    wave_type = bgm["wave"]
    sample_rate = 44100
    duration = 10.0
    total_samples = int(sample_rate * duration)
    scale_len = len(scale)

    def gen(t: float, freq: float, vol: float, wtype: str) -> float:
        phase = 2.0 * math.pi * freq * t
        wmap = {
            "sine": math.sin(phase),
            "triangle": (2.0 / math.pi) * math.asin(math.sin(phase)),
            "sawtooth": 2.0 * ((freq * t) % 1.0) - 1.0,
            "square": 1.0 if math.sin(phase) >= 0 else -1.0,
        }
        return vol * wmap.get(wtype, math.sin(phase))

    buf_l = [0.0] * total_samples

    # Layer 1: low drone with tremolo
    df = scale[0] / 2.0
    for i in range(total_samples):
        t_i = i / sample_rate
        tremolo = 1.0 + 0.12 * math.sin(2.0 * math.pi * 0.38 * t_i)
        buf_l[i] += gen(t_i, df, 0.09 * tremolo, "sine")

    # Layer 2: root overtone
    for i in range(total_samples):
        buf_l[i] += gen(i / sample_rate, scale[0], 0.04, "sine")

    # Layer 3: melody with random walk on scale
    beat_dur = 60.0 / bpm / 2.0
    notes_per_bar = 8
    mel_idx = scale_len // 2
    rng = random.Random(hash(top_emotion) + sum(ord(c) for c in top_emotion))

    notes = []
    t_i = 0.0
    nc = 0
    while t_i < duration:
        bp = nc % notes_per_bar
        if bp in (0, 4):  # strong beat
            freq, vol, nlen = scale[mel_idx], 0.15, beat_dur * 1.6
            if rng.random() < 0.3:
                hi = min(scale_len - 1, mel_idx + 2)
                hi_s = int(t_i * sample_rate)
                hi_e = int((t_i + nlen * 0.7) * sample_rate)
                notes.append((hi_s, hi_e, scale[hi], 0.05))
        elif bp in (2, 6):  # medium beat
            freq, vol, nlen = scale[mel_idx], 0.07, beat_dur * 1.1
        else:  # weak beat — occasional root touch
            freq, vol, nlen = 0, 0, beat_dur
            if rng.random() < 0.25:
                freq, vol, nlen = scale[0], 0.035, beat_dur * 0.6

        if vol > 0 and freq > 0:
            s_s = int(t_i * sample_rate)
            e_s = int((t_i + nlen) * sample_rate)
            notes.append((s_s, e_s, freq, vol))

        # random walk biased toward scale center
        center = scale_len // 2
        pull = (center - mel_idx) * 0.18
        mel_idx = max(0, min(scale_len - 1, mel_idx + round((rng.random() - 0.5) * 2.2 + pull)))
        t_i += beat_dur
        nc += 1

    for s_s, e_s, freq, vol in notes:
        s_s = max(0, min(total_samples - 1, s_s))
        e_s = max(s_s + 1, min(total_samples, e_s))
        for i in range(s_s, e_s):
            progress = (i - s_s) / max(1, e_s - s_s)
            attack = min(1.0, progress / 0.02)
            release = max(0.0, 1.0 - (progress - 0.55) / 0.45) if progress > 0.55 else 1.0
            env = attack * release
            buf_l[i] += gen(i / sample_rate, freq, vol * env, wave_type)

    # Fade out last 1.5 seconds for seamless looping
    fs = int(sample_rate * 8.5)
    for i in range(fs, total_samples):
        buf_l[i] *= 1.0 - (i - fs) / (total_samples - fs)

    # Normalize to 70%
    peak = max(max(abs(v) for v in buf_l), 0.001)
    gain = 0.70 / peak
    samples_16 = array('h', (int(max(-1.0, min(1.0, v * gain)) * 32767) for v in buf_l))

    bio = io.BytesIO()
    with wave.open(bio, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples_16.tobytes())
    bio.seek(0)
    return f"data:audio/wav;base64,{base64.b64encode(bio.read()).decode()}"


if __name__ == "__main__":
    for em in ["快乐", "悲伤", "愤怒", "恐惧", "惊讶", "厌恶", "期待", "信任"]:
        b64 = _generate_wav_audio(em)
        raw_bytes = base64.b64decode(b64.replace("data:audio/wav;base64,", ""))
        dur = len(raw_bytes) / 44100
        kb = len(raw_bytes) / 1024
        print(f"  {em}: {kb:.0f}KB ({dur:.1f}s)  OK")

    # Save one to disk so we can verify it plays
    b64 = _generate_wav_audio("快乐")
    raw_bytes = base64.b64decode(b64.replace("data:audio/wav;base64,", ""))
    with open("test_bgm.wav", "wb") as f:
        f.write(raw_bytes)
    import os
    size_kb = os.path.getsize("test_bgm.wav") / 1024
    print(f"\nSaved test_bgm.wav ({size_kb:.0f}KB) — play it to verify audio.")

    print("\nAll 8 emotions generated successfully!")

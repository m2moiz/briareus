#!/usr/bin/env python3
"""Generate a 103 BPM Macarena click track WAV (stdlib only — no numpy).

4-beat count-in (high blips) + 32 dance beats (downbeats accented), so the robot
dance and the click share the same count-in and beat grid.

    python3 make-click-track.py [out.wav] [bpm]
"""
import math
import struct
import sys
import wave

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/macarena_click_103bpm.wav"
BPM = float(sys.argv[2]) if len(sys.argv) > 2 else 103.0

SR = 44100
beat = 60.0 / BPM
count_in, beats = 4, 32
total = count_in + beats
n = int(total * beat * SR)
samples = [0.0] * n

for b in range(total):
    accent = (b >= count_in) and ((b - count_in) % 4 == 0)   # downbeat after count-in
    f = 1600 if b < count_in else (1300 if accent else 900)
    start = int(b * beat * SR)
    length = int(0.045 * SR)
    for i in range(length):
        j = start + i
        if j < n:
            env = math.exp(-6.0 * i / length)
            samples[j] += 0.6 * env * math.sin(2 * math.pi * f * i / SR)

with wave.open(OUT, "w") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples))

print(f"wrote {OUT}  ({total*beat:.1f}s, {count_in} count-in + {beats} beats @ {BPM:g} BPM, beat={beat:.4f}s)")

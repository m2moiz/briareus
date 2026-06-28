#!/usr/bin/env python3
"""Generate an alternating-tom drum loop WAV (stdlib only, no numpy).

Matches drumbeat.py's grid: a 4-beat count-in (high blips) then BARS of 4/4 with a
tom hit on every 8th note, alternating a low tom (left arm) and a mid tom (right
arm). Start this together with drumbeat.py and the count-ins line up.

A tom hit is a short pitched membrane sound: a sine whose pitch drops over a fast
exponential decay, with a noise transient at the attack.

    python3 make-drum-loop.py [out.wav] [bpm] [bars]      # defaults: 90 BPM, 4 bars
"""
import math
import struct
import sys
import wave

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/drum_loop_90bpm.wav"
BPM = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
BARS = int(sys.argv[3]) if len(sys.argv) > 3 else 4

SR = 44100
beat = 60.0 / BPM
eighth = beat / 2.0
COUNT_IN = 4
LOW_TOM, MID_TOM = 110.0, 165.0      # left arm = low tom, right arm = mid tom

total_s = COUNT_IN * beat + BARS * 4 * beat + 0.5
n = int(total_s * SR)
samples = [0.0] * n

# simple deterministic noise (no random module dependence on state across runs)
def _noise(i):
    x = math.sin(i * 12.9898) * 43758.5453
    return 2.0 * (x - math.floor(x)) - 1.0


def add_click(t, f=1500.0):
    start = int(t * SR)
    length = int(0.045 * SR)
    for i in range(length):
        j = start + i
        if 0 <= j < n:
            samples[j] += 0.5 * math.exp(-7.0 * i / length) * math.sin(2 * math.pi * f * i / SR)


def add_tom(t, f0):
    start = int(t * SR)
    length = int(0.26 * SR)
    for i in range(length):
        j = start + i
        if not (0 <= j < n):
            continue
        frac = i / length
        env = math.exp(-5.5 * frac)
        f = f0 * (1.0 - 0.35 * frac)                 # pitch drops as it decays
        body = math.sin(2 * math.pi * f * i / SR)
        attack = _noise(i) * math.exp(-60.0 * frac)  # short noisy transient
        samples[j] += 0.7 * env * (0.85 * body + 0.15 * attack)


# 4-beat count-in
for b in range(COUNT_IN):
    add_click(b * beat)

# alternating toms on every 8th note
t0 = COUNT_IN * beat
for s in range(BARS * 8):
    add_tom(t0 + s * eighth, LOW_TOM if s % 2 == 0 else MID_TOM)

peak = max(1e-9, max(abs(v) for v in samples))
scale = min(1.0, 0.95 / peak)
with wave.open(OUT, "w") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, v * scale)) * 32767)) for v in samples))

print(f"wrote {OUT}  ({total_s:.1f}s, {COUNT_IN} count-in + {BARS*8} tom hits @ {BPM:g} BPM)")

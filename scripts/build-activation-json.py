#!/usr/bin/env python3
"""
build-activation-json.py
Generates muscles_activation.json with per-lift activation curves.

Values are heuristic approximations informed by EMG literature on compound
lifts (not peer-reviewed clinical data). Each lift is modeled as a repeated
sin^2 pulse scaled by a per-muscle intensity. Prime movers peak near the
concentric (midpoint of each rep), stabilizers hold a lower baseline.

Timing stays in sync with the .glb animation durations. Resolution is set by
TIME_STEP_SECONDS.
"""

import json
import math
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "muscles_activation.json"

TIME_STEP_SECONDS = 0.25

# duration (s), reps
LIFTS = {
    "bench_press": (24.0, 8),
    "bicep_curl":  (16.0, 8),
    "squat":       (18.0, 6),
    "deadlift":    (18.0, 6),
}

# Per-lift intensity map: muscle_name -> intensity 0..1
# 1.0 = prime mover peak, 0.3-0.6 = synergist, 0.1-0.2 = stabilizer, 0 = silent
INTENSITIES = {
    "bench_press": {
        "pectoralis_major_left": 1.00, "pectoralis_major_right": 1.00,
        "triceps_brachii_left_long_head": 0.85, "triceps_brachii_left_lateral_head": 0.80,
        "triceps_brachii_left_medial_head": 0.75,
        "triceps_brachii_right_long_head": 0.85, "triceps_brachii_right_lateral_head": 0.80,
        "triceps_brachii_right_medial_head": 0.75,
        "biceps_brachii_left_long_head": 0.15, "biceps_brachii_left_short_head": 0.15,
        "biceps_brachii_right_long_head": 0.15, "biceps_brachii_right_short_head": 0.15,
        "rectus_abdominis": 0.25,
        "external_oblique_left": 0.20, "external_oblique_right": 0.20,
        "internal_oblique_left": 0.15, "internal_oblique_right": 0.15,
        "transverse_abdominis": 0.30,
    },
    "bicep_curl": {
        "biceps_brachii_left_long_head": 1.00, "biceps_brachii_left_short_head": 0.95,
        "biceps_brachii_right_long_head": 1.00, "biceps_brachii_right_short_head": 0.95,
        "triceps_brachii_left_long_head": 0.10, "triceps_brachii_left_lateral_head": 0.08,
        "triceps_brachii_left_medial_head": 0.08,
        "triceps_brachii_right_long_head": 0.10, "triceps_brachii_right_lateral_head": 0.08,
        "triceps_brachii_right_medial_head": 0.08,
        "pectoralis_major_left": 0.10, "pectoralis_major_right": 0.10,
        "rectus_abdominis": 0.15,
        "external_oblique_left": 0.10, "external_oblique_right": 0.10,
        "transverse_abdominis": 0.20,
    },
    "squat": {
        "rectus_femoris_left": 0.90, "rectus_femoris_right": 0.90,
        "vastus_lateralis_left": 1.00, "vastus_lateralis_right": 1.00,
        "vastus_medialis_left": 0.95, "vastus_medialis_right": 0.95,
        "vastus_intermedius_left": 0.90, "vastus_intermedius_right": 0.90,
        "gluteus_maximus_left": 0.90, "gluteus_maximus_right": 0.90,
        "gluteus_medius_left": 0.55, "gluteus_medius_right": 0.55,
        "biceps_femoris_left": 0.50, "biceps_femoris_right": 0.50,
        "semitendinosus_left": 0.45, "semitendinosus_right": 0.45,
        "semimembranosus_left": 0.45, "semimembranosus_right": 0.45,
        "gastrocnemius_left": 0.40, "gastrocnemius_right": 0.40,
        "soleus_left": 0.45, "soleus_right": 0.45,
        "rectus_abdominis": 0.35,
        "external_oblique_left": 0.30, "external_oblique_right": 0.30,
        "internal_oblique_left": 0.30, "internal_oblique_right": 0.30,
        "transverse_abdominis": 0.45,
    },
    "deadlift": {
        "biceps_femoris_left": 1.00, "biceps_femoris_right": 1.00,
        "semitendinosus_left": 0.90, "semitendinosus_right": 0.90,
        "semimembranosus_left": 0.90, "semimembranosus_right": 0.90,
        "gluteus_maximus_left": 1.00, "gluteus_maximus_right": 1.00,
        "gluteus_medius_left": 0.50, "gluteus_medius_right": 0.50,
        "rectus_femoris_left": 0.55, "rectus_femoris_right": 0.55,
        "vastus_lateralis_left": 0.60, "vastus_lateralis_right": 0.60,
        "vastus_medialis_left": 0.55, "vastus_medialis_right": 0.55,
        "vastus_intermedius_left": 0.55, "vastus_intermedius_right": 0.55,
        "gastrocnemius_left": 0.35, "gastrocnemius_right": 0.35,
        "soleus_left": 0.40, "soleus_right": 0.40,
        "rectus_abdominis": 0.45,
        "external_oblique_left": 0.40, "external_oblique_right": 0.40,
        "internal_oblique_left": 0.40, "internal_oblique_right": 0.40,
        "transverse_abdominis": 0.60,
    },
}


def curve(duration, reps, intensity):
    """sin^2 pulse per rep, scaled by intensity, with a small baseline for synergists."""
    per_rep = duration / reps
    steps = int(round(duration / TIME_STEP_SECONDS)) + 1
    out = []
    baseline = 0.05 * intensity  # tonic baseline for involved muscles
    for i in range(steps):
        t = i * TIME_STEP_SECONDS
        phase = (t % per_rep) / per_rep  # 0..1 within rep
        pulse = math.sin(math.pi * phase) ** 2
        v = baseline + (intensity - baseline) * pulse
        out.append(round(max(0.0, min(1.0, v)), 3))
    return out


def main():
    activation = {}
    for lift, (duration, reps) in LIFTS.items():
        activation[lift] = {}
        for muscle, intensity in INTENSITIES[lift].items():
            activation[lift][muscle] = curve(duration, reps, intensity)

    OUT_PATH.write_text(json.dumps(activation, separators=(",", ":")) + "\n", encoding="utf-8")
    size = OUT_PATH.stat().st_size
    print(f"wrote {OUT_PATH}  ({size} bytes)")
    for lift in LIFTS:
        n_samples = len(next(iter(activation[lift].values())))
        n_muscles = len(activation[lift])
        print(f"  {lift}:  {n_muscles} muscles  x  {n_samples} samples @ {TIME_STEP_SECONDS}s")


if __name__ == "__main__":
    main()

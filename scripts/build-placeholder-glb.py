#!/usr/bin/env python3
"""
build-placeholder-glb.py
Generates human_anatomy_gym_v1.glb — a rigged humanoid placeholder.

What's in the glb:
  * Cylinder-primitive humanoid (head, neck, chest/waist/pelvis torso,
    arms, legs). All limbs are children of joint nodes so rotating a
    joint moves everything downstream.
  * 40 muscle meshes (chest, biceps, triceps, core, glutes, quads,
    hamstrings, calves) parented to the joint their muscle crosses,
    so they move with the limb instead of floating.
  * Four exercise animations (bench_press, bicep_curl, squat, deadlift)
    with per-joint rotation keyframes shaped like real lift mechanics
    (shoulder flex + elbow extension for presses, hip + knee flex for
    squats, hip hinge for deadlift, etc).

This is still NOT anatomically accurate — cylinders are not muscle
bellies and the animations are stylized demonstrations, not mocap.
It just reads as a *figure performing a lift* instead of a floating
pile of blocks.
"""

import json
import math
import struct
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "human_anatomy_gym_v1.glb"

# ---------------------------------------------------------------------------
# Joints (hierarchical rig). Each entry: (name, parent, local_translation)
# Positions in meters. Root at feet, +Y up, +Z toward camera.
# ---------------------------------------------------------------------------

JOINTS = [
    ("root",         None,          (0.00,  0.00,  0.00)),
    ("pelvis",       "root",        (0.00,  0.95,  0.00)),
    ("spine_mid",    "pelvis",      (0.00,  0.09,  0.00)),
    ("spine_upper",  "spine_mid",   (0.00,  0.15,  0.00)),
    ("neck",         "spine_upper", (0.00,  0.19,  0.00)),
    ("head",         "neck",        (0.00,  0.09,  0.00)),

    ("shoulder_L",   "spine_upper", (-0.18, 0.17,  0.00)),
    ("elbow_L",      "shoulder_L",  (0.00, -0.28,  0.00)),
    ("wrist_L",      "elbow_L",     (0.00, -0.26,  0.00)),
    ("hand_L",       "wrist_L",     (0.00, -0.09,  0.00)),

    ("shoulder_R",   "spine_upper", ( 0.18, 0.17,  0.00)),
    ("elbow_R",      "shoulder_R",  (0.00, -0.28,  0.00)),
    ("wrist_R",      "elbow_R",     (0.00, -0.26,  0.00)),
    ("hand_R",       "wrist_R",     (0.00, -0.09,  0.00)),

    ("hip_L",        "pelvis",      (-0.10, -0.04, 0.00)),
    ("knee_L",       "hip_L",       (0.00, -0.42,  0.00)),
    ("ankle_L",      "knee_L",      (0.00, -0.42,  0.00)),
    ("foot_L",       "ankle_L",     (0.00, -0.04, 0.08)),

    ("hip_R",        "pelvis",      ( 0.10, -0.04, 0.00)),
    ("knee_R",       "hip_R",       (0.00, -0.42,  0.00)),
    ("ankle_R",      "knee_R",      (0.00, -0.42,  0.00)),
    ("foot_R",       "ankle_R",     (0.00, -0.04, 0.08)),
]

# ---------------------------------------------------------------------------
# Skin / limb meshes. Children of a joint. (name, parent_joint, local_translation, scale)
# Cylinders are 1 unit tall along +Y, 1 unit diameter. scale.y = length,
# scale.x = scale.z = diameter.
# ---------------------------------------------------------------------------

SKIN_LIMBS = [
    ("skin/head",         "head",        (0.00,  0.08,  0.02), (0.15, 0.22, 0.17)),
    ("skin/neck",         "neck",        (0.00,  0.04,  0.00), (0.08, 0.09, 0.08)),
    ("skin/chest",        "spine_upper", (0.00,  0.08,  0.00), (0.34, 0.26, 0.21)),
    ("skin/waist",        "spine_mid",   (0.00,  0.07,  0.00), (0.26, 0.18, 0.18)),
    ("skin/pelvis_core",  "pelvis",      (0.00,  0.00,  0.00), (0.30, 0.14, 0.19)),

    ("skin/upperarm_L",   "shoulder_L",  (0.00, -0.14,  0.00), (0.095, 0.28, 0.095)),
    ("skin/upperarm_R",   "shoulder_R",  (0.00, -0.14,  0.00), (0.095, 0.28, 0.095)),
    ("skin/forearm_L",    "elbow_L",     (0.00, -0.13,  0.00), (0.078, 0.26, 0.078)),
    ("skin/forearm_R",    "elbow_R",     (0.00, -0.13,  0.00), (0.078, 0.26, 0.078)),
    ("skin/hand_L",       "wrist_L",     (0.00, -0.09,  0.00), (0.075, 0.18, 0.045)),
    ("skin/hand_R",       "wrist_R",     (0.00, -0.09,  0.00), (0.075, 0.18, 0.045)),

    ("skin/thigh_L",      "hip_L",       (0.00, -0.21,  0.00), (0.145, 0.42, 0.145)),
    ("skin/thigh_R",      "hip_R",       (0.00, -0.21,  0.00), (0.145, 0.42, 0.145)),
    ("skin/shin_L",       "knee_L",      (0.00, -0.21,  0.00), (0.105, 0.42, 0.105)),
    ("skin/shin_R",       "knee_R",      (0.00, -0.21,  0.00), (0.105, 0.42, 0.105)),
    ("skin/foot_L",       "foot_L",      (0.00,  0.04,  0.05), (0.085, 0.08, 0.22)),
    ("skin/foot_R",       "foot_R",      (0.00,  0.04,  0.05), (0.085, 0.08, 0.22)),
]

# ---------------------------------------------------------------------------
# Muscles. Children of their crossing joint so they follow the limb.
# (name, parent_joint, local_translation, scale, group)
# ---------------------------------------------------------------------------

MUSCLES = [
    # chest — front of chest
    ("pectoralis_major_left",   "spine_upper", (-0.09, 0.13,  0.11), (0.17, 0.12, 0.05), "chest"),
    ("pectoralis_major_right",  "spine_upper", ( 0.09, 0.13,  0.11), (0.17, 0.12, 0.05), "chest"),

    # biceps — front of upper arm
    ("biceps_brachii_left_long_head",   "shoulder_L", ( 0.015, -0.14, 0.055), (0.040, 0.14, 0.040), "biceps"),
    ("biceps_brachii_left_short_head",  "shoulder_L", (-0.015, -0.14, 0.055), (0.035, 0.13, 0.040), "biceps"),
    ("biceps_brachii_right_long_head",  "shoulder_R", (-0.015, -0.14, 0.055), (0.040, 0.14, 0.040), "biceps"),
    ("biceps_brachii_right_short_head", "shoulder_R", ( 0.015, -0.14, 0.055), (0.035, 0.13, 0.040), "biceps"),

    # triceps — back of upper arm
    ("triceps_brachii_left_long_head",    "shoulder_L", ( 0.00, -0.14, -0.055), (0.040, 0.15, 0.040), "triceps"),
    ("triceps_brachii_left_lateral_head", "shoulder_L", (-0.03, -0.12, -0.045), (0.035, 0.12, 0.040), "triceps"),
    ("triceps_brachii_left_medial_head",  "shoulder_L", ( 0.03, -0.18, -0.045), (0.030, 0.10, 0.035), "triceps"),
    ("triceps_brachii_right_long_head",    "shoulder_R", ( 0.00, -0.14, -0.055), (0.040, 0.15, 0.040), "triceps"),
    ("triceps_brachii_right_lateral_head", "shoulder_R", ( 0.03, -0.12, -0.045), (0.035, 0.12, 0.040), "triceps"),
    ("triceps_brachii_right_medial_head",  "shoulder_R", (-0.03, -0.18, -0.045), (0.030, 0.10, 0.035), "triceps"),

    # core — front of waist/pelvis
    ("rectus_abdominis",       "spine_mid", ( 0.00,  0.03, 0.10), (0.12, 0.17, 0.03), "core"),
    ("external_oblique_left",  "spine_mid", (-0.11,  0.03, 0.08), (0.06, 0.15, 0.04), "core"),
    ("external_oblique_right", "spine_mid", ( 0.11,  0.03, 0.08), (0.06, 0.15, 0.04), "core"),
    ("internal_oblique_left",  "spine_mid", (-0.09, -0.03, 0.07), (0.05, 0.08, 0.03), "core"),
    ("internal_oblique_right", "spine_mid", ( 0.09, -0.03, 0.07), (0.05, 0.08, 0.03), "core"),
    ("transverse_abdominis",   "spine_mid", ( 0.00,  0.00, 0.09), (0.17, 0.09, 0.025), "core"),

    # glutes — back of pelvis
    ("gluteus_maximus_left",  "pelvis", (-0.09, -0.01, -0.11), (0.12, 0.14, 0.07), "glutes"),
    ("gluteus_maximus_right", "pelvis", ( 0.09, -0.01, -0.11), (0.12, 0.14, 0.07), "glutes"),
    ("gluteus_medius_left",   "pelvis", (-0.13,  0.04, -0.06), (0.06, 0.08, 0.05), "glutes"),
    ("gluteus_medius_right",  "pelvis", ( 0.13,  0.04, -0.06), (0.06, 0.08, 0.05), "glutes"),

    # quads — front of thigh
    ("rectus_femoris_left",      "hip_L", ( 0.00, -0.18, 0.08), (0.055, 0.22, 0.045), "quads"),
    ("rectus_femoris_right",     "hip_R", ( 0.00, -0.18, 0.08), (0.055, 0.22, 0.045), "quads"),
    ("vastus_lateralis_left",    "hip_L", (-0.06, -0.18, 0.05), (0.045, 0.22, 0.055), "quads"),
    ("vastus_lateralis_right",   "hip_R", ( 0.06, -0.18, 0.05), (0.045, 0.22, 0.055), "quads"),
    ("vastus_medialis_left",     "hip_L", ( 0.04, -0.30, 0.06), (0.045, 0.12, 0.045), "quads"),
    ("vastus_medialis_right",    "hip_R", (-0.04, -0.30, 0.06), (0.045, 0.12, 0.045), "quads"),
    ("vastus_intermedius_left",  "hip_L", ( 0.00, -0.18, 0.05), (0.045, 0.18, 0.03),  "quads"),
    ("vastus_intermedius_right", "hip_R", ( 0.00, -0.18, 0.05), (0.045, 0.18, 0.03),  "quads"),

    # hamstrings — back of thigh
    ("biceps_femoris_left",   "hip_L", (-0.04, -0.22, -0.08), (0.050, 0.20, 0.045), "hamstrings"),
    ("biceps_femoris_right",  "hip_R", ( 0.04, -0.22, -0.08), (0.050, 0.20, 0.045), "hamstrings"),
    ("semitendinosus_left",   "hip_L", ( 0.02, -0.22, -0.08), (0.035, 0.20, 0.035), "hamstrings"),
    ("semitendinosus_right",  "hip_R", (-0.02, -0.22, -0.08), (0.035, 0.20, 0.035), "hamstrings"),
    ("semimembranosus_left",  "hip_L", (-0.02, -0.28, -0.09), (0.040, 0.14, 0.035), "hamstrings"),
    ("semimembranosus_right", "hip_R", ( 0.02, -0.28, -0.09), (0.040, 0.14, 0.035), "hamstrings"),

    # calves — back of shin
    ("gastrocnemius_left",  "knee_L", ( 0.00, -0.13, -0.06), (0.070, 0.14, 0.050), "calves"),
    ("gastrocnemius_right", "knee_R", ( 0.00, -0.13, -0.06), (0.070, 0.14, 0.050), "calves"),
    ("soleus_left",         "knee_L", ( 0.00, -0.28, -0.05), (0.055, 0.12, 0.045), "calves"),
    ("soleus_right",        "knee_R", ( 0.00, -0.28, -0.05), (0.055, 0.12, 0.045), "calves"),
]

# ---------------------------------------------------------------------------
# Cylinder primitive. 1x1x1 cylinder centered at origin, axis = Y.
# ---------------------------------------------------------------------------

def cylinder_geometry(radial_segments=14):
    positions = []
    normals = []
    indices = []

    # Side vertices: two rings (top + bottom), each with per-vertex outward normals.
    for ring_y in (0.5, -0.5):
        for i in range(radial_segments):
            theta = 2 * math.pi * i / radial_segments
            x = 0.5 * math.cos(theta)
            z = 0.5 * math.sin(theta)
            positions.extend([x, ring_y, z])
            normals.extend([math.cos(theta), 0, math.sin(theta)])

    # Side triangles
    for i in range(radial_segments):
        a = i
        b = (i + 1) % radial_segments
        c = i + radial_segments
        d = ((i + 1) % radial_segments) + radial_segments
        indices.extend([a, c, b, b, c, d])

    # Top cap: center + ring (with up-pointing normals)
    top_center = len(positions) // 3
    positions.extend([0, 0.5, 0]); normals.extend([0, 1, 0])
    top_ring_start = len(positions) // 3
    for i in range(radial_segments):
        theta = 2 * math.pi * i / radial_segments
        positions.extend([0.5 * math.cos(theta), 0.5, 0.5 * math.sin(theta)])
        normals.extend([0, 1, 0])
    for i in range(radial_segments):
        indices.extend([top_center, top_ring_start + i, top_ring_start + ((i + 1) % radial_segments)])

    # Bottom cap: center + ring (down-pointing normals)
    bot_center = len(positions) // 3
    positions.extend([0, -0.5, 0]); normals.extend([0, -1, 0])
    bot_ring_start = len(positions) // 3
    for i in range(radial_segments):
        theta = 2 * math.pi * i / radial_segments
        positions.extend([0.5 * math.cos(theta), -0.5, 0.5 * math.sin(theta)])
        normals.extend([0, -1, 0])
    for i in range(radial_segments):
        indices.extend([bot_center, bot_ring_start + ((i + 1) % radial_segments), bot_ring_start + i])

    return positions, normals, indices


# ---------------------------------------------------------------------------
# Quaternion helpers
# ---------------------------------------------------------------------------

def quat_axis(axis, angle):
    half = angle / 2.0
    s = math.sin(half); c = math.cos(half)
    return {
        "X": (s, 0, 0, c),
        "Y": (0, s, 0, c),
        "Z": (0, 0, s, c),
    }[axis]


IDENTITY_Q = (0.0, 0.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# ★ Exercise animations
#
# Each builder returns a list of channel dicts:
#   { "node": joint_name,
#     "path": "rotation" | "translation",
#     "keys": [(t_seconds, value_tuple), ...]  }
#
# All curves are keyed at a few phases per rep and interpolated linearly.
# Rest poses omitted (joints at identity in the base glb).
# ---------------------------------------------------------------------------

def rep_phase_times(duration, reps, phase_count=5):
    """Yield (rep_index, phase_fraction, t_seconds) for the given rep layout.
       phase_fraction runs through evenly-spaced points in [0, 1]."""
    per_rep = duration / reps
    for r in range(reps):
        for p in range(phase_count):
            frac = p / (phase_count - 1)
            t = r * per_rep + frac * per_rep
            yield r, frac, t


def pose_curve(joint_fn, duration, reps, phase_count=5):
    """Collects (time, value) keys by calling joint_fn(phase) → dict{joint: (axis, angle)|('T', vec3)}
       and returns per-joint channel lists."""
    channels = {}  # (joint, path) -> [(t, value)]
    for _, frac, t in rep_phase_times(duration, reps, phase_count):
        pose = joint_fn(frac)
        for joint, spec in pose.items():
            if spec[0] in ("X", "Y", "Z"):
                axis, angle = spec
                key = (joint, "rotation")
                channels.setdefault(key, []).append((t, quat_axis(axis, angle)))
            elif spec[0] == "T":
                _, vec = spec
                key = (joint, "translation")
                channels.setdefault(key, []).append((t, tuple(vec)))
    # Make sure a key exists at t=0 and t=duration so the clip wraps cleanly
    # (pose_fn should already cover both if phase 0 and 1 are included).
    return channels


def bench_press_pose(phase):
    """Pretend bench press — standing, arms forward at shoulder height, elbows
       flex to bring hands toward chest at the bottom, extend at the top.
       phase 0 = fully extended (top of press), phase 0.5 = hands at chest."""
    # Shoulders raised forward 90° stays constant through the lift.
    # Elbow flex: 0° at top, 90° at bottom, back to 0°. sin(pi*phase) shape.
    elbow_flex = math.radians(85) * math.sin(math.pi * phase)
    return {
        "shoulder_L": ("X", math.radians(-90)),  # arms forward
        "shoulder_R": ("X", math.radians(-90)),
        "elbow_L":    ("X", -elbow_flex),         # flex toward chest
        "elbow_R":    ("X", -elbow_flex),
    }


def bicep_curl_pose(phase):
    """Arms at sides, elbows flex 0° (hands down) → ~130° (hands near shoulders) → 0°."""
    flex = math.radians(130) * math.sin(math.pi * phase)
    return {
        "shoulder_L": ("X", 0.0),   # keep arms down
        "shoulder_R": ("X", 0.0),
        "elbow_L":    ("X", -flex),
        "elbow_R":    ("X", -flex),
    }


def squat_pose(phase):
    """Hip + knee flex together, ankle dorsiflexes slightly. Root dips so the
       feet don't lift off the ground as the knees bend."""
    hip  = math.radians(85) * math.sin(math.pi * phase)
    knee = math.radians(100) * math.sin(math.pi * phase)
    ank  = math.radians(25) * math.sin(math.pi * phase)
    dip_y = -0.42 * math.sin(math.pi * phase)
    return {
        "root":     ("T", (0.0, dip_y, 0.0)),
        "hip_L":    ("X", hip),
        "hip_R":    ("X", hip),
        "knee_L":   ("X", -knee),
        "knee_R":   ("X", -knee),
        "ankle_L":  ("X", -ank),
        "ankle_R":  ("X", -ank),
        # Slight forward chest lean to keep the center of mass over feet
        "spine_mid":   ("X", math.radians(20) * math.sin(math.pi * phase)),
        "spine_upper": ("X", math.radians(10) * math.sin(math.pi * phase)),
    }


def deadlift_pose(phase):
    """Hip hinge — large hip flex, modest knee flex, torso bows forward. Root
       drops a touch so hands sweep down to shin level."""
    hip  = math.radians(90) * math.sin(math.pi * phase)
    knee = math.radians(35) * math.sin(math.pi * phase)
    torso = math.radians(60) * math.sin(math.pi * phase)
    dip_y = -0.18 * math.sin(math.pi * phase)
    # Shoulders rotate forward slightly as arms hang straight down
    shoulder = math.radians(5) * math.sin(math.pi * phase)
    return {
        "root":         ("T", (0.0, dip_y, 0.0)),
        "hip_L":        ("X", hip),
        "hip_R":        ("X", hip),
        "knee_L":       ("X", -knee),
        "knee_R":       ("X", -knee),
        "spine_mid":    ("X", torso * 0.5),
        "spine_upper":  ("X", torso * 0.5),
        "shoulder_L":   ("X", shoulder),
        "shoulder_R":   ("X", shoulder),
    }


EXERCISES = {
    # name: (duration_s, reps, pose_fn)
    "bench_press": (24.0, 8, bench_press_pose),
    "bicep_curl":  (16.0, 8, bicep_curl_pose),
    "squat":       (18.0, 6, squat_pose),
    "deadlift":    (18.0, 6, deadlift_pose),
}


# ---------------------------------------------------------------------------
# Binary packing — glTF 2.0 .glb
# ---------------------------------------------------------------------------

def pack_floats(values):  return struct.pack("<%df" % len(values), *values)
def pack_ushorts(values): return struct.pack("<%dH" % len(values), *values)


def align4(buf, pad_byte=b"\x00"):
    r = len(buf) % 4
    if r: buf += pad_byte * (4 - r)
    return buf


def build_glb():
    positions, normals, indices = cylinder_geometry(radial_segments=14)

    bin_data = bytearray()
    buffer_views = []
    accessors = []

    def add_view(data_bytes, target=None):
        offset = len(bin_data)
        bin_data.extend(data_bytes)
        while len(bin_data) % 4: bin_data.append(0)
        v = {"buffer": 0, "byteOffset": offset, "byteLength": len(data_bytes)}
        if target is not None: v["target"] = target
        return v

    # Shared geometry accessors
    buffer_views.append(add_view(pack_floats(positions), target=34962))
    pos_min = [min(positions[i::3]) for i in range(3)]
    pos_max = [max(positions[i::3]) for i in range(3)]
    accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                      "count": len(positions) // 3, "type": "VEC3",
                      "min": pos_min, "max": pos_max})
    pos_accessor = len(accessors) - 1

    buffer_views.append(add_view(pack_floats(normals), target=34962))
    accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                      "count": len(normals) // 3, "type": "VEC3"})
    nrm_accessor = len(accessors) - 1

    buffer_views.append(add_view(pack_ushorts(indices), target=34963))
    accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5123,
                      "count": len(indices), "type": "SCALAR"})
    idx_accessor = len(accessors) - 1

    # Materials
    materials = [
        {"name": "skin_placeholder",
         "pbrMetallicRoughness": {"baseColorFactor": [0.90, 0.78, 0.72, 0.22],
                                   "metallicFactor": 0.0, "roughnessFactor": 0.9},
         "alphaMode": "BLEND", "doubleSided": True},
        {"name": "muscle_default",
         "pbrMetallicRoughness": {"baseColorFactor": [0.78, 0.18, 0.18, 1.0],
                                   "metallicFactor": 0.0, "roughnessFactor": 0.6}},
    ]
    MAT_SKIN, MAT_MUSCLE = 0, 1

    # Shared meshes — one per material. Every limb/muscle node references these
    # by index, so geometry data is stored once.
    meshes = [
        {"name": "mesh_skin",
         "primitives": [{"attributes": {"POSITION": pos_accessor, "NORMAL": nrm_accessor},
                         "indices": idx_accessor, "material": MAT_SKIN, "mode": 4}]},
        {"name": "mesh_muscle",
         "primitives": [{"attributes": {"POSITION": pos_accessor, "NORMAL": nrm_accessor},
                         "indices": idx_accessor, "material": MAT_MUSCLE, "mode": 4}]},
    ]
    MESH_SKIN, MESH_MUSCLE = 0, 1

    # --- Node graph (joints + their mesh children) ---
    nodes = []
    joint_indices = {}

    def add_node(**kwargs):
        nodes.append(kwargs)
        return len(nodes) - 1

    # Create joints first (empty nodes), parented by iterating the JOINTS list.
    # Each joint's translation is its offset from its parent.
    parent_children = {}
    for name, parent, translation in JOINTS:
        node_idx = add_node(name=name, translation=list(translation))
        joint_indices[name] = node_idx
        if parent is not None:
            parent_children.setdefault(parent, []).append(node_idx)

    # Attach limb (skin) meshes as children of their parent joint
    for name, parent, translation, scale in SKIN_LIMBS:
        node_idx = add_node(name=name, mesh=MESH_SKIN,
                            translation=list(translation), scale=list(scale))
        parent_children.setdefault(parent, []).append(node_idx)

    # Attach muscle meshes as children of their parent joint
    muscle_leaf_names = []
    for name, parent, translation, scale, _group in MUSCLES:
        node_idx = add_node(name=f"muscles/{name}", mesh=MESH_MUSCLE,
                            translation=list(translation), scale=list(scale))
        parent_children.setdefault(parent, []).append(node_idx)
        muscle_leaf_names.append(f"muscles/{name}")

    # Wire children arrays onto each joint node now that we've collected them
    for parent_name, child_list in parent_children.items():
        parent_idx = joint_indices.get(parent_name)
        if parent_idx is None:
            # Shouldn't happen; every parent in JOINTS/SKIN_LIMBS/MUSCLES is a joint
            raise RuntimeError(f"Unknown parent joint: {parent_name!r}")
        nodes[parent_idx].setdefault("children", []).extend(child_list)

    scene_root = joint_indices["root"]

    # --- Animations ---
    animations = []
    for anim_name, (duration, reps, pose_fn) in EXERCISES.items():
        anim_channels = []
        anim_samplers = []
        channels = pose_curve(pose_fn, duration, reps)

        for (joint_name, path), keys in channels.items():
            joint_idx = joint_indices.get(joint_name)
            if joint_idx is None:
                continue

            # Dedup keys with the same time (shouldn't happen with phase sampler but safe)
            keys = sorted(keys, key=lambda k: k[0])

            times = [k[0] for k in keys]
            values = [k[1] for k in keys]
            buffer_views.append(add_view(pack_floats(times)))
            accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                              "count": len(times), "type": "SCALAR",
                              "min": [min(times)], "max": [max(times)]})
            t_accessor = len(accessors) - 1

            if path == "rotation":
                flat = [c for v in values for c in v]
                buffer_views.append(add_view(pack_floats(flat)))
                accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                                  "count": len(values), "type": "VEC4"})
                v_accessor = len(accessors) - 1
            else:  # translation
                flat = [c for v in values for c in v]
                buffer_views.append(add_view(pack_floats(flat)))
                accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                                  "count": len(values), "type": "VEC3"})
                v_accessor = len(accessors) - 1

            sampler_idx = len(anim_samplers)
            anim_samplers.append({"input": t_accessor,
                                   "interpolation": "LINEAR",
                                   "output": v_accessor})
            anim_channels.append({"sampler": sampler_idx,
                                   "target": {"node": joint_idx, "path": path}})

        animations.append({"name": anim_name,
                            "channels": anim_channels,
                            "samplers": anim_samplers})

    gltf = {
        "asset": {"version": "2.0",
                   "generator": "gym-anatomy-viewer rigged humanoid placeholder (NOT anatomically accurate)"},
        "scene": 0,
        "scenes": [{"name": "scene", "nodes": [scene_root]}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}],
        "animations": animations,
    }

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_bytes = align4(json_bytes, pad_byte=b" ")
    bin_bytes = align4(bytes(bin_data), pad_byte=b"\x00")

    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    header = struct.pack("<III", 0x46546C67, 2, total_length)
    json_chunk = struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    bin_chunk = struct.pack("<II", len(bin_bytes), 0x004E4942) + bin_bytes

    OUT_PATH.write_bytes(header + json_chunk + bin_chunk)
    print(f"wrote {OUT_PATH}  ({OUT_PATH.stat().st_size} bytes)")
    print(f"  joints: {len(JOINTS)}   skin: {len(SKIN_LIMBS)}   muscles: {len(MUSCLES)}")
    print(f"  animations: {len(animations)}")
    for a in animations:
        print(f"    {a['name']}: {len(a['channels'])} channels, {len(a['samplers'])} samplers")


if __name__ == "__main__":
    build_glb()

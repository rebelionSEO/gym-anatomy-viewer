#!/usr/bin/env python3
"""
build-mock-real-glb.py
Generates sample_real_anatomy.glb — the rigged humanoid placeholder with
PER-MUSCLE MORPH TARGETS (contract_{muscle_name}_01) so the demo's morph
target code path lights up.

Same joint hierarchy, skin, and animations as build-placeholder-glb.py.
Muscles each get their own glTF mesh entry so each can own a unique
targetNames array; morph POSITION deltas are shared (all muscles inflate
~15% at full influence).

Still NOT anatomically accurate. Cylinders, not muscle bellies.
"""

import json
import math
import struct
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "sample_real_anatomy.glb"

MORPH_INFLATION = 0.15  # delta = base * 0.15 → 15% uniform inflation at full influence

# ---------------------------------------------------------------------------
# Shared layout (keep in sync with build-placeholder-glb.py)
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

MUSCLES = [
    ("pectoralis_major_left",   "spine_upper", (-0.09, 0.13,  0.11), (0.17, 0.12, 0.05), "chest"),
    ("pectoralis_major_right",  "spine_upper", ( 0.09, 0.13,  0.11), (0.17, 0.12, 0.05), "chest"),
    ("biceps_brachii_left_long_head",   "shoulder_L", ( 0.015, -0.14, 0.055), (0.040, 0.14, 0.040), "biceps"),
    ("biceps_brachii_left_short_head",  "shoulder_L", (-0.015, -0.14, 0.055), (0.035, 0.13, 0.040), "biceps"),
    ("biceps_brachii_right_long_head",  "shoulder_R", (-0.015, -0.14, 0.055), (0.040, 0.14, 0.040), "biceps"),
    ("biceps_brachii_right_short_head", "shoulder_R", ( 0.015, -0.14, 0.055), (0.035, 0.13, 0.040), "biceps"),
    ("triceps_brachii_left_long_head",    "shoulder_L", ( 0.00, -0.14, -0.055), (0.040, 0.15, 0.040), "triceps"),
    ("triceps_brachii_left_lateral_head", "shoulder_L", (-0.03, -0.12, -0.045), (0.035, 0.12, 0.040), "triceps"),
    ("triceps_brachii_left_medial_head",  "shoulder_L", ( 0.03, -0.18, -0.045), (0.030, 0.10, 0.035), "triceps"),
    ("triceps_brachii_right_long_head",    "shoulder_R", ( 0.00, -0.14, -0.055), (0.040, 0.15, 0.040), "triceps"),
    ("triceps_brachii_right_lateral_head", "shoulder_R", ( 0.03, -0.12, -0.045), (0.035, 0.12, 0.040), "triceps"),
    ("triceps_brachii_right_medial_head",  "shoulder_R", (-0.03, -0.18, -0.045), (0.030, 0.10, 0.035), "triceps"),
    ("rectus_abdominis",       "spine_mid", ( 0.00,  0.03, 0.10), (0.12, 0.17, 0.03), "core"),
    ("external_oblique_left",  "spine_mid", (-0.11,  0.03, 0.08), (0.06, 0.15, 0.04), "core"),
    ("external_oblique_right", "spine_mid", ( 0.11,  0.03, 0.08), (0.06, 0.15, 0.04), "core"),
    ("internal_oblique_left",  "spine_mid", (-0.09, -0.03, 0.07), (0.05, 0.08, 0.03), "core"),
    ("internal_oblique_right", "spine_mid", ( 0.09, -0.03, 0.07), (0.05, 0.08, 0.03), "core"),
    ("transverse_abdominis",   "spine_mid", ( 0.00,  0.00, 0.09), (0.17, 0.09, 0.025), "core"),
    ("gluteus_maximus_left",  "pelvis", (-0.09, -0.01, -0.11), (0.12, 0.14, 0.07), "glutes"),
    ("gluteus_maximus_right", "pelvis", ( 0.09, -0.01, -0.11), (0.12, 0.14, 0.07), "glutes"),
    ("gluteus_medius_left",   "pelvis", (-0.13,  0.04, -0.06), (0.06, 0.08, 0.05), "glutes"),
    ("gluteus_medius_right",  "pelvis", ( 0.13,  0.04, -0.06), (0.06, 0.08, 0.05), "glutes"),
    ("rectus_femoris_left",      "hip_L", ( 0.00, -0.18, 0.08), (0.055, 0.22, 0.045), "quads"),
    ("rectus_femoris_right",     "hip_R", ( 0.00, -0.18, 0.08), (0.055, 0.22, 0.045), "quads"),
    ("vastus_lateralis_left",    "hip_L", (-0.06, -0.18, 0.05), (0.045, 0.22, 0.055), "quads"),
    ("vastus_lateralis_right",   "hip_R", ( 0.06, -0.18, 0.05), (0.045, 0.22, 0.055), "quads"),
    ("vastus_medialis_left",     "hip_L", ( 0.04, -0.30, 0.06), (0.045, 0.12, 0.045), "quads"),
    ("vastus_medialis_right",    "hip_R", (-0.04, -0.30, 0.06), (0.045, 0.12, 0.045), "quads"),
    ("vastus_intermedius_left",  "hip_L", ( 0.00, -0.18, 0.05), (0.045, 0.18, 0.03),  "quads"),
    ("vastus_intermedius_right", "hip_R", ( 0.00, -0.18, 0.05), (0.045, 0.18, 0.03),  "quads"),
    ("biceps_femoris_left",   "hip_L", (-0.04, -0.22, -0.08), (0.050, 0.20, 0.045), "hamstrings"),
    ("biceps_femoris_right",  "hip_R", ( 0.04, -0.22, -0.08), (0.050, 0.20, 0.045), "hamstrings"),
    ("semitendinosus_left",   "hip_L", ( 0.02, -0.22, -0.08), (0.035, 0.20, 0.035), "hamstrings"),
    ("semitendinosus_right",  "hip_R", (-0.02, -0.22, -0.08), (0.035, 0.20, 0.035), "hamstrings"),
    ("semimembranosus_left",  "hip_L", (-0.02, -0.28, -0.09), (0.040, 0.14, 0.035), "hamstrings"),
    ("semimembranosus_right", "hip_R", ( 0.02, -0.28, -0.09), (0.040, 0.14, 0.035), "hamstrings"),
    ("gastrocnemius_left",  "knee_L", ( 0.00, -0.13, -0.06), (0.070, 0.14, 0.050), "calves"),
    ("gastrocnemius_right", "knee_R", ( 0.00, -0.13, -0.06), (0.070, 0.14, 0.050), "calves"),
    ("soleus_left",         "knee_L", ( 0.00, -0.28, -0.05), (0.055, 0.12, 0.045), "calves"),
    ("soleus_right",        "knee_R", ( 0.00, -0.28, -0.05), (0.055, 0.12, 0.045), "calves"),
]


def cylinder_geometry(radial_segments=14):
    positions = []; normals = []; indices = []
    for ring_y in (0.5, -0.5):
        for i in range(radial_segments):
            theta = 2 * math.pi * i / radial_segments
            x = 0.5 * math.cos(theta); z = 0.5 * math.sin(theta)
            positions.extend([x, ring_y, z])
            normals.extend([math.cos(theta), 0, math.sin(theta)])
    for i in range(radial_segments):
        a = i; b = (i + 1) % radial_segments
        c = i + radial_segments; d = ((i + 1) % radial_segments) + radial_segments
        indices.extend([a, c, b, b, c, d])
    top_center = len(positions) // 3
    positions.extend([0, 0.5, 0]); normals.extend([0, 1, 0])
    top_ring_start = len(positions) // 3
    for i in range(radial_segments):
        theta = 2 * math.pi * i / radial_segments
        positions.extend([0.5 * math.cos(theta), 0.5, 0.5 * math.sin(theta)])
        normals.extend([0, 1, 0])
    for i in range(radial_segments):
        indices.extend([top_center, top_ring_start + i, top_ring_start + ((i + 1) % radial_segments)])
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


def quat_axis(axis, angle):
    half = angle / 2.0
    s = math.sin(half); c = math.cos(half)
    return {"X": (s, 0, 0, c), "Y": (0, s, 0, c), "Z": (0, 0, s, c)}[axis]


def rep_phase_times(duration, reps, phase_count=5):
    per_rep = duration / reps
    for r in range(reps):
        for p in range(phase_count):
            frac = p / (phase_count - 1)
            t = r * per_rep + frac * per_rep
            yield r, frac, t


def pose_curve(joint_fn, duration, reps, phase_count=5):
    channels = {}
    for _, frac, t in rep_phase_times(duration, reps, phase_count):
        pose = joint_fn(frac)
        for joint, spec in pose.items():
            if spec[0] in ("X", "Y", "Z"):
                axis, angle = spec
                channels.setdefault((joint, "rotation"), []).append((t, quat_axis(axis, angle)))
            elif spec[0] == "T":
                _, vec = spec
                channels.setdefault((joint, "translation"), []).append((t, tuple(vec)))
    return channels


def bench_press_pose(phase):
    elbow_flex = math.radians(85) * math.sin(math.pi * phase)
    return {"shoulder_L": ("X", math.radians(-90)), "shoulder_R": ("X", math.radians(-90)),
            "elbow_L": ("X", -elbow_flex), "elbow_R": ("X", -elbow_flex)}


def bicep_curl_pose(phase):
    flex = math.radians(130) * math.sin(math.pi * phase)
    return {"shoulder_L": ("X", 0.0), "shoulder_R": ("X", 0.0),
            "elbow_L": ("X", -flex), "elbow_R": ("X", -flex)}


def squat_pose(phase):
    hip  = math.radians(85) * math.sin(math.pi * phase)
    knee = math.radians(100) * math.sin(math.pi * phase)
    ank  = math.radians(25) * math.sin(math.pi * phase)
    dip_y = -0.42 * math.sin(math.pi * phase)
    return {"root": ("T", (0.0, dip_y, 0.0)),
            "hip_L": ("X", hip), "hip_R": ("X", hip),
            "knee_L": ("X", -knee), "knee_R": ("X", -knee),
            "ankle_L": ("X", -ank), "ankle_R": ("X", -ank),
            "spine_mid":   ("X", math.radians(20) * math.sin(math.pi * phase)),
            "spine_upper": ("X", math.radians(10) * math.sin(math.pi * phase))}


def deadlift_pose(phase):
    hip  = math.radians(90) * math.sin(math.pi * phase)
    knee = math.radians(35) * math.sin(math.pi * phase)
    torso = math.radians(60) * math.sin(math.pi * phase)
    dip_y = -0.18 * math.sin(math.pi * phase)
    shoulder = math.radians(5) * math.sin(math.pi * phase)
    return {"root": ("T", (0.0, dip_y, 0.0)),
            "hip_L": ("X", hip), "hip_R": ("X", hip),
            "knee_L": ("X", -knee), "knee_R": ("X", -knee),
            "spine_mid": ("X", torso * 0.5), "spine_upper": ("X", torso * 0.5),
            "shoulder_L": ("X", shoulder), "shoulder_R": ("X", shoulder)}


EXERCISES = {
    "bench_press": (24.0, 8, bench_press_pose),
    "bicep_curl":  (16.0, 8, bicep_curl_pose),
    "squat":       (18.0, 6, squat_pose),
    "deadlift":    (18.0, 6, deadlift_pose),
}


def pack_floats(values):  return struct.pack("<%df" % len(values), *values)
def pack_ushorts(values): return struct.pack("<%dH" % len(values), *values)


def align4(buf, pad_byte=b"\x00"):
    r = len(buf) % 4
    if r: buf += pad_byte * (4 - r)
    return buf


def build_glb():
    positions, normals, indices = cylinder_geometry(radial_segments=14)
    delta_positions = [p * MORPH_INFLATION for p in positions]

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

    buffer_views.append(add_view(pack_floats(delta_positions)))
    dmin = [min(delta_positions[i::3]) for i in range(3)]
    dmax = [max(delta_positions[i::3]) for i in range(3)]
    accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                      "count": len(delta_positions) // 3, "type": "VEC3",
                      "min": dmin, "max": dmax})
    delta_pos_accessor = len(accessors) - 1

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

    meshes = [{"name": "mesh_skin",
                "primitives": [{"attributes": {"POSITION": pos_accessor, "NORMAL": nrm_accessor},
                                "indices": idx_accessor, "material": MAT_SKIN, "mode": 4}]}]
    MESH_SKIN = 0

    # One mesh per muscle so each gets its own targetNames
    muscle_mesh_indices = {}
    for name, *_rest in [(m[0],) for m in MUSCLES]:
        meshes.append({
            "name": f"mesh_{name}",
            "primitives": [{"attributes": {"POSITION": pos_accessor, "NORMAL": nrm_accessor},
                            "indices": idx_accessor,
                            "material": MAT_MUSCLE,
                            "mode": 4,
                            "targets": [{"POSITION": delta_pos_accessor}]}],
            "weights": [0.0],
            "extras": {"targetNames": [f"contract_{name}_01"]},
        })
        muscle_mesh_indices[name] = len(meshes) - 1

    nodes = []
    joint_indices = {}
    parent_children = {}

    def add_node(**kwargs):
        nodes.append(kwargs)
        return len(nodes) - 1

    for name, parent, translation in JOINTS:
        node_idx = add_node(name=name, translation=list(translation))
        joint_indices[name] = node_idx
        if parent is not None:
            parent_children.setdefault(parent, []).append(node_idx)

    for name, parent, translation, scale in SKIN_LIMBS:
        node_idx = add_node(name=name, mesh=MESH_SKIN,
                            translation=list(translation), scale=list(scale))
        parent_children.setdefault(parent, []).append(node_idx)

    for name, parent, translation, scale, _group in MUSCLES:
        node_idx = add_node(name=f"muscles/{name}",
                            mesh=muscle_mesh_indices[name],
                            translation=list(translation), scale=list(scale))
        parent_children.setdefault(parent, []).append(node_idx)

    for parent_name, child_list in parent_children.items():
        parent_idx = joint_indices.get(parent_name)
        if parent_idx is None:
            raise RuntimeError(f"Unknown parent joint: {parent_name!r}")
        nodes[parent_idx].setdefault("children", []).extend(child_list)

    scene_root = joint_indices["root"]

    animations = []
    for anim_name, (duration, reps, pose_fn) in EXERCISES.items():
        anim_channels = []
        anim_samplers = []
        channels = pose_curve(pose_fn, duration, reps)

        for (joint_name, path), keys in channels.items():
            joint_idx = joint_indices.get(joint_name)
            if joint_idx is None:
                continue
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
            else:
                flat = [c for v in values for c in v]
                buffer_views.append(add_view(pack_floats(flat)))
                accessors.append({"bufferView": len(buffer_views) - 1, "componentType": 5126,
                                  "count": len(values), "type": "VEC3"})
                v_accessor = len(accessors) - 1

            sampler_idx = len(anim_samplers)
            anim_samplers.append({"input": t_accessor, "interpolation": "LINEAR", "output": v_accessor})
            anim_channels.append({"sampler": sampler_idx,
                                   "target": {"node": joint_idx, "path": path}})

        animations.append({"name": anim_name, "channels": anim_channels, "samplers": anim_samplers})

    gltf = {
        "asset": {"version": "2.0",
                   "generator": "gym-anatomy-viewer rigged humanoid + morph targets (NOT anatomically accurate)"},
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
    print(f"  joints: {len(JOINTS)}   skin: {len(SKIN_LIMBS)}   muscles: {len(MUSCLES)} (each with morph target)")
    print(f"  animations: {len(animations)}")


if __name__ == "__main__":
    build_glb()

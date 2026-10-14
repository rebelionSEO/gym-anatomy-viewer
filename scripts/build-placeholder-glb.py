#!/usr/bin/env python3
"""
build-placeholder-glb.py
Generates human_anatomy_gym_v1.glb as a wiring placeholder — primitive boxes
positioned where muscles roughly sit, named with the canonical "muscles/{name}"
convention so a real anatomy glb can drop in later without changing the demo.

This is NOT anatomically accurate geometry. It exists so the viewer, JSON files,
UI toggles, and animation playback can be exercised end-to-end.
"""

import json
import math
import struct
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "human_anatomy_gym_v1.glb"


# ---------------------------------------------------------------------------
# Scene definition — approximate placements on a ~1.8 m humanoid, origin at
# feet, facing +Z. Only placeholder cubes; swap for real meshes later.
# ---------------------------------------------------------------------------

# (name, position, scale, group)
MUSCLES = [
    # chest
    ("pectoralis_major_left",   (-0.11, 1.38, 0.08),  (0.17, 0.11, 0.06), "chest"),
    ("pectoralis_major_right",  ( 0.11, 1.38, 0.08),  (0.17, 0.11, 0.06), "chest"),
    # biceps
    ("biceps_brachii_left_long_head",   (-0.30, 1.30, 0.03), (0.045, 0.14, 0.04), "biceps"),
    ("biceps_brachii_left_short_head",  (-0.26, 1.30, 0.04), (0.040, 0.13, 0.04), "biceps"),
    ("biceps_brachii_right_long_head",  ( 0.30, 1.30, 0.03), (0.045, 0.14, 0.04), "biceps"),
    ("biceps_brachii_right_short_head", ( 0.26, 1.30, 0.04), (0.040, 0.13, 0.04), "biceps"),
    # triceps
    ("triceps_brachii_left_long_head",    (-0.28, 1.30, -0.04), (0.040, 0.15, 0.04), "triceps"),
    ("triceps_brachii_left_lateral_head", (-0.32, 1.32, -0.03), (0.035, 0.13, 0.04), "triceps"),
    ("triceps_brachii_left_medial_head",  (-0.28, 1.25, -0.04), (0.035, 0.10, 0.03), "triceps"),
    ("triceps_brachii_right_long_head",    ( 0.28, 1.30, -0.04), (0.040, 0.15, 0.04), "triceps"),
    ("triceps_brachii_right_lateral_head", ( 0.32, 1.32, -0.03), (0.035, 0.13, 0.04), "triceps"),
    ("triceps_brachii_right_medial_head",  ( 0.28, 1.25, -0.04), (0.035, 0.10, 0.03), "triceps"),
    # core
    ("rectus_abdominis",         ( 0.00, 1.10,  0.10), (0.10, 0.15, 0.04), "core"),
    ("external_oblique_left",   (-0.11, 1.10,  0.07), (0.05, 0.14, 0.04), "core"),
    ("external_oblique_right",  ( 0.11, 1.10,  0.07), (0.05, 0.14, 0.04), "core"),
    ("internal_oblique_left",   (-0.09, 1.03,  0.06), (0.04, 0.08, 0.03), "core"),
    ("internal_oblique_right",  ( 0.09, 1.03,  0.06), (0.04, 0.08, 0.03), "core"),
    ("transverse_abdominis",    ( 0.00, 1.05,  0.08), (0.14, 0.08, 0.025), "core"),
    # glutes
    ("gluteus_maximus_left",   (-0.09, 0.92, -0.12), (0.09, 0.11, 0.07), "glutes"),
    ("gluteus_maximus_right",  ( 0.09, 0.92, -0.12), (0.09, 0.11, 0.07), "glutes"),
    ("gluteus_medius_left",    (-0.12, 1.00, -0.08), (0.05, 0.07, 0.05), "glutes"),
    ("gluteus_medius_right",   ( 0.12, 1.00, -0.08), (0.05, 0.07, 0.05), "glutes"),
    # quads
    ("rectus_femoris_left",      (-0.10, 0.65,  0.07), (0.05, 0.18, 0.04), "quads"),
    ("rectus_femoris_right",     ( 0.10, 0.65,  0.07), (0.05, 0.18, 0.04), "quads"),
    ("vastus_lateralis_left",    (-0.14, 0.65,  0.04), (0.04, 0.18, 0.05), "quads"),
    ("vastus_lateralis_right",   ( 0.14, 0.65,  0.04), (0.04, 0.18, 0.05), "quads"),
    ("vastus_medialis_left",     (-0.07, 0.55,  0.05), (0.04, 0.11, 0.04), "quads"),
    ("vastus_medialis_right",    ( 0.07, 0.55,  0.05), (0.04, 0.11, 0.04), "quads"),
    ("vastus_intermedius_left",  (-0.10, 0.65,  0.05), (0.04, 0.17, 0.03), "quads"),
    ("vastus_intermedius_right", ( 0.10, 0.65,  0.05), (0.04, 0.17, 0.03), "quads"),
    # hamstrings
    ("biceps_femoris_left",   (-0.12, 0.65, -0.07), (0.045, 0.17, 0.04), "hamstrings"),
    ("biceps_femoris_right",  ( 0.12, 0.65, -0.07), (0.045, 0.17, 0.04), "hamstrings"),
    ("semitendinosus_left",   (-0.08, 0.65, -0.07), (0.030, 0.17, 0.03), "hamstrings"),
    ("semitendinosus_right",  ( 0.08, 0.65, -0.07), (0.030, 0.17, 0.03), "hamstrings"),
    ("semimembranosus_left",  (-0.10, 0.60, -0.08), (0.035, 0.14, 0.03), "hamstrings"),
    ("semimembranosus_right", ( 0.10, 0.60, -0.08), (0.035, 0.14, 0.03), "hamstrings"),
    # calves
    ("gastrocnemius_left",   (-0.10, 0.25, -0.06), (0.045, 0.12, 0.045), "calves"),
    ("gastrocnemius_right",  ( 0.10, 0.25, -0.06), (0.045, 0.12, 0.045), "calves"),
    ("soleus_left",          (-0.10, 0.18, -0.05), (0.040, 0.10, 0.040), "calves"),
    ("soleus_right",         ( 0.10, 0.18, -0.05), (0.040, 0.10, 0.040), "calves"),
]

# Semi-transparent "skin" placeholder — body-shaped boxes.
SKIN_PARTS = [
    ("torso",            ( 0.00, 1.15,  0.00), (0.22, 0.50, 0.14)),
    ("head",             ( 0.00, 1.70,  0.03), (0.11, 0.14, 0.11)),
    ("upper_arm_left",   (-0.28, 1.30,  0.00), (0.055, 0.17, 0.055)),
    ("upper_arm_right",  ( 0.28, 1.30,  0.00), (0.055, 0.17, 0.055)),
    ("forearm_left",     (-0.28, 1.00,  0.03), (0.045, 0.15, 0.045)),
    ("forearm_right",    ( 0.28, 1.00,  0.03), (0.045, 0.15, 0.045)),
    ("hand_left",        (-0.28, 0.80,  0.03), (0.040, 0.08, 0.030)),
    ("hand_right",       ( 0.28, 0.80,  0.03), (0.040, 0.08, 0.030)),
    ("upper_leg_left",   (-0.11, 0.63,  0.00), (0.08, 0.22, 0.09)),
    ("upper_leg_right",  ( 0.11, 0.63,  0.00), (0.08, 0.22, 0.09)),
    ("lower_leg_left",   (-0.11, 0.22,  0.00), (0.065, 0.18, 0.07)),
    ("lower_leg_right",  ( 0.11, 0.22,  0.00), (0.065, 0.18, 0.07)),
    ("foot_left",        (-0.11, 0.03,  0.05), (0.055, 0.03, 0.11)),
    ("foot_right",       ( 0.11, 0.03,  0.05), (0.055, 0.03, 0.11)),
]

# Simple skeleton placeholder — single vertical rod. Marker only.
SKELETON_PARTS = [
    ("spine", (0.00, 1.00, -0.02), (0.015, 0.70, 0.015)),
]


# ---------------------------------------------------------------------------
# Box primitive — 24 verts (4 per face so normals are flat), 36 indices.
# ---------------------------------------------------------------------------

def box_geometry():
    # Half-extents are 0.5 so the box is 1x1x1; node scale sizes it.
    h = 0.5
    faces = [
        # (normal, 4 corner positions ccw)
        ((0, 0,  1), [(-h, -h,  h), ( h, -h,  h), ( h,  h,  h), (-h,  h,  h)]),  # +Z
        ((0, 0, -1), [( h, -h, -h), (-h, -h, -h), (-h,  h, -h), ( h,  h, -h)]),  # -Z
        ((1, 0, 0),  [( h, -h,  h), ( h, -h, -h), ( h,  h, -h), ( h,  h,  h)]),  # +X
        ((-1, 0, 0), [(-h, -h, -h), (-h, -h,  h), (-h,  h,  h), (-h,  h, -h)]),  # -X
        ((0, 1, 0),  [(-h,  h,  h), ( h,  h,  h), ( h,  h, -h), (-h,  h, -h)]),  # +Y
        ((0, -1, 0), [(-h, -h, -h), ( h, -h, -h), ( h, -h,  h), (-h, -h,  h)]),  # -Y
    ]
    positions = []
    normals = []
    indices = []
    i = 0
    for n, corners in faces:
        for c in corners:
            positions.extend(c)
            normals.extend(n)
        indices.extend([i, i + 1, i + 2, i, i + 2, i + 3])
        i += 4
    return positions, normals, indices


# ---------------------------------------------------------------------------
# Animation keyframes — four exercise clips. These animate the root node only
# (position + rotation) so the figure moves in a lift-like pattern. Muscle-
# level activation is driven by muscles_activation.json in the demo, not by
# glb animation channels.
# ---------------------------------------------------------------------------

def rep_pattern(duration, rep_count, amp_y, lean_x_deg=0.0):
    """Keyframes for a rep: start at 0, bottom at mid, back to 0."""
    times = []
    translations = []  # [x,y,z] per key
    rotations = []     # quaternion [x,y,z,w] per key
    per_rep = duration / rep_count
    lean_rad = math.radians(lean_x_deg)
    for r in range(rep_count):
        t0 = r * per_rep
        t_mid = t0 + per_rep / 2.0
        times.append(t0)
        translations.append((0.0, 0.0, 0.0))
        rotations.append(quat_from_x(0.0))
        times.append(t_mid)
        translations.append((0.0, -amp_y, 0.0))
        rotations.append(quat_from_x(lean_rad))
    # final rest keyframe
    times.append(duration)
    translations.append((0.0, 0.0, 0.0))
    rotations.append(quat_from_x(0.0))
    return times, translations, rotations


def quat_from_x(angle_rad):
    s = math.sin(angle_rad / 2.0)
    c = math.cos(angle_rad / 2.0)
    return (s, 0.0, 0.0, c)


ANIMATIONS = {
    # name: (duration, reps, y_amplitude, forward_lean_deg)
    "bench_press": (24.0, 8, 0.00, 0.0),   # subtle — placeholder root doesn't move much
    "bicep_curl":  (16.0, 8, 0.00, 0.0),   # subtle
    "squat":       (18.0, 6, 0.30, 0.0),   # deep knee bend represented as root drop
    "deadlift":    (18.0, 6, 0.20, 25.0),  # root drop + forward lean
}


# ---------------------------------------------------------------------------
# Binary packing — glTF 2.0 .glb
# ---------------------------------------------------------------------------

def pack_floats(values):
    return struct.pack("<%df" % len(values), *values)


def pack_ushorts(values):
    return struct.pack("<%dH" % len(values), *values)


def align4(buf, pad_byte=b"\x00"):
    r = len(buf) % 4
    if r:
        buf += pad_byte * (4 - r)
    return buf


def build_glb():
    positions, normals, indices = box_geometry()

    bin_data = bytearray()

    def add_view(data_bytes, target=None):
        offset = len(bin_data)
        bin_data.extend(data_bytes)
        # pad bufferView to 4-byte boundary
        while len(bin_data) % 4:
            bin_data.append(0)
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data_bytes)}
        if target is not None:
            view["target"] = target
        return view

    buffer_views = []
    accessors = []

    # mesh data
    pos_view = add_view(pack_floats(positions), target=34962)  # ARRAY_BUFFER
    buffer_views.append(pos_view)
    pos_min = [min(positions[i::3]) for i in range(3)]
    pos_max = [max(positions[i::3]) for i in range(3)]
    accessors.append({
        "bufferView": len(buffer_views) - 1,
        "componentType": 5126,  # FLOAT
        "count": len(positions) // 3,
        "type": "VEC3",
        "min": pos_min,
        "max": pos_max,
    })
    pos_accessor = len(accessors) - 1

    nrm_view = add_view(pack_floats(normals), target=34962)
    buffer_views.append(nrm_view)
    accessors.append({
        "bufferView": len(buffer_views) - 1,
        "componentType": 5126,
        "count": len(normals) // 3,
        "type": "VEC3",
    })
    nrm_accessor = len(accessors) - 1

    idx_view = add_view(pack_ushorts(indices), target=34963)  # ELEMENT_ARRAY_BUFFER
    buffer_views.append(idx_view)
    accessors.append({
        "bufferView": len(buffer_views) - 1,
        "componentType": 5123,  # UNSIGNED_SHORT
        "count": len(indices),
        "type": "SCALAR",
    })
    idx_accessor = len(accessors) - 1

    # materials
    materials = [
        {  # 0: skin (translucent grey)
            "name": "skin_placeholder",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.90, 0.78, 0.72, 0.22],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.9,
            },
            "alphaMode": "BLEND",
            "doubleSided": True,
        },
        {  # 1: muscle default
            "name": "muscle_default",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.78, 0.18, 0.18, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.6,
            },
        },
        {  # 2: skeleton
            "name": "skeleton_placeholder",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.95, 0.95, 0.90, 1.0],
                "metallicFactor": 0.1,
                "roughnessFactor": 0.4,
            },
        },
    ]

    # three meshes = same primitive, different material binding
    meshes = []
    for mat_idx in [0, 1, 2]:
        meshes.append({
            "name": ["mesh_skin", "mesh_muscle", "mesh_skeleton"][mat_idx],
            "primitives": [{
                "attributes": {"POSITION": pos_accessor, "NORMAL": nrm_accessor},
                "indices": idx_accessor,
                "material": mat_idx,
                "mode": 4,  # TRIANGLES
            }],
        })
    MESH_SKIN, MESH_MUSCLE, MESH_SKELETON = 0, 1, 2

    # ---- nodes ----------------------------------------------------------
    nodes = []

    def add_node(name, children=None, mesh=None, translation=None, scale=None, rotation=None):
        node = {"name": name}
        if children:
            node["children"] = children
        if mesh is not None:
            node["mesh"] = mesh
        if translation is not None:
            node["translation"] = list(translation)
        if scale is not None:
            node["scale"] = list(scale)
        if rotation is not None:
            node["rotation"] = list(rotation)
        nodes.append(node)
        return len(nodes) - 1

    # Build leaf nodes first, group containers last.
    skin_leaf_ids = [add_node(f"skin/{name}", mesh=MESH_SKIN, translation=t, scale=s) for name, t, s in SKIN_PARTS]
    skeleton_leaf_ids = [add_node(f"skeleton/{name}", mesh=MESH_SKELETON, translation=t, scale=s) for name, t, s in SKELETON_PARTS]
    muscle_leaf_ids = [add_node(f"muscles/{name}", mesh=MESH_MUSCLE, translation=t, scale=s) for name, t, s, _ in MUSCLES]

    # Group containers
    human_skin_id = add_node("human/skin", children=skin_leaf_ids)
    human_skeleton_id = add_node("human/skeleton", children=skeleton_leaf_ids)
    muscles_root_id = add_node("muscles", children=muscle_leaf_ids)
    human_root_id = add_node("human", children=[human_skin_id, human_skeleton_id])
    scene_root_id = add_node("root", children=[human_root_id, muscles_root_id], translation=(0.0, 0.0, 0.0), rotation=quat_from_x(0.0))

    # ---- animations -----------------------------------------------------
    animations = []
    for anim_name, (duration, reps, amp_y, lean) in ANIMATIONS.items():
        times, translations, rotations = rep_pattern(duration, reps, amp_y, lean)

        # time accessor
        t_bytes = pack_floats(times)
        t_view = add_view(t_bytes)
        buffer_views.append(t_view)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "componentType": 5126,
            "count": len(times),
            "type": "SCALAR",
            "min": [min(times)],
            "max": [max(times)],
        })
        t_accessor = len(accessors) - 1

        # translation accessor
        tr_flat = [c for v in translations for c in v]
        tr_view = add_view(pack_floats(tr_flat))
        buffer_views.append(tr_view)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "componentType": 5126,
            "count": len(translations),
            "type": "VEC3",
        })
        tr_accessor = len(accessors) - 1

        # rotation accessor
        rt_flat = [c for q in rotations for c in q]
        rt_view = add_view(pack_floats(rt_flat))
        buffer_views.append(rt_view)
        accessors.append({
            "bufferView": len(buffer_views) - 1,
            "componentType": 5126,
            "count": len(rotations),
            "type": "VEC4",
        })
        rt_accessor = len(accessors) - 1

        animations.append({
            "name": anim_name,
            "channels": [
                {"sampler": 0, "target": {"node": scene_root_id, "path": "translation"}},
                {"sampler": 1, "target": {"node": scene_root_id, "path": "rotation"}},
            ],
            "samplers": [
                {"input": t_accessor, "interpolation": "LINEAR", "output": tr_accessor},
                {"input": t_accessor, "interpolation": "LINEAR", "output": rt_accessor},
            ],
        })

    # ---- assemble JSON -------------------------------------------------
    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "gym-anatomy-viewer placeholder builder (not anatomically accurate)",
        },
        "scene": 0,
        "scenes": [{"name": "scene", "nodes": [scene_root_id]}],
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
    print(f"  nodes: {len(nodes)}   muscles: {len(muscle_leaf_ids)}   animations: {len(animations)}")


if __name__ == "__main__":
    build_glb()

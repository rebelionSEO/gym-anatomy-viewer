#!/usr/bin/env python3
"""
build-mock-real-glb.py
Generates sample_real_anatomy.glb at repo root — a *mock* "real anatomy"
file for exercising the demo's morph-target code path. Geometry is still
primitive boxes (so this is NOT anatomically accurate either), but each
muscle mesh exposes a morph target named contract_{muscle_name}_01 whose
delta inflates the mesh by ~15% when fully active. The demo's activation
driver picks up the morph targets automatically; the color-tint fallback
is not used for muscles mapped to this file.

Mirrors build-placeholder-glb.py in structure. Duplication is intentional
to keep each script short and readable.
"""

import json
import math
import struct
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent.parent / "sample_real_anatomy.glb"


# Reuse the same canonical muscle list and placements as the placeholder.
MUSCLES = [
    ("pectoralis_major_left",   (-0.11, 1.38, 0.08),  (0.17, 0.11, 0.06), "chest"),
    ("pectoralis_major_right",  ( 0.11, 1.38, 0.08),  (0.17, 0.11, 0.06), "chest"),
    ("biceps_brachii_left_long_head",   (-0.30, 1.30, 0.03), (0.045, 0.14, 0.04), "biceps"),
    ("biceps_brachii_left_short_head",  (-0.26, 1.30, 0.04), (0.040, 0.13, 0.04), "biceps"),
    ("biceps_brachii_right_long_head",  ( 0.30, 1.30, 0.03), (0.045, 0.14, 0.04), "biceps"),
    ("biceps_brachii_right_short_head", ( 0.26, 1.30, 0.04), (0.040, 0.13, 0.04), "biceps"),
    ("triceps_brachii_left_long_head",    (-0.28, 1.30, -0.04), (0.040, 0.15, 0.04), "triceps"),
    ("triceps_brachii_left_lateral_head", (-0.32, 1.32, -0.03), (0.035, 0.13, 0.04), "triceps"),
    ("triceps_brachii_left_medial_head",  (-0.28, 1.25, -0.04), (0.035, 0.10, 0.03), "triceps"),
    ("triceps_brachii_right_long_head",    ( 0.28, 1.30, -0.04), (0.040, 0.15, 0.04), "triceps"),
    ("triceps_brachii_right_lateral_head", ( 0.32, 1.32, -0.03), (0.035, 0.13, 0.04), "triceps"),
    ("triceps_brachii_right_medial_head",  ( 0.28, 1.25, -0.04), (0.035, 0.10, 0.03), "triceps"),
    ("rectus_abdominis",         ( 0.00, 1.10,  0.10), (0.10, 0.15, 0.04), "core"),
    ("external_oblique_left",   (-0.11, 1.10,  0.07), (0.05, 0.14, 0.04), "core"),
    ("external_oblique_right",  ( 0.11, 1.10,  0.07), (0.05, 0.14, 0.04), "core"),
    ("internal_oblique_left",   (-0.09, 1.03,  0.06), (0.04, 0.08, 0.03), "core"),
    ("internal_oblique_right",  ( 0.09, 1.03,  0.06), (0.04, 0.08, 0.03), "core"),
    ("transverse_abdominis",    ( 0.00, 1.05,  0.08), (0.14, 0.08, 0.025), "core"),
    ("gluteus_maximus_left",   (-0.09, 0.92, -0.12), (0.09, 0.11, 0.07), "glutes"),
    ("gluteus_maximus_right",  ( 0.09, 0.92, -0.12), (0.09, 0.11, 0.07), "glutes"),
    ("gluteus_medius_left",    (-0.12, 1.00, -0.08), (0.05, 0.07, 0.05), "glutes"),
    ("gluteus_medius_right",   ( 0.12, 1.00, -0.08), (0.05, 0.07, 0.05), "glutes"),
    ("rectus_femoris_left",      (-0.10, 0.65,  0.07), (0.05, 0.18, 0.04), "quads"),
    ("rectus_femoris_right",     ( 0.10, 0.65,  0.07), (0.05, 0.18, 0.04), "quads"),
    ("vastus_lateralis_left",    (-0.14, 0.65,  0.04), (0.04, 0.18, 0.05), "quads"),
    ("vastus_lateralis_right",   ( 0.14, 0.65,  0.04), (0.04, 0.18, 0.05), "quads"),
    ("vastus_medialis_left",     (-0.07, 0.55,  0.05), (0.04, 0.11, 0.04), "quads"),
    ("vastus_medialis_right",    ( 0.07, 0.55,  0.05), (0.04, 0.11, 0.04), "quads"),
    ("vastus_intermedius_left",  (-0.10, 0.65,  0.05), (0.04, 0.17, 0.03), "quads"),
    ("vastus_intermedius_right", ( 0.10, 0.65,  0.05), (0.04, 0.17, 0.03), "quads"),
    ("biceps_femoris_left",   (-0.12, 0.65, -0.07), (0.045, 0.17, 0.04), "hamstrings"),
    ("biceps_femoris_right",  ( 0.12, 0.65, -0.07), (0.045, 0.17, 0.04), "hamstrings"),
    ("semitendinosus_left",   (-0.08, 0.65, -0.07), (0.030, 0.17, 0.03), "hamstrings"),
    ("semitendinosus_right",  ( 0.08, 0.65, -0.07), (0.030, 0.17, 0.03), "hamstrings"),
    ("semimembranosus_left",  (-0.10, 0.60, -0.08), (0.035, 0.14, 0.03), "hamstrings"),
    ("semimembranosus_right", ( 0.10, 0.60, -0.08), (0.035, 0.14, 0.03), "hamstrings"),
    ("gastrocnemius_left",   (-0.10, 0.25, -0.06), (0.045, 0.12, 0.045), "calves"),
    ("gastrocnemius_right",  ( 0.10, 0.25, -0.06), (0.045, 0.12, 0.045), "calves"),
    ("soleus_left",          (-0.10, 0.18, -0.05), (0.040, 0.10, 0.040), "calves"),
    ("soleus_right",         ( 0.10, 0.18, -0.05), (0.040, 0.10, 0.040), "calves"),
]

# Keep a torso + head skin shell so the figure reads as humanoid.
SKIN_PARTS = [
    ("torso",           ( 0.00, 1.15,  0.00), (0.22, 0.50, 0.14)),
    ("head",            ( 0.00, 1.70,  0.03), (0.11, 0.14, 0.11)),
    ("upper_arm_left",  (-0.28, 1.30,  0.00), (0.055, 0.17, 0.055)),
    ("upper_arm_right", ( 0.28, 1.30,  0.00), (0.055, 0.17, 0.055)),
    ("upper_leg_left",  (-0.11, 0.63,  0.00), (0.08, 0.22, 0.09)),
    ("upper_leg_right", ( 0.11, 0.63,  0.00), (0.08, 0.22, 0.09)),
    ("lower_leg_left",  (-0.11, 0.22,  0.00), (0.065, 0.18, 0.07)),
    ("lower_leg_right", ( 0.11, 0.22,  0.00), (0.065, 0.18, 0.07)),
]

MORPH_INFLATION = 0.15  # deltas = base * 0.15 → 15% uniform inflation at full influence


def box_geometry():
    h = 0.5
    faces = [
        ((0, 0,  1), [(-h, -h,  h), ( h, -h,  h), ( h,  h,  h), (-h,  h,  h)]),
        ((0, 0, -1), [( h, -h, -h), (-h, -h, -h), (-h,  h, -h), ( h,  h, -h)]),
        ((1, 0, 0),  [( h, -h,  h), ( h, -h, -h), ( h,  h, -h), ( h,  h,  h)]),
        ((-1, 0, 0), [(-h, -h, -h), (-h, -h,  h), (-h,  h,  h), (-h,  h, -h)]),
        ((0, 1, 0),  [(-h,  h,  h), ( h,  h,  h), ( h,  h, -h), (-h,  h, -h)]),
        ((0, -1, 0), [(-h, -h, -h), ( h, -h, -h), ( h, -h,  h), (-h, -h,  h)]),
    ]
    positions, normals, indices = [], [], []
    i = 0
    for n, corners in faces:
        for c in corners:
            positions.extend(c)
            normals.extend(n)
        indices.extend([i, i + 1, i + 2, i, i + 2, i + 3])
        i += 4
    return positions, normals, indices


def rep_pattern(duration, reps, amp_y, lean_x_deg=0.0):
    times, translations, rotations = [], [], []
    per_rep = duration / reps
    lean_rad = math.radians(lean_x_deg)
    for r in range(reps):
        t0 = r * per_rep
        t_mid = t0 + per_rep / 2.0
        times.append(t0);     translations.append((0.0, 0.0, 0.0));          rotations.append(quat_from_x(0.0))
        times.append(t_mid);  translations.append((0.0, -amp_y, 0.0));       rotations.append(quat_from_x(lean_rad))
    times.append(duration); translations.append((0.0, 0.0, 0.0)); rotations.append(quat_from_x(0.0))
    return times, translations, rotations


def quat_from_x(angle_rad):
    s = math.sin(angle_rad / 2.0); c = math.cos(angle_rad / 2.0)
    return (s, 0.0, 0.0, c)


ANIMATIONS = {
    "bench_press": (24.0, 8, 0.00, 0.0),
    "bicep_curl":  (16.0, 8, 0.00, 0.0),
    "squat":       (18.0, 6, 0.30, 0.0),
    "deadlift":    (18.0, 6, 0.20, 25.0),
}


def pack_floats(values): return struct.pack("<%df" % len(values), *values)
def pack_ushorts(values): return struct.pack("<%dH" % len(values), *values)


def align4(buf, pad_byte=b"\x00"):
    r = len(buf) % 4
    if r: buf += pad_byte * (4 - r)
    return buf


def build_glb():
    positions, normals, indices = box_geometry()
    # Morph delta positions: base * MORPH_INFLATION. Same vertex order as base.
    delta_positions = [p * MORPH_INFLATION for p in positions]

    bin_data = bytearray()
    buffer_views = []
    accessors = []

    def add_view(data_bytes, target=None):
        offset = len(bin_data)
        bin_data.extend(data_bytes)
        while len(bin_data) % 4: bin_data.append(0)
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data_bytes)}
        if target is not None: view["target"] = target
        return view

    # Shared base accessors (0..2)
    buffer_views.append(add_view(pack_floats(positions), target=34962))
    pos_min = [min(positions[i::3]) for i in range(3)]
    pos_max = [max(positions[i::3]) for i in range(3)]
    accessors.append({
        "bufferView": len(buffer_views) - 1, "componentType": 5126,
        "count": len(positions) // 3, "type": "VEC3",
        "min": pos_min, "max": pos_max,
    })
    pos_accessor = len(accessors) - 1

    buffer_views.append(add_view(pack_floats(normals), target=34962))
    accessors.append({
        "bufferView": len(buffer_views) - 1, "componentType": 5126,
        "count": len(normals) // 3, "type": "VEC3",
    })
    nrm_accessor = len(accessors) - 1

    buffer_views.append(add_view(pack_ushorts(indices), target=34963))
    accessors.append({
        "bufferView": len(buffer_views) - 1, "componentType": 5123,
        "count": len(indices), "type": "SCALAR",
    })
    idx_accessor = len(accessors) - 1

    # Morph delta POSITION accessor (shared by every muscle mesh)
    buffer_views.append(add_view(pack_floats(delta_positions)))
    dmin = [min(delta_positions[i::3]) for i in range(3)]
    dmax = [max(delta_positions[i::3]) for i in range(3)]
    accessors.append({
        "bufferView": len(buffer_views) - 1, "componentType": 5126,
        "count": len(delta_positions) // 3, "type": "VEC3",
        "min": dmin, "max": dmax,
    })
    delta_pos_accessor = len(accessors) - 1

    # Materials
    materials = [
        {   # 0: skin
            "name": "skin_placeholder",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.90, 0.78, 0.72, 0.22],
                "metallicFactor": 0.0, "roughnessFactor": 0.9,
            },
            "alphaMode": "BLEND", "doubleSided": True,
        },
        {   # 1: muscle
            "name": "muscle_default",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.78, 0.18, 0.18, 1.0],
                "metallicFactor": 0.0, "roughnessFactor": 0.6,
            },
        },
    ]
    MAT_SKIN, MAT_MUSCLE = 0, 1

    # One mesh per muscle (so each gets its own targetNames) + one skin mesh.
    meshes = []

    # Skin mesh (no morph targets — only muscles contract)
    meshes.append({
        "name": "mesh_skin",
        "primitives": [{
            "attributes": {"POSITION": pos_accessor, "NORMAL": nrm_accessor},
            "indices": idx_accessor,
            "material": MAT_SKIN,
            "mode": 4,
        }],
    })
    MESH_SKIN = 0

    muscle_mesh_indices = {}
    for name, *_rest in [(m[0],) for m in MUSCLES]:
        meshes.append({
            "name": f"mesh_{name}",
            "primitives": [{
                "attributes": {"POSITION": pos_accessor, "NORMAL": nrm_accessor},
                "indices": idx_accessor,
                "material": MAT_MUSCLE,
                "mode": 4,
                "targets": [{"POSITION": delta_pos_accessor}],
            }],
            "weights": [0.0],
            "extras": {"targetNames": [f"contract_{name}_01"]},
        })
        muscle_mesh_indices[name] = len(meshes) - 1

    # Nodes
    nodes = []
    def add_node(name, children=None, mesh=None, translation=None, scale=None, rotation=None):
        node = {"name": name}
        if children: node["children"] = children
        if mesh is not None: node["mesh"] = mesh
        if translation is not None: node["translation"] = list(translation)
        if scale is not None: node["scale"] = list(scale)
        if rotation is not None: node["rotation"] = list(rotation)
        nodes.append(node)
        return len(nodes) - 1

    skin_leaf_ids = [add_node(f"skin/{n}", mesh=MESH_SKIN, translation=t, scale=s) for n, t, s in SKIN_PARTS]
    muscle_leaf_ids = []
    for name, t, s, _group in MUSCLES:
        muscle_leaf_ids.append(add_node(
            f"muscles/{name}",
            mesh=muscle_mesh_indices[name],
            translation=t, scale=s,
        ))

    human_skin_id = add_node("human/skin", children=skin_leaf_ids)
    muscles_root_id = add_node("muscles", children=muscle_leaf_ids)
    human_root_id = add_node("human", children=[human_skin_id])
    scene_root_id = add_node("root", children=[human_root_id, muscles_root_id],
                             translation=(0.0, 0.0, 0.0), rotation=quat_from_x(0.0))

    # Animations (root-level translation/rotation only, same shape as placeholder)
    animations = []
    for anim_name, (duration, reps, amp_y, lean) in ANIMATIONS.items():
        times, translations, rotations = rep_pattern(duration, reps, amp_y, lean)

        t_bytes = pack_floats(times)
        buffer_views.append(add_view(t_bytes))
        accessors.append({
            "bufferView": len(buffer_views) - 1, "componentType": 5126,
            "count": len(times), "type": "SCALAR",
            "min": [min(times)], "max": [max(times)],
        })
        t_accessor = len(accessors) - 1

        tr_flat = [c for v in translations for c in v]
        buffer_views.append(add_view(pack_floats(tr_flat)))
        accessors.append({
            "bufferView": len(buffer_views) - 1, "componentType": 5126,
            "count": len(translations), "type": "VEC3",
        })
        tr_accessor = len(accessors) - 1

        rt_flat = [c for q in rotations for c in q]
        buffer_views.append(add_view(pack_floats(rt_flat)))
        accessors.append({
            "bufferView": len(buffer_views) - 1, "componentType": 5126,
            "count": len(rotations), "type": "VEC4",
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

    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "gym-anatomy-viewer mock-real builder (NOT anatomically accurate, with morph targets)",
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
    print(f"  muscles: {len(MUSCLES)}   morph targets: {len(MUSCLES)}  (one per muscle)")
    print(f"  animations: {len(animations)}")


if __name__ == "__main__":
    build_glb()

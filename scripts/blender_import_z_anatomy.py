"""
blender_import_z_anatomy.py
----------------------------
Helper script to run INSIDE Blender against the Z-Anatomy project
(https://github.com/LluisV/Z-Anatomy, CC BY-SA).

What it does
    1. Loads ui_manifest.json from this repo to get the 40 canonical
       muscle keys (muscles/pectoralis_major_left, etc.).
    2. Walks every mesh object in the Blender scene.
    3. Normalizes names (lowercase, strip prefixes, collapse separators)
       and matches each canonical muscle key to the best candidate mesh.
    4. Prints a report: exact matches, fuzzy candidates, unmatched muscles,
       unmatched meshes.
    5. If APPLY is True, renames matched meshes to muscles/<canonical>
       so the glb exporter emits them with the names the viewer expects.

What it does NOT do (manual Blender work still needed)
    * Rigging — add a Rigify / Auto-Rig Pro humanoid rig to the muscles
    * Mixamo clip retargeting — download bench_press / bicep_curl / squat /
      deadlift clips, retarget to the rig, rename the actions
    * glb export — File → Export → glTF 2.0, tick Include → Animations
    See scripts/BLENDER_WORKFLOW.md for the step-by-step.

How to run
    - Open Blender, open the Z-Anatomy muscular-system file
    - Scripting workspace → Open → point at this file
    - Set APPLY = True below if you want it to actually rename
    - Edit MANIFEST_PATH below to point at this repo's ui_manifest.json
    - Click Run Script
    - Read the console output
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG — edit these two lines for your setup
# ---------------------------------------------------------------------------

# Absolute path to ui_manifest.json in your clone of gym-anatomy-viewer.
# Example:  Path("/Users/you/code/gym-anatomy-viewer/ui_manifest.json")
MANIFEST_PATH = Path.home() / "gym-anatomy-viewer" / "ui_manifest.json"

# False = dry run (print the report, change nothing).  True = actually rename.
APPLY = False

# ---------------------------------------------------------------------------
# Blender import — guarded so the file is at least parseable outside Blender
# ---------------------------------------------------------------------------

try:
    import bpy  # noqa: F401 — Blender's own namespace
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False
    print("[warn] bpy not available — this script is a no-op outside Blender.")
    print("        Open it inside Blender's Scripting workspace and click Run Script.")


# ---------------------------------------------------------------------------
# Name normalization — mirrors demo/app.js:normalizeName so a mesh that
# auto-matches here will also auto-match in the viewer.
# ---------------------------------------------------------------------------

def normalize(name):
    s = str(name or "").lower()
    s = re.sub(r"^muscles[/\.]", "", s)
    s = re.sub(r"[\.\-\s]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


# Z-Anatomy sometimes decorates names with laterality tokens, anatomical
# qualifiers, or Latin suffixes. Rough aliases to help the normalizer land
# a match. Extend this map as you find Z-Anatomy names that should map to a
# canonical muscle key.
NAME_ALIASES = {
    # Latin / qualifiers → canonical fragments
    "sinister": "left",
    "sinistra": "left",
    "dexter":   "right",
    "dextra":   "right",
    "caput_longum":   "long_head",
    "caput_breve":    "short_head",
    "caput_laterale": "lateral_head",
    "caput_mediale":  "medial_head",
    "muscle":   "",
    "musculus": "",
}


def apply_aliases(normalized):
    """After basic normalization, swap known Latin/anatomical tokens for the
       canonical English fragments. Repeat until stable."""
    prev = None
    while normalized != prev:
        prev = normalized
        for src, dst in NAME_ALIASES.items():
            normalized = normalized.replace(src, dst)
        normalized = re.sub(r"_+", "_", normalized).strip("_")
    # Blender's convention: trailing .L / .R → _l / _r. Expand to _left / _right
    # so these line up with the canonical muscle keys. Only applied as a
    # SUFFIX so interior "l"/"r" letters are left alone.
    normalized = re.sub(r"_l$", "_left",  normalized)
    normalized = re.sub(r"_r$", "_right", normalized)
    return normalized


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def load_muscle_keys():
    if not MANIFEST_PATH.exists():
        print(f"[error] ui_manifest.json not found at: {MANIFEST_PATH}")
        print("        Edit MANIFEST_PATH at the top of this script.")
        return None
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    keys = []
    for group in manifest.get("groups", {}).values():
        keys.extend(group.get("muscles", []))
    return keys


# ---------------------------------------------------------------------------
# Scene walk
# ---------------------------------------------------------------------------

def collect_mesh_names():
    """Returns [(obj, name)] for every mesh object in the Blender scene."""
    if not IN_BLENDER:
        return []
    out = []
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            out.append((obj, obj.name))
    return out


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def match_meshes_to_keys(muscle_keys, mesh_entries):
    """Returns dict muscle_key -> (obj, mesh_name, confidence_label)."""
    # Build normalized index of mesh names (with alias substitution).
    by_norm = defaultdict(list)
    for obj, name in mesh_entries:
        norm = apply_aliases(normalize(name))
        by_norm[norm].append((obj, name))

    result = {}
    for key in muscle_keys:
        norm = apply_aliases(normalize(key))
        if norm in by_norm:
            # Exact normalized match
            obj, name = by_norm[norm][0]
            result[key] = (obj, name, "exact")
            continue

        # Fuzzy: find mesh whose normalized tokens are a superset of the key's
        key_tokens = set(norm.split("_"))
        best = None
        best_score = 0
        for mesh_norm, candidates in by_norm.items():
            mesh_tokens = set(mesh_norm.split("_"))
            overlap = len(key_tokens & mesh_tokens)
            # Prefer meshes that contain ALL the key's tokens, in the smallest
            # mesh name (less likely to be a wrong-side or wrong-head match).
            if overlap == len(key_tokens):
                score = overlap - 0.01 * len(mesh_tokens)
                if score > best_score:
                    best_score = score
                    best = candidates[0]
        if best is not None:
            obj, name = best
            result[key] = (obj, name, "fuzzy")

    return result


# ---------------------------------------------------------------------------
# Report + rename
# ---------------------------------------------------------------------------

def print_report(muscle_keys, mesh_entries, matches):
    exact = [k for k in muscle_keys if matches.get(k, (None, None, ""))[2] == "exact"]
    fuzzy = [k for k in muscle_keys if matches.get(k, (None, None, ""))[2] == "fuzzy"]
    missing = [k for k in muscle_keys if k not in matches]
    used = {obj.name for obj, _, _ in matches.values()}
    unused_meshes = [name for _obj, name in mesh_entries if name not in used]

    print(f"\n{'=' * 72}")
    print("Z-Anatomy → gym-anatomy-viewer mapping report")
    print(f"{'=' * 72}")
    print(f"Canonical muscle keys to map: {len(muscle_keys)}")
    print(f"Mesh objects in scene:        {len(mesh_entries)}")
    print(f"Exact matches:  {len(exact)}")
    print(f"Fuzzy matches:  {len(fuzzy)}")
    print(f"Unmatched keys: {len(missing)}")
    print()

    print("--- EXACT MATCHES ---")
    for k in exact:
        _obj, src, _ = matches[k]
        print(f"  {k:50s}  ←  {src}")

    print("\n--- FUZZY MATCHES  (review these!) ---")
    for k in fuzzy:
        _obj, src, _ = matches[k]
        print(f"  {k:50s}  ←  {src}")

    print("\n--- UNMATCHED MUSCLE KEYS  (will not be renamed) ---")
    for k in missing:
        print(f"  {k}")

    print(f"\n--- UNUSED MESH OBJECTS (sample up to 25) ---  total: {len(unused_meshes)}")
    for name in unused_meshes[:25]:
        print(f"  {name}")
    if len(unused_meshes) > 25:
        print(f"  … {len(unused_meshes) - 25} more")

    print(f"\n{'=' * 72}")
    print(f"APPLY mode: {'ON — renaming meshes' if APPLY else 'OFF — dry run, no changes'}")
    print(f"{'=' * 72}\n")


def apply_renames(matches):
    """Rename matched meshes to muscles/<canonical>. Idempotent — safe to re-run."""
    if not IN_BLENDER:
        return 0
    renamed = 0
    for key, (obj, src, _conf) in matches.items():
        target = key  # muscle_key already has the muscles/ prefix
        if obj.name == target:
            continue
        # Avoid Blender's unique-name suffix fight: temporarily reserve the name
        existing = bpy.data.objects.get(target)
        if existing is not None and existing is not obj:
            # Something else already owns the target name; let Blender resolve
            # by renaming the existing one with a .conflict suffix first.
            existing.name = target + ".conflict"
        obj.name = target
        renamed += 1
    return renamed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("blender_import_z_anatomy.py — starting")

    muscle_keys = load_muscle_keys()
    if not muscle_keys:
        return
    print(f"Loaded {len(muscle_keys)} canonical muscle keys from {MANIFEST_PATH}")

    mesh_entries = collect_mesh_names()
    if not mesh_entries:
        print("[warn] No mesh objects found in bpy.data.objects.")
        print("        Open the Z-Anatomy file (or ensure the muscular system")
        print("        collection is loaded) and run again.")
        return

    matches = match_meshes_to_keys(muscle_keys, mesh_entries)
    print_report(muscle_keys, mesh_entries, matches)

    if APPLY:
        renamed = apply_renames(matches)
        print(f"Renamed {renamed} mesh objects to muscles/<canonical> form.")
        print("Next: add a humanoid rig (Rigify or Auto-Rig Pro), bind the")
        print("muscles to it, retarget your Mixamo clips, then File → Export →")
        print("glTF 2.0 with Include → Animations ticked.")
    else:
        print("Dry run complete. Set APPLY = True at the top of this script to")
        print("actually rename the matched meshes.")


if __name__ == "__main__" or IN_BLENDER:
    main()

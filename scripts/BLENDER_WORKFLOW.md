# Z-Anatomy → gym-anatomy-viewer: Blender workflow

End-to-end steps to replace the placeholder figure with a real muscle-anatomy
glb sourced from Z-Anatomy. Honest about which steps are automated and which
are Blender clicking.

## Big picture

```
┌─────────────────┐    rename    ┌──────────────┐   rig +    ┌───────────────┐
│  Z-Anatomy      │  (automated  │  Named       │   retarget │  Rigged +     │
│  (.blend file)  │   by this    │  meshes      │  (manual   │  animated     │
│                 │   script)    │              │   Blender) │  .blend       │
└────────┬────────┘              └──────┬───────┘            └───────┬───────┘
         │                              │                            │
         │                              │                            │ File → Export → glTF
         │                              │                            ▼
         │                              │                    ┌───────────────┐
         │                              │                    │ anatomy.glb   │
         │                              │                    └───────┬───────┘
         │                              │                            │ drop into
         │                              │                            │ gym-anatomy-viewer
         │                              │                            ▼
         │                              │                    ┌───────────────┐
         │                              │                    │ live viewer   │
         │                              │                    │ shows your    │
         │                              │                    │ real anatomy  │
         │                              │                    └───────────────┘
```

The automated step is **mesh renaming** so the glb's node names match the
`muscles/{canonical_name}` convention the viewer looks for. Everything else
is a Blender session you drive.

## Step 1 — Install Blender (free)

Download from <https://www.blender.org/download/> and install. 4.0 or newer
is fine. Nothing to configure.

## Step 2 — Get Z-Anatomy

Clone or download: <https://github.com/LluisV/Z-Anatomy>

License is CC BY-SA 4.0 — if you ship the resulting glb, attribute Z-Anatomy
in your README and keep the share-alike licensing.

The repo ships multiple `.blend` files broken down by system (muscular,
skeletal, cardiovascular, etc). You want the **muscular** file. The exact
filename changes between Z-Anatomy releases, so look for whichever `.blend`
contains the muscles.

## Step 3 — Open in Blender and inspect

Open the muscular `.blend` file. In the **Outliner** panel you'll see a tree
of collections (anatomical regions) and underneath them, mesh objects named
in anatomical English or Latin — things like `Pectoralis.major.L`,
`Biceps.brachii.caput.longum.sinister`, etc.

Spend 60 seconds eyeballing the names so you know what naming convention
Z-Anatomy is using in this release. If it's radically different from what
the sample list below shows, you may need to extend the `NAME_ALIASES` dict
in `blender_import_z_anatomy.py` for your file.

## Step 4 — Run the renamer (automated)

1. Open the **Scripting** workspace tab at the top of Blender.
2. Click **Open** in the text editor panel. Point at this file:
   `scripts/blender_import_z_anatomy.py` in your clone of
   `gym-anatomy-viewer`.
3. Edit the two lines at the top of the script:
   - `MANIFEST_PATH` — absolute path to `ui_manifest.json` in your clone
   - `APPLY = False` — leave as `False` for the first pass (dry run)
4. Click **Run Script** (▶). Open the **Window → Toggle System Console** on
   Windows, or run Blender from a terminal on macOS / Linux so you can see
   the printed report.

The report will show four buckets:
- **Exact matches** — the mesh name normalized to the canonical form
  directly. Trustworthy.
- **Fuzzy matches** — mesh name's tokens are a superset of the canonical
  key's tokens. Usually right; worth a glance.
- **Unmatched muscle keys** — canonical muscles the script couldn't find a
  mesh for. You'll resolve these by hand in Step 5.
- **Unused meshes** — meshes the script left alone. Usually bones, nerves,
  skin, or extra anatomical detail that isn't in `ui_manifest.json`.

Once the report looks reasonable, set `APPLY = True` at the top of the
script and run it again. The matched meshes get renamed to
`muscles/<canonical_name>`. **Idempotent** — safe to re-run.

If a bunch of fuzzy matches look wrong, don't apply yet. Extend the
`NAME_ALIASES` dict with the Z-Anatomy-specific tokens you're seeing, then
re-run the dry pass.

## Step 5 — Manually resolve unmatched muscles

For each muscle in the unmatched list:
1. Search the Outliner (`Ctrl-F` in the Outliner panel) for the muscle's
   Latin or anatomical name.
2. Double-click the object and rename it to the canonical form:
   `muscles/pectoralis_major_left`, `muscles/gluteus_medius_right`, etc.

Also decide what to do with meshes you *don't* want in the viewer
(internal organs, extra heads of muscles you're ignoring). Options:
- Delete them (`X` → confirm) if you don't need them
- Move them to a hidden collection you don't export

## Step 6 — Rig the figure (manual)

This is where the real time goes. Options from easiest to best:

**6a — Rigify (built into Blender)**

1. Enable the Rigify add-on: `Edit → Preferences → Add-ons`, search
   "Rigify", tick it.
2. `Add → Armature → Human (Meta-Rig)` — Rigify's humanoid skeleton
   appears in T-pose.
3. Position the meta-rig to roughly match the Z-Anatomy figure (scale,
   limb positions).
4. In the armature's Properties → Rigify, click **Generate Rig**.
5. Select every muscle mesh + the generated rig, parent with **Automatic
   Weights**. Expect to clean up weights per muscle — some will deform
   wrong.

**6b — Auto-Rig Pro** (paid add-on, ~$40, much faster)

If you're going to do a lot of this, ARP's auto-weighting is dramatically
better than Rigify's defaults. Worth it if you value your time.

## Step 7 — Add exercise animations (manual)

You need four clips named exactly: `bench_press`, `bicep_curl`, `squat`,
`deadlift`. Three sources:

**7a — Mixamo** (free, requires an Adobe account)
1. <https://www.mixamo.com> → search "bench press", "bicep curl", etc.
2. Download each as **.fbx for Blender** with skin — gives you a mesh
   + armature + animation.
3. Install the **Mixamo add-on** or use **Rokoko Retarget** to transfer
   the Mixamo armature's animation onto your Rigify rig.
4. In the **Dope Sheet → Action Editor**, rename each action to the
   exact clip name the viewer expects (`bench_press` etc.).

**7b — Author by hand** (slow but gives you full control)

Set keyframes in **Pose Mode** — rotate shoulders / elbows / hips / knees
to shape each lift. 8 reps × 3s each per clip. Save each as its own
action.

**7c — Buy mocap bundles** (fastest)

Sketchfab, ActorCore, or Unity Asset Store have gym-motion packs for
~$10-$40. Same retarget step as 7a.

## Step 8 — Export glb

1. Select the root armature (and nothing above it in the hierarchy).
2. `File → Export → glTF 2.0 (.glb/.gltf)`
3. In the export panel on the right:
   - **Include → Limit to: Selected Objects + Visible Objects** — ticked
   - **Transform → +Y Up** — ticked (default)
   - **Geometry → Apply Modifiers** — ticked
   - **Animation → Animations** — ticked (critical — this is what carries
     your `bench_press` / `squat` etc. actions into the glb)
   - **Animation → Export Deformation Bones Only** — ticked (shrinks file)
4. Save as `my_real_anatomy.glb` (or whatever).

Expect 1–5 MB for a muscle-anatomy figure. If it's dramatically bigger,
check that you're not accidentally including bones from unused rigs.

## Step 9 — Drop into the viewer

Open <https://rebelionseo.github.io/gym-anatomy-viewer/demo/> (or your
local server). Drag the glb onto the viewer, or use **Choose .glb**.

If your Step-4 renaming landed cleanly, you'll see
`40 / 40 muscles mapped (<filename>)`. If not, open **Edit mapping…** and
assign the stragglers using the hover-outline preview. The mapping is
saved to `localStorage` so you don't repeat the work on the next load.

## Troubleshooting

**The report shows 0 exact matches**

Z-Anatomy's naming scheme in your release doesn't normalize cleanly to the
canonical form. Open two or three mesh names from the Outliner, run them
through the normalizer by hand (see the normalize/apply_aliases functions
in the script), and extend `NAME_ALIASES` with whatever Latin fragment
needs mapping.

**Mesh renames fine but viewer shows the figure as a frozen T-pose**

The glb exported without animations. Re-export with
**Animation → Animations** ticked. Also confirm your actions are named
*exactly* `bench_press`, `bicep_curl`, `squat`, `deadlift` — the viewer
reads clip names from `ui_manifest.json`.

**Muscles move but with the wrong limb**

Weight painting error on that muscle. In Blender, select the muscle →
Weight Paint mode → paint the weights so the muscle moves with its parent
bone.

**File is huge (> 50 MB)**

You exported too much (bones from unused rigs, all of Z-Anatomy instead of
muscular, or high-poly subdivision). In the exporter, limit to visible
objects and apply modifiers; delete unused Z-Anatomy collections before
exporting.

## Attribution

If you ship a glb derived from Z-Anatomy, add this line to your project's
credits:

> Muscle meshes adapted from Z-Anatomy (© Lluís Vinent), licensed under
> CC BY-SA 4.0: <https://github.com/LluisV/Z-Anatomy>

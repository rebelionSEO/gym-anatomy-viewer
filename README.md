# gym-anatomy-viewer

An interactive viewer for gym-movement muscle activation. The viewer, JSON
pipeline, and UI are production-shaped; the 3D model is a **wiring
placeholder** — primitive boxes positioned where muscles roughly sit, named
with the canonical `muscles/{name}` convention so a real rigged anatomy glb
can drop in with no demo code changes.

## What's real vs. placeholder

| Component | Status | Notes |
|---|---|---|
| `demo/` three.js viewer | real | rotate/pan/zoom, group toggles, isolate, animation scrub, activation chart |
| `ui_manifest.json`, `metadata.json` | real | muscle groups, colors, camera presets, canonical animation durations |
| `muscles_activation.json` | **approximation** | heuristic sin² pulse curves informed by general EMG literature on compound lifts, not from measured data |
| `human_anatomy_gym_v1.glb` — node graph | real | 40 named `muscles/{canonical_name}` nodes, 4 named clips, standard glTF 2.0 |
| `human_anatomy_gym_v1.glb` — geometry | **placeholder** | box primitives at approximate anatomical positions; NOT anatomically accurate |
| `human_anatomy_gym_v1.glb` — rigging | **absent** | no humanoid skeleton, no skinning, no IK |
| Blendshapes per muscle (`contract_{name}_01`) | **absent** | tint-based heatmap used instead; see "Swap in real anatomy" |
| LODs (LOD0/LOD1/LOD2), KTX2 textures | **absent** | placeholder is tiny (~13 KB) so LODs aren't meaningful |
| FBX / USDZ export | **absent** | nothing to export yet |

Everything marked "placeholder" or "absent" is honest about what this build
is: a working pipeline waiting on real anatomy. The next section explains the
swap-in.

## Files produced

```
gym-anatomy-viewer/
├── README.md                     ← you are here
├── human_anatomy_gym_v1.glb      ← placeholder model (~13 KB)
├── muscles_activation.json       ← per-lift activation curves (~42 KB)
├── ui_manifest.json              ← groups, colors, camera presets, controls
├── metadata.json                 ← time step, durations, build notes
├── scripts/
│   ├── build-placeholder-glb.py  ← regenerates the glb
│   └── build-activation-json.py  ← regenerates the activation JSON
└── demo/
    ├── index.html
    ├── app.js
    └── style.css
```

## Run the demo

Any static file server works. From the project root:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000/demo/>.

The demo loads the glb, both JSON files, and shows:

- rotate / pan / zoom camera (OrbitControls)
- play / pause / scrub a named animation clip
- toggle muscle groups
- isolate a single muscle
- transparent / solid / hidden skin shell
- **drag-and-drop a custom `.glb`** onto the viewer (or use the file picker)
  — the viewer tears down the current model and mounts the new one
- **tolerant auto-mapping** between muscle keys and the loaded glb's mesh
  names; override any mapping in the **Edit mapping…** modal, saved per
  filename in `localStorage`
- **morph target driving**: if a mapped mesh has morph targets like
  `contract_{muscle}_01`, activation drives `morphTargetInfluences`
  directly; otherwise the viewer falls back to color tint + emissive glow +
  a small uniform scale pulse
- an overlay chart of the selected muscle's activation vs. time with a live
  playhead
- a floating `?` pill opens a modal that labels the demo as placeholder
  hardware

See [`CHANGELOG.md`](CHANGELOG.md) for the full change list and
[`TESTING.md`](TESTING.md) for a manual test checklist.

## Loading snippet (three.js)

```js
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const [gltf, activation, manifest] = await Promise.all([
  new GLTFLoader().loadAsync('human_anatomy_gym_v1.glb'),
  fetch('muscles_activation.json').then(r => r.json()),
  fetch('ui_manifest.json').then(r => r.json()),
]);

const mixer = new THREE.AnimationMixer(gltf.scene);
mixer.clipAction(gltf.animations.find(c => c.name === 'squat')).play();

const pec = gltf.scene.getObjectByName('muscles/pectoralis_major_left');
```

See `demo/app.js` for the full flow (activation sampling, tinting, chart).

## Swap in real anatomy

Replace `human_anatomy_gym_v1.glb` with a real rigged anatomy glb and the
demo keeps working, provided it follows this contract:

1. **Node names.** Every muscle mesh is reachable at a node named
   `muscles/{canonical_name}` using the names in `ui_manifest.json`
   (`muscles/pectoralis_major_left`, `muscles/biceps_brachii_right_long_head`,
   etc.). Three.js finds them with `scene.getObjectByName()`.
2. **Animation clip names.** `bench_press`, `bicep_curl`, `squat`,
   `deadlift`. Durations should match `metadata.json` (or update it).
3. **Optional — blendshapes.** If each muscle mesh exposes
   `contract_{canonical_name}_01` morph targets, swap the tint-based heatmap
   in `app.js:updateActivationTint()` for `morphTargetInfluences`. Current
   fallback is color-based so the demo works without them.
4. **Optional — skinning.** The container nodes `human/skin`,
   `human/skeleton`, and `muscles` are expected; the viewer tolerates them
   being absent.

Candidates for sourcing a real base (CC-licensed, requires rigging and
muscle-mesh breakout in Blender):

- **BodyParts3D** (CC BY-SA, Life Science Databases Consortium — DBCLS,
  Japan) — anatomical reference mesh.
- **Z-Anatomy** (github.com/LluisV/Z-Anatomy, CC BY-SA 4.0) — open-source
  anatomy project with per-muscle meshes.

For animations, open-source mocap sources include **Mixamo** (free with
Adobe account, non-sublicensable), **CMU Motion Capture Database**, and
**AMASS** (research-license, body-shape-neutral mocap).

## Anatomical references (used for intensity assignments only)

The activation intensities in `scripts/build-activation-json.py` are
approximations drawn from general knowledge of compound-lift biomechanics
rather than specific peer-reviewed EMG studies. If this ships beyond a demo,
the intensity map should be re-grounded against literature such as:

- Netter FH. *Atlas of Human Anatomy*. (muscle origin/insertion, line of pull)
- Standring S, ed. *Gray's Anatomy*, 42nd ed., 2020. (reference anatomy)
- Schoenfeld BJ. *Science and Development of Muscle Hypertrophy*, 2016.
  (prime-mover vs. synergist patterns in bench, squat, deadlift, curl)
- Boeckh-Behrens WU, Buskies W. *Fitness-Krafttraining*. (EMG surveys of
  common gym lifts — German sports science reference)
- Clark DR, et al. "Muscle activation in the loaded free barbell squat: a
  brief review." *J Strength Cond Res* 2012. (squat EMG patterns)

**None of these were consulted directly for this build.** Any clinical,
educational, or safety-critical use must re-derive the intensity map from
primary sources.

## Why each muscle is tagged "active" (notes per clip)

- **bench_press** — primary: `pectoralis_major` (horizontal shoulder
  adduction, concentric), `triceps_brachii` (elbow extension at lockout).
  Core as isometric stabilizer.
- **bicep_curl** — primary: `biceps_brachii` long + short head (elbow
  flexion, forearm supination). Triceps baseline (co-contraction). Core low.
- **squat** — primary: `vastus_*` (knee extension, concentric), `rectus_
  femoris` (knee extension), `gluteus_maximus` (hip extension). Hamstrings
  as co-contractors; calves ankle-stabilize; core braces.
- **deadlift** — primary: hamstrings (`biceps_femoris`, `semitendinosus`,
  `semimembranosus`) and `gluteus_maximus` (hip extension from flexion).
  Quads at breakoff; `transverse_abdominis` and obliques brace. No erector
  spinae in current muscle list — a real build should add it.

## Licensing

- `human_anatomy_gym_v1.glb`, `muscles_activation.json`, `ui_manifest.json`,
  `metadata.json`, and everything in `scripts/` and `demo/` are generated
  originals for this project. Use at will; verify for any clinical or
  educational use.
- No third-party models, textures, or mocap are bundled.
- three.js loaded from the official jsDelivr CDN at demo runtime (MIT).

## Known gaps vs. the original brief

For transparency — these items in the original spec are **not** in this
build and need a real 3D pipeline (Blender + a rigged anatomy source) to
produce:

- Rigged humanoid skeleton with skinning and consistent weights
- Per-muscle blendshapes (`contract_{name}_01` / `_02`)
- Realistic mocap-grade keyframed joint animations
- LOD0 (~150k) / LOD1 (~60–80k) / LOD2 (~20–30k) tris
- KTX2/Basis textures, normal maps, roughness maps
- FBX animation-only export for Unity
- USDZ for iOS AR

The scaffolding here is designed so adding any of these later is a
drop-in — the demo code paths exist and will light up as the glb gains
features.

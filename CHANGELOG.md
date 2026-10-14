# Changelog

All notable changes to this project live here. Dates in ISO format.
Format roughly follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Drag-and-drop and file-input loading of custom `.glb` files directly in
  the viewer; no code edit required to try a new model.
- Tolerant auto-mapping between `ui_manifest.json` muscle keys and the
  loaded glb's mesh names (lowercase, strip `muscles/` prefix, collapse
  separators to `_`). Mappings persist per filename in `localStorage` so
  they survive reloads.
- Mapping UI modal: one row per muscle key with a dropdown of every mesh in
  the current glb. "Re-run auto match", "Clear all", and "Save & apply"
  controls. Rows are color-coded (unmapped / auto / manual).
- Morph target activation path. If a mapped mesh exposes morph targets
  named `contract_{muscle}_01` (or any variant listed in
  `morphKeyCandidates`), the viewer drives `morphTargetInfluences` from the
  activation curves instead of using color tint. Primitive-geometry models
  without morph targets automatically use the fallback.
- Fallback visualization gained a small uniform scale pulse (base × 1..1.06)
  on top of the existing tint + emissive glow so activation reads even in
  low-light angles.
- Lightweight toast notifications (info / warn / error) for glb load
  success/failure and mapping save confirmation.
- Help pill (floating `?` button) opens a modal that explicitly labels the
  demo as placeholder hardware and summarizes the swap-in contract.
- `TESTING.md` with the full manual test plan.

### Changed
- Model lifecycle refactored into a central `state` object plus
  `mountGltf()` / `tearDownCurrentModel()`. Swapping glbs is a clean reset:
  animations, materials, and node references are torn down and rebuilt.
- Clip list in the Animation dropdown is now driven from the loaded glb's
  own `gltf.animations`. Clips named in `ui_manifest.animations` come first;
  any extras from the glb are appended.
- Group toggles, isolate, skin/skeleton toggles, and the activation chart
  all re-bind to the current model on every load.

### Still placeholder / not addressed
- Geometry remains primitive boxes. No change to anatomical accuracy.
- Activation values in `muscles_activation.json` remain heuristic
  approximations; the README's "not anatomically accurate" disclaimer
  stands unchanged.
- No rigged humanoid skeleton, blendshape authoring, LODs, FBX, or USDZ
  export.

## [0.1.0] — 2026-10-13

### Added
- Initial scaffold: bundled placeholder `human_anatomy_gym_v1.glb`
  (40 named muscle nodes, 4 named clips), `muscles_activation.json`,
  `ui_manifest.json`, `metadata.json`, and the three.js viewer in `demo/`.
- Build scripts in `scripts/` (`build-placeholder-glb.py`,
  `build-activation-json.py`) — pure Python stdlib, no dependencies.
- README with the real-vs-placeholder scope table and the swap-in contract
  for a real anatomy glb.

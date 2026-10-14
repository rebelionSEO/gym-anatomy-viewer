# Testing the demo

Short checklist for verifying the viewer works end to end. Nothing here needs
a build step — just a static server.

## Run it

```bash
git clone https://github.com/rebelionSEO/gym-anatomy-viewer.git
cd gym-anatomy-viewer
python3 -m http.server 8000
# open http://localhost:8000/demo/
```

If a different port is already in use, change the number.

## What to check

### 1. Placeholder loads

- The viewer opens and shows a humanoid-ish arrangement of colored primitive
  boxes against a dark background.
- A short "Loaded." status appears top-left and then disappears.
- A toast reads **Loaded default** in the bottom-right.
- The `?` pill at the top-right of the viewer opens a modal that labels the
  demo as placeholder hardware.

### 2. Animations

- The **Animation** section's dropdown lists `bench press`, `bicep curl`,
  `squat`, `deadlift` (order preferred, any extras from the glb appended).
- **Play** → the figure moves. **Pause** → it stops. **Loop** → stops and
  restarts the clip when it reaches the end.
- The time readout counts up; the scrubber bar advances with it.
- Dragging the scrubber pauses playback and jumps to that time.

### 3. Activation chart updates

- Pick any muscle in the **Activation chart** dropdown. The orange curve
  renders between 0 and 1 across the full clip duration.
- When playback is running, a cyan playhead line sweeps across the chart,
  and the readout at top-left of the chart shows the current value.

### 4. Drag-and-drop custom glb — auto-mapping

- Drag any `.glb` from your file manager onto the viewer window. A dashed
  "Drop a .glb file to load it" overlay appears.
- On drop, the previous model is removed and the new one is centered.
- The **Model** section at the top of the sidebar now reads
  `model: <filename> — N meshes, M clips`.
- The **Mapping** section shows `X / 40 muscles mapped (<filename>)`. For a
  file whose node names already follow `muscles/{canonical_name}` (such as
  the bundled placeholder dropped as a file), X should equal 40.
- A toast reads **Loaded `<filename>`**.

Tip: dropping the bundled file (`human_anatomy_gym_v1.glb`) is a quick way
to prove the drop path works — auto-mapping should hit 40/40.

### 5. Morph target driving (if your glb has them)

The bundled placeholder has **no** morph targets, so you'll see the fallback
every time. To test the morph target path, load a glb whose muscle meshes
expose morph targets named `contract_{muscle_name}_01` (or any of the
other candidates listed in `app.js:morphKeyCandidates`).

- With a morph-equipped glb loaded and a clip playing, muscles with matching
  morph targets should visibly deform as the activation curve climbs.
- Muscles without matching morph targets should still change color + glow
  (the fallback). Check the browser console — the activation driver logs
  nothing per frame, so you can watch Three.js' own `morphTargetInfluences`
  via a selected object in DevTools' scene inspector if you have the
  three-devtools extension.

### 6. Fallback tint + scale pulse

- With the bundled placeholder and a clip playing, actively-firing muscles
  should:
  - Shift color toward yellow
  - Glow (emissive)
  - Scale up and down slightly (uniform ~6%)
- Non-firing muscles stay at their group color (chest red, biceps orange,
  etc.) with no scale change.

### 7. Mapping UI and persistence

- Click **Edit mapping…**. The modal shows one row per muscle key with a
  dropdown of every named mesh in the current glb.
- Red muscle-key label = currently unmapped. Teal = auto-matched. White =
  manually set.
- **Hover a row** — the matching mesh is outlined in yellow in the main
  viewer (THREE.BoxHelper). Changing the dropdown repaints the outline.
  Mouse-off clears it; closing the modal clears it.
- Change a mapping and click **Save & apply**. The viewer updates
  immediately and the modal closes. A toast confirms the save count.
- Reload the page. The viewer boots on the default glb; your mapping for
  "default" is restored from localStorage.
- **Clear mapping for this file** inside the modal wipes just the current
  file's saved mapping and re-runs auto-match. **Reset** in the sidebar
  wipes every saved mapping across every file.

### 7a. Mapping persistence (end-to-end)

Flow to confirm a round-trip through `localStorage`:

1. Load **sample real model** (button in the sidebar). Mapping status reads
   `40 / 40 muscles mapped (sample_real_anatomy.glb)`.
2. Open **Edit mapping…**. Change any one row's mesh (e.g. map
   `pectoralis_major_left` to `mesh_biceps_brachii_left_long_head` — a
   deliberately wrong match so you can see it). Click **Save & apply**.
3. Toast confirms the save; the viewer shows the "wrong" mesh glowing on
   the chest during a `bench_press` activation peak.
4. Reload the page (`Cmd-R` / `Ctrl-R`). Click **Load sample real model**
   again. Open the mapping modal: the wrong row is still assigned
   (persisted). Mapping status still reads `40 / 40`.
5. Open DevTools → Application → Local Storage → your origin → the key
   `gym-anatomy-viewer:mappings` should contain a `sample_real_anatomy.glb`
   object with the override.
6. Click **Clear mapping for this file** inside the modal. Confirm. The
   row flips back to the auto-matched mesh and the override is removed
   from localStorage.

### 7b. Morph target driving (end-to-end)

The bundled placeholder has NO morph targets so you'll always see the
fallback tint + scale pulse. The sample real model has one morph target
per muscle (`contract_{muscle_name}_01`) that inflates the mesh ~15% at
full influence. Flow:

1. Click **Load sample real model**. Pick `bicep_curl` from the Animation
   dropdown. Press Space to play.
2. Watch both biceps meshes. During each rep's concentric phase (middle of
   each 2-second rep) you should see the muscle *scale up uniformly* via
   morph target influence. This is **not** the fallback scale pulse — it's
   `morphTargetInfluences[0]` being driven directly from the activation
   array. Confirm by opening DevTools and inspecting a biceps mesh in the
   console:
   ```js
   // In DevTools console, with the demo open and sample loaded:
   // Find any biceps mesh via its name; influences[0] oscillates 0..1.
   ```
3. Switch to `squat`. The quad and glute meshes now inflate on each
   concentric; biceps stay flat (activation ≈ 0 in `muscles_activation.json`).
4. For comparison: click **Default** to swap back to the placeholder, play
   the same clip. The muscles still react, but via the fallback — color
   lerps toward yellow and the scale pulse is uniform ~6% (vs. 15% morph).

If no muscles move at all when playing on the sample model, check the
browser console for an error about `morphTargetDictionary` or
`extras.targetNames`; your glb may have morph targets with unexpected
names. The viewer tries six name variants
(see `demo/app.js: morphKeyCandidates`).

### 7c. Keyboard shortcuts

With the viewer focused and no modal open:
- Press **Space** — the current clip toggles between play and pause (same
  as clicking Play / Pause).
- Press **S** — the Show skin checkbox flips and the skin shell appears or
  disappears.
- Open the help pill (`?`) or the mapping modal. Try pressing Space; it
  should NOT play/pause. Close the modal and try again; it should work.
- Click into the file-picker label and tab to the muscle-isolate dropdown.
  Try pressing Space while the dropdown is focused; it should open the
  dropdown (default browser behavior), NOT play/pause.

### Screenshot reference

A reference screenshot of the sample-model-loaded state lives at
[`docs/screenshots/sample_loaded.png`](docs/screenshots/sample_loaded.png).
It won't exist in a fresh clone — see
[`docs/screenshots/README.md`](docs/screenshots/README.md) for what to
capture and how. If you run the sample flow and your viewer looks
materially different from the reference once it's there, flag it.

### 8. Other UI controls

- **Muscle groups** checkboxes toggle visibility per group.
- **Isolate** dropdown hides every muscle except the selected one (and
  hides the skin for clarity). Setting it back to "none" restores the
  previous group-toggle state.
- **Display → Show skin** / **Transparent skin** / **Show skeleton** behave
  as labeled.
- **Camera** preset buttons jump the camera to canonical angles.

## Where to look if something's off

| Symptom | File + section to check |
|---|---|
| Default glb won't load | `demo/app.js` → `loadGlbFromUrl` / `DEFAULT_GLB_URL` |
| Dropped glb can't parse | `demo/app.js` → `loadGlbFromArrayBuffer` (`loader.parse`) |
| Auto-mapping missed obvious matches | `demo/app.js` → `normalizeName`, `autoMatchMapping` |
| Mappings don't persist | `demo/app.js` → `STORAGE_KEY`, `saveMappingFor` |
| Morph targets not firing | `demo/app.js` → `morphKeyCandidates`, `updateActivation` |
| Tint fallback stuck or wrong | `demo/app.js` → `applyMappingToScene`, `updateActivation` |

All logic worth inspecting is in `demo/app.js` and marked with `★`
section headers for the two highest-leverage parts (mapping and
activation).

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
- Change a mapping and click **Save & apply**. The viewer updates
  immediately and the modal closes. A toast confirms the save count.
- Reload the page. The viewer boots on the default glb; your mapping for
  "default" is restored from localStorage.
- Click **Reset** in the sidebar to wipe every saved mapping. Confirm.

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

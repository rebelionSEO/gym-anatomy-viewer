# Screenshot references

A manual tester drops reference images here so testers can visually compare
the viewer against a known-good baseline.

## sample_loaded.png

The reference view after clicking **Load sample real model** and letting
`bicep_curl` play for one rep.

### How to capture

1. `python3 -m http.server 8000` from the repo root
2. Open <http://localhost:8000/demo/> in Chrome / Firefox / Safari
3. Click **Load sample real model** in the Model panel
4. Pick `bicep_curl` from the Animation dropdown
5. Press Space to play. Wait until the first rep hits its peak (~1s in)
   so both biceps meshes are visibly inflated via morph targets.
6. Press Space to pause at the peak
7. Click the default camera preset so framing is predictable
8. Capture the whole browser viewport (or just the `#stage` area). PNG,
   up to ~1200 × 900 is plenty.
9. Save as `sample_loaded.png` in this folder.

### Why there's no committed image yet

Reference screenshots are captured by a human from the running viewer —
there's no reliable way to generate one in this repo's build (no
headless-browser dependency). Adding the asset is deliberately left to a
manual tester so the baseline reflects what someone sees on real hardware.

### What a correct screenshot should show

- Humanoid-ish figure built from primitive colored boxes against a dark
  background
- Both bicep boxes (orange, labeled `biceps` in the manifest) visibly
  larger than at rest — this is the morph target firing
- Other muscles roughly at rest size
- Sidebar reads `model: sample_real_anatomy.glb — 41 meshes, 4 clips`
- Mapping status reads `40 / 40 muscles mapped (sample_real_anatomy.glb)`
- Activation chart at the bottom shows the curve for whichever muscle is
  selected, with a cyan playhead line at the pause point

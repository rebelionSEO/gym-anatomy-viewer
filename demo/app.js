// gym-anatomy-viewer — demo viewer
//
// Loads the bundled placeholder glb (or a user-dropped glb), maps meshes to
// muscle keys defined in ui_manifest.json, and drives activation
// visualization from muscles_activation.json. If mapped meshes expose morph
// targets named contract_{muscle_name}_01 the morph influences are driven
// directly; otherwise the viewer falls back to color tint + a small scale
// pulse so the demo still works for primitive geometry.
//
// Non-technical maintainers: look for the sections marked ★. The two most
// interesting pieces are MAPPING (how mesh names in the glb become muscle
// keys) and ACTIVATION (how activation values become either morph or tint).

import * as THREE          from 'three';
import { OrbitControls }    from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader }       from 'three/addons/loaders/GLTFLoader.js';

// ---------------------------------------------------------------------------
// Config + DOM lookups
// ---------------------------------------------------------------------------

const DEFAULT_GLB_URL = '../human_anatomy_gym_v1.glb';
const SAMPLE_GLB_URL  = '../sample_real_anatomy.glb';
const ACTIVATION_URL  = '../muscles_activation.json';
const MANIFEST_URL    = '../ui_manifest.json';
const METADATA_URL    = '../metadata.json';

const STORAGE_KEY = 'gym-anatomy-viewer:mappings';

const $ = id => document.getElementById(id);

const stage           = $('stage');
const canvas          = $('viewer');
const statusEl        = $('status');
const dropOverlay     = $('dropOverlay');
const toastContainer  = $('toastContainer');

const clipSelect      = $('clipSelect');
const playBtn         = $('playBtn');
const pauseBtn        = $('pauseBtn');
const loopToggle      = $('loopToggle');
const scrubber        = $('scrubber');
const timeReadout     = $('timeReadout');
const groupToggles    = $('groupToggles');
const isolateSelect   = $('isolateSelect');
const skinToggle      = $('skinToggle');
const skinTransparent = $('skinTransparent');
const skeletonToggle  = $('skeletonToggle');
const cameraPresets   = $('cameraPresets');
const chartMuscle     = $('chartMuscle');
const chartCanvas     = $('chart');

const loadDefaultBtn  = $('loadDefaultBtn');
const loadSampleBtn   = $('loadSampleBtn');
const glbFileInput    = $('glbFile');
const modelInfo       = $('modelInfo');

const openMappingBtn      = $('openMappingBtn');
const resetMappingBtn     = $('resetMappingBtn');
const mappingStatus       = $('mappingStatus');
const mappingModal        = $('mappingModal');
const mappingList         = $('mappingList');
const mappingAutoBtn      = $('mappingAutoBtn');
const mappingClearBtn     = $('mappingClearBtn');
const mappingClearFileBtn = $('mappingClearFileBtn');
const mappingSaveBtn      = $('mappingSaveBtn');

const helpBtn   = $('helpBtn');
const helpModal = $('helpModal');

// ---------------------------------------------------------------------------
// Scene setup
// ---------------------------------------------------------------------------

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14171c);

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
camera.position.set(0, 1.1, 3.2);

const orbit = new OrbitControls(camera, canvas);
orbit.target.set(0, 1.1, 0);
orbit.enableDamping = true;

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const keyLight = new THREE.DirectionalLight(0xffffff, 0.9);
keyLight.position.set(2, 3, 2);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
fillLight.position.set(-2, 1.5, -1);
scene.add(fillLight);

const ground = new THREE.Mesh(
  new THREE.CircleGeometry(2.2, 48),
  new THREE.MeshBasicMaterial({ color: 0x0b0d10 })
);
ground.rotation.x = -Math.PI / 2;
scene.add(ground);

function resize() {
  const w = stage.clientWidth;
  const h = stage.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

// ---------------------------------------------------------------------------
// Lightweight toasts
// ---------------------------------------------------------------------------

function toast(message, kind = 'info', ttl = 3500) {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = message;
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 350);
  }, ttl);
  console.log(`[${kind}] ${message}`);
}

// ---------------------------------------------------------------------------
// Load manifest + activation + metadata (shared across every model swap)
// ---------------------------------------------------------------------------

const [manifest, activation, metadata] = await Promise.all([
  fetch(MANIFEST_URL).then(r => r.json()),
  fetch(ACTIVATION_URL).then(r => r.json()),
  fetch(METADATA_URL).then(r => r.json()),
]).catch(err => {
  statusEl.textContent = 'Failed to load JSON: ' + err;
  toast('Failed to load manifest/activation JSON', 'error', 7000);
  throw err;
});

// Flat list of all canonical muscle keys from the manifest (in group order)
const MUSCLE_KEYS = Object.values(manifest.groups).flatMap(g => g.muscles);

// ---------------------------------------------------------------------------
// ★ MAPPING: muscle key ↔ mesh name
// ---------------------------------------------------------------------------
//
// A "muscle key" is a canonical identifier from ui_manifest.json
// (e.g. "muscles/pectoralis_major_left"). A "mesh name" is whatever string
// the glTF author used for a mesh/node (e.g. "Pectoralis_Major.L").
//
// Auto-matching normalizes both sides (lowercase, strip "muscles/" prefix,
// collapse separators to underscore) and looks for exact matches. For
// anything the auto-match misses, the user picks a mesh from a dropdown in
// the mapping UI. Mappings are persisted in localStorage keyed by an
// "originId" (the glb filename, or "default" for the bundled model).

function normalizeName(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/^muscles\//, '')
    .replace(/[.\-\s]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function loadAllMappings() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch (e) {
    console.warn('Could not read mapping localStorage:', e);
    return {};
  }
}
function saveAllMappings(all) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
  } catch (e) {
    console.warn('Could not persist mapping localStorage:', e);
  }
}
function loadMappingFor(originId) {
  return loadAllMappings()[originId] || {};
}
function saveMappingFor(originId, mapping) {
  const all = loadAllMappings();
  all[originId] = mapping;
  saveAllMappings(all);
}
function clearAllMappings() {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
}

function autoMatchMapping(muscleKeys, availableMeshNames) {
  // Normalized-name → first matching mesh name
  const byNorm = new Map();
  for (const name of availableMeshNames) byNorm.set(normalizeName(name), name);

  const mapping = {};
  for (const key of muscleKeys) {
    const norm = normalizeName(key);
    if (byNorm.has(norm)) mapping[key] = byNorm.get(norm);
  }
  return mapping;
}

// ---------------------------------------------------------------------------
// Model state (reset on every glb swap)
// ---------------------------------------------------------------------------

const state = {
  originId: 'default',
  modelRoot: null,     // THREE.Object3D added to scene
  mixer: null,         // THREE.AnimationMixer
  clips: [],           // [{ name, clip }]
  activeClip: null,
  activeAction: null,
  muscleNodes: new Map(),   // muscleKey -> THREE.Mesh (resolved from mapping)
  baseColors: new WeakMap(),
  baseScales: new WeakMap(),
  skinNodes: [],
  skeletonNodes: [],
  availableMeshNames: [],   // every mesh name in the current glb (for mapping UI)
  meshesByName: new Map(),  // name -> THREE.Mesh (any named mesh — powers hover preview)
  mapping: {},              // muscleKey -> mesh name (persisted)
  hoverOutline: null,       // THREE.BoxHelper used by the mapping-UI hover preview
};

function disposeObject(obj) {
  obj.traverse(o => {
    if (o.geometry) o.geometry.dispose?.();
    if (o.material) {
      if (Array.isArray(o.material)) o.material.forEach(m => m.dispose?.());
      else o.material.dispose?.();
    }
  });
}

function tearDownCurrentModel() {
  clearHoverOutline();
  if (state.activeAction) { state.activeAction.stop(); state.activeAction = null; }
  state.activeClip = null;
  state.mixer = null;
  state.clips = [];
  state.muscleNodes.clear();
  state.meshesByName.clear();
  state.baseColors  = new WeakMap();
  state.baseScales  = new WeakMap();
  state.skinNodes   = [];
  state.skeletonNodes = [];
  state.availableMeshNames = [];
  if (state.modelRoot) {
    scene.remove(state.modelRoot);
    disposeObject(state.modelRoot);
    state.modelRoot = null;
  }
}

// ---------------------------------------------------------------------------
// Mount a parsed gltf: resolve mapping, bind mixer, wire controls
// ---------------------------------------------------------------------------

function mountGltf(gltf, originId) {
  tearDownCurrentModel();

  state.originId  = originId;
  state.modelRoot = gltf.scene;
  scene.add(state.modelRoot);

  // Collect every named mesh so the mapping UI knows what's available, and
  // bucket skin/skeleton helpers by their canonical "skin/..." or
  // "skeleton/..." name prefixes (optional — real anatomy glbs may skip them).
  state.modelRoot.traverse(obj => {
    if (!obj.name || !obj.isMesh) return;
    state.availableMeshNames.push(obj.name);
    state.meshesByName.set(obj.name, obj);
    if (obj.name.startsWith('skin/')) {
      obj.material = obj.material.clone();
      state.skinNodes.push(obj);
    } else if (obj.name.startsWith('skeleton/')) {
      obj.material = obj.material.clone();
      obj.visible = false;
      state.skeletonNodes.push(obj);
    }
  });

  // Resolve mapping: saved mapping (if any) wins, then auto-match fills in.
  const saved = loadMappingFor(originId);
  const auto  = autoMatchMapping(MUSCLE_KEYS, state.availableMeshNames);
  state.mapping = { ...auto, ...saved };

  applyMappingToScene();

  // Animations
  state.mixer = new THREE.AnimationMixer(state.modelRoot);
  state.clips = buildClipList(gltf.animations, manifest.animations);

  rebuildClipSelect();
  if (state.clips.length) {
    selectClip(state.clips[0].name);
  } else {
    toast('No animation clips found in glb — playback disabled', 'warn');
  }

  // Refresh dependent UI
  skinToggleApply();
  skeletonToggleApply();
  updateModelInfo();
  refreshMappingStatus();
}

// Resolve current state.mapping to actual mesh references. Clone materials so
// per-muscle tinting doesn't bleed across meshes that share a material.
function applyMappingToScene() {
  state.muscleNodes.clear();
  state.baseColors  = new WeakMap();
  state.baseScales  = new WeakMap();

  const meshByName = new Map();
  state.modelRoot.traverse(obj => {
    if (obj.isMesh && obj.name) meshByName.set(obj.name, obj);
  });

  for (const key of MUSCLE_KEYS) {
    const meshName = state.mapping[key];
    if (!meshName) continue;
    const mesh = meshByName.get(meshName);
    if (!mesh) continue;
    if (!mesh._clonedForViewer) {
      mesh.material = mesh.material.clone();
      mesh._clonedForViewer = true;
    }
    state.muscleNodes.set(key, mesh);
    state.baseColors.set(mesh, mesh.material.color?.clone() ?? new THREE.Color(0xffffff));
    state.baseScales.set(mesh, mesh.scale.clone());
  }

  // Paint muscles with their group color (visual grouping — overwritten each
  // frame by activation tint during playback).
  for (const group of Object.values(manifest.groups)) {
    const c = new THREE.Color(group.color);
    for (const key of group.muscles) {
      const node = state.muscleNodes.get(key);
      if (node && node.material.color) {
        node.material.color.copy(c);
        state.baseColors.set(node, c.clone());
      }
    }
  }
}

function buildClipList(gltfAnimations, preferredNames) {
  const byName = new Map((gltfAnimations || []).map(c => [c.name, c]));
  const ordered = [];
  for (const name of preferredNames) {
    if (byName.has(name)) {
      ordered.push({ name, clip: byName.get(name) });
      byName.delete(name);
    }
  }
  for (const [name, clip] of byName) ordered.push({ name, clip });
  return ordered;
}

// ---------------------------------------------------------------------------
// GLB loading (from URL or from File / ArrayBuffer)
// ---------------------------------------------------------------------------

const loader = new GLTFLoader();

async function loadGlbFromUrl(url, originId = 'default') {
  statusEl.style.display = '';
  statusEl.textContent = 'Loading…';
  try {
    const gltf = await loader.loadAsync(url);
    mountGltf(gltf, originId);
    toast(`Loaded ${originId}`, 'info');
    statusEl.textContent = 'Loaded.';
    setTimeout(() => statusEl.style.display = 'none', 1200);
  } catch (err) {
    toast(`Failed to load glb: ${err.message || err}`, 'error', 6000);
    statusEl.textContent = 'Load failed.';
    throw err;
  }
}

function loadGlbFromArrayBuffer(buffer, filename) {
  statusEl.style.display = '';
  statusEl.textContent = `Loading ${filename}…`;
  loader.parse(buffer, '', gltf => {
    try {
      mountGltf(gltf, filename);
      toast(`Loaded ${filename}`, 'info');
      statusEl.textContent = 'Loaded.';
      setTimeout(() => statusEl.style.display = 'none', 1200);
    } catch (err) {
      toast(`Failed to mount glb: ${err.message || err}`, 'error', 6000);
      statusEl.textContent = 'Mount failed.';
      console.error(err);
    }
  }, err => {
    toast(`Could not parse glb: ${err.message || err}`, 'error', 6000);
    statusEl.textContent = 'Parse failed.';
    console.error(err);
  });
}

function handleFile(file) {
  if (!file) return;
  if (!/\.(glb|gltf)$/i.test(file.name)) {
    toast('Expected a .glb or .gltf file.', 'error');
    return;
  }
  file.arrayBuffer().then(buf => loadGlbFromArrayBuffer(buf, file.name));
}

// ---------------------------------------------------------------------------
// File input + drag-and-drop
// ---------------------------------------------------------------------------

loadDefaultBtn.addEventListener('click', () => loadGlbFromUrl(DEFAULT_GLB_URL, 'default'));
loadSampleBtn.addEventListener('click', () => loadGlbFromUrl(SAMPLE_GLB_URL, 'sample_real_anatomy.glb'));

glbFileInput.addEventListener('change', e => {
  const file = e.target.files?.[0];
  handleFile(file);
  e.target.value = ''; // allow re-selecting the same file
});

// Drop-zone wiring: show the overlay as soon as a drag enters the window,
// hide on leave/drop. Simpler than per-element bookkeeping, works across the
// stage canvas and the panel.
let dragDepth = 0;
window.addEventListener('dragenter', e => {
  if (!hasFiles(e)) return;
  dragDepth++;
  dropOverlay.classList.add('active');
});
window.addEventListener('dragover', e => { if (hasFiles(e)) e.preventDefault(); });
window.addEventListener('dragleave', () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) dropOverlay.classList.remove('active');
});
window.addEventListener('drop', e => {
  if (!hasFiles(e)) return;
  e.preventDefault();
  dragDepth = 0;
  dropOverlay.classList.remove('active');
  handleFile(e.dataTransfer.files?.[0]);
});
function hasFiles(e) {
  return e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files');
}

// ---------------------------------------------------------------------------
// Animation controls
// ---------------------------------------------------------------------------

function rebuildClipSelect() {
  clipSelect.innerHTML = '';
  for (const { name } of state.clips) {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name.replace(/_/g, ' ');
    clipSelect.appendChild(opt);
  }
}

function selectClip(name) {
  const entry = state.clips.find(c => c.name === name);
  if (!entry) return;
  if (state.activeAction) state.activeAction.stop();
  state.activeClip  = entry.clip;
  state.activeAction = state.mixer.clipAction(entry.clip);
  state.activeAction.setLoop(loopToggle.checked ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
  state.activeAction.clampWhenFinished = true;
  state.activeAction.play();
  state.activeAction.paused = true;
  scrubber.value = 0;
  clipSelect.value = name;
  rebuildChartMuscleDropdown(name);
  drawChart();
}

clipSelect.addEventListener('change', () => selectClip(clipSelect.value));

playBtn.addEventListener('click', () => {
  if (!state.activeAction) return;
  if (state.activeAction.time >= state.activeClip.duration - 1e-3) state.activeAction.time = 0;
  state.activeAction.paused = false;
});
pauseBtn.addEventListener('click', () => {
  if (state.activeAction) state.activeAction.paused = true;
});
loopToggle.addEventListener('change', () => {
  if (!state.activeAction) return;
  state.activeAction.setLoop(loopToggle.checked ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
});
scrubber.addEventListener('input', () => {
  if (!state.activeAction) return;
  state.activeAction.paused = true;
  state.activeAction.time = parseFloat(scrubber.value) * state.activeClip.duration;
});

// ---------------------------------------------------------------------------
// Group toggles + isolate
// ---------------------------------------------------------------------------

for (const [gid, group] of Object.entries(manifest.groups)) {
  const row = document.createElement('label');
  row.className = 'group-row';
  row.innerHTML =
    `<input type="checkbox" checked data-group="${gid}" />` +
    `<span class="swatch" style="background:${group.color}"></span>` +
    `<span>${group.label}</span>`;
  groupToggles.appendChild(row);
}
groupToggles.addEventListener('change', e => {
  const gid = e.target.dataset.group;
  if (!gid) return;
  const show = e.target.checked;
  for (const key of manifest.groups[gid].muscles) {
    const n = state.muscleNodes.get(key);
    if (n) n.visible = show;
  }
});

for (const [, group] of Object.entries(manifest.groups)) {
  const optgroup = document.createElement('optgroup');
  optgroup.label = group.label;
  for (const key of group.muscles) {
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = key.replace('muscles/', '');
    optgroup.appendChild(opt);
  }
  isolateSelect.appendChild(optgroup);
}
isolateSelect.addEventListener('change', () => {
  const target = isolateSelect.value;
  if (!target) {
    for (const [gid, group] of Object.entries(manifest.groups)) {
      const cb = groupToggles.querySelector(`input[data-group="${gid}"]`);
      for (const key of group.muscles) {
        const n = state.muscleNodes.get(key);
        if (n) n.visible = cb.checked;
      }
    }
    skinToggleApply();
  } else {
    state.muscleNodes.forEach((n, k) => { n.visible = (k === target); });
    for (const sn of state.skinNodes) sn.visible = false;
  }
});

// ---------------------------------------------------------------------------
// Skin, skeleton, camera presets
// ---------------------------------------------------------------------------

function skinToggleApply() {
  const show = skinToggle.checked;
  const transparent = skinTransparent.checked;
  for (const sn of state.skinNodes) {
    sn.visible = show;
    sn.material.transparent = true;
    sn.material.opacity = transparent ? 0.18 : 0.65;
    sn.material.depthWrite = !transparent;
  }
}
function skeletonToggleApply() {
  for (const n of state.skeletonNodes) n.visible = skeletonToggle.checked;
}
skinToggle.addEventListener('change', skinToggleApply);
skinTransparent.addEventListener('change', skinToggleApply);
skeletonToggle.addEventListener('change', skeletonToggleApply);

for (const [name, preset] of Object.entries(manifest.cameraPresets)) {
  const b = document.createElement('button');
  b.textContent = name;
  b.addEventListener('click', () => {
    camera.position.fromArray(preset.position);
    orbit.target.fromArray(preset.target);
    orbit.update();
  });
  cameraPresets.appendChild(b);
}

// ---------------------------------------------------------------------------
// Activation chart
// ---------------------------------------------------------------------------

function rebuildChartMuscleDropdown(clipName) {
  chartMuscle.innerHTML = '';
  const data = activation[clipName] || {};
  const names = Object.keys(data).sort();
  for (const name of names) {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    chartMuscle.appendChild(opt);
  }
}
chartMuscle.addEventListener('change', drawChart);

function drawChart() {
  const ctx = chartCanvas.getContext('2d');
  const w = chartCanvas.width;
  const h = chartCanvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#0f1114';
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = '#2a2f38';
  ctx.lineWidth = 1;
  for (let y = 0; y <= 4; y++) {
    const yy = (y / 4) * (h - 20) + 10;
    ctx.beginPath();
    ctx.moveTo(0, yy); ctx.lineTo(w, yy); ctx.stroke();
  }

  if (!state.activeClip) return;
  const clipName = state.activeClip.name;
  const muscle = chartMuscle.value;
  const series = activation[clipName]?.[muscle];
  if (!series) return;

  const step = metadata.timeStepSeconds;
  const duration = state.activeClip.duration;

  ctx.strokeStyle = '#e07a4f';
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  for (let i = 0; i < series.length; i++) {
    const t = i * step;
    const x = (t / duration) * (w - 2) + 1;
    const y = h - 10 - series[i] * (h - 20);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();

  if (state.activeAction) {
    const t = state.activeAction.time;
    const x = (t / duration) * (w - 2) + 1;
    ctx.strokeStyle = '#4ab8a0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();

    const i = Math.min(series.length - 1, Math.round(t / step));
    ctx.fillStyle = '#e6e8ec';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.fillText(`${muscle}  v=${series[i].toFixed(2)}`, 6, 14);
  }
}

// ---------------------------------------------------------------------------
// ★ ACTIVATION: drive morph target influences OR fallback tint + scale pulse
// ---------------------------------------------------------------------------
//
// For each mapped muscle:
//   • If the mesh has morphTargetDictionary + morphTargetInfluences, we try
//     a few canonical morph target names and set the matching influence to
//     the current activation value (0..1).
//   • Otherwise we fall back to:
//       - color lerp (base group color → yellow-hot)
//       - emissive glow proportional to activation
//       - small uniform scale pulse (base × 1.0..1.06)
//     The fallback is clearly labeled in the code and is purely cosmetic.

const HOT_COLOR  = new THREE.Color(0xffe066);

function morphKeyCandidates(muscleKey) {
  const base = normalizeName(muscleKey);
  return [
    `contract_${base}_01`,
    `contract_${base}`,
    `${base}_contract_01`,
    `${base}_contract`,
    'contract_01',
    'contract',
  ];
}

function sampleIndexFor(time) {
  // activation arrays are sampled every metadata.timeStepSeconds
  return Math.max(0, Math.round(time / metadata.timeStepSeconds));
}

function updateActivation() {
  if (!state.activeClip || !state.activeAction) return;
  const clipName = state.activeClip.name;
  const series = activation[clipName];
  if (!series) return;

  // Any muscle's series length is a safe upper bound
  const firstSeries = Object.values(series)[0] || [];
  const i = Math.min(firstSeries.length - 1, sampleIndexFor(state.activeAction.time));

  state.muscleNodes.forEach((node, key) => {
    const curve = series[normalizeName(key)] || series[key.replace('muscles/', '')] || series[key];
    const v = curve ? curve[i] : 0;

    // --- 1) morph target path ---------------------------------------------
    if (node.morphTargetDictionary && node.morphTargetInfluences) {
      let drove = false;
      for (const candidate of morphKeyCandidates(key)) {
        const idx = node.morphTargetDictionary[candidate];
        if (idx != null) {
          node.morphTargetInfluences[idx] = Math.max(0, Math.min(1, v));
          drove = true;
          break;
        }
      }
      if (drove) return;
    }

    // --- 2) fallback: color tint + emissive + tiny scale pulse ------------
    const base = state.baseColors.get(node);
    if (base && node.material.color) {
      node.material.color.copy(base).lerp(HOT_COLOR, Math.min(1, v));
    }
    if ('emissive' in node.material) {
      if (!node.material.emissive) node.material.emissive = new THREE.Color();
      node.material.emissive.setRGB(v * 0.5, v * 0.35, 0);
    }
    const baseScale = state.baseScales.get(node);
    if (baseScale) {
      const s = 1 + v * 0.06;
      node.scale.set(baseScale.x * s, baseScale.y * s, baseScale.z * s);
    }
  });
}

// ---------------------------------------------------------------------------
// Mapping UI
// ---------------------------------------------------------------------------

function openModal(el)  { el.hidden = false; }
function closeModal(el) {
  el.hidden = true;
  if (el === mappingModal) clearHoverOutline();
}

document.querySelectorAll('[data-close-modal]').forEach(btn => {
  btn.addEventListener('click', () => closeModal($(btn.dataset.closeModal)));
});
[helpModal, mappingModal].forEach(el => {
  el.addEventListener('click', e => { if (e.target === el) closeModal(el); });
});
helpBtn.addEventListener('click', () => openModal(helpModal));

openMappingBtn.addEventListener('click', () => {
  renderMappingList();
  openModal(mappingModal);
});

// Hover preview: outline the mesh referenced by the row's current <select>
// value in the main viewer. Uses THREE.BoxHelper so no materials are touched
// and the activation driver can keep running underneath.
function setHoverPreview(meshName) {
  clearHoverOutline();
  if (!meshName) return;
  const target = state.meshesByName.get(meshName);
  if (!target) return;
  state.hoverOutline = new THREE.BoxHelper(target, 0xffe066);
  state.hoverOutline.renderOrder = 999;
  scene.add(state.hoverOutline);
}
function clearHoverOutline() {
  if (state.hoverOutline) {
    scene.remove(state.hoverOutline);
    state.hoverOutline.geometry?.dispose();
    state.hoverOutline = null;
  }
}
// Clear hover outline if the modal closes without a mouseleave event firing.
mappingModal.addEventListener('click', e => { if (e.target === mappingModal) clearHoverOutline(); });

resetMappingBtn.addEventListener('click', () => {
  if (!confirm('Clear saved mappings for every glb? This can\'t be undone.')) return;
  clearAllMappings();
  // Re-mount current gltf by reloading from scratch — easiest way to get a
  // clean auto-match without reaching for the loader again.
  if (state.originId === 'default') loadGlbFromUrl(DEFAULT_GLB_URL, 'default');
  else toast('Cleared. Drop the glb again to re-run auto-match.', 'info');
  refreshMappingStatus();
});

function renderMappingList() {
  mappingList.innerHTML = '';
  const auto = autoMatchMapping(MUSCLE_KEYS, state.availableMeshNames);
  const current = { ...state.mapping };

  // Build the dropdown options once — same list for every row.
  const meshOptionsFragment = () => {
    const frag = document.createDocumentFragment();
    const none = document.createElement('option');
    none.value = ''; none.textContent = '— unmapped —';
    frag.appendChild(none);
    for (const name of state.availableMeshNames) {
      const opt = document.createElement('option');
      opt.value = name; opt.textContent = name;
      frag.appendChild(opt);
    }
    return frag;
  };

  for (const key of MUSCLE_KEYS) {
    const row = document.createElement('div');
    row.className = 'mapping-row';

    const label = document.createElement('div');
    label.className = 'muscle-key';
    label.textContent = key.replace('muscles/', '');
    if (!current[key])                     label.classList.add('unmapped');
    else if (current[key] === auto[key])   label.classList.add('auto');

    const sel = document.createElement('select');
    sel.appendChild(meshOptionsFragment());
    sel.value = current[key] || '';
    sel.dataset.key = key;

    row.appendChild(label);
    row.appendChild(sel);

    // Hover preview: outline whichever mesh this row currently points at.
    row.addEventListener('mouseenter', () => setHoverPreview(sel.value));
    row.addEventListener('mouseleave', clearHoverOutline);
    sel.addEventListener('change', () => setHoverPreview(sel.value));

    mappingList.appendChild(row);
  }
}

mappingAutoBtn.addEventListener('click', () => {
  const auto = autoMatchMapping(MUSCLE_KEYS, state.availableMeshNames);
  state.mapping = { ...auto };
  renderMappingList();
  toast(`Auto-matched ${Object.keys(auto).length} / ${MUSCLE_KEYS.length}`, 'info');
});

mappingClearBtn.addEventListener('click', () => {
  state.mapping = {};
  renderMappingList();
});

mappingClearFileBtn.addEventListener('click', () => {
  if (!confirm(`Wipe the saved mapping for "${state.originId}"? The current view will also reset.`)) return;
  const all = loadAllMappings();
  delete all[state.originId];
  saveAllMappings(all);
  state.mapping = autoMatchMapping(MUSCLE_KEYS, state.availableMeshNames);
  applyMappingToScene();
  renderMappingList();
  refreshMappingStatus();
  toast(`Cleared saved mapping for ${state.originId}`, 'info');
});

mappingSaveBtn.addEventListener('click', () => {
  const next = {};
  mappingList.querySelectorAll('select').forEach(sel => {
    if (sel.value) next[sel.dataset.key] = sel.value;
  });
  state.mapping = next;
  saveMappingFor(state.originId, next);
  applyMappingToScene();
  refreshMappingStatus();
  closeModal(mappingModal);
  toast(`Mapping saved for ${state.originId} (${Object.keys(next).length}/${MUSCLE_KEYS.length})`, 'info');
});

function refreshMappingStatus() {
  const mapped = Object.keys(state.mapping).length;
  const total  = MUSCLE_KEYS.length;
  mappingStatus.textContent = `${mapped} / ${total} muscles mapped (${state.originId})`;
}

function updateModelInfo() {
  modelInfo.textContent = `model: ${state.originId} — ${state.availableMeshNames.length} meshes, ${state.clips.length} clips`;
}

// ---------------------------------------------------------------------------
// Keyboard shortcuts
// ---------------------------------------------------------------------------
//
// Only fire when the user is NOT in a form element (so typing in the file
// name of a dropped file, or scrubbing with the keyboard, still works) and
// no modal is open (so Space doesn't play/pause while reading the help).

function anyModalOpen() {
  return !helpModal.hidden || !mappingModal.hidden;
}
function isTypingTarget(el) {
  return el && el.matches && el.matches('input, select, textarea, [contenteditable="true"]');
}
function togglePlayback() {
  if (!state.activeAction) return;
  if (state.activeAction.paused) {
    if (state.activeAction.time >= state.activeClip.duration - 1e-3) state.activeAction.time = 0;
    state.activeAction.paused = false;
  } else {
    state.activeAction.paused = true;
  }
}

window.addEventListener('keydown', e => {
  if (isTypingTarget(e.target)) return;
  if (anyModalOpen()) return;
  if (e.key === ' ' || e.code === 'Space') {
    e.preventDefault();
    togglePlayback();
  } else if (e.key === 's' || e.key === 'S') {
    e.preventDefault();
    skinToggle.checked = !skinToggle.checked;
    skinToggleApply();
  }
});

// ---------------------------------------------------------------------------
// Render loop
// ---------------------------------------------------------------------------

const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();
  if (state.mixer) state.mixer.update(dt);

  if (state.activeAction && !state.activeAction.paused) {
    scrubber.value = (state.activeAction.time / state.activeClip.duration).toFixed(4);
  }
  if (state.activeClip && state.activeAction) {
    timeReadout.textContent = `${state.activeAction.time.toFixed(2)} / ${state.activeClip.duration.toFixed(2)}s`;
  }

  updateActivation();
  drawChart();
  orbit.update();
  renderer.render(scene, camera);
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

await loadGlbFromUrl(DEFAULT_GLB_URL, 'default');
animate();

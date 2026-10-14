import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader }    from 'three/addons/loaders/GLTFLoader.js';

const GLB_URL        = '../human_anatomy_gym_v1.glb';
const ACTIVATION_URL = '../muscles_activation.json';
const MANIFEST_URL   = '../ui_manifest.json';
const METADATA_URL   = '../metadata.json';

const stage = document.getElementById('stage');
const canvas = document.getElementById('viewer');
const statusEl = document.getElementById('status');

// ---------------------------------------------------------------------------
// three.js scene
// ---------------------------------------------------------------------------
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14171c);

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
camera.position.set(0, 1.1, 3.2);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 1.1, 0);
controls.enableDamping = true;

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const key = new THREE.DirectionalLight(0xffffff, 0.9);
key.position.set(2, 3, 2);
scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 0.3);
fill.position.set(-2, 1.5, -1);
scene.add(fill);

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
// Load manifest + activation + glb
// ---------------------------------------------------------------------------
const [manifest, activation, metadata] = await Promise.all([
  fetch(MANIFEST_URL).then(r => r.json()),
  fetch(ACTIVATION_URL).then(r => r.json()),
  fetch(METADATA_URL).then(r => r.json()),
]).catch(err => {
  statusEl.textContent = 'Failed to load JSON: ' + err;
  throw err;
});

const gltf = await new GLTFLoader().loadAsync(GLB_URL).catch(err => {
  statusEl.textContent = 'Failed to load glb: ' + err;
  throw err;
});
scene.add(gltf.scene);
statusEl.textContent = 'Loaded.';
setTimeout(() => statusEl.style.display = 'none', 1500);

// ---------------------------------------------------------------------------
// Build node lookup. Clone materials so each muscle can be colored independently.
// ---------------------------------------------------------------------------
const muscleNodes = new Map();   // "muscles/pectoralis_major_left" -> node
const skinNodes   = [];
const skeletonNodes = [];
const baseColors  = new Map();   // node -> original THREE.Color

gltf.scene.traverse(obj => {
  if (!obj.name) return;
  if (obj.name.startsWith('muscles/') && obj.isMesh) {
    obj.material = obj.material.clone();
    muscleNodes.set(obj.name, obj);
    baseColors.set(obj, obj.material.color.clone());
  } else if (obj.name.startsWith('skin/') && obj.isMesh) {
    obj.material = obj.material.clone();
    skinNodes.push(obj);
  } else if (obj.name.startsWith('skeleton/') && obj.isMesh) {
    obj.material = obj.material.clone();
    skeletonNodes.push(obj);
    obj.visible = false;  // off by default
  }
});

// Apply group colors from manifest to muscle materials
for (const [, group] of Object.entries(manifest.groups)) {
  const c = new THREE.Color(group.color);
  for (const name of group.muscles) {
    const n = muscleNodes.get(name);
    if (n) {
      n.material.color.copy(c);
      baseColors.set(n, c.clone());
    }
  }
}

// ---------------------------------------------------------------------------
// Animation mixer
// ---------------------------------------------------------------------------
const mixer = new THREE.AnimationMixer(gltf.scene);
const clipsByName = new Map();
gltf.animations.forEach(clip => clipsByName.set(clip.name, clip));

let activeClip = null;
let activeAction = null;

function selectClip(name) {
  if (!clipsByName.has(name)) return;
  if (activeAction) activeAction.stop();
  activeClip = clipsByName.get(name);
  activeAction = mixer.clipAction(activeClip);
  activeAction.setLoop(loopToggle.checked ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
  activeAction.clampWhenFinished = true;
  activeAction.play();
  activeAction.paused = true;
  scrubber.value = 0;
  rebuildChartMuscleDropdown(name);
  drawChart();
}

// ---------------------------------------------------------------------------
// UI wiring
// ---------------------------------------------------------------------------
const clipSelect     = document.getElementById('clipSelect');
const playBtn        = document.getElementById('playBtn');
const pauseBtn       = document.getElementById('pauseBtn');
const loopToggle     = document.getElementById('loopToggle');
const scrubber       = document.getElementById('scrubber');
const timeReadout    = document.getElementById('timeReadout');
const groupToggles   = document.getElementById('groupToggles');
const isolateSelect  = document.getElementById('isolateSelect');
const skinToggle     = document.getElementById('skinToggle');
const skinTransparent= document.getElementById('skinTransparent');
const skeletonToggle = document.getElementById('skeletonToggle');
const labelToggle    = document.getElementById('labelToggle');
const cameraPresets  = document.getElementById('cameraPresets');
const chartMuscle    = document.getElementById('chartMuscle');
const chartCanvas    = document.getElementById('chart');

// clip select
manifest.animations.forEach(name => {
  const opt = document.createElement('option');
  opt.value = name;
  opt.textContent = name.replace('_', ' ');
  clipSelect.appendChild(opt);
});
clipSelect.addEventListener('change', () => selectClip(clipSelect.value));

playBtn.addEventListener('click', () => {
  if (!activeAction) return;
  if (activeAction.time >= activeClip.duration - 1e-3) activeAction.time = 0;
  activeAction.paused = false;
});
pauseBtn.addEventListener('click', () => {
  if (activeAction) activeAction.paused = true;
});
loopToggle.addEventListener('change', () => {
  if (!activeAction) return;
  activeAction.setLoop(loopToggle.checked ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
});
scrubber.addEventListener('input', () => {
  if (!activeAction) return;
  activeAction.paused = true;
  activeAction.time = parseFloat(scrubber.value) * activeClip.duration;
});

// group toggles
for (const [gid, group] of Object.entries(manifest.groups)) {
  const row = document.createElement('label');
  row.className = 'group-row';
  row.innerHTML = `<input type="checkbox" checked data-group="${gid}" /><span class="swatch" style="background:${group.color}"></span><span>${group.label}</span>`;
  groupToggles.appendChild(row);
}
groupToggles.addEventListener('change', e => {
  const gid = e.target.dataset.group;
  if (!gid) return;
  const show = e.target.checked;
  for (const name of manifest.groups[gid].muscles) {
    const n = muscleNodes.get(name);
    if (n) n.visible = show;
  }
});

// isolate dropdown
for (const [gid, group] of Object.entries(manifest.groups)) {
  const optgroup = document.createElement('optgroup');
  optgroup.label = group.label;
  for (const name of group.muscles) {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name.replace('muscles/', '');
    optgroup.appendChild(opt);
  }
  isolateSelect.appendChild(optgroup);
}
isolateSelect.addEventListener('change', () => {
  const target = isolateSelect.value;
  if (!target) {
    // reset to current group-toggle state
    for (const [gid, group] of Object.entries(manifest.groups)) {
      const cb = groupToggles.querySelector(`input[data-group="${gid}"]`);
      for (const name of group.muscles) {
        const n = muscleNodes.get(name);
        if (n) n.visible = cb.checked;
      }
    }
    skinToggleApply();
  } else {
    muscleNodes.forEach((n, k) => { n.visible = (k === target); });
    for (const sn of skinNodes) sn.visible = false;
  }
});

// skin + skeleton + labels
function skinToggleApply() {
  const show = skinToggle.checked;
  const transparent = skinTransparent.checked;
  for (const sn of skinNodes) {
    sn.visible = show;
    sn.material.transparent = true;
    sn.material.opacity = transparent ? 0.18 : 0.65;
    sn.material.depthWrite = !transparent;
  }
}
skinToggle.addEventListener('change', skinToggleApply);
skinTransparent.addEventListener('change', skinToggleApply);
skinToggleApply();

skeletonToggle.addEventListener('change', () => {
  for (const n of skeletonNodes) n.visible = skeletonToggle.checked;
});

// camera presets
for (const [name, preset] of Object.entries(manifest.cameraPresets)) {
  const b = document.createElement('button');
  b.textContent = name;
  b.addEventListener('click', () => {
    camera.position.fromArray(preset.position);
    controls.target.fromArray(preset.target);
    controls.update();
  });
  cameraPresets.appendChild(b);
}

// chart muscle dropdown — rebuilt per selected clip
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

// ---------------------------------------------------------------------------
// Activation chart
// ---------------------------------------------------------------------------
function drawChart() {
  const ctx = chartCanvas.getContext('2d');
  const w = chartCanvas.width;
  const h = chartCanvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#0f1114';
  ctx.fillRect(0, 0, w, h);

  // grid
  ctx.strokeStyle = '#2a2f38';
  ctx.lineWidth = 1;
  for (let y = 0; y <= 4; y++) {
    const yy = (y / 4) * (h - 20) + 10;
    ctx.beginPath();
    ctx.moveTo(0, yy); ctx.lineTo(w, yy); ctx.stroke();
  }

  if (!activeClip) return;
  const clipName = activeClip.name;
  const muscle = chartMuscle.value;
  const series = activation[clipName]?.[muscle];
  if (!series) return;

  const step = metadata.timeStepSeconds;
  const duration = activeClip.duration;

  // curve
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

  // playhead
  if (activeAction) {
    const t = activeAction.time;
    const x = (t / duration) * (w - 2) + 1;
    ctx.strokeStyle = '#4ab8a0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();

    // value at playhead
    const i = Math.min(series.length - 1, Math.round(t / step));
    ctx.fillStyle = '#e6e8ec';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.fillText(`${muscle}  v=${series[i].toFixed(2)}`, 6, 14);
  }
}

// ---------------------------------------------------------------------------
// Per-frame activation tinting
// ---------------------------------------------------------------------------
function updateActivationTint() {
  if (!activeClip || !activeAction) return;
  const clipName = activeClip.name;
  const series = activation[clipName];
  if (!series) return;
  const step = metadata.timeStepSeconds;
  const i = Math.min(
    Math.round(activeAction.time / step),
    series[Object.keys(series)[0]].length - 1
  );
  const hot = new THREE.Color(0xffe066);
  muscleNodes.forEach((node, name) => {
    const curve = series[name];
    const v = curve ? curve[i] : 0;
    const base = baseColors.get(node);
    node.material.color.copy(base).lerp(hot, Math.min(1, v));
    node.material.emissive = node.material.emissive || new THREE.Color();
    node.material.emissive.setRGB(v * 0.5, v * 0.35, 0);
  });
}

// ---------------------------------------------------------------------------
// Render loop
// ---------------------------------------------------------------------------
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();
  mixer.update(dt);

  if (activeAction && !activeAction.paused) {
    scrubber.value = (activeAction.time / activeClip.duration).toFixed(4);
  }
  if (activeClip) {
    timeReadout.textContent = `${activeAction.time.toFixed(2)} / ${activeClip.duration.toFixed(2)}s`;
  }

  updateActivationTint();
  drawChart();
  controls.update();
  renderer.render(scene, camera);
}

// Boot — pick first animation
selectClip(manifest.animations[0]);
animate();

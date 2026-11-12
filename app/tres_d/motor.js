// Motor 3D de prueba (estilo "maqueta con maniquíes"). three.js r169, se renderiza en Chromium sin pantalla.
import * as THREE from 'three';

export { THREE };

// ---------- texturas hechas a mano (sin descargar nada) ----------
function ruido(w, h, base, var_, grano = 1, manchas = 0) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d'); const im = g.createImageData(w, h);
  // value noise de varias escalas
  const capas = [64, 16, 4].map(s => {
    const gw = Math.ceil(w / s) + 2, gh = Math.ceil(h / s) + 2;
    const a = new Float32Array(gw * gh).map(() => Math.random());
    return { s, gw, a };
  });
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let v = 0, peso = [0.55, 0.3, 0.15];
    capas.forEach((L, i) => {
      const fx = x / L.s, fy = y / L.s, ix = Math.floor(fx), iy = Math.floor(fy), tx = fx - ix, ty = fy - iy;
      const q = (X, Y) => L.a[Y * L.gw + X];
      const sx = tx * tx * (3 - 2 * tx), sy = ty * ty * (3 - 2 * ty);
      v += peso[i] * ((q(ix, iy) * (1 - sx) + q(ix + 1, iy) * sx) * (1 - sy) + (q(ix, iy + 1) * (1 - sx) + q(ix + 1, iy + 1) * sx) * sy);
    });
    v += (Math.random() - 0.5) * 0.12 * grano;
    const k = (y * w + x) * 4;
    for (let j = 0; j < 3; j++) im.data[k + j] = Math.max(0, Math.min(255, base[j] + (v - 0.5) * var_));
    im.data[k + 3] = 255;
  }
  g.putImageData(im, 0, 0);
  if (manchas) {           // grietas / manchas oscuras
    g.strokeStyle = 'rgba(0,0,0,0.35)';
    for (let i = 0; i < manchas; i++) {
      g.lineWidth = 1 + Math.random() * 2; g.beginPath();
      let x = Math.random() * w, y = Math.random() * h; g.moveTo(x, y);
      for (let k = 0; k < 6; k++) { x += (Math.random() - 0.5) * 60; y += Math.random() * 40; g.lineTo(x, y); }
      g.stroke();
    }
  }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export const TEX = {
  concreto: () => ruido(512, 512, [128, 126, 122], 70, 1, 10),
  roca: () => ruido(512, 512, [92, 88, 84], 120, 1.5, 30),
  arena: () => ruido(512, 512, [176, 160, 132], 40, 0.8),
  ladrillo: () => {
    const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
    g.fillStyle = '#5e5a55'; g.fillRect(0, 0, 512, 512);
    for (let y = 0; y < 512; y += 32) for (let x = -64; x < 512; x += 64) {
      const o = (y / 32) % 2 ? 32 : 0, l = 120 + Math.random() * 30;
      g.fillStyle = `rgb(${l},${l - 6},${l - 14})`; g.fillRect(x + o + 2, y + 2, 60, 28);
    }
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t;
  },
};

// ---------- escena base ----------
export function crear(W, H, opciones = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(W, H);
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = opciones.exposicion || 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  document.getElementById('lienzo').appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(opciones.fov || 38, W / H, 0.1, 500);
  return { renderer, scene, cam };
}

export function cielo(scene, arriba, abajo) {
  const c = document.createElement('canvas'); c.width = 4; c.height = 256; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, 256); gr.addColorStop(0, arriba); gr.addColorStop(1, abajo);
  g.fillStyle = gr; g.fillRect(0, 0, 4, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; scene.background = t;
}

export function luces(scene, { sol = 2.6, cielo_ = 0.9, dir = [8, 14, 6], color = 0xfff1dd } = {}) {
  scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x6b5f50, cielo_));
  const s = new THREE.DirectionalLight(color, sol); s.position.set(...dir); s.castShadow = true;
  s.shadow.mapSize.set(2048, 2048); const k = 25;
  Object.assign(s.shadow.camera, { left: -k, right: k, top: k, bottom: -k, near: 1, far: 80 });
  s.shadow.bias = -0.0004; s.shadow.normalBias = 0.02; scene.add(s);
  return s;
}

export function caja(scene, w, h, d, x, y, z, mat, sombra = true) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z); m.castShadow = sombra; m.receiveShadow = true; scene.add(m); return m;
}

export function mat(color, extra = {}) { return new THREE.MeshStandardMaterial(Object.assign({ color, roughness: 0.85 }, extra)); }
export function matTex(tex, rep = [1, 1], color = 0xffffff, extra = {}) {
  const t = tex.clone(); t.needsUpdate = true; t.repeat.set(...rep);
  return new THREE.MeshStandardMaterial(Object.assign({ map: t, color, roughness: 0.95 }, extra));
}

// ---------- maniquí articulado ----------
const PIEL = () => new THREE.MeshStandardMaterial({ color: 0xd9d6d0, roughness: 0.55, metalness: 0.0 });

function hueso(radio, largo, material) {
  const g = new THREE.Group();
  const m = new THREE.Mesh(new THREE.CapsuleGeometry(radio, largo, 6, 14), material);
  m.position.y = -largo / 2; m.castShadow = true; m.receiveShadow = true; g.add(m);
  const fin = new THREE.Group(); fin.position.y = -largo; g.add(fin); g.userData.fin = fin;
  return g;
}
function bola(r, material) { const m = new THREE.Mesh(new THREE.SphereGeometry(r, 18, 14), material); m.castShadow = true; return m; }

/** ropa: {camisa, pantalon, gorra, casco, linterna, escala} colores hex o null (null = madera gris) */
export function maniqui(ropa = {}) {
  const piel = PIEL();
  const camisa = ropa.camisa != null ? mat(ropa.camisa, { roughness: 0.9 }) : piel;
  const pantalon = ropa.pantalon != null ? mat(ropa.pantalon, { roughness: 0.9 }) : piel;
  const raiz = new THREE.Group();
  const cadera = new THREE.Group(); cadera.position.y = 0.95; raiz.add(cadera);
  const pelvis = new THREE.Mesh(new THREE.SphereGeometry(0.16, 18, 14), pantalon); pelvis.scale.set(1.15, 0.7, 0.8); pelvis.castShadow = true; cadera.add(pelvis);
  // columna
  const torso = new THREE.Group(); torso.position.y = 0.05; cadera.add(torso);
  const pecho = new THREE.Mesh(new THREE.CapsuleGeometry(0.15, 0.32, 6, 16), camisa); pecho.position.y = 0.26; pecho.scale.set(1.25, 1, 0.75); pecho.castShadow = true; torso.add(pecho);
  const cuello = new THREE.Group(); cuello.position.y = 0.55; torso.add(cuello);
  cuello.add(Object.assign(bola(0.045, piel), {}));
  const cabeza = new THREE.Group(); cabeza.position.y = 0.06; cuello.add(cabeza);
  const craneo = bola(0.11, piel); craneo.scale.set(0.9, 1.15, 1); craneo.position.y = 0.1; cabeza.add(craneo);
  if (ropa.casco) {
    const c = new THREE.Mesh(new THREE.SphereGeometry(0.125, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), mat(ropa.casco, { roughness: 0.4 }));
    c.position.y = 0.16; c.castShadow = true; cabeza.add(c);
    const ala = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.015, 24), mat(ropa.casco, { roughness: 0.4 })); ala.position.y = 0.16; cabeza.add(ala);
  }
  if (ropa.gorra) {
    const c = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.115, 0.07, 20), mat(ropa.gorra)); c.position.y = 0.22; c.castShadow = true; cabeza.add(c);
    const v = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.012, 0.09), mat(0x111111)); v.position.set(0, 0.19, 0.12); cabeza.add(v);
  }
  if (ropa.linterna) {
    const l = new THREE.SpotLight(0xfff3d0, 30, 14, 0.38, 0.55, 1.3); l.position.set(0, 0.2, 0.1); l.castShadow = true;
    l.shadow.mapSize.set(512, 512); cabeza.add(l); const tg = new THREE.Object3D(); tg.position.set(0, 0.0, 3); cabeza.add(tg); l.target = tg;
    const foco = bola(0.025, new THREE.MeshBasicMaterial({ color: 0xfff6d8 })); foco.position.set(0, 0.2, 0.12); cabeza.add(foco);
    raiz.userData.linterna = l;
  }
  const J = { raiz, cadera, torso, cuello, cabeza };
  // brazos
  for (const [lado, s] of [['i', 1], ['d', -1]]) {
    const hombro = new THREE.Group(); hombro.position.set(0.22 * s, 0.47, 0); torso.add(hombro);
    hombro.add(bola(0.055, camisa));
    const brazo = hueso(0.045, 0.24, camisa); hombro.add(brazo);
    const codo = brazo.userData.fin; codo.add(bola(0.042, piel));
    const ante = hueso(0.038, 0.22, piel); codo.add(ante);
    const mano = bola(0.045, piel); mano.scale.set(0.8, 1.2, 0.6); mano.position.y = -0.04; ante.userData.fin.add(mano);
    // pierna
    const ingle = new THREE.Group(); ingle.position.set(0.1 * s, -0.03, 0); cadera.add(ingle);
    const muslo = hueso(0.065, 0.36, pantalon); ingle.add(muslo);
    const rod = muslo.userData.fin; rod.add(bola(0.055, pantalon));
    const pierna = hueso(0.05, 0.36, pantalon); rod.add(pierna);
    const pie = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.06, 0.22), mat(0x2a2a2a)); pie.position.set(0, -0.06, 0.05); pie.castShadow = true;
    pierna.userData.fin.add(pie);
    Object.assign(J, { ['hombro_' + lado]: brazo, ['codo_' + lado]: ante, ['muslo_' + lado]: muslo, ['rodilla_' + lado]: pierna });
  }
  raiz.userData.J = J;
  raiz.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return raiz;
}

const R = Math.PI / 180;
/** poses: angulos en grados. p = {torso:[x,y,z], cabeza:[x,y,z], hombro_i:[x,y,z], codo_i:x, muslo_i:x, rodilla_i:x, ... , baja: metros} */
export function posar(m, p) {
  const J = m.userData.J;
  const set = (o, v) => { if (!v) return; if (typeof v === 'number') o.rotation.x = v * R; else o.rotation.set(v[0] * R, (v[1] || 0) * R, (v[2] || 0) * R); };
  set(J.torso, p.torso); set(J.cabeza, p.cabeza); set(J.cadera, p.cadera);
  for (const k of ['hombro_i', 'hombro_d', 'codo_i', 'codo_d', 'muslo_i', 'muslo_d', 'rodilla_i', 'rodilla_d']) set(J[k], p[k]);
  J.cadera.position.y = 0.95 - (p.baja || 0);
}

export const POSE = {
  parado: { hombro_i: [0, 0, 6], hombro_d: [0, 0, -6], codo_i: -8, codo_d: -8 },
  mira_arriba: { cabeza: [-35, 0, 0], torso: [-6, 0, 0], hombro_i: [0, 0, 8], hombro_d: [-20, 0, -10], codo_d: -30 },
  senala: { cabeza: [-30, 0, 0], torso: [-5, 0, 0], hombro_d: [-150, 0, -10], codo_d: -5, hombro_i: [0, 0, 8] },
  corre: (f = 0) => ({ torso: [14, 0, 0], hombro_i: [-50 * Math.sin(f), 0, 8], hombro_d: [50 * Math.sin(f), 0, -8], codo_i: -70, codo_d: -70,
    muslo_i: [50 * Math.sin(f), 0, 0], muslo_d: [-50 * Math.sin(f), 0, 0], rodilla_i: 30 + 40 * Math.max(0, -Math.sin(f)), rodilla_d: 30 + 40 * Math.max(0, Math.sin(f)), baja: 0.06 }),
  sentado: { muslo_i: [-90, 0, 4], muslo_d: [-90, 0, -4], rodilla_i: 90, rodilla_d: 90, baja: 0.47, hombro_i: [-30, 0, 6], hombro_d: [-30, 0, -6], codo_i: -40, codo_d: -40, torso: [8, 0, 0] },
  patea: { torso: [-8, 0, 0], muslo_d: [-60, 0, 0], rodilla_d: 10, muslo_i: [10, 0, 0], hombro_i: [-30, 0, 40], hombro_d: [30, 0, -40] },
  agarra: { cabeza: [-20, 0, 0], hombro_i: [-170, 0, 10], hombro_d: [-170, 0, -10], codo_i: -10, codo_d: -10 },
};

// ---------- helicóptero tipo Alouette II ----------
export function helicoptero(color = 0x1f3a5f) {
  const h = new THREE.Group();
  const cuerpo = mat(color, { roughness: 0.45, metalness: 0.2 });
  const vidrio = new THREE.MeshPhysicalMaterial({ color: 0x9fc4dd, roughness: 0.05, transmission: 0.0, transparent: true, opacity: 0.45, metalness: 0.1 });
  const burbuja = new THREE.Mesh(new THREE.SphereGeometry(0.95, 28, 20), vidrio); burbuja.scale.set(1.25, 0.95, 0.95); burbuja.position.set(0.5, 1.45, 0); h.add(burbuja);
  const piso = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.25, 1.6), cuerpo); piso.position.set(0.3, 0.75, 0); h.add(piso);
  const motor = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.7, 0.9), cuerpo); motor.position.set(-0.8, 1.5, 0); h.add(motor);
  // cola en celosía
  const viga = (a, b, r = 0.03) => {
    const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), L = A.distanceTo(B);
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, L, 6), cuerpo); m.position.copy(A).add(B).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), B.clone().sub(A).normalize()); m.castShadow = true; h.add(m);
  };
  const largo = 5.2;
  for (const [y, z] of [[1.75, 0.25], [1.75, -0.25], [1.25, 0], [1.25, 0]]) viga([-1.3, y, z], [-1.3 - largo, 1.6, 0], 0.035);
  for (let i = 0; i < 9; i++) { const x = -1.4 - i * 0.55; const k = 1 - i / 10; viga([x, 1.6 + 0.15 * k, 0.25 * k], [x - 0.55, 1.3 + 0.3 * (1 - k), -0.25 * k], 0.018); }
  const timon = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.9, 0.05), cuerpo); timon.position.set(-1.3 - largo, 1.75, 0.08); h.add(timon);
  // patines
  for (const z of [0.8, -0.8]) {
    viga([1.6, 0, z], [-1.2, 0, z], 0.05);
    viga([0.9, 0, z], [0.6, 0.7, z * 0.7], 0.035); viga([-0.6, 0, z], [-0.4, 0.7, z * 0.7], 0.035);
  }
  viga([-0.6, 1.85, 0], [-0.6, 2.35, 0], 0.07);
  const rotor = new THREE.Group(); rotor.position.set(-0.6, 2.38, 0); h.add(rotor);
  for (let i = 0; i < 3; i++) { const p = new THREE.Mesh(new THREE.BoxGeometry(5.0, 0.03, 0.22), mat(0x222222)); p.position.x = 2.5; const g = new THREE.Group(); g.rotation.y = i * 2 * Math.PI / 3; g.add(p); rotor.add(g); }
  // disco borroso del rotor
  const disco = new THREE.Mesh(new THREE.CircleGeometry(5, 48), new THREE.MeshBasicMaterial({ color: 0x111111, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false }));
  disco.rotation.x = -Math.PI / 2; rotor.add(disco);
  const rc = new THREE.Group(); rc.position.set(-1.3 - largo, 1.75, -0.12); h.add(rc);
  for (let i = 0; i < 2; i++) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.9, 0.02), mat(0x222222)); p.rotation.z = i * Math.PI / 2; rc.add(p); }
  h.userData.rotor = rotor; h.userData.rc = rc;
  h.traverse(o => { if (o.isMesh && o.material !== vidrio) { o.castShadow = true; o.receiveShadow = true; } });
  disco.castShadow = false; disco.receiveShadow = false;
  return h;
}

// ---------- polvo ----------
export function polvo(scene, n = 60, color = 0xcbbfa8) {
  const g = new THREE.Group(); const tx = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d');
    const gr = x.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,0.8)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = gr; x.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c);
  })();
  for (let i = 0; i < n; i++) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, color, transparent: true, opacity: 0.0, depthWrite: false }));
    s.userData = { a: Math.random() * Math.PI * 2, r: Math.random(), v: 0.5 + Math.random() }; g.add(s);
  }
  scene.add(g); return g;
}
export function moverPolvo(g, cx, cz, fuerza, t) {
  g.children.forEach(s => {
    const u = s.userData, r = 1.5 + (u.r * 6 + t * u.v * 2) % 7;
    s.position.set(cx + Math.cos(u.a) * r, 0.3 + u.r * 1.2, cz + Math.sin(u.a) * r);
    const k = 1.5 + r * 0.6; s.scale.set(k, k, 1); s.material.opacity = 0.35 * fuerza * (1 - r / 9);
  });
}

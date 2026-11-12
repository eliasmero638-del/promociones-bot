// Personas 3D realistas (Microsoft Rocketbox, licencia MIT: uso comercial libre) cargadas desde FBX.
import * as THREE from 'three';
import { FBXLoader } from './tj/examples/jsm/loaders/FBXLoader.js';
import * as SkeletonUtils from './tj/examples/jsm/utils/SkeletonUtils.js';

const BASE = 'rb/Assets/Avatars/';
const cache = {};

function cargador(carpeta) {
  const man = new THREE.LoadingManager();
  man.setURLModifier(url => {
    // las texturas vienen como .tga con rutas de la PC del autor → las mandamos a nuestras copias livianas
    const m = url.match(/([^\/\\]+)\.(tga|png|jpg)$/i);
    if (m && !url.startsWith('data:') && !url.endsWith('.fbx')) {
      const n = m[1];
      if (/specular/i.test(n)) return 'rb/vacio.png';            // no se usa (ahorra peso)
      return carpeta + 'Textures/' + n + (/opacity/i.test(n) ? '.png' : '.jpg');
    }
    return url;
  });
  man.addHandler(/\.tga$/i, new THREE.TextureLoader(man));
  return new FBXLoader(man);
}

let indice = null;
export async function cargar(nombre) {          // 'Male_Adult_01' o 'Adults/Male_Adult_01'
  if (!nombre.includes('/')) {
    indice = indice || await fetch('rb/indice.json').then(r => r.json()).catch(() => ({}));
    if (!indice[nombre]) throw new Error('persona 3D no descargada: ' + nombre + ' (python3 tools/tres_d.py preparar ' + nombre + ')');
    nombre = indice[nombre];
  }
  if (!cache[nombre]) {
    const carpeta = BASE + nombre + '/';
    const id = nombre.split('/').pop();
    cache[nombre] = cargador(carpeta).loadAsync(carpeta + 'Export/' + id + '.fbx').then(obj => {
      obj.traverse(o => {
        if (!o.isMesh) return;
        o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false;
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        const nuevos = mats.map(m => {
          const s = new THREE.MeshStandardMaterial({ map: m.map || null, normalMap: m.normalMap || null, color: 0xffffff,
            roughness: 0.75, metalness: 0.0 });
          if (m.map) m.map.colorSpace = THREE.SRGBColorSpace;
          const opa = /opacity/i.test(m.name) || (m.alphaMap) || (m.map && /opacity/i.test(m.map.name || m.map.image?.src || ''));
          if (opa || m.transparent) { s.alphaTest = 0.4; s.transparent = false; s.side = THREE.DoubleSide; if (m.alphaMap) s.alphaMap = m.alphaMap; }
          s.name = m.name; return s;
        });
        o.material = Array.isArray(o.material) ? nuevos : nuevos[0];
      });
      return obj;
    });
  }
  const orig = await cache[nombre];
  const c = SkeletonUtils.clone(orig);
  c.scale.setScalar(0.01);                       // vienen en centímetros
  c.userData.huesos = {};
  c.traverse(o => { if (o.isBone) c.userData.huesos[o.name] = o; });
  return c;
}

const anims = {};
export async function animacion(archivo) {
  if (!anims[archivo]) anims[archivo] = new FBXLoader().loadAsync('rb/Assets/Animations/' + archivo).then(o => o.animations[0]);
  return anims[archivo];
}

/** Pone a la persona en un cuadro concreto de una animación (sin mover su posición en el mundo). */
export function enPose(persona, clip, segundo, quedarse = true) {
  const mix = new THREE.AnimationMixer(persona);
  let c = clip;
  if (quedarse) {                                // quitar el avance de la cadera (que no se salga de su sitio)
    c = clip.clone();
    c.tracks = c.tracks.map(t => {
      if (t.name !== 'Bip01.position') return t;
      const t2 = t.clone(); const v = t2.values;
      for (let i = 0; i < v.length; i += 3) { v[i] = t.values[0]; v[i + 2] = t.values[2]; }   // sin avanzar en X/Z
      return t2;
    }).filter(t => !/MotionExtractionHelper/.test(t.name));
  }
  const a = mix.clipAction(c); a.play(); mix.setTime(segundo % clip.duration);
  persona.userData.mixer = mix;
  return mix;
}

/** Gira un hueso (grados) sumándolo a la pose actual. */
export function girar(persona, hueso, x = 0, y = 0, z = 0) {
  const b = persona.userData.huesos[hueso]; if (!b) return;
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(x * Math.PI / 180, y * Math.PI / 180, z * Math.PI / 180));
  b.quaternion.multiply(q);
}

/** Espera a que todas las texturas de la escena terminen de cargar. */
export async function esperarTexturas(scene, max = 20000) {
  const t0 = performance.now();
  while (performance.now() - t0 < max) {
    let faltan = 0;
    scene.traverse(o => { if (!o.isMesh) return; (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => {
      for (const k of ['map', 'normalMap', 'alphaMap']) { const t = m[k]; if (t && (!t.image || (t.image.complete === false) || (t.image.width === 0))) faltan++; } }); });
    if (!faltan) return true;
    await new Promise(r => setTimeout(r, 100));
  }
  return false;
}

// Kit de escenarios 3D reutilizables para las escenas de Ridmer. Cada función arma un escenario en una THREE.Scene.
// Agrega aquí los escenarios nuevos que armes (cada uno que sirva para otras historias).
import * as THREE from 'three';
import * as M from './motor.js';
import * as G from './gente.js';

export const ease = x => x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
export const lerp = (a, b, k) => a + (b - a) * k;
export const A = 'all_animations_max_motextr_static/', AX = 'all_animations_max_motextr_xy/';
export const emis = (c, i = 1) => new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: i });

/** Persona realista con una animación. Devuelve el objeto; muévela con p.userData.mixer.setTime(seg). */
export async function persona(sc, quien, anim, x = 0, z = 0, giro = 0) {
  const p = await G.cargar(quien); p.position.set(x, 0, z); p.rotation.y = giro * Math.PI / 180; sc.add(p);
  const clip = await G.animacion(anim.includes('/') ? anim : A + anim);
  G.enPose(p, clip, 0); p.userData.clip = clip; return p;
}
/** Cambia la animación de una persona (por ejemplo de mirar a correr). */
export async function cambiar(p, anim) {
  const clip = await G.animacion(anim.includes('/') ? anim : A + anim);
  p.userData.mixer?.stopAllAction(); G.enPose(p, clip, 0); p.userData.clip = clip; return clip;
}
/** Carga una animación para usarla después con cambiarClip (sin esperar dentro de frame). */
export const clip = anim => G.animacion(anim.includes('/') ? anim : A + anim);
export function cambiarClip(p, c) { p.userData.mixer?.stopAllAction(); G.enPose(p, c, 0); p.userData.clip = c; }
/** Hace que mire hacia arriba (grados) después de setTime. */
export function mirarArriba(p, grados) {
  p.updateMatrixWorld(true); G.girar(p, 'Bip01_Neck', 0, 0, -grados * 0.4); G.girar(p, 'Bip01_Head', 0, 0, -grados * 0.6);
}
/** Haz de luz visible (postes, faros, linternas). */
export function cono(sc, x, y, z, alto, radio, color, op = 0.08, rot = null) {
  const g = new THREE.ConeGeometry(radio, alto, 32, 1, true); g.translate(0, -alto / 2, 0);
  const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  m.position.set(x, y, z); if (rot) m.rotation.set(...rot); sc.add(m); return m;
}

/** Carro sedán (frente hacia +X). antena=true → carro del FBI que rastrea. */
export function carro(sc, color = 0x1d2329, antena = false, faros = true) {
  const g = new THREE.Group(); const m = M.mat(color, { roughness: 0.35, metalness: 0.5 }), v = M.mat(0x0b0d12, { roughness: 0.1, metalness: 0.8 });
  const add = (w, h, d, x, y, z, mm) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; b.receiveShadow = true; g.add(b); return b; };
  add(4.6, 0.7, 1.8, 0, 0.6, 0, m); add(2.4, 0.6, 1.6, -0.2, 1.2, 0, v); add(2.3, 0.08, 1.62, -0.2, 1.52, 0, m);
  for (const [x, z] of [[1.45, 0.85], [1.45, -0.85], [-1.45, 0.85], [-1.45, -0.85]]) {
    const r = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.36, 0.25, 20), M.mat(0x111111)); r.rotation.x = Math.PI / 2; r.position.set(x, 0.36, z); g.add(r); }
  add(0.05, 0.18, 0.4, 2.31, 0.75, 0.6, emis(0xfff4d0, 3)); add(0.05, 0.18, 0.4, 2.31, 0.75, -0.6, emis(0xfff4d0, 3));
  add(0.05, 0.14, 0.35, -2.31, 0.75, 0.6, emis(0xff2a1a, 2)); add(0.05, 0.14, 0.35, -2.31, 0.75, -0.6, emis(0xff2a1a, 2));
  if (antena) { add(0.5, 0.06, 0.35, -0.9, 1.57, 0, M.mat(0x222222)); const a = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 1.1, 6), M.mat(0x222222)); a.position.set(-0.9, 2.1, 0); g.add(a); }
  if (faros) for (const z of [0.6, -0.6]) { cono(g, 2.3, 0.75, z, 9, 1.6, 0xfff2d0, 0.05, [0, 0, Math.PI / 2 - 0.08]);
    const l = new THREE.SpotLight(0xfff0cc, 60, 30, 0.45, 0.5, 1.2); l.position.set(2.3, 0.75, z); const tg = new THREE.Object3D(); tg.position.set(12, 0, z); g.add(tg); l.target = tg; g.add(l); }
  sc.add(g); return g;
}

/** Cárcel de día: patio con cancha, edificio de celdas con barrotes, muros con alambre, torres. Patio centrado en 0,0. */
export function carcel(scene) {
  const con = M.TEX.concreto(), lad = M.TEX.ladrillo();
  M.cielo(scene, '#7d8fa6', '#d9c9b0'); scene.fog = new THREE.Fog(0xcfc4b2, 45, 120);
  M.caja(scene, 60, 0.2, 60, 0, -0.1, 0, M.matTex(con, [10, 10], 0x9b968c));
  M.caja(scene, 34, 11, 6, 0, 5.5, -13, M.matTex(lad, [9, 3], 0xb8a89a));
  const negro = M.mat(0x16171a), barra = M.mat(0x6f6f6f, { metalness: 0.6, roughness: 0.4 });
  for (let f = 0; f < 3; f++) for (let c = 0; c < 12; c++) {
    const x = -14.5 + c * 2.65, y = 2.4 + f * 3.1;
    M.caja(scene, 1.0, 1.4, 0.1, x, y, -9.95, negro, false);
    for (let b = 0; b < 4; b++) M.caja(scene, 0.06, 1.4, 0.08, x - 0.36 + b * 0.24, y, -9.88, barra, false);
  }
  M.caja(scene, 35, 0.6, 7, 0, 11.3, -13, M.mat(0x4a4642));
  for (const x of [-14, 14]) {
    M.caja(scene, 0.8, 6, 24, x, 3, 0, M.matTex(con, [6, 2], 0xa8a39a));
    for (let z = -11; z < 12; z += 0.9) { const r = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.025, 6, 16), barra); r.position.set(x, 6.4, z); r.rotation.y = Math.PI / 2; scene.add(r); }
  }
  for (const x of [-14, 14]) { const z = -10;
    M.caja(scene, 2, 9, 2, x, 4.5, z, M.matTex(con, [1, 4], 0x8f8a82)); M.caja(scene, 2.8, 1.8, 2.8, x, 9.9, z, M.mat(0x3b3936));
    M.caja(scene, 2.5, 0.8, 0.05, x, 10, z + 1.42, M.mat(0xfbe3a0, { emissive: 0x6a5a30 }), false); M.caja(scene, 3.4, 0.25, 3.4, x, 10.9, z, M.mat(0x2a2826)); }
  const linea = M.mat(0xe8e4da);
  M.caja(scene, 0.12, 0.02, 14, 0, 0.01, 0, linea, false); M.caja(scene, 16, 0.02, 0.12, 0, 0.01, 7, linea, false); M.caja(scene, 16, 0.02, 0.12, 0, 0.01, -7, linea, false);
  M.luces(scene, { dir: [10, 16, 8], sol: 3.2 });
}

/** Calle de ciudad de noche: edificios de departamentos con ventanas prendidas, postes con luz, carros estacionados.
 *  La calle va a lo largo de X (z≈0..3); los edificios atrás en z≈-13. Devuelve {ventanaEspecial: [x,y,z]}. */
export function calleNoche(sA) {
  M.cielo(sA, '#05070d', '#1b2233'); sA.fog = new THREE.FogExp2(0x0d121c, 0.025);
  sA.add(new THREE.HemisphereLight(0x6f86b8, 0x1a1a22, 0.9));
  const luna = new THREE.DirectionalLight(0x8aa4ff, 1.4); luna.position.set(-10, 20, 8); luna.castShadow = true; luna.shadow.mapSize.set(2048, 2048);
  Object.assign(luna.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30 }); sA.add(luna);
  M.caja(sA, 120, 0.2, 40, 0, -0.1, 0, M.matTex(M.TEX.concreto(), [30, 10], 0x3a3a3e));
  M.caja(sA, 120, 0.3, 4, 0, 0.05, -6, M.matTex(M.TEX.concreto(), [30, 1], 0x77736c));
  for (let x = -40; x < 40; x += 4) M.caja(sA, 2, 0.02, 0.15, x, 0.01, 0, emis(0xcfc6a0, 0.15), false);
  const lad = M.TEX.ladrillo(); let especial = null; let semilla = 3;
  const azar = () => { semilla = (semilla * 9301 + 49297) % 233280; return semilla / 233280; };
  for (const [x0, ancho, pisos] of [[-22, 14, 3], [-7, 13, 3], [8, 15, 4], [24, 12, 3]]) {
    M.caja(sA, ancho, pisos * 3.2, 9, x0, pisos * 1.6, -13, M.matTex(lad, [ancho / 3, pisos], 0x9a7f70));
    for (let p = 0; p < pisos; p++) for (let c = 0; c < Math.floor(ancho / 2.6); c++) {
      const x = x0 - ancho / 2 + 1.6 + c * 2.6, y = 1.7 + p * 3.2;
      const es = (x0 === -7 && p === 1 && c === 2), prende = azar() < 0.5;
      M.caja(sA, 1.2, 1.5, 0.1, x, y, -8.45, es ? emis(0x7fd6ff, 0.9) : prende ? emis(0xffb465, 0.55) : M.mat(0x0c0e14, { roughness: 0.2 }), false);
      if (es) { const l = new THREE.PointLight(0x7fd6ff, 6, 8); l.position.set(x, y, -7.6); sA.add(l); especial = [x, y, -8.4]; }
    }
  }
  for (let x = -30; x <= 30; x += 12) {
    M.caja(sA, 0.15, 6, 0.15, x, 3, -4.6, M.mat(0x2a2a2a)); M.caja(sA, 1.2, 0.12, 0.25, x, 6, -4.1, M.mat(0x2a2a2a));
    M.caja(sA, 0.5, 0.06, 0.25, x + 0.3, 5.93, -3.7, emis(0xffb35c, 3), false);
    cono(sA, x + 0.3, 5.9, -3.7, 5.9, 3.2, 0xffa050, 0.07);
    const l = new THREE.SpotLight(0xffa85a, 120, 18, 0.7, 0.6, 1.4); l.position.set(x + 0.3, 5.9, -3.7); const tg = new THREE.Object3D(); tg.position.set(x + 0.3, 0, -2); sA.add(tg); l.target = tg; sA.add(l);
  }
  for (const [x, c] of [[-16, 0x5a1c1c], [3, 0x2a3540], [15, 0x6b6b6b]]) carro(sA, c, false, false).position.set(x, 0, -3.2);
  return { ventanaEspecial: especial };
}

/** Cuarto oscuro con escritorio y computadora de tubo (pantalla verde que corre), ventana con persianas y luz de luna.
 *  La silla está en (0.2, -0.95) mirando a -Z. Llama a cuarto.pantalla(t) en cada cuadro. */
export function cuartoComputadora(sB) {
  sB.background = new THREE.Color(0x05060a);
  sB.add(new THREE.HemisphereLight(0x405070, 0x101014, 0.25));
  const pared = M.matTex(M.TEX.concreto(), [3, 2], 0x6d6a66), piso = M.matTex(M.TEX.concreto(), [4, 4], 0x4a3f36);
  M.caja(sB, 8, 0.1, 8, 0, -0.05, 0, piso); M.caja(sB, 8, 3, 0.1, 0, 1.5, -2.2, pared); M.caja(sB, 0.1, 3, 8, -3, 1.5, 0, pared);
  M.caja(sB, 0.05, 1.4, 1.6, -2.94, 1.7, 0.6, emis(0x22324d, 0.6), false);
  for (let i = 0; i < 12; i++) M.caja(sB, 0.06, 0.06, 1.65, -2.9, 1.05 + i * 0.115, 0.6, M.mat(0xbfbab0), false);
  const luna = new THREE.SpotLight(0x7f9cff, 25, 10, 0.5, 0.7, 1.3); luna.position.set(-2.6, 2.2, 0.6); const tl = new THREE.Object3D(); tl.position.set(0.5, 0, 0.3); sB.add(tl); luna.target = tl; luna.castShadow = true; sB.add(luna);
  const madera = M.mat(0x4a3424, { roughness: 0.7 });
  M.caja(sB, 1.8, 0.05, 0.8, 0.2, 0.75, -1.6, madera); for (const [x, z] of [[-0.6, -1.9], [1.0, -1.9], [-0.6, -1.3], [1.0, -1.3]]) M.caja(sB, 0.05, 0.75, 0.05, x, 0.375, z, madera);
  M.caja(sB, 0.5, 0.42, 0.45, 0.2, 1.0, -1.75, M.mat(0xcfc8b6, { roughness: 0.5 })); M.caja(sB, 0.42, 0.34, 0.3, 0.2, 1.0, -1.98, M.mat(0xbfb8a6));
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 384;
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.31), new THREE.MeshBasicMaterial({ map: tex })); scr.position.set(0.2, 1.0, -1.522); sB.add(scr);
  const b1 = new THREE.PointLight(0x5cff9a, 1.6, 3.5, 1.6); b1.position.set(0.2, 1.05, -1.3); sB.add(b1);
  const b2 = new THREE.SpotLight(0x8affb6, 3.2, 3, 0.9, 0.8, 1.5); b2.position.set(0.2, 1.05, -1.45); const tb = new THREE.Object3D(); tb.position.set(0.2, 1.2, 0.5); sB.add(tb); b2.target = tb; sB.add(b2);
  M.caja(sB, 0.45, 0.03, 0.16, 0.2, 0.79, -1.35, M.mat(0xd8d2c0)); M.caja(sB, 0.06, 0.03, 0.18, 0.75, 0.79, -1.4, M.mat(0x1a1a1a));
  M.caja(sB, 0.06, 0.12, 0.02, 0.75, 0.86, -1.48, M.mat(0x1a1a1a));
  for (let i = 0; i < 4; i++) M.caja(sB, 0.3, 0.02, 0.22, -0.4 + i * 0.03, 0.79 + i * 0.022, -1.65, M.mat(0xe8e2d0), false);
  M.caja(sB, 0.5, 0.05, 0.5, 0.2, 0.47, -0.95, M.mat(0x222226)); M.caja(sB, 0.5, 0.6, 0.06, 0.2, 0.8, -0.68, M.mat(0x222226));
  return {
    pantalla(t) {          // letras verdes al azar que corren (no es código real)
      const g = cv.getContext('2d'); g.fillStyle = '#031a08'; g.fillRect(0, 0, 512, 384); g.font = '18px monospace';
      const r = Math.floor(t * 9);
      const al = k => { let s = '', x = Math.sin(k * 12.9898) * 43758.5453; for (let i = 0; i < 40; i++) { x = Math.sin(x) * 10000; s += '01ABCDEF><:/.#$%'[Math.floor((x - Math.floor(x)) * 16)]; } return s; };
      for (let i = 0; i < 18; i++) { g.fillStyle = i === 17 ? '#b8ffc8' : '#36e070'; g.fillText(al(r + i).slice(0, 10 + (r + i) * 7 % 30), 14, 26 + i * 20); }
      g.fillStyle = 'rgba(0,0,0,0.25)'; for (let y = 0; y < 384; y += 3) g.fillRect(0, y, 512, 1); tex.needsUpdate = true;
    },
  };
}

/** Pasillo de edificio con focos y una puerta en la pared izquierda (x=-1.44, z=-1). */
export function pasillo(sC) {
  sC.background = new THREE.Color(0x0a0a0c); sC.add(new THREE.HemisphereLight(0xfff0d8, 0x202020, 0.35));
  const pared = M.matTex(M.TEX.concreto(), [3, 1], 0x8c8576), piso = M.matTex(M.TEX.concreto(), [2, 8], 0x5a4c3e);
  M.caja(sC, 3, 0.1, 14, 0, -0.05, 0, piso); M.caja(sC, 0.1, 3, 14, -1.5, 1.5, 0, pared); M.caja(sC, 0.1, 3, 14, 1.5, 1.5, 0, pared); M.caja(sC, 3, 0.1, 14, 0, 3, 0, pared);
  M.caja(sC, 0.08, 2.1, 0.95, -1.44, 1.05, -1, M.mat(0x5b3a24, { roughness: 0.6 }));
  M.caja(sC, 0.05, 0.06, 0.06, -1.39, 1.0, -0.65, M.mat(0xc9a64a, { metalness: 0.8, roughness: 0.3 }));
  for (const z of [-4, 1, 5]) { M.caja(sC, 0.4, 0.05, 0.4, 0, 2.95, z, emis(0xfff1d0, 2), false); const l = new THREE.PointLight(0xffe2b8, 8, 7, 1.5); l.position.set(0, 2.7, z); l.castShadow = z === 1; sC.add(l); }
}

/** Espera a que carguen las texturas de una escena (llamar antes de devolver frame). */
export const esperar = sc => G.esperarTexturas(sc);

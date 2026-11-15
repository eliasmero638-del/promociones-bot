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
    pantalla(t, mensaje = null, k = 1) {   // letras verdes al azar que corren (no es código real); mensaje = texto que se escribe
      const g = cv.getContext('2d'); g.fillStyle = '#031a08'; g.fillRect(0, 0, 512, 384); g.font = '18px monospace';
      if (mensaje) {
        const lineas = mensaje.split('\n'), total = mensaje.replace(/\n/g, '').length; let n = Math.floor(total * Math.min(1, k)), y = 70;
        g.font = 'bold 34px monospace'; g.fillStyle = '#7dffa8';
        for (const l of lineas) { const parte = l.slice(0, Math.max(0, n)); n -= l.length; g.fillText(parte + (n < 0 && Math.floor(t * 3) % 2 ? '_' : ''), 24, y); y += 48; }
        g.fillStyle = 'rgba(0,0,0,0.25)'; for (let y2 = 0; y2 < 384; y2 += 3) g.fillRect(0, y2, 512, 1); tex.needsUpdate = true; return;
      }
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

/** Bosque de pinos de noche (invierno, algo de nieve). Claro en el centro (0,0). Linternas: usa linterna(). */
export function bosqueNoche(sc, { luna = 1.0, semilla = 7, claro = 5 } = {}) {
  M.cielo(sc, '#03050b', '#121a2b'); sc.fog = new THREE.FogExp2(0x0b1018, 0.045);
  sc.add(new THREE.HemisphereLight(0x5a6f99, 0x15141a, 0.55 * luna));
  const l = new THREE.DirectionalLight(0x8fa8ff, 1.1 * luna); l.position.set(-12, 22, 6); l.castShadow = true; l.shadow.mapSize.set(2048, 2048);
  Object.assign(l.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30 }); sc.add(l);
  M.caja(sc, 140, 0.2, 140, 0, -0.1, 0, M.matTex(M.TEX.arena(), [40, 40], 0x6c6a72));
  const nieve = M.mat(0x8d95a6, { roughness: 1 });
  let s = semilla; const az = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  for (let i = 0; i < 140; i++) { const r = new THREE.Mesh(new THREE.CircleGeometry(0.3 + az() * 0.9, 7), nieve); r.rotation.x = -Math.PI / 2; r.position.set((az() - 0.5) * 70, 0.012 + i * 0.0001, (az() - 0.5) * 70); sc.add(r); }
  const tronco = M.mat(0x2b2018, { roughness: 1 }), hoja = M.mat(0x14261c, { roughness: 1 }), hoja2 = M.mat(0x1b3326, { roughness: 1 });
  const arboles = [];
  for (let i = 0; i < 260; i++) {
    const x = (az() - 0.5) * 80, z = (az() - 0.5) * 80; if (Math.hypot(x, z) < claro) continue;
    const h = 6 + az() * 8, g = new THREE.Group();
    const t = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.25, h, 7), tronco); t.position.y = h / 2; t.castShadow = true; g.add(t);
    for (let k = 0; k < 4; k++) { const c = new THREE.Mesh(new THREE.ConeGeometry(1.9 - k * 0.38, 2.6, 9), k % 2 ? hoja : hoja2); c.position.y = h * 0.35 + k * 1.5; c.castShadow = true; g.add(c); }
    g.position.set(x, 0, z); g.rotation.y = az() * 6; sc.add(g); arboles.push(g);
  }
  return { arboles };
}

/** Linterna en la mano de una persona (haz visible). Llama a lin.seguir() después de setTime. */
export function linterna(sc, p, alcance = 14) {
  const l = new THREE.SpotLight(0xfff1cf, 40, alcance, 0.32, 0.5, 1.3); const tg = new THREE.Object3D(); sc.add(tg); l.target = tg; sc.add(l);
  const haz = cono(sc, 0, 0, 0, alcance * 0.7, alcance * 0.18, 0xfff1cf, 0.05);
  const v = new THREE.Vector3(), d = new THREE.Vector3();
  return {
    seguir(baja = 0.25) {
      p.updateMatrixWorld(true); const mano = p.getObjectByName('Bip01_R_Hand') || p; mano.getWorldPosition(v);
      d.set(0, 0, 1).applyQuaternion(p.quaternion); d.y = -baja; d.normalize();
      l.position.copy(v); tg.position.copy(v).addScaledVector(d, 10);
      haz.position.copy(v); haz.lookAt(tg.position); haz.rotateX(-Math.PI / 2);
    },
  };
}

/** Brillo suave (sprite con degradado radial): fuego, faros, explosiones. */
export function brilloSprite(color = '#ffb060', tam = 4, op = 1) {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, color);
  gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  sp.scale.setScalar(tam); return sp;
}

/** Bola de fuego con estela (meteoro). b.poner(pos, dir, brillo): dir = hacia dónde viaja. */
export function bolaFuego(sc, largo = 16) {
  const g = new THREE.Group(); sc.add(g);
  const nucleo = brilloSprite('#fff2c0', 3.2), halo = brilloSprite('#ff8a2a', 9, 0.8); g.add(halo); g.add(nucleo);
  const cola = []; for (let i = 0; i < 26; i++) { const sp = brilloSprite(i < 8 ? '#ffc060' : i < 16 ? '#ff7a20' : '#a03010', 2.6 - i * 0.07, 0.75 - i * 0.025); sc.add(sp); cola.push(sp); }
  const luz = new THREE.PointLight(0xff9a40, 300, 80, 1.6); g.add(luz);
  return { g, luz, poner(pos, dir, brillo = 1) {
    g.position.copy(pos); const d = dir.clone().normalize();
    cola.forEach((sp, i) => { sp.position.copy(pos).addScaledVector(d, -(i + 1) * largo / cola.length); sp.position.x += Math.sin(i * 1.7) * 0.15; sp.visible = brillo > 0.01; });
    luz.intensity = 300 * brillo; halo.scale.setScalar(8 + Math.random() * 1.5); g.visible = brillo > 0.01; } };
}

/** Objeto en forma de bellota (Kecksburg 1965): metal cobrizo con un anillo de símbolos raros en la base. */
export function bellota(sc, x = 0, z = 0) {
  const g = new THREE.Group(), met = M.mat(0x8a5a2b, { metalness: 0.75, roughness: 0.38 });
  const cuerpo = new THREE.Mesh(new THREE.SphereGeometry(1.25, 32, 24, 0, Math.PI * 2, 0, Math.PI * 0.62), met); cuerpo.scale.set(1, 1.35, 1); cuerpo.position.y = 0.9; g.add(cuerpo);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(1.18, 1.0, 0.6, 32), M.mat(0x6e4520, { metalness: 0.8, roughness: 0.35 })); base.position.y = 0.55; g.add(base);
  const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 64; const c2 = cv.getContext('2d');
  c2.fillStyle = '#4a2c12'; c2.fillRect(0, 0, 1024, 64); c2.strokeStyle = '#e8c27a'; c2.lineWidth = 4;
  for (let i = 0; i < 26; i++) { const x0 = 14 + i * 39; c2.beginPath(); const k = (i * 7) % 5;
    if (k === 0) { c2.arc(x0 + 14, 32, 12, 0, Math.PI * 1.5); } else if (k === 1) { c2.moveTo(x0, 50); c2.lineTo(x0 + 14, 14); c2.lineTo(x0 + 28, 50); }
    else if (k === 2) { c2.moveTo(x0, 14); c2.lineTo(x0 + 28, 14); c2.moveTo(x0 + 14, 14); c2.lineTo(x0 + 14, 50); c2.arc(x0 + 14, 50, 4, 0, 6.3); }
    else if (k === 3) { c2.moveTo(x0, 32); c2.lineTo(x0 + 28, 32); c2.moveTo(x0 + 6, 16); c2.lineTo(x0 + 22, 48); }
    else { c2.rect(x0 + 4, 18, 20, 28); } c2.stroke(); }
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const anillo = new THREE.Mesh(new THREE.CylinderGeometry(1.21, 1.21, 0.42, 48, 1, true), new THREE.MeshStandardMaterial({ map: tx, metalness: 0.6, roughness: 0.4, emissive: 0xffffff, emissiveMap: tx, emissiveIntensity: 0.45 }));
  anillo.position.y = 0.55; g.add(anillo);
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  g.position.set(x, -0.25, z); g.rotation.z = 0.18; sc.add(g); return g;
}

/** Camión militar verde con la carga tapada por una lona (frente hacia +X). */
export function camionMilitar(sc, carga = true) {
  const g = new THREE.Group(), verde = M.mat(0x3b4a2a, { roughness: 0.8 }), lona = M.mat(0x4f5236, { roughness: 1 });
  const add = (w, h, d, x, y, z, m) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); b.position.set(x, y, z); b.castShadow = true; b.receiveShadow = true; g.add(b); return b; };
  add(7, 0.35, 2.3, 0, 1.0, 0, M.mat(0x1d1f18)); add(1.9, 1.6, 2.3, 2.6, 2.0, 0, verde); add(0.05, 0.6, 1.9, 3.56, 2.3, 0, M.mat(0x0b0d10, { metalness: 0.7, roughness: 0.1 }));
  add(4.6, 0.6, 2.4, -1.0, 1.45, 0, verde);
  if (carga) { const t = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 14), lona); t.scale.set(2.1, 1.0, 1.1); t.position.set(-1.0, 1.9, 0); t.castShadow = true; g.add(t);
    for (const x of [-2.6, -1.0, 0.6]) add(0.06, 0.06, 2.45, x, 2.2, 0, M.mat(0x2a2a1e)); }
  for (const [x, z] of [[2.6, 1.1], [2.6, -1.1], [-0.6, 1.1], [-0.6, -1.1], [-2.4, 1.1], [-2.4, -1.1]]) {
    const r = new THREE.Mesh(new THREE.CylinderGeometry(0.52, 0.52, 0.4, 18), M.mat(0x111111)); r.rotation.x = Math.PI / 2; r.position.set(x, 0.52, z); g.add(r); }
  for (const z of [0.85, -0.85]) { add(0.05, 0.25, 0.25, 3.56, 1.5, z, emis(0xfff4d0, 3));
    cono(g, 3.6, 1.5, z, 12, 2.2, 0xfff2d0, 0.05, [0, 0, Math.PI / 2 - 0.06]);
    const l = new THREE.SpotLight(0xfff0cc, 80, 35, 0.45, 0.5, 1.2); l.position.set(3.6, 1.5, z); const tg = new THREE.Object3D(); tg.position.set(15, 0, z); g.add(tg); l.target = tg; g.add(l); }
  add(0.05, 0.18, 0.3, -3.52, 1.3, 0.9, emis(0xff2a1a, 2)); add(0.05, 0.18, 0.3, -3.52, 1.3, -0.9, emis(0xff2a1a, 2));
  sc.add(g); return g;
}

/** Calle de Brooklyn de día (nublado): vereda, casas de ladrillo vecinas, terreno con EXCAVACIÓN a la derecha (x≈7..15).
 *  Devuelve {hueco: [x, z]}. El edificio que cae va con edificioQueCae() en x≈0. */
export function calleBrooklyn(sc, { hueco = true } = {}) {
  M.cielo(sc, '#9aa6b4', '#d9dde2'); sc.fog = new THREE.Fog(0xc9ced4, 40, 140);
  M.luces(sc, { sol: 1.6, cielo_: 1.4, dir: [-10, 18, 14], color: 0xf2f0ea });
  const con = M.TEX.concreto(), lad = M.TEX.ladrillo();
  M.caja(sc, 160, 0.2, 60, 0, -0.1, 10, M.matTex(con, [40, 15], 0x5c5c60));
  M.caja(sc, 160, 0.25, 4, 0, 0.02, 7, M.matTex(con, [40, 1], 0x9a968e));
  for (let x = -60; x < 60; x += 4) M.caja(sc, 2, 0.02, 0.15, x, 0.01, 13, M.mat(0xe8e0b0), false);
  for (const [x, w, h, c] of [[-9, 6, 9, 0xa7705a], [-15.5, 7, 12, 0x8a5d4a], [-22, 6, 9, 0xb08a70], [21, 8, 12, 0x93664f], [28, 6, 9, 0xa87a62]]) {
    M.caja(sc, w, h, 10, x, h / 2, -1, M.matTex(lad, [w / 2, h / 2], c));
    for (let p = 0; p < h / 3 - 0.5; p++) for (let k = 0; k < Math.floor(w / 1.8); k++)
      M.caja(sc, 0.9, 1.4, 0.1, x - w / 2 + 1.1 + k * 1.8, 1.8 + p * 3, 4.02, M.mat(0x1b2028, { roughness: 0.2, metalness: 0.4 }), false);
  }
  if (hueco) {                                   // terreno de al lado con un hueco excavado y tierra amontonada
    const tierra = M.matTex(M.TEX.arena(), [4, 4], 0x7a6248);
    M.caja(sc, 10, 0.25, 10, 12, -0.1, -1, M.mat(0x3a2e22));        // fondo oscuro del hueco (se ve hundido por las paredes)
    M.caja(sc, 10, 0.05, 10, 12, -3.0, -1, tierra);
    for (const [x, z, w, d] of [[7.05, -1, 0.1, 10], [16.95, -1, 0.1, 10], [12, -6, 10, 0.1]]) M.caja(sc, w, 3, d, x, -1.5, z, tierra);
    for (let i = 0; i < 6; i++) { const m = new THREE.Mesh(new THREE.ConeGeometry(1.2 + i * 0.2, 1.4, 8), tierra); m.position.set(13 + (i % 3) * 1.6, 0.6, -5 + Math.floor(i / 3) * 1.4); sc.add(m); }
    const valla = M.mat(0x2f6b3a); for (let x = 7.5; x < 17; x += 1.2) M.caja(sc, 1.1, 2, 0.05, x, 1, 4.2, valla);
  }
  return { hueco: [12, -1] };
}

/** Polvo (nube gris que crece). p.poner(t) con t = segundos desde el derrumbe. */
export function nubePolvo(sc, x, y, z, n = 40, tam = 6) {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(190,180,165,0.9)'); gr.addColorStop(1, 'rgba(190,180,165,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128); const tx = new THREE.CanvasTexture(c);
  const ps = []; let s = 9; const az = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  for (let i = 0; i < n; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, depthWrite: false, opacity: 0 }));
    sp.userData = { dx: (az() - 0.5) * 2, dy: az() * 0.8 + 0.2, dz: (az() - 0.2) * 1.6, r: 0.6 + az() }; sc.add(sp); ps.push(sp); }
  return { poner(t) { ps.forEach(sp => { const u = sp.userData, k = Math.max(0, t); sp.visible = t > 0;
    sp.position.set(x + u.dx * k * 2.2, y + u.dy * k * 2.5 + 0.5, z + u.dz * k * 2.2); sp.scale.setScalar(tam * u.r * (0.4 + k * 0.6));
    sp.material.opacity = Math.min(0.85, k * 2) * Math.max(0, 1 - k / 9); }); } };
}

/** Edificio de ladrillo de 3 pisos hecho de pedazos que se desploman hacia el lado del hueco (+X).
 *  e.poner(t): t = segundos desde que empieza a caer (negativo = de pie). */
export function edificioQueCae(sc, x0 = 0, z0 = -1, ancho = 7, alto = 9.6, fondo = 10) {
  const lad = M.TEX.ladrillo(), m1 = M.matTex(lad, [1, 1], 0xa9654a), vid = M.mat(0x1b2028, { roughness: 0.2, metalness: 0.4 }), los = M.mat(0x8f8a84);
  const piezas = []; let s = 5; const az = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  const pw = 1.4, ph = 1.6, nx = Math.round(ancho / pw), ny = Math.round(alto / ph);
  const add = (geo, mat, x, y, z) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; sc.add(m);
    m.userData = { p0: m.position.clone(), r: [az() - 0.5, az() - 0.5, az() - 0.5], d: 0 }; piezas.push(m); return m; };
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {         // fachada
    const x = x0 - ancho / 2 + pw / 2 + i * pw, y = ph / 2 + j * ph;
    const p = add(new THREE.BoxGeometry(pw, ph, 0.35), m1, x, y, z0 + fondo / 2);
    if (j % 2 === 1 && i % 2 === 0) { const v = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.0, 0.06), vid); v.position.set(0, 0, 0.19); p.add(v); }
  }
  for (const lado of [-1, 1]) for (let k = 0; k < Math.round(fondo / pw); k++) for (let j = 0; j < ny; j++)   // costados
    add(new THREE.BoxGeometry(0.35, ph, pw), m1, x0 + lado * ancho / 2, ph / 2 + j * ph, z0 - fondo / 2 + pw / 2 + k * pw);
  for (let j = 1; j <= 3; j++) for (let i = 0; i < 3; i++) add(new THREE.BoxGeometry(ancho / 3, 0.3, fondo), los, x0 - ancho / 3 + i * ancho / 3, j * 3.2, z0);   // losas
  const xm = x0 + ancho / 2;
  piezas.forEach(p => { const u = p.userData; u.d = (xm - u.p0.x) * 0.12 + (alto - u.p0.y) * 0.03 + az() * 0.35; u.v = 1.5 + az() * 2.5; u.fin = 0.4 + az() * 1.6; });
  return { piezas, poner(t) { piezas.forEach(p => { const u = p.userData, k = t - u.d;
    if (k <= 0) { p.position.copy(u.p0); p.rotation.set(0, 0, 0); return; }
    const y = Math.max(u.fin * (u.p0.y / alto) + 0.2, u.p0.y - 4.9 * k * k);
    p.position.set(u.p0.x + u.v * k * (1 + (u.p0.y / alto)), y, u.p0.z + u.r[2] * k * 1.5);
    const gir = Math.min(1, k * 0.8); p.rotation.set(u.r[0] * 2 * gir, u.r[1] * gir, -u.r[2] * 2.5 * gir - gir * 0.6); }); } };
}

/** Excavadora amarilla sencilla (cabina + brazo). ex.mover(k) baja y sube el brazo (k 0..1). */
export function excavadora(sc, x, z, giro = 0) {
  const g = new THREE.Group(), am = M.mat(0xe0a020, { roughness: 0.5 }), ne = M.mat(0x1a1a1a);
  const add = (w, h, d, x_, y_, z_, m, padre = g) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); b.position.set(x_, y_, z_); b.castShadow = true; padre.add(b); return b; };
  add(3.2, 0.7, 2.4, 0, 0.35, 0, ne); add(2.6, 1.0, 2.2, 0, 1.2, 0, am); add(1.1, 1.1, 1.0, 0.6, 2.2, 0.55, am);
  const brazo = new THREE.Group(); brazo.position.set(1.2, 1.6, -0.3); g.add(brazo);
  add(3.2, 0.4, 0.4, 1.6, 0, 0, am, brazo); const ant = new THREE.Group(); ant.position.set(3.2, 0, 0); brazo.add(ant);
  add(0.35, 2.4, 0.35, 0, -1.2, 0, am, ant); add(0.8, 0.6, 0.9, 0.2, -2.4, 0, ne, ant);
  g.position.set(x, 0, z); g.rotation.y = giro; sc.add(g);
  return { g, mover(k) { brazo.rotation.z = -0.5 + Math.sin(k * Math.PI * 2) * 0.35; ant.rotation.z = 0.3 + Math.cos(k * Math.PI * 2) * 0.3; } };
}

// ======================= 14-nov: selva y río, balsa, bote, sala de computadoras, posada con vela, celda, oficina =======================
function _azar(s0 = 11) { let s = s0; return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; }; }
function _texAgua(base = '#5b4a33', vetas = 'rgba(230,220,190,0.35)') {
  const c = document.createElement('canvas'); c.width = 256; c.height = 512; const g = c.getContext('2d');
  g.fillStyle = base; g.fillRect(0, 0, 256, 512); const az = _azar(5);
  for (let i = 0; i < 260; i++) { g.strokeStyle = vetas; g.lineWidth = 1 + az() * 2.5; g.beginPath(); const x = az() * 256, y = az() * 512, l = 20 + az() * 70;
    g.moveTo(x, y); g.bezierCurveTo(x + 6, y + l * 0.3, x - 6, y + l * 0.6, x + (az() - 0.5) * 10, y + l); g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t;
}
/** Árbol de selva (tronco alto + copas redondas). */
export function arbolSelva(sc, x, z, h = 12, az = Math.random) {
  const g = new THREE.Group(), tr = M.mat(0x4a3a2a, { roughness: 1 });
  const t = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.35, h, 7), tr); t.position.y = h / 2; t.castShadow = true; g.add(t);
  const verdes = [0x2f5a24, 0x3d6b2a, 0x264a1d, 0x4c7a32, 0x1f3d18];
  for (let k = 0; k < 5; k++) { const r = 1.6 + az() * 2.2, m = new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), M.mat(verdes[Math.floor(az() * 5)], { roughness: 1, flatShading: true }));
    m.position.set((az() - 0.5) * 3, h - 0.5 + (az() - 0.3) * 2.5, (az() - 0.5) * 3); m.scale.y = 0.7; m.castShadow = true; g.add(m); }
  g.position.set(x, 0, z); sc.add(g); return g;
}
/** Río en la selva (de día, nublado). El agua corre hacia +Z, el cauce va de x=-ancho/2 a ancho/2.
 *  caida = z donde termina el río en una cascada (null = sin cascada). Llama a rio.mover(t) cada cuadro. */
export function rioSelva(sc, { ancho = 14, caida = null, semilla = 3, rapidos = true, dia = 1 } = {}) {
  M.cielo(sc, '#8fa3a8', '#d4d8c8'); sc.fog = new THREE.Fog(0xb7bfae, 25, 110);
  M.luces(sc, { sol: 2.2 * dia, cielo_: 1.3 * dia, dir: [-12, 20, 8], color: 0xfff3dc });
  const az = _azar(semilla), largo = 200, zfin = caida ?? 100;
  const tex = _texAgua('#7d6d50', 'rgba(235,228,205,0.22)'); tex.repeat.set(3, 12);
  const agua = new THREE.Mesh(new THREE.PlaneGeometry(ancho + 6, largo), new THREE.MeshStandardMaterial({ map: tex, color: 0xd8c8a4, roughness: 0.15, metalness: 0.25 }));
  agua.rotation.x = -Math.PI / 2; agua.position.set(0, 0, zfin - largo / 2); agua.receiveShadow = true; sc.add(agua);
  const tierra = M.matTex(M.TEX.arena(), [20, 40], 0x5e5236);
  for (const lado of [-1, 1]) {
    M.caja(sc, 60, 1.2, caida != null ? largo + 1 : largo + 60, lado * (ancho / 2 + 30), 0.2, caida != null ? zfin - largo / 2 + 0.5 : zfin - largo / 2, tierra);
    const roca = M.matTex(M.TEX.roca(), [6, 2], 0x8a7a66);
    for (let z = zfin - 4; z > zfin - 140; z -= 6 + az() * 6) { const r = new THREE.Mesh(new THREE.DodecahedronGeometry(1.2 + az() * 1.8, 0), roca);
      r.position.set(lado * (ancho / 2 + 0.6 + az()), 0.3, z); r.rotation.set(az(), az(), az()); r.castShadow = true; sc.add(r); }
    for (let i = 0; i < 70; i++) { const z = zfin - (caida != null ? 2 : -8) - az() * 150, x = lado * (ancho / 2 + 2.5 + az() * 22); arbolSelva(sc, x, z, 9 + az() * 10, az); }
    for (let i = 0; i < 60; i++) { const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.8 + az() * 1.2, 0), M.mat(az() < 0.5 ? 0x3a6a28 : 0x2c5220, { flatShading: true }));
      m.position.set(lado * (ancho / 2 + 1.2 + az() * 4), 0.7, zfin - (caida != null ? 1.5 : -6) - az() * 140); m.scale.y = 0.6; sc.add(m); }
  }
  const espuma = [], rocas = [];
  const mEsp = new THREE.MeshBasicMaterial({ color: 0xf2efe6, transparent: true, opacity: 0.6, depthWrite: false });
  if (rapidos) for (let i = 0; i < 26; i++) {
    const x = (az() - 0.5) * (ancho - 2), z = zfin - 3 - az() * 40;
    const r = new THREE.Mesh(new THREE.DodecahedronGeometry(0.4 + az() * 0.7, 0), M.matTex(M.TEX.roca(), [1, 1], 0x6a6258)); r.position.set(x, 0.05, z); r.castShadow = true; sc.add(r); rocas.push(r);
    for (let k = 0; k < 3; k++) { const e = new THREE.Mesh(new THREE.CircleGeometry(0.5 + az() * 0.8, 10), mEsp); e.rotation.x = -Math.PI / 2; e.position.set(x + (az() - 0.5) * 1.5, 0.03 + k * 0.002, z + 0.8 + k * 0.7); sc.add(e); espuma.push(e); }
  }
  let cascada = null, bruma = [];
  if (caida != null) {                      // cascada: el agua cae 8 m después de zfin a una poza
    const tc = _texAgua('#b9c2bf', 'rgba(255,255,255,0.75)'); tc.repeat.set(4, 2);
    cascada = new THREE.Mesh(new THREE.PlaneGeometry(ancho + 6, 9), new THREE.MeshStandardMaterial({ map: tc, color: 0xffffff, roughness: 0.3, transparent: true, opacity: 0.8 }));
    cascada.position.set(0, -4.4, zfin + 0.6); cascada.rotation.x = -0.12; sc.add(cascada);
    M.caja(sc, 220, 0.5, 90, 0, -9.3, zfin + 46, tierra);
    for (let i = 0; i < 40; i++) { const lado = az() < 0.5 ? -1 : 1; arbolSelva(sc, lado * (ancho / 2 + 6 + az() * 30), zfin + 6 + az() * 40, 9 + az() * 8, az).position.y = -9; }
    const poza = new THREE.Mesh(new THREE.PlaneGeometry(ancho + 8, 60), new THREE.MeshStandardMaterial({ map: tex, color: 0x7f735a, roughness: 0.3 }));
    poza.rotation.x = -Math.PI / 2; poza.position.set(0, -8.8, zfin + 20); sc.add(poza);
    M.caja(sc, 60, 9, 2, -(ancho / 2 + 30), -4.4, zfin + 1, M.matTex(M.TEX.roca(), [10, 2], 0x6e665c));
    M.caja(sc, 60, 9, 2, (ancho / 2 + 30), -4.4, zfin + 1, M.matTex(M.TEX.roca(), [10, 2], 0x6e665c));
    for (let i = 0; i < 30; i++) { const b = brilloSprite('#e8eee8', 4 + az() * 4, 0.1); b.material.blending = THREE.NormalBlending; b.position.set((az() - 0.5) * ancho, -7 + az() * 3, zfin + 1.5 + az() * 3); sc.add(b); bruma.push(b); }
  }
  return { agua, tex, espuma, cascada, bruma, zfin, mover(t, vel = 1) {
    tex.offset.y = -t * 0.35 * vel; if (cascada) cascada.material.map.offset.y = t * 1.6;
    espuma.forEach((e, i) => { e.material.opacity = 0.45 + 0.25 * Math.sin(t * 6 + i); e.scale.setScalar(1 + 0.15 * Math.sin(t * 5 + i * 2)); });
    bruma.forEach((b, i) => { b.position.y += Math.sin(t * 2 + i) * 0.01; }); } };
}
/** Balsa de troncos (frente hacia +Z). */
export function balsa(sc) {
  const g = new THREE.Group(), m = M.mat(0x6b5133, { roughness: 1 }), soga = M.mat(0xb59a6a);
  for (let i = 0; i < 7; i++) { const l = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 3.4, 10), m); l.rotation.x = Math.PI / 2; l.position.set(-0.78 + i * 0.26, 0.12, 0); l.castShadow = true; l.receiveShadow = true; g.add(l); }
  for (const z of [-1.2, 0, 1.2]) { const s = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.06, 0.08), soga); s.position.set(0, 0.25, z); g.add(s); }
  const mo = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.35, 0.4), M.mat(0x5a6a3a)); mo.position.set(0.4, 0.42, -1.1); mo.castShadow = true; g.add(mo);
  sc.add(g); return g;
}
/** Bote de madera con motor fuera de borda (frente hacia +X). */
export function bote(sc, color = 0x7a5a3a) {
  const g = new THREE.Group(), m = M.mat(color, { roughness: 0.8 });
  const add = (w, h, d, x, y, z, mm = m) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; g.add(b); return b; };
  add(5, 0.12, 1.4, 0, 0.1, 0); add(5, 0.6, 0.1, 0, 0.4, 0.7); add(5, 0.6, 0.1, 0, 0.4, -0.7); add(0.1, 0.6, 1.4, -2.5, 0.4, 0);
  const proa = new THREE.Mesh(new THREE.ConeGeometry(0.75, 1.4, 4), m); proa.rotation.z = -Math.PI / 2; proa.rotation.x = Math.PI / 4; proa.position.set(3.1, 0.4, 0); g.add(proa);
  add(0.4, 0.6, 0.35, -2.75, 0.75, 0, M.mat(0x222222)); add(0.12, 0.8, 0.12, -2.8, 0.1, 0, M.mat(0x333333));
  sc.add(g); return g;
}
/** Sala de computadoras de universidad de noche (filas de escritorios con monitores). sala.pantallas(k): 0..1 cuántas se encienden. */
export function salaComputadoras(sc, filas = 4, cols = 6) {
  sc.background = new THREE.Color(0x05070b); sc.add(new THREE.HemisphereLight(0x3a4a66, 0x0a0a0c, 0.35));
  const piso = M.matTex(M.TEX.concreto(), [6, 6], 0x3d3a40), pared = M.matTex(M.TEX.concreto(), [4, 1], 0x5a5a62);
  M.caja(sc, 20, 0.1, 20, 0, -0.05, 0, piso); M.caja(sc, 20, 4, 0.2, 0, 2, -7, pared); M.caja(sc, 0.2, 4, 20, -8, 2, 0, pared);
  for (let i = 0; i < 4; i++) M.caja(sc, 0.06, 1.4, 1.8, -7.9, 2.0, -4 + i * 3, emis(0x1d2c4a, 0.5), false);
  const madera = M.mat(0x6a5a48), pantallas = [], az = _azar(17);
  for (let f = 0; f < filas; f++) for (let c = 0; c < cols; c++) {
    const x = -5 + c * 2.0, z = -5 + f * 2.4;
    M.caja(sc, 1.6, 0.05, 0.8, x, 0.75, z, madera); M.caja(sc, 0.05, 0.75, 0.7, x - 0.75, 0.375, z, madera); M.caja(sc, 0.05, 0.75, 0.7, x + 0.75, 0.375, z, madera);
    M.caja(sc, 0.5, 0.42, 0.42, x, 1.0, z - 0.15, M.mat(0xcfc8b6, { roughness: 0.5 }));
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.31), new THREE.MeshBasicMaterial({ color: 0x0b0f0b })); scr.position.set(x, 1.0, z + 0.065); sc.add(scr);
    const l = new THREE.PointLight(0x4cff88, 0, 2.2, 1.6); l.position.set(x, 1.05, z + 0.4); sc.add(l);
    M.caja(sc, 0.45, 0.03, 0.16, x, 0.79, z + 0.25, M.mat(0xd8d2c0));
    pantallas.push({ scr, l, orden: az() });
  }
  pantallas.sort((a, b) => a.orden - b.orden);
  return { pantallas(k, t = 0, color = 0x3cff7a) { pantallas.forEach((p, i) => { const on = i / pantallas.length < k;
    const parp = on ? 0.75 + 0.25 * Math.sin(t * 20 + i * 3) : 0; p.scr.material.color.setHex(on ? color : 0x0b0f0b); p.scr.material.color.multiplyScalar(on ? parp : 1);
    p.l.color.setHex(color); p.l.intensity = on ? 1.4 * parp : 0; }); } };
}
/** Caja de hierro con tapa que se abre (tapa.rotation.x). Devuelve {g, abrir(k)}. */
export function cajaHierro(sc, x = 0, y = 0, z = 0, tam = 0.5) {
  const g = new THREE.Group(), hi = M.mat(0x3a3530, { metalness: 0.7, roughness: 0.55 }), rem = M.mat(0x6a5a40, { metalness: 0.8, roughness: 0.4 });
  const cu = new THREE.Mesh(new THREE.BoxGeometry(tam * 1.4, tam * 0.7, tam), hi); cu.position.y = tam * 0.35; cu.castShadow = true; g.add(cu);
  for (const xx of [-0.5, 0.5]) { const b = new THREE.Mesh(new THREE.BoxGeometry(tam * 0.08, tam * 0.72, tam * 1.02), rem); b.position.set(xx * tam, tam * 0.35, 0); g.add(b); }
  const piv = new THREE.Group(); piv.position.set(0, tam * 0.7, -tam / 2); g.add(piv);
  const tapa = new THREE.Mesh(new THREE.BoxGeometry(tam * 1.42, tam * 0.12, tam * 1.02), hi); tapa.position.set(0, tam * 0.06, tam / 2); tapa.castShadow = true; piv.add(tapa);
  const cand = new THREE.Mesh(new THREE.BoxGeometry(tam * 0.18, tam * 0.2, tam * 0.05), rem); cand.position.set(0, tam * 0.55, tam * 0.52); g.add(cand);
  g.position.set(x, y, z); sc.add(g); return { g, abrir(k) { piv.rotation.x = -ease(k) * 1.9; } };
}
/** Hoja de papel viejo llena de números (como los papeles de Beale). */
export function hojaNumeros(sc, x, y, z, semilla = 1, ancho = 0.42) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 660; const g = c.getContext('2d');
  g.fillStyle = '#d9c9a0'; g.fillRect(0, 0, 512, 660); const az = _azar(semilla * 7 + 3);
  for (let i = 0; i < 400; i++) { g.fillStyle = `rgba(120,90,40,${az() * 0.08})`; g.beginPath(); g.arc(az() * 512, az() * 660, 4 + az() * 30, 0, 6.3); g.fill(); }
  g.fillStyle = '#2a1e12'; g.font = 'italic 25px Georgia, serif';
  for (let l = 0; l < 20; l++) { let s = ''; for (let k = 0; k < 9; k++) s += Math.floor(1 + az() * 980) + ', '; g.fillText(s, 22, 50 + l * 30); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(ancho, ancho * 1.29), new THREE.MeshStandardMaterial({ map: t, roughness: 0.95 }));
  m.rotation.x = -Math.PI / 2; m.position.set(x, y, z); m.receiveShadow = true; sc.add(m); return m;
}
/** Cuarto de posada antigua de noche, iluminado por una vela sobre la mesa (mesa en 0,0; cara de lectura hacia +Z). vela.mover(t) titila. */
export function posadaVela(sc) {
  sc.background = new THREE.Color(0x070504); sc.add(new THREE.HemisphereLight(0x5a4630, 0x0c0806, 0.25));
  const tabla = M.mat(0x5a3e26, { roughness: 0.9 }), pared = M.matTex(M.TEX.concreto(), [3, 2], 0x7a6a56);
  M.caja(sc, 10, 0.1, 10, 0, -0.05, 0, M.matTex(M.TEX.arena(), [4, 4], 0x5a4632)); M.caja(sc, 10, 3.2, 0.2, 0, 1.6, -2.6, pared); M.caja(sc, 0.2, 3.2, 10, -3.2, 1.6, 0, pared);
  for (let i = 0; i < 6; i++) M.caja(sc, 10, 0.18, 0.18, 0, 3.0, -2.4 + i * 1.2, tabla);
  M.caja(sc, 1.8, 0.08, 1.0, 0, 0.78, 0, tabla); for (const [x, z] of [[-0.8, -0.42], [0.8, -0.42], [-0.8, 0.42], [0.8, 0.42]]) M.caja(sc, 0.08, 0.78, 0.08, x, 0.39, z, tabla);
  M.caja(sc, 0.6, 1.8, 0.4, -2.6, 0.9, -2.2, tabla); M.caja(sc, 0.8, 0.05, 0.3, -2.0, 1.6, -2.45, tabla);
  const vela = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.22, 12), M.mat(0xefe6cf)); vela.position.set(-0.55, 0.93, -0.2); sc.add(vela);
  const llama = brilloSprite('#ffb04a', 0.18); llama.position.set(-0.55, 1.08, -0.2); sc.add(llama);
  const halo = brilloSprite('#ff9a30', 1.4, 0.35); halo.position.copy(llama.position); sc.add(halo);
  const luz = new THREE.PointLight(0xffa34a, 6, 7, 1.6); luz.position.set(-0.55, 1.15, -0.2); luz.castShadow = true; luz.shadow.mapSize.set(1024, 1024); sc.add(luz);
  return { mover(t) { const f = 0.85 + 0.1 * Math.sin(t * 13) + 0.05 * Math.sin(t * 31); luz.intensity = 6 * f; llama.scale.set(0.12, 0.2 * f, 1); } };
}
/** Celda de prisión pequeña: catre, inodoro, foco arriba y puerta de barrotes en z=+1.6 (el preso adentro, mirando a +Z). */
export function celda(sc) {
  sc.background = new THREE.Color(0x050506); sc.add(new THREE.HemisphereLight(0xc8d0d8, 0x101010, 0.3));
  const con = M.matTex(M.TEX.concreto(), [2, 1], 0x8c8a86);
  M.caja(sc, 8, 0.1, 8, 0, -0.05, 0, M.matTex(M.TEX.concreto(), [3, 3], 0x5f5d5a));
  M.caja(sc, 0.2, 3, 3.4, -1.3, 1.5, 0, con); M.caja(sc, 0.2, 3, 3.4, 1.3, 1.5, 0, con); M.caja(sc, 2.8, 3, 0.2, 0, 1.5, -1.6, con); M.caja(sc, 2.8, 0.2, 3.4, 0, 3, 0, con);
  M.caja(sc, 0.8, 0.12, 2.0, -0.8, 0.45, -0.4, M.mat(0x6a6a6a, { metalness: 0.5 })); M.caja(sc, 0.75, 0.12, 1.9, -0.8, 0.56, -0.4, M.mat(0x8a8f96));
  M.caja(sc, 0.4, 0.45, 0.5, 0.95, 0.22, -1.2, M.mat(0xb8b8b8, { metalness: 0.7, roughness: 0.3 }));
  const barra = M.mat(0x4f4f4f, { metalness: 0.7, roughness: 0.4 });
  for (let x = -1.15; x <= 1.16; x += 0.16) M.caja(sc, 0.04, 3, 0.04, x, 1.5, 1.6, barra, false);
  M.caja(sc, 2.6, 0.08, 0.08, 0, 1.0, 1.6, barra, false); M.caja(sc, 2.6, 0.08, 0.08, 0, 2.2, 1.6, barra, false);
  M.caja(sc, 0.3, 0.05, 0.3, 0, 2.93, 0, emis(0xf4f0e0, 2), false);
  const l = new THREE.SpotLight(0xf0ecdc, 18, 6, 0.9, 0.6, 1.4); l.position.set(0, 2.9, 0); const tg = new THREE.Object3D(); tg.position.set(0, 0, 0); sc.add(tg); l.target = tg; l.castShadow = true; sc.add(l);
  M.caja(sc, 8, 3, 0.2, 0, 1.5, 4.5, M.matTex(M.TEX.concreto(), [3, 1], 0x4a4846));
}
/** Oficina de empresa de los 80 (luz de tubo, escritorios con teléfonos). El escritorio principal está en (0, 0) mirando a +Z. */
export function oficina(sc) {
  sc.background = new THREE.Color(0x15171a); sc.add(new THREE.HemisphereLight(0xe8f0ff, 0x30302c, 0.7));
  M.caja(sc, 16, 0.1, 16, 0, -0.05, 0, M.matTex(M.TEX.arena(), [6, 6], 0x6a6a5e)); M.caja(sc, 16, 3, 0.2, 0, 1.5, -3, M.matTex(M.TEX.concreto(), [4, 1], 0xb8b2a2));
  M.caja(sc, 0.2, 3, 16, -5, 1.5, 0, M.matTex(M.TEX.concreto(), [4, 1], 0xb8b2a2));
  for (const [x, z] of [[-2, -1.5], [1.5, 2.5], [0, 5], [3.5, 0]]) { M.caja(sc, 2.0, 1.4, 0.06, x, 0.7, z - 0.8, M.mat(0x5a6e7a)); }
  for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) { M.caja(sc, 1.6, 0.06, 0.2, -2 + i * 3, 2.95, -1 + j * 3, emis(0xf6faff, 2.2), false);
    const l = new THREE.PointLight(0xeef4ff, 5, 7, 1.5); l.position.set(-2 + i * 3, 2.7, -1 + j * 3); sc.add(l); }
  const esc = (x, z) => { M.caja(sc, 1.6, 0.05, 0.8, x, 0.75, z, M.mat(0x8a7a62)); M.caja(sc, 1.6, 0.7, 0.05, x, 0.37, z - 0.38, M.mat(0x6a5e4c));
    M.caja(sc, 0.22, 0.08, 0.18, x + 0.5, 0.82, z, M.mat(0x1d1d1d)); M.caja(sc, 0.06, 0.05, 0.2, x + 0.5, 0.89, z, M.mat(0x1d1d1d));
    for (let k = 0; k < 3; k++) M.caja(sc, 0.3, 0.01, 0.22, x - 0.3 + k * 0.02, 0.79 + k * 0.012, z + 0.05, M.mat(0xece6d6), false); };
  esc(0, 0); esc(-2, -1.5); esc(3.5, 0); esc(1.5, 2.5);
}
/** Teléfono en la mano derecha (auricular). Llama a tel.seguir() después de setTime. */
export function telefonoMano(sc, p, color = 0x1d1d1d) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.2, 0.06), M.mat(color, { roughness: 0.5 })); sc.add(m);
  const v = new THREE.Vector3(), q = new THREE.Quaternion();
  return { seguir() { p.updateMatrixWorld(true); const mano = p.getObjectByName('Bip01_R_Hand') || p; mano.getWorldPosition(v); mano.getWorldQuaternion(q); m.position.copy(v); m.quaternion.copy(q); } };
}

// ===================== 15-nov: mar de noche, remolcador, cabina hundida, desierto, luces en V, máquina de refrescos =====================
/** Mar abierto de noche con olas que se mueven (tormenta opcional: lluvia + relámpagos). mar.mover(t); mar.relampago(k 0..1). */
export function marNoche(sc, { tormenta = true, olas = 1 } = {}) {
  M.cielo(sc, '#03060c', '#162130'); sc.fog = new THREE.FogExp2(0x0a1220, 0.022);
  const hemi = new THREE.HemisphereLight(0x7a90b8, 0x0a0c12, 0.9); sc.add(hemi);
  const luna = new THREE.DirectionalLight(0x9db4ff, 0.9); luna.position.set(-20, 30, 10); sc.add(luna);
  const geo = new THREE.PlaneGeometry(240, 240, 120, 120); geo.rotateX(-Math.PI / 2);
  const base = geo.attributes.position.array.slice();
  const agua = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0x0d2233, roughness: 0.25, metalness: 0.45, flatShading: true })); sc.add(agua);
  const flash = new THREE.DirectionalLight(0xdfe8ff, 0); flash.position.set(15, 40, -30); sc.add(flash);
  let lluvia = null;
  if (tormenta) { const n = 2500, p = new Float32Array(n * 3); for (let i = 0; i < n; i++) { p[i * 3] = (Math.random() - 0.5) * 60; p[i * 3 + 1] = Math.random() * 30; p[i * 3 + 2] = (Math.random() - 0.5) * 60; }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    lluvia = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xaab8d0, size: 0.06, transparent: true, opacity: 0.55 })); sc.add(lluvia); }
  const alto = (x, z, t) => olas * (0.55 * Math.sin(x * 0.18 + t * 1.3) + 0.35 * Math.sin(z * 0.23 - t * 1.1) + 0.18 * Math.sin((x + z) * 0.5 + t * 2.2));
  return { agua, alto, flash, mover(t) {
      const a = geo.attributes.position.array;
      for (let i = 0; i < a.length; i += 3) a[i + 1] = alto(base[i], base[i + 2], t);
      geo.attributes.position.needsUpdate = true; geo.computeVertexNormals();
      if (lluvia) { const q = lluvia.geometry.attributes.position.array; for (let i = 1; i < q.length; i += 3) { q[i] -= 0.9; if (q[i] < 0) q[i] += 30; } lluvia.geometry.attributes.position.needsUpdate = true; }
    },
    relampago(k) { flash.intensity = 7 * k; hemi.intensity = 0.9 + 2.2 * k; } };
}
/** Remolcador de altamar (casco rojo y negro, puente blanco con ventanas encendidas, mástil con luces). Frente hacia +X, largo ~14 m. */
export function remolcador(sc) {
  const g = new THREE.Group(); const add = (w, h, d, x, y, z, mm) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; g.add(b); return b; };
  const rojo = M.mat(0x8a1e18, { roughness: 0.6 }), negro = M.mat(0x16181b, { roughness: 0.5 }), blanco = M.mat(0xd9d6cc, { roughness: 0.6 });
  add(13, 1.6, 4.6, 0, -0.4, 0, rojo); add(13.2, 1.3, 4.8, 0, 1.0, 0, negro);
  const proa = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.3, 2.9, 3, 1, false), negro); proa.rotation.y = Math.PI / 6; proa.scale.set(1.2, 1, 1); proa.position.set(6.7, 0.3, 0); g.add(proa);
  add(13, 0.15, 4.6, 0, 1.72, 0, M.mat(0x4d4a44));
  add(5, 2.2, 3.6, 1.8, 2.9, 0, blanco); add(3.4, 1.6, 3.2, 2.4, 4.8, 0, blanco); add(3.6, 0.15, 3.4, 2.4, 5.65, 0, M.mat(0x3a3a3a));
  for (let i = 0; i < 4; i++) { add(0.05, 0.6, 0.55, 4.12, 4.9, -1.2 + i * 0.8, emis(0xffd18a, 1.2)); add(0.55, 0.6, 0.05, 1.2 + i * 0.8, 4.9, 1.62, emis(0xffd18a, 1.0)); }
  for (let i = 0; i < 5; i++) add(0.5, 0.5, 0.05, -0.2 + i * 0.9, 2.9, 1.82, emis(0xffc070, 0.7));
  add(0.2, 4, 0.2, 2.4, 7.6, 0, M.mat(0x2a2a2a)); add(1.4, 0.12, 0.12, 2.4, 8.4, 0, M.mat(0x2a2a2a));
  add(0.9, 1.4, 0.9, 0.2, 4.2, 0, M.mat(0xc8b820));
  add(0.15, 0.15, 0.15, 2.4, 9.6, 0, emis(0xffffff, 4)); add(0.15, 0.15, 0.15, 3.1, 8.4, 0.1, emis(0xff2020, 3)); add(0.15, 0.15, 0.15, 1.7, 8.4, -0.1, emis(0x20ff40, 3));
  for (let i = 0; i < 6; i++) { const r = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.16, 8, 14), M.mat(0x111111)); r.position.set(-5 + i * 2, 0.9, 2.45); g.add(r); }
  add(3, 0.8, 0.5, -4.5, 2.1, 0, M.mat(0x6b4a2a));
  const l = new THREE.PointLight(0xffc880, 25, 14, 1.6); l.position.set(2, 4, 2.5); g.add(l);
  const l2 = new THREE.PointLight(0xffe0b0, 30, 18, 1.6); l2.position.set(-3, 3.5, 0); g.add(l2);
  sc.add(g); return g;
}
/** Cabina de barco hundido y volteado (al revés: la cama y la mesa quedan en el techo). Agua oscura hasta y=agua.
 *  Persona de pie en (0, 0) con la cabeza afuera del agua. cab.mover(t) mueve la superficie; cab.buzo(k) prende una linterna que entra por la puerta (x=-2). */
export function cabinaHundida(sc, { nivel = 1.45 } = {}) {
  sc.background = new THREE.Color(0x010204); sc.fog = new THREE.FogExp2(0x02060a, 0.12);
  sc.add(new THREE.HemisphereLight(0x3a5a70, 0x05080a, 0.25));
  const pared = M.matTex(M.TEX.concreto(), [2, 1], 0x5c6a6a), metal = M.mat(0x3d4442, { roughness: 0.7, metalness: 0.4 });
  M.caja(sc, 5, 0.1, 5, 0, -0.05, 0, metal); M.caja(sc, 5, 0.1, 5, 0, 2.55, 0, pared);
  M.caja(sc, 0.1, 2.6, 5, -2.5, 1.25, 0, pared); M.caja(sc, 0.1, 2.6, 5, 2.5, 1.25, 0, pared); M.caja(sc, 5, 2.6, 0.1, 0, 1.25, -2.5, pared); M.caja(sc, 5, 2.6, 0.1, 0, 1.25, 2.5, pared);
  // muebles al revés colgando del "techo" (que antes era el piso)
  M.caja(sc, 1.9, 0.35, 0.9, 1.3, 2.3, -1.9, M.mat(0x5a4a3a)); M.caja(sc, 1.8, 0.18, 0.85, 1.3, 2.05, -1.9, M.mat(0x8a8e88));
  M.caja(sc, 1.0, 0.05, 0.7, -1.4, 1.85, -1.6, M.mat(0x4a3424)); for (const [x, z] of [[-1.85, -1.9], [-0.95, -1.9], [-1.85, -1.3], [-0.95, -1.3]]) M.caja(sc, 0.05, 0.65, 0.05, x, 2.2, z, M.mat(0x4a3424));
  M.caja(sc, 0.1, 1.9, 0.9, -2.44, 1.3, 1.2, M.mat(0x2a3030)); // puerta
  const tex = _texAgua('#06202a', 'rgba(140,200,210,0.25)'); tex.repeat.set(2, 2);
  const sup = new THREE.Mesh(new THREE.PlaneGeometry(5, 5), new THREE.MeshStandardMaterial({ map: tex, color: 0x5a9aa8, roughness: 0.1, metalness: 0.3, transparent: true, opacity: 0.82 }));
  sup.rotation.x = -Math.PI / 2; sup.position.y = nivel; sc.add(sup);
  const vol = new THREE.Mesh(new THREE.BoxGeometry(4.9, nivel, 4.9), new THREE.MeshBasicMaterial({ color: 0x041a22, transparent: true, opacity: 0.9, depthWrite: false })); vol.position.y = nivel / 2; sc.add(vol);
  const tenue = new THREE.PointLight(0x6aa8c8, 7, 6, 1.4); tenue.position.set(0.7, 2.3, 1.4); sc.add(tenue);
  const lin = new THREE.SpotLight(0xe8fbff, 0, 9, 0.35, 0.5, 1.2); lin.position.set(-2.4, 1.0, 1.2); const tg = new THREE.Object3D(); tg.position.set(0, 1.2, 0); sc.add(tg); lin.target = tg; sc.add(lin);
  const haz = cono(sc, -2.4, 1.0, 1.2, 3.2, 0.7, 0xcff4ff, 0); haz.lookAt(0, 1.2, 0); haz.rotateX(-Math.PI / 2);
  const burb = []; for (let i = 0; i < 25; i++) { const b = new THREE.Mesh(new THREE.SphereGeometry(0.02 + Math.random() * 0.03, 6, 6), new THREE.MeshBasicMaterial({ color: 0x9fd8e8, transparent: true, opacity: 0.6 })); b.userData.o = [(Math.random() - 0.5) * 4, Math.random() * nivel, (Math.random() - 0.5) * 4, 0.2 + Math.random() * 0.4]; sc.add(b); burb.push(b); }
  return { sup, lin, tg, mover(t) { tex.offset.set(Math.sin(t * 0.7) * 0.05, t * 0.02); sup.position.y = nivel + Math.sin(t * 1.3) * 0.02;
      burb.forEach(b => { const [x, y, z, v] = b.userData.o; b.position.set(x, (y + t * v) % nivel, z); }); },
    buzo(k) { lin.intensity = 60 * k; haz.material.opacity = 0.055 * k; } };
}
/** Desierto de Arizona de noche: arena, cerros oscuros, saguaros, carretera y casas con luces; resplandor de ciudad al fondo (-Z). */
export function desiertoNoche(sc, { semilla = 4, ciudad = true } = {}) {
  M.cielo(sc, '#04060f', '#1d2238'); sc.fog = new THREE.FogExp2(0x0c1020, 0.012);
  sc.add(new THREE.HemisphereLight(0x5f6f9a, 0x1a140e, 0.6));
  const luna = new THREE.DirectionalLight(0x9aaeff, 0.9); luna.position.set(-15, 25, 12); luna.castShadow = true; luna.shadow.mapSize.set(2048, 2048);
  Object.assign(luna.shadow.camera, { left: -25, right: 25, top: 25, bottom: -25 }); sc.add(luna);
  M.caja(sc, 400, 0.2, 400, 0, -0.1, 0, M.matTex(M.TEX.arena(), [60, 60], 0x6e6050));
  M.caja(sc, 400, 0.02, 6, 0, 0.01, 6, M.mat(0x26262a)); for (let x = -100; x < 100; x += 5) M.caja(sc, 2, 0.02, 0.15, x, 0.03, 6, emis(0xd8c070, 0.2), false);
  const az = _azar(semilla), cerro = M.mat(0x141620, { roughness: 1, flatShading: true });
  for (let i = 0; i < 18; i++) { const c = new THREE.Mesh(new THREE.ConeGeometry(14 + az() * 22, 8 + az() * 14, 6), cerro); c.position.set(-160 + i * 19 + az() * 8, 3, -110 - az() * 40); sc.add(c); }
  const verde = M.mat(0x2a3a26, { roughness: 1 });
  const saguaro = (x, z, h) => { const s = new THREE.Group(); const t = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.26, h, 8), verde); t.position.y = h / 2; t.castShadow = true; s.add(t);
    for (const l of [-1, 1]) { const b = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, h * 0.35, 8), verde); b.position.set(l * 0.55, h * 0.55, 0); s.add(b);
      const c = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.6, 8), verde); c.rotation.z = Math.PI / 2; c.position.set(l * 0.33, h * 0.4, 0); s.add(c); }
    s.position.set(x, 0, z); s.rotation.y = az() * 6; sc.add(s); };
  for (let i = 0; i < 40; i++) { const x = (az() - 0.5) * 120, z = -4 - az() * 70; if (Math.abs(x) < 4 && z > -12) continue; saguaro(x, z, 3 + az() * 3); }
  for (let i = 0; i < 70; i++) { const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.3 + az() * 0.5, 0), M.mat(0x3a3a28, { flatShading: true })); m.position.set((az() - 0.5) * 100, 0.15, 12 - az() * 80); m.scale.y = 0.5; sc.add(m); }
  if (ciudad) { for (let i = 0; i < 260; i++) { const c = [0xffc070, 0xffe0a0, 0xfff2d0][i % 3]; M.caja(sc, 0.5, 0.3, 0.1, -120 + az() * 240, 0.3 + az() * 1.5, -85 - az() * 15, emis(c, 1.5), false); }
    const r = brilloSprite('#ff9a40', 1, 0.25); r.scale.set(260, 40, 1); r.position.set(0, 2, -100); sc.add(r); }
  return { saguaro };
}
/** Formación de luces en forma de V (5 luces ámbar) con una silueta oscura casi invisible. Abre hacia +X (punta hacia -X por defecto). v.g = grupo. */
export function lucesV(sc, { n = 5, ancho = 40, silueta = true } = {}) {
  const g = new THREE.Group(); const lz = [];
  const pos = []; const m = Math.floor(n / 2);
  for (let i = 0; i < n; i++) { const k = i - m; pos.push([Math.abs(k) * ancho / n, 0, k * ancho / n]); }
  for (const [x, y, z] of pos) { const s = brilloSprite('#ffb050', 5.5, 1); s.position.set(x, y, z); g.add(s); lz.push(s);
    const c = brilloSprite('#fff4d8', 1.6, 1); c.position.set(x, y, z); g.add(c); }
  if (silueta) { const sh = new THREE.Shape(); const a = pos[0], b = pos[m], c = pos[n - 1];
    sh.moveTo(b[0] - 3, b[2]); sh.lineTo(a[0] + 3, a[2] - 3); sh.lineTo(a[0] - 3, a[2] + 4); sh.lineTo(b[0] + 6, b[2]); sh.lineTo(c[0] - 3, c[2] - 4); sh.lineTo(c[0] + 3, c[2] + 3); sh.lineTo(b[0] - 3, b[2]);
    const mm = new THREE.Mesh(new THREE.ShapeGeometry(sh), new THREE.MeshBasicMaterial({ color: 0x07080c, transparent: true, opacity: 0.55, side: THREE.DoubleSide, depthWrite: false }));
    mm.rotation.x = Math.PI / 2; mm.position.y = 0.4; g.add(mm); }
  const luz = new THREE.PointLight(0xffb060, 0, 200, 1.2); g.add(luz);
  sc.add(g); return { g, lz, luz, pulso(t) { lz.forEach((s, i) => s.scale.setScalar(5.5 + Math.sin(t * 3 + i) * 0.5)); } };
}
/** Máquina de refrescos vieja (roja, años 70) con 6 botones amarillos "?" y ranura de latas. Frente hacia +Z, base en (x,0,z).
 *  maq.lata(k): una lata cae por la ranura (0..1). maq.luz(on). */
export function maquinaRefrescos(sc, x = 0, z = 0, giro = 0) {
  const g = new THREE.Group();
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 512; const c = cv.getContext('2d');
  c.fillStyle = '#b3161a'; c.fillRect(0, 0, 256, 512);
  const gr = c.createLinearGradient(0, 0, 256, 0); gr.addColorStop(0, 'rgba(0,0,0,0.25)'); gr.addColorStop(0.5, 'rgba(255,255,255,0.08)'); gr.addColorStop(1, 'rgba(0,0,0,0.3)');
  c.fillStyle = '#e8e2d4'; c.fillRect(14, 40, 228, 150); c.fillStyle = '#b3161a'; c.fillRect(22, 48, 212, 134);
  c.strokeStyle = '#f4efe6'; c.lineWidth = 10; c.beginPath(); c.moveTo(24, 150); c.bezierCurveTo(90, 90, 160, 170, 232, 100); c.stroke();
  c.fillStyle = '#f4efe6'; c.font = 'bold 54px serif'; c.textAlign = 'center'; c.fillText('SODA', 128, 120);
  c.fillStyle = '#1b1b1b'; c.fillRect(14, 210, 228, 150);
  for (let i = 0; i < 6; i++) { const bx = 26 + (i % 3) * 72, by = 224 + Math.floor(i / 3) * 66; c.fillStyle = '#f2d43a'; c.fillRect(bx, by, 60, 50);
    c.fillStyle = '#c0281e'; c.font = 'bold 11px sans-serif'; c.fillText('MYSTERY', bx + 30, by + 18); c.fillStyle = '#2050c0'; c.font = 'bold 26px sans-serif'; c.fillText('?', bx + 30, by + 44); }
  c.fillStyle = '#d8d0c0'; c.fillRect(190, 372, 46, 26); c.fillStyle = '#111'; c.font = 'bold 18px sans-serif'; c.fillText('75¢', 213, 391);
  c.fillStyle = '#0b0b0b'; c.fillRect(40, 420, 120, 60);
  c.fillStyle = gr; c.fillRect(0, 0, 256, 512);
  for (let i = 0; i < 400; i++) { c.fillStyle = `rgba(${Math.random() < 0.5 ? '0,0,0' : '255,240,220'},${Math.random() * 0.12})`; c.fillRect(Math.random() * 256, Math.random() * 512, 2 + Math.random() * 6, 1 + Math.random() * 3); }
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const cuerpo = M.mat(0x9a1418, { roughness: 0.55, metalness: 0.2 });
  const caja = new THREE.Mesh(new THREE.BoxGeometry(0.95, 1.85, 0.8), cuerpo); caja.position.y = 0.95; caja.castShadow = true; caja.receiveShadow = true; g.add(caja);
  const fr = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 1.8), new THREE.MeshStandardMaterial({ map: tx, roughness: 0.5, emissive: 0xffffff, emissiveMap: tx, emissiveIntensity: 0.35 })); fr.position.set(0, 0.95, 0.401); g.add(fr);
  const luzF = new THREE.PointLight(0xffd8c0, 3.5, 3.2, 1.6); luzF.position.set(0, 1.4, 0.6); g.add(luzF);
  const lata = new THREE.Mesh(new THREE.CylinderGeometry(0.033, 0.033, 0.12, 14), M.mat(0x2a7a3a, { metalness: 0.7, roughness: 0.3 })); lata.rotation.z = Math.PI / 2; lata.visible = false; g.add(lata);
  g.position.set(x, 0, z); g.rotation.y = giro * Math.PI / 180; sc.add(g);
  return { g, luzF, fr, lata(k) { lata.visible = k > 0; lata.position.set(-0.12 + 0.05 * k, 0.32 - 0.12 * Math.min(1, k * 1.6), 0.36 + 0.04 * k); },
    luz(on) { luzF.intensity = on ? 3.5 : 0; fr.material.emissiveIntensity = on ? 0.35 : 0.05; } };
}
/** Papel blanco amarrado a un tubo con texto escrito (nota). Devuelve el grupo. */
export function notaEnTubo(sc, x, z, texto = 'Went for a walk.') {
  const g = new THREE.Group(); const tubo = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.1, 10), M.mat(0x777b7e, { metalness: 0.7, roughness: 0.35 })); tubo.position.y = 0.55; g.add(tubo);
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 180; const c = cv.getContext('2d'); c.fillStyle = '#f1ede2'; c.fillRect(0, 0, 256, 180);
  c.fillStyle = '#1a1a40'; c.font = 'italic 34px serif'; c.textAlign = 'center'; const p = texto.split(' '); c.fillText(p.slice(0, 2).join(' '), 128, 78); c.fillText(p.slice(2).join(' '), 128, 122);
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const hoja = new THREE.Mesh(new THREE.PlaneGeometry(0.28, 0.2), new THREE.MeshStandardMaterial({ map: tx, side: THREE.DoubleSide, roughness: 0.9 })); hoja.position.set(0, 0.8, 0.04); g.add(hoja);
  g.position.set(x, 0, z); sc.add(g); return g;
}
/** Celular en la oreja (se pone entre la mano derecha y la cabeza, sirve para hombres y mujeres). Llama a tel.seguir() después de setTime. */
export function telefonoOreja(sc, p, color = 0x3a3f46) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.14, 0.012), M.mat(color, { roughness: 0.4, metalness: 0.3 })); sc.add(m);
  const a = new THREE.Vector3(), b = new THREE.Vector3();
  return { m, seguir() { p.updateMatrixWorld(true); (p.getObjectByName('Bip01_R_Hand') || p).getWorldPosition(a); (p.getObjectByName('Bip01_Head') || p).getWorldPosition(b);
    m.position.copy(a).lerp(b, 0.22); m.position.y += 0.07; m.rotation.set(0, p.rotation.y + Math.PI / 2, 0.25); m.visible = a.distanceTo(b) < 0.5; } };
}
/** Fachada de tienda a pie de calle (para calleNoche: vereda en z≈-6, edificios desde z=-8.5). Vitrina iluminada, puerta y letrero. */
export function fachadaTienda(sc, x = 0, letrero = 'LOCKSMITH', zf = -8.42) {
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 96; const c = cv.getContext('2d');
  c.fillStyle = '#1d2a3a'; c.fillRect(0, 0, 512, 96); c.fillStyle = '#ffe2a0'; c.font = 'bold 58px sans-serif'; c.textAlign = 'center'; c.fillText(letrero, 256, 70);
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const l = new THREE.Mesh(new THREE.PlaneGeometry(4, 0.75), new THREE.MeshStandardMaterial({ map: tx, emissive: 0xffffff, emissiveMap: tx, emissiveIntensity: 0.7 })); l.position.set(x, 3.0, zf + 0.05); sc.add(l);
  M.caja(sc, 2.4, 1.7, 0.06, x - 0.9, 1.35, zf, emis(0xffc98a, 0.5), false); M.caja(sc, 1.0, 2.2, 0.08, x + 1.35, 1.1, zf, M.mat(0x2a1c14));
  M.caja(sc, 5.2, 0.15, 0.6, x, 3.5, zf + 0.3, M.mat(0x3a2a20));
  const luz = new THREE.PointLight(0xffc98a, 10, 6, 1.5); luz.position.set(x - 0.9, 1.6, zf + 1.0); sc.add(luz);
  return { luz };
}
/** Camioneta de reparto (furgón cerrado, frente hacia +X). */
export function furgon(sc, color = 0xd8d4c8, faros = true) {
  const g = new THREE.Group(); const m = M.mat(color, { roughness: 0.5, metalness: 0.2 }), v = M.mat(0x0b0d12, { roughness: 0.1, metalness: 0.8 });
  const add = (w, h, d, x, y, z, mm) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; g.add(b); return b; };
  add(3.6, 2.3, 2.1, -0.8, 1.55, 0, m); add(1.5, 1.5, 2.0, 1.75, 1.15, 0, m); add(0.05, 0.7, 1.7, 2.51, 1.55, 0, v); add(0.8, 0.6, 0.05, 1.8, 1.55, 1.01, v); add(0.8, 0.6, 0.05, 1.8, 1.55, -1.01, v);
  for (const [x, z] of [[1.6, 0.95], [1.6, -0.95], [-1.7, 0.95], [-1.7, -0.95]]) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.38, 0.28, 20), M.mat(0x111111)); r.rotation.x = Math.PI / 2; r.position.set(x, 0.38, z); g.add(r); }
  add(0.05, 0.18, 0.35, 2.51, 0.85, 0.7, emis(0xfff4d0, 3)); add(0.05, 0.18, 0.35, 2.51, 0.85, -0.7, emis(0xfff4d0, 3));
  if (faros) for (const z of [0.7, -0.7]) { cono(g, 2.5, 0.85, z, 8, 1.4, 0xfff2d0, 0.04, [0, 0, Math.PI / 2 - 0.08]); }
  sc.add(g); return g;
}

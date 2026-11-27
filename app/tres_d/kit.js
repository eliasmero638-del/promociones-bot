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

// ===================== 16-nov: base aérea en el desierto, caza a reacción, esfera ovni, túnel de mina con canastilla, estudio de radio, deportivo, supermercado =====================
/** Base aérea en el desierto al amanecer (tipo La Joya, Arequipa): pista a lo largo de X en z≈0, hangares y torre atrás (z≈-25),
 *  volcanes al fondo (-Z). cielo: 'amanecer' | 'dia' | 'alto' (estratosfera azul oscuro, sin suelo cerca). */
export function baseAereaDesierto(sc, { cielo = 'amanecer', semilla = 6 } = {}) {
  const az = _azar(semilla);
  if (cielo === 'alto') { M.cielo(sc, '#020a24', '#4d7fc4'); M.luces(sc, { sol: 3.0, cielo_: 1.1, dir: [20, 10, 10], color: 0xfff4e4 }); return {}; }
  if (cielo === 'amanecer') { M.cielo(sc, '#5d7fae', '#f2c49a'); sc.fog = new THREE.Fog(0xe7c7a6, 60, 420); M.luces(sc, { sol: 2.6, cielo_: 1.1, dir: [30, 9, 14], color: 0xffd9b0 }); }
  else { M.cielo(sc, '#6f9fd8', '#dfe6ee'); sc.fog = new THREE.Fog(0xdde2e6, 80, 500); M.luces(sc, { sol: 3, cielo_: 1.2, dir: [10, 20, 8] }); }
  const arena = M.matTex(M.TEX.arena(), [60, 60], 0xc7a27a);
  M.caja(sc, 1200, 0.2, 1200, 0, -0.1, 0, arena);
  M.caja(sc, 400, 0.04, 22, 0, 0.02, 0, M.matTex(M.TEX.concreto(), [80, 4], 0x6c6b68), false);
  for (let x = -190; x < 190; x += 12) M.caja(sc, 6, 0.02, 0.5, x, 0.05, 0, M.mat(0xe8e4d8), false);
  M.caja(sc, 400, 0.02, 0.4, 0, 0.05, 10, M.mat(0xe8e4d8), false); M.caja(sc, 400, 0.02, 0.4, 0, 0.05, -10, M.mat(0xe8e4d8), false);
  const gris = M.matTex(M.TEX.concreto(), [4, 2], 0xb5b0a6);
  for (const x of [-60, -30, 0, 30]) { M.caja(sc, 22, 9, 18, x, 4.5, -38, gris);
    const techo = new THREE.Mesh(new THREE.CylinderGeometry(11, 11, 18, 32), M.mat(0x8f8d88, { metalness: 0.4, roughness: 0.5 }));
    techo.rotation.x = Math.PI / 2; techo.scale.set(1, 1, 0.35); techo.position.set(x, 9, -38); techo.castShadow = true; sc.add(techo);
    M.caja(sc, 16, 7, 0.2, x, 3.5, -28.9, M.mat(0x3a3a3c)); }
  M.caja(sc, 4, 16, 4, 55, 8, -32, gris); M.caja(sc, 7, 3, 7, 55, 17.5, -32, M.mat(0x2d3a44, { metalness: 0.5, roughness: 0.2 })); M.caja(sc, 7.6, 0.4, 7.6, 55, 19.2, -32, M.mat(0x555555));
  const cerro = M.matTex(M.TEX.roca(), [6, 3], 0x9c7f66);
  for (let i = 0; i < 14; i++) { const h = 30 + az() * 60, r = 60 + az() * 90, m = new THREE.Mesh(new THREE.ConeGeometry(r, h, 9), cerro);
    m.position.set(-500 + i * 75 + az() * 30, h / 2 - 2, -260 - az() * 120); sc.add(m); }
  const misti = new THREE.Mesh(new THREE.ConeGeometry(230, 220, 24), M.matTex(M.TEX.roca(), [8, 4], 0x8a7462)); misti.position.set(-80, 108, -520); sc.add(misti);
  const nieve = new THREE.Mesh(new THREE.ConeGeometry(48, 46, 24), M.mat(0xf4f1ee)); nieve.position.set(-80, 196, -520); sc.add(nieve);
  return {};
}
/** Caza a reacción de los 80 tipo Sukhoi 22 (alas en flecha, toma de aire en la nariz). Frente hacia +X, ~19 m de largo.
 *  c.g = grupo; c.fuego(k) = brillo de la tobera (0..1). */
export function cazaReaccion(sc, { camuflaje = true } = {}) {
  const g = new THREE.Group(), c1 = M.mat(camuflaje ? 0x9aa58f : 0xa0a4a8, { roughness: 0.55, metalness: 0.35 }), c2 = M.mat(0x5d6e52, { roughness: 0.6, metalness: 0.3 });
  const osc = M.mat(0x2a2c2e, { roughness: 0.4, metalness: 0.6 });
  const fus = new THREE.Mesh(new THREE.CylinderGeometry(0.85, 0.75, 15, 20), c1); fus.rotation.z = Math.PI / 2; g.add(fus);
  const nariz = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.85, 2.4, 20, 1, true), c1); nariz.rotation.z = -Math.PI / 2; nariz.position.x = 8.7; g.add(nariz);
  const toma = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.1, 20), osc); toma.rotation.z = Math.PI / 2; toma.position.x = 9.9; g.add(toma);
  const cono = new THREE.Mesh(new THREE.ConeGeometry(0.3, 0.9, 16), M.mat(0xb0281e, { roughness: 0.4 })); cono.rotation.z = -Math.PI / 2; cono.position.x = 10.2; g.add(cono);
  const cab = new THREE.Mesh(new THREE.SphereGeometry(0.62, 20, 14), new THREE.MeshStandardMaterial({ color: 0x1b2a38, roughness: 0.05, metalness: 0.9 }));
  cab.scale.set(2.4, 0.9, 0.8); cab.position.set(5.0, 0.85, 0); g.add(cab);
  const lomo = new THREE.Mesh(new THREE.BoxGeometry(7, 0.5, 0.7), c1); lomo.position.set(0.5, 0.8, 0); g.add(lomo);
  const ala = (lado) => { const s = new THREE.Shape(); s.moveTo(2.2, 0); s.lineTo(-3.2, 5.6 * lado); s.lineTo(-4.6, 5.6 * lado); s.lineTo(-3.4, 0); s.lineTo(2.2, 0);
    const m = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: 0.14, bevelEnabled: false }), lado > 0 ? c2 : c1); m.rotation.x = -Math.PI / 2; m.position.set(0, -0.15, 0); g.add(m); };
  ala(1); ala(-1);
  const deriva = new THREE.Shape(); deriva.moveTo(-4.0, 0); deriva.lineTo(-6.8, 3.6); deriva.lineTo(-7.8, 3.6); deriva.lineTo(-7.4, 0); deriva.lineTo(-4.0, 0);
  const dv = new THREE.Mesh(new THREE.ExtrudeGeometry(deriva, { depth: 0.14, bevelEnabled: false }), c2); dv.position.set(0, 0.6, -0.07); g.add(dv);
  for (const lado of [1, -1]) { const s = new THREE.Shape(); s.moveTo(-5.4, 0); s.lineTo(-7.4, 2.6 * lado); s.lineTo(-8.0, 2.6 * lado); s.lineTo(-7.6, 0); s.lineTo(-5.4, 0);
    const m = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: 0.1, bevelEnabled: false }), c1); m.rotation.x = -Math.PI / 2; m.position.y = 0; g.add(m); }
  const tob = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.55, 0.6, 20), osc); tob.rotation.z = Math.PI / 2; tob.position.x = -7.8; g.add(tob);
  const llama = brilloSprite('#ff9a40', 2.4, 0.95), halo = brilloSprite('#ffd27a', 1.2, 1); llama.position.x = -8.6; halo.position.x = -8.3; g.add(llama); g.add(halo);
  const luz = new THREE.PointLight(0xff9a40, 0, 12, 1.6); luz.position.x = -9; g.add(luz);
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  sc.add(g);
  return { g, fuego(k) { llama.scale.setScalar(1.2 + 3.2 * k + Math.random() * 0.3); llama.material.opacity = 0.3 + 0.65 * k; halo.material.opacity = k; luz.intensity = 30 * k; } };
}
/** Objeto plateado redondo (relato de La Joya 1980): esfera de metal pulido con cúpula color crema arriba y base ancha de metal.
 *  Sin alas, ventanas ni motores. o.g = grupo; o.brillo(k) = resplandor. Diámetro ~10 m con escala 1. */
export function esferaOvni(sc, escala = 1) {
  const g = new THREE.Group();
  const plata = new THREE.MeshStandardMaterial({ color: 0xd4d8de, metalness: 0.75, roughness: 0.26, emissive: 0x6a7280, emissiveIntensity: 0.35 });
  const cuerpo = new THREE.Mesh(new THREE.SphereGeometry(4.2, 48, 32), plata); cuerpo.scale.y = 0.78; g.add(cuerpo);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(5.0, 3.4, 1.2, 48), plata); base.position.y = -2.2; g.add(base);
  const anillo = new THREE.Mesh(new THREE.TorusGeometry(4.95, 0.18, 12, 64), plata); anillo.rotation.x = Math.PI / 2; anillo.position.y = -1.65; g.add(anillo);
  const cup = new THREE.Mesh(new THREE.SphereGeometry(2.2, 32, 18, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0xf1e2bc, metalness: 0.2, roughness: 0.08, emissive: 0x6d5a30, emissiveIntensity: 0.5, transparent: true, opacity: 0.92 }));
  cup.position.y = 2.9; g.add(cup);
  const halo = brilloSprite('#fff4dc', 19, 0.3); g.add(halo);
  g.scale.setScalar(escala); g.traverse(o => { if (o.isMesh) { o.castShadow = true; } }); sc.add(g);
  return { g, brillo(k) { halo.material.opacity = 0.1 + 0.3 * k; plata.emissiveIntensity = 0.25 + 0.3 * k; } };
}
/** Avión que pasa: estela de vapor blanca detrás de un punto (k 0..1 de largo). */
export function estela(sc, n = 30) {
  const ps = []; for (let i = 0; i < n; i++) { const s = brilloSprite('#ffffff', 2, 0.25); s.material.blending = THREE.NormalBlending; sc.add(s); ps.push(s); }
  return { poner(pos, dir, largo = 30) { const d = dir.clone().normalize(); ps.forEach((s, i) => { s.position.copy(pos).addScaledVector(d, -(i + 1) * largo / n); s.scale.setScalar(2.6 + i * 0.2); s.material.opacity = 0.3 * (1 - i / n); }); } };
}
/** Nubes bajas (alfombra de nubes vista desde arriba, a la altura y). */
export function marNubes(sc, y = -40, n = 120, semilla = 3) {
  const az = _azar(semilla), c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d');
  const gr = x.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,0.95)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = gr; x.fillRect(0, 0, 128, 128);
  const tx = new THREE.CanvasTexture(c); const g = new THREE.Group();
  for (let i = 0; i < n; i++) { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, depthWrite: false, opacity: 0.85, fog: false }));
    s.position.set((az() - 0.5) * 900, y + az() * 10, (az() - 0.5) * 900 - 150); s.scale.setScalar(80 + az() * 120); g.add(s); }
  sc.add(g); return g;
}

/** Túnel de mina subterránea de roca dura (a casi 1 km), de noche total: galería a lo largo de Z (de z=-30 a 10), ancho 5, alto 4.5.
 *  Malla de acero en el techo, tubo de ventilación, luces débiles. Devuelve {caerRocas(t), polvo}. */
export function minaTunel(sc, { luz = 0.6 } = {}) {
  sc.background = new THREE.Color(0x020202); sc.fog = new THREE.FogExp2(0x0b0907, 0.06);
  sc.add(new THREE.HemisphereLight(0x8a7e70, 0x0c0a08, 0.18 * luz));
  const roca = M.matTex(M.TEX.roca(), [8, 2], 0x7a7068), az = _azar(21);
  M.caja(sc, 6, 0.3, 50, 0, -0.15, -10, M.matTex(M.TEX.arena(), [3, 20], 0x5a5048));
  for (let z = -34; z < 12; z += 1.6) for (const lado of [-1, 1]) {
    const r = new THREE.Mesh(new THREE.DodecahedronGeometry(1.4 + az() * 0.6, 1), roca); r.position.set(lado * (3.0 + az() * 0.5), 1.0 + az() * 2.6, z); r.scale.set(1, 1.6, 1.2); r.receiveShadow = true; r.castShadow = true; sc.add(r);
    const t = new THREE.Mesh(new THREE.DodecahedronGeometry(1.5 + az() * 0.5, 1), roca); t.position.set(lado * (1.2 + az()), 5.0 + az() * 0.4, z); t.receiveShadow = true; sc.add(t); }
  const malla = M.mat(0x6a6a66, { metalness: 0.7, roughness: 0.5 });
  for (let z = -34; z < 12; z += 2.2) { M.caja(sc, 4.8, 0.06, 0.06, 0, 4.15, z, malla, false); }
  for (let x = -2.2; x <= 2.2; x += 0.55) M.caja(sc, 0.04, 0.04, 46, x, 4.12, -11, malla, false);
  const tubo = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 46, 16), M.mat(0xc9b23a, { roughness: 0.7 })); tubo.rotation.x = Math.PI / 2; tubo.position.set(1.9, 3.6, -11); sc.add(tubo);
  for (const z of [-24, -12, 2]) { M.caja(sc, 0.25, 0.12, 0.25, -2.1, 3.4, z, emis(0xffd890, 1.6), false); const l = new THREE.PointLight(0xffc880, 3 * luz, 9, 1.6); l.position.set(-2.0, 3.2, z); sc.add(l); }
  const caidas = []; for (let i = 0; i < 26; i++) { const r = new THREE.Mesh(new THREE.DodecahedronGeometry(0.2 + az() * 0.7, 0), roca); r.castShadow = true;
    r.userData = { x: (az() - 0.5) * 4.4, z: -3.2 + (az() - 0.5) * 2.4, d: az() * 0.8, v: 0.5 + az(), r: [az() * 4, az() * 4] }; r.visible = false; sc.add(r); caidas.push(r); }
  const n0 = sc.children.length, polvo = nubePolvo(sc, 0, 3.0, -3.5, 26, 2.6);
  sc.children.slice(n0).forEach(o => { if (o.material) { o.material.color.setHex(0x6a6052); } });
  return { caerRocas(t) { caidas.forEach(r => { const u = r.userData, k = t - u.d; r.visible = k > 0; if (k <= 0) return;
      const y = Math.max(0.25, 4.2 - 4.9 * k * k * u.v); r.position.set(u.x, y, u.z); r.rotation.set(u.r[0] * k, u.r[1] * k, 0); }); polvo.poner(t > 0 ? t * 0.9 : -1); } };
}
/** Canastilla metálica (jaula de 1,2 m de alto) en la punta del brazo de un manipulador telescópico. Base en (x,0,z). */
export function canastilla(sc, x = 0, z = 0, { brazo = true } = {}) {
  const g = new THREE.Group(), ac = M.mat(0xd9a521, { metalness: 0.4, roughness: 0.5 }), gr = M.mat(0x5d5f60, { metalness: 0.7, roughness: 0.4 });
  M.caja(g, 2.2, 0.08, 1.4, 0, 0.04, 0, gr);
  for (const [px, pz] of [[-1.05, -0.65], [1.05, -0.65], [-1.05, 0.65], [1.05, 0.65]]) M.caja(g, 0.07, 1.2, 0.07, px, 0.6, pz, ac);
  for (const y of [0.6, 1.2]) { M.caja(g, 2.2, 0.06, 0.06, 0, y, -0.65, ac); M.caja(g, 2.2, 0.06, 0.06, 0, y, 0.65, ac); M.caja(g, 0.06, 0.06, 1.4, -1.05, y, 0, ac); M.caja(g, 0.06, 0.06, 1.4, 1.05, y, 0, ac); }
  for (let i = -1; i <= 1; i += 0.25) { M.caja(g, 0.025, 1.15, 0.025, i, 0.6, -0.65, gr, false); }
  if (brazo) { const b = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 6), ac); b.position.set(0, 0.9, -3.6); b.rotation.x = -0.12; b.castShadow = true; g.add(b); }
  g.position.set(x, 0, z); sc.add(g); return g;
}
/** Linterna de casco minero en una persona realista (casco amarillo + foco). l.seguir() después de setTime. */
export function cascoMinero(sc, p, { color = 0xf2c230, potencia = 30 } = {}) {
  const casco = new THREE.Mesh(new THREE.SphereGeometry(0.135, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), M.mat(color ?? 0xf2c230, { roughness: 0.4 }));
  const ala = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.012, 24), M.mat(color ?? 0xf2c230, { roughness: 0.4 })); casco.add(ala);
  const foco = new THREE.Mesh(new THREE.SphereGeometry(0.03, 10, 8), new THREE.MeshBasicMaterial({ color: 0xfff6d8 })); foco.position.set(0, 0.06, 0.13); casco.add(foco);
  sc.add(casco); if (color === null) { casco.material.visible = false; ala.material.visible = false; }
  const l = new THREE.SpotLight(0xfff1cf, potencia, 12, 0.42, 0.5, 1.4); l.castShadow = true; l.shadow.mapSize.set(512, 512); sc.add(l); const tg = new THREE.Object3D(); sc.add(tg); l.target = tg;
  const haz = cono(sc, 0, 0, 0, 5, 1.0, 0xfff1cf, 0.035);
  const v = new THREE.Vector3(), q = new THREE.Quaternion(), d = new THREE.Vector3();
  return { seguir() { p.updateMatrixWorld(true); const h = p.getObjectByName('Bip01_Head') || p; h.getWorldPosition(v); h.getWorldQuaternion(q);
    casco.position.copy(v).add(new THREE.Vector3(0, 0.1, 0)); d.set(0, 0, 1).applyQuaternion(p.quaternion); d.y = -0.2; d.normalize();
    casco.rotation.set(0, p.rotation.y, 0); l.position.copy(casco.position).addScaledVector(d, 0.15); l.position.y += 0.06; tg.position.copy(l.position).addScaledVector(d, 8);
    haz.position.copy(l.position); haz.lookAt(tg.position); haz.rotateX(-Math.PI / 2); } };
}
/** Estudio de radio de 1990 de noche: consola con perillas, micrófono en brazo, letrero ON AIR rojo, tablero de líneas telefónicas
 *  con focos (tab.lineas(k, t, especial) → k = cuántas prenden). Locutor en (0, -0.9) mirando a +Z hacia la cámara. */
export function estudioRadio(sc, { letrero = 'ON AIR' } = {}) {
  sc.background = new THREE.Color(0x07070a); sc.add(new THREE.HemisphereLight(0x8090b0, 0x141018, 0.4));
  const pared = M.matTex(M.TEX.concreto(), [4, 2], 0x3f3a48), piso = M.matTex(M.TEX.arena(), [4, 4], 0x3a3036);
  M.caja(sc, 10, 0.1, 10, 0, -0.05, 0, piso); M.caja(sc, 10, 3.2, 0.2, 0, 1.6, -2.6, pared); M.caja(sc, 0.2, 3.2, 10, -3.6, 1.6, 0, pared);
  for (let i = 0; i < 18; i++) for (let j = 0; j < 6; j++) M.caja(sc, 0.45, 0.45, 0.12, -4 + i * 0.5, 0.6 + j * 0.5, -2.45, M.mat(j % 2 === i % 2 ? 0x2a2630 : 0x34303c, { roughness: 1 }), false);
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 96; const c2 = cv.getContext('2d');
  c2.fillStyle = '#300'; c2.fillRect(0, 0, 256, 96); c2.fillStyle = '#ff3a2a'; c2.font = 'bold 56px Arial'; c2.textAlign = 'center'; c2.fillText(letrero, 128, 68);
  const tl = new THREE.CanvasTexture(cv); tl.colorSpace = THREE.SRGBColorSpace;
  const onair = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.38), new THREE.MeshBasicMaterial({ map: tl })); onair.position.set(0.9, 2.55, -2.38); sc.add(onair);
  const lr = new THREE.PointLight(0xff3020, 3, 4, 1.6); lr.position.set(0.9, 2.5, -2.0); sc.add(lr);
  const consola = M.mat(0x2b2c30, { roughness: 0.5, metalness: 0.3 });
  M.caja(sc, 2.6, 0.12, 1.0, 0, 0.82, -0.1, consola); M.caja(sc, 2.6, 0.8, 0.1, 0, 0.42, 0.38, consola);
  const tabla = new THREE.Mesh(new THREE.BoxGeometry(2.3, 0.08, 0.55), M.mat(0x3a3c42, { metalness: 0.4 })); tabla.position.set(0, 0.92, -0.2); tabla.rotation.x = 0.25; sc.add(tabla);
  for (let i = 0; i < 12; i++) { M.caja(sc, 0.05, 0.03, 0.18, -1.0 + i * 0.18, 0.98, -0.18 + (i % 3) * 0.02, M.mat(0xdcdcdc), false); M.caja(sc, 0.04, 0.04, 0.04, -1.0 + i * 0.18, 1.0, -0.36, emis(i % 4 ? 0x4cff7a : 0xffb030, 1.2), false); }
  const brazoM = M.mat(0x161616, { metalness: 0.6 });
  M.caja(sc, 0.04, 0.6, 0.04, -0.55, 1.2, -0.25, brazoM); const bm = M.caja(sc, 0.04, 0.04, 0.55, -0.42, 1.48, -0.5, brazoM); bm.rotation.y = -0.5;
  const mic = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.22, 16), M.mat(0x222222, { metalness: 0.6, roughness: 0.4 })); mic.rotation.x = Math.PI / 2.4; mic.position.set(-0.25, 1.46, -0.72); sc.add(mic);
  const lc = document.createElement('canvas'); lc.width = 512; lc.height = 256; const lg = lc.getContext('2d');
  const lt = new THREE.CanvasTexture(lc); lt.colorSpace = THREE.SRGBColorSpace;
  const panel = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 0.55), new THREE.MeshBasicMaterial({ map: lt })); panel.position.set(-1.7, 1.75, -2.36); sc.add(panel);
  const lp = new THREE.PointLight(0xff5a3a, 0, 3, 1.6); lp.position.set(-1.7, 1.75, -1.9); sc.add(lp);
  for (const x of [-1.6, 1.6]) { const l = new THREE.SpotLight(0xffe6c0, 14, 7, 0.6, 0.7, 1.4); l.position.set(x, 3, 1.2); const tg = new THREE.Object3D(); tg.position.set(0, 1, -1); sc.add(tg); l.target = tg; l.castShadow = x < 0; sc.add(l); }
  const telefono = new THREE.Group(); M.caja(telefono, 0.3, 0.1, 0.22, 0, 0, 0, M.mat(0xdedad0)); M.caja(telefono, 0.32, 0.06, 0.07, 0, 0.08, 0, M.mat(0xdedad0)); telefono.position.set(0.95, 0.93, -0.25); sc.add(telefono);
  return { lineas(k, t, especial = null) {
    lg.fillStyle = '#121214'; lg.fillRect(0, 0, 512, 256); lg.font = 'bold 26px Arial'; lg.fillStyle = '#bbb'; lg.fillText('LÍNEAS', 18, 34);
    for (let i = 0; i < 10; i++) { const x = 40 + (i % 5) * 96, y = 100 + Math.floor(i / 5) * 90, on = i / 10 < k;
      const parp = on && Math.sin(t * 14 + i * 2.3) > -0.2; lg.fillStyle = parp ? '#ff3a22' : '#401010'; lg.beginPath(); lg.arc(x, y, 26, 0, 6.3); lg.fill();
      lg.fillStyle = '#888'; lg.font = '18px Arial'; lg.fillText(String(i + 1), x - 6, y + 50); }
    if (especial) { lg.fillStyle = 'rgba(0,0,0,0.75)'; lg.fillRect(0, 0, 512, 256); lg.fillStyle = '#4cff7a'; lg.font = 'bold 92px Arial'; lg.textAlign = 'center'; lg.fillText(especial, 256, 160); lg.textAlign = 'left'; }
    lt.needsUpdate = true; lp.intensity = k > 0 ? 2 + Math.sin(t * 14) : 0; } };
}
/** Deportivo de los 80 en cuña (tipo Porsche 944), frente hacia +X, rojo por defecto. */
export function deportivo(sc, color = 0xc4161c) {
  const g = new THREE.Group(), m = M.mat(color, { roughness: 0.22, metalness: 0.55 }), v = M.mat(0x3a4a5c, { roughness: 0.12, metalness: 0.3 });
  const add = (geo, mm, x, y, z) => { const b = new THREE.Mesh(geo, mm); b.position.set(x, y, z); b.castShadow = true; b.receiveShadow = true; g.add(b); return b; };
  add(new THREE.BoxGeometry(4.2, 0.55, 1.75), m, 0, 0.55, 0);
  add(new THREE.BoxGeometry(1.7, 0.1, 1.7), m, 1.3, 0.86, 0);
  add(new THREE.BoxGeometry(1.9, 0.5, 1.5), v, -0.45, 1.05, 0);
  const vid = add(new THREE.BoxGeometry(0.9, 0.06, 1.5), v, 0.75, 1.02, 0); vid.rotation.z = -0.55;
  add(new THREE.BoxGeometry(1.4, 0.06, 1.52), m, -0.5, 1.31, 0); const tr = add(new THREE.BoxGeometry(1.0, 0.06, 1.5), v, -1.4, 1.08, 0); tr.rotation.z = 0.4;
  for (const [x, z] of [[1.35, 0.82], [1.35, -0.82], [-1.3, 0.82], [-1.3, -0.82]]) { const r = add(new THREE.CylinderGeometry(0.33, 0.33, 0.26, 22), M.mat(0x121212), x, 0.33, z); r.rotation.x = Math.PI / 2;
    const l = add(new THREE.CylinderGeometry(0.2, 0.2, 0.27, 12), M.mat(0x9a9a9a, { metalness: 0.9, roughness: 0.3 }), x, 0.33, z); l.rotation.x = Math.PI / 2; }
  add(new THREE.BoxGeometry(0.05, 0.12, 1.5), emis(0xff2a1a, 1.5), -2.11, 0.68, 0); add(new THREE.BoxGeometry(0.05, 0.1, 0.35), emis(0xfff4d0, 2), 2.11, 0.62, 0.6); add(new THREE.BoxGeometry(0.05, 0.1, 0.35), emis(0xfff4d0, 2), 2.11, 0.62, -0.6);
  sc.add(g); return g;
}
/** Pasillo de supermercado (luz de tubo blanca): estantes con cajas de colores a ambos lados de X=±1.6, a lo largo de Z. */
export function supermercado(sc) {
  sc.background = new THREE.Color(0xdfe3e6); sc.add(new THREE.HemisphereLight(0xffffff, 0x8a8a84, 1.1));
  M.caja(sc, 30, 0.1, 40, 0, -0.05, 0, M.matTex(M.TEX.concreto(), [8, 10], 0xd8d4cc)); M.caja(sc, 30, 0.1, 40, 0, 3.6, 0, M.mat(0xe8e8e4));
  const az = _azar(8), cols = [0xd12b2b, 0xf0b417, 0x2a6fd1, 0x2fa04a, 0xf07a1a, 0xffffff, 0x8a3fb0];
  for (const x of [-1.8, 1.8]) { M.caja(sc, 0.3, 2.4, 24, x + Math.sign(x) * 0.3, 1.2, -6, M.mat(0xc7c9cc, { metalness: 0.3 }));
    for (let n = 0; n < 5; n++) M.caja(sc, 0.5, 0.04, 24, x + Math.sign(x) * 0.05, 0.28 + n * 0.55, -6, M.mat(0xb8bcc0, { metalness: 0.4 }), false);
    for (let n = 0; n < 4; n++) for (let z = -17.5; z < 5.5; z += 0.32) { const h = 0.22 + az() * 0.18;
      M.caja(sc, 0.25, h, 0.28, x, 0.3 + n * 0.55 + h / 2, z, M.mat(cols[Math.floor(az() * cols.length)], { roughness: 0.6 }), false); } }
  for (let z = -16; z < 6; z += 4) { M.caja(sc, 0.3, 0.05, 2.4, 0, 3.52, z, emis(0xffffff, 2), false); const l = new THREE.PointLight(0xffffff, 6, 8, 1.4); l.position.set(0, 3.2, z); sc.add(l); }
  const carrito = new THREE.Group(), ac = M.mat(0xb0b4b8, { metalness: 0.8, roughness: 0.3 });
  M.caja(carrito, 0.55, 0.45, 0.85, 0, 0.75, 0, M.mat(0x9aa0a6, { metalness: 0.7, roughness: 0.35, transparent: true, opacity: 0.7 })); M.caja(carrito, 0.04, 0.6, 0.04, -0.25, 0.35, 0.35, ac); M.caja(carrito, 0.04, 0.6, 0.04, 0.25, 0.35, 0.35, ac);
  M.caja(carrito, 0.04, 0.6, 0.04, -0.25, 0.35, -0.35, ac); M.caja(carrito, 0.04, 0.6, 0.04, 0.25, 0.35, -0.35, ac); M.caja(carrito, 0.6, 0.04, 0.04, 0, 1.1, 0.5, ac);
  sc.add(carrito); return { carrito };
}

// ===================== 17-nov: carretera en bosque de pinos (Texas), objeto diamante con fuego, helicóptero Chinook, granja al atardecer (Oregón),
// platillo de McMinnville, cajero automático de noche, laptop con pantalla, patio de casa de noche con barril enterrado =====================
/** Carretera de dos carriles a lo largo de X (z≈0) entre pinos densos (este de Texas), de noche y mojada. Los árboles empiezan en |z|>4.5. */
export function carreteraBosque(sc, { semilla = 21, luna = 1 } = {}) {
  M.cielo(sc, '#04060c', '#141b2a'); sc.fog = new THREE.FogExp2(0x0a0f18, 0.03);
  sc.add(new THREE.HemisphereLight(0x5a6f99, 0x15141a, 0.5 * luna));
  const l = new THREE.DirectionalLight(0x8fa8ff, 0.9 * luna); l.position.set(-10, 22, 8); l.castShadow = true; l.shadow.mapSize.set(2048, 2048);
  Object.assign(l.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30 }); sc.add(l);
  M.caja(sc, 200, 0.2, 140, 0, -0.12, 0, M.matTex(M.TEX.arena(), [50, 40], 0x2c2a22));
  M.caja(sc, 200, 0.05, 6.4, 0, 0.0, 0, M.matTex(M.TEX.concreto(), [50, 2], 0x2a2b2e, { roughness: 0.35, metalness: 0.15 }));
  for (let x = -100; x < 100; x += 5) M.caja(sc, 2.4, 0.02, 0.12, x, 0.03, 0, emis(0xd6b04a, 0.12), false);
  for (const z of [3.0, -3.0]) M.caja(sc, 200, 0.02, 0.1, 0, 0.03, z, M.mat(0xbdb8a8), false);
  const az = _azar(semilla), tronco = M.mat(0x2b2018, { roughness: 1 }), h1 = M.mat(0x16281c, { roughness: 1 }), h2 = M.mat(0x1d3424, { roughness: 1 });
  for (let i = 0; i < 380; i++) {
    const lado = az() < 0.5 ? -1 : 1, z = lado * (4.8 + az() * 40), x = (az() - 0.5) * 160, h = 9 + az() * 10, g = new THREE.Group();
    const t = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.28, h, 7), tronco); t.position.y = h / 2; t.castShadow = true; g.add(t);
    for (let k = 0; k < 3; k++) { const c = new THREE.Mesh(new THREE.ConeGeometry(1.7 - k * 0.4, 2.8, 8), k % 2 ? h1 : h2); c.position.y = h * 0.55 + k * 1.6; c.castShadow = true; g.add(c); }
    g.position.set(x, 0, z); g.rotation.y = az() * 6; sc.add(g);
  }
}
/** Objeto plateado gigante con forma de diamante (Cash-Landrum 1980): puntas cortadas, luces azules en el centro y llamas por debajo.
 *  d.mover(t, fuego 0..1). d.g = grupo (alto ≈ 9 m). La luz de las llamas ilumina el suelo. */
export function diamante(sc, escala = 1) {
  const g = new THREE.Group(); sc.add(g);
  const met = M.mat(0xb8bcc4, { metalness: 0.45, roughness: 0.35, emissive: 0x1a1e26, flatShading: true });
  const arr = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 4.2, 4.0, 4, 1), met); arr.position.y = 2.0; g.add(arr);
  const aba = new THREE.Mesh(new THREE.CylinderGeometry(4.2, 1.0, 4.4, 4, 1), met); aba.position.y = -2.2; g.add(aba);
  const luces = [];
  for (let i = 0; i < 16; i++) { const a = i / 16 * Math.PI * 2, r = 3.0 * (Math.abs(Math.cos(a)) + Math.abs(Math.sin(a))) ** -1 * 1.42;
    const sp = brilloSprite('#5aa8ff', 0.9, 1); sp.position.set(Math.cos(a) * r, 0, Math.sin(a) * r); g.add(sp); luces.push(sp); }
  const llama = []; for (let i = 0; i < 18; i++) { const sp = brilloSprite(i < 6 ? '#fff0b0' : i < 12 ? '#ff9a30' : '#ff4a10', 3.2 - i * 0.08, 0.9 - i * 0.03); g.add(sp); llama.push(sp); }
  const luz = new THREE.PointLight(0xff8a3a, 0, 90, 1.3); luz.position.set(0, -10, 0); g.add(luz);
  const plata = new THREE.PointLight(0xc8d4ff, 40, 14, 1.2); plata.position.set(6, 1, 6); g.add(plata);
  const azul = new THREE.PointLight(0x7ab0ff, 60, 40, 1.5); g.add(azul);
  g.rotation.y = Math.PI / 4; g.scale.setScalar(escala);
  return { g, mover(t, fuego = 1) {
    llama.forEach((sp, i) => { const k = i / llama.length; sp.visible = fuego > 0.02;
      sp.position.set(Math.sin(t * 17 + i) * 0.25 * k, -4.6 - k * 7 * fuego, Math.cos(t * 13 + i * 2) * 0.25 * k);
      sp.scale.setScalar((3.6 - k * 1.6) * (0.6 + fuego * 0.6) * (0.9 + 0.15 * Math.sin(t * 25 + i))); });
    luz.intensity = 1100 * fuego * (0.85 + 0.15 * Math.sin(t * 30));
    luces.forEach((sp, i) => sp.material.opacity = 0.5 + 0.5 * Math.sin(t * 6 + i * 0.8)); } };
}
/** Helicóptero militar de doble hélice tipo Chinook (verde oliva), frente hacia +X, ~15 m. h.userData.mover(t) gira las hélices. */
export function chinook(sc, { foco = true } = {}) {
  const g = new THREE.Group(), olivo = M.mat(0x3d4430, { roughness: 0.7 }), osc = M.mat(0x1c1e18);
  const add = (geo, m, x, y, z, p = g) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; p.add(o); return o; };
  const cu = add(new THREE.BoxGeometry(11, 2.6, 2.5), olivo, 0, 2.2, 0);
  add(new THREE.CylinderGeometry(1.3, 1.3, 2.5, 16, 1, false, 0, Math.PI), olivo, 5.5, 2.2, 0).rotation.x = Math.PI / 2;
  add(new THREE.BoxGeometry(1.4, 0.9, 2.3), M.mat(0x0b0d10, { metalness: 0.7, roughness: 0.15 }), 5.9, 2.9, 0);
  add(new THREE.BoxGeometry(2.2, 4.4, 1.0), olivo, -5.2, 3.6, 0); add(new THREE.BoxGeometry(2.0, 1.4, 2.0), olivo, 4.6, 3.8, 0);
  for (const z of [1.3, -1.3]) add(new THREE.BoxGeometry(7, 1.2, 0.5), olivo, -0.5, 1.4, z);
  for (const [x, z] of [[3.5, 1.2], [3.5, -1.2], [-3.5, 1.3], [-3.5, -1.3]]) { add(new THREE.CylinderGeometry(0.4, 0.4, 0.3, 14), osc, x, 0.4, z).rotation.x = Math.PI / 2; }
  const rotores = [];
  for (const [x, y] of [[4.6, 4.7], [-5.2, 6.0]]) { const r = new THREE.Group(); r.position.set(x, y, 0); g.add(r); rotores.push(r);
    for (let i = 0; i < 3; i++) { const p = new THREE.Mesh(new THREE.BoxGeometry(9.0, 0.06, 0.5), osc); p.position.x = 4.5; const gg = new THREE.Group(); gg.rotation.y = i * 2 * Math.PI / 3; gg.add(p); r.add(gg); }
    const d = new THREE.Mesh(new THREE.CircleGeometry(9, 40), new THREE.MeshBasicMaterial({ color: 0x0a0a0a, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false })); d.rotation.x = -Math.PI / 2; r.add(d); }
  add(new THREE.BoxGeometry(0.1, 0.1, 0.1), emis(0xff2a1a, 4), -5.3, 5.9, 0); add(new THREE.BoxGeometry(0.15, 0.15, 0.15), emis(0x30ff60, 3), 0, 2.2, 1.3);
  add(new THREE.BoxGeometry(0.15, 0.15, 0.15), emis(0xff3020, 3), 0, 2.2, -1.3);
  const parp = brilloSprite('#ffffff', 3.5, 1); parp.position.set(0, 3.7, 0); g.add(parp);
  const roja = brilloSprite('#ff3020', 1.6, 0.9); roja.position.set(-5.3, 6.1, 0); g.add(roja);
  if (foco) { const l = new THREE.SpotLight(0xfff2d8, 300, 60, 0.25, 0.4, 1.2); l.position.set(5, 0.9, 0); const tg = new THREE.Object3D(); tg.position.set(14, -20, 0); g.add(tg); l.target = tg; g.add(l);
    cono(g, 5, 0.9, 0, 30, 4, 0xfff2d8, 0.035, [0, 0, 0.45]); }
  g.userData.mover = t => { rotores[0].rotation.y = t * 22; rotores[1].rotation.y = -t * 22; parp.visible = Math.floor(t * 2.5) % 2 === 0; };
  sc.add(g); return g;
}
/** Granja en el campo al atardecer (Oregón 1950): pasto, galpón con tanque de agua, casa de madera, poste de teléfono con cables y cerros.
 *  La casa está en (0, -14), el galpón con tanque en (-8, -6), el poste en (9, -8). Devuelve {cables: [y alto]}. */
export function granja(sc, { semilla = 5 } = {}) {
  M.cielo(sc, '#6f7f96', '#e8c9a0'); sc.fog = new THREE.Fog(0xcfb79a, 40, 170);
  M.luces(sc, { sol: 1.6, cielo_: 1.1, dir: [-20, 10, -12], color: 0xffd6a0 });
  M.caja(sc, 300, 0.2, 300, 0, -0.1, 0, M.matTex(M.TEX.arena(), [60, 60], 0x6c7244));
  const az = _azar(semilla), mad = M.matTex(M.TEX.ladrillo(), [3, 2], 0x8a7a64), techo = M.mat(0x3a302a, { roughness: 0.9 });
  M.caja(sc, 8, 4, 6, 0, 2, -16, M.mat(0xd8d0c0)); const t1 = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 4.6, 2.2, 4, 1), techo); t1.rotation.y = Math.PI / 4; t1.scale.set(1.25, 1, 0.95); t1.position.set(0, 5.1, -16); sc.add(t1);
  for (const x of [-2.2, 0, 2.2]) M.caja(sc, 0.9, 1.1, 0.06, x, 2.2, -12.95, emis(0xffc070, 0.45), false);
  M.caja(sc, 6, 3.4, 5, -8, 1.7, -7, M.mat(0x7a5236, { roughness: 0.95 })); M.caja(sc, 6.4, 0.3, 5.6, -8, 3.5, -7, techo);
  const tq = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.4, 2.6, 20), M.mat(0x9a9890, { metalness: 0.5, roughness: 0.5 })); tq.rotation.z = Math.PI / 2; tq.position.set(-7.6, 1.4, -3.8); tq.castShadow = true; sc.add(tq);
  const poste = M.mat(0x3a2c20); M.caja(sc, 0.25, 9, 0.25, 9, 4.5, -8, poste); M.caja(sc, 2.2, 0.15, 0.15, 9, 8.4, -8, poste);
  const cab = M.mat(0x1a1a1a);
  for (const [dz, y] of [[-0.9, 8.5], [0.9, 8.5]]) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 60, 4), cab); c.rotation.z = Math.PI / 2; c.rotation.y = 0.35; c.position.set(-15, y - 0.4, -8 + dz - 8); sc.add(c); }
  for (let i = 0; i < 8; i++) { const r = 30 + az() * 30, c = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), M.mat(0x48503a, { roughness: 1 }));
    c.scale.y = 0.18 + az() * 0.1; c.position.set(-140 + i * 40 + az() * 20, -1, -120 - az() * 30); sc.add(c); }
  for (let i = 0; i < 40; i++) { const x = (az() - 0.5) * 120, z = -25 - az() * 60; if (Math.abs(x) < 6) continue; const h = 5 + az() * 7, gg = new THREE.Group();
    const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.25, h, 6), M.mat(0x3a2c20)); tr.position.y = h / 2; gg.add(tr);
    const co = new THREE.Mesh(new THREE.ConeGeometry(1.8, h * 0.8, 8), M.mat(0x2e4024)); co.position.y = h * 0.75; gg.add(co); gg.position.set(x, 0, z); sc.add(gg); }
  for (let x = -20; x < 20; x += 2.5) { M.caja(sc, 0.12, 1.2, 0.12, x, 0.6, 3, M.mat(0x6a5440)); }
  M.caja(sc, 40, 0.08, 0.06, 0, 1.0, 3, M.mat(0x6a5440)); M.caja(sc, 40, 0.08, 0.06, 0, 0.6, 3, M.mat(0x6a5440));
  return {};
}
/** Platillo metálico de McMinnville: disco plano con una torre pequeña desplazada arriba (diámetro 2*r). Devuelve el grupo. */
export function platillo(sc, r = 4) {
  const g = new THREE.Group(), met = M.mat(0x9a9ea6, { metalness: 0.85, roughness: 0.28 });
  const d = new THREE.Mesh(new THREE.SphereGeometry(r, 40, 16), met); d.scale.y = 0.16; g.add(d);
  const b = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.55, r * 0.75, r * 0.12, 32), M.mat(0x5a5e66, { metalness: 0.8, roughness: 0.4 })); b.position.y = -r * 0.08; g.add(b);
  const to = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.06, r * 0.1, r * 0.35, 10), met); to.position.set(r * 0.12, r * 0.28, 0); g.add(to);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; }); sc.add(g); return g;
}
/** Laptop abierta (pantalla hacia +Z). lap.pantalla(t, texto) dibuja texto que se escribe (no es código real). lap.g = grupo. */
export function laptop(sc, x = 0, y = 0, z = 0, giro = 0) {
  const g = new THREE.Group(), neg = M.mat(0x1d1f24, { roughness: 0.4, metalness: 0.4 });
  const base = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.02, 0.25), neg); base.position.y = 0.01; g.add(base);
  const piv = new THREE.Group(); piv.position.set(0, 0.02, -0.12); piv.rotation.x = -0.25; g.add(piv);
  const tapa = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.24, 0.012), neg); tapa.position.y = 0.12; piv.add(tapa);
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 320; const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.33, 0.21), new THREE.MeshBasicMaterial({ map: tx })); scr.position.set(0, 0.12, 0.007); piv.add(scr);
  const luz = new THREE.PointLight(0x7fb8ff, 1.6, 2.2, 1.6); luz.position.set(0, 0.2, 0.25); g.add(luz);
  g.position.set(x, y, z); g.rotation.y = giro; sc.add(g);
  return { g, luz, pantalla(t, texto = 'BUSCANDO REDES...', color = '#7fd0ff') {
    const c = cv.getContext('2d'); c.fillStyle = '#06101c'; c.fillRect(0, 0, 512, 320); c.fillStyle = color; c.font = 'bold 30px monospace';
    c.fillText(texto.slice(0, Math.floor(t * 14)) + (Math.floor(t * 3) % 2 ? '_' : ''), 24, 60);
    for (let i = 0; i < 6; i++) { const w = 120 + ((Math.sin(i * 7.1 + Math.floor(t * 2)) + 1) * 150); c.fillStyle = 'rgba(127,208,255,0.35)'; c.fillRect(24, 100 + i * 34, w, 18); }
    tx.needsUpdate = true; } };
}
/** Vestíbulo de cajeros automáticos de noche (Manhattan 2003): 3 cajeros en la pared del fondo (z=-2), vidriera a la calle en z=+2.5.
 *  Los cajeros están en x = -1.4, 0, 1.4 (pantalla a y≈1.35). Afuera, calle de noche. */
export function cajeros(sc) {
  sc.background = new THREE.Color(0x06080d); sc.add(new THREE.HemisphereLight(0xdfe8ff, 0x202024, 0.45));
  const piso = M.matTex(M.TEX.concreto(), [3, 3], 0x8a8478, { roughness: 0.4 }), pared = M.matTex(M.TEX.concreto(), [2, 1], 0xc8c2b4);
  M.caja(sc, 30, 0.1, 30, 0, -0.05, 0, piso); M.caja(sc, 5, 3, 0.2, 0, 1.5, -2.2, pared); M.caja(sc, 0.2, 3, 4.6, -2.5, 1.5, 0.1, pared); M.caja(sc, 0.2, 3, 4.6, 2.5, 1.5, 0.1, pared);
  M.caja(sc, 5, 0.1, 4.6, 0, 3, 0.1, M.mat(0xe8e6e0));
  for (const x of [-1.2, 1.2]) { M.caja(sc, 1.6, 0.05, 0.25, x, 2.95, 0, emis(0xf2f6ff, 2.5), false); const l = new THREE.PointLight(0xeef4ff, 7, 7, 1.5); l.position.set(x, 2.7, 0.2); sc.add(l); }
  const cvs = [];
  for (const x of [-1.4, 0, 1.4]) { M.caja(sc, 0.9, 1.9, 0.5, x, 0.95, -1.9, M.mat(0x4a4e56, { metalness: 0.6, roughness: 0.4 }));
    M.caja(sc, 0.9, 0.35, 0.06, x, 2.05, -1.66, emis(0x2a5aa8, 0.9), false);
    M.caja(sc, 0.42, 0.32, 0.03, x, 1.38, -1.64, emis(0x4a9aff, 1.1), false); M.caja(sc, 0.35, 0.08, 0.2, x, 1.05, -1.55, M.mat(0x2a2d33));
    M.caja(sc, 0.18, 0.02, 0.04, x + 0.25, 1.2, -1.64, M.mat(0x111111), false); }
  const vid = new THREE.MeshStandardMaterial({ color: 0x9fb4c8, transparent: true, opacity: 0.18, roughness: 0.05, metalness: 0.3 });
  M.caja(sc, 5, 3, 0.05, 0, 1.5, 2.4, vid, false); M.caja(sc, 5, 0.12, 0.12, 0, 3, 2.4, M.mat(0x2a2a2a)); M.caja(sc, 0.1, 3, 0.12, 0.6, 1.5, 2.4, M.mat(0x2a2a2a));
  M.caja(sc, 60, 0.05, 20, 0, -0.02, 14, M.matTex(M.TEX.concreto(), [20, 6], 0x2a2a2e));
  for (let i = 0; i < 6; i++) { M.caja(sc, 6, 10 + (i % 3) * 3, 4, -15 + i * 6, 5, 22, M.mat(0x1a1c22)); for (let j = 0; j < 8; j++) M.caja(sc, 0.8, 1.0, 0.05, -17 + i * 6 + (j % 3) * 1.8, 2 + Math.floor(j / 3) * 3, 19.95, emis(j % 2 ? 0xffb465 : 0x2a3040, 0.6), false); }
  for (const x of [-8, 6]) { const l = new THREE.SpotLight(0xffa85a, 80, 16, 0.7, 0.6, 1.4); l.position.set(x, 6, 8); const tg = new THREE.Object3D(); tg.position.set(x, 0, 8); sc.add(tg); l.target = tg; sc.add(l); }
}
/** Patio trasero de una casa de Miami de noche: pasto, cerca de madera, pared con ventana encendida, palmera, un hueco con tierra y un barril azul.
 *  El hueco está en (0, 0); b.subir(k) saca el barril del hueco (k 0..1). */
export function patioBarril(sc) {
  M.cielo(sc, '#04060c', '#1a2236'); sc.fog = new THREE.FogExp2(0x0b0f18, 0.03);
  sc.add(new THREE.HemisphereLight(0x6f86b8, 0x1a1a14, 0.55));
  const luna = new THREE.DirectionalLight(0x9ab0ff, 1.0); luna.position.set(-8, 18, 6); luna.castShadow = true; luna.shadow.mapSize.set(2048, 2048);
  Object.assign(luna.shadow.camera, { left: -15, right: 15, top: 15, bottom: -15 }); sc.add(luna);
  M.caja(sc, 60, 0.2, 60, 0, -0.1, 0, M.matTex(M.TEX.arena(), [20, 20], 0x34482a));
  M.caja(sc, 14, 3.2, 0.3, 0, 1.6, -6, M.matTex(M.TEX.concreto(), [4, 1], 0xd8cdb8)); M.caja(sc, 14.6, 0.3, 2.0, 0, 3.25, -5.4, M.mat(0x6a4a3a));
  M.caja(sc, 1.4, 1.1, 0.06, -3, 1.7, -5.83, emis(0xffc070, 0.7), false); M.caja(sc, 1.0, 2.1, 0.06, 2.5, 1.05, -5.83, M.mat(0x4a3a2a));
  const lv = new THREE.PointLight(0xffb060, 10, 9, 1.6); lv.position.set(-3, 1.8, -4.8); sc.add(lv);
  const mad = M.mat(0x6a5038, { roughness: 1 }); for (let x = -9; x <= 9; x += 0.32) M.caja(sc, 0.28, 1.9, 0.05, x, 0.95, 7, mad);
  for (const z of [-6, 7]) for (const s of [-1, 1]) {}
  for (let z = -6; z <= 7; z += 0.32) { M.caja(sc, 0.05, 1.9, 0.28, -9, 0.95, z, mad); M.caja(sc, 0.05, 1.9, 0.28, 9, 0.95, z, mad); }
  const pal = new THREE.Group(); const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.28, 7, 8), M.mat(0x6a5a44)); tr.position.y = 3.5; pal.add(tr);
  for (let i = 0; i < 8; i++) { const h = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.04, 0.5), M.mat(0x2e4a24)); h.position.set(1.4, 0, 0); const gg = new THREE.Group(); gg.add(h); gg.rotation.set(0, i * Math.PI / 4, -0.45); gg.position.y = 7; pal.add(gg); }
  pal.position.set(6, 0, -3); pal.traverse(o => { if (o.isMesh) o.castShadow = true; }); sc.add(pal);
  const tierra = M.matTex(M.TEX.arena(), [2, 2], 0x5a4632);
  M.caja(sc, 1.6, 0.04, 1.6, 0, 0.005, 0, M.mat(0x140e08), false);
  for (let i = 0; i < 4; i++) { const m = new THREE.Mesh(new THREE.ConeGeometry(0.7 + i * 0.1, 0.6, 8), tierra); m.position.set(1.4 + (i % 2) * 0.6, 0.25, -0.6 + i * 0.4); m.castShadow = true; sc.add(m); }
  const bar = new THREE.Group(); const cuerpo = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 1.0, 24), M.mat(0x1f4fa8, { roughness: 0.5 })); cuerpo.position.y = 0.5; cuerpo.castShadow = true; bar.add(cuerpo);
  for (const y of [0.25, 0.75]) { const a = new THREE.Mesh(new THREE.TorusGeometry(0.43, 0.025, 6, 24), M.mat(0x173c80)); a.rotation.x = Math.PI / 2; a.position.y = y; bar.add(a); }
  const tapa = new THREE.Mesh(new THREE.CylinderGeometry(0.43, 0.43, 0.04, 24), M.mat(0x173c80)); tapa.position.y = 1.01; bar.add(tapa);
  bar.position.set(0, -1.05, 0); sc.add(bar);
  return { barril: bar, tapa, subir(k) { bar.position.y = K_lerp(-1.05, 0.02, k); } };
}
const K_lerp = (a, b, k) => a + (b - a) * Math.max(0, Math.min(1, k));
/** Pala en las manos (se pone en la mano derecha, apuntando abajo). pa.seguir() después de setTime. */
export function pala(sc, p) {
  const g = new THREE.Group(); const m = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 1.2, 6), M.mat(0x7a5a3a)); m.position.y = -0.5; g.add(m);
  const h = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.28, 0.02), M.mat(0x6a6a6a, { metalness: 0.7 })); h.position.y = -1.2; g.add(h); sc.add(g);
  const v = new THREE.Vector3();
  return { seguir() { p.updateMatrixWorld(true); (p.getObjectByName('Bip01_R_Hand') || p).getWorldPosition(v); g.position.copy(v); g.rotation.set(0.35, p.rotation.y, 0.2); } };
}
/** Letrero de número de puerta (placa dorada). */
export function numeroPuerta(sc, texto, x, y, z, giroY = Math.PI / 2) {
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 96; const c = cv.getContext('2d');
  c.fillStyle = '#b8964a'; c.fillRect(0, 0, 256, 96); c.fillStyle = '#1a1208'; c.font = 'bold 70px serif'; c.textAlign = 'center'; c.fillText(texto, 128, 74);
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 0.11), new THREE.MeshStandardMaterial({ map: tx, metalness: 0.6, roughness: 0.35 })); m.position.set(x, y, z); m.rotation.y = giroY; sc.add(m); return m;
}

// ===================== 18-nov: avioneta monomotor, cabina de avioneta, sala de casa de los años 50 con techo que se rompe,
// casa de pueblo de madera, pila de escombros de concreto y hueco entre escombros =====================
/** Avioneta monomotor de 6 plazas tipo Piper Malibu (blanca con franja azul, ala baja). Nariz hacia +X, largo ~8,7 m.
 *  av.mover(t) gira la hélice y hace parpadear las luces. */
export function avioneta(sc, { franja = 0x1f4fa8 } = {}) {
  const g = new THREE.Group(), bl = M.mat(0xf2f2ee, { roughness: 0.35, metalness: 0.2 }), az = M.mat(franja, { roughness: 0.4 }), vi = M.mat(0x0d1520, { roughness: 0.08, metalness: 0.8 });
  const fus = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.22, 8, 20), bl); fus.rotation.z = Math.PI / 2; fus.position.x = -0.4; fus.scale.z = 1.0; g.add(fus);
  const nariz = new THREE.Mesh(new THREE.SphereGeometry(0.62, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), bl); nariz.rotation.z = -Math.PI / 2; nariz.position.x = 3.6; nariz.scale.set(1, 1.4, 1); g.add(nariz);
  const fr = new THREE.Mesh(new THREE.CylinderGeometry(0.635, 0.3, 6.8, 20, 1, true), az); fr.rotation.z = Math.PI / 2; fr.position.set(-0.1, -0.12, 0); fr.scale.set(1, 1, 1); fr.material.side = THREE.DoubleSide; g.add(fr);
  const tapa = new THREE.Mesh(new THREE.CylinderGeometry(0.64, 0.31, 6.8, 20, 1, true, Math.PI * 0.25, Math.PI * 1.5), bl); tapa.rotation.z = Math.PI / 2; tapa.position.set(-0.1, 0, 0); g.add(tapa);
  for (let i = 0; i < 4; i++) for (const s of [1, -1]) { const w = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.3, 0.04), vi); w.position.set(1.2 - i * 0.62, 0.22, s * 0.6); g.add(w); }
  const pb = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.35, 1.0), vi); pb.position.set(2.45, 0.38, 0); pb.rotation.z = -0.5; g.add(pb);
  const ala = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.12, 13), bl); ala.position.set(0.6, -0.45, 0); g.add(ala);
  for (const s of [1, -1]) { const p = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.13, 0.25), az); p.position.set(0.6, -0.45, s * 6.4); g.add(p); }
  const est = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.08, 4.2), bl); est.position.set(-4.1, 0.1, 0); g.add(est);
  const der = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.5, 0.08), bl); der.position.set(-4.1, 0.85, 0); der.rotation.z = 0.35; g.add(der);
  const der2 = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.09), az); der2.position.set(-4.35, 1.3, 0); der2.rotation.z = 0.35; g.add(der2);
  const helice = new THREE.Group(); helice.position.set(4.25, 0, 0); g.add(helice);
  const cubo = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.4, 14), M.mat(0x2a2a2a)); cubo.rotation.z = -Math.PI / 2; helice.add(cubo);
  for (let i = 0; i < 3; i++) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.04, 1.0, 0.14), M.mat(0x1a1a1a)); p.position.y = 0.5; const h = new THREE.Group(); h.rotation.x = i * Math.PI * 2 / 3; h.add(p); helice.add(h); }
  const disco = new THREE.Mesh(new THREE.CircleGeometry(1.0, 32), new THREE.MeshBasicMaterial({ color: 0x9aa0a8, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false })); disco.rotation.y = Math.PI / 2; disco.position.x = 0.05; helice.add(disco);
  const lr = emis(0xff2020, 4), lv = emis(0x20ff50, 4), lb = emis(0xffffff, 6);
  const nl = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 8), lr); nl.position.set(0.6, -0.45, -6.55); g.add(nl);
  const nv = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 8), lv); nv.position.set(0.6, -0.45, 6.55); g.add(nv);
  const st = new THREE.Mesh(new THREE.SphereGeometry(0.1, 8, 8), lb); st.position.set(-4.5, 1.6, 0); g.add(st);
  const luzR = new THREE.PointLight(0xff3030, 3, 6), luzB = new THREE.PointLight(0xffffff, 0, 14); luzR.position.copy(nl.position); luzB.position.copy(st.position); g.add(luzR); g.add(luzB);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  sc.add(g);
  return { g, helice, mover(t) { helice.rotation.x = t * 60; const on = (t % 1.2) < 0.08; st.visible = on; luzB.intensity = on ? 40 : 0; } };
}
/** Interior de avioneta de noche (cabina estrecha, techo a 1,45 m). Pasajero sentado en (-1.15, 0, ±0.32) mirando a +X; cabina de mando adelante (+X)
 *  con instrumentos que brillan. ca.relampago(k) ilumina las ventanas; ca.gas(k) llena la cabina de una bruma gris (0..1); ca.mover(t). */
export function cabinaAvioneta(sc) {
  sc.background = new THREE.Color(0x020306);
  sc.add(new THREE.HemisphereLight(0x5d6a88, 0x0a0a0c, 0.35));
  const tap = M.mat(0x5a5650, { roughness: 0.9 }), cuero = M.mat(0x3b2f27, { roughness: 0.6 }), vi = new THREE.MeshStandardMaterial({ color: 0x0a1424, roughness: 0.05, metalness: 0.6, emissive: 0x1a2a48, emissiveIntensity: 0.3 });
  M.caja(sc, 5, 0.06, 1.3, 0.5, -0.03, 0, M.mat(0x2a2622));
  M.caja(sc, 5, 0.06, 1.3, 0.5, 1.48, 0, tap);
  for (const s of [1, -1]) { M.caja(sc, 5, 1.5, 0.06, 0.5, 0.72, s * 0.68, tap);
    for (let i = 0; i < 3; i++) { const w = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.3, 0.02), vi); w.position.set(-0.9 + i * 0.75, 1.05, s * 0.64); sc.add(w); } }
  M.caja(sc, 0.06, 1.5, 1.3, -1.9, 0.72, 0, tap);
  for (const [x, z] of [[1.15, 0.32], [1.15, -0.32], [-1.2, 0.32], [-1.2, -0.32]]) {   // asientos (respaldo hacia -X); fila del medio vacía para la cámara
    M.caja(sc, 0.5, 0.12, 0.48, x + 0.1, 0.45, z, cuero); M.caja(sc, 0.12, 0.75, 0.48, x - 0.15, 0.85, z, cuero); }
  M.caja(sc, 0.3, 0.55, 1.2, 2.25, 0.85, 0, M.mat(0x16181a));                           // tablero
  for (let i = 0; i < 6; i++) { const c = new THREE.Mesh(new THREE.CircleGeometry(0.05, 16), emis(i % 2 ? 0x40ff90 : 0xffa040, 1.2)); c.position.set(2.09, 0.9 + (i % 2) * 0.13, -0.4 + Math.floor(i / 2) * 0.22); c.rotation.y = -Math.PI / 2; sc.add(c); }
  const pv = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.45, 1.1), vi); pv.position.set(2.3, 1.25, 0); pv.rotation.z = 0.5; sc.add(pv);
  const tab = new THREE.PointLight(0xffb070, 1.6, 3, 1.5); tab.position.set(1.9, 1.0, 0); sc.add(tab);
  const dom = new THREE.PointLight(0xffe2b0, 0.9, 3, 1.6); dom.position.set(0.2, 1.38, 0); sc.add(dom);
  const flash = new THREE.PointLight(0xc8d8ff, 0, 6, 1.2); flash.position.set(0, 1.1, 1.3); sc.add(flash);
  const c = document.createElement('canvas'); c.width = c.height = 128; const gx = c.getContext('2d');
  const gr = gx.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(170,170,165,0.8)'); gr.addColorStop(1, 'rgba(170,170,165,0)'); gx.fillStyle = gr; gx.fillRect(0, 0, 128, 128);
  const tx = new THREE.CanvasTexture(c), bruma = [];
  for (let i = 0; i < 30; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, opacity: 0, depthWrite: false }));
    sp.userData.o = [-1.6 + Math.random() * 3.6, 0.3 + Math.random() * 1.0, (Math.random() - 0.5) * 1.0, Math.random() * 6]; sp.scale.setScalar(0.8 + Math.random() * 0.8); sc.add(sp); bruma.push(sp); }
  let kg = 0;
  return { relampago(k) { flash.intensity = 25 * k; vi.emissiveIntensity = 0.3 + 3 * k; }, gas(k) { kg = k; },
    mover(t) { bruma.forEach(sp => { const [x, y, z, f] = sp.userData.o; sp.position.set(x + Math.sin(t * 0.4 + f) * 0.2, y + Math.sin(t * 0.3 + f) * 0.08, z); sp.material.opacity = 0.22 * kg; }); } };
}
/** Sala de una casa de los años 50 de día: piso de madera, papel tapiz, ventana con luz, sofá con cobija (asiento en x≈0, z≈-1.2, mirando a +Z),
 *  radio de consola de madera a la derecha (x≈1.6, z≈-1.3), lámpara y cuadro. Techo a 2,6 m con un pedazo que se rompe sobre el sofá.
 *  sala.caer(t): t = segundos desde que la roca rompe el techo (negativo = todo intacto). Devuelve también la roca. */
export function salaCasa50(sc) {
  sc.background = new THREE.Color(0x0e0c0a);
  sc.add(new THREE.HemisphereLight(0xfff0d8, 0x3a2c20, 0.75));
  const pap = (() => { const cv = document.createElement('canvas'); cv.width = cv.height = 128; const g = cv.getContext('2d'); g.fillStyle = '#c9b48a'; g.fillRect(0, 0, 128, 128);
    g.fillStyle = 'rgba(120,80,50,0.25)'; for (let y = 0; y < 128; y += 32) for (let x = (y / 32 % 2) * 16; x < 128; x += 32) { g.beginPath(); g.arc(x + 8, y + 8, 5, 0, 7); g.fill(); }
    g.fillStyle = 'rgba(255,255,255,0.12)'; for (let x = 0; x < 128; x += 16) g.fillRect(x, 0, 3, 128);
    const t = new THREE.CanvasTexture(cv); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t; })();
  const pared = M.matTex(pap, [6, 3], 0xffffff), mad = M.matTex(M.TEX.ladrillo(), [10, 2], 0x7a5434), techoM = M.mat(0xe8e2d4, { roughness: 0.95 });
  M.caja(sc, 7, 0.1, 6, 0, -0.05, 0, M.mat(0x6b4a2e, { roughness: 0.6 }));
  M.caja(sc, 7, 2.6, 0.1, 0, 1.3, -2.0, pared); M.caja(sc, 0.1, 2.6, 6, -3.5, 1.3, 1, pared); M.caja(sc, 0.1, 2.6, 6, 3.5, 1.3, 1, pared);
  M.caja(sc, 7, 0.12, 0.05, 0, 0.06, -1.94, M.mat(0x4a3220));
  // techo en piezas: el pedazo sobre el sofá (x -0.2..0.6, z -1.5..-0.7) se rompe
  M.caja(sc, 7, 0.12, 4.5, 0, 2.66, 1.95, techoM); M.caja(sc, 3.3, 0.12, 1.5, -1.85, 2.66, -1.25, techoM); M.caja(sc, 2.9, 0.12, 1.5, 2.05, 2.66, -1.25, techoM);
  const tapa = M.caja(sc, 0.8, 0.12, 0.8, 0.2, 2.66, -1.1, techoM);
  M.caja(sc, 0.8, 0.12, 0.35, 0.2, 2.66, -1.8, techoM); M.caja(sc, 0.8, 0.12, 0.0, 0.2, 2.66, -0.7, techoM);
  // ventana con luz de mediodía
  M.caja(sc, 0.05, 1.2, 1.4, -3.44, 1.5, 0.3, emis(0xfff4dc, 1.4), false);
  for (const z of [-0.42, 1.02]) M.caja(sc, 0.08, 1.3, 0.08, -3.42, 1.5, z, M.mat(0xf2efe6));
  M.caja(sc, 0.08, 0.08, 1.5, -3.42, 1.5, 0.3, M.mat(0xf2efe6));
  const sol = new THREE.SpotLight(0xfff0d0, 50, 12, 0.5, 0.6, 1.2); sol.position.set(-4.5, 2.6, 0.3); sol.target.position.set(0, 0, -0.5); sc.add(sol); sc.add(sol.target); sol.castShadow = true;
  // sofá (respaldo contra la pared del fondo) con cobija
  const tela = M.mat(0x6f8a6a, { roughness: 0.9 });
  M.caja(sc, 2.2, 0.42, 0.85, 0.1, 0.21, -1.45, tela); M.caja(sc, 2.2, 0.75, 0.22, 0.1, 0.7, -1.85, tela);
  for (const x of [-1.05, 1.25]) M.caja(sc, 0.22, 0.62, 0.85, x, 0.31, -1.45, tela);
  M.caja(sc, 0.9, 0.06, 0.8, 0.45, 0.47, -1.35, M.mat(0xb03a30, { roughness: 1 }));
  // radio de consola
  const rad = new THREE.Group(); rad.position.set(1.85, 0, -1.55); sc.add(rad);
  M.caja(rad, 0.95, 0.95, 0.45, 0, 0.475, 0, M.mat(0x6a3e1e, { roughness: 0.45 }));
  M.caja(rad, 0.7, 0.4, 0.02, 0, 0.42, 0.23, M.mat(0xb8a27a, { roughness: 1 }));
  M.caja(rad, 0.5, 0.12, 0.02, 0, 0.78, 0.23, emis(0xffc070, 0.6));
  for (const x of [-0.2, 0.2]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.04, 12), M.mat(0x2a1a0a)); p.rotation.x = Math.PI / 2; p.position.set(x, 0.62, 0.24); rad.add(p); }
  // mesita, lámpara y cuadro
  M.caja(sc, 0.5, 0.55, 0.5, -1.55, 0.275, -1.5, M.mat(0x5a3a22));
  const pie = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.08, 0.45, 10), M.mat(0x8a7040, { metalness: 0.6 })); pie.position.set(-1.55, 0.78, -1.5); sc.add(pie);
  const pan = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.22, 0.25, 16, 1, true), new THREE.MeshStandardMaterial({ color: 0xf0e2c0, emissive: 0xffd8a0, emissiveIntensity: 0.4, side: THREE.DoubleSide })); pan.position.set(-1.55, 1.1, -1.5); sc.add(pan);
  M.caja(sc, 0.8, 0.6, 0.04, 0.1, 1.75, -1.93, M.mat(0x4a3220)); M.caja(sc, 0.68, 0.48, 0.02, 0.1, 1.75, -1.9, M.mat(0x7a8c9a));
  // roca, escombros, haz de luz por el hueco y polvo
  const roca = new THREE.Mesh(new THREE.DodecahedronGeometry(0.11, 1), M.mat(0x1c1a18, { roughness: 0.95 })); roca.scale.set(1.2, 0.9, 1); roca.castShadow = true; roca.visible = false; sc.add(roca);
  const brillo = brilloSprite('#ff8a30', 0.9, 0.9); roca.add(brillo);
  const yeso = []; for (let i = 0; i < 22; i++) { const m = new THREE.Mesh(new THREE.BoxGeometry(0.05 + Math.random() * 0.12, 0.03, 0.05 + Math.random() * 0.12), techoM); m.castShadow = true;
    m.userData = { x: 0.2 + (Math.random() - 0.5) * 0.7, z: -1.1 + (Math.random() - 0.5) * 0.7, d: Math.random() * 0.25, r: Math.random() * 6, f: 0.48 + Math.random() * 0.1 }; m.visible = false; sc.add(m); yeso.push(m); }
  const haz = cono(sc, 0.2, 3.6, -1.1, 3.6, 0.55, 0xfff2d0, 0); haz.rotation.z = -0.15;
  const luzH = new THREE.SpotLight(0xfff2d8, 0, 8, 0.4, 0.5, 1); luzH.position.set(0.4, 4.5, -1.1); luzH.target.position.set(0.1, 0, -1.2); sc.add(luzH); sc.add(luzH.target);
  const polvo = nubePolvo(sc, 0.2, 1.2, -1.1, 24, 1.1);
  sc.children.slice(-24).forEach(o => { if (o.material) o.material.color.setHex(0xe8e0d0); });
  // trayectoria de la roca: hueco del techo → radio (rebote) → cadera de la persona en el sofá
  const P0 = new THREE.Vector3(0.25, 2.9, -1.1), P1 = new THREE.Vector3(1.75, 0.98, -1.5), P2 = new THREE.Vector3(0.65, 0.62, -1.25);
  return { roca, tapa, P0, P1, P2, caer(t) {
    const rota = t >= 0; tapa.visible = !rota; haz.material.opacity = rota ? 0.06 : 0; luzH.intensity = rota ? 40 : 0;
    yeso.forEach(m => { const u = m.userData, k = t - u.d; m.visible = k > 0; if (k <= 0) return; m.position.set(u.x, Math.max(u.f, 2.6 - 4.9 * k * k), u.z); m.rotation.set(u.r * k, u.r * 0.5 * k, 0); });
    polvo.poner(rota ? t * 0.8 : -1);
    roca.visible = rota; if (!rota) return;
    if (t < 0.28) { const k = t / 0.28; roca.position.lerpVectors(P0, P1, k); roca.position.y = K_lerp(P0.y, P1.y, k * k); }
    else if (t < 0.62) { const k = (t - 0.28) / 0.34; roca.position.lerpVectors(P1, P2, k); roca.position.y += Math.sin(k * Math.PI) * 0.45; }
    else roca.position.copy(P2);
    roca.rotation.set(t * 9, t * 6, 0); brillo.material.opacity = Math.max(0, 0.9 - t * 1.5); } };
}
/** Casa de pueblo de madera (años 50), blanca con porche y techo a dos aguas; pasto, árboles, calle de tierra y cielo de mediodía.
 *  La casa está centrada en (0,0,-6) con el frente hacia +Z. Devuelve {techo} (grupo del techo). */
export function casaPueblo(sc, { semilla = 8 } = {}) {
  M.cielo(sc, '#5d86c0', '#d8e4ee'); sc.fog = new THREE.Fog(0xcfdce6, 50, 180);
  M.luces(sc, { sol: 2.2, cielo_: 1.1, dir: [12, 22, 10], color: 0xfff4e0 });
  M.caja(sc, 300, 0.2, 300, 0, -0.1, 0, M.matTex(M.TEX.arena(), [60, 60], 0x6f8a48));
  M.caja(sc, 300, 0.05, 6, 0, 0.01, 6, M.matTex(M.TEX.arena(), [60, 2], 0xa08a6a));
  const tabla = (() => { const cv = document.createElement('canvas'); cv.width = 64; cv.height = 64; const g = cv.getContext('2d'); g.fillStyle = '#eceae2'; g.fillRect(0, 0, 64, 64);
    g.fillStyle = 'rgba(0,0,0,0.13)'; for (let y = 0; y < 64; y += 8) g.fillRect(0, y, 64, 1.5); const t = new THREE.CanvasTexture(cv); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t; })();
  M.caja(sc, 9, 3.2, 7, 0, 1.6, -6, M.matTex(tabla, [4, 3], 0xffffff));
  const techo = new THREE.Group(); techo.position.set(0, 3.2, -6); sc.add(techo);
  const tm = M.mat(0x4a3a34, { roughness: 0.9 });
  for (const s of [1, -1]) { const p = new THREE.Mesh(new THREE.BoxGeometry(9.6, 0.15, 4.4), tm); p.position.set(0, 1.1, s * 1.85); p.rotation.x = s * 0.55; p.castShadow = true; techo.add(p); }
  const tri = new THREE.Shape(); tri.moveTo(-3.6, 0); tri.lineTo(3.6, 0); tri.lineTo(0, 2.2); tri.lineTo(-3.6, 0);
  for (const x of [-4.5, 4.5]) { const m = new THREE.Mesh(new THREE.ShapeGeometry(tri), M.matTex(tabla, [3, 1])); m.rotation.y = Math.PI / 2; m.position.set(x, 0, 0); m.material.side = THREE.DoubleSide; techo.add(m); }
  M.caja(sc, 0.5, 1.6, 0.5, 2.5, 4.3, -6.5, M.matTex(M.TEX.ladrillo(), [1, 2], 0x9a5a44));
  M.caja(sc, 9, 0.2, 2.2, 0, 0.3, -1.4, M.mat(0x8a7a6a)); M.caja(sc, 9, 0.1, 2.4, 0, 2.9, -1.4, M.mat(0xe8e6de));
  for (const x of [-4.3, -1.5, 1.5, 4.3]) M.caja(sc, 0.15, 2.6, 0.15, x, 1.6, -0.4, M.mat(0xf2f0ea));
  M.caja(sc, 1.0, 2.1, 0.06, 0, 1.25, -2.48, M.mat(0x3a4a5a));
  for (const x of [-2.8, 2.8]) { M.caja(sc, 1.4, 1.2, 0.06, x, 1.7, -2.48, M.mat(0x1a2430, { roughness: 0.1, metalness: 0.5 })); M.caja(sc, 0.3, 1.3, 0.08, x - 0.9, 1.7, -2.46, M.mat(0x2f4a3a)); M.caja(sc, 0.3, 1.3, 0.08, x + 0.9, 1.7, -2.46, M.mat(0x2f4a3a)); }
  const az = _azar(semilla);
  for (let i = 0; i < 26; i++) { const x = (az() - 0.5) * 90, z = -14 - az() * 50; if (Math.abs(x) < 7 && z > -20) continue; arbolPino(sc, x, z, 7 + az() * 7, az); }
  for (const [x, z] of [[-9, -3], [10, -4], [-14, -10]]) arbolPino(sc, x, z, 8, az);
  for (let i = 0; i < 4; i++) { const xx = -40 + i * 26 + (i > 1 ? 14 : 0); M.caja(sc, 7, 3, 6, xx, 1.5, -18, M.mat([0xd8cfc0, 0xb8c4c8, 0xe0d8b8, 0xc8b8a8][i])); M.caja(sc, 7.4, 0.3, 6.4, xx, 3.2, -18, tm); }
  return { techo };
}
function arbolPino(sc, x, z, h, az) {
  const gg = new THREE.Group(); const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.25, h, 6), M.mat(0x4a3424)); tr.position.y = h / 2; gg.add(tr);
  const co = new THREE.Mesh(new THREE.ConeGeometry(1.6 + az(), h * 0.75, 8), M.mat(0x2e4a28)); co.position.y = h * 0.7; co.castShadow = true; gg.add(co); gg.position.set(x, 0, z); sc.add(gg);
}
/** Pila de escombros de concreto (losas inclinadas con varillas) centrada en (x,z), radio r. */
export function pilaEscombros(sc, x = 0, z = 0, { r = 4, n = 40, semilla = 3, alto = 2.5 } = {}) {
  const az = _azar(semilla), con = M.matTex(M.TEX.concreto(), [1, 1], 0xa49d92), var_ = M.mat(0x5a3a2a, { metalness: 0.5, roughness: 0.6 });
  for (let i = 0; i < n; i++) { const a = az() * Math.PI * 2, d = Math.sqrt(az()) * r, y = (1 - d / r) * alto * az();
    const s = new THREE.Mesh(new THREE.BoxGeometry(0.6 + az() * 2.2, 0.18 + az() * 0.15, 0.6 + az() * 1.8), con);
    s.position.set(x + Math.cos(a) * d, y + 0.1, z + Math.sin(a) * d); s.rotation.set((az() - 0.5) * 1.2, az() * 3, (az() - 0.5) * 1.2); s.castShadow = true; s.receiveShadow = true; sc.add(s);
    if (az() < 0.4) for (let k = 0; k < 3; k++) { const v = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.8 + az(), 4), var_); v.position.copy(s.position); v.position.y += 0.3; v.rotation.set(az() * 1.5, 0, az() * 1.5); sc.add(v); } }
}
/** Hueco estrecho entre escombros (túnel de ~1,2 m de alto que avanza hacia -Z), oscuro, con losas inclinadas encima. Entrada en z≈2. */
export function huecoEscombros(sc, { largo = 10, semilla = 5 } = {}) {
  sc.background = new THREE.Color(0x020202); sc.fog = new THREE.FogExp2(0x0a0908, 0.16);
  sc.add(new THREE.HemisphereLight(0x8a8478, 0x0c0a08, 0.12));
  const az = _azar(semilla), con = M.matTex(M.TEX.concreto(), [2, 2], 0x8f897e), var_ = M.mat(0x5a3a2a, { metalness: 0.5, roughness: 0.6 });
  M.caja(sc, 4, 0.2, largo + 4, 0, -0.1, -largo / 2, M.matTex(M.TEX.arena(), [2, 6], 0x6a6258));
  for (let z = 2; z > -largo; z -= 0.9) { const h = 1.2 + az() * 0.2, inc = (az() - 0.5) * 0.3;
    const t = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.25, 1.0), con); t.position.set((az() - 0.5) * 0.3, h + 0.12, z); t.rotation.set((az() - 0.5) * 0.15, 0, inc); t.castShadow = true; t.receiveShadow = true; sc.add(t);
    for (const s of [1, -1]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.6, h + 0.3, 1.0), con); p.position.set(s * (0.75 + az() * 0.2), h / 2, z); p.rotation.set(0, 0, s * (0.1 + az() * 0.2)); p.receiveShadow = true; sc.add(p); }
    if (az() < 0.5) { const v = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.9, 4), var_); v.position.set((az() < 0.5 ? -1 : 1) * (0.6 + az() * 0.12), h - 0.35, z); v.rotation.set(az() * 0.4, 0, az() * 0.4); sc.add(v); } }
  for (let i = 0; i < 40; i++) { const r = new THREE.Mesh(new THREE.DodecahedronGeometry(0.06 + az() * 0.12, 0), con); r.position.set((az() - 0.5) * 1.2, 0.05, 2 - az() * largo); sc.add(r); }
}

// ===================== 19-nov: avión jet de 4 motores (tipo Avro RJ85/BAe 146), cerros de noche con lluvia,
// lago con ciudad mexica (Tenochtitlan), monolito redondo tallado, outback australiano con árbol DIG, taller de pintor con caballete y horno,
// cuadro con marco (imagen o pintura hecha a mano) =====================
/** Avión jet de pasajeros de ala alta con 4 motores bajo el ala y cola en T (tipo Avro RJ85). Nariz hacia +X, largo ~28 m.
 *  jet.motores(k): 1 = motores encendidos (brillo), 0 = apagados. jet.mover(t) hace parpadear las luces. */
export function avionJet(sc, { franja = 0x1f8a5a, franja2 = 0xc8202a } = {}) {
  const g = new THREE.Group(), bl = M.mat(0xf0f0ec, { roughness: 0.35, metalness: 0.25 }), vi = M.mat(0x0d1520, { roughness: 0.08, metalness: 0.8 });
  const fus = new THREE.Mesh(new THREE.CylinderGeometry(1.75, 1.75, 22, 28), bl); fus.rotation.z = Math.PI / 2; g.add(fus);
  const nariz = new THREE.Mesh(new THREE.SphereGeometry(1.75, 28, 16, 0, Math.PI * 2, 0, Math.PI / 2), bl); nariz.rotation.z = -Math.PI / 2; nariz.position.x = 11; nariz.scale.set(1, 1.6, 1); g.add(nariz);
  const cola = new THREE.Mesh(new THREE.CylinderGeometry(1.75, 0.45, 6, 28), bl); cola.rotation.z = -Math.PI / 2; cola.position.x = -14; cola.position.y = 0.45; g.add(cola);
  for (const [c, y] of [[franja, -0.55], [franja2, -0.95]]) { const f = new THREE.Mesh(new THREE.CylinderGeometry(1.77, 1.77, 21.5, 28, 1, true, Math.PI * 0.62, Math.PI * 0.12), M.mat(c, { roughness: 0.4 }));
    f.rotation.z = Math.PI / 2; f.position.set(0, y + 0.55, 0); g.add(f); const f2 = f.clone(); f2.rotation.x = Math.PI; f2.rotation.z = Math.PI / 2; g.add(f2); }
  const ventanas = [];
  for (let i = 0; i < 16; i++) for (const s of [1, -1]) { const w = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.36, 0.05), emis(0xffe2a8, 0.8)); w.position.set(7.5 - i * 1.1, 0.45, s * 1.72); g.add(w); ventanas.push(w); }
  const pb = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.6, 2.6), vi); pb.position.set(11.6, 0.75, 0); pb.rotation.z = -0.55; g.add(pb);
  const ala = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.3, 26), bl); ala.position.set(1.0, 1.7, 0); ala.rotation.y = 0; g.add(ala);
  const motores = [];
  for (const z of [-8.5, -4.6, 4.6, 8.5]) { const m = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.55, 2.6, 18), M.mat(0xdedcd6, { roughness: 0.4, metalness: 0.4 })); m.rotation.z = Math.PI / 2; m.position.set(2.6, 0.75, z); g.add(m);
    const pil = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.8, 0.2), bl); pil.position.set(2.2, 1.3, z); g.add(pil);
    const boca = new THREE.Mesh(new THREE.CircleGeometry(0.5, 18), M.mat(0x111111)); boca.rotation.y = Math.PI / 2; boca.position.set(3.92, 0.75, z); g.add(boca);
    const esc = new THREE.Mesh(new THREE.CircleGeometry(0.45, 18), emis(0xff9a40, 2)); esc.rotation.y = -Math.PI / 2; esc.position.set(1.28, 0.75, z); g.add(esc); motores.push(esc);
    const b = brilloSprite('#ff8a30', 3.2, 0.9); b.position.set(0.9, 0.75, z); g.add(b); esc.userData.b = b; }
  const deriva = new THREE.Mesh(new THREE.BoxGeometry(3.6, 5.2, 0.3), bl); deriva.position.set(-14.6, 3.3, 0); deriva.rotation.z = 0.45; g.add(deriva);
  const dc = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.6, 0.32), M.mat(franja, { roughness: 0.4 })); dc.position.set(-14.4, 3.2, 0); dc.rotation.z = 0.45; g.add(dc);
  const hz = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.22, 10), bl); hz.position.set(-16.2, 5.8, 0); g.add(hz);
  const lr = emis(0xff2020, 4), lv = emis(0x20ff50, 4), lb = emis(0xffffff, 6);
  const nl = new THREE.Mesh(new THREE.SphereGeometry(0.18, 8, 8), lr); nl.position.set(1, 1.7, -13.1); g.add(nl);
  const nv = new THREE.Mesh(new THREE.SphereGeometry(0.18, 8, 8), lv); nv.position.set(1, 1.7, 13.1); g.add(nv);
  const st = new THREE.Mesh(new THREE.SphereGeometry(0.22, 8, 8), lb); st.position.set(-17, 6, 0); g.add(st);
  const luzB = new THREE.PointLight(0xffffff, 0, 30); luzB.position.copy(st.position); g.add(luzB);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  sc.add(g);
  return { g, motores(k) { motores.forEach(m => { m.material.emissiveIntensity = 2 * k; m.userData.b.material.opacity = 0.9 * k; }); },
    cabina(k) { ventanas.forEach(w => { w.material.emissiveIntensity = 0.8 * k; }); },
    mover(t) { const on = (t % 1.3) < 0.09; st.visible = on; luzB.intensity = on ? 120 : 0; } };
}
/** Cerros oscuros con selva de noche (Andes colombianos): cerro principal en (0,0,-40). Lluvia opcional: ce.llover(t). */
export function cerrosNoche(sc, { semilla = 9, lluvia = true } = {}) {
  M.cielo(sc, '#02030a', '#11182a'); sc.fog = new THREE.FogExp2(0x0a0f1a, 0.012);
  sc.add(new THREE.HemisphereLight(0x4a5a80, 0x0a0a0c, 0.5));
  const l = new THREE.DirectionalLight(0x8094c8, 0.7); l.position.set(-20, 40, 20); sc.add(l);
  const az = _azar(semilla), verde = M.mat(0x0e1a12, { roughness: 1, flatShading: true }), verde2 = M.mat(0x14231a, { roughness: 1, flatShading: true });
  for (let i = 0; i < 26; i++) { const r = 18 + az() * 30, h = 14 + az() * 26, c = new THREE.Mesh(new THREE.ConeGeometry(r, h, 7), i % 2 ? verde : verde2);
    c.position.set(-160 + i * 13 + az() * 10, h / 2 - 4, -40 - az() * 120); c.rotation.y = az() * 3; sc.add(c); }
  const piso = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), verde); piso.rotation.x = -Math.PI / 2; piso.position.y = -4; sc.add(piso);
  for (let i = 0; i < 160; i++) { const c = [0xffc070, 0xffe0a0][i % 2]; M.caja(sc, 0.6, 0.4, 0.1, -200 + az() * 400, -3.5 + az() * 1, -240 - az() * 40, emis(c, 1.4), false); }
  let gotas = null;
  if (lluvia) { const n = 2500, pos = new Float32Array(n * 3); for (let i = 0; i < n; i++) { pos[i * 3] = (az() - 0.5) * 80; pos[i * 3 + 1] = az() * 40; pos[i * 3 + 2] = (az() - 0.5) * 80; }
    const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    gotas = new THREE.Points(gg, new THREE.PointsMaterial({ color: 0x9fb2d8, size: 0.12, transparent: true, opacity: 0.55, depthWrite: false })); sc.add(gotas); }
  return { gotas, llover(t, centro = new THREE.Vector3()) { if (!gotas) return; gotas.position.set(centro.x, centro.y - ((t * 28) % 40) + 10, centro.z); } };
}
/** Lluvia que se puede pegar a cualquier escena (alrededor de un centro). ll.mover(t, centro). */
export function lluvia(sc, { n = 2000, ancho = 30, alto = 20, op = 0.5 } = {}) {
  const az = _azar(5), pos = new Float32Array(n * 6);
  for (let i = 0; i < n; i++) { const x = (az() - 0.5) * ancho, y = az() * alto, z = (az() - 0.5) * ancho; pos.set([x, y, z, x + 0.02, y - 0.45, z], i * 6); }
  const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const l = new THREE.LineSegments(gg, new THREE.LineBasicMaterial({ color: 0xaabbdd, transparent: true, opacity: op, depthWrite: false })); sc.add(l);
  return { mover(t, c = { x: 0, y: 0, z: 0 }) { l.position.set(c.x, c.y - ((t * 14) % (alto / 2)), c.z); } };
}
/** Pedazos blancos de fuselaje regados (restos de un avión) alrededor de (x, z). Sin nada gráfico. */
export function restosFuselaje(sc, x = 0, z = 0, { n = 14, r = 6, semilla = 4 } = {}) {
  const az = _azar(semilla), bl = M.mat(0xe8e8e2, { roughness: 0.5, metalness: 0.3 }), gr = M.mat(0x1f8a5a, { roughness: 0.5 });
  for (let i = 0; i < n; i++) { const a = az() * 6.28, d = az() * r, w = 0.6 + az() * 2.6;
    const s = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, w * 0.6, 12, 1, true, 0, 0.8 + az() * 1.5), i % 5 ? bl : gr); s.material.side = THREE.DoubleSide;
    s.position.set(x + Math.cos(a) * d, 0.3 + az() * 0.6, z + Math.sin(a) * d); s.rotation.set(az() * 3, az() * 3, az() * 3); s.castShadow = true; sc.add(s); }
}
/** Disco de piedra tallado (tipo monolito de la Coyolxauhqui, sin copiar el relieve: figuras geométricas). Acostado en el piso. */
export function monolitoRedondo(sc, x = 0, y = 0, z = 0, r = 1.6) {
  const cv = document.createElement('canvas'); cv.width = cv.height = 512; const g = cv.getContext('2d');
  g.fillStyle = '#7e6c5c'; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 9000; i++) { g.fillStyle = `rgba(${60 + Math.random() * 60},${50 + Math.random() * 40},40,0.15)`; g.fillRect(Math.random() * 512, Math.random() * 512, 3, 3); }
  g.strokeStyle = 'rgba(28,20,16,0.85)'; g.lineWidth = 9; g.lineCap = 'round';
  g.beginPath(); g.arc(256, 256, 240, 0, 7); g.stroke();
  for (let i = 0; i < 9; i++) { const a = i * 0.7, rr = 60 + (i % 3) * 55; g.beginPath(); g.arc(256 + Math.cos(a) * rr, 256 + Math.sin(a) * rr, 28 + (i % 2) * 18, 0, 7); g.stroke();
    g.beginPath(); g.moveTo(256 + Math.cos(a) * (rr - 50), 256 + Math.sin(a) * (rr - 50)); g.quadraticCurveTo(256 + Math.cos(a + 0.4) * (rr + 30), 256 + Math.sin(a + 0.4) * (rr + 30), 256 + Math.cos(a + 0.8) * rr, 256 + Math.sin(a + 0.8) * rr); g.stroke(); }
  for (let i = 0; i < 24; i++) { const a = i / 24 * 6.28; g.beginPath(); g.arc(256 + Math.cos(a) * 215, 256 + Math.sin(a) * 215, 9, 0, 7); g.stroke(); }
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const lado = M.matTex(M.TEX.roca(), [3, 1], 0x9c8a78);
  const d = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.3, 48), [lado, new THREE.MeshStandardMaterial({ map: tx, color: 0x9a8878, roughness: 0.95, bumpMap: tx, bumpScale: 3 }), lado]);
  d.position.set(x, y + 0.15, z); d.castShadow = true; d.receiveShadow = true; sc.add(d); return d;
}
/** Zanja de obra en una calle de noche con lámpara de obra (para hallazgos al cavar). Zanja centrada en (0,0), 6x4 m, 1,2 m de hondo. */
export function zanjaObra(sc) {
  const con = M.matTex(M.TEX.concreto(), [8, 8], 0x55524c), tierra = M.matTex(M.TEX.arena(), [3, 3], 0x5c4632);
  for (const [w, d, x, z] of [[40, 18, 0, -11], [40, 18, 0, 11], [17, 4, -11.5, 0], [17, 4, 11.5, 0]]) M.caja(sc, w, 0.3, d, x, -0.15, z, con);
  M.caja(sc, 6, 0.2, 4, 0, -1.3, 0, tierra);
  for (const [w, d, x, z] of [[6, 0.2, 0, -2], [6, 0.2, 0, 2], [0.2, 4, -3, 0], [0.2, 4, 3, 0]]) M.caja(sc, w, 1.2, d, x, -0.7, z, tierra);
  const az = _azar(12); for (let i = 0; i < 18; i++) { const m = new THREE.Mesh(new THREE.DodecahedronGeometry(0.3 + az() * 0.4, 0), M.mat(0x4e3c2a, { flatShading: true })); m.position.set((az() - 0.5) * 7, 0.1, 2.6 + az() * 1.5); m.scale.y = 0.5; sc.add(m); }
  for (const [x, z] of [[-3.2, -2.2], [3.2, -2.2], [-3.2, 2.2], [3.2, 2.2]]) { M.caja(sc, 0.08, 1, 0.08, x, 0.5, z, M.mat(0xff7a1a));
    M.caja(sc, 0.4, 0.06, 0.06, x, 0.9, z, emis(0xff7a1a, 0.6), false); }
  const poste = M.caja(sc, 0.1, 3.5, 0.1, -3.6, 1.75, -2.8, M.mat(0x333333)); M.caja(sc, 0.6, 0.4, 0.3, -3.3, 3.4, -2.6, emis(0xfff4d8, 3), false);
  const f = new THREE.SpotLight(0xfff0d0, 110, 22, 0.75, 0.5, 1.2); f.position.set(-3.2, 3.4, -2.5); const tg = new THREE.Object3D(); tg.position.set(0.5, -1.2, 0.3); sc.add(tg); f.target = tg; f.castShadow = true; sc.add(f);
  cono(sc, -3.2, 3.4, -2.5, 5, 3, 0xfff0d0, 0.05, [0.5, 0, -0.5]);
}
/** Lago con ciudad mexica sobre una isla: pirámide doble (Templo Mayor) en (0,0), casas blancas, canales, chinampas con milpas,
 *  calzada hacia +X, volcanes al fondo y canoas. hora: 'amanecer' | 'dia'. la.mover(t) mueve canoas y agua. */
export function lagoTenochtitlan(sc, { hora = 'amanecer', semilla = 3 } = {}) {
  if (hora === 'amanecer') { M.cielo(sc, '#3a5a8c', '#f2b27a'); sc.fog = new THREE.Fog(0xe0b590, 80, 420); }
  else { M.cielo(sc, '#5b8ccf', '#d6e4f0'); sc.fog = new THREE.Fog(0xcfdce8, 90, 450); }
  sc.add(new THREE.HemisphereLight(0xdfe8ff, 0x4a5a4a, 0.9));
  const sol = new THREE.DirectionalLight(hora === 'amanecer' ? 0xffc89a : 0xfff4e0, 2.6); sol.position.set(60, 50, 40); sol.castShadow = true; sol.shadow.mapSize.set(2048, 2048);
  Object.assign(sol.shadow.camera, { left: -60, right: 60, top: 60, bottom: -60, far: 300 }); sc.add(sol);
  const agua = new THREE.Mesh(new THREE.PlaneGeometry(1200, 1200), new THREE.MeshStandardMaterial({ color: 0x3f6f78, roughness: 0.15, metalness: 0.55 })); agua.rotation.x = -Math.PI / 2; sc.add(agua);
  const az = _azar(semilla), cal = M.mat(0xe9e2d2, { roughness: 0.8 }), piedra = M.matTex(M.TEX.concreto(), [4, 4], 0xd8cdb8), tierra = M.mat(0x5d4a32, { roughness: 1 });
  const isla = new THREE.Mesh(new THREE.CylinderGeometry(55, 58, 1, 40), M.mat(0xb9a98c, { roughness: 1 })); isla.position.y = 0.2; isla.receiveShadow = true; sc.add(isla);
  // recinto y pirámide doble
  M.caja(sc, 46, 0.5, 46, 0, 0.9, 0, piedra);
  for (let k = 0; k < 5; k++) { const w = 22 - k * 3.6; M.caja(sc, w, 2.4, w * 0.9, 0, 1.15 + 1.2 + k * 2.4, -4, piedra); }
  M.caja(sc, 4.5, 12.5, 2.0, 0, 7.4, 4.5, M.mat(0xcbbca2));
  for (const [x, c] of [[-3.2, 0xb8322a], [3.2, 0x2d5fa8]]) { M.caja(sc, 4.6, 3.4, 4.2, x, 15.8, -4.5, M.mat(0xf2ead8)); M.caja(sc, 4.8, 1.2, 4.4, x, 18.1, -4.5, M.mat(c)); }
  for (const [x, z, s] of [[-15, 12, 4], [15, 12, 4], [-16, -16, 5], [16, -14, 3]]) for (let k = 0; k < s; k++) M.caja(sc, 6 - k * 1.2, 1.4, 6 - k * 1.2, x, 1.3 + k * 1.4, z, piedra);
  // casas
  for (let i = 0; i < 260; i++) { const a = az() * 6.28, d = 25 + az() * 28, x = Math.cos(a) * d, z = Math.sin(a) * d;
    if (Math.abs(z) < 3 && x > 0) continue; const w = 2 + az() * 3, h = 1.6 + az() * 1.6; const c = M.caja(sc, w, h, w * (0.8 + az() * 0.4), x, 0.7 + h / 2, z, cal); c.rotation.y = az() * 0.3;
    if (az() < 0.3) { const t = new THREE.Mesh(new THREE.BoxGeometry(w * 0.9, 0.2, w * 0.7), M.mat(0x2f6b3a)); t.position.set(x, 0.8 + h, z); sc.add(t); } }
  // canales (franjas de agua sobre la isla)
  const aguaC = new THREE.MeshStandardMaterial({ color: 0x3f6f78, roughness: 0.15, metalness: 0.55 });
  for (const a of [0.4, 1.9, 3.3, 4.6]) { const c = new THREE.Mesh(new THREE.PlaneGeometry(30, 2.2), aguaC); c.rotation.x = -Math.PI / 2; c.rotation.z = a; c.position.set(Math.cos(a) * 40, 0.72, -Math.sin(a) * 40); sc.add(c); }
  // calzada hacia +X
  M.caja(sc, 180, 0.8, 4.5, 145, 0.3, 0, piedra);
  // chinampas (fuera de la isla, hacia +Z) con milpas
  const milpa = M.mat(0x4f7a2e, { roughness: 1 }), milpa2 = M.mat(0x6b8f34, { roughness: 1 });
  const chin = [];
  for (let i = 0; i < 7; i++) for (let j = 0; j < 4; j++) { const x = -40 + i * 13, z = 66 + j * 9; const b = M.caja(sc, 10, 0.6, 6, x, 0.25, z, tierra); chin.push(b);
    for (let k = 0; k < 18; k++) { const p = new THREE.Mesh(new THREE.ConeGeometry(0.25, 1.6 + az(), 5), k % 2 ? milpa : milpa2); p.position.set(x - 4.2 + (k % 6) * 1.7, 1.3, z - 2 + Math.floor(k / 6) * 2); sc.add(p); }
    for (const s of [-1, 1]) { const ar = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.25, 6, 6), M.mat(0x5a4630)); ar.position.set(x + s * 4.6, 3, z - 2.6); sc.add(ar);
      const co = new THREE.Mesh(new THREE.ConeGeometry(0.9, 4.5, 7), M.mat(0x2e5a2a)); co.position.set(x + s * 4.6, 6.5, z - 2.6); sc.add(co); } }
  // volcanes
  for (const [x, z, r, h, nieve] of [[-220, -330, 90, 110, true], [-60, -360, 80, 95, true], [180, -340, 70, 45, false], [320, -260, 60, 40, false]]) {
    const v = new THREE.Mesh(new THREE.ConeGeometry(r, h, 24), M.mat(0x5d6a7a, { roughness: 1 })); v.position.set(x, h / 2 - 2, z); sc.add(v);
    if (nieve) { const n = new THREE.Mesh(new THREE.ConeGeometry(r * 0.28, h * 0.28, 24), M.mat(0xf4f4f4)); n.position.set(x, h - 2 - h * 0.14 + 0.5, z); sc.add(n); } }
  // canoas
  const canoas = []; const madera = M.mat(0x6a4a2a, { roughness: 0.8 });
  for (let i = 0; i < 14; i++) { const c = new THREE.Group(); const b = new THREE.Mesh(new THREE.BoxGeometry(5, 0.45, 1.0), madera); b.position.y = 0.2; c.add(b);
    const rem = new THREE.Mesh(new THREE.BoxGeometry(0.4, 1.1, 0.4), M.mat(0xe8dcc0)); rem.position.set(-1.6, 0.9, 0); c.add(rem);
    const cab = new THREE.Mesh(new THREE.SphereGeometry(0.2, 8, 8), M.mat(0x4a3020)); cab.position.set(-1.6, 1.6, 0); c.add(cab);
    for (let k = 0; k < 3; k++) { const bulto = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 6), M.mat([0xd8b040, 0x8a5a2a, 0x4f7a2e][k])); bulto.position.set(0.5 + k * 0.7, 0.55, 0); c.add(bulto); }
    const a = az() * 6.28, d = 62 + az() * 30; c.position.set(Math.cos(a) * d, 0, Math.sin(a) * d); c.rotation.y = -a; c.userData.v = 1 + az(); c.userData.a = a; c.userData.d = d; sc.add(c); canoas.push(c); }
  return { canoas, chin, mover(t) { canoas.forEach(c => { const a = c.userData.a + t * 0.004 * c.userData.v; c.position.set(Math.cos(a) * c.userData.d, Math.sin(t * 2 + a) * 0.05, Math.sin(a) * c.userData.d); c.rotation.y = -a; }); } };
}
/** Canoa sola con remero de pie (persona realista) — pon la persona tú; devuelve el grupo de la canoa (largo 5 m, eje X). */
export function canoa(sc, x = 0, z = 0) {
  const g = new THREE.Group(); const b = new THREE.Mesh(new THREE.BoxGeometry(5, 0.45, 1.0), M.mat(0x6a4a2a, { roughness: 0.8 })); b.position.y = 0.2; b.castShadow = true; g.add(b);
  for (let k = 0; k < 4; k++) { const bulto = new THREE.Mesh(new THREE.SphereGeometry(0.28, 8, 6), M.mat([0xd8b040, 0x8a5a2a, 0x4f7a2e, 0xc04a2a][k])); bulto.position.set(0.6 + k * 0.5, 0.55, (k % 2 - 0.5) * 0.3); g.add(bulto); }
  g.position.set(x, 0, z); sc.add(g); return g;
}
/** Outback australiano al atardecer (o de día): tierra roja, arroyo seco con agua quieta, eucaliptos (coolibah). Árbol grande en (0,0,-2).
 *  hora: 'tarde' | 'manana'. Devuelve {arbol, tallar(k)}: tallar(0..1) hace aparecer las letras DIG en el tronco. */
export function outback(sc, { hora = 'tarde', semilla = 6, letras = 'DIG' } = {}) {
  if (hora === 'tarde') { M.cielo(sc, '#2c3d6a', '#f08a4a'); sc.fog = new THREE.Fog(0xd48a5a, 25, 140); }
  else { M.cielo(sc, '#7fa8d8', '#f4e2c4'); sc.fog = new THREE.Fog(0xead6b8, 30, 160); }
  sc.add(new THREE.HemisphereLight(0xffe8d0, 0x5a3a24, hora === 'tarde' ? 0.7 : 1.0));
  const sol = new THREE.DirectionalLight(hora === 'tarde' ? 0xffa060 : 0xfff2dc, hora === 'tarde' ? 2.4 : 2.8);
  sol.position.set(hora === 'tarde' ? -30 : 20, hora === 'tarde' ? 10 : 30, -20); sol.castShadow = true; sol.shadow.mapSize.set(2048, 2048);
  Object.assign(sol.shadow.camera, { left: -25, right: 25, top: 25, bottom: -25 }); sc.add(sol);
  M.caja(sc, 400, 0.2, 400, 0, -0.1, 0, M.matTex(M.TEX.arena(), [60, 60], 0xb0623a));
  const agua = new THREE.Mesh(new THREE.PlaneGeometry(200, 7), new THREE.MeshStandardMaterial({ color: 0x6a5a42, roughness: 0.2, metalness: 0.5 })); agua.rotation.x = -Math.PI / 2; agua.position.set(0, 0.02, -9); sc.add(agua);
  const az = _azar(semilla), tronco = M.mat(0xcfc6b8, { roughness: 0.9 }), hoja = M.mat(0x56653e, { roughness: 1 }), hoja2 = M.mat(0x6d7a48, { roughness: 1 });
  const eucalipto = (x, z, h, grueso = 0.35) => { const g = new THREE.Group();
    const t = new THREE.Mesh(new THREE.CylinderGeometry(grueso * 0.6, grueso, h * 0.55, 9), tronco); t.position.y = h * 0.27; t.castShadow = true; g.add(t);
    for (let k = 0; k < 4; k++) { const ra = new THREE.Mesh(new THREE.CylinderGeometry(grueso * 0.2, grueso * 0.35, h * 0.45, 6), tronco); const a = k * 1.6 + az();
      ra.position.set(Math.cos(a) * h * 0.12, h * 0.6, Math.sin(a) * h * 0.12); ra.rotation.set(Math.sin(a) * 0.6, 0, -Math.cos(a) * 0.6); g.add(ra);
      for (let j = 0; j < 3; j++) { const c = new THREE.Mesh(new THREE.IcosahedronGeometry(h * 0.16 + az() * h * 0.06, 1), j % 2 ? hoja : hoja2); c.position.set(Math.cos(a) * h * 0.25 + (az() - 0.5) * 2, h * 0.82 + (az() - 0.5) * 1.5, Math.sin(a) * h * 0.25 + (az() - 0.5) * 2); c.scale.y = 0.6; c.castShadow = true; g.add(c); } }
    g.position.set(x, 0, z); sc.add(g); return g; };
  const arbol = eucalipto(0, -2, 11, 0.75);
  for (let i = 0; i < 40; i++) { const x = (az() - 0.5) * 150, z = -6 - az() * 60; if (Math.abs(x) < 6 && z > -12) continue; eucalipto(x, z, 6 + az() * 7); }
  for (let i = 0; i < 12; i++) { const x = (az() - 0.5) * 80, z = 8 + az() * 40; eucalipto(x, z, 5 + az() * 5); }
  for (let i = 0; i < 80; i++) { const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.25 + az() * 0.4, 0), M.mat(0x7a6a3a, { flatShading: true })); m.position.set((az() - 0.5) * 80, 0.12, (az() - 0.5) * 60); m.scale.y = 0.6; sc.add(m); }
  // letras talladas en el tronco (lado +Z)
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 256; const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const pl = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.62), new THREE.MeshStandardMaterial({ map: tx, transparent: true, roughness: 1, polygonOffset: true, polygonOffsetFactor: -2 })); pl.position.set(0, 1.55, -2 + 0.69); sc.add(pl);
  const tallar = k => { const g = cv.getContext('2d'); g.clearRect(0, 0, 256, 256); g.font = 'bold 120px serif'; g.textAlign = 'center';
    const n = Math.ceil(letras.length * Math.min(1, Math.max(0, k))); const s = letras.slice(0, n);
    g.fillStyle = 'rgba(120,70,40,0.95)'; g.fillText(s, 128, 170); g.fillStyle = 'rgba(60,30,15,0.6)'; g.fillText(s, 124, 166); tx.needsUpdate = true; };
  tallar(0);
  // fogata apagada / campamento: cerco de palos y restos
  for (let i = 0; i < 10; i++) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 1.4, 5), M.mat(0x5a4330)); p.position.set(4 + i * 0.6, 0.7, 2); sc.add(p); }
  M.caja(sc, 6, 0.08, 0.08, 6.7, 1.1, 2, M.mat(0x5a4330));
  for (let i = 0; i < 6; i++) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.8, 5), M.mat(0x2a2018)); p.position.set(-3 + Math.cos(i) * 0.3, 0.05, 3 + Math.sin(i) * 0.3); p.rotation.z = Math.PI / 2; p.rotation.y = i; sc.add(p); }
  return { arbol, tallar, eucalipto };
}
/** Montoncito de tierra removida (donde se enterró algo). */
export function montonTierra(sc, x, z, r = 0.8) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), M.mat(0x7a4a2a, { roughness: 1 })); m.scale.y = 0.35; m.position.set(x, 0, z); m.receiveShadow = true; sc.add(m); return m;
}
/** Pintura hecha a mano estilo maestro holandés (fondo oscuro, figuras con luz) o una imagen (url relativa a la página). */
export function texturaCuadro(url = null, { estado = 'nuevo' } = {}) {
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 400; const g = cv.getContext('2d');
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const pintar = est => {
    g.fillStyle = '#2a1e14'; g.fillRect(0, 0, 512, 400);
    if (est === 'blanco') { g.fillStyle = '#d8ccb0'; g.fillRect(0, 0, 512, 400); }
    else if (est === 'raspado') { g.fillStyle = '#8a7a60'; g.fillRect(0, 0, 512, 400); for (let i = 0; i < 300; i++) { g.fillStyle = `rgba(40,28,18,${Math.random() * 0.4})`; g.fillRect(Math.random() * 512, Math.random() * 400, 30 + Math.random() * 60, 4 + Math.random() * 8); } }
    else { const gr = g.createRadialGradient(250, 180, 10, 250, 180, 300); gr.addColorStop(0, '#9a7448'); gr.addColorStop(1, '#1a120c'); g.fillStyle = gr; g.fillRect(0, 0, 512, 400);
      g.fillStyle = '#e8e0cc'; g.fillRect(90, 250, 330, 90);
      const fig = (x, y, c) => { g.fillStyle = c; g.beginPath(); g.ellipse(x, y + 70, 48, 80, 0, 0, 7); g.fill(); g.fillStyle = '#d9b48c'; g.beginPath(); g.arc(x, y, 24, 0, 7); g.fill(); };
      fig(130, 150, '#5a6a3a'); fig(256, 130, '#2f4f8a'); fig(380, 150, '#a8803a'); g.fillStyle = '#c89a5a'; g.beginPath(); g.arc(256, 270, 16, 0, 7); g.fill(); }
    if (est === 'viejo' || est === 'nuevo') { g.strokeStyle = est === 'viejo' ? 'rgba(10,6,2,0.55)' : 'rgba(0,0,0,0)'; g.lineWidth = 1;
      for (let i = 0; i < 260; i++) { let x = Math.random() * 512, y = Math.random() * 400; g.beginPath(); g.moveTo(x, y); for (let k = 0; k < 4; k++) { x += (Math.random() - 0.5) * 30; y += (Math.random() - 0.5) * 30; g.lineTo(x, y); } g.stroke(); } }
    tx.needsUpdate = true; };
  let img = null; if (url) { img = new Image(); img.onload = () => { g.drawImage(img, 0, 0, 512, 400); tx.needsUpdate = true; }; img.src = url; } else pintar(estado);
  return { tx, pintar, imagen: () => img && img.complete && (g.drawImage(img, 0, 0, 512, 400), tx.needsUpdate = true) };
}
/** Cuadro con marco dorado colgado o sobre caballete. tex = THREE.Texture. Devuelve el grupo (cara hacia +Z). */
export function cuadroMarco(sc, tex, ancho = 1.2, alto = 0.95, { marco = true } = {}) {
  const g = new THREE.Group(); const lien = new THREE.Mesh(new THREE.PlaneGeometry(ancho, alto), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.75 })); lien.position.z = 0.02; g.add(lien);
  if (marco) { const oro = M.mat(0xb08a3a, { metalness: 0.7, roughness: 0.35 }); const e = 0.09;
    for (const [w, h, x, y] of [[ancho + 2 * e, e, 0, alto / 2 + e / 2], [ancho + 2 * e, e, 0, -alto / 2 - e / 2], [e, alto, -ancho / 2 - e / 2, 0], [e, alto, ancho / 2 + e / 2, 0]]) { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.07), oro); b.position.set(x, y, 0.02); b.castShadow = true; g.add(b); } }
  else { const b = new THREE.Mesh(new THREE.BoxGeometry(ancho, alto, 0.03), M.mat(0x8a7350)); b.position.z = -0.0; g.add(b); }
  sc.add(g); return g;
}
/** Taller de pintor de los años 30–40: piso de madera, ventana con luz, mesa con frascos de pigmento, caballete en (0, 0, -0.6) con el cuadro
 *  mirando a +Z (pintor parado en z≈0.1 mirando a -Z), horno en (2.4, 0, -1.4) con puerta que brilla (ta.horno(k)), rodillo en la mesa. */
export function tallerPintor(sc, tex) {
  sc.background = new THREE.Color(0x0c0907); sc.add(new THREE.HemisphereLight(0xffe8c8, 0x2a2018, 0.55));
  const pared = M.matTex(M.TEX.concreto(), [3, 1.5], 0x8a7c66), piso = M.matTex(M.TEX.ladrillo(), [8, 6], 0x6b4a2e);
  M.caja(sc, 9, 0.1, 8, 0, -0.05, 0, piso); M.caja(sc, 9, 3.4, 0.1, 0, 1.7, -2.5, pared); M.caja(sc, 0.1, 3.4, 8, -3.5, 1.7, 0, pared); M.caja(sc, 0.1, 3.4, 8, 3.6, 1.7, 0, pared);
  M.caja(sc, 0.05, 1.7, 1.4, -3.44, 1.9, -0.6, emis(0xdfe8ff, 0.9), false);
  for (const y of [1.3, 1.9, 2.5]) M.caja(sc, 0.06, 0.06, 1.5, -3.4, y, -0.6, M.mat(0x3a2a1a), false);
  const v = new THREE.SpotLight(0xfff2dc, 70, 12, 0.7, 0.6, 1.2); v.position.set(-3.3, 2.4, -0.6); const tv = new THREE.Object3D(); tv.position.set(0, 0.8, -0.4); sc.add(tv); v.target = tv; v.castShadow = true; sc.add(v);
  const madera = M.mat(0x4a3424, { roughness: 0.7 });
  // caballete
  const cab = new THREE.Group(); cab.position.set(0, 0, -0.6); sc.add(cab);
  for (const x of [-0.45, 0.45]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.06, 2.1, 0.06), madera); p.position.set(x, 1.0, 0); p.rotation.z = x > 0 ? -0.08 : 0.08; cab.add(p); }
  const pt = new THREE.Mesh(new THREE.BoxGeometry(0.06, 2.0, 0.06), madera); pt.position.set(0, 0.95, -0.45); pt.rotation.x = -0.25; cab.add(pt);
  const rep = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.05, 0.12), madera); rep.position.set(0, 0.85, 0.05); cab.add(rep);
  const cuadro = cuadroMarco(sc, tex, 1.1, 0.86, { marco: false }); cuadro.position.set(0, 1.32, -0.55); cuadro.rotation.x = -0.08;
  // mesa con frascos y rodillo
  M.caja(sc, 1.8, 0.05, 0.8, -1.9, 0.8, -1.6, madera); for (const [x, z] of [[-2.7, -1.9], [-1.1, -1.9], [-2.7, -1.3], [-1.1, -1.3]]) M.caja(sc, 0.05, 0.8, 0.05, x, 0.4, z, madera);
  const cols = [0x1f3c8a, 0xd8b030, 0x8a2a1a, 0xe8e0cc, 0x2a1a10, 0x4a6a3a];
  for (let i = 0; i < 9; i++) { const f = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.14 + (i % 3) * 0.05, 10), new THREE.MeshStandardMaterial({ color: cols[i % 6], roughness: 0.2, transparent: true, opacity: 0.9 })); f.position.set(-2.6 + i * 0.16, 0.9, -1.75 + (i % 2) * 0.15); sc.add(f); }
  const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.9, 16), M.mat(0x7a6a52)); rod.rotation.z = Math.PI / 2; rod.position.set(-1.7, 0.95, -1.35); sc.add(rod);
  const paleta = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.02, 16), madera); paleta.position.set(-1.3, 0.84, -1.45); sc.add(paleta);
  // horno
  M.caja(sc, 1.2, 1.3, 0.9, 2.4, 0.65, -1.6, M.mat(0x2a2a2c, { metalness: 0.6, roughness: 0.4 }));
  const puerta = M.caja(sc, 0.9, 0.7, 0.04, 2.4, 0.75, -1.13, new THREE.MeshStandardMaterial({ color: 0x1a0a04, emissive: 0xff6a1a, emissiveIntensity: 0.0 }), false);
  const brasa = new THREE.PointLight(0xff7a2a, 0, 4, 1.4); brasa.position.set(2.4, 0.8, -0.9); sc.add(brasa);
  M.caja(sc, 0.15, 0.6, 0.15, 2.7, 1.6, -1.8, M.mat(0x2a2a2c)); 
  const foco = new THREE.PointLight(0xffd9a0, 4, 6, 1.5); foco.position.set(0.6, 2.8, 0.6); sc.add(foco);
  M.caja(sc, 0.25, 0.08, 0.25, 0.6, 3.0, 0.6, emis(0xfff0c8, 2), false);
  return { cuadro, rodillo: rod, horno(k) { puerta.material.emissiveIntensity = 1.2 * k; brasa.intensity = 6 * k; } };
}
/** Sala de museo: pared oscura con un cuadro iluminado por un foco (cuadro en (0, 1.6, -2.4) mirando a +Z), piso de madera y banca. */
export function salaMuseo(sc, tex, { ancho = 1.6, alto = 1.25 } = {}) {
  sc.background = new THREE.Color(0x0a0a0c); sc.add(new THREE.HemisphereLight(0xfff0e0, 0x201812, 0.35));
  M.caja(sc, 14, 0.1, 10, 0, -0.05, 0, M.matTex(M.TEX.ladrillo(), [10, 8], 0x6a4a30)); M.caja(sc, 14, 4.2, 0.1, 0, 2.1, -2.5, M.mat(0x5a1e22, { roughness: 0.95 }));
  M.caja(sc, 0.1, 4.2, 10, -5, 2.1, 0, M.mat(0x5a1e22, { roughness: 0.95 }));
  const c = cuadroMarco(sc, tex, ancho, alto); c.position.set(0, 1.65, -2.42);
  const f = new THREE.SpotLight(0xfff0d8, 90, 8, 0.45, 0.5, 1.3); f.position.set(0, 3.6, -0.8); const tg = new THREE.Object3D(); tg.position.set(0, 1.6, -2.4); sc.add(tg); f.target = tg; f.castShadow = true; sc.add(f);
  for (const x of [-3.2, 3.2]) { const c2 = cuadroMarco(sc, texturaCuadro(null, { estado: 'viejo' }).tx, 0.9, 1.1); c2.position.set(x, 1.7, -2.42); }
  M.caja(sc, 2.0, 0.08, 0.5, 0, 0.45, 1.4, M.mat(0x2a1a10)); for (const x of [-0.8, 0.8]) M.caja(sc, 0.08, 0.45, 0.4, x, 0.22, 1.4, M.mat(0x2a1a10));
  return { cuadro: c };
}

// ======================= 20-nov: lancha de pescador, isla tropical, cabaña de troncos, tortuga marina =======================
/** Lancha de pescador de fibra (7 m, blanca) con hielera grande. Frente hacia +X. Pon a la gente con lancha.add(p) (piso en y=0.16).
 *  Para que flote: flotarEnMar(mar, lancha, x, z, t). */
export function lanchaPescador(sc, { hielera = true } = {}) {
  const g = bote(sc, 0xdcd8cc);
  if (hielera) { const h = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.75, 0.9), M.mat(0xf2f2ee, { roughness: 0.5 })); h.position.set(-1.3, 0.5, 0); h.castShadow = true; g.add(h); }
  return g;
}
/** Hace flotar un grupo sobre marNoche() siguiendo las olas (inclina según la pendiente). */
export function flotarEnMar(mar, g, x, z, t, fuerza = 1, hundir = 0.36) {
  const h = mar.alto(x, z, t), hx = mar.alto(x + 2, z, t) - mar.alto(x - 2, z, t), hz = mar.alto(x, z + 0.8, t) - mar.alto(x, z - 0.8, t);
  g.position.set(x, h * 0.85 - hundir, z); g.rotation.z = Math.atan2(hx, 4) * fuerza; g.rotation.x = -Math.atan2(hz, 1.6) * fuerza * 0.6;
}
/** Isla tropical de arena blanca con palmeras (atolón), centro en (0,0,-48), radio ~40. Úsala con marNoche({tormenta:false}) en colores de día. */
export function islaTropical(sc, { semilla = 3, palmeras = 26 } = {}) {
  const arena = M.mat(0xe9dcb4, { roughness: 1 });
  const isla = new THREE.Mesh(new THREE.CylinderGeometry(40, 46, 2, 48), arena); isla.position.set(0, -0.6, -48); isla.receiveShadow = true; sc.add(isla);
  const az = _azar(semilla), tronco = M.mat(0x7a5e40, { roughness: 1 }), hoja = M.mat(0x2f7a2a, { roughness: 0.9, side: THREE.DoubleSide });
  for (let i = 0; i < palmeras; i++) { const g = new THREE.Group(), h = 6 + az() * 5;
    const t = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.25, h, 7), tronco); t.position.y = h / 2; t.rotation.z = (az() - 0.5) * 0.3; t.castShadow = true; g.add(t);
    for (let k = 0; k < 7; k++) { const f = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 0.7), hoja); f.position.set(Math.cos(k) * 1.4, h - 0.2, Math.sin(k) * 1.4); f.rotation.set(-0.5, -k, 0.4); f.castShadow = true; g.add(f); }
    g.position.set((az() - 0.5) * 60, 0.4, -14 - az() * 40); sc.add(g); }
  return isla;
}
/** Cabaña de troncos (Siberia, pueblo de 1900) con banca adelante. Pared de troncos en z=-2.2 (mira a +Z), banca en (-0.6, 1.35). */
export function cabanaTroncos(sc) {
  const tr = M.mat(0x6a4a32, { roughness: 1 });
  for (let i = 0; i < 9; i++) { const l = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 6, 10), tr); l.rotation.z = Math.PI / 2; l.position.set(0, 0.16 + i * 0.3, -2.2); l.castShadow = true; l.receiveShadow = true; sc.add(l); }
  M.caja(sc, 1.0, 1.2, 0.05, 1.4, 1.5, -1.95, M.mat(0x1c1c22), false);
  const techo = new THREE.Mesh(new THREE.ConeGeometry(4.6, 1.8, 4), M.mat(0x3a2a20)); techo.rotation.y = Math.PI / 4; techo.scale.z = 0.7; techo.position.set(0, 3.6, -3.6); sc.add(techo);
  M.caja(sc, 6, 2.8, 3, 0, 1.4, -3.6, tr);
  M.caja(sc, 1.8, 0.08, 0.45, -0.6, 0.5, 1.35, M.mat(0x7a5a3e)); for (const x of [-1.3, 0.1]) M.caja(sc, 0.08, 0.5, 0.4, x, 0.25, 1.35, M.mat(0x7a5a3e));
}
/** Tortuga marina sencilla (caparazón, cabeza y aletas). Cabeza hacia +X. */
export function tortugaMarina(sc) {
  const g = new THREE.Group(), cv = M.mat(0x4a5a2c, { roughness: 0.7 }), pi = M.mat(0x7a7a52, { roughness: 0.8 });
  const cap = new THREE.Mesh(new THREE.SphereGeometry(0.45, 20, 12), cv); cap.scale.set(1.2, 0.35, 0.9); g.add(cap);
  const cab = new THREE.Mesh(new THREE.SphereGeometry(0.13, 12, 10), pi); cab.position.set(0.6, 0, 0); g.add(cab);
  for (const [x, z, r] of [[0.25, 0.42, 0.5], [0.25, -0.42, -0.5], [-0.35, 0.3, 0.3], [-0.35, -0.3, -0.3]]) { const a = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.04, 0.16), pi); a.position.set(x, -0.02, z); a.rotation.y = r; g.add(a); }
  sc.add(g); return g;
}

// ======================= 21-nov: crucero de guerra 1945, náufragos con chaleco, mar de día, banco de arena con torre de piedras y humo,
// galeón, espacio (estrellas, Tierra, Luna), nave Apolo (módulo de mando + servicio + lunar), cabina de cápsula, avión de 4 hélices (Lancastrian),
// glaciar de los Andes, motor de avión viejo =======================
/** Colores de día para marNoche() (llamar justo después): cielo celeste, agua azul, sol fuerte. */
export function marDia(sc, mar, { sol = 2.2 } = {}) {
  M.cielo(sc, '#5d8fc4', '#cfe0ec'); sc.fog = new THREE.FogExp2(0xbcd2e2, 0.006);
  mar.agua.material.color.setHex(0x1d5a7a); mar.agua.material.roughness = 0.35;
  const s = new THREE.DirectionalLight(0xfff4e0, sol); s.position.set(30, 60, 20); sc.add(s);
  sc.add(new THREE.HemisphereLight(0xdfefff, 0x2a4a5a, 1.0)); return s;
}
/** Crucero pesado de la Segunda Guerra (gris, 2 chimeneas, torres de cañones). Proa hacia +X, largo ~60 m.
 *  cr.fuego(k) enciende el incendio del costado; cr.mover(t) mueve llamas y humo. Inclínalo/húndelo con cr.g. */
export function crucero(sc) {
  const g = new THREE.Group(), gr = M.mat(0x6c7277, { roughness: 0.7, metalness: 0.2 }), gr2 = M.mat(0x585e63, { roughness: 0.7 }), os = M.mat(0x2b2f33, { roughness: 0.8 });
  const add = (w, h, d, x, y, z, mm) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; g.add(b); return b; };
  add(50, 5, 6.4, -3, 0, 0, gr); add(50, 1.2, 6.4, -3, -2.6, 0, os);
  const proa = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 3.2, 12, 4, 1), gr); proa.rotation.z = -Math.PI / 2; proa.rotation.x = Math.PI / 4; proa.scale.set(1, 1, 0.42 / 0.42); proa.position.set(28, 0, 0); g.add(proa);
  const popa = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.2, 5, 16, 1, false, 0, Math.PI), gr); popa.rotation.x = Math.PI / 2; popa.rotation.z = Math.PI / 2; popa.position.set(-28, 0, 0); popa.scale.set(1, 1, 0.99); g.add(popa);
  add(62, 0.3, 6.5, 0, 2.6, 0, gr2);
  add(10, 4, 4.4, 8, 4.7, 0, gr); add(6, 3, 3.6, 8.6, 8.2, 0, gr); add(3, 2, 3, 9, 10.7, 0, gr2); add(6.2, 0.6, 1, 9.2, 8.6, 1.9, os);
  add(8, 3.4, 4, -6, 4.4, 0, gr); add(4, 2.2, 3, -6.5, 7.2, 0, gr);
  for (const x of [1, -3]) { const ch = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.3, 7, 16), gr); ch.position.set(x, 7, 0); ch.rotation.z = 0.08; g.add(ch); const tp = new THREE.Mesh(new THREE.CylinderGeometry(1.12, 1.12, 0.5, 16), os); tp.position.set(x + 0.28, 10.4, 0); g.add(tp); }
  const mastil = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.2, 12, 8), os); mastil.position.set(7, 15, 0); g.add(mastil); add(0.2, 0.2, 5, 7, 18, 0, os);
  for (const [x, s] of [[19, 1], [14, 1], [-15, -1]]) { const t = new THREE.Mesh(new THREE.CylinderGeometry(2, 2.2, 1.6, 18), gr); t.position.set(x, 3.6, 0); g.add(t);
    for (const z of [-0.6, 0, 0.6]) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.2, 7, 8), os); c.rotation.z = Math.PI / 2; c.position.set(x + s * 4.5, 3.8, z); g.add(c); } }
  for (let i = 0; i < 14; i++) for (const s of [1, -1]) add(0.5, 0.4, 0.05, -20 + i * 3, 1.2, s * 3.22, emis(0xffd59a, 0.25));
  const llamas = [], humo = [];
  for (let i = 0; i < 14; i++) { const b = brilloSprite(i % 3 ? '#ff7a20' : '#ffd060', 4 + (i % 4), 0.9); b.userData.o = [14 + (i % 5) * 1.6, 1 + (i % 4) * 1.1, 3.6]; g.add(b); llamas.push(b); }
  const c = document.createElement('canvas'); c.width = c.height = 128; const gx = c.getContext('2d'); const grd = gx.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, 'rgba(40,36,34,0.9)'); grd.addColorStop(1, 'rgba(40,36,34,0)'); gx.fillStyle = grd; gx.fillRect(0, 0, 128, 128); const tx = new THREE.CanvasTexture(c);
  for (let i = 0; i < 26; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, opacity: 0, depthWrite: false })); sp.userData.f = i / 26; g.add(sp); humo.push(sp); }
  const luz = new THREE.PointLight(0xff8a30, 0, 90, 1.4); luz.position.set(16, 4, 6); g.add(luz);
  g.traverse(o => { if (o.isMesh) o.receiveShadow = true; }); sc.add(g);
  let kf = 0;
  return { g, fuego(k) { kf = k; }, mover(t) {
    llamas.forEach((b, i) => { const [x, y, z] = b.userData.o; b.position.set(x + Math.sin(t * 5 + i) * 0.3, y + kf * (1 + Math.abs(Math.sin(t * 7 + i * 2))), z); b.material.opacity = 0.9 * kf; b.visible = kf > 0.01; });
    humo.forEach((sp, i) => { const f = (sp.userData.f + t * 0.12) % 1; sp.position.set(16 - f * 14, 4 + f * 22, 3 + f * 3); sp.scale.setScalar(4 + f * 16); sp.material.opacity = 0.75 * kf * (1 - f); });
    luz.intensity = kf * (900 + 300 * Math.sin(t * 17)); } };
}
/** Persona flotando en el mar con chaleco salvavidas de corcho (kapok). Devuelve la persona; muévela con flotar(mar, p, x, z, t). */
export async function naufrago(sc, quien, anim = 'm_idle_nervous_01.max.fbx', giro = 0, color = 0xa8945e) {
  const p = await persona(sc, quien, anim, 0, 0, giro);
  const ch = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.11, 10, 20), M.mat(color, { roughness: 0.9 })); ch.rotation.x = Math.PI / 2; ch.scale.set(1.15, 0.85, 1.6); ch.position.y = 1.22; p.add(ch);
  const ch2 = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.3, 0.26), M.mat(color, { roughness: 0.9 })); ch2.position.y = 1.32; p.add(ch2);
  return p;
}
/** Hace flotar a un náufrago: la superficie del mar le queda a la altura del pecho (hundir ~1.15). */
export function flotar(mar, p, x, z, t, hundir = 1.12) { p.position.set(x, mar.alto(x, z, t) - hundir, z); p.rotation.z = Math.sin(t * 1.3 + x) * 0.06; }
/** Columna de humo (señales, incendios). h.mover(t); h.g se puede mover. color oscuro o claro. */
export function columnaHumo(sc, { n = 30, alto = 14, ancho = 3, color = '200,200,195', op = 0.6 } = {}) {
  const g = new THREE.Group(); sc.add(g);
  const [r, gg, bb] = color.split(',').map(Number), col = new THREE.Color(r / 255, gg / 255, bb / 255);
  const geo = new THREE.IcosahedronGeometry(1, 2);
  const ps = []; for (let i = 0; i < n; i++) { const sp = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: col, transparent: true, opacity: 0, depthWrite: false })); sp.userData.f = i / n; g.add(sp); ps.push(sp); }
  return { g, mover(t, k = 1) { ps.forEach((sp, i) => { const f = (sp.userData.f + t * 0.1) % 1; sp.position.set(Math.sin(i * 2.1) * 0.3 + f * ancho * 0.6, f * alto, Math.cos(i * 1.7) * 0.3);
    sp.scale.setScalar(0.4 + f * ancho * 0.8); sp.material.opacity = op * 0.55 * k * Math.min(1, f * 6) * (1 - f); }); } };
}
/** Banco de arena casi a ras del mar (sin árboles), centro en (0,0,0), ~30 x 12 m. Con restos de madera, caparazones y piedras. */
export function bancoArena(sc, { semilla = 4 } = {}) {
  const az = _azar(semilla), arena = M.matTex(M.TEX.arena(), [6, 3], 0xf0e2bc);
  const b = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 16), arena); b.scale.set(16, 0.9, 6); b.position.y = -0.45; b.receiveShadow = true; sc.add(b);
  const madera = M.mat(0x6b5038, { roughness: 1 });
  for (let i = 0; i < 9; i++) { const t = new THREE.Mesh(new THREE.BoxGeometry(1.5 + az() * 2.5, 0.12, 0.25), madera); t.position.set(-10 + az() * 20, 0.42, -3 + az() * 6); t.rotation.y = az() * 3; t.castShadow = true; sc.add(t); }
  const roca = M.matTex(M.TEX.roca(), [1, 1], 0xb8b0a0);
  for (let i = 0; i < 14; i++) { const r = new THREE.Mesh(new THREE.DodecahedronGeometry(0.2 + az() * 0.3), roca); r.position.set(-12 + az() * 24, 0.4, -4 + az() * 8); r.castShadow = true; sc.add(r); }
  return b;
}
/** Caparazón de tortuga boca arriba (sirve de depósito de agua). */
export function caparazon(sc, x, z, y = 0.42, r = 0.45) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 10, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), M.mat(0x5a4a2a, { roughness: 0.6, side: THREE.DoubleSide }));
  m.scale.set(1.2, 0.5, 1); m.position.set(x, y + r * 0.5, z); m.castShadow = true; sc.add(m);
  const agua = new THREE.Mesh(new THREE.CircleGeometry(r * 0.95, 20), M.mat(0x6a9ab0, { roughness: 0.1, metalness: 0.3 })); agua.rotation.x = -Math.PI / 2; agua.scale.set(1.2, 1, 1); agua.position.set(x, y + r * 0.35, z); sc.add(agua);
  return { m, agua, nivel(k) { agua.position.y = y + r * (0.05 + 0.4 * k); agua.visible = k > 0.02; } };
}
/** Torre de piedras y corales (refugio de náufragos), alto ~2.6 m, en (x, z). */
export function torrePiedras(sc, x = 0, z = 0, { alto = 2.6, semilla = 9 } = {}) {
  const az = _azar(semilla), m1 = M.matTex(M.TEX.roca(), [1, 1], 0xcfc6b0), m2 = M.matTex(M.TEX.roca(), [1, 1], 0xe0d6c4);
  for (let y = 0; y < alto; y += 0.32) { const r = 1.3 - y * 0.25, n = Math.max(5, Math.round(r * 9));
    for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2 + y; if (y > 0.6 && Math.abs(Math.sin(a * 0.5 - 0.9)) < 0.15) continue;
      const p = new THREE.Mesh(new THREE.DodecahedronGeometry(0.2 + az() * 0.12), az() > 0.5 ? m1 : m2); p.position.set(x + Math.cos(a) * r, 0.45 + y, z + Math.sin(a) * r); p.rotation.set(az() * 3, az() * 3, 0); p.castShadow = true; p.receiveShadow = true; sc.add(p); } }
}
/** Galeón español del siglo XVI (casco de madera, 3 mástiles con velas). Proa hacia +X, largo ~30 m. */
export function galeon(sc) {
  const g = new THREE.Group(), ma = M.mat(0x5a3a22, { roughness: 0.9 }), ma2 = M.mat(0x3a2414, { roughness: 0.9 }), vela = M.mat(0xe8dfc8, { roughness: 1, side: THREE.DoubleSide });
  const add = (w, h, d, x, y, z, mm) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; g.add(b); return b; };
  add(22, 4, 7, 0, 1, 0, ma); add(22, 1, 7.2, 0, -0.8, 0, ma2); add(7, 4, 7, -9, 4.5, 0, ma); add(4, 2.5, 6, 9, 3.6, 0, ma);
  const proa = new THREE.Mesh(new THREE.ConeGeometry(3.6, 7, 4), ma); proa.rotation.z = -Math.PI / 2; proa.rotation.x = Math.PI / 4; proa.position.set(14, 1.4, 0); g.add(proa);
  for (const [x, h, w] of [[6, 18, 9], [-1, 21, 11], [-8, 15, 7]]) { const m = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.28, h, 8), ma2); m.position.set(x, 2 + h / 2, 0); g.add(m);
    for (const [y, k] of [[0.45, 1], [0.78, 0.7]]) { const v = new THREE.Mesh(new THREE.PlaneGeometry(w * k * 0.75, h * 0.28, 6, 4), vela); const pa = v.geometry.attributes.position; for (let i = 0; i < pa.count; i++) pa.setZ(i, Math.cos(pa.getX(i) / (w * k * 0.4)) * 0.8);
      v.rotation.y = Math.PI / 2; v.position.set(x + 0.4, 2 + h * y, 0); g.add(v); } }
  sc.add(g); return g;
}
/** Fondo de espacio: estrellas + Tierra + Luna. Devuelve {tierra, luna}. Tierra con océanos, nubes y lado de noche (luz del sol desde +X). */
export function espacio(sc, { tierra = [0, 0, -400], rT = 60, luna = null, rL = 16 } = {}) {
  sc.background = new THREE.Color(0x000000);
  const n = 3000, p = new Float32Array(n * 3), az = _azar(3);
  for (let i = 0; i < n; i++) { const u = az() * 2 - 1, a = az() * 6.283, r = 900; p.set([Math.sqrt(1 - u * u) * Math.cos(a) * r, u * r, Math.sqrt(1 - u * u) * Math.sin(a) * r], i * 3); }
  const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.BufferAttribute(p, 3));
  sc.add(new THREE.Points(gg, new THREE.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, fog: false })));
  const sol = new THREE.DirectionalLight(0xfff6e8, 3.2); sol.position.set(300, 80, 120); sc.add(sol); sc.add(new THREE.AmbientLight(0x404a58, 0.6));
  const c = document.createElement('canvas'); c.width = 1024; c.height = 512; const g = c.getContext('2d');
  g.fillStyle = '#1b4a8a'; g.fillRect(0, 0, 1024, 512); const a2 = _azar(8);
  for (let i = 0; i < 26; i++) { g.fillStyle = ['#5a7a3a', '#8a7a4a', '#4a6a34'][i % 3]; g.beginPath(); const cx = a2() * 1024, cy = 90 + a2() * 330; for (let k = 0; k < 12; k++) { const an = k / 12 * 6.283, rr = 30 + a2() * 70; g.lineTo(cx + Math.cos(an) * rr * 1.4, cy + Math.sin(an) * rr); } g.fill(); }
  g.fillStyle = 'rgba(255,255,255,0.85)'; for (let i = 0; i < 160; i++) { g.beginPath(); g.ellipse(a2() * 1024, a2() * 512, 10 + a2() * 60, 4 + a2() * 10, a2() * 0.6, 0, 6.283); g.fill(); }
  g.fillStyle = '#ffffff'; g.fillRect(0, 0, 1024, 30); g.fillRect(0, 482, 1024, 30);
  const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace;
  const T = new THREE.Mesh(new THREE.SphereGeometry(rT, 64, 40), new THREE.MeshStandardMaterial({ map: tx, roughness: 0.7 })); T.position.set(...tierra); sc.add(T);
  const at = new THREE.Mesh(new THREE.SphereGeometry(rT * 1.025, 64, 40), new THREE.MeshBasicMaterial({ color: 0x6fb0ff, transparent: true, opacity: 0.18, side: THREE.BackSide, blending: THREE.AdditiveBlending, depthWrite: false })); at.position.copy(T.position); sc.add(at);
  let L = null;
  if (luna) { const cl = document.createElement('canvas'); cl.width = 512; cl.height = 256; const gl = cl.getContext('2d'); gl.fillStyle = '#9a968e'; gl.fillRect(0, 0, 512, 256);
    for (let i = 0; i < 220; i++) { gl.fillStyle = `rgba(${a2() > 0.5 ? '60,58,55' : '190,186,178'},${0.2 + a2() * 0.3})`; gl.beginPath(); gl.arc(a2() * 512, a2() * 256, 2 + a2() * 18, 0, 6.283); gl.fill(); }
    const tl = new THREE.CanvasTexture(cl); tl.colorSpace = THREE.SRGBColorSpace; L = new THREE.Mesh(new THREE.SphereGeometry(rL, 48, 32), new THREE.MeshStandardMaterial({ map: tl, roughness: 1 })); L.position.set(...luna); sc.add(L); }
  return { tierra: T, luna: L, sol };
}
/** Nave Apolo: módulo de mando (cono), módulo de servicio (cilindro con motor) y módulo lunar acoplado en la punta. Eje hacia +X (punta del cono +X).
 *  nave.explotar(k): 0..1 arranca un panel del módulo de servicio con chispas y una nube de gas que se escapa; nave.mover(t). */
export function naveApolo(sc, { lunar = true } = {}) {
  const g = new THREE.Group(), pl = M.mat(0xe4e4e0, { roughness: 0.35, metalness: 0.35 }), bl = M.mat(0xf2f2ee, { roughness: 0.55, metalness: 0.1 }), os = M.mat(0x2a2a2a, { roughness: 0.6 });
  const cm = new THREE.Mesh(new THREE.ConeGeometry(1.95, 3.4, 40), pl); cm.rotation.z = -Math.PI / 2; cm.position.x = 1.7; g.add(cm);
  for (const z of [0.9, -0.9]) { const v = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.25, 0.05), M.mat(0x0a1018, { metalness: 0.9, roughness: 0.1 })); v.position.set(1.2, 0.55, z * 1.0); v.lookAt(new THREE.Vector3(5, 3, z * 4)); g.add(v); }
  const sm = new THREE.Mesh(new THREE.CylinderGeometry(1.95, 1.95, 7.4, 40), bl); sm.rotation.z = Math.PI / 2; sm.position.x = -3.7; g.add(sm);
  for (let i = 0; i < 6; i++) { const f = new THREE.Mesh(new THREE.BoxGeometry(7.4, 0.04, 0.06), M.mat(0xb8b8b4)); const a = i / 6 * Math.PI * 2; f.position.set(-3.7, Math.cos(a) * 1.96, Math.sin(a) * 1.96); f.rotation.x = a; g.add(f); }
  const tob = new THREE.Mesh(new THREE.ConeGeometry(1.25, 3.4, 30, 1, true), M.mat(0x3a3a3a, { side: THREE.DoubleSide, metalness: 0.6, roughness: 0.4 })); tob.rotation.z = -Math.PI / 2; tob.position.x = -8.9; g.add(tob);
  const ant = new THREE.Group(); ant.position.set(-7, -2.2, 0); g.add(ant); for (let i = 0; i < 4; i++) { const d = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.06, 16), bl); d.rotation.z = Math.PI / 2; d.position.set(0, -0.6, (i - 1.5) * 0.8); ant.add(d); }
  const panel = new THREE.Mesh(new THREE.CylinderGeometry(1.98, 1.98, 3, 20, 1, true, -0.5, 1.0), bl); panel.material = bl.clone(); panel.material.side = THREE.DoubleSide; panel.rotation.z = Math.PI / 2; panel.position.x = -3.7; g.add(panel);
  const hueco = new THREE.Mesh(new THREE.CylinderGeometry(1.9, 1.9, 2.9, 20, 1, true, -0.5, 1.0), M.mat(0x1a1410, { side: THREE.DoubleSide, roughness: 1 })); hueco.rotation.z = Math.PI / 2; hueco.position.x = -3.7; g.add(hueco);
  if (lunar) { const lm = new THREE.Group(); lm.position.set(3.7, 0, 0); g.add(lm);
    const oro = M.mat(0xd8b048, { roughness: 0.4, metalness: 0.4 }), gris = M.mat(0xb8b8b2, { roughness: 0.6, metalness: 0.2 });
    const asc = new THREE.Mesh(new THREE.DodecahedronGeometry(1.6, 0), gris); asc.scale.set(0.8, 1, 1.1); asc.position.x = 0.8; lm.add(asc);
    const des = new THREE.Mesh(new THREE.CylinderGeometry(2.1, 2.1, 1.8, 8), oro); des.rotation.z = Math.PI / 2; des.position.x = 2.9; lm.add(des);
    for (let i = 0; i < 4; i++) { const a = i / 4 * Math.PI * 2 + Math.PI / 4; const pata = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 3.2, 6), oro); pata.position.set(3.6, Math.cos(a) * 2.4, Math.sin(a) * 2.4); pata.rotation.set(a, 0, Math.PI / 2 - 0.5 * Math.sign(Math.cos(a) || 1) * 0); lm.add(pata);
      const pie = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.08, 12), oro); pie.position.set(5.1, Math.cos(a) * 2.9, Math.sin(a) * 2.9); pie.rotation.z = Math.PI / 2; lm.add(pie); } }
  const c = document.createElement('canvas'); c.width = c.height = 128; const gx = c.getContext('2d'); const grd = gx.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, 'rgba(235,240,255,0.95)'); grd.addColorStop(1, 'rgba(235,240,255,0)'); gx.fillStyle = grd; gx.fillRect(0, 0, 128, 128); const tx = new THREE.CanvasTexture(c);
  const gas = []; for (let i = 0; i < 70; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, opacity: 0, depthWrite: false, fog: false })); sp.userData.o = [Math.random(), (Math.random() - 0.5) * 1.6, (Math.random() - 0.5) * 1.6, Math.random() * 2 - 1]; sc.add(sp); gas.push(sp); }
  const chispa = brilloSprite('#ffd8a0', 6, 1); chispa.visible = false; g.add(chispa); chispa.position.set(-3.7, 2.2, 0.2);
  const luz = new THREE.PointLight(0xffc890, 0, 40, 1.4); luz.position.set(-3.7, 3, 0); g.add(luz);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; }); sc.add(g);
  let ke = 0, t0 = 0;
  return { g, explotar(k) { ke = k; },
    mover(t) { const v = new THREE.Vector3(-3.7, 2.1, 0); g.localToWorld(v); const up = new THREE.Vector3(0, 1, 0).applyQuaternion(g.quaternion);
      panel.visible = ke < 0.15; if (ke >= 0.15) { panel.position.set(-3.7 + 0, 2 + (ke - 0.15) * 10, 0); panel.visible = true; panel.rotation.x = (ke - 0.15) * 4; panel.material.transparent = true; panel.material.opacity = Math.max(0, 1 - (ke - 0.15) * 1.4); }
      chispa.visible = ke > 0.1 && ke < 0.4; chispa.scale.setScalar(4 + 10 * Math.max(0, 0.4 - ke)); luz.intensity = (ke > 0.1 && ke < 0.45) ? 900 * (0.45 - ke) : 0;
      gas.forEach((sp, i) => { const [f0, a, b, d] = sp.userData.o; const f = ke > 0.12 ? ((f0 + t * 0.25) % 1) : 0;
        sp.position.copy(v).addScaledVector(up, f * 14).add(new THREE.Vector3(a * f * 6 + d * f * 3, 0, b * f * 6)); sp.scale.setScalar(0.6 + f * 6); sp.material.opacity = ke > 0.12 ? 0.55 * (1 - f) * Math.min(1, (ke - 0.12) * 5) : 0; }); } };
}
/** Interior de cápsula espacial apretada (paneles grises con luces, 3 asientos). Asientos en z = -0.7, 0, 0.7 mirando a +X (al tablero en x≈1.3).
 *  ca.alarma(k) prende luces rojas; ca.temblor(t, k) sacude la cámara (devuelve un offset). ca.mover(t) parpadea los indicadores. */
export function capsula(sc) {
  sc.background = new THREE.Color(0x020203); sc.add(new THREE.HemisphereLight(0xb8c4d8, 0x101014, 0.45));
  const gris = M.mat(0x8a8c88, { roughness: 0.6 }), osc = M.mat(0x2e3034, { roughness: 0.5 });
  M.caja(sc, 4, 0.06, 3, 0, -0.03, 0, osc); M.caja(sc, 0.06, 2.6, 3, -1.4, 1.3, 0, gris); M.caja(sc, 4, 2.6, 0.06, 0, 1.3, -1.45, gris); M.caja(sc, 4, 2.6, 0.06, 0, 1.3, 1.45, gris);
  const tab = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.1, 2.8), osc); tab.position.set(1.35, 1.55, 0); tab.rotation.z = 0.35; sc.add(tab);
  const ind = [], az = _azar(12);
  for (let i = 0; i < 70; i++) { const m = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.05, 0.07), emis([0xffffff, 0x60ff80, 0xffb040, 0xff3030][i % 4], 0.8)); const y = 1.12 + az() * 0.85, z = -1.3 + az() * 2.6;
    m.position.set(1.2 - (y - 1.1) * 0.37 + 0.02, y, z); m.rotation.z = 0.35; sc.add(m); ind.push(m); }
  for (let i = 0; i < 18; i++) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.02, 14), M.mat(0x111111)); r.rotation.z = Math.PI / 2 + 0.35; const y = 1.2 + (i % 3) * 0.25, z = -1.1 + Math.floor(i / 3) * 0.44; r.position.set(1.2 - (y - 1.1) * 0.37 + 0.03, y, z); sc.add(r); }
  const vent = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.3, 0.35), emis(0x112244, 0.6)); vent.position.set(0.9, 2.3, -0.9); vent.rotation.z = 0.8; sc.add(vent);
  for (const z of [-0.7, 0, 0.7]) { M.caja(sc, 0.9, 0.1, 0.55, -0.35, 0.42, z, M.mat(0x4a4f56)); M.caja(sc, 0.1, 0.9, 0.55, -0.85, 0.85, z, M.mat(0x4a4f56)); }
  const luz = new THREE.PointLight(0xfff2dc, 3, 5, 1.5); luz.position.set(0.3, 2.3, 0); sc.add(luz);
  const roja = new THREE.PointLight(0xff2010, 0, 6, 1.3); roja.position.set(0.8, 2.0, 0); sc.add(roja);
  let ka = 0;
  return { alarma(k) { ka = k; }, mover(t) { ind.forEach((m, i) => { m.material.emissiveIntensity = 0.5 + 0.5 * Math.sin(t * (2 + i % 5) + i) + (i % 4 === 3 ? ka * 2 * (Math.sin(t * 12) > 0 ? 1 : 0) : 0); });
      roja.intensity = ka * (Math.sin(t * 9) > 0 ? 9 : 1.5); luz.intensity = 3 * (1 - ka * 0.6) * (ka > 0 && Math.sin(t * 23) > 0.85 ? 0.3 : 1); },
    temblor(t, k) { return new THREE.Vector3(Math.sin(t * 47) * 0.04 * k, Math.sin(t * 61) * 0.035 * k, Math.sin(t * 53) * 0.04 * k); } };
}
/** Avión de pasajeros de 4 hélices de los años 40 (tipo Avro Lancastrian: ala media, doble deriva, plateado). Nariz +X, largo ~23 m.
 *  av.mover(t) gira las hélices y parpadea la luz. */
export function avionHelices(sc) {
  const g = new THREE.Group(), pl = M.mat(0xc8ccd0, { roughness: 0.3, metalness: 0.8 }), os = M.mat(0x1a1a1a);
  const fus = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 0.45, 20, 24), pl); fus.rotation.z = Math.PI / 2; fus.position.x = -1; g.add(fus);
  const nariz = new THREE.Mesh(new THREE.SphereGeometry(1.1, 24, 14, 0, Math.PI * 2, 0, Math.PI / 2), pl); nariz.rotation.z = -Math.PI / 2; nariz.position.x = 9; nariz.scale.set(1, 1.8, 1); g.add(nariz);
  const vid = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.4, 1.2), M.mat(0x0b1220, { metalness: 0.8, roughness: 0.1 })); vid.position.set(8.2, 0.85, 0); vid.rotation.z = -0.3; g.add(vid);
  for (let i = 0; i < 8; i++) for (const s of [1, -1]) { const w = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.04), emis(0xffe2a8, 0.6)); w.position.set(4 - i * 1.3, 0.25, s * 1.06); g.add(w); }
  const ala = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.28, 31), pl); ala.position.set(1.8, -0.1, 0); g.add(ala);
  const hel = [];
  for (const z of [-9.5, -4.6, 4.6, 9.5]) { const n = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.45, 3.6, 16), pl); n.rotation.z = Math.PI / 2; n.position.set(3.4, -0.1, z); g.add(n);
    const h = new THREE.Group(); h.position.set(5.3, -0.1, z); g.add(h); for (let i = 0; i < 3; i++) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.6, 0.22), os); p.position.y = 0.8; const q = new THREE.Group(); q.rotation.x = i * 2.094; q.add(p); h.add(q); }
    const d = new THREE.Mesh(new THREE.CircleGeometry(1.6, 28), new THREE.MeshBasicMaterial({ color: 0xaaaaaa, transparent: true, opacity: 0.1, side: THREE.DoubleSide, depthWrite: false })); d.rotation.y = Math.PI / 2; h.add(d); hel.push(h); }
  const est = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.15, 9), pl); est.position.set(-10, 0.3, 0); g.add(est);
  for (const z of [4.5, -4.5]) { const d = new THREE.Mesh(new THREE.BoxGeometry(2.0, 2.6, 0.15), pl); d.position.set(-10.2, 1.2, z); g.add(d); }
  const st = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 8), emis(0xff2020, 5)); st.position.set(1.8, -0.1, -15.6); g.add(st);
  const st2 = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 8), emis(0x20ff40, 5)); st2.position.set(1.8, -0.1, 15.6); g.add(st2);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; }); sc.add(g);
  return { g, mover(t) { hel.forEach((h, i) => { h.rotation.x = t * 50 + i; }); } };
}
/** Montañas nevadas de los Andes (picos blancos con roca) y nubes; valle/glaciar en y=0 alrededor de (0,0). an.nubes(t) mueve las nubes.
 *  dia: 'tarde' (luz cálida) | 'tormenta' (gris oscuro, nieve que cae). */
export function andesNieve(sc, { dia = 'tarde', semilla = 5 } = {}) {
  const tor = dia === 'tormenta';
  M.cielo(sc, tor ? '#3a4250' : '#6f8fb8', tor ? '#9aa4b0' : '#f2d4b0'); sc.fog = new THREE.FogExp2(tor ? 0x7d8692 : 0xd8d8e0, tor ? 0.0035 : 0.0025);
  sc.add(new THREE.HemisphereLight(0xe8f0ff, 0x4a4a50, tor ? 0.6 : 0.55));
  const s = new THREE.DirectionalLight(tor ? 0xd0d8e8 : 0xffe2c0, tor ? 1.2 : 1.5); s.position.set(-60, 80, 40); s.castShadow = true; s.shadow.mapSize.set(2048, 2048);
  Object.assign(s.shadow.camera, { left: -40, right: 40, top: 40, bottom: -40, near: 1, far: 300 }); sc.add(s);
  const az = _azar(semilla), nieve = M.mat(0xd6dce4, { roughness: 0.9, flatShading: true }), roca = M.mat(0x4a4642, { roughness: 1, flatShading: true });
  const piso = new THREE.Mesh(new THREE.PlaneGeometry(800, 800, 80, 80), nieve); piso.rotation.x = -Math.PI / 2;
  const pa = piso.geometry.attributes.position; for (let i = 0; i < pa.count; i++) { const x = pa.getX(i), y = pa.getY(i); const d = Math.hypot(x, y); pa.setZ(i, d < 25 ? Math.sin(x * 0.3) * 0.25 + Math.cos(y * 0.25) * 0.2 : (d - 25) * 0.25 * (0.6 + 0.4 * Math.sin(x * 0.05 + y * 0.07))); }
  piso.geometry.computeVertexNormals(); piso.receiveShadow = true; sc.add(piso);
  for (let i = 0; i < 40; i++) { const a = az() * 6.283, r = 70 + az() * 220, h = 40 + az() * 110, rad = 25 + az() * 45;
    const c = new THREE.Mesh(new THREE.ConeGeometry(rad, h, 6 + Math.floor(az() * 3)), az() > 0.35 ? nieve : roca); c.position.set(Math.cos(a) * r, h / 2 - 6, Math.sin(a) * r); c.rotation.y = az() * 3; sc.add(c);
    const cap = new THREE.Mesh(new THREE.ConeGeometry(rad * 0.45, h * 0.45, 6), nieve); cap.position.set(c.position.x, h * 0.77 - 6, c.position.z); cap.rotation.y = c.rotation.y; sc.add(cap); }
  const cv = document.createElement('canvas'); cv.width = cv.height = 128; const gx = cv.getContext('2d'); const grd = gx.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, tor ? 'rgba(200,205,212,0.9)' : 'rgba(255,255,255,0.9)'); grd.addColorStop(1, 'rgba(255,255,255,0)'); gx.fillStyle = grd; gx.fillRect(0, 0, 128, 128); const tx = new THREE.CanvasTexture(cv);
  const nubes = []; for (let i = 0; i < 90; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, opacity: 0.55, depthWrite: false })); sp.userData.o = [(az() - 0.5) * 500, 20 + az() * 60, (az() - 0.5) * 500]; sp.scale.setScalar(40 + az() * 60); sc.add(sp); nubes.push(sp); }
  let copos = null;
  if (tor) { const n = 3000, p = new Float32Array(n * 3); for (let i = 0; i < n; i++) p.set([(az() - 0.5) * 60, az() * 40, (az() - 0.5) * 60], i * 3);
    const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.BufferAttribute(p, 3)); copos = new THREE.Points(gg, new THREE.PointsMaterial({ color: 0xffffff, size: 0.18, transparent: true, opacity: 0.8, depthWrite: false })); sc.add(copos); }
  return { piso, nubes(t, c = { x: 0, y: 0, z: 0 }) { nubes.forEach((sp, i) => { const [x, y, z] = sp.userData.o; sp.position.set(x + t * (6 + i % 5), y, z); });
      if (copos) copos.position.set(c.x + Math.sin(t) * 2, c.y - ((t * 4) % 20), c.z); } };
}
/** Motor de avión viejo semienterrado en la nieve (bloque en V con cilindros, hélice doblada). */
export function motorViejo(sc, x = 0, z = 0, giro = 0) {
  const g = new THREE.Group(), met = M.mat(0x4a4038, { roughness: 0.8, metalness: 0.6 }), oxi = M.mat(0x6a4a30, { roughness: 1, metalness: 0.3 });
  const b = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.6, 0.7), met); b.position.y = 0.3; g.add(b);
  for (const s of [1, -1]) { const v = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.4, 0.3), oxi); v.position.set(0, 0.6, s * 0.25); v.rotation.x = s * 0.5; g.add(v); for (let i = 0; i < 6; i++) { const e = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.25, 6), met); e.position.set(-0.7 + i * 0.28, 0.82, s * 0.38); g.add(e); } }
  const cubo = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.3, 0.5, 14), met); cubo.rotation.z = Math.PI / 2; cubo.position.set(1.1, 0.3, 0); g.add(cubo);
  for (let i = 0; i < 3; i++) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.3, 0.22), oxi); const q = new THREE.Group(); q.position.set(1.35, 0.3, 0); q.rotation.x = i * 2.094; p.position.y = 0.6; p.rotation.z = i === 1 ? 0.7 : 0.15; q.add(p); g.add(q); }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; }); g.position.set(x, -0.15, z); g.rotation.set(0.25, giro, 0.12); sc.add(g); return g;
}

// ======================= 22-nov: cueva inundada, avión ATR turbohélice, cabina de pilotos, carretera de campo de noche, huevo de luz =======================
/** Textura de agua oscura con ondas (para ríos subterráneos, cuevas, charcos). */
function _texOndas(base = '#0e2a2c', luz = 'rgba(160,220,210,0.10)') {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'); g.fillStyle = base; g.fillRect(0, 0, 256, 256);
  const az = _azar(13); for (let i = 0; i < 120; i++) { g.strokeStyle = luz; g.lineWidth = 1 + az() * 2; g.beginPath(); const x = az() * 256, y = az() * 256, r = 6 + az() * 26;
    g.ellipse(x, y, r, r * 0.35, 0, 0, Math.PI * 2); g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t;
}
/** Cueva de roca caliza inundada (tipo Tham Luang): galería a lo largo de Z (z=-40..12), ancho ~5, techo bajo con estalactitas,
 *  agua turbia que sube (cu.agua(nivel, t)) y una roca seca/lodo en la zona z∈[-30,-24] (repisa en x≈-1, y≈0.6). Oscuridad total:
 *  la luz la ponen las linternas (K.linterna) o cu.luz (luz cálida de apoyo, intensidad). */
export function cuevaInundada(sc, { semilla = 17, apoyo = 1 } = {}) {
  sc.background = new THREE.Color(0x010202); sc.fog = new THREE.FogExp2(0x060807, 0.075);
  sc.add(new THREE.HemisphereLight(0x8a9a90, 0x0c0a08, 0.12 * apoyo));
  const roca = M.matTex(M.TEX.roca(), [3, 2], 0x8a7c66), lodo = M.matTex(M.TEX.arena(), [6, 18], 0x5c4a36), az = _azar(semilla);
  M.caja(sc, 8, 0.3, 60, 0, -1.2, -14, lodo);
  for (let z = -42; z < 14; z += 1.4) for (const lado of [-1, 1]) {
    const r = new THREE.Mesh(new THREE.DodecahedronGeometry(1.5 + az() * 0.7, 1), roca); r.position.set(lado * (3.0 + az() * 0.6), 0.6 + az() * 2.2, z); r.scale.set(1, 1.7, 1.2); r.receiveShadow = true; r.castShadow = true; sc.add(r);
    const t = new THREE.Mesh(new THREE.DodecahedronGeometry(1.7 + az() * 0.6, 1), roca); t.position.set(lado * (1.0 + az() * 1.2), 4.1 + az() * 0.5, z); t.receiveShadow = true; sc.add(t); }
  for (let i = 0; i < 70; i++) { const h = 0.2 + az() * 0.7, e = new THREE.Mesh(new THREE.ConeGeometry(0.05 + az() * 0.08, h, 6), roca); e.rotation.x = Math.PI; e.position.set((az() - 0.5) * 4, 3.3 - h / 2 + az() * 0.3, -40 + az() * 52); sc.add(e); }
  for (let i = 0; i < 9; i++) { const r = new THREE.Mesh(new THREE.DodecahedronGeometry(0.8 + az() * 0.5, 1), lodo); r.scale.set(1.7, 0.32, 1.4); r.position.set(-1.0 + (az() - 0.5) * 2.0, -0.05, -27 + (az() - 0.5) * 4); r.receiveShadow = true; r.castShadow = true; sc.add(r); }
  const tx = _texOndas(); tx.repeat.set(3, 20);
  const agua = new THREE.Mesh(new THREE.PlaneGeometry(8, 60), new THREE.MeshStandardMaterial({ map: tx, color: 0x7f9a8e, emissive: 0x0d2624, emissiveMap: tx, emissiveIntensity: 1.6, roughness: 0.12, metalness: 0.45, transparent: true, opacity: 0.95 }));
  agua.rotation.x = -Math.PI / 2; agua.position.set(0, -0.6, -14); agua.receiveShadow = true; sc.add(agua);
  const luz = new THREE.PointLight(0xffc890, 0, 12, 1.4); luz.position.set(0.5, 2.4, -24.5); sc.add(luz);
  const gotas = []; for (let i = 0; i < 40; i++) { const g = new THREE.Mesh(new THREE.SphereGeometry(0.018, 6, 4), M.mat(0xbfd8d0, { roughness: 0.1, metalness: 0.4 })); g.userData = { x: (az() - 0.5) * 3.6, z: -38 + az() * 48, f: az() * 3 }; sc.add(g); gotas.push(g); }
  return { agua: agua, luz, poner(nivel, t) { agua.position.y = nivel; tx.offset.set(Math.sin(t * 0.3) * 0.05, -t * 0.08);
      gotas.forEach(g => { const u = g.userData, k = ((t + u.f) % 1.2) / 1.2; g.position.set(u.x, 3.2 - k * (3.2 - nivel), u.z); }); } };
}
/** Avión turbohélice regional de ala alta y dos motores (tipo ATR 42), blanco con cola azul. Nariz +X, largo ~22 m.
 *  a.userData.mover(t) gira las hélices. */
export function atr42(sc, { cola = 0x1f3f9a } = {}) {
  const g = new THREE.Group(), bl = M.mat(0xf2f2f0, { roughness: 0.35, metalness: 0.25 }), az_ = M.mat(cola, { roughness: 0.4, metalness: 0.2 }), gr = M.mat(0x2a2d33, { roughness: 0.4 });
  const vid = M.mat(0x0b0f16, { roughness: 0.05, metalness: 0.8 });
  const fus = new THREE.Mesh(new THREE.CylinderGeometry(1.35, 1.35, 15, 28), bl); fus.rotation.z = Math.PI / 2; g.add(fus);
  const nariz = new THREE.Mesh(new THREE.SphereGeometry(1.35, 28, 18, 0, Math.PI * 2, 0, Math.PI / 2), bl); nariz.scale.set(1, 2.0, 1); nariz.rotation.z = -Math.PI / 2; nariz.position.x = 7.5; g.add(nariz);
  const colaF = new THREE.Mesh(new THREE.ConeGeometry(1.35, 6, 28), bl); colaF.rotation.z = Math.PI / 2; colaF.position.set(-10.4, 0.45, 0); colaF.scale.set(1, 1, 0.9); g.add(colaF);
  for (const z of [1, -1]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.42, 0.05), vid); p.position.set(9.0, 0.55, z * 0.82); p.rotation.y = z * -0.35; g.add(p); }
  for (let i = 0; i < 14; i++) for (const z of [1.34, -1.34]) { const w = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.32, 0.03), vid); w.position.set(5.2 - i * 0.82, 0.35, z); g.add(w); }
  const ala = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.28, 24.5), bl); ala.position.set(1.2, 1.55, 0); g.add(ala);
  const deriva = new THREE.Mesh(new THREE.BoxGeometry(3.2, 4.2, 0.22), az_); deriva.position.set(-11.2, 2.9, 0); deriva.rotation.z = 0.35; g.add(deriva);
  const estab = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.14, 7.2), bl); estab.position.set(-12.2, 4.9, 0); g.add(estab);
  const franja = new THREE.Mesh(new THREE.BoxGeometry(14.5, 0.18, 2.74), az_); franja.position.set(-0.2, -0.25, 0); g.add(franja);
  const helices = [];
  for (const z of [4.1, -4.1]) { const n = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.45, 4.6, 18), bl); n.rotation.z = Math.PI / 2; n.position.set(1.6, 1.05, z); g.add(n);
    const cono_ = new THREE.Mesh(new THREE.ConeGeometry(0.32, 0.8, 16), gr); cono_.rotation.z = -Math.PI / 2; cono_.position.set(4.3, 1.05, z); g.add(cono_);
    const h = new THREE.Group(); h.position.set(4.05, 1.05, z); g.add(h); helices.push(h);
    for (let k = 0; k < 4; k++) { const pa = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.9, 0.22), gr); pa.position.y = 0.95; const piv = new THREE.Group(); piv.rotation.x = k * Math.PI / 2; piv.add(pa); h.add(piv); }
    const disco = new THREE.Mesh(new THREE.CircleGeometry(1.95, 32), new THREE.MeshBasicMaterial({ color: 0x9aa0a8, transparent: true, opacity: 0.14, depthWrite: false, side: THREE.DoubleSide })); disco.rotation.y = Math.PI / 2; h.add(disco); }
  for (const [x, z] of [[1.0, 1.2], [1.0, -1.2], [7, 0]]) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.25, 14), M.mat(0x111111)); r.rotation.x = Math.PI / 2; r.position.set(x, -1.55, z); g.add(r); }
  const luzRoja = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 6), emis(0xff2a1a, 3)); luzRoja.position.set(1.2, 1.6, 12.3); g.add(luzRoja);
  const luzVerde = new THREE.Mesh(new THREE.SphereGeometry(0.12, 8, 6), emis(0x2aff6a, 3)); luzVerde.position.set(1.2, 1.6, -12.3); g.add(luzVerde);
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  g.userData.mover = t => helices.forEach(h => { h.rotation.x = t * 37; });
  sc.add(g); return g;
}
/** Cabina de pilotos de avión regional (dos asientos mirando a +X, piloto en z=-0.45 y copiloto en z=+0.45, asiento en x=0).
 *  Tablero en x≈0.95 con 4 pantallas; parabrisas con niebla/cielo. ca.pantallas(t, modo): 'negro' (sin datos, rayas), 'ok' (horizonte), 'alerta'. */
export function cabinaPilotos(sc, { afuera = '#9aa3ad' } = {}) {
  sc.background = new THREE.Color(0x05060a); sc.add(new THREE.HemisphereLight(0x9aa8c0, 0x141416, 0.35));
  const gris = M.mat(0x2b2e33, { roughness: 0.7 }), asiento = M.mat(0x1d2230, { roughness: 0.8 });
  M.caja(sc, 3.2, 0.06, 2.0, 0, -0.03, 0, M.mat(0x1a1b1e)); M.caja(sc, 3.2, 0.06, 2.0, 0, 1.95, 0, gris);
  for (const s of [1, -1]) M.caja(sc, 3.2, 2.0, 0.06, 0, 0.97, s * 1.0, gris);
  M.caja(sc, 0.5, 0.75, 1.9, 1.05, 0.75, 0, M.mat(0x17191c)); M.caja(sc, 0.6, 0.12, 0.35, 0.55, 0.75, 0, M.mat(0x22252a));
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 128; const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const pan = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.4), new THREE.MeshBasicMaterial({ map: tx })); pan.position.set(0.79, 0.93, 0); pan.rotation.y = -Math.PI / 2; pan.rotation.x = 0; sc.add(pan);
  const brillo = new THREE.PointLight(0x9fc8ff, 1.2, 2.2, 1.5); brillo.position.set(0.6, 1.0, 0); sc.add(brillo);
  for (const z of [-0.45, 0.45]) { M.caja(sc, 0.5, 0.12, 0.5, 0.0, 0.48, z, asiento); M.caja(sc, 0.12, 0.85, 0.5, -0.28, 0.92, z, asiento);
    M.caja(sc, 0.05, 0.35, 0.05, 0.45, 0.62, z, M.mat(0x111111)); M.caja(sc, 0.06, 0.06, 0.28, 0.47, 0.8, z, M.mat(0x111111)); }
  const c2 = document.createElement('canvas'); c2.width = 4; c2.height = 128; const g2 = c2.getContext('2d'); const gr = g2.createLinearGradient(0, 0, 0, 128); gr.addColorStop(0, '#d7dde4'); gr.addColorStop(1, afuera); g2.fillStyle = gr; g2.fillRect(0, 0, 4, 128);
  const tc = new THREE.CanvasTexture(c2); tc.colorSpace = THREE.SRGBColorSpace;
  const vidrio = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 0.8), new THREE.MeshBasicMaterial({ map: tc })); vidrio.position.set(1.35, 1.5, 0); vidrio.rotation.y = -Math.PI / 2; vidrio.rotation.z = 0; sc.add(vidrio);
  M.caja(sc, 0.06, 0.06, 1.9, 1.33, 1.5, 0, M.mat(0x111214)); M.caja(sc, 0.06, 0.82, 0.06, 1.33, 1.5, 0, M.mat(0x111214));
  const dia = new THREE.DirectionalLight(0xdfe6f0, 1.4); dia.position.set(3, 2.5, 0.3); sc.add(dia);
  return { vidrio: tc, pantallas(t, modo = 'negro') {
    const g = cv.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 512, 128);
    for (let i = 0; i < 4; i++) { const x = 8 + i * 126; g.fillStyle = '#05070a'; g.fillRect(x, 8, 118, 112); g.strokeStyle = '#3a3f46'; g.lineWidth = 3; g.strokeRect(x, 8, 118, 112);
      if (modo === 'ok' && i < 2) { g.fillStyle = '#2f7fd8'; g.fillRect(x + 3, 11, 112, 52); g.fillStyle = '#8a5a2a'; g.fillRect(x + 3, 63, 112, 54); g.strokeStyle = '#fff'; g.beginPath(); g.moveTo(x + 40, 63); g.lineTo(x + 78, 63); g.stroke(); }
      else if (i < 2) { g.strokeStyle = modo === 'alerta' ? '#ff4030' : '#c83226'; g.lineWidth = 5; g.beginPath(); g.moveTo(x + 14, 22); g.lineTo(x + 104, 106); g.moveTo(x + 104, 22); g.lineTo(x + 14, 106); g.stroke();
        if (Math.floor(t * 3) % 2) { g.fillStyle = '#ffb020'; g.font = 'bold 22px monospace'; g.fillText('ATT', x + 38, 70); } }
      else { g.fillStyle = '#1fd060'; g.font = '16px monospace'; for (let k = 0; k < 5; k++) g.fillText('--- ' + (k % 2 ? '- -' : '---'), x + 14, 32 + k * 19); } }
    tx.needsUpdate = true; } };
}
/** Carretera recta de dos carriles a lo largo de X (z≈0) en campo plano de noche (oeste de Texas, años 50): surcos de algodón,
 *  postes de teléfono con cables, cielo con nubes de tormenta. ca.relampago(k 0..1) ilumina el horizonte. */
export function carreteraCampo(sc, { semilla = 8, luna = 1 } = {}) {
  M.cielo(sc, '#04060c', '#1a2030'); sc.fog = new THREE.FogExp2(0x0b0f18, 0.018);
  const hemi = new THREE.HemisphereLight(0x5a6c94, 0x141210, 0.5 * luna); sc.add(hemi);
  const l = new THREE.DirectionalLight(0x8ea4d8, 0.9 * luna); l.position.set(-20, 30, 15); l.castShadow = true; l.shadow.mapSize.set(2048, 2048);
  Object.assign(l.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30 }); sc.add(l);
  const az = _azar(semilla);
  M.caja(sc, 300, 0.2, 300, 0, -0.1, 0, M.matTex(M.TEX.arena(), [60, 60], 0x5a4c3c));
  M.caja(sc, 300, 0.04, 7, 0, 0.02, 0, M.matTex(M.TEX.concreto(), [60, 2], 0x34343a));
  for (let x = -150; x < 150; x += 5) M.caja(sc, 2.6, 0.02, 0.14, x, 0.05, 0, M.mat(0xcfc07a, { roughness: 0.6 }), false);
  const surco = M.mat(0x3d3226, { roughness: 1 }), algodon = M.mat(0xb8b4aa, { roughness: 1 });
  for (const lado of [-1, 1]) for (let i = 0; i < 26; i++) { const z = lado * (5.5 + i * 1.3);
    M.caja(sc, 300, 0.25, 0.5, 0, 0.1, z, surco, false);
    for (let k = 0; k < 40; k++) { const b = new THREE.Mesh(new THREE.SphereGeometry(0.12 + az() * 0.1, 6, 4), algodon); b.position.set(-100 + az() * 200, 0.3, z + (az() - 0.5) * 0.3); sc.add(b); } }
  const madera = M.mat(0x3a2c20, { roughness: 1 });
  for (let x = -120; x <= 120; x += 22) { M.caja(sc, 0.25, 8, 0.25, x, 4, -5, madera); M.caja(sc, 2.4, 0.15, 0.15, x, 7.6, -5, madera); }
  for (const dz of [-1.0, 0, 1.0]) { const cab = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 240, 4), M.mat(0x111111)); cab.rotation.z = Math.PI / 2; cab.position.set(0, 7.45, -5 + dz * 0.01); cab.position.x = 0; cab.position.z = -5; cab.translateY(0); cab.position.y = 7.5 + dz * 0.0; cab.position.z = -5 + dz; sc.add(cab); }
  const casa = (x, z) => { M.caja(sc, 6, 3, 5, x, 1.5, z, M.mat(0x5e5548)); M.caja(sc, 1, 1, 0.1, x + 1, 1.6, z + 2.52, emis(0xffb460, 0.8), false); };
  casa(-60, -40); casa(45, 50); casa(90, -70);
  const fl = new THREE.PointLight(0xbfd0ff, 0, 400, 0.5); fl.position.set(40, 30, -120); sc.add(fl);
  return { relampago(k) { fl.intensity = 30000 * k; hemi.intensity = 0.5 * luna + 1.4 * k; } };
}
/** Objeto de luz en forma de huevo (relatos de Levelland 1957): óvalo brillante anaranjado-blanco con halo y luz que ilumina el piso.
 *  h.brillo(k) 0..1 (k=0 apagado). h.g = grupo (largo `largo` a lo largo de X). */
export function huevoLuz(sc, largo = 30, color = 0xffb060) {
  const g = new THREE.Group(); sc.add(g);
  const cuerpo = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 24), new THREE.MeshBasicMaterial({ color: new THREE.Color(color).lerp(new THREE.Color(0xffffff), 0.55), transparent: true, fog: false }));
  cuerpo.scale.set(largo / 2, largo / 7, largo / 5.5); g.add(cuerpo);
  const nucleo = brilloSprite('#ffe0a0', largo * 1.25, 0.9), halo = brilloSprite('#ff8a3a', largo * 2.4, 0.55); g.add(halo); g.add(nucleo);
  const luz = new THREE.PointLight(color, 4000, largo * 4, 1.4); luz.position.y = -largo / 8; g.add(luz);
  return { g, brillo(k) { cuerpo.material.opacity = Math.min(1, k * 1.2); cuerpo.visible = k > 0.02; nucleo.material.opacity = 0.9 * k; halo.material.opacity = 0.55 * k * (0.9 + Math.random() * 0.1); luz.intensity = 4000 * k; } };
}

// ======================= 23-nov: bergantín (Mary Celeste), camarote de barco, isla-cárcel de noche, balsa de impermeables,
// barrio japonés de los años 40, destello, selva tropical densa, choza/campamento con lámpara, volantes que caen =======================
/** Bergantín del siglo XIX (casco negro con franja, 2 mástiles; trinquete con velas cuadradas, mayor con cangreja). Proa hacia +X, largo ~30 m.
 *  Cubierta en y≈2.1 (local). velas: 0..1 cuánto están desplegadas (1/2 = a medio desplegar). b.timon = rueda (gírala con rotation.x). */
export function bergantin(sc, { velas = 0.5, rasgadas = true } = {}) {
  const g = new THREE.Group(), ne = M.mat(0x16181b, { roughness: 0.6 }), fr = M.mat(0xd9d2bd, { roughness: 0.8 }), cu = M.mat(0x8a6a48, { roughness: 0.9 }),
    ma = M.mat(0x5a3e26, { roughness: 0.9 }), ve = M.mat(0xe6dcc2, { roughness: 1, side: THREE.DoubleSide });
  const add = (w, h, d, x, y, z, mm, padre = g) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; b.receiveShadow = true; padre.add(b); return b; };
  // casco: varias rebanadas que se angostan hacia proa y popa
  for (let i = 0; i < 14; i++) { const x = -13 + i * 2, k = Math.min(1, (14 - Math.abs(x + 1)) / 6), w = 7.6 * (0.45 + 0.55 * Math.sqrt(Math.max(0, k)));
    add(2.05, 2.6, w, x, 0.6, 0, ne); add(2.05, 0.28, w + 0.04, x, 1.7, 0, fr); add(2.05, 0.1, w - 0.3, x, 2.05, 0, cu); }
  const proa = new THREE.Mesh(new THREE.ConeGeometry(2.4, 4.5, 4), ne); proa.rotation.z = -Math.PI / 2; proa.rotation.x = Math.PI / 4; proa.scale.set(1, 1, 0.8); proa.position.set(16.2, 1.0, 0); g.add(proa);
  const baup = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.2, 9, 8), ma); baup.rotation.z = -Math.PI / 2 + 0.25; baup.position.set(19, 3.2, 0); g.add(baup);
  for (const z of [-1, 1]) for (let i = 0; i < 13; i++) add(0.12, 0.7, 0.12, -12.5 + i * 2.1, 2.45, z * (3.1 - Math.max(0, i - 9) * 0.5), ma);
  for (const z of [-1, 1]) add(27, 0.1, 0.16, 0, 2.8, z * 3.05, ma);
  add(5, 1.6, 3.6, -7.5, 2.9, 0, cu); add(5.2, 0.12, 3.8, -7.5, 3.75, 0, ma);   // camarote en popa
  for (const z of [-1.81, 1.81]) for (const x of [-9, -6]) add(0.5, 0.4, 0.04, x, 3.1, z, M.mat(0x2a3138, { metalness: 0.5, roughness: 0.2 }), g);
  add(2.4, 0.35, 2, 2, 2.25, 0, ma); add(2.2, 0.06, 1.8, 2, 2.44, 0, M.mat(0x3a2a1a));   // escotilla de carga
  const timon = new THREE.Group(); timon.position.set(-11.3, 3.2, 0); g.add(timon);
  const aro = new THREE.Mesh(new THREE.TorusGeometry(0.55, 0.05, 6, 20), ma); aro.rotation.y = Math.PI / 2; timon.add(aro);
  for (let i = 0; i < 8; i++) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.4, 5), ma); r.rotation.x = i * Math.PI / 8; timon.add(r); }
  add(0.3, 1.1, 0.3, -11.3, 2.6, 0, ma);
  const velasG = [];
  for (const [x, h, cuadradas] of [[7, 20, true], [-3, 22, false]]) {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.3, h, 8), ma); m.position.set(x, 2 + h / 2, 0); m.castShadow = true; g.add(m);
    if (cuadradas) for (const [y, w] of [[0.32, 10], [0.55, 8.4], [0.75, 6.8], [0.9, 5]]) {
      const ver = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, w, 6), ma); ver.rotation.x = Math.PI / 2; ver.position.set(x + 0.3, 2 + h * y + 2.2, 0); g.add(ver);
      const alto = h * 0.2 * (y < 0.7 ? velas : 0.15), v = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.92, Math.max(0.3, alto), 8, 4), ve);
      const pa = v.geometry.attributes.position; for (let i = 0; i < pa.count; i++) pa.setZ(i, Math.cos(pa.getX(i) / (w * 0.5)) * 0.6 + (rasgadas && y < 0.4 ? Math.sin(pa.getX(i) * 3) * 0.15 : 0));
      v.rotation.y = Math.PI / 2; v.position.set(x + 0.45, 2 + h * y + 2.2 - Math.max(0.3, alto) / 2, 0); v.castShadow = true; g.add(v); velasG.push(v);
    } else {
      const bo = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 9, 6), ma); bo.rotation.z = Math.PI / 2; bo.position.set(x - 4.5, 4.2, 0); g.add(bo);
      const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(-8.5, 0); sh.lineTo(-7.5, h * 0.45 * (0.4 + velas * 0.6)); sh.lineTo(0, h * 0.55 * (0.4 + velas * 0.6)); sh.closePath();
      const v = new THREE.Mesh(new THREE.ShapeGeometry(sh), ve); v.position.set(x - 0.2, 4.3, 0.05); v.castShadow = true; g.add(v); velasG.push(v);
    }
  }
  for (const [a, b] of [[[7, 22, 0], [18.5, 4.3, 0]], [[7, 22, 0], [-3, 24, 0]], [[-3, 24, 0], [-13, 3, 0]], [[7, 20, 0], [7, 2.5, 3.3]], [[7, 20, 0], [7, 2.5, -3.3]], [[-3, 22, 0], [-3, 2.5, 3.3]], [[-3, 22, 0], [-3, 2.5, -3.3]]]) {
    const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), c = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, A.distanceTo(B), 4), M.mat(0x2a2418));
    c.position.copy(A).add(B).multiplyScalar(0.5); c.lookAt(B); c.rotateX(Math.PI / 2); g.add(c); }
  g.userData.timon = timon; g.userData.velas = velasG; sc.add(g); return g;
}
/** Camarote del capitán de un barco de vela (madera, ojo de buey con luz de día, mesa con platos y tazas, litera, baúl, mapa).
 *  Mesa en (0, 0) con la cara hacia +Z; la puerta en (1.6, z=1.8). Devuelve {mover(t)} (el cuarto se mece con el mar). */
export function camarote(sc) {
  sc.background = new THREE.Color(0x0b0806); sc.add(new THREE.HemisphereLight(0xd8c8a8, 0x1a120a, 0.45));
  const g = new THREE.Group(); sc.add(g);
  const tab = M.mat(0x6b4a2c, { roughness: 0.85 }), tab2 = M.mat(0x4a3220, { roughness: 0.9 });
  const add = (w, h, d, x, y, z, mm) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; b.receiveShadow = true; g.add(b); return b; };
  add(7, 0.1, 6, 0, -0.05, 0, tab2); add(7, 2.4, 0.15, 0, 1.2, -2.2, tab); add(0.15, 2.4, 6, -2.6, 1.2, 0, tab); add(0.15, 2.4, 6, 2.6, 1.2, 0, tab); add(7, 0.12, 6, 0, 2.4, 0, tab2);
  for (let i = 0; i < 7; i++) add(7, 0.12, 0.14, 0, 2.3, -2.2 + i * 0.75, tab2);
  for (let i = 0; i < 9; i++) add(0.02, 2.4, 0.02, -2.5, 1.2, -2 + i * 0.6, tab2);
  const ojo = new THREE.Mesh(new THREE.CircleGeometry(0.22, 24), emis(0xdfe9f2, 1.6)); ojo.position.set(-0.6, 1.6, -2.12); g.add(ojo);
  const aro = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.04, 8, 24), M.mat(0xb08a3a, { metalness: 0.8, roughness: 0.3 })); aro.position.set(-0.6, 1.6, -2.1); g.add(aro);
  const sol = new THREE.SpotLight(0xfff0d8, 30, 8, 0.35, 0.6, 1.2); sol.position.set(-0.6, 1.6, -2.0); const tg = new THREE.Object3D(); tg.position.set(0.2, 0.7, 0.6); g.add(tg); sol.target = tg; sol.castShadow = true; g.add(sol);
  add(1.6, 0.07, 0.9, 0, 0.76, 0, tab); for (const [x, z] of [[-0.7, -0.38], [0.7, -0.38], [-0.7, 0.38], [0.7, 0.38]]) add(0.07, 0.76, 0.07, x, 0.38, z, tab2);
  const loza = M.mat(0xece6d8, { roughness: 0.4 });
  for (const [x, z] of [[-0.45, 0.2], [0.4, 0.2], [0, -0.25]]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.1, 0.025, 20), loza); p.position.set(x, 0.81, z); g.add(p);
    const tz = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.035, 0.08, 12), loza); tz.position.set(x + 0.18, 0.84, z - 0.05); g.add(tz); }
  const pan = new THREE.Mesh(new THREE.SphereGeometry(0.09, 10, 8), M.mat(0xb07a3a)); pan.scale.y = 0.6; pan.position.set(0.05, 0.84, 0.05); g.add(pan);
  add(0.45, 0.02, 0.32, -0.3, 0.8, -0.2, M.mat(0xd8c9a0)); // mapa
  add(0.9, 0.5, 1.9, -2.1, 0.75, -0.6, tab); add(0.8, 0.12, 1.8, -2.1, 1.05, -0.6, M.mat(0x8a2a22)); add(0.6, 0.12, 0.35, -2.1, 1.17, -1.3, M.mat(0xe8e0d0));
  add(0.8, 0.5, 0.45, 1.8, 0.25, -1.7, tab2); add(0.82, 0.06, 0.47, 1.8, 0.52, -1.7, M.mat(0x2a2016)); // baúl
  add(0.05, 0.4, 0.5, 2.5, 1.5, -0.8, M.mat(0x2a2016)); add(0.06, 0.32, 0.42, 2.49, 1.5, -0.8, M.mat(0xc8b890)); // cuadro
  for (const x of [-0.5, 0.5]) { add(0.4, 0.05, 0.4, x, 0.46, 0.75, tab2); add(0.4, 0.5, 0.05, x, 0.72, 0.95, tab2); }
  const lamp = brilloSprite('#ffcf8a', 0.25, 0.6); lamp.position.set(0.9, 2.0, -0.4); g.add(lamp);
  return { g, mover(t) { g.rotation.z = Math.sin(t * 0.9) * 0.03; g.rotation.x = Math.sin(t * 0.7 + 1) * 0.015; } };
}
/** Isla-cárcel de noche (tipo Alcatraz): roca oscura, bloque de celdas largo con ventanitas encendidas, torre de agua y faro con haz que gira.
 *  Centro en (0,0,-60). Úsala con marNoche({tormenta:false}). Devuelve {mover(t)}. */
export function islaCarcel(sc, { z0 = -60 } = {}) {
  const g = new THREE.Group(); g.position.z = z0; sc.add(g);
  const roca = M.matTex(M.TEX.roca(), [6, 2], 0x4a4640), con = M.matTex(M.TEX.concreto(), [6, 2], 0x9a958a);
  const add = (w, h, d, x, y, z, mm, s = true) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = s; b.receiveShadow = true; g.add(b); return b; };
  const az = _azar(13);
  for (let i = 0; i < 26; i++) { const r = new THREE.Mesh(new THREE.DodecahedronGeometry(6 + az() * 6, 0), roca); r.position.set((az() - 0.5) * 60, -2 + az() * 3, (az() - 0.5) * 18); r.scale.y = 0.55; g.add(r); }
  add(56, 5, 18, 0, 1.5, 0, roca);
  add(34, 9, 9, 2, 8.5, 0, con); add(35, 0.6, 9.6, 2, 13.2, 0, M.mat(0x3a3a3a));
  for (let p = 0; p < 2; p++) for (let i = 0; i < 16; i++) add(0.7, 1.6, 0.1, -13 + i * 2, 7 + p * 3.2, 4.56, az() < 0.35 ? emis(0xffd08a, 1.4) : M.mat(0x111317), false);
  add(10, 6, 7, -20, 6, 2, con); add(3, 12, 3, 20, 10, -2, con);
  const tq = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, 3, 16), M.mat(0x6a645a)); tq.position.set(24, 15, 4); g.add(tq);
  for (const [x, z] of [[22.5, 2.5], [25.5, 2.5], [22.5, 5.5], [25.5, 5.5]]) add(0.2, 13, 0.2, x, 7.5, z, M.mat(0x4a4a4a));
  add(1.6, 14, 1.6, -26, 9, -3, M.mat(0xd8d4cc)); add(2.2, 1.6, 2.2, -26, 16.8, -3, emis(0xfff0c8, 2.5));
  const haz = cono(g, -26, 16.8, -3, 70, 7, 0xfff3d0, 0.06, [0, 0, Math.PI / 2]);
  const luz = new THREE.PointLight(0xfff0c8, 200, 60, 1.5); luz.position.set(-26, 17, -3); g.add(luz);
  return { g, mover(t) { haz.rotation.set(0, t * 0.9, Math.PI / 2); } };
}
/** Balsa inflable improvisada con impermeables (gris oscura, bordes como salchichas). Frente hacia +X, ~3 x 1.8 m. */
export function balsaImpermeables(sc) {
  const g = new THREE.Group(), m = M.mat(0x3c3f3a, { roughness: 0.55, metalness: 0.05 });
  for (const z of [-0.8, 0.8]) { const t = new THREE.Mesh(new THREE.CapsuleGeometry(0.22, 2.7, 6, 12), m); t.rotation.z = Math.PI / 2; t.position.set(0, 0.22, z); t.castShadow = true; g.add(t); }
  for (const x of [-1.5, 1.5]) { const t = new THREE.Mesh(new THREE.CapsuleGeometry(0.2, 1.3, 6, 12), m); t.rotation.x = Math.PI / 2; t.position.set(x, 0.2, 0); g.add(t); }
  const piso = new THREE.Mesh(new THREE.BoxGeometry(3, 0.06, 1.6), m); piso.position.y = 0.05; g.add(piso);
  sc.add(g); return g;
}
/** Barrio japonés de los años 40 de día: calle de tierra a lo largo de X (z≈0), casas bajas de madera con techos de teja oscura,
 *  postes de luz con cables y un cerro al fondo. Devuelve {sol, hemi} para poder hacer el destello. */
export function barrioJapones(sc, { semilla = 4 } = {}) {
  M.cielo(sc, '#7fa6cf', '#e6ecef'); sc.fog = new THREE.Fog(0xd8e0e6, 40, 160);
  const sol = M.luces(sc, { sol: 2.4, cielo_: 1.1, dir: [12, 20, 10] }); const hemi = sc.children.find(o => o.isHemisphereLight);
  M.caja(sc, 200, 0.2, 80, 0, -0.1, 0, M.matTex(M.TEX.arena(), [40, 16], 0x9a8a70));
  const az = _azar(semilla), mad = [0x5a4632, 0x6b5640, 0x4a3a2a], teja = M.mat(0x2a2c30, { roughness: 0.7 });
  for (const lado of [-1, 1]) for (let x = -60; x < 60; x += 7 + az() * 2) {
    const w = 5 + az() * 1.5, d = 5 + az() * 2, h = 2.8 + (az() < 0.3 ? 2.8 : 0), z = lado * (5 + d / 2);
    M.caja(sc, w, h, d, x, h / 2, z, M.mat(mad[Math.floor(az() * 3)], { roughness: 0.9 }));
    M.caja(sc, w * 0.8, 1.2, 0.06, x, 1.2, z - lado * (d / 2 + 0.03), M.mat(0xe8e0cc, { roughness: 1 }), false);   // shoji
    const r = new THREE.Mesh(new THREE.ConeGeometry(Math.hypot(w, d) * 0.62, 1.6, 4), teja); r.rotation.y = Math.PI / 4; r.scale.set(w / Math.hypot(w, d) * 1.45, 1, d / Math.hypot(w, d) * 1.45); r.position.set(x, h + 0.8, z); r.castShadow = true; sc.add(r);
  }
  for (let x = -50; x < 60; x += 14) { M.caja(sc, 0.2, 7, 0.2, x, 3.5, -3.6, M.mat(0x3a2e22)); M.caja(sc, 1.4, 0.1, 0.1, x, 6.6, -3.6, M.mat(0x3a2e22)); }
  for (const y of [6.5, 6.2]) M.caja(sc, 110, 0.02, 0.02, 0, y, -3.6, M.mat(0x111111), false);
  const cerro = new THREE.Mesh(new THREE.SphereGeometry(60, 20, 12), M.mat(0x4a6a44, { flatShading: true })); cerro.scale.y = 0.35; cerro.position.set(10, -6, -120); sc.add(cerro);
  return { sol, hemi };
}
/** Destello enorme de luz blanca (para explosiones lejanas): d.poner(k) con k 0..1 (0 apagado). Pon un plano blanco delante de la cámara. */
export function destello(sc, cam) {
  const pl = new THREE.Mesh(new THREE.PlaneGeometry(10, 10), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthTest: false, depthWrite: false, fog: false }));
  pl.renderOrder = 999; sc.add(pl); const luz = new THREE.PointLight(0xfff6e8, 0, 0, 0.5); sc.add(luz);
  const v = new THREE.Vector3();
  return { poner(k, fuente = null) { cam.updateMatrixWorld(); cam.getWorldDirection(v); pl.position.copy(cam.position).addScaledVector(v, 0.5); pl.quaternion.copy(cam.quaternion);
    pl.material.opacity = Math.min(1, k); pl.visible = k > 0.001; if (fuente) { luz.position.copy(fuente); luz.intensity = 40000 * k; } } };
}
/** Selva tropical densa de día (Filipinas): suelo de hojas, árboles altos, palmeras, helechos y arbustos; claro en (0,0) de radio `claro`.
 *  noche=true la oscurece (luna). */
export function selvaTropical(sc, { claro = 6, semilla = 12, noche = false, n = 160 } = {}) {
  if (noche) { M.cielo(sc, '#03060a', '#0e1a14'); sc.fog = new THREE.FogExp2(0x07100b, 0.05); sc.add(new THREE.HemisphereLight(0x5a7a6a, 0x0a0c0a, 0.35)); }
  else { M.cielo(sc, '#9fb4a6', '#dfe6d2'); sc.fog = new THREE.Fog(0xa9b8a2, 12, 70); M.luces(sc, { sol: 2.0, cielo_: 1.2, dir: [-8, 22, 6], color: 0xfff1d4 }); }
  M.caja(sc, 200, 0.2, 200, 0, -0.1, 0, M.matTex(M.TEX.arena(), [50, 50], noche ? 0x2a2a1c : 0x5a5030));
  const az = _azar(semilla), arbs = [];
  for (let i = 0; i < n; i++) { const x = (az() - 0.5) * 90, z = (az() - 0.5) * 90; if (Math.hypot(x, z) < claro) continue;
    if (az() < 0.35) { arbs.push(palmera(sc, x, z, 7 + az() * 6, az)); } else arbs.push(arbolSelva(sc, x, z, 10 + az() * 10, az)); }
  const ver = [0x2f5a24, 0x3d6b2a, 0x264a1d, 0x4c7a32];
  for (let i = 0; i < 220; i++) { const x = (az() - 0.5) * 70, z = (az() - 0.5) * 70; if (Math.hypot(x, z) < claro * 0.7) continue;
    const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.5 + az() * 1.1, 0), M.mat(ver[Math.floor(az() * 4)], { flatShading: true, roughness: 1 })); m.position.set(x, 0.4, z); m.scale.y = 0.65; m.castShadow = true; sc.add(m); }
  return { arbs };
}
/** Palmera (tronco curvo + hojas). */
export function palmera(sc, x, z, h = 9, az = Math.random) {
  const g = new THREE.Group(), tr = M.mat(0x6a5a44, { roughness: 1 }), ho = M.mat(0x3d6b2a, { roughness: 1, side: THREE.DoubleSide });
  for (let i = 0; i < 6; i++) { const s = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.26, h / 6 + 0.05, 7), tr); s.position.set(Math.sin(i / 6) * 0.8 * (i / 6), h / 12 + i * h / 6, 0); s.rotation.z = -0.08 * i / 6; g.add(s); }
  for (let k = 0; k < 8; k++) { const f = new THREE.Mesh(new THREE.PlaneGeometry(4, 0.8), ho); f.position.set(0.8, h, 0); f.rotation.set(Math.PI / 2 + 0.4, 0, k * Math.PI / 4); f.translateX(1.8); f.castShadow = true; g.add(f); }
  g.position.set(x, 0, z); g.rotation.y = az() * 6; sc.add(g); return g;
}
/** Volantes de papel que caen del cielo dando vueltas (n hojas alrededor de (x,z) en un radio r). v.mover(t). */
export function volantes(sc, { n = 60, x = 0, z = 0, r = 12, alto = 30, semilla = 5 } = {}) {
  const az = _azar(semilla), m = new THREE.MeshStandardMaterial({ color: 0xf4f0e4, roughness: 0.9, side: THREE.DoubleSide }), hs = [];
  for (let i = 0; i < n; i++) { const h = new THREE.Mesh(new THREE.PlaneGeometry(0.21, 0.3), m); h.userData = { x: x + (az() - 0.5) * 2 * r, z: z + (az() - 0.5) * 2 * r, y0: alto * (0.3 + az()), v: 1.2 + az() * 0.8, f: az() * 6 };
    h.castShadow = true; sc.add(h); hs.push(h); }
  return { hs, mover(t) { hs.forEach(h => { const u = h.userData, y = Math.max(0.02, u.y0 - u.v * t);
    h.position.set(u.x + Math.sin(t * 1.3 + u.f) * 0.6, y, u.z + Math.cos(t * 1.1 + u.f) * 0.6);
    if (y > 0.03) h.rotation.set(t * 2 + u.f, t * 1.4 + u.f, Math.sin(t * 3 + u.f)); else h.rotation.set(-Math.PI / 2, 0, u.f); }); } };
}
/** Choza de campaña de madera y hojas de palma (sin pared adelante, +Z), con lámpara de aceite colgada. Centro (x,z). l.mover(t) titila. */
export function chozaLampara(sc, x = 0, z = 0) {
  const g = new THREE.Group(); g.position.set(x, 0, z); sc.add(g); const ma = M.mat(0x5a4430, { roughness: 1 }), pa = M.mat(0x8a7a4a, { roughness: 1, side: THREE.DoubleSide });
  const add = (w, h, d, x_, y_, z_, mm) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x_, y_, z_); b.castShadow = true; b.receiveShadow = true; g.add(b); return b; };
  for (const [a, b] of [[-2, -1.6], [2, -1.6], [-2, 1.6], [2, 1.6]]) add(0.15, 2.6, 0.15, a, 1.3, b, ma);
  add(4.2, 2.6, 0.08, 0, 1.3, -1.6, pa); add(0.08, 2.6, 3.2, -2, 1.3, 0, pa); add(0.08, 2.6, 3.2, 2, 1.3, 0, pa);
  for (const s of [-1, 1]) { const t = add(4.6, 0.1, 2.3, 0, 3.0, s * 0.85, pa); t.rotation.x = s * 0.45; }
  add(1.2, 0.06, 0.7, 0.8, 0.75, -0.9, ma); for (const [a, b] of [[0.3, -1.15], [1.3, -1.15], [0.3, -0.65], [1.3, -0.65]]) add(0.06, 0.75, 0.06, a, 0.37, b, ma);
  const ll = brilloSprite('#ffb04a', 0.5); ll.position.set(0.8, 2.1, -0.3); g.add(ll);
  add(0.12, 0.2, 0.12, 0.8, 2.0, -0.3, M.mat(0x3a3020, { metalness: 0.4 }));
  const luz = new THREE.PointLight(0xffa850, 10, 9, 1.4); luz.position.set(0.8, 2.0, -0.3); g.add(luz);
  return { g, mover(t) { const f = 0.85 + 0.1 * Math.sin(t * 11) + 0.05 * Math.sin(t * 27); luz.intensity = 10 * f; } };
}
/** Fogata (troncos + llama con brillo y luz). f.mover(t). */
export function fogata(sc, x = 0, z = 0) {
  const g = new THREE.Group(); g.position.set(x, 0, z); sc.add(g);
  for (let i = 0; i < 5; i++) { const l = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.8, 6), M.mat(0x3a2a1a)); l.rotation.set(Math.PI / 2 - 0.3, i * 1.25, 0); l.position.y = 0.12; g.add(l); }
  const fl = [brilloSprite('#ffd070', 0.9), brilloSprite('#ff8a30', 1.6, 0.7), brilloSprite('#ff6020', 2.6, 0.35)]; fl.forEach((f, i) => { f.position.y = 0.35 + i * 0.1; g.add(f); });
  const luz = new THREE.PointLight(0xff9a40, 14, 14, 1.3); luz.position.y = 0.7; luz.castShadow = true; luz.shadow.mapSize.set(1024, 1024); g.add(luz);
  return { g, mover(t) { const f = 0.8 + 0.15 * Math.sin(t * 12) + 0.08 * Math.sin(t * 29); luz.intensity = 14 * f; fl.forEach((s, i) => s.scale.setScalar((0.9 + i * 0.8) * f)); } };
}
/** Carpa de campaña pequeña (triangular) frente hacia +Z. */
export function carpa(sc, x = 0, z = 0, color = 0xc8701e) {
  const g = new THREE.Group(); g.position.set(x, 0, z); sc.add(g);
  const sh = new THREE.Shape(); sh.moveTo(-1.1, 0); sh.lineTo(1.1, 0); sh.lineTo(0, 1.3); sh.closePath();
  const geo = new THREE.ExtrudeGeometry(sh, { depth: 2.2, bevelEnabled: false }); geo.translate(0, 0, -1.1);
  const m = new THREE.Mesh(geo, M.mat(color, { roughness: 0.8 })); m.castShadow = true; m.receiveShadow = true; g.add(m);
  const boca = new THREE.Mesh(new THREE.ShapeGeometry((() => { const s = new THREE.Shape(); s.moveTo(-0.5, 0); s.lineTo(0.5, 0); s.lineTo(0, 0.8); s.closePath(); return s; })()), M.mat(0x120c08));
  boca.position.set(0, 0.01, 1.11); g.add(boca); return g;
}
/** Viste a una persona con uniforme de un solo color (cambia el color de la ropa de su textura y deja la piel).
 *  Sirve para soldados de otra época (p. ej. japonés de 1944 → caqui oliva). Llamar ANTES de esperar(). */
export function uniformar(p, { color = [118, 112, 72], claro = 1.0 } = {}) {
  p.traverse(o => { if (!o.isMesh) return; (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => {
    const mp = m.map; if (!mp || !/body/i.test(m.name + ' ' + (mp.name || '') + ' ' + (mp.image?.src || ''))) return;
    const pinta = () => { const im = mp.image; if (!im || !im.width) return false;
      const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const g = c.getContext('2d'); g.drawImage(im, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height), a = d.data;
      for (let i = 0; i < a.length; i += 4) { const r = a[i], gg = a[i + 1], b = a[i + 2], mx = Math.max(r, gg, b), mn = Math.min(r, gg, b), s = mx ? (mx - mn) / mx : 0;
        let h = 0; if (mx !== mn) { if (mx === r) h = 60 * (((gg - b) / (mx - mn)) % 6); else if (mx === gg) h = 60 * ((b - r) / (mx - mn) + 2); else h = 60 * ((r - gg) / (mx - mn) + 4); } if (h < 0) h += 360;
        const piel = r > gg && gg > b && h < 45 && s > 0.18 && s < 0.68 && mx > 70 && (r - b) > 25;
        if (piel) continue; const l = Math.min(1.4, (0.3 * r + 0.59 * gg + 0.11 * b) / 255 * 1.6 + 0.25) * claro;
        a[i] = Math.min(255, color[0] * l); a[i + 1] = Math.min(255, color[1] * l); a[i + 2] = Math.min(255, color[2] * l); }
      g.putImageData(d, 0, 0); const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; tx.flipY = mp.flipY; m.map = tx; m.needsUpdate = true; return true; };
    if (!pinta()) { const iv = setInterval(() => { if (pinta()) clearInterval(iv); }, 100); }
  }); });
  return p;
}
/** Gorra militar de campaña (con visera corta) en la cabeza. g.seguir() después de setTime. */
export function gorraMilitar(sc, p, color = 0x6a6440) {
  const g = new THREE.Group(), m = M.mat(color, { roughness: 0.9 });
  const cop = new THREE.Mesh(new THREE.CylinderGeometry(0.105, 0.11, 0.09, 18), m); g.add(cop);
  const vis = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.012, 18, 1, false, -Math.PI / 2.4, Math.PI / 1.2), M.mat(0x2a2618)); vis.position.set(0, -0.04, 0.04); vis.scale.set(1, 1, 1.5); g.add(vis);
  sc.add(g); const v = new THREE.Vector3(), q = new THREE.Quaternion();
  return { g, seguir(dy = 0.135) { p.updateMatrixWorld(true); const h = p.getObjectByName('Bip01_Head'); h.getWorldPosition(v);
    g.position.copy(v); g.position.y += dy; g.rotation.set(0, p.rotation.y, 0); } };
}

// ======================= 24-nov: faro en isla rocosa (Flannan 1900), cuarto de guardián con reloj y percheros =======================
/** Isla rocosa con acantilados (sale del mar en y=0, meseta arriba en y=alto) y FARO blanco con casa de guardianes.
 *  Centro de la meseta en (0, alto, 0). f.lampara(k 0..1, t) enciende/apaga la luz (con haz que gira). f.puerta = posición de la puerta. */
export function faroIsla(sc, { alto = 22, semilla = 7, r = 26 } = {}) {
  const az = _azar(semilla), roca = M.mat(0x2e2c2a, { roughness: 1, flatShading: true }), pasto = M.mat(0x2f3a24, { roughness: 1, flatShading: true });
  const base = new THREE.Mesh(new THREE.CylinderGeometry(r, r * 1.25, alto + 6, 11, 3), roca); base.position.y = alto / 2 - 3;
  const pa = base.geometry.attributes.position; for (let i = 0; i < pa.count; i++) { const x = pa.getX(i), z = pa.getZ(i), d = Math.hypot(x, z); if (d > 1) { const f = 1 + (az() - 0.5) * 0.18; pa.setX(i, x * f); pa.setZ(i, z * f); } }
  base.geometry.computeVertexNormals(); base.castShadow = base.receiveShadow = true; sc.add(base);
  const top = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.97, r, 0.8, 11), pasto); top.position.y = alto + 0.2; top.receiveShadow = true; sc.add(top);
  for (let i = 0; i < 26; i++) { const a = az() * 6.283, b = new THREE.Mesh(new THREE.DodecahedronGeometry(2 + az() * 5), roca); b.position.set(Math.cos(a) * (r + az() * 3), az() * alto * 0.7, Math.sin(a) * (r + az() * 3)); b.rotation.set(az(), az(), az()); b.castShadow = true; sc.add(b); }
  const g = new THREE.Group(); g.position.set(0, alto + 0.6, 0); sc.add(g);
  const blanco = M.mat(0xe8e4da, { roughness: 0.7 }), gris = M.mat(0x3a3d40, { roughness: 0.5, metalness: 0.4 });
  const torre = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.9, 16, 24), blanco); torre.position.y = 8; torre.castShadow = true; g.add(torre);
  const balcon = new THREE.Mesh(new THREE.CylinderGeometry(2.3, 2.3, 0.3, 24), gris); balcon.position.y = 16.1; g.add(balcon);
  const baranda = new THREE.Mesh(new THREE.CylinderGeometry(2.3, 2.3, 0.8, 24, 1, true), new THREE.MeshStandardMaterial({ color: 0x2a2c2e, wireframe: true })); baranda.position.y = 16.6; g.add(baranda);
  const vidrioM = new THREE.MeshStandardMaterial({ color: 0x1a2228, roughness: 0.1, metalness: 0.6, emissive: 0xffe0a0, emissiveIntensity: 0 });
  const linterna = new THREE.Mesh(new THREE.CylinderGeometry(1.3, 1.3, 2.2, 16), vidrioM); linterna.position.y = 17.4; g.add(linterna);
  const cupula = new THREE.Mesh(new THREE.SphereGeometry(1.4, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), gris); cupula.position.y = 18.5; g.add(cupula);
  const casa = new THREE.Mesh(new THREE.BoxGeometry(9, 3.6, 6), blanco); casa.position.set(-6, 1.8, 0); casa.castShadow = casa.receiveShadow = true; g.add(casa);
  const techo = new THREE.Mesh(new THREE.BoxGeometry(9.4, 0.4, 6.4), gris); techo.position.set(-6, 3.75, 0); g.add(techo);
  for (let i = 0; i < 3; i++) { const v = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.0, 0.05), M.mat(0x101418)); v.position.set(-9 + i * 2.6, 2.1, 3.03); g.add(v); }
  const puerta = new THREE.Mesh(new THREE.BoxGeometry(1.0, 2.1, 0.05), M.mat(0x2a3a4a)); puerta.position.set(-1.8, 1.05, 3.03); g.add(puerta);
  const muro = M.mat(0x8a8680, { roughness: 1 }); for (const [w, x, z, ry] of [[20, -4, 7, 0], [20, -4, -7, 0], [14, -14, 0, Math.PI / 2], [14, 6, 0, Math.PI / 2]]) { const m = new THREE.Mesh(new THREE.BoxGeometry(w, 1.1, 0.4), muro); m.position.set(x, 0.55, z); m.rotation.y = ry; m.castShadow = true; g.add(m); }
  const mastil = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 7, 6), gris); mastil.position.set(3.5, 3.5, 5); g.add(mastil);
  const luz = new THREE.PointLight(0xffe0a0, 0, 60, 1.4); luz.position.y = 17.4; g.add(luz);
  const haz = cono(g, 0, 17.4, 0, 60, 7, 0xfff0c0, 0.12, [0, 0, Math.PI / 2]); haz.visible = false;
  return { g, alto, puerta: new THREE.Vector3(-1.8, alto + 0.6, 3.2),
    lampara(k, t = 0) { vidrioM.emissiveIntensity = 3 * k; luz.intensity = 400 * k; haz.visible = k > 0.05; haz.material.opacity = 0.12 * k; haz.parent.rotation.y = 0; haz.rotation.set(0, t * 1.2, Math.PI / 2); } };
}
/** Cuarto de los guardianes de un faro de 1900 (cocina): paredes encaladas, mesa con sillas, chimenea apagada, reloj de pared
 *  (manecillas quietas), 3 ganchos junto a la puerta con UN solo impermeable amarillo. Puerta en x=-3, reloj en (0, 2.1, -2.95). */
export function cuartoFaro(sc, { abrigos = 1 } = {}) {
  sc.background = new THREE.Color(0x0b0c0e);
  const cal = M.mat(0xcfc8b8, { roughness: 1 }), mad = M.mat(0x6a4a30, { roughness: 0.9 }), piedra = M.mat(0x5a5650, { roughness: 1 });
  M.caja(sc, 6.2, 0.1, 6, 0, -0.05, 0, M.mat(0x5a4a3a)); M.caja(sc, 6.2, 0.1, 6, 0, 3.05, 0, cal);
  M.caja(sc, 6.2, 3.1, 0.1, 0, 1.5, -3, cal); M.caja(sc, 0.1, 3.1, 6, -3.1, 1.5, 0, cal); M.caja(sc, 0.1, 3.1, 6, 3.1, 1.5, 0, cal);
  M.caja(sc, 1.6, 0.08, 0.9, 0.3, 0.78, -0.6, mad); for (const [x, z] of [[-0.4, -0.95], [1.0, -0.95], [-0.4, -0.25], [1.0, -0.25]]) M.caja(sc, 0.07, 0.78, 0.07, x, 0.39, z, mad);
  for (const [x, z] of [[-0.8, -0.6], [1.4, -0.6]]) { M.caja(sc, 0.42, 0.06, 0.42, x, 0.46, z, mad); M.caja(sc, 0.06, 0.5, 0.42, x + (x < 0 ? -0.2 : 0.2), 0.72, z, mad); }
  M.caja(sc, 1.6, 1.4, 0.5, 2.0, 0.7, -2.75, piedra); M.caja(sc, 0.9, 0.8, 0.1, 2.0, 0.45, -2.5, M.mat(0x0a0a0a)); M.caja(sc, 1.8, 0.12, 0.6, 2.0, 1.45, -2.72, mad);
  const reloj = new THREE.Group(); reloj.position.set(-0.6, 2.15, -2.93); sc.add(reloj);
  const cara = new THREE.Mesh(new THREE.CircleGeometry(0.28, 32), M.mat(0xf2ead8)); reloj.add(cara);
  const aro = new THREE.Mesh(new THREE.TorusGeometry(0.29, 0.035, 8, 32), mad); reloj.add(aro);
  for (let i = 0; i < 12; i++) { const m = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.05, 0.01), M.mat(0x111111)); const a = i / 12 * Math.PI * 2; m.position.set(Math.sin(a) * 0.23, Math.cos(a) * 0.23, 0.01); m.rotation.z = -a; reloj.add(m); }
  const mano = (l, a) => { const m = new THREE.Mesh(new THREE.BoxGeometry(0.018, l, 0.01), M.mat(0x111111)); m.geometry.translate(0, l / 2, 0); m.position.z = 0.02; m.rotation.z = -a; reloj.add(m); };
  mano(0.14, 2.4); mano(0.21, 5.6); reloj.children.slice(-2).forEach(m => m.position.z = 0.025);
  M.caja(sc, 0.1, 2.2, 1.0, -3.04, 1.1, 1.6, M.mat(0x2a3a4a));
  M.caja(sc, 0.05, 0.08, 1.4, -3.03, 1.75, 0.0, mad);
  for (let i = 0; i < 3; i++) { const z = -0.5 + i * 0.5; M.caja(sc, 0.14, 0.03, 0.03, -2.97, 1.72, z, M.mat(0x222222));
    if (i < abrigos) { const ab = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.24, 1.0, 10), M.mat(0xd8b020, { roughness: 0.35 })); ab.position.set(-2.86, 1.2, z); ab.castShadow = true; sc.add(ab);
      const hom = new THREE.Mesh(new THREE.SphereGeometry(0.14, 10, 8), M.mat(0xd8b020, { roughness: 0.35 })); hom.scale.set(1, 0.5, 1.2); hom.position.set(-2.86, 1.68, z); sc.add(hom); } }
  const vent = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.9), new THREE.MeshBasicMaterial({ color: 0x8aa0b4 })); vent.position.set(3.04, 1.8, 0.4); vent.rotation.y = -Math.PI / 2; sc.add(vent);
  sc.add(new THREE.HemisphereLight(0xc8d4e0, 0x2a2420, 0.7));
  const dia = new THREE.SpotLight(0xc8d8ea, 40, 12, 0.9, 0.6, 1.2); dia.position.set(3.0, 2.0, 0.4); dia.target.position.set(-2, 0.5, -0.5); dia.castShadow = true; sc.add(dia); sc.add(dia.target);
  return { reloj, puerta: new THREE.Vector3(-3, 0, 1.6) };
}

// ===================== 25-nov: Boeing 777, sala de radar, satélite, playa de rocas, robot submarino, velero, carguero, hoja impresa =====================
/** Avión de pasajeros de fuselaje ancho, ala baja y DOS motores grandes (tipo Boeing 777), blanco con franja azul y roja genérica (sin logos).
 *  Nariz hacia +X, largo ~63 m (escala 1 = metros reales). a.mover(t) hace titilar las luces; a.cabina(k) prende las ventanas. */
export function avion777(sc, { franja = 0x1b3f8a, franja2 = 0xc0222a } = {}) {
  const g = new THREE.Group(), bl = M.mat(0xf2f2ee, { roughness: 0.35, metalness: 0.25 }), gr = M.mat(0xb8bcc2, { roughness: 0.4, metalness: 0.4 });
  const R = 3.1, L = 46;
  const fus = new THREE.Mesh(new THREE.CylinderGeometry(R, R, L, 32), bl); fus.rotation.z = Math.PI / 2; g.add(fus);
  const nariz = new THREE.Mesh(new THREE.SphereGeometry(R, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), bl); nariz.rotation.z = -Math.PI / 2; nariz.position.x = L / 2; nariz.scale.set(1, 2.2, 1); g.add(nariz);
  const cola = new THREE.Mesh(new THREE.CylinderGeometry(R, 0.6, 13, 32), bl); cola.rotation.z = -Math.PI / 2; cola.position.set(-L / 2 - 6.5, 1.2, 0); g.add(cola);
  const panza = new THREE.Mesh(new THREE.CylinderGeometry(R * 1.01, R * 1.01, L, 32, 1, true, Math.PI * 0.75, Math.PI * 0.5), gr); panza.rotation.z = Math.PI / 2; g.add(panza);
  for (const [c, a0] of [[franja, 0.30], [franja2, 0.27]]) for (const s of [1, -1]) {
    const f = new THREE.Mesh(new THREE.CylinderGeometry(R * 1.012, R * 1.012, L - 2, 32, 1, true, Math.PI * (s > 0 ? a0 : 2 - a0 - 0.03), Math.PI * 0.03), M.mat(c, { roughness: 0.4 }));
    f.rotation.z = Math.PI / 2; g.add(f); }
  const vi = M.mat(0x0d1520, { roughness: 0.08, metalness: 0.8 });
  const pb = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.9, 3.6), vi); pb.position.set(L / 2 + 3.2, 1.35, 0); pb.rotation.z = -0.5; g.add(pb);
  const ventanas = [];
  for (let i = 0; i < 34; i++) for (const s of [1, -1]) { const w = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.5, 0.06), emis(0xffe2a8, 0.8)); w.position.set(L / 2 - 2 - i * 1.25, 0.9, s * (R - 0.02)); g.add(w); ventanas.push(w); }
  // alas en flecha (ala baja)
  for (const s of [1, -1]) { const sh = new THREE.Shape(); sh.moveTo(6, 0); sh.lineTo(-4, 0); sh.lineTo(-16, s * 30); sh.lineTo(-12, s * 30); sh.closePath();
    const ala = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.5, bevelEnabled: false }), bl); ala.rotation.x = Math.PI / 2; ala.position.set(2, -1.6, 0); g.add(ala);
    const e = new THREE.Mesh(new THREE.CylinderGeometry(1.7, 1.5, 7, 24), M.mat(0xdedcd6, { roughness: 0.4, metalness: 0.4 })); e.rotation.z = Math.PI / 2; e.position.set(5, -3.4, s * 9.8); g.add(e);
    const boca = new THREE.Mesh(new THREE.CircleGeometry(1.5, 24), M.mat(0x111111)); boca.rotation.y = Math.PI / 2; boca.position.set(8.55, -3.4, s * 9.8); g.add(boca);
    const pil = new THREE.Mesh(new THREE.BoxGeometry(4, 1.6, 0.4), bl); pil.position.set(3.5, -2.3, s * 9.8); g.add(pil); }
  const deriva = new THREE.Shape(); deriva.moveTo(0, 0); deriva.lineTo(-9, 0); deriva.lineTo(-11, 11); deriva.lineTo(-7, 11); deriva.closePath();
  const dv = new THREE.Mesh(new THREE.ExtrudeGeometry(deriva, { depth: 0.4, bevelEnabled: false }), bl); dv.position.set(-L / 2 - 2, 2.2, -0.2); g.add(dv);
  for (const s of [1, -1]) { const hz = new THREE.Shape(); hz.moveTo(0, 0); hz.lineTo(-5, 0); hz.lineTo(-9, s * 10); hz.lineTo(-7, s * 10); hz.closePath();
    const h = new THREE.Mesh(new THREE.ExtrudeGeometry(hz, { depth: 0.3, bevelEnabled: false }), bl); h.rotation.x = Math.PI / 2; h.position.set(-L / 2 - 3, 1.6, 0); g.add(h); }
  const lr = emis(0xff2020, 5), lv = emis(0x20ff50, 5), lb = emis(0xffffff, 8);
  const nl = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), lr); nl.position.set(-12, -1.6, -30); g.add(nl);
  const nv = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), lv); nv.position.set(-12, -1.6, 30); g.add(nv);
  const bal = new THREE.Mesh(new THREE.SphereGeometry(0.35, 8, 8), lr); bal.position.set(0, R + 0.2, 0); g.add(bal);
  const st = new THREE.Mesh(new THREE.SphereGeometry(0.35, 8, 8), lb); st.position.set(-L / 2 - 13, 1.2, 0); g.add(st);
  const hr = brilloSprite('#ff3030', 5, 0.9); hr.position.copy(nl.position); g.add(hr);
  const hv = brilloSprite('#30ff60', 5, 0.9); hv.position.copy(nv.position); g.add(hv);
  const hb = brilloSprite('#ff2020', 6, 0.9); hb.position.copy(bal.position); g.add(hb);
  const luzB = new THREE.PointLight(0xff3030, 0, 40); luzB.position.copy(bal.position); g.add(luzB);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  sc.add(g);
  return { g, cabina(k) { ventanas.forEach(w => { w.material.emissiveIntensity = 0.8 * k; }); },
    luces(on = true) { for (const o of [nl, nv, hr, hv]) o.visible = on; },
    mover(t) { const on = (t % 1.2) < 0.12; bal.visible = hb.visible = on; luzB.intensity = on ? 300 : 0; st.visible = (t % 1.5) < 0.08; } };
}
/** Pantalla de radar de control aéreo (canvas). r.dibujar(t, {k: 0..1 avance del avión, visible, etiqueta}) ; r.mesh = plano. */
export function pantallaRadar(sc, ancho = 1.2, alto = 1.2) {
  const cv = document.createElement('canvas'); cv.width = cv.height = 512; const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(ancho, alto), new THREE.MeshBasicMaterial({ map: tx })); sc.add(mesh);
  const otros = [[120, 140, 'SIA22'], [380, 110, 'CPA715'], [400, 380, 'TGW8'], [150, 400, 'AXM50']];
  return { mesh, dibujar(t, { k = 0, visible = true, etiqueta = 'MAS370', perdido = false } = {}) {
    const g = cv.getContext('2d'); g.fillStyle = '#020a06'; g.fillRect(0, 0, 512, 512);
    g.strokeStyle = 'rgba(40,200,110,0.35)'; g.lineWidth = 1.5; for (const r of [60, 120, 180, 240]) { g.beginPath(); g.arc(256, 256, r, 0, 6.3); g.stroke(); }
    g.beginPath(); g.moveTo(256, 0); g.lineTo(256, 512); g.moveTo(0, 256); g.lineTo(512, 256); g.stroke();
    g.fillStyle = 'rgba(80,160,120,0.25)'; g.beginPath(); g.moveTo(20, 470); g.bezierCurveTo(120, 380, 160, 300, 140, 200); g.lineTo(60, 120); g.lineTo(10, 160); g.closePath(); g.fill();
    const a = t * 2.2; const gr = g.createConicGradient ? g.createConicGradient(a - 0.8, 256, 256) : null;
    if (gr) { gr.addColorStop(0, 'rgba(60,255,140,0)'); gr.addColorStop(0.12, 'rgba(60,255,140,0.28)'); gr.addColorStop(0.125, 'rgba(60,255,140,0)'); g.fillStyle = gr; g.beginPath(); g.arc(256, 256, 250, 0, 6.3); g.fill(); }
    g.font = 'bold 18px monospace';
    for (const [x, y, n] of otros) { g.fillStyle = '#4cff98'; g.fillRect(x - 4, y - 4, 8, 8); g.fillText(n, x + 10, y - 6); }
    const x = 200 + k * 90, y = 330 - k * 110;
    if (visible) { g.fillStyle = '#ffe14a'; g.fillRect(x - 6, y - 6, 12, 12); g.fillText(etiqueta, x + 12, y - 10); g.fillText('FL350', x + 12, y + 12);
      g.strokeStyle = '#ffe14a'; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 30, y - 36); g.stroke(); }
    else if (perdido && Math.floor(t * 3) % 2) { g.strokeStyle = '#ff4a3a'; g.lineWidth = 3; g.strokeRect(x - 22, y - 22, 44, 44); g.fillStyle = '#ff4a3a'; g.fillText('SIN SEÑAL', x - 50, y + 46); }
    tx.needsUpdate = true; } };
}
/** Sala de control de tráfico aéreo de noche: escritorio largo con 3 pantallas de radar (centro en x=0, z=-0.6, cara hacia +Z), luz azulada.
 *  Silla del controlador en (0, 0, 0.35). Devuelve {radar (la pantalla del centro), lados:[...]}. */
export function salaRadar(sc) {
  sc.background = new THREE.Color(0x03050a); sc.add(new THREE.HemisphereLight(0x46608a, 0x08080a, 0.35));
  M.caja(sc, 14, 0.1, 10, 0, -0.05, 0, M.mat(0x1d2026)); M.caja(sc, 14, 3.2, 0.2, 0, 1.6, -2.2, M.mat(0x22262e));
  M.caja(sc, 4.6, 0.08, 1.0, 0, 0.78, -0.75, M.mat(0x2e3138, { roughness: 0.5 })); M.caja(sc, 4.6, 0.75, 0.9, 0, 0.38, -0.8, M.mat(0x23262c));
  const radar = pantallaRadar(sc, 0.95, 0.95); radar.mesh.position.set(0, 1.35, -1.18); radar.mesh.rotation.x = -0.12;
  const lados = [-1.3, 1.3].map(x => { const r = pantallaRadar(sc, 0.85, 0.85); r.mesh.position.set(x, 1.3, -1.12); r.mesh.rotation.set(-0.12, -x * 0.3, 0); return r; });
  for (const x of [-1.3, 0, 1.3]) M.caja(sc, 1.0, 1.0, 0.08, x, 1.33, -1.24, M.mat(0x111317));
  const l = new THREE.PointLight(0x5cff9a, 3, 3.5, 1.5); l.position.set(0, 1.35, -0.5); sc.add(l);
  M.caja(sc, 0.5, 0.08, 0.5, 0, 0.48, 0.35, M.mat(0x15171b)); M.caja(sc, 0.5, 0.6, 0.08, 0, 0.82, 0.62, M.mat(0x15171b));
  for (let i = 0; i < 4; i++) M.caja(sc, 0.9, 0.04, 0.3, -1.5 + i * 1.0, 0.83, -0.4, M.mat(0x0e0f12));
  return { radar, lados };
}
/** Satélite de comunicaciones (cuerpo dorado, 2 paneles solares y antena parabólica que mira a -Y). Centro en el origen del grupo. */
export function satelite(sc, escala = 1) {
  const g = new THREE.Group(), oro = M.mat(0xc8a040, { metalness: 0.8, roughness: 0.35 }), panel = M.mat(0x1a2a6a, { metalness: 0.5, roughness: 0.3, emissive: 0x0a1a4a, emissiveIntensity: 0.4 });
  const c = new THREE.Mesh(new THREE.BoxGeometry(2.2, 2.6, 2.2), oro); g.add(c);
  for (const s of [1, -1]) { const brazo = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 2, 6), M.mat(0xaaaaaa)); brazo.rotation.x = Math.PI / 2; brazo.position.z = s * 2; g.add(brazo);
    for (let i = 0; i < 3; i++) { const p = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.06, 2.6), panel); p.position.set(0, 0, s * (4 + i * 2.7)); g.add(p);
      const marco = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.04, 0.08), M.mat(0xcccccc)); marco.position.set(0, 0.04, s * (4 + i * 2.7 + 1.3)); g.add(marco); } }
  const plato = new THREE.Mesh(new THREE.SphereGeometry(1.6, 24, 12, 0, Math.PI * 2, 0, 0.9), M.mat(0xe8e8e8, { side: THREE.DoubleSide, roughness: 0.4 })); plato.rotation.x = Math.PI; plato.position.y = -2.4; g.add(plato);
  const ant = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 1.2, 6), M.mat(0xcccccc)); ant.position.y = -1.7; g.add(ant);
  g.scale.setScalar(escala); sc.add(g); return g;
}
/** Anillo de señal (onda que se expande): s.poner(pos, k 0..1, color). */
export function ondaSenal(sc, color = 0x5cffb0) {
  const m = new THREE.Mesh(new THREE.TorusGeometry(1, 0.04, 6, 64), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
  sc.add(m); return { m, poner(pos, k, escala = 30) { m.position.copy(pos); m.scale.setScalar(0.1 + k * escala); m.material.opacity = k <= 0 || k >= 1 ? 0 : (1 - k) * 0.9; } };
}
/** Playa de piedras volcánicas oscuras con arena gris (tipo isla de La Reunión), mar a -Z (usa marNoche + marDia). Orilla en z≈-4. */
export function playaRocas(sc, { semilla = 9, n = 140 } = {}) {
  const arena = M.matTex(M.TEX.arena(), [10, 10], 0x77736a);
  const p = new THREE.Mesh(new THREE.PlaneGeometry(120, 40, 60, 20), arena); p.rotation.x = -Math.PI / 2; p.position.set(0, 0.05, 14);
  p.position.y = 0; p.receiveShadow = true; sc.add(p);
  const az = _azar(semilla), roca = M.matTex(M.TEX.roca(), [1, 1], 0x3a3836);
  for (let i = 0; i < n; i++) { const r = 0.15 + az() * 0.55, m = new THREE.Mesh(new THREE.DodecahedronGeometry(r, 0), roca);
    m.position.set((az() - 0.5) * 50, r * 0.4, -3 + az() * 22); m.rotation.set(az() * 3, az() * 3, az() * 3); m.scale.y = 0.6; m.castShadow = true; m.receiveShadow = true; sc.add(m); }
  for (let i = 0; i < 8; i++) { const m = new THREE.Mesh(new THREE.DodecahedronGeometry(4 + az() * 4, 1), roca); m.position.set(-60 + i * 16, 2, 34 + az() * 8); sc.add(m); }
  return p;
}
/** Pieza de ala (flaperón) blanca y sucia, ~2,5 x 1 m, con lapas. Acostada en el piso, centro en (x, z). */
export function flaperon(sc, x = 0, z = 0, giro = 0) {
  const g = new THREE.Group(), bl = M.mat(0xd8d4c6, { roughness: 0.8 });
  const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(2.6, 0); sh.lineTo(2.4, 0.95); sh.lineTo(0.15, 1.05); sh.closePath();
  const pz = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.18, bevelEnabled: true, bevelSize: 0.05, bevelThickness: 0.05 }), bl); pz.rotation.x = -Math.PI / 2 + 0.12; pz.position.set(-1.3, 0.15, 0.5); pz.castShadow = true; g.add(pz);
  const az = _azar(4); for (let i = 0; i < 60; i++) { const l = new THREE.Mesh(new THREE.ConeGeometry(0.025, 0.05, 5), M.mat(0x6a6058)); l.position.set(-1.2 + az() * 2.4, 0.36, -0.4 + az() * 0.9); g.add(l); }
  g.position.set(x, 0, z); g.rotation.y = giro; sc.add(g); return g;
}
/** Fondo marino profundo y oscuro (barro con rocas) + robot submarino amarillo con focos que barre el fondo. r.mover(t, x) ; sonar visible. */
export function fondoMarino(sc, { semilla = 5 } = {}) {
  sc.background = new THREE.Color(0x00060c); sc.fog = new THREE.FogExp2(0x001018, 0.06); sc.add(new THREE.HemisphereLight(0x1a3a55, 0x000000, 0.25));
  const geo = new THREE.PlaneGeometry(200, 200, 80, 80); geo.rotateX(-Math.PI / 2); const a = geo.attributes.position, az = _azar(semilla);
  for (let i = 0; i < a.count; i++) a.setY(i, Math.sin(a.getX(i) * 0.15) * 0.4 + Math.sin(a.getZ(i) * 0.21) * 0.5 + az() * 0.15); geo.computeVertexNormals();
  const piso = new THREE.Mesh(geo, M.matTex(M.TEX.arena(), [30, 30], 0x5a5a50)); piso.receiveShadow = true; sc.add(piso);
  for (let i = 0; i < 60; i++) { const r = 0.2 + az() * 1.2, m = new THREE.Mesh(new THREE.DodecahedronGeometry(r, 0), M.matTex(M.TEX.roca(), [1, 1], 0x4a4842)); m.position.set((az() - 0.5) * 80, 0.1, (az() - 0.5) * 80); m.castShadow = true; sc.add(m); }
  const g = new THREE.Group(), am = M.mat(0xf2c21a, { roughness: 0.4, metalness: 0.2 });
  const cu = new THREE.Mesh(new THREE.CapsuleGeometry(0.45, 3.6, 8, 16), am); cu.rotation.z = Math.PI / 2; cu.castShadow = true; g.add(cu);
  const aleta = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.9, 0.06), M.mat(0x222222)); aleta.position.set(-2.1, 0.4, 0); g.add(aleta);
  const helice = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.9, 0.12), M.mat(0x333333)); helice.position.set(-2.5, 0, 0); g.add(helice);
  const foco = new THREE.SpotLight(0xdfefff, 220, 22, 0.55, 0.5, 1.2); foco.position.set(2.1, -0.2, 0); const tg = new THREE.Object3D(); tg.position.set(8, -6, 0); g.add(tg); foco.target = tg; foco.castShadow = true; g.add(foco);
  cono(g, 2.1, -0.2, 0, 9, 3.2, 0xbfe0ff, 0.06, [0, 0, Math.PI / 2 + 0.6]);
  const brillo = brilloSprite('#e8f4ff', 1.2, 0.95); brillo.position.set(2.3, -0.2, 0); g.add(brillo);
  const pl = new THREE.PointLight(0xfff0c0, 8, 6, 1.5); pl.position.set(0, 1.5, 2); g.add(pl);
  const son = new THREE.Mesh(new THREE.PlaneGeometry(1, 30), new THREE.MeshBasicMaterial({ color: 0x40ffb0, transparent: true, opacity: 0.18, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  son.rotation.x = -Math.PI / 2; son.position.y = 0.15; sc.add(son);
  sc.add(g);
  return { robot: g, mover(t, x = 0, z = 0) { g.position.set(x, 4 + Math.sin(t * 0.8) * 0.15, z); helice.rotation.x = t * 30; son.position.set(x - 1, 0.15, z); son.material.opacity = 0.12 + 0.1 * Math.abs(Math.sin(t * 4)); } };
}
/** Velero pequeño de un mástil (sloop de ~6,5 m, casco blanco, vela mayor y foque). Proa hacia +X. v.escorar(rad). */
export function velero(sc, { color = 0xf2f0ea } = {}) {
  const g = new THREE.Group(), bl = M.mat(color, { roughness: 0.5 }), ma = M.mat(0x9a9a9a, { metalness: 0.6, roughness: 0.4 }), ve = M.mat(0xf0ece0, { roughness: 1, side: THREE.DoubleSide });
  const casco = new THREE.Shape(); casco.moveTo(-3.2, 0.9); casco.lineTo(3.4, 0.9); casco.quadraticCurveTo(3.2, -0.1, 2.2, -0.4); casco.lineTo(-2.8, -0.4); casco.lineTo(-3.2, 0.9);
  for (const s of [1, -1]) { const c = new THREE.Mesh(new THREE.ExtrudeGeometry(casco, { depth: 0.05, bevelEnabled: false }), bl); c.position.z = s * 1.1; c.castShadow = true; g.add(c); }
  const fondo = new THREE.Mesh(new THREE.BoxGeometry(5.6, 0.1, 2.1), bl); fondo.position.set(-0.3, -0.35, 0); g.add(fondo);
  const cub = new THREE.Mesh(new THREE.BoxGeometry(6.2, 0.08, 2.2), M.mat(0xc9b48a, { roughness: 0.8 })); cub.position.set(0, 0.88, 0); g.add(cub);
  const proa = new THREE.Mesh(new THREE.BoxGeometry(0.1, 1.3, 2.2), bl); proa.position.set(3.35, 0.25, 0); g.add(proa);
  const cab = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.55, 1.5), bl); cab.position.set(0.2, 1.2, 0); g.add(cab);
  const mastil = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 9, 8), ma); mastil.position.set(1.0, 5.4, 0); g.add(mastil);
  const botav = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 3.6, 6), ma); botav.rotation.z = Math.PI / 2; botav.position.set(-0.8, 1.9, 0); g.add(botav);
  const m1 = new THREE.Shape(); m1.moveTo(0, 0); m1.lineTo(-3.5, 0); m1.lineTo(0, 7.6); m1.closePath();
  const vm = new THREE.Mesh(new THREE.ShapeGeometry(m1), ve); vm.position.set(0.95, 1.95, 0.02); vm.castShadow = true; g.add(vm);
  const f1 = new THREE.Shape(); f1.moveTo(0, 0); f1.lineTo(2.6, 0); f1.lineTo(0, 7.2); f1.closePath();
  const fq = new THREE.Mesh(new THREE.ShapeGeometry(f1), ve); fq.position.set(1.1, 1.6, 0.02); g.add(fq);
  const luz = new THREE.Mesh(new THREE.SphereGeometry(0.08, 8, 8), emis(0xffffff, 6)); luz.position.set(1.0, 9.9, 0); g.add(luz);
  sc.add(g); return g;
}
/** Barco carguero grande lejano (casco oscuro, contenedores de colores, puente blanco a popa con luces). Proa +X, largo ~120 m. */
export function carguero(sc) {
  const g = new THREE.Group(), add = (w, h, d, x, y, z, mm) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mm); b.position.set(x, y, z); b.castShadow = true; g.add(b); return b; };
  add(120, 9, 18, 0, 0, 0, M.mat(0x1f2a33, { roughness: 0.6 })); add(120, 2, 18.2, 0, -3.5, 0, M.mat(0x7a1e1a));
  const proa = new THREE.Mesh(new THREE.ConeGeometry(9, 14, 3), M.mat(0x1f2a33)); proa.rotation.z = -Math.PI / 2; proa.position.set(66, 0.5, 0); g.add(proa);
  const cols = [0xb23a2a, 0x2a5aa0, 0xd8a030, 0x3a8a4a, 0x8a8a8a, 0xe06a20], az = _azar(12);
  for (let i = 0; i < 16; i++) for (let k = 0; k < 3; k++) add(5.6, 2.5, 16, 50 - i * 6, 5.8 + k * 2.6, 0, M.mat(cols[Math.floor(az() * cols.length)], { roughness: 0.7 }));
  add(10, 14, 16, -52, 11, 0, M.mat(0xe8e6de)); for (let k = 0; k < 4; k++) add(10.2, 0.8, 16.2, -52, 7 + k * 3, 0, emis(0xffe8b0, 0.6));
  sc.add(g); return g;
}
/** Hoja de impresora de computadora de los 70 (papel pautado) con columnas de letras y números; marca opcional en rojo "6EQUJ5" encerrado.
 *  h.circulo(k 0..1) dibuja el círculo y la palabra a mano. Acostada (cara arriba) en (x,y,z). */
export function hojaImpresa(sc, x = 0, y = 0.8, z = 0, { ancho = 0.5, marca = '6EQUJ5', palabra = 'Wow!' } = {}) {
  const c = document.createElement('canvas'); c.width = 600; c.height = 800; const g = c.getContext('2d'); const az = _azar(21);
  g.fillStyle = '#f2f0e4'; g.fillRect(0, 0, 600, 800); for (let i = 0; i < 800; i += 40) { g.fillStyle = '#dfe9d6'; g.fillRect(0, i, 600, 20); }
  for (let i = 0; i < 800; i += 30) { g.fillStyle = '#bbb'; g.beginPath(); g.arc(12, i + 15, 5, 0, 6.3); g.fill(); g.beginPath(); g.arc(588, i + 15, 5, 0, 6.3); g.fill(); }
  g.fillStyle = '#222'; g.font = 'bold 24px monospace'; const cx = 300, cy = 400;
  for (let l = 0; l < 32; l++) for (let k = 0; k < 10; k++) { const yy = 40 + l * 24, xx = 50 + k * 50;
    if (k === 4 && l >= 12 && l <= 17) continue;
    const v = az(); g.fillText(v < 0.55 ? '1' : v < 0.75 ? '2' : v < 0.85 ? '3' : ' ', xx, yy); }
  g.font = 'bold 26px monospace'; marca.split('').forEach((ch, i) => g.fillText(ch, 250, 40 + (12 + i) * 24));
  const img = g.getImageData(0, 0, 600, 800);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(ancho, ancho * 4 / 3), new THREE.MeshStandardMaterial({ map: t, roughness: 0.95 }));
  m.rotation.x = -Math.PI / 2; m.position.set(x, y, z); m.receiveShadow = true; sc.add(m);
  const ex = 258, ey = 40 + 14.5 * 24 - 8;
  return { m, circulo(k) { g.putImageData(img, 0, 0);
      if (k > 0) { g.strokeStyle = '#c0161c'; g.lineWidth = 6; g.beginPath(); g.ellipse(ex, ey, 26, 86, 0.03, -1.2, -1.2 + Math.min(1, k * 1.4) * 6.5); g.stroke(); }
      if (k > 0.7) { g.fillStyle = '#c0161c'; g.font = 'italic bold 60px Georgia, serif'; const n = Math.ceil(palabra.length * Math.min(1, (k - 0.7) / 0.3)); g.save(); g.translate(150, ey + 40); g.rotate(-0.25); g.fillText(palabra.slice(0, n), -110, 0); g.restore(); }
      t.needsUpdate = true; } };
}
/** Balsa salvavidas redonda inflable (tubos negros, piso, toldo naranja abierto adelante), diámetro ~1,9 m. Centro en el origen; piso en y≈0.1. */
export function balsaRedonda(sc, { toldo = true } = {}) {
  const g = new THREE.Group(), ne = M.mat(0x1c1d1f, { roughness: 0.5 }), na = M.mat(0xe0601a, { roughness: 0.8, side: THREE.DoubleSide });
  for (const [y, r] of [[0.18, 0.95], [0.48, 0.95]]) { const t = new THREE.Mesh(new THREE.TorusGeometry(r, 0.16, 12, 40), ne); t.rotation.x = Math.PI / 2; t.position.y = y; t.castShadow = true; g.add(t); }
  const piso = new THREE.Mesh(new THREE.CylinderGeometry(0.95, 0.95, 0.05, 32), ne); piso.position.y = 0.05; g.add(piso);
  if (toldo) { const d = new THREE.Mesh(new THREE.SphereGeometry(1.0, 24, 12, Math.PI * 0.35, Math.PI * 1.3, 0, Math.PI / 2), na); d.position.y = 0.55; d.scale.y = 1.15; d.castShadow = true; g.add(d);
    const arco = new THREE.Mesh(new THREE.TorusGeometry(1.0, 0.05, 8, 24, Math.PI), ne); arco.position.y = 0.55; arco.rotation.y = Math.PI * 0.35 + Math.PI / 2; g.add(arco); }
  sc.add(g); return g;
}
/** Ballena (silueta oscura simple, cola con aletas). Nariz hacia +X, largo ~12 m. b.userData.cola = pivote de la cola (rotation.z). */
export function ballena(sc) {
  const g = new THREE.Group(), m = M.mat(0x3a4650, { roughness: 0.5 });
  const c = new THREE.Mesh(new THREE.SphereGeometry(1.6, 24, 16), m); c.scale.set(4, 1, 1.1); g.add(c);
  const piv = new THREE.Group(); piv.position.x = -6; g.add(piv);
  const pe = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.35, 3, 12), m); pe.rotation.z = Math.PI / 2; pe.position.x = -1.5; piv.add(pe);
  const al = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.15, 4.2), m); al.position.x = -3.2; piv.add(al);
  for (const s of [1, -1]) { const a = new THREE.Mesh(new THREE.BoxGeometry(2, 0.12, 0.8), m); a.position.set(1.5, -0.8, s * 1.6); a.rotation.y = s * 0.5; g.add(a); }
  g.userData.cola = piv; g.traverse(o => { if (o.isMesh) o.castShadow = true; }); sc.add(g); return g;
}

// ======================= 26-nov: molino de viento de granja (1890), nave en forma de puro (1897), estallido de fuego y humo =======================
/** Molino de viento de granja (tipo americano de 1890: torre de madera de 4 patas, rueda de aspas y cola), ~9 m.
 *  Devuelve {g, rueda, cabeza, mover(t, vel), romper(k)}: romper(0..1) hace caer la cabeza y la rueda. */
export function molinoViento(sc, x = 0, z = 0, { alto = 9 } = {}) {
  const g = new THREE.Group(), mad = M.mat(0x6a5238, { roughness: 0.95 }), met = M.mat(0x5a5a58, { metalness: 0.6, roughness: 0.5 });
  const b = 1.4, a = 0.35;
  for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
    const p = new THREE.Mesh(new THREE.BoxGeometry(0.14, alto, 0.14), mad); p.position.set(sx * (b + a) / 2, alto / 2, sz * (b + a) / 2);
    p.rotation.set(-sz * Math.atan((b - a) / 2 / alto), 0, sx * Math.atan((b - a) / 2 / alto)); g.add(p);
  }
  for (let i = 1; i < 5; i++) { const y = i * alto / 5, w = b - (b - a) * (y / alto); for (const r of [0, Math.PI / 2]) for (const sg of [1, -1]) {
    const tr = new THREE.Mesh(new THREE.BoxGeometry(w + 0.1, 0.08, 0.08), mad); tr.position.set(r ? sg * w / 2 : 0, y, r ? 0 : sg * w / 2); tr.rotation.y = r; g.add(tr); } }
  const cabeza = new THREE.Group(); cabeza.position.set(0, alto + 0.2, 0); g.add(cabeza);
  const caja = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.45, 0.45), met); cabeza.add(caja);
  const cola = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.9, 0.04), M.mat(0x8a3020, { roughness: 0.8 })); cola.position.set(-1.6, 0.2, 0); cabeza.add(cola);
  const brazo = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.06, 0.06), met); brazo.position.set(-0.8, 0.1, 0); cabeza.add(brazo);
  const rueda = new THREE.Group(); rueda.position.set(0.6, 0, 0); cabeza.add(rueda);
  for (let i = 0; i < 18; i++) { const as = new THREE.Mesh(new THREE.BoxGeometry(0.03, 1.4, 0.32), M.mat(0x9a9a92, { metalness: 0.4, roughness: 0.6 }));
    const q = new THREE.Group(); q.rotation.x = i / 18 * Math.PI * 2; as.position.y = 1.0; as.rotation.y = 0.5; q.add(as); rueda.add(q); }
  const aro = new THREE.Mesh(new THREE.TorusGeometry(1.65, 0.03, 6, 40), met); aro.rotation.y = Math.PI / 2; rueda.add(aro);
  const bomba = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, alto, 6), met); bomba.position.y = alto / 2; g.add(bomba);
  const pozo = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.75, 0.6, 18), M.matTex(M.TEX.ladrillo(), [2, 1], 0x9a8a78)); pozo.position.y = 0.3; g.add(pozo);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  g.position.set(x, 0, z); sc.add(g);
  return { g, rueda, cabeza, mover(t, vel = 1) { rueda.rotation.x = t * vel; },
    romper(k) { const c = Math.min(1, k); cabeza.position.set(c * 2.2, alto + 0.2 - (alto - 0.4) * c * c, c * 0.8); cabeza.rotation.set(c * 1.6, 0, -c * 2.4); } };
}
/** Nave en forma de puro (cigarro) de los relatos de 1897: casco metálico, góndola debajo y luces. Frente hacia +X, ~10 m. */
export function naveCigarro(sc, escala = 1) {
  const g = new THREE.Group(), met = M.mat(0x8f8f88, { metalness: 0.7, roughness: 0.35 });
  const c = new THREE.Mesh(new THREE.SphereGeometry(1.2, 28, 16), met); c.scale.set(4.2, 1, 1); g.add(c);
  const gon = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.6, 0.8), M.mat(0x3a3430, { metalness: 0.4, roughness: 0.6 })); gon.position.y = -1.25; g.add(gon);
  for (const x of [-0.9, 0, 0.9]) { const v = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.25, 0.82), emis(0xffd890, 2)); v.position.set(x, -1.25, 0); g.add(v); }
  for (const s of [1, -1]) { const al = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.05, 1.6), met); al.position.set(-4.2, 0, s * 0.9); g.add(al);
    const al2 = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.6, 0.05), met); al2.position.set(-4.2, s * 0.9, 0); g.add(al2); }
  const luz = brilloSprite('#ffe6a0', 3, 0.9); luz.position.set(5.1, 0, 0); g.add(luz);
  const foco = new THREE.PointLight(0xffd890, 60, 25, 1.5); foco.position.set(0, -1.6, 0); g.add(foco);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; }); g.scale.setScalar(escala); sc.add(g); return g;
}
/** Explosión de fuego y humo en un punto: e.poner(k) con k = segundos desde el estallido (negativo = nada). */
export function estallido(sc, x, y, z, { tam = 6, n = 26 } = {}) {
  const fu = []; let s = 5; const az = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  for (let i = 0; i < n; i++) { const sp = brilloSprite(i % 3 ? '#ff8a2a' : '#fff0c0', 1, 1); sp.userData = { d: new THREE.Vector3(az() - 0.5, az() * 0.8, az() - 0.5).normalize(), v: 0.5 + az() }; sc.add(sp); fu.push(sp); }
  const humo = nubePolvo(sc, x, y - 0.5, z, 30, tam);
  const luz = new THREE.PointLight(0xff8a3a, 0, 60, 1.4); luz.position.set(x, y, z); sc.add(luz);
  return { poner(k) { fu.forEach(sp => { const u = sp.userData; sp.visible = k > 0 && k < 1.6;
      sp.position.set(x + u.d.x * k * tam * u.v, y + u.d.y * k * tam * u.v, z + u.d.z * k * tam * u.v); sp.scale.setScalar(tam * (0.3 + k) * u.v); sp.material.opacity = Math.max(0, 1 - k / 1.6); });
    luz.intensity = k > 0 ? 900 * Math.max(0, 1 - k / 1.2) : 0; humo.poner(k > 0 ? k * 0.9 : -1); } };
}

// ======================= 27-nov: aldea africana de chozas redondas (Camerún), lago en cráter, nube de gas que baja pegada al suelo =======================
/** Aldea de chozas redondas de barro con techo de paja cónico, en un valle con cerros verdes. noche=true: cielo oscuro y ventanas cálidas.
 *  Centro (0,0); las chozas quedan a los lados de un camino de tierra a lo largo de Z. Devuelve {chozas}. */
export function aldeaAfricana(sc, { noche = true, semilla = 6, n = 12 } = {}) {
  if (noche) { M.cielo(sc, '#04060e', '#1c2640'); sc.fog = new THREE.FogExp2(0x0e1424, 0.022);
    sc.add(new THREE.HemisphereLight(0x6a7ab0, 0x141210, 0.7)); const l = new THREE.DirectionalLight(0x9fb2ff, 0.9); l.position.set(-15, 25, 10); l.castShadow = true; l.shadow.mapSize.set(2048, 2048);
    Object.assign(l.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30 }); sc.add(l); }
  else { M.cielo(sc, '#9aa8b4', '#e4e2da'); sc.fog = new THREE.Fog(0xd6d6d0, 20, 120); M.luces(sc, { sol: 1.4, cielo_: 1.1, dir: [10, 20, 8], color: 0xfff0dc }); }
  M.caja(sc, 300, 0.2, 300, 0, -0.1, 0, M.matTex(M.TEX.arena(), [60, 60], noche ? 0x3a4a2a : 0x6a7a44));
  M.caja(sc, 4, 0.03, 300, 0, 0.01, 0, M.matTex(M.TEX.arena(), [2, 60], noche ? 0x5a4a38 : 0xa08060));
  const az = _azar(semilla), barro = M.mat(0x8a5a3a, { roughness: 1 }), paja = M.mat(0x9a8050, { roughness: 1, flatShading: true }), chozas = [];
  for (let i = 0; i < n; i++) { const lado = i % 2 ? 1 : -1, x = lado * (5 + az() * 6), z = 8 - Math.floor(i / 2) * 7 - az() * 2, r = 1.6 + az() * 0.6, g = new THREE.Group();
    const p = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 2.2, 18), barro); p.position.y = 1.1; p.castShadow = true; p.receiveShadow = true; g.add(p);
    const t = new THREE.Mesh(new THREE.ConeGeometry(r * 1.35, 2.2, 18), paja); t.position.y = 3.2; t.castShadow = true; g.add(t);
    const pu = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 1.5), noche && az() < 0.6 ? emis(0xffa040, 1.4) : M.mat(0x1a120c)); pu.position.set(0, 0.75, r + 0.01); g.add(pu);
    g.position.set(x, 0, z); g.rotation.y = lado > 0 ? -Math.PI / 2 : Math.PI / 2; sc.add(g); chozas.push(g); }
  for (let i = 0; i < 12; i++) { const a = az() * 6.28, R = 70 + az() * 40, h = 25 + az() * 30; const c = new THREE.Mesh(new THREE.SphereGeometry(h, 14, 10), M.mat(noche ? 0x1c2a1c : 0x4a6a3a, { flatShading: true })); c.scale.y = 0.45; c.position.set(Math.cos(a) * R, -h * 0.1, Math.sin(a) * R); sc.add(c); }
  return { chozas };
}
/** Nube de gas blanquecina que baja pegada al suelo como un río (dirección -Z por defecto). n.mover(t): t = segundos desde que llega.
 *  Avanza desde (x, z0) hacia z0 - vel*t, con ancho a. */
export function neblinaRasante(sc, { x = 0, z0 = 30, vel = 6, ancho = 16, n = 90, color = 'rgba(220,226,232,0.85)', op = 0.55 } = {}) {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, color); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const tx = new THREE.CanvasTexture(c), az = _azar(11), ps = [];
  for (let i = 0; i < n; i++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, depthWrite: false, opacity: 0 }));
    sp.userData = { dx: (az() - 0.5) * ancho, dz: az() * 18, y: 0.4 + az() * 1.6, s: 3 + az() * 4, w: az() * 6 }; sc.add(sp); ps.push(sp); }
  return { mover(t) { const frente = z0 - vel * t; ps.forEach(sp => { const u = sp.userData, z = frente + u.dz;
    sp.position.set(x + u.dx + Math.sin(t * 0.7 + u.w) * 0.6, u.y + Math.sin(t + u.w) * 0.15, z); sp.scale.setScalar(u.s * (1 + 0.1 * Math.sin(t + u.w)));
    sp.material.opacity = op * Math.min(1, Math.max(0, (z0 + 4 - z) / 6)); }); } };
}
/** Lago redondo dentro de un cráter (paredes empinadas), de noche o de día. Centro (0,0), radio r. l.burbujas(t, k): el agua se agita (k 0..1). */
export function lagoCrater(sc, { r = 30, noche = true, color = 0x1a3a4a } = {}) {
  if (noche) { M.cielo(sc, '#03050c', '#1a2238'); sc.fog = new THREE.FogExp2(0x0c1222, 0.01); sc.add(new THREE.HemisphereLight(0x7080b0, 0x121010, 0.8));
    const l = new THREE.DirectionalLight(0xa0b4ff, 1.1); l.position.set(-30, 40, 20); sc.add(l); }
  else { M.cielo(sc, '#8aa6c4', '#e2e6e2'); sc.fog = new THREE.Fog(0xd0d8dc, 40, 220); M.luces(sc, { sol: 1.8, cielo_: 1.1, dir: [20, 30, 10] }); }
  const geo = new THREE.CircleGeometry(r, 64, 0, Math.PI * 2); geo.rotateX(-Math.PI / 2);
  const agua = new THREE.Mesh(new THREE.PlaneGeometry(r * 2.2, r * 2.2, 70, 70).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color, roughness: 0.2, metalness: 0.4, flatShading: true })); sc.add(agua);
  const base = agua.geometry.attributes.position.array.slice();
  const pared = new THREE.Mesh(new THREE.CylinderGeometry(r * 2.2, r * 1.02, r * 0.6, 48, 4, true), M.mat(noche ? 0x24301e : 0x4a6a34, { side: THREE.DoubleSide, flatShading: true, roughness: 1 }));
  const pp = pared.geometry.attributes.position; const az = _azar(4); for (let i = 0; i < pp.count; i++) { pp.setX(i, pp.getX(i) * (1 + (az() - 0.5) * 0.06)); pp.setZ(i, pp.getZ(i) * (1 + (az() - 0.5) * 0.06)); }
  pared.geometry.computeVertexNormals(); pared.position.y = r * 0.3 - 0.2; sc.add(pared);
  return { agua, burbujas(t, k = 0) { const a = agua.geometry.attributes.position.array;
    for (let i = 0; i < a.length; i += 3) { const x = base[i], z = base[i + 2], d = Math.hypot(x, z); a[i + 1] = 0.08 * Math.sin(x * 0.3 + t) + k * Math.max(0, 1 - d / (r * 0.6)) * (0.9 * Math.sin(d * 0.8 - t * 6) + 0.4 * Math.sin(x * 1.3 + t * 9)); }
    agua.geometry.attributes.position.needsUpdate = true; agua.geometry.computeVertexNormals(); } };
}

// ======================= 27-nov: paso Diátlov — ladera nevada con pendiente, carpa larga de lona (con cortes), cedro grande =======================
/** Ladera nevada de montaña (sube hacia -Z con `incl` grados), con un escalón plano cavado en (0,0) para la carpa y el bosque abajo (+Z).
 *  noche=true: luna azul; 'dia': cielo gris claro. Devuelve {nieve(t)} (copos con viento) y la función alto(z) de la ladera. */
export function laderaNevada(sc, { noche = true, incl = 16, bosque = 34, viento = 1, semilla = 8 } = {}) {
  if (noche) { M.cielo(sc, '#03050c', '#1a2236'); sc.fog = new THREE.FogExp2(0x101828, 0.03);
    sc.add(new THREE.HemisphereLight(0x8ea4d8, 0x1a1c22, 0.9)); }
  else { M.cielo(sc, '#8a96a6', '#dfe3e8'); sc.fog = new THREE.FogExp2(0xc8ced6, 0.018); sc.add(new THREE.HemisphereLight(0xeef2ff, 0x6a6a70, 1.0)); }
  const l = new THREE.DirectionalLight(noche ? 0x9fb4ff : 0xfff4e8, noche ? 1.3 : 1.6); l.position.set(-14, 26, 10); l.castShadow = true; l.shadow.mapSize.set(2048, 2048);
  Object.assign(l.shadow.camera, { left: -25, right: 25, top: 25, bottom: -25, near: 1, far: 90 }); sc.add(l);
  const nv = M.mat(noche ? 0xb8c4d8 : 0xe8ecf2, { roughness: 0.95, flatShading: true }), tg = Math.tan(incl * Math.PI / 180);
  const alto = z => (z < -1.6 ? (-1.6 - z) * tg + 0.0 : z > 1.6 ? -(z - 1.6) * tg : 0);
  const geo = new THREE.PlaneGeometry(120, 140, 90, 110); geo.rotateX(-Math.PI / 2);
  const pa = geo.attributes.position, az = _azar(semilla);
  for (let i = 0; i < pa.count; i++) { const x = pa.getX(i), z = pa.getZ(i); const cerca = Math.abs(x) < 2.8 && Math.abs(z) < 2.2;
    pa.setY(i, (cerca ? 0 : alto(z)) + (cerca ? 0 : Math.sin(x * 0.4) * 0.12 + Math.cos(z * 0.5 + x * 0.2) * 0.1 + (az() - 0.5) * 0.06)); }
  geo.computeVertexNormals(); const piso = new THREE.Mesh(geo, nv); piso.receiveShadow = true; sc.add(piso);
  const tr = M.mat(0x1e1a16, { roughness: 1 }), ho = M.mat(noche ? 0x14221a : 0x24362a, { roughness: 1 });
  for (let i = 0; i < 160; i++) { const x = (az() - 0.5) * 110, z = bosque + az() * 50, h = 7 + az() * 8, g = new THREE.Group();
    const t = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.3, h, 6), tr); t.position.y = h / 2; g.add(t);
    for (let k = 0; k < 3; k++) { const c = new THREE.Mesh(new THREE.ConeGeometry(2 - k * 0.5, 3, 8), ho); c.position.y = h * 0.4 + k * 1.6; c.castShadow = true; g.add(c); }
    g.position.set(x, alto(z) - 0.2, z); sc.add(g); }
  const n = 2500, p = new Float32Array(n * 3); for (let i = 0; i < n; i++) p.set([(az() - 0.5) * 40, az() * 14, (az() - 0.5) * 40], i * 3);
  const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.BufferAttribute(p, 3));
  const copos = new THREE.Points(gg, new THREE.PointsMaterial({ color: 0xffffff, size: 0.06, transparent: true, opacity: 0.8 * viento, depthWrite: false })); sc.add(copos);
  return { alto, piso, nieve(t) { copos.position.set(((t * 6 * viento) % 20) - 10, -((t * 2) % 7), 0); } };
}
/** Carpa larga de lona (tipo carpa de expedición de los años 50), cumbrera a lo largo de X, largo ~4 m. cortes: n tajos negros en el
 *  costado que mira a +Z; hundida 0..1: el techo cede y queda cubierta de nieve. Devuelve el grupo. */
export function carpaLarga(sc, x = 0, z = 0, { largo = 4.2, cortes = 0, hundida = 0, color = 0xb8a888, noche = true } = {}) {
  const g = new THREE.Group(); g.position.set(x, 0, z); sc.add(g);
  const alto = 1.25 * (1 - 0.55 * hundida), sh = new THREE.Shape(); sh.moveTo(-1.0, 0); sh.lineTo(1.0, 0); sh.lineTo(0.1 * hundida, alto); sh.closePath();
  const geo = new THREE.ExtrudeGeometry(sh, { depth: largo, bevelEnabled: false }); geo.translate(0, 0, -largo / 2); geo.rotateY(Math.PI / 2);
  const lona = new THREE.Mesh(geo, M.mat(color, { roughness: 1, side: THREE.DoubleSide })); lona.castShadow = true; lona.receiveShadow = true; g.add(lona);
  for (const xx of [-largo / 2 - 0.05, largo / 2 + 0.05]) { const pal = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, alto + 0.3, 6), M.mat(0x5a4632)); pal.position.set(xx, (alto + 0.3) / 2, 0); g.add(pal); }
  const negro = M.mat(0x050505);
  const nz = alto, ny = 1, nl = Math.hypot(nz, ny);
  for (let i = 0; i < cortes; i++) { const c = new THREE.Mesh(new THREE.PlaneGeometry(0.06 + (i % 2) * 0.05, 0.45 + (i % 3) * 0.12), negro);
    const xx = -largo / 2 + 0.6 + i * (largo - 1.2) / Math.max(1, cortes - 1), y = alto * 0.45, zz = 1 - 0.45;
    c.position.set(xx, y + ny / nl * 0.012, zz + nz / nl * 0.012); c.lookAt(xx, y + ny / nl, zz + nz / nl); c.rotateZ((i % 2 ? 0.25 : -0.2)); g.add(c); }
  if (hundida > 0) { const nm = M.mat(noche ? 0xb8c4d8 : 0xf0f2f6, { roughness: 1, flatShading: true });
    for (let i = 0; i < 7; i++) { const c = new THREE.Mesh(new THREE.SphereGeometry(0.5, 10, 6), nm); c.scale.set(1.3, 0.35 * hundida + 0.1, 0.9);
      c.position.set(-largo / 2 + 0.4 + i * (largo - 0.8) / 6, alto * (0.55 + 0.25 * Math.sin(i * 2.3)), -0.35 + 0.3 * Math.cos(i * 1.7)); c.castShadow = true; g.add(c); }
    const banco = new THREE.Mesh(new THREE.SphereGeometry(1, 14, 8), nm); banco.scale.set(largo * 0.6, 0.35, 0.8); banco.position.set(0, 0.05, -1.2); g.add(banco); }
  return g;
}
/** Cedro siberiano grande (tronco grueso, ramas bajas quebradas). */
export function cedroGrande(sc, x = 0, z = 0, { h = 16 } = {}) {
  const g = new THREE.Group(); g.position.set(x, 0, z); sc.add(g);
  const tr = M.mat(0x3a2c22, { roughness: 1 }), ho = M.mat(0x1a2a1e, { roughness: 1 });
  const t = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.6, h, 10), tr); t.position.y = h / 2; t.castShadow = true; g.add(t);
  for (let k = 0; k < 6; k++) { const c = new THREE.Mesh(new THREE.ConeGeometry(3.4 - k * 0.45, 3.2, 10), ho); c.position.y = 6 + k * 1.8; c.castShadow = true; g.add(c); }
  for (let k = 0; k < 7; k++) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.07, 0.9 + (k % 3) * 0.3, 5), tr); r.position.set(Math.cos(k * 1.7) * 0.5, 1.6 + k * 0.5, Math.sin(k * 1.7) * 0.5);
    r.rotation.set(Math.sin(k) * 0.8, k, 1.2); g.add(r); }
  return g;
}

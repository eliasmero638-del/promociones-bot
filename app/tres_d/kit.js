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

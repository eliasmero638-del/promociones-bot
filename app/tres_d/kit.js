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

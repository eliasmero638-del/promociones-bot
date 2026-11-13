// fb3 Kecksburg · enganche: la bola de fuego cruza el cielo, cae detrás de los árboles y dos testigos miran.
export async function montar({ THREE, K, W, H, renderer, scene: s, cam, texto, dur }) {
  K.bosqueNoche(s, { claro: 9 });
  const bola = K.bolaFuego(s);
  const a = await K.persona(s, 'Male_Adult_04', 'm_idle_look_around_01.max.fbx', -0.42, 2.0, 180);
  const b = await K.persona(s, 'Female_Adult_02', 'f_idle_look_around_01.max.fbx', 0.45, 2.3, 172);
  const brillo = new THREE.PointLight(0xff7a2a, 0, 70, 1.4); brillo.position.set(-4, 3, -16); s.add(brillo);
  const fuego = K.brilloSprite('#ff7020', 1, 0.9); fuego.position.set(-5, 4, -22); s.add(fuego);
  await K.esperar(s);
  const vert = H > W, P0 = new THREE.Vector3(34, 32, -42), P1 = new THREE.Vector3(-5, 0, -22);
  const C1 = dur * 0.5, C2 = dur * 0.75, tc = dur * 0.62;            // tc = choque
  return t => {
    const k = Math.min(1, t / tc), pos = P0.clone().lerp(P1, k), dir = P1.clone().sub(P0);
    bola.poner(pos, dir, t < tc ? 1 : 0);
    const fl = t < tc ? 0 : Math.max(0, 1 - (t - tc) * 1.5); brillo.intensity = t < tc ? 0 : 900 * (0.35 + fl);
    fuego.visible = t >= tc; fuego.scale.setScalar(6 + 26 * fl + Math.sin(t * 20) * 0.6);
    a.userData.mixer.setTime(1 + t); b.userData.mixer.setTime(2 + t);
    const arriba = 25 + 20 * (1 - k); K.mirarArriba(a, arriba); K.mirarArriba(b, arriba);
    texto({ f: '9 de diciembre de 1965', t: 'Kecksburg', s: 'Pensilvania · EE. UU.' });
    if (t < C1) {          // de espaldas a ellos: el cielo y la bola que cruza
      const q = t / C1; cam.fov = vert ? 62 : 45; cam.position.set(-1.4, 1.0, 5.6 - q * 0.6); cam.lookAt(K.lerp(9, 3, q), K.lerp(9, 5.5, q), -20);
    } else if (t < C2) {   // la caída detrás de los árboles
      const q = (t - C1) / (C2 - C1); cam.fov = vert ? 55 : 40; cam.position.set(3.2, 1.3, 3.5); cam.lookAt(-5, K.lerp(5, 3, q), -22);
      cam.position.x += (t > tc ? Math.sin(t * 60) * 0.03 * fl : 0);
    } else {              // sus caras iluminadas de naranja
      const q = (t - C2) / (dur - C2); brillo.intensity = 1400; cam.fov = vert ? 40 : 30; cam.position.set(K.lerp(0.1, -0.05, q), 1.45, K.lerp(-1.9, -1.4, q)); cam.lookAt(-0.05, 1.55, 2.2);
    }
    renderer.render(s, cam);
  };
}

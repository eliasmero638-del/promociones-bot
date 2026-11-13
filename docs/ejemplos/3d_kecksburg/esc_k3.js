// fb3 · "parecía una estrella en llamas": la bola de fuego cruza sobre los pinos, despacio.
export async function montar({ THREE, K, W, H, renderer, scene: s, cam, texto, dur }) {
  K.bosqueNoche(s, { claro: 10, semilla: 41 });
  const bola = K.bolaFuego(s, 26);
  const est = new THREE.Group(); for (let i = 0; i < 300; i++) { const e = K.brilloSprite('#cfe0ff', 0.25 + Math.random() * 0.35, 0.8); e.position.set((Math.random() - 0.5) * 200, 25 + Math.random() * 60, -60 - Math.random() * 30); est.add(e); } s.add(est);
  const mama = await K.persona(s, 'Female_Adult_01', 'f_idle_look_around_01.max.fbx', -1.4, 2.6, 165);
  await K.esperar(s);
  const vert = H > W, P0 = new THREE.Vector3(34, 34, -40), P1 = new THREE.Vector3(-30, 12, -40);
  return t => {
    const k = t / dur, pos = P0.clone().lerp(P1, k); bola.poner(pos, P1.clone().sub(P0), 1);
    mama.userData.mixer.setTime(t); K.mirarArriba(mama, 38);
    texto({ f: 'Un niño de 8 años', t: '"Una estrella en llamas"', s: 'Así se lo contó a la radio' });
    cam.fov = vert ? K.lerp(62, 48, k) : K.lerp(46, 36, k); cam.position.set(0.2, 0.8, 5.5); cam.lookAt(pos.x * 0.6, K.lerp(9, 10, k), -30);
    renderer.render(s, cam);
  };
}

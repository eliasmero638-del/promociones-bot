// fb3 · miles la ven: la bola de fuego cruza sobre un pueblo, la gente sale a la calle y mira.
export async function montar({ THREE, K, W, H, renderer, scene: s, cam, texto, dur }) {
  K.calleNoche(s);
  const bola = K.bolaFuego(s, 22);
  const gente = [];
  for (const [q, an, x, z, g] of [['Male_Adult_06', 'm_idle_look_around_02.max.fbx', -1.2, 1.4, 160], ['Female_Adult_03', 'f_idle_look_around_01.max.fbx', 0.3, 0.9, 180],
    ['Male_Adult_10', 'm_idle_nervous_02.max.fbx', 1.5, 1.8, 200], ['Female_Adult_05', 'f_idle_nervous_01.max.fbx', -3.2, 0.4, 170]]) gente.push(await K.persona(s, q, an, x, z, g));
  await K.esperar(s);
  const vert = H > W, P0 = new THREE.Vector3(26, 30, -22), P1 = new THREE.Vector3(-26, 21, -28);
  return t => {
    const k = t / dur, pos = P0.clone().lerp(P1, k); bola.poner(pos, P1.clone().sub(P0), 1);
    gente.forEach((p, i) => { p.userData.mixer.setTime(1 + t + i); K.mirarArriba(p, 35); });
    texto({ f: '9 de diciembre de 1965', t: 'Miles la vieron', s: 'En 6 estados y en Canadá' });
    cam.fov = vert ? 60 : 44; cam.position.set(K.lerp(1.5, 0.5, k), 0.9, 6.5); cam.lookAt(K.lerp(3, -2, k), 7.5, -10);
    renderer.render(s, cam);
  };
}

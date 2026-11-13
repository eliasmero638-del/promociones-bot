// fb3 · llegan soldados y policías con linternas y sacan a todos del bosque.
export async function montar({ THREE, K, W, H, renderer, scene: s, cam, texto, dur }) {
  K.bosqueNoche(s, { claro: 7, semilla: 23 });
  const sold = [];
  for (const [q, x, z, g, an] of [['Military_Male_01', -1.2, -1.5, 20, 'm_idle_angry_01.max.fbx'], ['Military_Male_02', 1.3, -2.2, -15, 'm_idle_look_around_02.max.fbx'],
    ['Police_Male_02', 0.2, -4.2, 0, 'm_idle_angry_01.max.fbx']]) { const p = await K.persona(s, q, an, x, z, g); sold.push(p); }
  const lins = sold.map(p => K.linterna(s, p, 12));
  const civ = [];
  for (const [q, x, z] of [['Male_Adult_02', -0.6, 2.0], ['Female_Adult_04', 0.7, 2.6], ['Male_Adult_05', 1.6, 1.6]]) {
    const p = await K.persona(s, q, 'all_animations_max_motextr_xy/m_walk_neutral_01.max.fbx', x, z, 0); civ.push(p); }
  const auto = K.camionMilitar(s, false); auto.position.set(-3.5, 0, -8); auto.rotation.y = 0.5;
  const sirena = new THREE.PointLight(0xff2020, 0, 20); sirena.position.set(-3, 3, -7); s.add(sirena);
  await K.esperar(s);
  const vert = H > W;
  return t => {
    const k = t / dur;
    sold.forEach((p, i) => { p.userData.mixer.setTime(1 + t + i * 0.7); lins[i].seguir(0.3); });
    civ.forEach((p, i) => { p.userData.mixer.setTime(t + i * 0.4); p.position.z = [2.0, 2.6, 1.6][i] + t * 1.1; });
    sirena.intensity = 20;
    texto({ f: 'Versión oficial', t: '"No encontramos nada"', s: 'Dijeron que fue un meteoro' });
    cam.fov = vert ? 48 : 36; cam.position.set(K.lerp(-0.9, -0.6, k), 1.62, K.lerp(1.0, 0.4, k)); cam.lookAt(-1.1, 1.6, -1.5);
    renderer.render(s, cam);
  };
}

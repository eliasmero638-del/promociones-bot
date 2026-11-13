// fb3 · un muchacho ve salir un camión militar con algo grande tapado con una lona.
export async function montar({ THREE, K, W, H, renderer, scene: s, cam, texto, dur }) {
  K.bosqueNoche(s, { claro: 6, semilla: 31, luna: 1.8 });
  const farol = new THREE.SpotLight(0xffe6c0, 160, 30, 0.6, 0.6, 1.2); farol.position.set(-1, 7, 5); const tf = new THREE.Object3D(); tf.position.set(0, 0, 0.5); s.add(tf); farol.target = tf; s.add(farol);
  const cam_ = K.camionMilitar(s, true);
  const chico = await K.persona(s, 'Male_Adult_04', 'm_idle_look_around_03.max.fbx', 1.5, 4.2, 200);
  const sold = await K.persona(s, 'Military_Male_01', 'm_idle_neutral_01.max.fbx', -2.5, 3.2, 150);
  const l = K.linterna(s, sold, 10);
  await K.esperar(s);
  const vert = H > W;
  return t => {
    const k = t / dur; cam_.position.set(K.lerp(-9, 5, k), 0, 0.5); cam_.rotation.y = 0;
    chico.userData.mixer.setTime(1 + t); sold.userData.mixer.setTime(t); l.seguir(0.4);
    texto({ f: 'Esa noche', t: 'El camión militar', s: 'Con algo grande bajo una lona' });
    cam.fov = vert ? 50 : 36; cam.position.set(K.lerp(2.6, 2.2, k), 1.55, K.lerp(7.6, 7.0, k)); cam.lookAt(K.lerp(-3, 2, k), 1.6, 0);
    renderer.render(s, cam);
  };
}

// fb3 · la bellota de cerca: del tamaño de un carro, con un anillo de símbolos raros.
export async function montar({ THREE, K, W, H, renderer, scene: s, cam, texto, dur }) {
  K.bosqueNoche(s, { claro: 4, semilla: 5 });
  const obj = K.bellota(s, 0, 0);
  const l1 = new THREE.SpotLight(0xfff1cf, 70, 16, 0.35, 0.5, 1.3); l1.position.set(3.5, 1.8, 4); l1.target = obj; s.add(l1);
  const l2 = new THREE.PointLight(0xff9a50, 12, 6, 1.6); l2.position.set(-1.5, 0.8, 1.5); s.add(l2);
  const humo = K.brilloSprite('#ff7a30', 4, 0.25); humo.position.set(-1.2, 0.3, -1.4); s.add(humo);
  const p = await K.persona(s, 'Male_Adult_07', 'm_idle_nervous_01.max.fbx', -3.0, 2.2, 125);
  const lin = K.linterna(s, p, 10);
  await K.esperar(s);
  const vert = H > W;
  return t => {
    const k = t / dur, a = K.lerp(-0.5, 0.15, K.ease(k)), r = K.lerp(7.4, 6.4, k);
    p.userData.mixer.setTime(1 + t); lin.seguir(0.25);
    texto({ f: 'Lo que vio', t: 'Forma de bellota', s: 'Del tamaño de un carro' });
    cam.fov = vert ? 44 : 32; cam.position.set(Math.sin(a) * r, K.lerp(1.6, 1.1, k), Math.cos(a) * r); cam.lookAt(0, 1.05, 0);
    renderer.render(s, cam);
  };
}

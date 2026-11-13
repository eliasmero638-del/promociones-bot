// fb3 · el camionero baja al bosque con su linterna y la ve detrás de un árbol.
export async function montar({ THREE, K, W, H, renderer, scene: s, cam, texto, dur }) {
  K.bosqueNoche(s, { claro: 3, semilla: 11 });
  const obj = K.bellota(s, 0, -9); obj.position.y = 0.05;
  const res = new THREE.PointLight(0xff9a50, 30, 9, 1.6); res.position.set(0.5, 1.2, -7.5); s.add(res);
  const humo = K.brilloSprite('#ff8040', 5, 0.35); humo.position.set(-1.6, 0.4, -10.2); s.add(humo);
  const p = await K.persona(s, 'Male_Adult_07', 'all_animations_max_motextr_xy/m_walk_slow_01.max.fbx', 0, 3, 180);
  const lin = K.linterna(s, p);
  await K.esperar(s);
  const vert = H > W;
  return t => {
    const k = t / dur, z = K.lerp(3, -4.2, K.ease(Math.min(1, k * 1.15)));
    p.position.set(Math.sin(k * 3) * 0.15, 0, z); p.userData.mixer.setTime(t); lin.seguir(0.12);
    humo.scale.setScalar(5 + Math.sin(t * 3) * 0.6);
    texto({ f: 'Esa noche', t: 'En el bosque', s: 'Kecksburg · 1965' });
    if (k < 0.55) { cam.fov = vert ? 50 : 38; cam.position.set(0.9, 1.7, z + 2.6); cam.lookAt(-0.1, 1.3, z - 4); }
    else { const q = (k - 0.55) / 0.45; cam.fov = vert ? 44 : 32; cam.position.set(K.lerp(1.8, 2.1, q), 1.6, K.lerp(-0.6, -1.4, q)); cam.lookAt(K.lerp(-0.4, -0.1, q), K.lerp(1.4, 1.1, q), K.lerp(-5, -9, q)); }
    renderer.render(s, cam);
  };
}

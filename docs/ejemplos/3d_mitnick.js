// Escena 3D de ejemplo (aprobada por el dueño el 12-nov): enganche de Kevin Mitnick. 4 planos con cortes:
// calle de noche con el carro del FBI → cuarto con la computadora → pasillo, tocan la puerta → primer plano de él.
// Se adapta sola a la duración (ctx.dur) y a vertical u horizontal.
export async function montar({ THREE, M, K, W, H, renderer, scene: sA, cam, texto, dur }) {
  const sB = new THREE.Scene(), sC = new THREE.Scene();
  K.calleNoche(sA);
  const auto = K.carro(sA, 0x1d2329, true);
  const cuarto = K.cuartoComputadora(sB);
  K.pasillo(sC);
  const hacker = await K.persona(sB, 'Male_Adult_09', 'm_sit_table_idle_neutral_01.max.fbx', 0.2, -0.95, 180);
  const agente1 = await K.persona(sC, 'Business_Male_01', 'm_knock_door.max.fbx', -0.85, -1.0, -90);
  const agente2 = await K.persona(sC, 'Business_Male_03', 'm_idle_nervous_01.max.fbx', -0.2, 0.2, -110);
  const voltea = await K.clip('m_sit_table_idle_look_around.max.fbx');
  for (const s of [sA, sB, sC]) await K.esperar(s);
  const vert = H > W, e = dur / 10, C = [3.4 * e, 6.8 * e, 9.0 * e];
  let mirando = false;
  return t => {
    let sc;
    if (t < C[0]) {
      sc = sA; const k = t / C[0];
      auto.position.set(K.lerp(16, -3, k), 0, 1.6);
      cam.fov = vert ? 50 : 34; cam.position.set(K.lerp(7, 1, k), 5.5, 15); cam.lookAt(K.lerp(5, -2, k), 2.2, -4);
      texto({ f: '15 de febrero de 1995', t: 'Raleigh', s: 'Carolina del Norte · EE. UU.' }, 'El FBI llevaba <b>más de dos años</b> buscándolo');
    } else if (t < C[1]) {
      sc = sB; const k = (t - C[0]) / (C[1] - C[0]);
      hacker.userData.mixer.setTime(1 + t); cuarto.pantalla(t);
      cam.fov = vert ? 38 : 28; cam.position.set(K.lerp(2.0, 1.45, K.ease(k)), K.lerp(1.55, 1.45, k), K.lerp(0.1, -0.7, K.ease(k))); cam.lookAt(0.2, 1.1, -1.2);
      texto({ f: 'Esa madrugada', t: 'Un cuarto, una computadora' }, 'El hacker <b>más buscado</b> de Estados Unidos');
    } else if (t < C[2]) {
      sc = sC; const k = (t - C[1]) / (C[2] - C[1]);
      agente1.userData.mixer.setTime(2.2 + (t - C[1]) / e); agente2.userData.mixer.setTime(1 + t);   // 2.2 s = levanta la mano y toca
      cam.fov = vert ? 42 : 32; cam.position.set(0.8, 1.65, K.lerp(-3.6, -3.0, K.ease(k))); cam.lookAt(-0.8, 1.35, -0.4);
      texto({ f: 'Pasillo del edificio', t: 'Tocaron la puerta' }, 'Lo encontraron <b>por la señal de su celular</b>');
    } else {
      sc = sB; const k = (t - C[2]) / (dur - C[2]);
      if (!mirando) { mirando = true; K.cambiarClip(hacker, voltea); }
      hacker.userData.mixer.setTime(1.2 + (t - C[2]) * 1.4); cuarto.pantalla(t);
      cam.fov = vert ? 30 : 22; cam.position.set(0.85, 1.32, K.lerp(-1.55, -1.45, k)); cam.lookAt(0.2, 1.3, -0.95);
      texto({ t: 'Kevin Mitnick' }, 'Lo encontraron <b>por la señal de su celular</b>');
    }
    renderer.render(sc, cam);
  };
}

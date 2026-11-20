## Reporte Fase S4-4 — Arte, iluminación y ambientación por sala (KayKit)

Hecho:
- **Assets:** KayKit Dungeon Remastered 1.0, del repositorio oficial del autor (`KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0`, commit `b0ca9bd`), licencia **CC0 1.0** verificada en su `LICENSE.txt`. Solo los FBX y la textura (6,8 MB) en `Assets/ThirdParty/KayKit/`; registrado en `docs/licencias.md`.
- **`Editor/ConfigurarArte.cs`** (menú *Quimica/6*, y cada build si falta algo) arma por código en `Resources/Arte/`:
  - un material con el atlas (los FBX importaban URP Lit sin textura: se habrían visto grises);
  - los prefabs Pared, Piso, Techo, Rejilla, Puerta, Reja, Consola, Palanca y GemaMontacargas;
  - 3 materiales de gema emisiva;
  - el Volume (tonemapping Neutral + bloom 0,35 con umbral 1, así solo brillan las gemas).
  Además deja en la escena la **niebla** exp2 (0,045) y la **luz ambiente** plana. La niebla va en la escena porque URP quita del build las variantes de niebla que ninguna escena usa.
- **Escala:** los módulos de KayKit miden 4 m y la celda del juego, 2 m. **No se cambió la celda** (habría movido posiciones del servidor, el alcance de agarre y las pruebas). El arte va **encima** de los colliders del greybox, que siguen siendo los mismos y quedan invisibles. Colisión, puertas y raycast sin cambios.
- **`GeneradorNivel` aplica el arte por carácter de la grilla:**
  - `#` → un panel de pared en cada cara que da a una celda libre;
  - celda libre → piso + techo;
  - `M` → rejilla;
  - `D` → reja de puerta, que baja al abrirse igual que el cubo (deja 40 cm asomando);
  - muro central → 6 tramos de reja.
  Las consolas, palancas y montacargas salen de los datos del nivel. **Decisión del PM (mezcla):** consola = `table_small_decorated_A`; palanca = base `column` + palo de metal + pomo; montacargas = rejilla del piso. Cada uno lleva un acento emisivo con el mismo color que tenía en el greybox.
- **Luz por sala:** una luz puntual por sala y por lado, con el color `luz` del JSON, **sin sombras**. Solo la luz principal de la escena tiene sombras.
  - El techo proyecta sombra por las dos caras: es una baldosa dada vuelta y, sin eso, el sol entraba y los biseles dejaban rayas.
  - Una losa que solo proyecta sombra (`ShadowsOnly`) sobre cada lado tapa las juntas del techo: por ellas el sol dibujaba un panal de luz.
- **F3** (`Depuracion.cs`): contador de FPS (verde ≥ 60, amarillo si no) y las etiquetas de depuración (`dial_h2`, `D1_w`…), **ocultas por defecto**. La cámara del jugador activa el post-proceso: viene apagado en las cámaras creadas por código.
- **Pruebas:** la herramienta de capturas de `ui-diseno` se pasó a `sprint-4` (`711ab97`). Paso nuevo `medir_fps`: renderiza la cámara del jugador a 1920×1080 sin tope ni vsync y espera a la GPU en cada cuadro (es una medida conservadora).

Probado (cómo y resultado):
- **Capturas antes y después** de las 10 vistas (5 salas × 2 lados) en `docs/capturas/s4-4/antes/` y `docs/capturas/s4-4/despues/`. Revisé varias yo mismo y, por ellas, corregí dos defectos (el sol que entraba por el techo y las gemas lavadas a blanco).
  - Antes: greybox, luminancia 0,37–0,41 e igual en todas.
  - Después: luminancia 0,19–0,27 y contraste 0,08–0,11. Cada sala tiene su color (azul, verde, verde agua, rojo, ámbar) y 0 materiales con shader faltante (627 renderers).
- **Rendimiento:** **544 FPS** a 1920×1080 (1,8 ms de media, peor cuadro 4,6 ms) en esta PC (RTX 5050, OpenGL Core).
- `probar_build.sh` (los 5 escenarios): **TODO OK, 43 ✔**.
- Unity en batch: 0 `error CS`. Build de Linux: **100,3 MB** (era 96,0): entran solo las piezas usadas, no los 203 FBX.

Pendiente / riesgos:
- **Revisión visual de Jona** (como pide el calendario de la S4-4): mirar las capturas de `despues/` y jugar con F3 para ver los FPS.
- Sobre la vela de la consola se ve una aguja blanca vertical. Creo que viene del propio modelo de KayKit (su bounding box mide 1,62 m y la mesa unos 0,9 m), pero no lo verifiqué. Si molesta, se cambia por `table_small_decorated_B` o `table_small`.
- La reja del muro central casi no se ve en juego: las salas tienen techo y paredes propias. Está porque lo pide el alcance.
- El contador de F3 es IMGUI, igual que el HUD actual. Cuando la UI-3 pase el HUD a UI Toolkit (en `ui-diseno`), pasa con él.
- Falta el build de Windows (no lo pidió el criterio); se hace en la S4-5.

Necesito de Jona:
- Aprobar las capturas `docs/capturas/s4-4/despues/` y confirmar ≥ 60 FPS con F3 en su PC (en Windows también, si la prueba es ahí).
- El detalle de las pruebas que reportó el cliente (sigue teniendo prioridad sobre lo que quede del arte).

Commit: ver `git log` de `sprint-4` (desde `1e075cd`).

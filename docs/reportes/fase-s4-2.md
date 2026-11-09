## Reporte Fase S4-2 (arranque) — Cliente en primera persona y greybox desde el JSON

> S4-2 arrancada un día antes (lunes 09). Estado: **núcleo escrito y compilando (cero error
> CS)**. Falta el build de Linux y el escenario de `probar_build.sh` con dos bots, que son la
> parte que necesita el ejecutable; eso cierra S4-2 (martes). El guion de la prueba manual ya
> está en `docs/pruebas/s4-greybox.md`.

### Hecho
- **Condiciones de S4-1 cerradas:**
  - (a) **El cliente siempre arranca el laberinto:** `ClienteRed.IniciarPartida()` manda `iniciar {modo:"laberinto"}`. El modo agua **no se expone** en la UI; queda solo para los tests del servidor y el panel.
  - (b) **Tarea agregada a S4-5** en `MDs/SPRINT4.md`: migrar el panel (`estadisticas.py`, `admin_api.py`, React, tests) a *errores por concepto* y borrar el modo agua, con criterio de terminado: `grep` sin referencias a la misión agua + `pytest` en verde.
- **El nivel se construye desde el dato (SPRINT4 §3.1/§3.2):**
  - `server.py`: `inicio` del laberinto ahora incluye el **layout estático** de las salas (ids y posiciones de consolas, palancas, montacargas y puertas), sin las respuestas.
  - `GeneradorNivel.cs`: arma el greybox a partir de ese dato — cubos grises para paredes/pisos, muro central, puertas, y marcadores de color con su `Interactuable` para consolas (cian), palancas (amarillo) y montacargas (magenta). **Ninguna coordenada está escrita a mano.**
- **Primera persona (SPRINT4 §3.3), preparada para VR:**
  - `Interaccion.cs`: `IInteractor` (qué se quiere hacer: moverse, mirar, activar) separado de `EntradaTeclado` (cómo se ingresa). En VR solo se agrega `EntradaXR`. Más la marca `Interactuable`.
  - `PrimeraPersona.cs`: `CharacterController` + vista con el mouse (cursor bloqueado; **ESC** libera y abre la pausa con **sensibilidad ajustable**), **WASD**, **E** por un raycast desde la mira (`+`) con texto contextual. HUD con sala/concepto/reacción/números y el campo para fijar consolas de valor.
  - `pos` lleva **`pitch`**: al otro jugador se lo ve como cápsula con el nombre y una "cabeza" que gira con su inclinación. Las puertas se pintan de verde a medida que se completan las salas (`sala_estado`).
  - `ClienteRed.cs`/`GestorPartida.cs`: modelos del nivel y de `sala_estado`, envíos `dial`/`interactuar`/`montacargas`/`palanca`, y el armado de la escena del laberinto (jugador local en 1ª persona, remotos como cápsulas).

### Probado (cómo y resultado)
- **Compilación en batch (editor cerrado): cero `error CS`.** `logs/unity_s42_compile.log`: compile time 4,3 s, 0 errores, 1 domain reload. (Criterio de §7 cumplido.)
- `pytest` del servidor: **40 en verde** (el cambio de `inicio_info` es aditivo; `test_laberinto`/`test_nivel`/panel sin romperse).

### Correcciones de la revisión del PM
1. **Puertas y muro central bloquean físicamente desde el greybox (hecho, compila cero CS).** Cada puerta es ahora un cubo **sólido** que llena el hueco de la pared; su collider se **desactiva** cuando `sala_estado` la marca abierta (`GeneradorNivel.AbrirHasta`), y entonces baja y se pinta de verde. El muro central y el borde de cada mitad son paredes `#` sólidas: se ve por el hueco, no se cruza. El guion `s4-greybox.md` suma el paso 1b (intentar cruzar una puerta cerrada y el muro: no se puede).
2. **Los escenarios viejos de `probar_build.sh` se migran al laberinto (no se borran):** pendiente, es trabajo sobre el **build** (ver abajo).

### Pendiente / riesgos (cierre de S4-2, martes) — necesita el ejecutable
> No pude generar ni correr el build de Linux headless en esta sesión (Unity build + Docker + ejecutar el binario), así que esta parte queda escrita como plan y se hace al armar el build. Lo demás ya está verificado (compila cero CS; `pytest` 40 en verde).

- **Build de Linux** del greybox.
- **`scripts/probar_build.sh laberinto`**, con el plan concreto:
  - **Hook determinista en el servidor:** variable `NIVEL_SEMILLA` para que `Partida` sortee con semilla fija; así `probar_build.py` importa `nivel` y **conoce las respuestas** para resolver los puzzles.
  - **Recorrido de las 5 salas con dos bots** (protocolo, como `test_laberinto.py`), comprobando que cada puerta abre.
  - **Comprobación física (necesita el build):** un paso nuevo en `PruebaAutomatica.cs` que camina contra una puerta **cerrada** y reporta que **no la cruza** (la posición no pasa el umbral).
  - **Migrar los escenarios viejos al laberinto, cubriendo lo mismo:** 2 partidas seguidas sin cerrar ventanas (B1), un Player que sale a mitad y el resto sigue (B2), el Wizard que sale y la sala se cierra (B2), y la reconexión tras reiniciar el servidor (B4). `probar_perfiles` (login/perfil) no depende del modo y sigue válido.
- La corrección visual/jugable (que cada sala se entienda y no aburra) la valida Jona en **S4-3** con el guion `docs/pruebas/s4-greybox.md`.

### Necesito de Jona
1. Para la prueba de jugabilidad (S4-3, miércoles si S4-2 cierra el martes): abrir el proyecto una vez desde Unity Hub si el batch pide licencia, y después jugar en pareja con el guion.
2. Seguir con los **assets CC0** (§4) — no bloquea el greybox.

### Commit / push
- Rama `sprint-4`, pusheada a GitHub. Hashes al pie del push.

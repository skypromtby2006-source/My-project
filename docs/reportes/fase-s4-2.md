## Reporte Fase S4-2 — Cliente en primera persona y greybox desde el JSON

> **S4-2 CERRADA.** Núcleo en primera persona + greybox desde el dato, build de Linux generado
> (96 MB, 0 error CS) y `probar_build.sh laberinto` en verde contra el build real, con el
> **door-cross físico** incluido. El guion de la prueba manual (Jona, S4-3) está en
> `docs/pruebas/s4-greybox.md`.

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
- **Build de Linux generado:** `Quimica/3. Build Linux` en batch (editor cerrado) → **Succeeded, 96 MB, 0 `error CS`** (`logs/unity_s42_build.log`).
- **`scripts/probar_build.sh laberinto` y `laberinto_player`: TODO OK** contra el build real (headless), con un servidor propio de semilla fija. Cubre:
  - **Door-cross físico (la corrección del PM):** con la puerta **cerrada**, el Wizard empuja contra ella y **no la cruza** (`local_x > 9`); al completar la sala, la **misma** puerta abre y **sí la cruza** (`local_x < 8`).
  - **B1:** dos partidas seguidas sin cerrar la ventana; en cada una el Wizard/Player ve al otro y, al volver al lobby, no queda la escena vieja.
  - **B2:** sale el Player → el Wizard sigue; sale el Wizard → el Player vuelve al lobby con el aviso.
  - **B4:** el build reconecta tras reiniciar el servidor.
- `pytest` del servidor: **42 en verde** (40 previos + 2 del hook `NIVEL_SEMILLA`).

### Correcciones de la revisión del PM (ambas hechas y verificadas)
1. **Puertas y muro central bloquean físicamente desde el greybox.** Cada puerta es un cubo **sólido** que llena el hueco de la pared; su collider se **desactiva** cuando `sala_estado` la marca abierta (`GeneradorNivel.AbrirHasta`), y entonces baja y se pinta de verde. El muro central y el borde de cada mitad son paredes `#` sólidas. **Verificado en el build** por el door-cross de `probar_build.sh laberinto`. El guion `s4-greybox.md` suma el paso 1b.
2. **Escenarios viejos migrados al laberinto (no borrados):** su cobertura (B1/B2/B2/B4) vive ahora en `laberinto` y `laberinto_player`, porque el cliente **siempre** inicia en modo laberinto (los de la misión agua ya no aplicaban). `sesion`/`reinicio`/`panel`, que no dependen del modo, siguen igual.

### Cómo se hizo verificable
- **Hook determinista** `NIVEL_SEMILLA` en `server.py`: con semilla fija, `probar_build.py` importa `nivel` y **conoce las respuestas**; vacío en producción (sorteo al azar). Tiene su test.
- **El escenario levanta su propio servidor** (`ServidorLocal`, puerto 7788, en memoria): no depende de Docker y permite la prueba B4 reiniciándolo. El Wizard es el build (manda `dial`/`palanca` reales) y el Player un bot que resuelve su lado; la palanca de cada lado baja con < 2 s de diferencia por señales.
- **Pasos nuevos en `PruebaAutomatica.cs`:** `colocar` (teletransporta para la prueba), `empujar` (mueve con el mismo `CharacterController`, así choca con el collider), `dial`/`palanca`/`interactuar`, `esperar_escena`/`esperar_sala`/`esperar_nivel`.

### Necesito de Jona
1. **Prueba de jugabilidad (S4-3, miércoles):** jugar en pareja con el guion `docs/pruebas/s4-greybox.md` y anotar por sala si aburre/confunde/es fácil.
2. Seguir con los **assets CC0** (§4) — no bloquea el greybox.

### Commit / push
- Rama `sprint-4`, pusheada a GitHub. Hashes al pie del push.

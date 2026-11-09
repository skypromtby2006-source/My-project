## Reporte Fase S4-1 — Servidor: nivel como dato, los 5 puzzles y el protocolo nuevo

> Sprint 4. Estado: **S4-1 terminada.** El nivel vive en un JSON, el servidor sortea los
> números, valida los 5 puzzles por el protocolo nuevo y registra los datos para la
> investigación. Las 3 decisiones de diseño que quedaron abiertas las resolvió el PM y
> ya están aplicadas (ver abajo). Hay **una decisión de alcance** que tomé yo y que
> conviene que el PM confirme: el retiro escalonado de "Sintetizar agua".

### Hecho
- **Decisiones del PM aplicadas:**
  1. `n` (mol de agua base) se sortea en **{6, 12, 18, 24, 30, 36}**.
  2. **Masas molares reales** (Cl = 35,5 → HCl 36,5 y NaCl 58,5); la balanza de la Sala 3 trabaja con 1 decimal.
  3. **Sala 5 = combustión del amoníaco** `4NH₃ + 3O₂ → 2N₂ + 6H₂O` (Opción B): el NH₃ de la Sala 4 es su reactivo real, el encadenamiento cierra químicamente. Actualicé la fila de la Sala 5 en `MDs/SPRINT4.md §2`.
- **Protocolo nuevo conectado en `server.py`** (SPRINT4 §3.2), con validación total del lado del servidor:
  - `dial {consola, valor}`, `interactuar {obj, accion}`, `montacargas {obj}`, `palanca {puerta}` y el broadcast `sala_estado {sala, concepto, reaccion, puerta, datos, palancas, mensaje}`.
  - `pos` ahora incluye **`pitch`** (inclinación de la cabeza) para la primera persona.
  - **Apertura conjunta real:** la puerta solo abre si los dos lados dejaron su parte correcta **y** bajan su palanca con < 2 s de diferencia (clase `Partida` + `nivel.palanca_ok`). Anti-trampa de lado: un Player no puede tocar una consola del Wizard.
  - Eventos nuevos: **`error_estequiometria {sala, concepto, esperado, recibido, usuario}`**, **`sala_completada {sala, segundos, errores}`** y `nivel_completado`. Progreso del nivel guardado en `misiones_completadas` (mision = "laberinto").
- **El nivel es un dato:** `servidor/niveles/laberinto_01.json` (grilla por lado + los 5 puzzles) y `servidor/nivel.py` (carga, sorteo con enteros garantizados, validadores).

### Probado (cómo y resultado)
- `pytest` del servidor: **40 pasan** (29 del panel sin tocar + 7 de `test_nivel.py` + 4 de `test_laberinto.py`).
- `test_laberinto.py` maneja el juego por el **protocolo TCP real** (fixtures `servidor_juego` + `bot`):
  - **Un test que recorre las 5 salas enteras** con respuestas correctas → abre el portón, 5 `sala_completada` + `nivel_completado`, progreso guardado.
  - **Un error por concepto** (balanceo/mol/masa/limitante/rendimiento): con la parte mal, aunque bajen las dos palancas **no abre**, y queda el `error_estequiometria` con su concepto; al corregir, abre.
  - **Ventana de 2 s** de las palancas (abre con < 2 s, no abre con 5 s) y rechazo de consola ajena.
- `test_nivel.py`: 3000 sorteos dan enteros en las 5 salas (incluida la Sala 5 nueva), el encadenamiento cierra (NH₃ de la 4 → reactivo de la 5) y `requeridos`/`activaciones` por sala.
- `probar_perfiles` / el cliente ya desplegado: **no afectados** — el default de `iniciar` sigue siendo la misión de agua; el laberinto es opt-in con `modo:"laberinto"`. (Necesitan servidor Docker + build para correr; no se pudieron ejecutar en esta máquina de desarrollo sin levantar el entorno.)

### Que los números cierren (resuelto)
El encadenamiento obliga a que `n` sea **múltiplo de 6** (par → O₂/H₂ y gramos enteros; múltiplo de 3 → NH₃ entero). Con las masas de secundaria, la Sala 3 da gramos enteros porque `n` es par. La Sala 5 (combustión de NH₃) mide el rendimiento sobre el N₂ producido: `nh3 = n/3` siempre es par, así que `N₂ = nh3/2` y su masa teórica (28·mol) son enteros, y el % sorteado {60,70,75,80,90} es la respuesta. Todo verificado con 3000 sorteos.

### Decisión de alcance que tomé (conviene que el PM la confirme)
**No borré del todo "Sintetizar agua"; lo retiré de forma escalonada.** El laberinto es el juego nuevo (vía `modo:"laberinto"`); la misión de agua queda como **modo legado opt-in**.
**Por qué:** borrarla ahora deja `pytest` en rojo (lo que §7 pide en verde). La misión de agua está acoplada a **54 usos en 7 archivos**, incluido todo el panel de Sprint 3 (`estadisticas.py`, `admin_api.py`), el **frontend React** (`Estadisticas.jsx`, `UsuarioDetalle.jsx`) y los `probar_*`, porque el panel muestra **errores por elemento** y confusiones. Reemplazar eso por **errores por concepto** es exactamente el trabajo del §3.4, que el calendario agenda para **S4-5 (Dom 15)**. Hacerlo ahora dejaría el panel (deliverable aprobado de v0.4) a medio migrar.
**Qué hice en su lugar:** el servidor ya emite `error_estequiometria`/`sala_completada` con el concepto, listos para que el panel los consuma en S4-5. El retiro final del agua y la migración del panel van juntos en S4-5.
→ **Si el PM quiere el retiro total ahora**, lo hago, pero arrastra la migración del panel a concepto (backend + React + sus tests) dentro de esta fase.

### Pendiente / riesgos
- S4-2 (primera persona + greybox desde el JSON) es la fase grande que sigue; las grillas del JSON son greybox de relleno y se finalizan ahí.
- El panel sigue mostrando estadísticas **por elemento** (del juego legado) hasta la migración a concepto en S4-5.

### Necesito de Jona
1. **Confirmar la decisión de alcance** (retiro escalonado del agua) o pedir el retiro total ahora.
2. Avanzar con la **descarga de assets CC0** (§4) a `QuimicaVR/Assets/ThirdParty/<pack>/` — tarea 🧑, no bloquea.
3. Nada más del lado numérico: las 3 decisiones ya están aplicadas y testeadas.

### Commit / push
- Rama `sprint-4`, pusheada a GitHub junto con `main` + tag `v0.4-demo`. Hashes al pie del push.

## Reporte — Presentación v0.6-demo (build de Windows, pruebas y kit)

Brief: `MDs/PRESENTACION.md`. Fecha de la presentación: **sin completar** (el brief y el pedido traían el campo vacío).

### Versión y rama
- Última versión: `v0.6-rc1` (candidata del 20/11; `v0.6-demo` nunca se había cortado). Esta es **`v0.6-demo`**.
- Rama `presentacion` creada desde **`revision`**, no desde `main`: `main` estaba en la v0.4 (Sprint 3) y lo último aprobado (rol docente, espectador, UI-3, iluminación; revisión con el docente del 20/11) vivía en `revision` sin mergear. `main` es ancestro de `presentacion`, así que el merge es directo.
- No se agregaron funciones de juego. Lo nuevo es empaquetado, datos de demo, pruebas y documentación.

### Hecho
- **Datos de demo** (`servidor/demo.py`, todo el SQL en `repositorio.py`):
  - `docente_demo` con contraseña generada; clase "Química 5to A" con código de 8; reto `laberinto_01` con semilla fija `20261121`; `ana_demo`, `beto_demo`, `carla_demo`, `dani_demo` inscritos con 6 intentos (2 grupos completos y 1 incompleto) y errores en los 5 conceptos.
  - Idempotente: re-sembrar no duplica y conserva la contraseña y el código (los lee de `demo_credenciales.txt`, que también lleva la contraseña del admin).
  - `limpiar` borra el docente demo con su clase, su reto e intentos, y **todos** los usuarios `*_demo` (también los que se crean en vivo durante la presentación). No toca nada más.
  - Cómo se corre: `scripts/sembrar_demo.py` / `limpiar_demo.py` (Linux); `Servidor\sembrar_demo.bat` / `limpiar_demo.bat` en Windows, que llaman a **`QuimicaServidor.exe --sembrar-demo`** (el colegio no tiene Python: lo hace el mismo `.exe`, sobre su propio `quimica.db`); `ServidorDedicado\sembrar_demo_docker.bat` (Docker, `demo.py` dentro del contenedor contra PostgreSQL).
  - `contrasena_al_azar` pasó de `servidor_local.py` a `auth.py`, porque la imagen de Docker no lleva `servidor_local.py`.
- **Paquete**: `empaquetar.sh` agrega los dos `.bat` a `Servidor\` (CRLF verificado) y nunca copia un `demo_credenciales.txt`; `sembrar_demo_docker.bat` va en `ServidorDedicado\`; el LEEME tiene la sección "Datos de demo".
- **Capturas de respaldo** en `docs/presentacion/capturas/` (33 PNG): `salas/` (5 salas × Wizard y Player), `menus/` (login, menú, Mi perfil con clase, salas, lobby con reto, lobby con 2), `hud/` (partida y pausa), `panel/` (login, 8 páginas de admin, 6 de docente con los datos de demo).
  - Nuevo escenario `menus` en `probar_build.py` (capturas de cada pantalla del menú con el juego real).
  - Nuevo `scripts/capturas_panel.py`: servidor propio + datos de demo + Firefox headless por WebDriver BiDi (no hizo falta instalar nada).
- **Docs**: `docs/pruebas/windows-v0.6-demo.md` (checklist ✅/❌ para Jona), `docs/presentacion/tutorial.md`, `docs/presentacion/guion.md`, README y backlog.

### Probado (cómo y resultado)
- **pytest** (`scripts/probar_tests.sh`): **166 passed, 0 skipped**. Memoria 34 · SQLite 58 · PostgreSQL 58 · sin motor 16. Incluye `test_demo.py` (8): sembrar dos veces sin duplicados y con la misma contraseña; el panel docente con datos en los 5 conceptos; limpiar borra solo la demo (un docente, una clase, un `estu_real` y un `xdemo` quedan intactos) y se puede volver a sembrar; `--sembrar-demo` y `--limpiar-demo` del `.exe` sobre su propio `quimica.db`.
- **Builds de Unity** (batch, editor cerrado): Linux y Windows `Succeeded`, 0 `error CS`.
- **`probar_build.sh`**: los **9 escenarios** (laberinto, laberinto_player, sesion, reinicio, panel, reto, espectador, hud, menus) → `TODO OK ✔`, RESULTADO_BUILD comprobaciones ✔, 0 ✘.
- **`probar_paquete.sh`**:
  - Docker en Arch, desde el zip: PostgreSQL, `probar_cliente` (modo agua + una partida del laberinto), panel, y `demo.py` sembrar ×2 sin duplicar (6 intentos) y limpiar → `PAQUETE OK ✔`.
  - `.exe` en GitHub Actions (windows-latest), run 44878438780 sobre la rama: además de lo de siempre, `--sembrar-demo` ×2 (1 docente, 1 clase, 6 intentos, 4 estudiantes; misma contraseña) y `--limpiar-demo` (borra solo la demo) → `PAQUETE OK ✔`.
  - Con el tag: RESULTADO_RELEASE.
- Capturas revisadas a ojo: la tabla de resultados del docente muestra los 6 intentos con errores por concepto; el lobby muestra *Reto: Química 5to A*.

### Partes del guion ajustadas (y por qué)
1. **Bloque 4, el reto**: los retos no tienen nombre. Se ven como *reto N · laberinto_01 · semilla 20261121*, no como "Laberinto — Sala 1 a 5" (backlog).
2. **Bloque 5, unirse a la clase**: está en **Mi perfil → Unirse a clase**, no en el lobby. Los estudiantes de la demo en vivo son **nuevos** (`eli_demo`, `fede_demo`, creados a T-60) para que el "unirse con el código" sea real: los 4 sembrados ya están inscritos.
3. **Bloque 5**: se nombran los lados **Wizard** y **Player** (así aparecen en el juego). "Equivocarse con un coeficiente" pasa a "un **valor incorrecto en una consola**", que es como se ingresan los datos.
4. **Bloque 6, orden**: **el intento se guarda al terminar las 5 salas o al salir de la sala**, no al terminar la Sala 1. Por eso el orden queda así: espectador (y "Partidas en vivo") mientras se juega → salir de la sala → resultados. Guardar por sala va al backlog.
5. **Bloque 7**: el que se construye y prueba en Windows en cada versión es el **servidor `.exe`**. El juego se construye en Linux y se prueba con los escenarios del build real. Cifras reales: 166 pruebas y 9 escenarios.
6. **Preguntas, plan C**: necesita Python instalado (se aclara).
7. **Qué no mostrar**: la página Estadísticas del admin y el contador "Errores cometidos" de Mi perfil. Los dos salen de la misión vieja del agua y quedan vacíos con el laberinto. Los errores por concepto se muestran en el panel docente (backlog).
8. **No verificado** (sin acceso a las fuentes desde acá; marcado ⚠️ en el guion): el precio de Labster ("desde 5.000 USD/año") y la cifra 1.231.872 de SITEAL-UNESCO. Jona tiene que confirmarlos antes de presentar.

### Plan B si algo falla
- Detallado en `docs/presentacion/tutorial.md` § "Si algo falla en vivo" (tabla síntoma → qué hacer).
- **Antivirus bloquea el `.exe`** → plan C: `ServidorDedicado\iniciar_servidor_sin_docker.bat` con Python, y `py -3 demo.py sembrar` desde `ServidorDedicado\servidor\`.
- **Nada anda** → presentar sobre las capturas de `docs/presentacion/capturas/` con el mismo guion (`panel/docente_resultados.png` es la tabla de errores por concepto; `menus/sala_dos.png` es el lobby con reto).
- Se cerró el servidor → reabrirlo: los datos siguen en `quimica.db`.

### Pendiente / riesgos
- La **prueba manual en Windows** (`docs/pruebas/windows-v0.6-demo.md`) no se hizo: la hace Jona el día anterior. En particular, la consola de `sembrar_demo.bat` en un Windows real (la salida con tildes está probada en Actions solo redirigida a un archivo).
- Completar la fecha y hora de la presentación en el tutorial.
- Verificar las dos cifras externas del guion.
- La subida del zip completo al Release (`gh release upload`) la bloqueó el clasificador de permisos en la v0.6-rc1. Si vuelve a pasar, el comando está más abajo.

### Necesito de Jona
1. Correr el checklist de Windows y devolver las filas con ❌.
2. Completar la fecha en `tutorial.md` y confirmar Labster y SITEAL.

Commit: COMMIT_FINAL · Tag: `v0.6-demo`

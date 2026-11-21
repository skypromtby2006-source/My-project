## Reporte Fase UI-2 — Salas, Lobby y Mi perfil en UI Toolkit (+ decisiones del PM sobre la UI-1)

Hecho:
- **Decisiones del PM sobre la UI-1:**
  - `sprint-4`: `servidor/Dockerfile` copia `servidor/niveles` (`3055691`). El `.exe` ya los traía (`datas` de `quimica_servidor.spec`, en `_internal/niveles/`), y ahora está comprobado (ver abajo).
  - `sprint-4`: `probar_cliente.py`, la prueba de humo de `probar_paquete.sh` (Docker y .exe) y del workflow de Actions, ahora también **inicia una partida del laberinto** (`modo: laberinto`, llega el nivel, la palanca responde con `sala_estado`). El bot del escenario `panel` también inicia en modo laberinto (`615bf16`).
  - Merge de `sprint-4` en `ui-diseno` (`bdb4136`).
  - `Sprint_UI.zip` borrado de la raíz; `git restore` de `UnityConnectSettings.asset`. `Editor/ConfigurarServicios.cs` deja Unity Services apagado (por `SerializedObject`, al cargar el editor y al cerrarlo; también desde el menú *Quimica/5*) (`30d9e75`).
- **Salas** (`Salas.uxml` + `PantallaSalas.cs`): lista a la izquierda con nombre, chip "Cooperativo", cupo y "Unirse" (deshabilitado con chip "En partida" o "Llena"), botón Actualizar + refresco automático cada 2 s, unirse con código de **4** caracteres (en mayúsculas, con placeholder). A la derecha, Crear sala: nombre (sugerido "Sala de <nombre>"), modo fijo en Cooperativo con "PvP · próximamente" deshabilitado, máximo de jugadores con − / + (de 2 a 8, el mismo rango que el servidor). Sin contraseña de sala.
- **Lobby** (`Lobby.uxml` + `PantallaLobby.cs`): código grande arriba a la derecha, **Lado Wizard / Lado Player** según el rol que manda el servidor, avatar con la inicial en el color del perfil, chip *Host* para el anfitrión y *Listo / No listo* para los demás. El chip de estado dice qué falta ("Falta al menos un jugador más", "Faltan N jugadores por marcarse como listos", "Todos listos…"). El anfitrión ve **Iniciar partida**, habilitado solo con ≥ 2 jugadores y todos listos (las mismas reglas que valida `server.py`); los demás ven "Estoy listo / Ya no estoy listo". Sin "Cambiar de equipo" ni "Expulsar" (al backlog 🟢).
- **Mi perfil** (`Perfil.uxml` + `PantallaPerfil.cs`): usuario no editable, nombre visible, selector de color, Guardar / Volver, chips de error y de "Perfil guardado". Tarjeta Progreso: niveles completados, mejor tiempo, "Errores cometidos (todas las partidas)" e historial de las últimas 5.
- Se borró el IMGUI de Salas, Sala y Mi perfil en `MenuLobby.cs`: solo queda el HUD de la partida (pasa en la UI-3). Las listas se rearman solo si cambian sus datos, para que el botón bajo el mouse no parpadee con el refresco.
- Ninguna función de juego nueva; la red y el protocolo no cambian.

Probado (cómo y resultado):
- **Contraprueba del Dockerfile:** `probar_cliente.py` contra la imagen vieja (sin `niveles/`) → falla con "el servidor no inició el laberinto (¿falta servidor/niveles/…?)". Con el arreglo → `TODO OK`.
- **Contraprueba del .exe:** armé el servidor de PyInstaller en Linux con la misma spec: `probar_paquete.sh … exe` → `PAQUETE OK`. Con `_internal/niveles/` borrado del zip → falla con `FileNotFoundError …/_internal/niveles/laberinto_01.json`.
- **Paquete Docker desde el zip** (`empaquetar.sh --sin-exe` + `probar_paquete.sh … docker`): `PAQUETE OK`, con el laberinto incluido. El zip de prueba se borró.
- **GitHub Actions** run `44540699118` (windows-latest, `615bf16`): verde; `probar_cliente: TODO OK` desde el zip del .exe.
- **Unity Services:** lo prendí a propósito con un script descartable; la siguiente corrida en batch lo apagó (`[Quimica] Unity Services desactivado (estaba prendido)`) y `git status` quedó limpio. En dos corridas normales y un build, el archivo no volvió a cambiar.
- Unity en batch (`Construir.Linux`): **0 `error CS`**, sin advertencias de USS/UXML, build OK (97,1 MB).
- `scripts/probar_build.sh` (los 5 escenarios: laberinto, laberinto_player, sesion, reinicio, panel): **TODO OK ✔, 30 comprobaciones**, sin excepciones en los logs de los builds.
- `scripts/probar_tests.sh`: **121 passed**.

Pendiente / riesgos:
- **Todavía no vi las pantallas renderizadas.** Las pruebas recorren el mismo código que los botones, pero el build corre sin ventana: una superposición o un texto cortado no se detectaría. Las capturas a 1280×720 y 1920×1080 son de la UI-4; si Jona quiere adelantar, alcanza con abrir `scripts/jugar_linux.sh`.
- El servidor de Docker del repo quedó reconstruido y corriendo con el arreglo.

Necesito de Jona:
- Nada bloqueante. Opcional: una mirada al build antes de la UI-3.

Commit: ver `git log` de `ui-diseno` (los hashes de esta fase están arriba y en el commit de la UI-2).

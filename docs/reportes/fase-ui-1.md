## Reporte Fase UI-1 — Tokens, Manrope, Login y Menú en UI Toolkit

Hecho:
- Rama `ui-diseno` creada desde `sprint-4` (`87188b7`), la rama más avanzada (main y sprint-3 no tienen nada que sprint-4 no tenga).
- **Sistema visual:** `Assets/UI/Resources/UI/Estilos.uss` con los tokens de SPRINT_UI §1 y las mismas clases del diseño (`.btn`, `.btn.sec`, `.btn.sm`, `.card`, `.card-destacada`, `.chip.ok/.warn/.host`, `.inp`, `.row`). Como USS no tiene `gap`, las clases `g8`…`g36` las aplica `Ui.AplicarGaps`.
- **Fuente Manrope** 400/600/800 en `Assets/Fonts/` (SIL OFL), con la licencia en `Assets/Licencias/` y registrada en `docs/licencias.md`.
- **PanelSettings** generado por código (`Editor/ConfigurarUI.cs`, menú *Quimica/4*): Scale With Screen Size, 1280×720, match 0,5. Lo llaman ConfigurarDemo y cada build, así un clon nuevo del repo no depende de un paso manual.
- **Login** (`Login.uxml` + `PantallaLogin.cs`): dos columnas como `Main.dc.html`, pestañas Entrar / Crear cuenta, **sin contraseña**, IP + puerto (reemplaza a la pantalla de Conexión), nombre visible y selector de 8 colores en Crear cuenta, chip de estado real del servidor abajo a la izquierda, validación del usuario (4 a 16) y Enter = botón principal.
- **Menú principal** (`Menu.uxml` + `PantallaMenu.cs`): 3 tarjetas con Multijugador destacado; Historia y Laboratorio como "Próxima fase" y deshabilitadas; chip con nombre + color del perfil; Perfil · Ajustes (deshabilitado, al backlog) · Cerrar sesión. Sin el chip de "progreso sincronizado".
- `MenuLobby` separa estado y acciones de la vista. Salas, Sala, Mi perfil y HUD **siguen en IMGUI** hasta la UI-2/UI-3 (se dibujan solo cuando la pantalla no tiene vista de UI Toolkit, así no hay menú duplicado).
- `docs/decisiones.md`: por qué UI Toolkit, el truco del `gap` y la conclusión sobre **VR**: Unity 6.3 trae `PanelRenderMode.WorldSpace` (verificado en este editor); falta probar el rayo de XR sobre UI Toolkit en la fase de VR, con plan B documentado (Canvas uGUI World Space).
- Ninguna función de juego nueva. La red y el protocolo no cambian.

Probado (cómo y resultado):
- Glifos con `fc-query` en las 3 variantes de Manrope: "_", tildes, ñ, ¿¡, →, ·, ₂ y × están todos → **no hizo falta Noto Sans**.
- Unity en batch (`ConfigurarUI.Configurar` y `Construir.Linux`): **0 `error CS`**, sin advertencias de importación de USS/UXML, build de Linux generado.
- `scripts/probar_tests.sh`: **121 passed, 0 skipped** (memoria, sqlite, postgres).
- `scripts/probar_build.sh` (todos): **laberinto, laberinto_player, sesion y reinicio en verde (23 ✔)**. **panel ✘**: ver riesgos (no lo causa la UI).
- Los escenarios se adaptaron al flujo nuevo Login → Menú → Salas: `PruebaAutomatica` suma `abrir_salas` (el botón "Ver salas") y `esperar_conectado`; `probar_build.py` usa los nombres nuevos (`Login`, `Menu`).

Pendiente / riesgos:
- 🔴 **Bug de Sprint 4, ajeno a la UI: el servidor de Docker no puede iniciar el laberinto.** `servidor/Dockerfile` copia solo `servidor/*.py` y no `servidor/niveles/`; al iniciar con `modo: laberinto` el servidor tira `FileNotFoundError` en `nivel.cargar()` (traceback en `docker compose logs servidor`). Los escenarios del laberinto pasan porque levantan su propio servidor con Python, no el de Docker. **Además**, el bot del escenario `panel` iniciaba en modo "agua" y desde la S4-2 eso tira al cliente (`NullReferenceException` en `GeneradorNivel.AparicionMundo`: JsonUtility deja `nivel` como objeto vacío en vez de null). Corregí el bot para que pida `modo: laberinto` como el cliente real; el escenario sigue en rojo por el Dockerfile. **No lo arreglé en `ui-diseno`** (el brief dice que esta rama no toca el juego); la línea `COPY servidor/niveles ./niveles` iría en `sprint-4`. Conviene revisar también si el `.exe` de PyInstaller incluye `niveles/`.
- Todavía no hay capturas: van en la UI-4. La comparación visual con el diseño queda para entonces.
- `Sprint_UI.zip` quedó en la raíz del repo sin seguimiento; no lo subí.

Necesito de Jona:
- Que decida si el arreglo del Dockerfile entra ya en `sprint-4` (hay que revisar el congelamiento de infraestructura) antes de la próxima prueba con el servidor de Docker.
- Opcional: abrir el build (`scripts/jugar_linux.sh`) y mirar Login y Menú antes de la UI-2.

Commit: `dfd4aeb`, `2333ccb`, `1626ff7` (código y pruebas) + este reporte

## Reporte Fase S2-2 — Perfiles en el cliente Unity

Hecho:
- `ClienteRed.cs`:
  - Modelos `InfoPerfil`, `InfoProgreso` y `EntradaHistorial`. `InfoJugador` ahora trae `color`.
  - Propiedad `MiPerfil` y métodos `Registrar`, `Login`, `EditarPerfil` y `VerPerfil`.
  - `MiId` sale del mensaje `perfil`. `Conectar` ya no manda `hola`.
  - `Paleta` es la misma lista que en `server.py`.
- `MenuLobby.cs` (IMGUI):
  - Flujo nuevo: Conexión (solo IP y puerto) → **Perfil**, con las pestañas *Iniciar sesión* y *Crear perfil* → lobby.
  - **EditarPerfil**: usuario de solo lectura, nombre visible, selector de color (8 cuadrados, con borde blanco y negro en el elegido), *Guardar* / *Volver* y la sección Progreso (completadas, mejor tiempo, errores totales y las últimas 5 misiones con fecha local, duración y errores).
  - El botón *Mi perfil* está en el lobby **y dentro de la sala**, para poder hacer la prueba S2-3 de editar estando en la sala. *Volver* regresa a donde estabas.
  - El último usuario se recuerda en `PlayerPrefs`. Los errores se muestran arriba.
  - La validación del cliente es la misma que la del servidor, solo por comodidad.
  - Nombres de la sala pintados con el color de cada jugador.
- `GestorPartida.cs`: el color de la cápsula sale de `jugador.color` (`ColorUtility.TryParseHtmlString`) y ya no del índice.

Probado (cómo y resultado):
- Batch `Construir.Linux` → `Build Finished, Result: Success` (95,3 MB). En el log: **0 `error CS`** y ningún warning en `Assets/`.
- El flujo con la UI **no lo probé**: no puedo ver la ventana del juego. Se prueba en la S2-3.

Pendiente / riesgos:
- Mientras dura la partida, las cápsulas no se actualizan si alguien edita su perfil. No es posible desde el HUD porque *Mi perfil* no está ahí, así que no afecta a la demo.
- Los nombres se muestran con *rich text*: si alguien escribe `<b>` en su nombre, se ve en negrita. Es cosmético.
- `ProjectSettings/UnityConnectSettings.asset` aparece modificado (`m_Enabled: 0 → 1`, Unity Services). Lo hizo Unity, no este sprint, y **no lo incluí en el commit**. Jona decide si lo descarta.

Necesito de Jona (Fase S2-3):
1. `scripts/servidor_iniciar.sh` (reconstruye el servidor con perfiles) y `scripts/jugar_linux.sh 2`.
2. Crear 2 perfiles con colores distintos. A crea la sala y B se une. B entra en *Mi perfil*, cambia el nombre y *Guardar*: A lo tiene que ver cambiado en la sala.
3. Completar la misión. En *Mi perfil*, el Player tiene que ver +1 y el Wizard 0.
4. Cerrar todo, `scripts/servidor_detener.sh` y `scripts/servidor_iniciar.sh`, y volver a entrar: el progreso sigue ahí.
5. Abrir una tercera ventana e intentar entrar con un usuario que ya está conectado: tiene que salir "Ese usuario ya tiene una sesión abierta".
6. Pasarme lo que falle (captura o texto del error).

Commit: d686d73

## Reporte Fase S1-2 — Cliente Unity (roles, misión y sincronización)

Hecho:
- **Requisito del PM, fuente de verdad única:** `mision` ahora incluye `mesa` (centro y tamaño) y `radio_objeto`, y en `server.py` las posiciones de las esferas se calculan a partir de la mesa. El cliente dibuja la mesa, el reactor y las esferas solo con `inicio.mision`. Lo único fijo que queda en el cliente es el suelo, el punto de aparición de los jugadores, la cámara y desplazamientos relativos (etiquetas, objeto sobre la cabeza).
- `ClienteRed.cs`:
  - Modelos `InfoObjeto`, `InfoMision`, `EstadoMision`, `InfoReactor`, `InfoMesa` e `ItemReceta`, con los mismos nombres de campo que el servidor. `InfoJugador.rol`, `MiRol` y `SoyWizard`.
  - `Agarrar`, `Soltar` (con `InvariantCulture`), `Senalar` y `Reiniciar`.
  - `obj` llega como objeto en el mensaje `obj` y como texto en `senal`, y `JsonUtility` no admite un campo con dos tipos. Por eso esos dos mensajes se leen con clases propias. **El protocolo no cambia.**
- `GestorPartida.cs`:
  - Reactor como disco translúcido. Cada esfera tiene un color fijo según su posición en la mesa, **no según su elemento**: como el servidor reparte los elementos al azar en cada misión, el color no delata nada.
  - Player: **E** agarra la esfera libre más cercana (≤ 1.5 m) o suelta la que lleva, 1 m delante (sobre la mesa o en el suelo). La esfera agarrada se dibuja sobre la cabeza del portador.
  - Wizard: **clic** sobre una esfera (raycast) para señalarla.
  - El símbolo solo aparece si mi rol es wizard; los players ven "?". Se revisa en cada frame por si el rol cambia.
  - `senal`: la esfera pulsa en escala y brillo durante 2 s en todos los clientes.
  - Al reiniciar, solo se rehace la misión: los jugadores no vuelven al inicio.
  - El cliente solo pide: ninguna esfera se mueve hasta que el servidor lo confirma con `obj`.
- `MenuLobby.cs`:
  - En la sala aparece el rol de cada jugador ("Wizard (anfitrión)" / "Player · listo"), con texto y color en lugar de emojis.
  - Iniciar queda desactivado con menos de 2 jugadores y se muestra el motivo.
  - HUD: rol, controles, reactor, errores y, para el Wizard, la receta y el botón "Reiniciar misión". Mensaje central: la victoria queda fija y los demás mensajes duran 3 s (en rojo si es un error). Los rechazos del servidor aparecen abajo.
- `ConfigurarDemo.cs` crea `MatEsfera` (con `_EMISSION`) y `MatTranslucido` (transparente) en `Resources/Materiales`. Esas variantes del shader solo entran al build si un material las usa; es el mismo problema del magenta.

Probado (cómo y resultado):
- Compilación en batch: 0 `error CS`.
- `ConfigurarDemo.Configurar`: se crearon los 2 materiales. Revisé en el `.mat` que tuvieran `_EMISSION` y `_SURFACE_TYPE_TRANSPARENT`. La escena no necesitaba cambios, así que `Demo.unity` regenerada (mismo contenido, otros fileID) se devolvió a la versión del repo.
- `Construir.Linux` → `Succeeded (95,3 MB, 0 errores)`.
- `probar_servidor.sh` con el servidor reconstruido → `TODO OK ✔` (ahora además comprueba que llegue `mesa`).
- **No probado en pantalla:** el juego en sí (E, clic, pulso, HUD) lo prueba Jona en la S1-3.

Pendiente / riesgos:
- `H₂O` y `→` de la receta: la fuente por defecto de IMGUI podría no tener esos caracteres. Si se ven como cuadros, se cambia el texto en `server.py`.
- Los jugadores atraviesan la mesa (no hay colisiones; igual que en la v0.1).
- Unity cambió `ProjectSettings/UnityConnectSettings.asset` por su cuenta durante el batch. Lo devolví a la versión del repo y no se commiteó.

Necesito de Jona (Fase S1-3):
- Servidor arriba (`scripts/servidor_iniciar.sh`). Editor → Play = Wizard (crea la sala). `scripts/jugar_linux.sh 1` = Player (se une y marca Listo).
- Recorrer: llevar Na al reactor (error en rojo, vuelve a la mesa), señalar con clic (pulsa en las dos ventanas), completar 2 H + 1 O (mensaje verde) y Reiniciar misión.
- Avisarme lo que falle, con captura o el texto de la consola.

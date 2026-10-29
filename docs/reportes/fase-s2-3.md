## Reporte Fase S2-3 — Correcciones de la prueba (B1–B7)

Hecho:
- **Prueba nueva con el build real** (`scripts/probar_build.sh`, `servidor/probar_build.py` + `PruebaAutomatica.cs`). Lanza `Build/Linux/QuimicaDemo.x86_64` sin ventana (`-batchmode -prueba "<pasos>"`) contra el servidor de Docker, con bots, y revisa lo que el jugador estaría viendo: pantalla, aviso, cápsulas, posiciones y progreso. Los pasos llaman a los mismos métodos que los botones (se separaron de `OnGUI` en `MenuLobby`). Sin `-prueba`, el juego no cambia. Commit `7c98776`, hecho **antes** de corregir: reprodujo B1 y B2.
- 🔴 **B1, el Wizard no ve a los demás** (`46a960b`). No era el id: `MiId` no cambia con `perfil_editar` y se renueva bien al volver a entrar. La causa: al volver al lobby, la escena de la partida quedaba viva detrás del menú, y en la partida siguiente el `inicio` se tomaba por un "reiniciar misión", así que no se creaban las cápsulas de los jugadores nuevos. El perfil editado solo coincidía en el tiempo: beto editó su perfil entre H639 y GSWH, y el Wizard (sdada) traía la escena vieja de H639. Ahora `fuera` borra la escena y un reinicio se reconoce por el código de sala.
- 🔴 **B2, regla nueva de salida** (`ee14d05`). Si sale un Player, los demás siguen, también a mitad de la misión, y el objeto que llevaba cae al suelo donde estaba. Si sale el Wizard (con `salir`, al entrar a otra sala o al desconectarse), la sala se cierra y todos reciben `fuera` con `msg: "El Wizard salió, la sala se cerró"`. El "sacar a todos" venía del cliente: cualquier mensaje `sala` llevaba a la pantalla de la sala, también en plena partida. En el HUD ahora se avisa "<nombre> salió de la sala". Actualizados `protocolo.md`, `decisiones.md` y el LEEME.
- 🔴 **B3, progreso** (`ee7d8f3`). **No es un error de guardado.** `misiones_completadas` tiene las filas de la prueba (beto en H639, kbrazo123 en 869D), `perfil_ver` las devuelve, y el build real las muestra en Mi perfil antes y después de `servidor_detener.sh` + `servidor_iniciar.sh`, también cuando el Wizard sale justo al terminar. El perfil en 0 era `anastacia`, que fue **Wizard** en las dos misiones completadas y por regla no suma. Para que no vuelva a confundir: Mi perfil explica quién suma, y al completar, el HUD dice "+1 misión en tu perfil" al Player y "El Wizard no suma progreso" al Wizard. El servidor ahora registra `Progreso guardado: ...` y también los login/registro rechazados.
- 🟠 **B4, reconexión** (`0fafb1b`). Reproducido con el build real al conectar apenas termina `servidor_iniciar.sh`. El proxy de Docker acepta la conexión en el 7777 antes de que el servidor escuche y la corta: el juego pasaba a Perfil, el login se perdía y volvía con "Se perdió la conexión". Ahora `Conectar` confirma con `ping`/`pong`; si el servidor todavía arranca, se queda en Conexión con "el servidor todavía no responde; espera unos segundos y vuelve a intentar". `servidor_iniciar.sh` e `instalar_servidor.bat` esperan a "Servidor escuchando". Además, el hilo de una conexión cerrada ya no puede tumbar a la nueva.
- 🟡 **B5, puntos de aparición** (`7fefc42`). Los reparte el servidor en `inicio.apariciones` (fila en z=-5, 2.5 m entre jugadores) y el cliente los usa. Lo más probable es que la coincidencia de la prueba viniera de B1: una cápsula vieja que seguía mandando su posición.
- 🟢 **B6** (`972a137`): "guion bajo" en palabras en la ayuda y en el error.
- 🟢 **B7** (`f5aedcc`): usuario de 4 a 16 caracteres, en el servidor y en el cliente. No había usuarios de 3 caracteres en la BD.

Probado (cómo y resultado):
- Build "antes" (con el modo de prueba, sin correcciones) → `probar_build.py`: fallaban 10 comprobaciones de B1/B2; B3 y la sesión única pasaban.
- `probar_cliente.py` pasos 13-15 (regla de B2): con el `server.py` anterior falla en el 14 (Caro recibe `sala` como nueva anfitriona en vez de `fuera`).
- Build final (`Succeeded`, 0 `error CS`) y servidor reconstruido:
  - `probar_cliente.py` → `TODO OK ✔`
  - `probar_perfiles.py` → `TODO OK ✔`
  - `probar_perfiles.sh` (persistencia con el contenedor recreado) → `TODO OK ✔`
  - `probar_build.py` (wizard, player, sesion, reinicio, progreso) → `TODO OK ✔`, 50 comprobaciones.
- Comprobado a mano: un juego que conecta justo cuando vuelve `docker compose up -d` se queda en Conexión con el aviso nuevo. El servidor ni registra esa conexión, porque solo la aceptó el proxy.

Pendiente / riesgos:
- **P15–P18:** no encontré su definición en el repo. Probé sesión única (segunda ventana rechazada; usuario liberado al cerrar la ventana, con *Desconectar* y al matar el proceso) y reconexión tras reiniciar el servidor. Si P15–P18 piden otra cosa, necesito el texto o las capturas.
- Lo que no se puede probar sin ventana: dibujo, fuentes y clics de verdad. Eso se ve en la S2-3 de Jona.
- La fuente tampoco dibuja "_" **dentro** de los nombres de usuario (por ejemplo, `ana_1`). Solo se cambió el texto de ayuda, como se pidió.
- Si en plena partida se van todos los Players, el Wizard queda solo y la misión no se puede completar. Puede reiniciar o salir con ESC.
- Sin push todavía: la fase cierra cuando Jona apruebe la prueba.

Necesito de Jona (repetir la prueba S2-3 completa):
1. `scripts/servidor_iniciar.sh` (ya está corriendo con el servidor nuevo, pero no hace daño) y `scripts/jugar_linux.sh 2` (o `4`).
2. Crear 2 perfiles de colores distintos (el usuario ahora necesita al menos 4 caracteres). A crea la sala y B se une. B entra en *Mi perfil*, cambia el nombre y *Guardar*: A lo ve en la sala.
3. Completar la misión: el Player ve "+1 misión en tu perfil" y, con ESC → *Mi perfil*, +1 en el historial. El Wizard ve "El Wizard no suma progreso" y 0.
4. **B1:** jugar una segunda partida sin cerrar las ventanas (y una tercera después de editar el perfil o de volver a entrar): todos se ven.
5. **B2:** con 3 jugadores, un Player sale con ESC a mitad de la misión llevando una esfera: los otros siguen jugando y la esfera cae. Después sale el Wizard: todos vuelven al lobby con "El Wizard salió, la sala se cerró".
6. **B4:** cerrar todo, `scripts/servidor_detener.sh` y `scripts/servidor_iniciar.sh` (ahora espera al servidor), volver a entrar: el progreso sigue ahí. Una tercera ventana con un usuario conectado: "Ese usuario ya tiene una sesión abierta".
7. Pasarme lo que falle (captura y hora, para buscarlo en `servidor_logs.sh`, que ahora también registra los rechazos).

Commits: `7c98776` (test), `46a960b` (B1), `ee14d05` (B2), `ee7d8f3` (B3), `0fafb1b` (B4), `7fefc42` (B5), `972a137` (B6), `f5aedcc` (B7)

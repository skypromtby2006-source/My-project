## Reporte Fase 3 — Builds y prueba en Linux

Hecho:
- 3.1 Builds en batch: `Build/Linux/QuimicaDemo.x86_64` y `Build/Windows/QuimicaDemo.exe`, ambos `Succeeded` con 0 errores (con el arreglo del magenta, ver reporte de la Fase 2).
- 3.2 `scripts/jugar_linux.sh N`: abre N ventanas de 1280×720, cada una con su log en `logs/jugador_N.log` (ruta absoluta: el player resuelve las relativas desde la carpeta del ejecutable). Avisa si el servidor no está arriba.
- 3.4 Corrección: la comprobación del servidor en `jugar_linux.sh` abría una conexión TCP real, que aparecía en el log del servidor como un "Jugador" fantasma y dejaba un evento `desconexion` falso en la BD. Ahora usa `ss` (solo mira si el puerto escucha).

Probado (cómo y resultado):
- Jona, con `jugar_linux.sh 2`: funciona. Log del servidor: `Jugador518 creó la sala PS42` → `Jugador889 se unió` → `Partida iniciada en PS42`. Los nombres ya salen distintos y no se ve magenta.
- `logs/jugador_1.log` y `jugador_2.log`: sin errores ni excepciones.
- Nueva comprobación de `ss`: detecta el servidor y deja 0 conexiones en el log del servidor.

Pendiente / riesgos:
- ~~Cambio de anfitrión sin verificar~~ → **Confirmado por Jona** en una segunda prueba: al cerrar A, B pasa a ser anfitrión. Casilla 3.3 marcada.
- Lo de la 3.4 no tocó Unity, así que no hizo falta re-build.

Necesito de Jona:
- Repetir solo el final de la 3.3: A crea, B se une, A inicia, **cerrar A** y confirmar que B aparece como anfitrión.
- Confirmar si se borra la carpeta `My project/`.

Commit: 392eb08

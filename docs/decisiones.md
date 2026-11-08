# Decisiones de diseño (para defender la demo)

Tomado de la explicación de la demo original (`_base/LEEME_demo_anterior.md`, eliminado en v0.1-demo; sigue en el historial de git).

**Por qué Docker:** el docente puede correr exactamente el mismo servidor en otra PC sin instalar Python ni PostgreSQL a mano. `docker-compose.yml` describe los dos contenedores y cómo se conectan entre sí (el servidor llega a la BD por el nombre `db`, la red interna de Docker resuelve ese nombre).

**Por qué la BD es opcional en el código:** si PostgreSQL falla, el servidor sigue funcionando en memoria. En una demo en vivo lo último que quieres es que todo se caiga por la base de datos. Por ahora la BD guarda un registro de eventos (conexiones, salas creadas, partidas iniciadas): sirve de evidencia de que Python + PostgreSQL están integrados.

**Por qué IMGUI y no Canvas:** para una demo con plazo de un día, armar UI con Canvas consume horas en cosas visuales. IMGUI da un menú funcional en código puro; en la siguiente fase se cambia por la UI definitiva sin tocar `ClienteRed`, que es el que realmente habla con el servidor.

**Protocolo:** TCP con un mensaje **JSON por línea**. TCP garantiza que los mensajes llegan completos y en orden, que es justo lo que necesita un lobby (no puedes perder un "me uní a la sala"). Cortar por `\n` resuelve el problema clásico de TCP: es un flujo de bytes, no de mensajes, así que hay que marcar dónde termina cada uno. Mensajes completos en [protocolo.md](protocolo.md).

**Servidor autoritativo:** el servidor valida todo (sala llena, partida ya iniciada, solo el anfitrión inicia, todos listos). El cliente solo *pide*; así un cliente modificado no puede, por ejemplo, iniciar una partida ajena.

**asyncio:** un solo hilo atiende a todos los jugadores, porque mientras espera datos de uno no se bloquea, atiende a otro. Para decenas de jugadores es de sobra y evita los problemas de sincronizar hilos.

**En Unity, ¿por qué un hilo + cola?** Leer del socket bloquea; si lo haces en el hilo principal el juego se congela. El hilo de fondo solo encola los mensajes y `Update()` los procesa en el hilo principal, porque la API de Unity (crear objetos, mover cosas) **solo** se puede usar desde ahí.

**Posición 15 veces/seg + interpolación:** mandar cada frame (60+) desperdicia red sin mejora visible; con 15 envíos y `Lerp` en los remotos, el movimiento se ve suave.

**Si sale un Player, los demás siguen; si sale el Wizard, la sala se cierra** (decisión del cliente en la prueba S2-3, reemplaza el traspaso de anfitrión del Sprint 1). Un Player que se va no impide terminar la misión: si llevaba un objeto, se cae al suelo donde estaba para que otro lo levante. El Wizard es el único que ve la receta y los elementos, así que pasar el rol a un Player a mitad de partida le daba la respuesta a alguien que estuvo jugando a ciegas. El servidor saca a todos con `fuera` y el motivo, y borra la sala: así no quedan salas "fantasma" en la lista.

**`InvariantCulture` al enviar posiciones:** en una PC con Windows en español, `1.5f.ToString()` da `"1,5"`, lo que rompe el JSON. Es un bug típico en Bolivia/Latinoamérica.

**Materiales en `Resources/` (agregado en el sprint 0):** los objetos de la partida se crean por código, así que ninguna escena referencia el shader URP/Lit y Unity lo eliminaba del build (todo se veía magenta). Lo que está en `Resources/` entra siempre al build junto con su shader.

## Sprint 3 — Panel web

**La API recibe el módulo del juego como parámetro** (`crear_app(juego, ...)`) en vez de hacer `import server`. Al ejecutar `python server.py`, el módulo se llama `__main__`, y un `import server` cargaría una **segunda copia** con sus propias salas vacías: el panel mostraría todo en cero.

**El panel no puede tumbar el juego.** Si faltan dependencias (`fastapi`, `jwt`), si no hay `ADMIN_PASSWORD` o si el puerto 8000 está ocupado, el servidor lo dice en el log y el juego sigue funcionando. uvicorn hace `sys.exit(1)` cuando el puerto está ocupado; se atrapa para que no cierre también el servidor del juego.

**`expulsado` cierra la conexión, pero la limpieza la hace el mismo `finally` de siempre** (salir de la sala, liberar la sesión). Así no hay dos caminos de limpieza que puedan quedar distintos.

**`sala_cerrada` es un mensaje distinto de `fuera`**, para que el juego distinga "el Wizard se fue" de "lo cerró un administrador".

**HashRouter en el panel** (`/#/salas`): FastAPI sirve el panel como archivos estáticos, sin tener que redirigir cada ruta a `index.html`.

**Una sola conexión WebSocket para todo el panel**, compartida por las páginas. Cambiar de página no corta el flujo de logs. Se reconecta sola, con espera creciente, si el servidor se reinicia.

**Los tests del panel corren sin BD** (`servidor/tests`, modo Plan B2) y no necesitan Docker. El camino con PostgreSQL se prueba con curl y con `probar_build.sh panel` contra el servidor real.

**Dependencias de tests aparte** (`servidor/requirements-dev.txt`): pytest y httpx no van en la imagen de Docker ni en el venv del Plan B2.


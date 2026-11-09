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

**Los tests del panel corren sin BD** (`servidor/tests`, modo Plan B2) y no necesitan Docker. El camino con PostgreSQL se prueba con curl y con `probar_build.sh panel` contra el servidor real. *(Reemplazado en el Sprint 4: la batería corre contra memoria, SQLite y PostgreSQL; ver "Los tests corren contra los dos motores" más abajo.)*

**Dependencias de tests aparte** (`servidor/requirements-dev.txt`): pytest y httpx no van en la imagen de Docker ni en el venv del Plan B2.

## Sprint 4 — Dos formas de correr el servidor

El juego necesita un servidor. Hay dos maneras de ofrecerlo, y conviven:

**Servidor dedicado — Docker + PostgreSQL (recomendado para varios equipos).** Es lo que ya existe (`docker-compose.yml`). Una PC lo levanta y toda el aula se conecta a su IP. PostgreSQL guarda perfiles, progreso, eventos, logs y auditoría con durabilidad real y consultas concurrentes. Es la opción para una clase entera o un laboratorio fijo.

**Servidor local — un solo ejecutable + SQLite (para una PC sin Docker).** Para el docente que solo quiere probarlo en su máquina, o para la prueba en Windows sin instalar Docker Desktop. Un `.exe` (PyInstaller, modo carpeta) trae el servidor del juego, la API y el panel. Si no hay `DATABASE_URL`, el servidor usa un archivo **SQLite** (`quimica.db`) junto al ejecutable, con **las mismas tablas y las mismas consultas** que PostgreSQL. Si SQLite fallara, cae a memoria (como antes). No reemplaza al servidor dedicado: SQLite es de un solo escritor, pensado para una PC, no para un aula conectándose a la vez.

**Por qué una capa de datos (`servidor/repositorio.py`) y no dos caminos de SQL.** Antes cada función tenía su SQL de PostgreSQL embebido. Para soportar los dos motores sin duplicar queries ni "traducir" SQL con regex (frágil), todo el SQL vive ahora en `repositorio.py`. El SQL se escribe **portable** (SQLite ≥ 3.38 y PostgreSQL soportan `RETURNING`, `FILTER (WHERE …)` y `->>`), y las pocas diferencias **inevitables** se declaran en un **diccionario explícito por motor** (no en reemplazos de texto):

| Diferencia | PostgreSQL | SQLite |
|---|---|---|
| Timestamp actual | `now()` | `strftime('%Y-%m-%d %H:%M:%f', 'now')` (texto UTC con milisegundos: con solo segundos, dos filas del mismo instante empatan al ordenar) |
| Clave autoincremental | `SERIAL PRIMARY KEY` | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| JSON | `JSONB` | `TEXT` (con las funciones `json1`) |
| Fecha con zona | `TIMESTAMPTZ` | `TEXT` ISO-8601 (UTC) |
| Búsqueda sin distinguir mayúsculas | `ILIKE` | `LIKE` (SQLite no distingue mayúsculas en ASCII) |
| Placeholder de parámetro | `$1, $2, …` | `?1, ?2, …` (numerado, para reusar un parámetro igual que en PostgreSQL) |
| Fecha como parámetro | `datetime` | texto UTC con el mismo formato que el timestamp actual |

**Versión de SQLite:** se verificó que `RETURNING`, `FILTER` y `->>` funcionan en el `sqlite3` de la stdlib — comprobado aquí en **Python 3.14.8 con SQLite 3.54.0**. En el Python 3.12 del entorno de Jona el `sqlite3` trae SQLite ≥ 3.45, de sobra por encima del mínimo requerido (**3.38**, por `->>`). Se usa el `sqlite3` de la biblioteca estándar (sin dependencias nuevas, mejor para empaquetar con PyInstaller); como `sqlite3` es sincrónico, cada consulta corre en un hilo con `asyncio.to_thread` sobre **una única conexión** (`check_same_thread=False`) y un `threading.Lock` tomado *dentro* del hilo la serializa: el event loop nunca espera el lock, solo el resultado. Una sola conexión y no un pool porque SQLite admite un escritor a la vez. `PRAGMA journal_mode=WAL` (lectores y escritor no se bloquean si otra herramienta abre el archivo) y `busy_timeout=5000` (esperar en vez de fallar con "database is locked").

**El juego no se congela mientras la BD trabaja (medido).** `tests/test_concurrencia.py` carga 500 000 errores, lanza la consulta de las estadísticas (~0,8 s solo de SQL) y mientras tanto un jugador hace `ping` sin parar; se mide el **hueco entre pongs**. Resultado: SQLite ~115 ms de hueco máximo, PostgreSQL ~55 ms. *Contraprueba:* con el backend SQLite sin `to_thread` el test falla (un solo pong en 0,8 s). El test también destapó que **asyncpg decodifica las filas dentro del loop**: 500 000 filas de una vez lo frenaban ~0,4 s, así que los resultados grandes se leen con un cursor de a 5000 filas (`fetch_grande`). El JSON y pandas de las estadísticas también van en un hilo; aun así, armar el DataFrame es una llamada en C que retiene el GIL, y con 500 000 errores deja cortes de ~0,25 s. Con los datos de un aula (miles de eventos) es imperceptible; si algún día molestara, el paso siguiente es calcular en un proceso aparte.

**Los tests corren contra los dos motores.** La misma batería (perfiles, progreso, panel, laberinto) se parametriza con la fixture `motor`: `memoria`, `sqlite` y `postgres`. Así "mismas consultas" no es una promesa sino algo probado. `scripts/probar_tests.sh` levanta un PostgreSQL **descartable** (`docker-compose.test.yml`: proyecto aparte, datos en tmpfs, puerto 55432 solo en 127.0.0.1) y lo apaga al terminar; los tests lo leen de `TEST_DATABASE_URL` y **no** de `DATABASE_URL`, porque vacían las tablas en cada caso y no deben poder tocar la BD real. Si falta la BD de prueba, los tests de postgres **fallan** en lugar de saltearse; para correr sin Docker hay que elegirlo explícitamente (`--motores=memoria,sqlite`). El reporte termina con "N passed, 0 skipped" por motor.


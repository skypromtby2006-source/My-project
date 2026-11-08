## Reporte Fase S2-4 — Entrega v0.3

Hecho:
- **`entrega/windows/iniciar_servidor_sin_docker.bat`** (Plan B2), en `b86ee00`:
  - Busca Python con `py -3` y, si no lo encuentra, con `python`. El alias `python` de Microsoft Store no es Python, y el lanzador `py` evita ese problema.
  - Pide Python 3.8 o más nuevo.
  - Crea `Servidor\.venv` la primera vez y ahí instala `requirements.txt`. Una marca (`.venv\instalado.txt`) evita repetir pip, así que después arranca sin internet.
  - Si `pip` falla, avisa y sigue igual: `asyncpg` solo se importa con `DATABASE_URL`. Por ejemplo, un Python muy nuevo puede no tener una rueda de asyncpg.
  - Vacía `DATABASE_URL`, muestra las IP y deja el servidor en primer plano: se apaga cerrando la ventana o con Ctrl+C.
- **LEEME v0.3** (`78ec046`): explica cómo elegir entre Docker y el Plan B2, el paso 2-B, el perfil en el paso 3, una sección de perfiles y progreso (quién suma, sesión única, datos mínimos) y los problemas nuevos.
- **Build de Windows**: `Succeeded`, 98,5 MB, 0 errores (`logs/unity_s2-4_windows.log`). Incluye la fuente DejaVu Sans.
- **`dist/QuimicaDemo_Windows_v0.3.zip`** (37 MB): no incluye `DoNotShip`, trae los 7 `.bat` en CRLF y el LEEME nuevo.

Probado (cómo y resultado):
- `server.py` con un venv limpio (sin asyncpg), sin `DATABASE_URL` y en el puerto 7790 avisa "Sin DATABASE_URL..." y muestra "Servidor escuchando". Contra ese servidor, `probar_cliente.py` y `probar_perfiles.py` dan `TODO OK ✔`.
- El `.bat` no se pudo ejecutar en Linux: falta probarlo en Windows.

Pendiente / riesgos:
- 🧑 La prueba en Windows 11 con `iniciar_servidor_sin_docker.bat`. Sin BD, los perfiles y el progreso se pierden al cerrar el servidor, y eso es lo esperado.
- Después, si la prueba sale bien: merge de `sprint-2` a `main`, tag `v0.3-demo` y push con tags.
- `sprint-2` todavía no está en GitHub: 20 commits solo en esta PC.
- El calendario de `MDs/SPRINT3.md` está vencido. La S3 no arranca hasta tener las fechas nuevas del PM.

Necesito de Jona:
1. Copiar `dist/QuimicaDemo_Windows_v0.3.zip` a Windows 11 y descomprimirlo.
2. Ejecutar `Servidor\iniciar_servidor_sin_docker.bat`. La primera vez instala Python si hace falta y crea el venv. Hay que ver "Servidor escuchando" y aceptar el firewall.
3. Abrir `Juego\QuimicaDemo.exe` dos veces y hacer los pasos 2 a 5 de `docs/pruebas/s2-3.md`, fijándose en que se vean el "_", el "₂" y la "→" con la fuente en Windows.
4. Cerrar la ventana del servidor y abrirla de nuevo. Tiene que arrancar sin reinstalar nada, y que el progreso esté en 0 es lo esperado.
5. Pasarme lo que falle, con captura y hora.

Commits: `be42c52` (cierre S2-3), `b86ee00` (.bat), `78ec046` (LEEME)

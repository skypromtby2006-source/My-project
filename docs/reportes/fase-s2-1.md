## Reporte Fase S2-1 — Perfiles y progreso en el servidor

Hecho:
- Requisito previo cerrado. Jona aprobó la v0.2 en Windows 11. Merge de `sprint-1` a `main` (`7ded327`), tag `v0.2-demo`, push con tags y rama `sprint-2` creada desde `main`.
- Los briefs del PM se movieron a `MDs/`. `README.md` sigue en la raíz para que GitHub lo muestre.
- `servidor/server.py`:
  - Tablas `usuarios` y `misiones_completadas` (más un índice por `usuario_id`), creadas con `CREATE TABLE IF NOT EXISTS` en `iniciar_bd()`.
  - Mensajes `registro`, `login`, `perfil_editar` y `perfil_ver`, que responden con `perfil` (lleva el `id` de conexión, que antes llegaba en `bienvenido`). `hola` ya no existe.
  - Sin sesión, se rechazan `listar`, `crear_sala` y `unirse` con "Inicia sesión primero".
  - Una sesión por usuario. El usuario se libera al desconectarse. La comprobación se repite después de consultar la BD, para que dos logins simultáneos no pasen los dos.
  - Validaciones en el servidor: usuario en minúsculas con `^[a-z0-9_]{3,16}$`, nombre de 1 a 20 caracteres y color de la paleta (también acepta minúsculas). Para evitar carreras, el usuario duplicado se resuelve con `ON CONFLICT` sobre la restricción `UNIQUE`.
  - `sala.info()` lleva `color`. `perfil_editar` reenvía `sala` a toda la sala.
  - Progreso: al completarse la misión, se guarda un registro por cada **player** presente, con sus propios errores. `reaccion_fallida` lleva `usuario` en `eventos`.
  - Sin BD (Plan B2), todo funciona en diccionarios en memoria, con un `WARNING` al arrancar.
- `probar_cliente.py` usa `registro` en vez de `hola`, con usuarios aleatorios por corrida.
- Nuevos: `servidor/probar_perfiles.py` (3 jugadores) y `scripts/probar_perfiles.sh` (test → recrea el contenedor → comprueba la persistencia).
- `docs/protocolo.md` actualizado (sesión, paleta, objeto *perfil*, progreso y tablas). `docs/backlog.md` incluye lo que quedó fuera de alcance.

Probado (cómo y resultado):
- `scripts/probar_servidor.sh` → `TODO OK ✔` (regresión del Sprint 1).
- `scripts/probar_perfiles.sh` contra Docker → `TODO OK ✔` en las dos partes. Cubre los 7 puntos del brief:
  1. Sin login → error.
  2. Registro OK, duplicado, 5 formatos inválidos, nombre vacío o largo, color fuera de la paleta.
  3. Login de un usuario inexistente y doble sesión.
  4. La edición en la sala se refleja en los otros dos.
  5. Beto y Caro +1, Ana (wizard) en 0.
  6. Beto con 2 errores y Caro con 1.
  7. Reconexión, y **recreación del contenedor** con el progreso intacto.
- Los mismos dos tests contra `server.py` sin `DATABASE_URL` (Plan B2) → `TODO OK ✔`, salvo la persistencia, que en memoria no aplica.
- psql: `usuarios` y `misiones_completadas` tienen filas. El wizard no tiene registros y `reaccion_fallida` trae `usuario`.

Pendiente / riesgos:
- **Decisión técnica a validar por el PM:** `errores_totales` cuenta los `reaccion_fallida` de la tabla `eventos`, no suma la columna `misiones_completadas.errores`. Así también cuentan los errores de misiones reiniciadas o abandonadas, y es el mismo dato que se analiza con pandas.
- `mejor_tiempo_s = 0` significa "sin misiones", porque `JsonUtility` no lee `null`.
- **El cliente Unity actual (v0.2) ya no es compatible con este servidor:** sigue mandando `hola`. Se resuelve en la S2-2.
- `entrega/windows/iniciar_servidor_sin_docker.bat`, que el brief menciona para el Plan B2, **no existe** en el repo. Propongo crearlo en la S2-4.
- Login sin contraseña: cualquiera puede entrar como otro usuario. Es una decisión del cliente y quedó anotada en el backlog.

Necesito de Jona:
- Nada para esta fase. Opcional: abrir pgAdmin (`scripts/pgadmin.sh`) y mirar las tablas `usuarios` y `misiones_completadas`.
- Para la S2-2 necesito el editor de Unity **cerrado** (modo batch).

Commit: dca8fe9

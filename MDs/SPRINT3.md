# SPRINT3.md — Panel web de administración del servidor

> Brief del PM para Claude Code. Siguen vigentes **todas** las reglas de `CLAUDE.md`.
> Pedido del docente después de la presentación del 26/10: *"algo más palpable del servidor a nivel web: gestión del servidor, captura de logs y auditoría de los perfiles creados y su progreso"*.
> **Presentación: lunes 09/11/2026** (el 02/11 fue feriado). Depende del **Sprint 2** (perfiles + progreso), que se hace primero.

## 0. Orden de trabajo (replanificado: el lunes 02/11 fue feriado y no hubo revisión)
El Sprint 2 ya está cerrado: `v0.3-demo` aprobada en Windows con el Plan B2 y mergeada a `main`. El pedido del docente sigue en pie.

| Día | Trabajo | Corte |
|---|---|---|
| Vie 06 | **S3-1** (backend: API, auth, logs, auditoría) | |
| Sáb 07 | **S3-2 + S3-3** (frontend React completo) | **22:00** revisión de las prioridades 🔴 |
| Dom 08 | **S3-4** (Unity: expulsado/aviso/bloqueado) + **S3-5** (prueba integral + paquete) | **20:00 → `v0.4-demo`** |
| Lun 09 | 🎤 Presentación | |

**Por qué el Sprint 2 va primero:** sin perfiles no hay nada que auditar.
**Corte:** si el domingo 08/11 a las 20:00 la v0.4 no está aprobada, se presenta la `v0.3-demo`.
**Prueba en Windows:** solo con `iniciar_servidor_sin_docker.bat` (Docker Desktop está roto en esa PC, ver `docs/backlog.md`).

## 0.1 Prioridades (implementar en este orden dentro de cada fase)
| Nivel | Qué | Por qué |
|---|---|---|
| 🔴 Imprescindible | Login admin · estado en vivo · salas (expulsar/cerrar) · usuarios + detalle de progreso · logs en vivo · auditoría de acciones de admin | Es exactamente lo que pidió el docente |
| 🟡 Importante | Estadísticas con pandas · bloquear usuarios · aviso global | Las estadísticas son el argumento de investigación; si falta tiempo, se hacen como una tabla simple, sin gráficos |
| 🟢 Si sobra tiempo | Exportar CSV · gráfico de conexiones · histórico paginado de logs | Lucen bien, pero no se pidieron |

Si el sábado a las 22:00 el frontend no tiene todo lo 🔴, se dejan de lado 🟡 y 🟢 y se avisa al PM.

## 1. Qué se construye (decisiones del cliente)

### Acceso
- **Login de administrador** con usuario y contraseña definidos en la configuración del servidor (archivo `.env`, **nunca en git**).
- Cada sesión de admin recibe un **token JWT** que dura 8 horas.

### Gestión del servidor
1. **Estado en vivo:** uptime, jugadores conectados, salas activas, partidas en curso y un gráfico de conexiones de los últimos 30 minutos.
2. **Expulsar** a un jugador y **cerrar** una sala.
3. **Mensaje global:** un aviso que aparece en todos los juegos conectados.
4. **Bloquear o desbloquear usuarios:** un usuario bloqueado no puede iniciar sesión, y si está conectado se lo expulsa.

### Captura de logs
- Todos los logs del servidor (INFO, WARNING y ERROR) se ven **en vivo** en el panel y quedan **guardados** en la base de datos.
- Filtros por nivel, búsqueda por texto, histórico paginado y **exportación a CSV**.

### Auditoría de perfiles y progreso
- Tabla de usuarios: usuario, nombre, color, fecha de creación, último login, estado (activo/bloqueado), misiones completadas, mejor tiempo y errores.
- Detalle de cada usuario: historial de misiones y **errores frecuentes por elemento** (por ejemplo, "confunde Na con H: 4 veces").
- **Auditoría de acciones de admin:** cada expulsión, bloqueo, cierre de sala o mensaje global queda registrado con quién lo hizo, cuándo, a quién y por qué.

### Estadísticas (puente con el perfil de investigación)
- Página que muestra: errores más frecuentes por elemento (de todos los usuarios), tiempo promedio por misión y misiones completadas por día.
- **Se calculan con pandas en el backend.** **Por qué:** es la evidencia concreta del uso de Python + pandas para el "análisis de errores frecuentes" que justifica el perfil.

### Fuera de alcance (a `docs/backlog.md`)
Varios admins con roles distintos · roles docente/estudiante · HTTPS con certificado · editar perfiles desde el panel · notificaciones por correo.

## 2. Diseño técnico

### 2.1 Arquitectura
```
 Navegador (React) ──HTTP /api + WebSocket /api/ws──┐
                                                     ▼
 Juego Unity ──TCP 7777──►  ┌─────────────────────────────────────────┐
                            │ server.py  (UN solo proceso asyncio)    │
                            │  • servidor de juego TCP (ya existe)    │
                            │  • FastAPI/uvicorn en :8000 (nuevo)     │
                            │  • sirve también el React compilado     │
                            └──────────────────┬──────────────────────┘
                                               ▼
                                         PostgreSQL 16
```
**Por qué la API va en el mismo proceso que el servidor del juego:** para mostrar las salas en vivo, expulsar o mandar un aviso, la API necesita tocar el **estado en memoria** (`salas`, `jugadores`). Si fuera un proceso aparte, habría que inventar un canal de comunicación entre los dos. Uvicorn corre sobre asyncio igual que el servidor TCP, así que los dos conviven en el mismo event loop:
```python
await asyncio.gather(servidor_tcp.serve_forever(), uvicorn.Server(config).serve())
```

**Por qué FastAPI sirve el React compilado (y no un nginx aparte):**
- Todo sale del mismo origen (`:8000`), así que no hace falta configurar CORS.
- **El Plan B2 sigue funcionando:** en Windows, sin Docker, `python server.py` levanta juego + API + panel.

### 2.2 Estructura nueva
```
servidor/
├─ server.py            ← arranca TCP + uvicorn; el juego queda igual
├─ admin_api.py         ← FastAPI: rutas /api/*
├─ auth.py              ← login admin, JWT, rate limit
├─ registro_logs.py     ← logging.Handler → buffer en memoria + BD + WebSocket
├─ estadisticas.py      ← consultas + pandas
├─ tests/               ← pytest
└─ requirements.txt     ← + fastapi, uvicorn[standard], pyjwt, pandas, pytest, httpx
panel/                  ← React + Vite
├─ src/pages/  Login, Dashboard, Salas, Usuarios, UsuarioDetalle, Logs, Auditoria, Estadisticas
└─ src/api.js  ← fetch con token + reconexión del WebSocket
.env.example            ← ADMIN_USER, ADMIN_PASSWORD, JWT_SECRET (el .env real va en .gitignore)
```
- **Frontend:** React 18 + Vite + React Router + Recharts (gráficos). **JavaScript**, no TypeScript. **Por qué:** es un stack menos que aprender esta semana. El tipado queda en el backlog.
- **Dockerfile multi-etapa:** la etapa 1 (`node:20-alpine`) compila `panel/` y la etapa 2 (`python:3.12-slim`) copia `panel/dist` y el servidor. **Por qué:** la imagen final no lleva Node, solo el resultado compilado.
- **Compose:** publicar `8000:8000` (panel) y agregar `env_file: .env`.

### 2.3 Base de datos (todo con `IF NOT EXISTS`, igual que en el Sprint 2)
```sql
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS bloqueado BOOLEAN DEFAULT false;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS motivo_bloqueo TEXT;

logs (id SERIAL PK, nivel TEXT, mensaje TEXT, fecha TIMESTAMPTZ DEFAULT now())
     -- índice por fecha; se borran los de más de 30 días al arrancar

auditoria_admin (id SERIAL PK, admin TEXT, accion TEXT,   -- expulsar|cerrar_sala|aviso|bloquear|desbloquear|login|login_fallido
                 objetivo TEXT, detalle JSONB, ip TEXT, fecha TIMESTAMPTZ DEFAULT now())
```
- **Por qué los logs se guardan en la BD con un tope de 30 días:** se pueden consultar y filtrar desde la web, y la tabla no crece para siempre.
- Escribir en la BD **no debe frenar el juego**: los logs se encolan y se guardan en lotes cada 2 segundos.
- **Sin BD (Plan B2):** los logs y la auditoría quedan solo en memoria (últimos 2000) y el panel lo indica con un aviso amarillo, "Modo sin base de datos".

### 2.4 API (todas las rutas, salvo login, exigen `Authorization: Bearer <token>`)
| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/api/login` | `{usuario, contrasena}` → `{token}`. **Máximo 5 intentos por minuto por IP.** Registra `login` / `login_fallido` |
| GET | `/api/estado` | uptime, conectados, salas, partidas en curso, modo BD sí/no |
| GET | `/api/salas` | salas en vivo: jugadores, roles, estado de la misión |
| POST | `/api/salas/{id}/cerrar` | `{motivo}` → avisa a sus jugadores y los devuelve al lobby |
| POST | `/api/jugadores/{id}/expulsar` | `{motivo}` → mensaje `expulsado` al cliente y cierre del socket |
| POST | `/api/aviso` | `{mensaje}` (máx. 200 caracteres) → `aviso` a todos los conectados |
| GET | `/api/usuarios?buscar=&pagina=` | tabla de auditoría de perfiles con su progreso |
| GET | `/api/usuarios/{usuario}` | detalle + historial + errores frecuentes |
| POST | `/api/usuarios/{usuario}/bloquear` · `/desbloquear` | `{motivo}`; si está conectado, se lo expulsa |
| GET | `/api/logs?nivel=&buscar=&desde=&pagina=` | histórico paginado |
| GET | `/api/logs.csv` | exportación con los mismos filtros |
| GET | `/api/auditoria?pagina=` | acciones de admin |
| GET | `/api/estadisticas` | métricas calculadas con pandas |
| WS | `/api/ws?token=` | empuja `{"tipo":"log",...}` en cuanto ocurre y `{"tipo":"estado",...}` cada 2 s |

- **Por qué el token del WebSocket va en la URL:** el navegador no permite enviar headers propios al abrir un WebSocket.
- **Contraseña:** se compara con `secrets.compare_digest`. **Por qué:** una comparación normal tarda distinto según cuántos caracteres coinciden, y eso permite adivinar la contraseña midiendo tiempos.
- **Si no existe `.env` o falta `ADMIN_PASSWORD`:** el panel arranca **deshabilitado** y lo avisa en el log. Nunca se usa una contraseña por defecto.

### 2.5 Cambios en el juego (protocolo, actualizar `docs/protocolo.md`)
| Servidor → Cliente | Qué hace el cliente Unity |
|---|---|
| `{"t":"expulsado","motivo":"..."}` | Vuelve a la pantalla de conexión con el mensaje en rojo |
| `{"t":"sala_cerrada","motivo":"..."}` | Sale de la partida y vuelve al lobby con el mensaje |
| `{"t":"aviso","msg":"..."}` | Banner amarillo arriba, durante 6 s, en cualquier pantalla |
| `login` de un usuario bloqueado → `error` "Cuenta bloqueada: <motivo>" | Se muestra en la ventana de perfil |

### 2.6 Diseño del panel
- Barra lateral con las secciones, un indicador de "● En vivo" (verde si el WebSocket está conectado) y un botón para cerrar sesión.
- **Toda acción destructiva** (expulsar, cerrar sala, bloquear) pide confirmación y un **motivo obligatorio**. **Por qué:** el motivo es lo que hace útil a la auditoría.
- Tema oscuro, en español, que se vea bien en un proyector a 1280×720.

## 3. Plan de trabajo

### Fase S3-1 — Backend · 🤖
- [ ] `git checkout -b sprint-3` desde `main` (ya con la v0.3).
- [ ] Implementar 2.1 a 2.5 en el servidor. Ajustar el Dockerfile multi-etapa y el compose. Crear `.env.example` y agregar `.env` al `.gitignore`.
- [ ] Tests con `pytest` (`servidor/tests/`):
  1. Login OK; contraseña mala → 401; el sexto intento en un minuto → 429.
  2. Sin token → 401 en todas las rutas protegidas.
  3. Expulsar: un cliente TCP de prueba recibe `expulsado` y se cierra su conexión.
  4. Bloquear: el login del usuario bloqueado falla; si estaba conectado, se lo expulsa.
  5. Aviso: todos los clientes TCP lo reciben.
  6. Cada acción deja su fila en `auditoria_admin`.
  7. `logs.csv` respeta los filtros.
- [ ] **Criterio de terminado:** `pytest` en verde, `probar_servidor.sh` sigue en `TODO OK ✔` (el juego no se rompió) y `curl` a `/api/estado` con token responde.
- [ ] Commit, push y reporte S3-1.

### Fase S3-2 — Frontend base · 🤖
- [ ] `panel/` con Vite + React + Router + Recharts. Páginas Login, Dashboard (con el gráfico) y Salas (en vivo, con expulsar y cerrar).
- [ ] `npm run build` sin errores. La imagen Docker sirve el panel en `http://localhost:8000`.
- [ ] `scripts/panel_dev.sh`: modo desarrollo con Vite (proxy de `/api` → `:8000`) para iterar rápido.
- [ ] Commit y reporte S3-2.

### Fase S3-3 — Frontend: auditoría · 🤖
- [ ] Páginas Usuarios, UsuarioDetalle, Logs (en vivo + histórico + CSV), Auditoría y Estadísticas.
- [ ] Commit y reporte S3-3.

### Fase S3-4 — Cliente Unity · 🤖
- [ ] Manejar `expulsado`, `sala_cerrada` y `aviso`, y el error de cuenta bloqueada (tabla 2.5). Batch sin `error CS` + build de Linux.
- [ ] Commit y reporte S3-4.

### Fase S3-5 — Prueba integral + entrega · 🧑 + 🤖
- [ ] 🧑 Con el panel abierto en el navegador y 2 juegos en Arch:
  - Ver la sala y los jugadores aparecer **en vivo**.
  - Mandar un aviso global → aparece en los 2 juegos.
  - Expulsar a un jugador → vuelve a la pantalla de conexión con el motivo.
  - Bloquear su usuario → no puede volver a entrar.
  - Completar una misión → se refleja en Usuarios y en Estadísticas.
  - Revisar que todo quedó en Auditoría y en Logs, y exportar el CSV.
- [ ] 🧑 Abrir el panel **desde el celular** en la misma red (`http://<IP-de-tu-PC>:8000`). **Por qué:** es la prueba más "palpable" para el inge.
- [ ] 🤖 Paquete de Windows v0.4. `iniciar_servidor_sin_docker.bat` ahora necesita instalar dependencias: crear un venv + `pip install -r requirements.txt` la primera vez, e incluir `panel/dist` ya compilado. LEEME actualizado.
- [ ] 🤖 Merge, tag `v0.4-demo`, push y reporte final.
- [ ] 🤖 `docs/arquitectura.md` con el diagrama 2.1 y una explicación corta de cada pieza, para usar en la presentación.

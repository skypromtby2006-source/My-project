# SPRINT3.md — Panel de administración

> Brief del PM para Claude Code. Siguen vigentes **todas** las reglas de `CLAUDE.md`.
> ⚠️ **Archivo incompleto:** por ahora solo tiene el calendario y las prioridades que dictó el PM el 29/10/2026.
> Falta el detalle de las fases S3-1 a S3-5 (qué entra en cada una). Hay que pegarlo aquí antes de empezar la S3-1.

## 0. Calendario

| Día | Fase |
|---|---|
| Jue 29/10 | Cierre del Sprint 2: prueba S2-3, correcciones, S2-4 y tag `v0.3-demo` **antes de las 22:00** |
| Vie 30/10 | S3-1 |
| Sáb 31/10 | S3-2 + S3-3 |
| Dom 01/11 | S3-4 + S3-5 |

**Corte: domingo 01/11/2026 a las 20:00.** Si a esa hora no está aprobado, se presenta la `v0.3-demo`.

**Requisito previo:** la `v0.3-demo` cerrada (merge a `main` y tag). Su prueba en Windows se hizo **solo con `iniciar_servidor_sin_docker.bat`**, porque Docker Desktop está roto en la PC Windows de prueba (ver `docs/backlog.md`).

## Prioridades

Dentro de cada fase se implementa **en este orden**: primero lo imprescindible, luego lo importante y al final lo que sobre.
**Por qué:** si el corte llega a mitad de una fase, lo que queda sin hacer es lo menos necesario para la presentación.

1. **Imprescindible**
   - Login de administrador
   - Estado del servidor en vivo
   - Salas: expulsar jugadores y cerrar salas
   - Usuarios + detalle de su progreso
   - Logs en vivo
   - Auditoría de las acciones del administrador
2. **Importante**
   - Estadísticas con pandas
   - Bloquear usuarios
   - Aviso global a todos los jugadores
3. **Si sobra tiempo**
   - Exportar a CSV
   - Gráfico de conexiones
   - Histórico paginado

## Fases

_(Pendiente: detalle de S3-1 a S3-5, del PM.)_

# Backlog

Ideas que surgen durante el sprint y quedan **fuera del alcance congelado** (ver `MDs/CLAUDE.md`, secciones 2 y 8).
Se anotan aquí para no perderlas y se priorizan en el siguiente sprint.

| Fecha | Idea | Origen | Notas |
|---|---|---|---|
| 26/10/2026 | Voz integrada en el juego | SPRINT1.md | Por ahora hablan en persona o con una app de voz externa |
| 26/10/2026 | Más misiones / recetas | SPRINT1.md | La receta está en constantes de `server.py`; habría que pasarla a datos |
| 26/10/2026 | Anti-trampas: no enviar `elemento` a los players | SPRINT1.md | Hoy el servidor manda el símbolo a todos y el cliente lo oculta; un cliente modificado podría verlo |
| 26/10/2026 | Validar en el servidor la distancia al agarrar | S1-1 | Hoy el límite de 1.5 m solo lo aplica el cliente |
| 26/10/2026 | VR y física real de los objetos | SPRINT1.md | — |
| 26/10/2026 | **Riesgo del entorno (no del proyecto):** Docker Desktop roto en la PC Windows 11 de prueba | Prueba v0.2 en Windows | Build 22621.525 con Windows Update deshabilitado: `exec format error` en **todos** los contenedores, incluida la imagen del servidor Python. El `.exe` se probó con el servidor corriendo directo con Python (Plan B2). Para una PC sin Docker, conviene documentar ese plan en el LEEME |
| 27/10/2026 | Contraseña con hash bcrypt | SPRINT2.md | Hoy el login es solo con el usuario (decisión del cliente para la demo): cualquiera puede entrar como otro |
| 27/10/2026 | Roles estudiante / docente / admin | SPRINT2.md | Pendiente de consultar con el docente |
| 27/10/2026 | Guardado local estilo Steam Cloud | SPRINT2.md | — |
| 27/10/2026 | Borrar cuenta | SPRINT2.md | También sirve para el derecho de supresión de datos |
| 27/10/2026 | Avatares 3D | SPRINT2.md | Hoy el avatar es la cápsula con el color del perfil |
| 08/11/2026 | Paquete de Windows v0.4 (venv + `pip install`, `panel/dist` compilado y LEEME) | Replanificación del PM | Fuera del alcance del domingo. Sin él, el zip v0.3 sigue con el servidor de la v0.3 (sin panel) |
| 08/11/2026 | Exportar logs a CSV (`/api/logs.csv`) · gráfico de conexiones de los últimos 30 min · histórico paginado de logs en el panel | SPRINT3.md 🟢 | La API `/api/logs` ya pagina y filtra por nivel y texto; falta la pantalla. La página Logs hoy muestra las últimas 2000 líneas en vivo |
| 08/11/2026 | Gráficos en Estadísticas (Recharts) | SPRINT3.md | El domingo se hicieron como tablas simples (prioridad 🟡) |
| 08/11/2026 | Límite de 5 logins por minuto por IP detrás de Docker | S3-1 | Con Docker, todas las conexiones llegan con la IP de la red de Docker (`172.18.0.1`): el límite se comparte entre todos los equipos y la auditoría no ve la IP real. Sin Docker (Plan B2) sí se ve la IP real. Se arregla con `network_mode: host` o un proxy que mande `X-Forwarded-For` |
| 08/11/2026 | Varios admins con roles · HTTPS con certificado · editar perfiles desde el panel · notificaciones por correo | SPRINT3.md | Fuera de alcance del Sprint 3 desde el brief |
| 09/11/2026 | 🟢 Caché de las estadísticas del panel (recalcular cada 30 s) si el volumen de datos crece | Servidor local §6.1 | Medido en `test_concurrencia.py`: con 500 000 errores, pandas deja cortes de ~0,25 s en el juego aunque corra en un hilo (armar el DataFrame retiene el GIL). Con los datos de un aula no se nota; con una caché, el costo se paga como mucho una vez cada 30 s y no en cada visita a la página |

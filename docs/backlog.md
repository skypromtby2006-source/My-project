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

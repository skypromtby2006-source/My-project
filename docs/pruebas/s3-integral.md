# Guion de prueba S3 integral — Panel web de administración (v0.4)

> Lo ejecuta Jona en Arch con el panel abierto en el navegador y 2 juegos (build de Linux).
> Cubre lo 🔴 de `MDs/SPRINT3.md` §0.1 y lo 🟡 que se alcanzó (estadísticas en tabla, aviso global, bloquear).
> La parte automatizable ya la cubren `servidor/tests` (pytest) y `scripts/probar_build.sh panel`, que **no reemplazan** esta prueba: no ven el dibujo, los colores ni los clics reales.

## Preparación
1. `scripts/servidor_iniciar.sh`. La primera vez tarda varios minutos más de lo normal porque la imagen ahora compila el panel (Node) e instala pandas.
2. Abrir **http://localhost:8000** en el navegador.
   - Usuario: `admin`
   - Contraseña: la de `ADMIN_PASSWORD` en el archivo `.env` de la raíz del repo (te la paso en el reporte).
3. `scripts/jugar_linux.sh 2`. El build de Linux ya está compilado con los cambios del Sprint 3.
4. Anotar la hora de inicio: si algo falla, se busca en la página **Logs** del panel o en `scripts/servidor_logs.sh`.

## Pasos

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1 | En el panel, entrar con la contraseña **mal** escrita. Después, con la correcta | Con la mala sale "Usuario o contraseña incorrectos". Con la buena se abre **Estado** y abajo a la izquierda se ve **● En vivo** en verde |
| 2 | En los 2 juegos, conectar a `127.0.0.1` y entrar con 2 perfiles (A y B). Mirar el panel **sin recargar** | En **Estado** suben "Jugadores conectados" y "con sesión iniciada", y A y B aparecen en "Usuarios activos ahora" en 2 s como mucho |
| 3 | A crea una sala y B se une y marca *Listo*. Abrir **Salas** | Aparece la tarjeta con el código de la sala, "⏳ Esperando", A como 🧙 Wizard y B como 🧑‍🔬 Player. Lo de B cambia de "no listo" a "✔ Listo" en vivo |
| 4 | A inicia la partida. B lleva al reactor un elemento que **no** va (por ejemplo Na) y después completa la misión | La tarjeta pasa a "▶ Jugando" y muestra el reactor, lo que falta, el tiempo y **Errores: 1** en rojo. Al terminar dice "✔ Misión completada" |
| 5 | En **Estado**, escribir un aviso en "Mensaje global" (por ejemplo "Prueba de aviso") y *Enviar a todos* | En los 2 juegos aparece arriba una franja amarilla con "AVISO: Prueba de aviso" durante unos 6 s, aunque estén en plena partida. En el panel sale "Aviso enviado a 2 juego(s)" |
| 6 | Abrir **Usuarios**, buscar a B y entrar a su detalle | En la tabla B tiene 1 misión, su mejor tiempo y 1 error. En el detalle están el historial de la misión y, en "Errores frecuentes por elemento", **Na** con su barra, más "Llevó Na cuando faltaba H" (y O) en Confusiones |
| 7 | Abrir **Estadísticas** | Las tablas muestran Na entre los errores más frecuentes, la misión "Sintetizar agua" con su tiempo promedio y la fila de hoy en "Misiones completadas por día". Arriba dice "calculadas con pandas" |
| 8 | A crea otra sala y B se une. En **Salas**, *Cerrar sala* con el motivo **vacío**; después con "Fin de la clase" | Con el motivo vacío no deja ("Escribe el motivo…"). Con motivo, los 2 juegos vuelven a la lista de salas con "Un administrador cerró la sala: Fin de la clase" en rojo, y la tarjeta desaparece del panel |
| 9 | En **Estado**, *Expulsar* a B con el motivo "Prueba de expulsión" | El juego de B vuelve a la pantalla de conexión con "Fuiste expulsado por un administrador. Motivo: Prueba de expulsión" en rojo (**no** "Se perdió la conexión"). B puede volver a conectar y entrar normalmente |
| 10 | Abrir el detalle de B y hacer *🔒 Bloquear cuenta* con un motivo. Con B fuera, intentar entrar con B en el juego. Después, *🔓 Desbloquear* y volver a intentarlo | Si B estaba conectado, lo expulsa con "Cuenta bloqueada: <motivo>". En el panel sale la etiqueta "Bloqueado" y el motivo. Al intentar entrar, la ventana de perfil muestra "Cuenta bloqueada: <motivo>". Después de desbloquear, entra |
| 11 | Abrir **Logs** y, sin recargar, hacer algo en un juego (entrar, crear una sala) | Las líneas nuevas aparecen solas abajo. Si se desmarca INFO quedan las WARNING (expulsiones y bloqueos, en amarillo). La búsqueda por texto filtra (probar con el usuario de B). *⏸ Pausar* congela la vista |
| 12 | Abrir **Auditoría** | Están, de la más nueva a la más vieja: desbloqueo, bloqueo, expulsión, cierre de sala, aviso, inicio de sesión y el **login fallido** (en rojo). Cada fila tiene admin, a quién, el motivo y la IP |
| 13 | **Desde el celular**, en la misma red Wi-Fi: abrir `http://<IP-de-tu-PC>:8000` (la IP la muestra `servidor_iniciar.sh`) y entrar | Se ve el panel adaptado al celular, con el menú ☰. Estado y Salas se actualizan en vivo. Si no carga, revisar el firewall de Arch para el puerto 8000 |
| 14 | Con el panel abierto: `scripts/servidor_detener.sh` y después `scripts/servidor_iniciar.sh` | Mientras el servidor está apagado, el indicador pasa a "● Reconectando…" en rojo. Cuando vuelve, se pone **● En vivo** solo, sin recargar. La Auditoría y los Usuarios siguen ahí (están en PostgreSQL) |
| 15 | Reportar lo que falle | Captura y hora de cada fallo |

**Esperado y no es un fallo:** con Docker, la columna IP muestra `172.18.0.1` para todos (es la red de Docker, ver `docs/backlog.md`).

## Resultado
| Fecha | Build (commit) | Quién | Resultado | Notas |
|---|---|---|---|---|
| | | Jona | | |

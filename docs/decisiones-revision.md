# Decisiones tomadas sin consulta — revisión del 20/11/2026

Trabajo autónomo (sin cliente ni PM). Regla: la opción más simple que mantenga los tests en verde. Cada decisión, con su porqué, para que el PM la revise.

## D1. La mejora visual sale del merge de `sprint-4`, con KayKit incluido
El plan decía "KayKit no está, la mejora es solo con luces, techo, Volume y etiquetas". Al revisar el repo, KayKit **sí está**: `sprint-4` (commit `1e075cd`, CC0, con licencia en `docs/licencias.md`) ya tenía la S4-4 terminada y probada: luz puntual por sala con el color `luz` del JSON, techo, Volume (tonemapping neutral + bloom suave), niebla, etiquetas ocultas salvo con F3 y capturas antes/después en `docs/capturas/s4-4/`.
**Por qué:** rehacer lo mismo "sin assets" costaba horas y daba un resultado peor. El merge (`b2eb566`) solo tuvo 4 conflictos triviales y dejó los **5 escenarios de `probar_build.sh` en verde** (laberinto a 527 FPS a 1920×1080). Si el PM prefiere la versión sin KayKit, se revierte con `git revert -m 1 b2eb566`.

## D2. El rol docente solo existe con base de datos
Sin PostgreSQL ni SQLite (modo memoria, Plan B2) la API del docente responde 503 y `unirse_clase` da error. **Por qué:** duplicar docentes, clases, retos e intentos en listas de memoria era el doble de código y de tests para un modo que solo es de emergencia. El servidor local (.exe) usa SQLite, así que ahí también funciona.

## D3. Pertenencia: 404 y no 403 con lo de otro docente
Si un docente pide una clase, un reto o un estudiante de otro, la API responde **404 "No existe"**. **Por qué:** con 403 confirmaría que esa clase existe. Lo prueba `test_un_docente_no_ve_las_clases_ni_los_retos_de_otro`.

## D4. El docente no usa el WebSocket del admin; su panel consulta cada 2–5 s
El WebSocket empuja TODO el estado y todos los logs; filtrarlo por docente obligaba a reescribirlo. Las páginas del docente piden `/api/docente/vivo` y `/api/docente/logs`, que ya vienen filtradas. **Por qué:** es lo más simple y el docente no necesita tiempo real al milisegundo.

## D5. Logs del docente: líneas que nombran a sus estudiantes, su conexión o su sala
Los logs son texto libre. Se muestran las líneas que contienen (como palabra entera) el usuario de un estudiante suyo, el id de su conexión o el código de la sala donde está ahora. **Por qué:** muchas líneas del servidor nombran la sala o la conexión y no el usuario. Limitación conocida: una línea vieja de una sala que ya cerró y que no nombra al usuario no aparece. Salen del buffer en memoria (últimas 2000 líneas).

## D6. "Jugadores por grupo" es un máximo
`iniciar` rechaza la partida si hay más jugadores que `jugadores_por_grupo`; con menos (mínimo 2, regla de siempre) se puede jugar. **Por qué:** exigir el número exacto deja trabado a un grupo si falta alguien el día de la clase.

## D7. Intento por jugador, Wizard incluido, guardado una sola vez
El progreso de siempre (`misiones_completadas`) solo cuenta a los Players; en un reto se guarda un intento para **cada** jugador, porque el docente evalúa a todo el grupo. Se guarda al terminar el nivel (completado), al agotarse el tiempo, al irse el jugador o al cerrarse la sala a medias (no completado). Un set por partida evita duplicados.

## D8. Semilla: si el docente no la elige, se sortea al crear el reto y queda fija
**Por qué:** "semilla fija" es para que todos los grupos del reto jueguen los mismos números y se puedan comparar; da igual quién la elija mientras no cambie.

## D9. El tiempo límite lo controla el servidor; el reloj del HUD es informativo
Al vencer, el servidor deja de aceptar acciones del laberinto y manda `sala_estado` con `tiempo_agotado`. Los jugadores ven "Se acabó el tiempo del reto" y salen con la acción de siempre. **Por qué:** cerrar la sala en el acto los sacaría sin dejarles leer el mensaje.

## D10. Elegir reto con un botón "Cambiar reto" que rota la lista
En el Lobby, el anfitrión rota entre "Sin reto" y los retos abiertos de sus clases. **Por qué:** UI Toolkit no tiene un desplegable con el estilo del diseño ya hecho; un botón con el estilo existente es lo más simple y lo puede manejar `PruebaAutomatica`.

## D11. Escenario nuevo `reto` en probar_build.sh (ahora son 6)
Usa el servidor de Docker (necesita la BD y el panel, como `panel`). Los 5 de antes no cambiaron.

## D12. Espectador: el docente entra con la pestaña "Docente" del Login, sin menú de juego
El Login del juego tiene una tercera pestaña, **Docente**, con usuario y la contraseña del panel (`login_docente`, verificada con el mismo scrypt). Después del login va directo a la lista de salas: no tiene Mi perfil ni progreso, y "Volver" cierra su sesión. **Por qué:** es lo más simple y evita que el docente toque pantallas que el servidor le rechaza (perfil, crear sala, unirse a clase).

## D13. El espectador no ocupa lugar ni es jugador; mira cualquier sala, llena o en partida
El servidor lo guarda en `sala.espectadores`, aparte de `sala.jugadores`: no cuenta para el máximo, no tiene rol, no marca listo y no aparece en la lista de jugadores. Recibe todo lo que se difunde en la sala; su `pos` se ignora (ni siquiera la manda: la cámara libre no envía posición) y cualquier acción de juego se rechaza con "Los docentes entran como espectadores". En la lista de salas el botón dice **Mirar** y está habilitado aunque la sala esté llena o jugando. **Por qué:** así el espectador no puede cambiar en nada la partida que evalúa.

## D14. Al entrar a una partida en curso recibe el mismo "inicio" que los jugadores
Con el estado de la sala **actual** del laberinto (puertas abiertas hasta ahí). Los jugadores aparecen en su punto de inicio y saltan a su posición real con el próximo `pos` (15 por segundo). **Por qué:** reusar `inicio` evita un mensaje y un camino nuevo en el cliente.

## D15. Cámara libre sin colisiones
WASD + mouse, Q/E para bajar y subir, Shift rápido, Esc sale (como un jugador). Atraviesa paredes. **Por qué:** para mirar desde arriba o cambiar de lado del laberinto (Wizard ↔ Player) sin quedar trabado; un espectador no tiene cuerpo.

## D16. Escenario nuevo `espectador` en probar_build.sh (ahora son 7)
Usa el servidor de Docker como `reto`. Dos bots juegan y el build entra como docente: comprueba cámara libre, que no cuenta como jugador, que ve moverse al Player y que al salir vuelve a la lista sin tocar la partida.

# Guion de presentación — v0.6-demo

> Duración objetivo: **12–15 min + preguntas**. Cada bloque dice **qué se muestra** y **qué se dice**.
> La preparación (qué tiene que estar abierto antes) está en [`tutorial.md`](tutorial.md).
> Ajustado a lo que el juego hace en la v0.6-demo: los cambios respecto del borrador del PM están marcados con **[ajustado]** y explicados en `docs/reportes/presentacion-v0.6-demo.md`.

**Antes de empezar, en pantalla:** las dos ventanas del juego (Eli y Fede) en el Menú principal, la tercera (docente) minimizada, y el navegador con las pestañas admin y docente.

---

## Bloque 1 — El problema (1 min)
*Se muestra:* la pantalla de inicio de sesión del juego.

> "En La Paz, muchos estudiantes de secundaria no tienen acceso a un laboratorio ni a reactivos. Aprenden reacciones químicas solo en la pizarra, y les cuesta imaginarse lo que pasa. Nuestro proyecto es un laboratorio de química en forma de juego cooperativo, preparado para realidad virtual, donde se puede practicar sin reactivos."

## Bloque 2 — El giro del negocio (2 min)
*Se muestra:* el panel docente → **Retos** → el reto de "Química 5to A" (la tabla de resultados con errores por concepto).

> "No vendemos solo un juego: es una **plataforma de aprendizaje y evaluación**. Los estudiantes practican jugando, y el docente crea clases, asigna retos y ve con datos en qué concepto se equivoca cada estudiante: balanceo, mol a mol, masa a masa, reactivo limitante o rendimiento."
>
> "El modelo es **freemium institucional**: el estudiante juega gratis, y el colegio paga una licencia anual que le da su propio servidor, el panel docente y los reportes. Para los colegios fiscales, la licencia la puede cubrir un municipio o un patrocinador."
>
> "Como referencia, Labster, el laboratorio virtual más conocido, cobra desde 5.000 dólares por año por institución. Nosotros apuntamos a una alternativa local, en español y mucho más accesible. El precio exacto lo vamos a validar con entrevistas a colegios."

⚠️ **Verificar antes de presentar** la cifra de Labster en https://labster.com/pricing (no se pudo confirmar desde acá). Si la página no muestra un precio, decir: *"Labster vende licencias institucionales anuales"* sin la cifra.

## Bloque 3 — Los tres roles (1 min)
*Se muestra:* la pantalla de inicio de sesión del juego (pestañas **Estudiante** y **Docente**) y el login del panel.

> "Hay tres roles. El **estudiante** entra solo con su usuario, sin contraseña, porque son menores de edad y pedimos el mínimo de datos. El **docente** entra con usuario y contraseña, y su cuenta la crea el **administrador**, que es quien gestiona el servidor y ve todos los logs."

*(Opcional, 15 s: en la pestaña admin, ir a **Logs** para mostrar los logs en vivo.)*

## Bloque 4 — Demo: el docente prepara la clase (2 min)
*Se muestra:* la pestaña del panel docente.

1. **Mis clases**: mostrar "Química 5to A", su **código de 8 caracteres** y los estudiantes inscritos.
2. **Retos**: mostrar el reto ya creado (aparece como *reto N · laberinto_01 · semilla 20261121*) **[ajustado]**, o crear uno en vivo: elegir la clase en el formulario de arriba → **Crear reto**.

> "Cada reto tiene una **semilla fija**: todos los grupos de la clase juegan exactamente el mismo laberinto con los mismos números. Así la evaluación es justa."

Dictar en voz alta el código de la clase para el bloque siguiente.

## Bloque 5 — Demo: los estudiantes juegan (4 min)
*Se muestran:* las dos ventanas del juego, lado a lado.

1. En las dos ventanas: **Mi perfil** → escribir el código → **Unirse a clase** → **Volver**. **[ajustado: unirse a la clase está en Mi perfil]**
2. Ventana de Eli: **Jugar** → **Crear sala** → **Cambiar reto** hasta que diga *Reto: Química 5to A*. Ventana de Fede: elegir la sala de Eli en la lista → **Estoy listo**. Eli: **Iniciar partida**.

> "Eli es el **Wizard** y Fede el **Player**. El laberinto está separado por un muro: cada jugador ve una parte de la receta y tiene sus propias tareas. Ninguno puede resolverlo solo, así que tienen que comunicarse. Para abrir la puerta, los dos bajan su palanca a la vez." **[ajustado: se nombran los dos lados del juego]**

3. Jugar la **Sala 1**. Mientras tanto:

> "Las cinco salas siguen el orden en que se enseña estequiometría: balanceo, mol a mol, masa a masa, reactivo limitante y rendimiento porcentual. Y el producto de cada sala se usa en la siguiente: el agua de la primera reacciona con sodio en la segunda, y así hasta el final."

4. Equivocarse a propósito una vez: poner un **valor incorrecto en una consola** de la Sala 1 (aparece el aviso de error). **[ajustado: en el juego se ingresan valores en consolas, no "coeficientes" sueltos]**

> "Ese error queda registrado con su concepto, para el docente."

## Bloque 6 — Demo: el docente observa y evalúa (2 min)
*Se muestran:* la tercera ventana del juego (espectador) y el panel docente. **[ajustado: cambia el orden — el espectador y "Partidas en vivo" van mientras se juega; los resultados, después de salir de la sala]**

1. Con la partida todavía en curso, abrir la tercera ventana (docente) → en la lista de salas, **Mirar** en la sala de Eli.

> "El docente entra como **espectador**: ve la partida con una cámara libre, sin ocupar un lugar en la sala."

2. (Opcional) Panel docente → **Partidas en vivo**: la sala de Eli y Fede, en qué sala del laberinto van y cuántos errores llevan.
3. Esc en la ventana del docente (vuelve a la lista). En las ventanas de Eli y Fede: Esc → **Salir de la sala**.
4. Panel docente → **Retos** → el reto → recargar: aparecen los intentos de Eli y Fede, con el **tiempo** y los **errores por concepto** de cada uno (el error de la Sala 1 en la columna *balanceo*), junto a los de Ana, Beto, Carla y Dani.

> "El intento se guarda cuando el grupo termina el laberinto o sale de la sala. El docente no tiene que adivinar quién entendió: ve en qué concepto se traba cada uno, y puede reforzar justo eso en la clase."

## Bloque 7 — Arquitectura y servidor (2 min)
*Se muestran:* la ventana de `QuimicaServidor.exe`, el panel admin y (si hay Docker en la PC) `docker compose ps`.

> "Hay dos formas de tener el servidor. El **servidor local** es un solo `.exe`: el colegio lo abre con doble clic y no necesita instalar nada, y guarda los datos en SQLite, un solo archivo. El **servidor dedicado** usa Docker con PostgreSQL, para el servidor oficial. Es el mismo código en los dos casos: todo el acceso a datos pasa por una capa llamada repositorio, que permite cambiar de base de datos sin tocar la lógica del juego."
>
> "El servidor `.exe` de cada versión se construye y se prueba automáticamente en una máquina con Windows antes de publicarse. Además hay **166 pruebas automáticas** del servidor, que corren contra las dos bases de datos, y **9 escenarios** que abren el juego real y lo juegan solos." **[ajustado: el que se construye y prueba en Windows es el servidor; el juego se construye en Linux y se prueba con los escenarios. Cifras reales al momento del tag]**

## Bloque 8 — Cierre y próximos pasos (1 min)

> "Lo que viene: arte final del laberinto, generación procedural de niveles con semilla para que el docente controle la dificultad, pistas integradas en el escenario para aprender descubriendo, y la versión en realidad virtual, para la que el código ya está preparado: la forma de interactuar está separada de la forma de ingresar, así que agregar los controles del visor no cambia el resto."

*(Todo esto es trabajo futuro: hoy la semilla cambia los números de cada sala, no la forma del laberinto.)*

---

## Qué NO mostrar
- La página **Estadísticas** del admin como "análisis por concepto": sus tablas de errores vienen de la misión vieja del agua y con el laberinto quedan vacías. Los errores por concepto se muestran en el **panel docente** (Retos → resultados).
- El contador "Errores cometidos" de **Mi perfil** en el juego: también es de la misión vieja.

## Preguntas probables (tabla para estudiar)
| Pregunta | Respuesta corta |
|---|---|
| ¿Cómo evitan que un estudiante entre como docente? | La cuenta docente la crea solo el admin y tiene contraseña; la del estudiante no da acceso al panel. |
| ¿Dónde están los datos? | En el servidor local, en `quimica.db` junto al `.exe`. En el dedicado, en PostgreSQL dentro de Docker, con un volumen persistente. |
| ¿Y si no hay internet en el colegio? | El servidor local funciona en la red del colegio, sin internet. |
| ¿Cómo es justa la evaluación si juegan en grupo? | Los errores se atribuyen al estudiante que los cometió, y todos los grupos juegan con la misma semilla. |
| ¿Por qué el estudiante no tiene contraseña? | Minimización de datos de menores: solo usuario, nombre visible y color. |
| ¿Qué datos de mercado tienen? | 1.231.872 estudiantes de secundaria en Bolivia (Memoria Institucional 2024 del Ministerio de Educación, vía SITEAL-UNESCO). El precio se valida con entrevistas. ⚠️ Confirmar la cifra en la fuente antes de presentar. |
| ¿Cuándo llega la VR? | En la fase siguiente; la arquitectura ya separa la interacción del dispositivo de entrada. |
| ¿Qué pasa si el antivirus bloquea el `.exe`? | Hay un plan C: el mismo servidor con un `.bat` que lo corre con Python (hay que tener Python instalado). **[ajustado]** |
| ¿Qué pasa si se corta el servidor en plena clase? | Al reabrirlo, perfiles, clases y resultados siguen ahí. La partida en curso se pierde y el grupo vuelve a entrar. |

**Fuentes que se pueden citar:** SITEAL-UNESCO, perfil educativo de Bolivia (https://siteal.iiep.unesco.org/pais/educacion-pdf/bolivia) · Labster, página de precios (https://labster.com/pricing).

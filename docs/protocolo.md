# Protocolo de red — Juego de Química (demo)

**Transporte:** TCP, puerto **7777**. Cada mensaje es **un objeto JSON en una sola línea**, terminado en `\n`, codificado en UTF-8.
El campo `t` indica el tipo de mensaje.

**Por qué TCP + JSON por línea:** TCP garantiza que los mensajes llegan completos y en orden (en un lobby no se puede perder un "me uní a la sala"). Pero TCP es un flujo de bytes, no de mensajes: cortar por `\n` marca dónde termina cada uno. JSON se lee a simple vista en los logs y lo entienden Python y C# sin librerías extra.

> ⚠️ **Números:** todo número que viaje en el JSON se escribe con punto decimal (`InvariantCulture` en C#). En un Windows en español, `1.5f.ToString()` da `"1,5"` y rompe el JSON.

> Cambiar este protocolo obliga a actualizar **este archivo**, `servidor/server.py` y `QuimicaVR/Assets/Scripts/Red/ClienteRed.cs` en el mismo commit.

## Resumen

| Cliente → Servidor | Servidor → Cliente |
|---|---|
| `registro`, `login` | `perfil` (tu id, tus datos y tu progreso) |
| `perfil_editar`, `perfil_ver` | `perfil` (+ `sala` a toda la sala si estás en una) |
| `listar` | `salas` (lista) |
| `crear_sala`, `unirse`, `salir` | `sala` (estado completo de la sala), `fuera` |
| `listo`, `iniciar` (solo anfitrión) | `inicio` |
| `pos` (x, y, z, rotación) | `pos` (de los demás), `salio`, `error` |
| `agarrar`, `soltar` (solo player) | `obj` (estado de un objeto), `estado` (estado de la misión) |
| `senalar` (solo wizard) | `senal` |
| `reiniciar` (solo wizard) | `inicio` con la misión nueva |
| `ping` | `pong` |

## Sesión

- **Primero la identidad:** sin `registro` o `login` previo, el servidor rechaza `listar`, `crear_sala`, `unirse`, `perfil_editar` y `perfil_ver` con `"Inicia sesión primero"`. Sin identidad no hay a quién asignarle el progreso.
- **Una sesión por usuario:** un segundo `login` con un usuario conectado se rechaza; si no, dos ventanas sumarían progreso al mismo perfil. Al desconectarse, el usuario se libera.
- Una conexión inicia sesión una sola vez (`"Ya iniciaste sesión en esta conexión"`); para cambiar de usuario se reconecta.
- `hola`/`bienvenido` ya no existen: la identidad viene del perfil.
- **Las validaciones las impone el servidor.** El cliente también valida, pero solo por comodidad.

**Paleta** (constante en `server.py` y en `ClienteRed.cs`): `#3FA9F5 #F5D33F #E04FD8 #4FE07A #F5913F #E04F4F #FFFFFF #6A5AE0`. El servidor acepta minúsculas y guarda el color en mayúsculas.

## Cliente → Servidor

| `t` | Campos | Qué hace | Validaciones del servidor |
|---|---|---|---|
| `registro` | `usuario`, `nombre`, `color` | Crear un perfil e iniciar sesión con él | `usuario` se pasa a minúsculas y debe cumplir `^[a-z0-9_]{3,16}$` (no se puede cambiar después); `nombre` de 1 a 20 caracteres; `color` de la *paleta*. Usuario repetido → `"Ese usuario ya existe"` |
| `login` | `usuario` | Iniciar sesión (sin contraseña: decisión del cliente para la demo) | Debe existir (`"Usuario no encontrado"`) y no tener otra sesión abierta (`"Ese usuario ya tiene una sesión abierta"`) |
| `perfil_editar` | `nombre`, `color` | Cambiar el nombre visible y el color | Mismas reglas que en `registro`. Si estás en una sala, todos reciben `sala` actualizada |
| `perfil_ver` | — | Pedir el perfil con el progreso al día | Requiere sesión |
| `listar` | — | Pedir la lista de salas | — |
| `crear_sala` | `nombre_sala`, `maximo` | Crear sala y entrar como anfitrión | Nombre a 30 caracteres; `maximo` entre 2 y 8 (por defecto 4). Si ya estaba en una sala, primero sale |
| `unirse` | `sala_id` (código de 4 letras) | Entrar a una sala | Debe existir, estar `esperando` y no estar llena. No distingue mayúsculas |
| `salir` | — | Salir de la sala actual | — |
| `listo` | `valor` (bool) | Marcar / desmarcar "Listo" | Solo dentro de una sala |
| `iniciar` | — | Empezar la partida | Solo el anfitrión, con **al menos 2 jugadores** y todos los demás listos |
| `pos` | `x`, `y`, `z`, `ry` (float) | Posición y rotación Y del jugador (~15 veces/seg) | Solo con la partida `jugando`; se reenvía a los demás de la sala. El servidor guarda la última |
| `agarrar` | `obj` (id, p. ej. `"o3"`) | Tomar un objeto | Solo `player`; el objeto no tiene portador ni está en el reactor; el jugador no lleva otro; la misión no está completada |
| `soltar` | `obj`, `x`, `y`, `z` (float) | Dejar el objeto que llevo en esa posición | Solo `player` y solo el portador. Si `(x, z)` cae dentro del reactor, se evalúa la receta (ver *Misión*) |
| `senalar` | `obj` | Marcar un objeto para que todos lo vean pulsar | Solo `wizard` |
| `reiniciar` | — | Volver a empezar la misión | Solo `wizard`; responde con `inicio` |
| `ping` | — | Comprobar la conexión | — |

## Servidor → Cliente

| `t` | Campos | Cuándo |
|---|---|---|
| `perfil` | `id`, `usuario`, `nombre`, `color`, `progreso` | Respuesta a `registro`, `login`, `perfil_editar` y `perfil_ver`. `id` es el de la conexión e identifica al jugador en los demás mensajes (`host`, `portador`, `pos`) |
| `salas` | `lista`: array de *sala* | Respuesta a `listar` |
| `sala` | `sala`: objeto *sala* | Cada vez que cambia la sala (alguien entra, sale o marca listo). Se envía a todos sus jugadores |
| `fuera` | — | Confirmación de `salir` |
| `inicio` | `sala`: objeto *sala*, `mision`: objeto *misión* | El anfitrión inició la partida, o el wizard reinició la misión |
| `pos` | `id`, `x`, `y`, `z`, `ry` | Posición de otro jugador |
| `salio` | `id` | Un jugador dejó la sala (o se desconectó) |
| `obj` | `obj`: objeto *objeto* | Un objeto cambió (lo agarraron, lo soltaron, volvió a la mesa o se le cayó a alguien) |
| `senal` | `obj`, `por` (id del wizard) | El wizard señaló un objeto: todos lo hacen pulsar ~2 s |
| `estado` | `reactor` (símbolos), `errores`, `completada`, `mensaje` | Después de cada `soltar` |
| `error` | `msg` | Petición rechazada (sala llena, no existe, no eres anfitrión, JSON inválido…) |
| `pong` | — | Respuesta a `ping` |

### Objeto *sala*

```json
{
  "id": "AB12",
  "nombre": "Lab 1",
  "host": "3ea3b344",
  "maximo": 4,
  "cantidad": 2,
  "estado": "esperando",
  "jugadores": [
    {"id": "3ea3b344", "nombre": "Ana", "color": "#3FA9F5", "listo": false, "rol": "wizard"},
    {"id": "2fce7993", "nombre": "Beto", "color": "#E04F4F", "listo": true, "rol": "player"}
  ]
}
```

- `id`: código de 4 caracteres, sin letras confusas (sin `O/0` ni `I/1`).
- `estado`: `esperando` | `jugando`.
- `rol`: `wizard` (el anfitrión) | `player` (los demás). Si cambia el anfitrión, cambia el rol.
- `nombre` y `color` salen del perfil de cada jugador.

### Objeto *perfil*

```json
{"t": "perfil", "id": "2fce7993", "usuario": "beto", "nombre": "Beto", "color": "#E04F4F",
 "progreso": {"completadas": 3, "mejor_tiempo_s": 41.2, "errores_totales": 5,
              "historial": [{"fecha": "2026-10-27T14:03:10+00:00", "duracion_s": 41.2, "errores": 1}]}}
```

- `mejor_tiempo_s` es el mejor tiempo en "Sintetizar agua"; `0` = todavía sin misiones (`JsonUtility` no lee `null` en un `float`).
- `errores_totales`: todos los `reaccion_fallida` de ese usuario, también los de misiones reiniciadas o sin terminar.
- `historial`: las últimas 5 misiones completadas, la más reciente primero. `fecha` en ISO 8601 (UTC).

### Objeto *misión* (en `inicio`)

```json
{
  "objetos": [
    {"id": "o1", "elemento": "H", "x": -1.75, "y": 1.15, "z": 0.0, "portador": ""},
    "... 6 en total: H, H, O, Na, Cl y C"
  ],
  "reactor": {"x": 0.0, "y": 0.0, "z": 4.0, "radio": 1.0},
  "mesa": {"x": 0.0, "y": 0.5, "z": 0.0, "ancho": 4.0, "alto": 1.0, "largo": 1.5},
  "radio_objeto": 0.15,
  "receta": [{"elemento": "H", "cantidad": 2}, {"elemento": "O", "cantidad": 1}],
  "formula": "2 H + 1 O → H2O",
  "estado": {"reactor": [], "errores": 0, "completada": false, "mensaje": ""}
}
```

- **El escenario sale de aquí:** el cliente no tiene posiciones propias de la mesa, las esferas ni el reactor; los dibuja con estos datos. `mesa` es el centro y el tamaño de la caja (x = ancho, y = alto, z = largo); `reactor` es el centro de un disco en el suelo. Así la única fuente de verdad es `server.py`.
- *Objeto*: `portador` es el `id` del jugador que lo lleva, o `""` si nadie (cadena vacía y no `null`, para que `JsonUtility` lo lea sin sorpresas).
- `receta` es una lista y no un diccionario porque `JsonUtility` de Unity no lee diccionarios.
- Los objetos van en 6 posiciones fijas sobre la mesa, pero **los elementos se barajan** en cada misión: si no, el player los memorizaría y ya no necesitaría al wizard.
- **Mientras alguien lleva un objeto no viajan mensajes extra:** cada cliente lo dibuja sobre la cápsula de su `portador`, cuya posición ya llega por `pos`. Así se ahorra red y no hay un segundo flujo de posiciones que se pueda desincronizar.

## Misión: sintetizar agua

Al `soltar` dentro del reactor (distancia horizontal al centro ≤ `radio`), el servidor compara el elemento con lo que **falta** de la receta:

- **Falta** → entra al reactor (ya no se puede agarrar) y `mensaje = "H agregado al reactor"`. Si era el último: `completada = true` y `mensaje = "¡Reacción completada! 2 H + 1 O → H2O"`.
- **No falta** → `errores + 1`, el objeto **vuelve a su lugar en la mesa** y `mensaje = "Reacción inestable: Na no va en la receta"`.
- Fuera del reactor, el objeto simplemente queda donde se soltó.

Con la misión completada ya no se puede agarrar; el wizard puede `reiniciar`.

**Progreso:** al completarse, se guarda un registro en `misiones_completadas` por cada **player** presente en la sala, con sus propios errores en esa misión. El wizard guía pero no suma. Cada error se atribuye al player que soltó el elemento.

## Reglas de la sala

- **Servidor autoritativo:** el servidor valida todo; el cliente solo *pide*. Así un cliente modificado no puede, por ejemplo, iniciar una partida ajena.
- **Si el anfitrión se va**, el rol pasa al siguiente jugador (los demás reciben `salio` y luego `sala` con el nuevo `host`), que se vuelve **wizard**: sin wizard la misión no se puede ganar.
- **Si se va alguien que llevaba un objeto**, el objeto cae al suelo en su última posición (`obj` con `portador: ""`). Lo mismo si el player que pasa a wizard llevaba algo, porque un wizard no puede soltar.
- **Dos jugadores agarran la misma esfera a la vez:** el servidor atiende un mensaje por vez; el primero se la lleva y el segundo recibe `error`.
- **Si la sala queda vacía**, se elimina: no quedan salas "fantasma" en la lista.

## Ejemplo de sesión

```
→ {"t":"login","usuario":"ana"}
← {"t":"perfil","id":"3ea3b344","usuario":"ana","nombre":"Ana","color":"#3FA9F5","progreso":{...}}
→ {"t":"crear_sala","nombre_sala":"Lab 1","maximo":4}
← {"t":"sala","sala":{"id":"AB12", ... }}
   (Beto se une y marca listo: Ana recibe más mensajes "sala")
→ {"t":"iniciar"}
← {"t":"inicio","sala":{ ... "estado":"jugando" ... }}
→ {"t":"pos","x":1.5,"y":0,"z":2,"ry":90}
← {"t":"pos","id":"2fce7993","x":-1.0,"y":0.0,"z":0.5,"ry":180.0}
```

## Persistencia (PostgreSQL)

El servidor guarda un registro en la tabla `eventos (id, tipo, detalle JSONB, fecha)`.
Tipos: `perfil_creado`, `conexion` (al iniciar sesión), `desconexion`, `sala_creada`, `union`, `partida_iniciada`, `sala_cerrada`,
`agarrar`, `soltar`, `senal`, `reaccion_fallida` (`{usuario, esperado, recibido}`: quién lo soltó, lo que faltaba y lo que entró), `mision_completada` (`{errores, duracion_s}`) y `mision_reiniciada`.
`reaccion_fallida` es el dato de "errores frecuentes" para el análisis posterior con pandas.
Además:

```sql
usuarios (id, usuario UNIQUE, nombre, color, creado, ultimo_login)
misiones_completadas (id, usuario_id → usuarios, mision, sala, duracion_s, errores, fecha)
```

Las tablas se crean con `CREATE TABLE IF NOT EXISTS` al arrancar el servidor y no con un `.sql` en `docker-entrypoint-initdb.d`: Postgres solo ejecuta esos scripts con el volumen vacío, y `datos_db` ya existe en las instalaciones anteriores.

El perfil guarda **solo** usuario, nombre visible y color: los usuarios son estudiantes de secundaria, en su mayoría menores de edad (minimización de datos).

Si la BD no está disponible (o en el Plan B2, sin Docker), el servidor sigue funcionando en memoria, **perfiles y progreso incluidos**, pero se pierden al cerrarlo; lo avisa con un `WARNING` al arrancar. En una demo en vivo no debe caerse todo por la base de datos.

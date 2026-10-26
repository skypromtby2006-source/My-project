# Protocolo de red — Juego de Química (demo)

**Transporte:** TCP, puerto **7777**. Cada mensaje es **un objeto JSON en una sola línea**, terminado en `\n`, codificado en UTF-8.
El campo `t` indica el tipo de mensaje.

**Por qué TCP + JSON por línea:** TCP garantiza que los mensajes llegan completos y en orden (en un lobby no se puede perder un "me uní a la sala"). Pero TCP es un flujo de bytes, no de mensajes: cortar por `\n` marca dónde termina cada uno. JSON se lee a simple vista en los logs y lo entienden Python y C# sin librerías extra.

> ⚠️ **Números:** todo número que viaje en el JSON se escribe con punto decimal (`InvariantCulture` en C#). En un Windows en español, `1.5f.ToString()` da `"1,5"` y rompe el JSON.

> Cambiar este protocolo obliga a actualizar **este archivo**, `servidor/server.py` y `QuimicaVR/Assets/Scripts/Red/ClienteRed.cs` en el mismo commit.

## Resumen

| Cliente → Servidor | Servidor → Cliente |
|---|---|
| `hola` (nombre) | `bienvenido` (tu id) |
| `listar` | `salas` (lista) |
| `crear_sala`, `unirse`, `salir` | `sala` (estado completo de la sala), `fuera` |
| `listo`, `iniciar` (solo anfitrión) | `inicio` |
| `pos` (x, y, z, rotación) | `pos` (de los demás), `salio`, `error` |
| `agarrar`, `soltar` (solo player) | `obj` (estado de un objeto), `estado` (estado de la misión) |
| `senalar` (solo wizard) | `senal` |
| `reiniciar` (solo wizard) | `inicio` con la misión nueva |
| `ping` | `pong` |

## Cliente → Servidor

| `t` | Campos | Qué hace | Validaciones del servidor |
|---|---|---|---|
| `hola` | `nombre` | Presentarse al conectar | Nombre recortado a 20 caracteres; vacío → `"Jugador"` |
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
| `bienvenido` | `id`, `nombre` | Respuesta a `hola`. `id` identifica al jugador en los demás mensajes |
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
    {"id": "3ea3b344", "nombre": "Ana", "listo": false, "rol": "wizard"},
    {"id": "2fce7993", "nombre": "Beto", "listo": true, "rol": "player"}
  ]
}
```

- `id`: código de 4 caracteres, sin letras confusas (sin `O/0` ni `I/1`).
- `estado`: `esperando` | `jugando`.
- `rol`: `wizard` (el anfitrión) | `player` (los demás). Si cambia el anfitrión, cambia el rol.

### Objeto *misión* (en `inicio`)

```json
{
  "objetos": [
    {"id": "o1", "elemento": "H", "x": -1.25, "y": 1.15, "z": 0.0, "portador": ""},
    "... 6 en total: H, H, O, Na, Cl y C"
  ],
  "reactor": {"x": 0.0, "y": 0.0, "z": 4.0, "radio": 1.0},
  "receta": [{"elemento": "H", "cantidad": 2}, {"elemento": "O", "cantidad": 1}],
  "formula": "2 H + 1 O → H₂O",
  "estado": {"reactor": [], "errores": 0, "completada": false, "mensaje": ""}
}
```

- *Objeto*: `portador` es el `id` del jugador que lo lleva, o `""` si nadie (cadena vacía y no `null`, para que `JsonUtility` lo lea sin sorpresas).
- `receta` es una lista y no un diccionario porque `JsonUtility` de Unity no lee diccionarios.
- Los objetos van en 6 posiciones fijas sobre la mesa, pero **los elementos se barajan** en cada misión: si no, el player los memorizaría y ya no necesitaría al wizard.
- **Mientras alguien lleva un objeto no viajan mensajes extra:** cada cliente lo dibuja sobre la cápsula de su `portador`, cuya posición ya llega por `pos`. Así se ahorra red y no hay un segundo flujo de posiciones que se pueda desincronizar.

## Misión: sintetizar agua

Al `soltar` dentro del reactor (distancia horizontal al centro ≤ `radio`), el servidor compara el elemento con lo que **falta** de la receta:

- **Falta** → entra al reactor (ya no se puede agarrar) y `mensaje = "H agregado al reactor"`. Si era el último: `completada = true` y `mensaje = "¡Reacción completada! 2 H + 1 O → H₂O"`.
- **No falta** → `errores + 1`, el objeto **vuelve a su lugar en la mesa** y `mensaje = "Reacción inestable: Na no va en la receta"`.
- Fuera del reactor, el objeto simplemente queda donde se soltó.

Con la misión completada ya no se puede agarrar; el wizard puede `reiniciar`.

## Reglas de la sala

- **Servidor autoritativo:** el servidor valida todo; el cliente solo *pide*. Así un cliente modificado no puede, por ejemplo, iniciar una partida ajena.
- **Si el anfitrión se va**, el rol pasa al siguiente jugador (los demás reciben `salio` y luego `sala` con el nuevo `host`), que se vuelve **wizard**: sin wizard la misión no se puede ganar.
- **Si se va alguien que llevaba un objeto**, el objeto cae al suelo en su última posición (`obj` con `portador: ""`). Lo mismo si el player que pasa a wizard llevaba algo, porque un wizard no puede soltar.
- **Dos jugadores agarran la misma esfera a la vez:** el servidor atiende un mensaje por vez; el primero se la lleva y el segundo recibe `error`.
- **Si la sala queda vacía**, se elimina: no quedan salas "fantasma" en la lista.

## Ejemplo de sesión

```
→ {"t":"hola","nombre":"Ana"}
← {"t":"bienvenido","id":"3ea3b344","nombre":"Ana"}
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
Tipos: `conexion`, `desconexion`, `sala_creada`, `union`, `partida_iniciada`, `sala_cerrada`,
`agarrar`, `soltar`, `senal`, `reaccion_fallida` (`{esperado, recibido}`: lo que faltaba y lo que entró), `mision_completada` (`{errores, duracion_s}`) y `mision_reiniciada`.
`reaccion_fallida` es el dato de "errores frecuentes" para el análisis posterior con pandas.
Si la BD no está disponible el servidor sigue funcionando en memoria: en una demo en vivo no debe caerse todo por la base de datos.

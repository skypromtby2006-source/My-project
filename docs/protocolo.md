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
| `iniciar` | — | Empezar la partida | Solo el anfitrión, y todos los demás deben estar listos |
| `pos` | `x`, `y`, `z`, `ry` (float) | Posición y rotación Y del jugador (~15 veces/seg) | Solo con la partida `jugando`; se reenvía a los demás de la sala |
| `ping` | — | Comprobar la conexión | — |

## Servidor → Cliente

| `t` | Campos | Cuándo |
|---|---|---|
| `bienvenido` | `id`, `nombre` | Respuesta a `hola`. `id` identifica al jugador en los demás mensajes |
| `salas` | `lista`: array de *sala* | Respuesta a `listar` |
| `sala` | `sala`: objeto *sala* | Cada vez que cambia la sala (alguien entra, sale o marca listo). Se envía a todos sus jugadores |
| `fuera` | — | Confirmación de `salir` |
| `inicio` | `sala`: objeto *sala* | El anfitrión inició la partida |
| `pos` | `id`, `x`, `y`, `z`, `ry` | Posición de otro jugador |
| `salio` | `id` | Un jugador dejó la sala (o se desconectó) |
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
    {"id": "3ea3b344", "nombre": "Ana", "listo": false},
    {"id": "2fce7993", "nombre": "Beto", "listo": true}
  ]
}
```

- `id`: código de 4 caracteres, sin letras confusas (sin `O/0` ni `I/1`).
- `estado`: `esperando` | `jugando`.

## Reglas de la sala

- **Servidor autoritativo:** el servidor valida todo; el cliente solo *pide*. Así un cliente modificado no puede, por ejemplo, iniciar una partida ajena.
- **Si el anfitrión se va**, el rol pasa al siguiente jugador (los demás reciben `salio` y luego `sala` con el nuevo `host`).
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
Tipos: `conexion`, `desconexion`, `sala_creada`, `union`, `partida_iniciada`, `sala_cerrada`.
Si la BD no está disponible el servidor sigue funcionando en memoria: en una demo en vivo no debe caerse todo por la base de datos.

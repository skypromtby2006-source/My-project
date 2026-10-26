# Demo multijugador — Juego de Química

Qué incluye esta demo:
- Servidor en **Python** (asyncio, TCP) que corre en **Docker** junto a **PostgreSQL**
- Cliente en **Unity**: conexión por IP, **crear sala**, **unirse** (por lista o por código de 4 letras), "Listo", el anfitrión inicia y todos se ven moverse en un escenario plano
- Scripts `.bat` para instalar/levantar el servidor con un doble clic e instalador `.exe` opcional (Inno Setup)

```
demo/
├─ Servidor/            server.py, Dockerfile, requirements.txt, probar_cliente.py
├─ Unity/Scripts/       ClienteRed.cs, MenuLobby.cs, GestorPartida.cs
├─ Instalador/          QuimicaDemo.iss  (instalador opcional)
├─ docker-compose.yml   servidor + PostgreSQL
└─ *.bat                instalar_servidor, detener_servidor, ver_logs, ver_eventos_bd, abrir_firewall
```

---

## 1. Levantar el servidor (10 min)

1. Instala **Docker Desktop** (si no lo tienes) y ábrelo hasta que diga *Engine running*.
2. Doble clic en **`instalar_servidor.bat`**.
   - Construye la imagen de Python, levanta PostgreSQL y el servidor en el puerto **7777**.
   - Al final te muestra tus IP de red local.
3. Comprobar que funciona sin Unity: `python Servidor/probar_cliente.py` → debe terminar en **TODO OK ✔**.

**Por qué Docker:** el docente puede correr exactamente el mismo servidor en otra PC sin instalar Python ni PostgreSQL a mano. `docker-compose.yml` describe los dos contenedores y cómo se conectan entre sí (el servidor llega a la BD por el nombre `db`, la red interna de Docker resuelve ese nombre).

**Por qué la BD es opcional en el código:** si PostgreSQL falla, el servidor sigue funcionando en memoria. En una demo en vivo lo último que quieres es que todo se caiga por la base de datos. Por ahora la BD guarda un registro de eventos (conexiones, salas creadas, partidas iniciadas) que puedes mostrar con `ver_eventos_bd.bat` — sirve de evidencia de que Python + PostgreSQL están integrados.

## 2. Montar el cliente en Unity (20 min)

1. Copia la carpeta `Unity/Scripts` dentro de `Assets/` de tu proyecto.
2. Crea una escena nueva (o usa una vacía) con su **Main Camera** y una **Directional Light**.
3. Crea un GameObject vacío llamado **`Red`** y agrégale los tres scripts: `ClienteRed`, `MenuLobby`, `GestorPartida`.
4. *Edit → Project Settings → Player → Active Input Handling* = **Both** (o *Input Manager (Old)*). Los scripts usan `Input.GetAxisRaw`; si el proyecto solo tiene el *Input System* nuevo, lanza error.
5. Dale Play: conecta a `127.0.0.1`, crea una sala.

Nada más. No hay Canvas ni prefabs: el menú es **IMGUI** (`OnGUI`) y el escenario se genera por código.
**Por qué así:** para una demo con plazo de un día, armar UI con Canvas consume horas en cosas visuales. IMGUI te da un menú funcional en código puro; en la siguiente fase lo cambias por la UI definitiva sin tocar `ClienteRed`, que es el que realmente habla con el servidor.

## 3. Generar el ejecutable (10 min)

1. *File → Build Settings* → agrega la escena → *Windows, x86_64*.
2. *Player Settings*: Product Name = **QuimicaDemo**, *Fullscreen Mode* = **Windowed** (resolución 1280×720). En ventana puedes abrir 2–3 copias en la misma PC para mostrar el multijugador.
3. Build en una carpeta **`Build/`** al lado de `Servidor/`.

### (Opcional) Instalador .exe
Instala [Inno Setup](https://jrsoftware.org/isinfo.php), abre `Instalador/QuimicaDemo.iss` y compila. Genera `QuimicaDemo_Setup.exe` que instala el juego + la carpeta del servidor, crea accesos directos y abre el puerto 7777 en el firewall.

## 4. Guion para presentar la demo

1. Doble clic en `instalar_servidor.bat` → se ve Docker levantando los contenedores.
2. `ver_logs.bat` en otra ventana (el docente ve en vivo lo que pasa en el servidor).
3. Abre 2 copias del juego → Jugador A crea sala → aparece el **código**.
4. Jugador B ve la sala en la lista (se refresca sola cada 2 s) o escribe el código → entra.
5. B marca **Listo** → A pulsa **Iniciar** → ambos se mueven con WASD y se ven en tiempo real.
6. `ver_eventos_bd.bat` → los eventos quedaron guardados en PostgreSQL.
7. Si hay otra laptop en la misma red: conecta con la IP que mostró el `.bat`.

---

## Cómo funciona por dentro (para defenderlo)

**Protocolo:** TCP con un mensaje **JSON por línea**. TCP garantiza que los mensajes llegan completos y en orden, que es justo lo que necesita un lobby (no puedes perder un "me uní a la sala"). Cortar por `\n` resuelve el problema clásico de TCP: es un flujo de bytes, no de mensajes, así que hay que marcar dónde termina cada uno.

| Cliente → Servidor | Servidor → Cliente |
|---|---|
| `hola` (nombre) | `bienvenido` (tu id) |
| `listar` | `salas` (lista) |
| `crear_sala`, `unirse`, `salir` | `sala` (estado completo de la sala) |
| `listo`, `iniciar` (solo anfitrión) | `inicio` |
| `pos` (x, y, z, rotación) | `pos` (de los demás), `salio`, `error` |

**Servidor autoritativo:** el servidor valida todo (sala llena, partida ya iniciada, solo el anfitrión inicia, todos listos). El cliente solo *pide*; así un cliente modificado no puede, por ejemplo, iniciar una partida ajena.

**asyncio:** un solo hilo atiende a todos los jugadores, porque mientras espera datos de uno no se bloquea, atiende a otro. Para decenas de jugadores es de sobra y evita los problemas de sincronizar hilos.

**En Unity, ¿por qué un hilo + cola?** Leer del socket bloquea; si lo haces en el hilo principal el juego se congela. El hilo de fondo solo encola los mensajes y `Update()` los procesa en el hilo principal, porque la API de Unity (crear objetos, mover cosas) **solo** se puede usar desde ahí.

**Posición 15 veces/seg + interpolación:** mandar cada frame (60+) desperdicia red sin mejora visible; con 15 envíos y `Lerp` en los remotos, el movimiento se ve suave.

**El anfitrión se va:** el servidor pasa el rol al siguiente jugador, y si la sala queda vacía la elimina. Así no quedan salas "fantasma" en la lista.

**`InvariantCulture` al enviar posiciones:** en una PC con Windows en español, `1.5f.ToString()` da `"1,5"`, lo que rompe el JSON. Es un bug típico en Bolivia/Latinoamérica.

## Problemas comunes

| Síntoma | Causa / solución |
|---|---|
| "No se pudo conectar…" | El servidor no está arriba → `docker compose ps`, o IP equivocada |
| Otra PC no conecta | Firewall → `abrir_firewall.bat` como administrador; ambas PCs en la misma red |
| Error de `Input` en consola | Active Input Handling = Both |
| Nombres flotantes no se ven | Versión de Unity sin fuente incorporada; no afecta la demo |
| `docker compose` no existe | Docker Desktop muy viejo → actualizar (o usar `docker-compose` con guion) |

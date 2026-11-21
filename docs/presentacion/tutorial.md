# Tutorial de preparación — presentación v0.6-demo

> Para Jona. Paso a paso, en orden. Fecha y hora de la presentación: **____________** (completar).
> Lo que se dice en cada momento está en [`guion.md`](guion.md).

## Palabras que aparecen acá
- **Servidor**: el programa `QuimicaServidor.exe`. Tiene que estar abierto todo el tiempo: el juego y el panel se conectan a él.
- **Panel**: la página web del servidor, `http://localhost:8000`. Ahí entran el admin y el docente.
- **IP**: la dirección de la PC en la red (por ejemplo `192.168.0.5`). La muestra la ventana del servidor.
- **Código de clase**: las 8 letras que identifican a "Química 5to A". Lo muestra el panel docente y `demo_credenciales.txt`.

---

## El día anterior
1. **Probar el zip en Windows** con la lista [`docs/pruebas/windows-v0.6-demo.md`](../pruebas/windows-v0.6-demo.md). Marcar ✅/❌ cada fila. Si algo da ❌, pasárselo a Claude Code ese mismo día.
2. **Copiar a la USB**:
   - `QuimicaDemo_Windows_v0.6-demo.zip` (del Release `v0.6-demo` en GitHub o de `dist/`).
   - La carpeta `docs/presentacion/capturas/` completa (es el respaldo si algo falla).
   - (Opcional, plan C) el instalador de Python 3 de https://www.python.org/downloads/.
3. **Cargar el celular** (para mostrar el panel desde otro dispositivo).
4. **Anotar en papel** lo que dejó `sembrar_demo.bat` en `Servidor\demo_credenciales.txt`:
   - admin: usuario `admin`, contraseña `__________`
   - docente: usuario `docente_demo`, contraseña `__________`
   - código de la clase: `__________`
   (Si se descomprime de nuevo en la PC de la presentación, las contraseñas cambian: anotar las nuevas a T-60.)

## T-60 min (una hora antes)
Hacer **todo** esto antes, para que en vivo no aparezcan los avisos de SmartScreen o del firewall.

1. Encender la PC y conectarla a la red (Wi-Fi o cable) donde va a estar el celular.
2. Copiar el zip al **Escritorio** → clic derecho → *Extraer todo* → Escritorio.
3. Abrir `Escritorio\QuimicaDemo\Servidor\QuimicaServidor.exe`.
   - "Windows protegió su PC" → *Más información* → *Ejecutar de todas formas*.
   - Aviso del firewall → marcar **Redes privadas** → *Permitir*.
   - Anotar la IP que muestra la ventana: `__________`.
4. Doble clic en `Servidor\sembrar_demo.bat`. Anotar la contraseña de `docente_demo` y el código de la clase (también quedan en `Servidor\demo_credenciales.txt`).
5. En el navegador (se abrió solo), dos pestañas:
   - Pestaña 1: entrar como **admin**. Dejarla en **Logs**.
   - Pestaña 2 (pestaña nueva con `Ctrl+T` y escribir `localhost:8000`; cada pestaña guarda su propia sesión): entrar como **docente_demo**. Dejarla en **Mis clases**.
6. Abrir `Juego\QuimicaDemo.exe` **dos veces** y acomodarlas lado a lado.
   - En cada una: IP `127.0.0.1`, puerto `7777` → Conectar.
   - Ventana A: **Crear cuenta** → usuario `eli_demo`, nombre `Eli`, un color.
   - Ventana B: **Crear cuenta** → usuario `fede_demo`, nombre `Fede`, otro color.
   - **No** unirse a la clase todavía: eso se hace en vivo.
   *(Son estudiantes nuevos a propósito: así en vivo se ve cómo se unen con el código y aparece un intento nuevo en el panel. `limpiar_demo.bat` también los borra.)*
7. Abrir `Juego\QuimicaDemo.exe` una **tercera** vez (para el docente espectador). Conectar → pestaña **Docente** → `docente_demo` + contraseña. Dejarla minimizada en la lista de salas.
8. En el celular: abrir `http://<IP>:8000` y comprobar que carga el login del panel.
9. Abrir en otra pestaña del navegador la carpeta de capturas (`docs/presentacion/capturas/`, desde la USB) y dejarla lista.

## T-15 min — checklist de 5 puntos
| | Verificar | ✅ |
|---|---|---|
| 1 | La ventana del servidor está abierta y sin errores en rojo. | |
| 2 | Panel: pestaña admin en Logs y pestaña docente en Mis clases, las dos con sesión iniciada. | |
| 3 | Las 2 ventanas del juego en el Menú principal (Eli y Fede) y la del docente en la lista de salas. | |
| 4 | El celular en la misma red y con el panel cargado. | |
| 5 | Las capturas de respaldo abiertas en una pestaña. | |

## Si algo falla en vivo
| Síntoma | Qué hacer |
|---|---|
| El juego no conecta | ¿Está abierta la ventana del servidor? IP `127.0.0.1` y puerto `7777` en la misma PC. Desde otra PC: la IP de la ventana del servidor y `Servidor\abrir_firewall.bat` (clic derecho → *Ejecutar como administrador*). |
| El celular no abre el panel | Misma red Wi-Fi que la PC. Correr `abrir_firewall.bat` como administrador. Si sigue sin andar: mostrarlo en la PC y seguir. |
| "No existe la clase" al unirse | Revisar el código en el panel docente (Mis clases). Son 8 caracteres, sin O ni 0, sin I ni 1. |
| El reto no aparece en el lobby | El anfitrión tiene que estar inscrito en la clase: Mi perfil → Unirse a clase. Después, **Cambiar reto** en el lobby. |
| El intento nuevo no aparece en el panel | El intento se guarda al **salir de la sala** (Esc → Salir de la sala) o al terminar las 5 salas. Salir y recargar la página del reto. |
| La contraseña del docente no anda | Está en `Servidor\demo_credenciales.txt`. Si no, correr de nuevo `sembrar_demo.bat`: muestra la misma. |
| El `.exe` del servidor está bloqueado o borrado por el antivirus | **Plan C**: instalar Python (marcar *Add python.exe to PATH*) y en `ServidorDedicado\` copiar `.env.example` como `.env` y escribir una contraseña en `ADMIN_PASSWORD`, y abrir `iniciar_servidor_sin_docker.bat` (la primera vez necesita internet para instalar dependencias). Los datos de demo se cargan con `py -3 demo.py sembrar` desde `ServidorDedicado\servidor\` (abrir ahí una terminal: en el explorador, escribir `cmd` en la barra de direcciones y Enter). |
| Se cerró el servidor | Volver a abrir `QuimicaServidor.exe`: los datos siguen (están en `quimica.db`). Las ventanas del juego tienen que volver a conectar. |
| Nada anda | Mostrar las capturas de `docs/presentacion/capturas/` y explicar sobre ellas, siguiendo el mismo guion: `menus/` (login, perfil, lobby con reto), `salas/` (las 5 salas de cada lado), `hud/` (la partida y la pausa) y `panel/` (`docente_resultados.png` es la tabla de errores por concepto). |

## Después
1. (Opcional) `Servidor\limpiar_demo.bat`: borra el docente demo, su clase y su reto, y todos los usuarios `*_demo` (también Eli y Fede). No toca nada más.
2. Cerrar las ventanas del juego y después la ventana del servidor.

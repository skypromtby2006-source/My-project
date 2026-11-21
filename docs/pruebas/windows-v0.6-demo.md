# Prueba manual en Windows — v0.6-demo

> La hace **Jona** en Windows 11, el día anterior a la presentación, con el zip
> `QuimicaDemo_Windows_v0.6-demo.zip` (del GitHub Release `v0.6-demo` o de la USB).
> Marca cada fila con ✅ o ❌. Si algo da ❌, anota qué se vio en "Notas" y pásalo a Claude Code.

Fecha y hora de la prueba: ____________  PC: ____________  IP de la PC: ____________

| # | Qué hacer | Qué tiene que pasar | ✅/❌ | Notas |
|---|---|---|---|---|
| 1 | Copiar el zip al **Escritorio** y descomprimirlo ahí (clic derecho → *Extraer todo*). **No** en Archivos de programa. | Queda la carpeta `Escritorio\QuimicaDemo\` con `Juego\`, `Servidor\`, `ServidorDedicado\` y `LEEME.txt`. | | |
| 2a | Doble clic en `Servidor\QuimicaServidor.exe`. | Si aparece "Windows protegió su PC": *Más información* → *Ejecutar de todas formas*. | | |
| 2b | — | Windows Defender **no** lo bloquea ni lo borra. | | |
| 2c | — | Si aparece el aviso del firewall: marcar **Redes privadas** → *Permitir*. | | |
| 2d | — | La ventana negra muestra el puerto 7777, las IP de la PC y el usuario/contraseña del panel. | | |
| 2e | — | Se abre solo el navegador con el panel (`http://localhost:8000`). | | |
| 3 | Doble clic en `Servidor\sembrar_demo.bat`. | La ventana muestra `docente_demo` con su contraseña y el código de la clase. Se crea `Servidor\demo_credenciales.txt`. **Anotar las credenciales en papel.** | | |
| 3b | Volver a correr `sembrar_demo.bat`. | Muestra la **misma** contraseña y el **mismo** código (no duplica nada). | | |
| 4a | Panel → entrar como **admin** (usuario `admin`, contraseña de la ventana o de `demo_credenciales.txt`). Ir a **Logs**. | Se ven los logs en vivo (aparecen líneas nuevas al hacer algo en el juego). | | |
| 4b | Admin → **Docentes** → crear un docente nuevo (por ejemplo `profe_prueba`, contraseña de 8+ caracteres). | Aparece en la lista. Se puede entrar con él en otra pestaña. | | |
| 5 | En otra pestaña (o ventana privada), panel → entrar como **docente_demo**. | En **Mis clases**: "Química 5to A", su código de 8 letras y 4 inscritos. En **Retos** → el reto → la tabla con los 6 intentos y los errores por concepto (balanceo, mol, masa, limitante, rendimiento). | | |
| 6a | Abrir `Juego\QuimicaDemo.exe` **dos veces**. En cada una: IP `127.0.0.1`, puerto `7777` → Conectar. | Las dos ventanas llegan a la pantalla de inicio de sesión. | | |
| 6b | Ventana A: iniciar sesión como `ana_demo`. Ventana B: `beto_demo`. (Pestaña Estudiante, sin contraseña.) | Las dos llegan al Menú principal. | | |
| 6c | En las dos: **Mi perfil** → *Mis clases* → escribir el código de la clase → **Unirse a clase**. | Aparece "Química 5to A" en Mis clases (ya estaban inscritos por el sembrado: no da error). | | |
| 6d | A: Jugar → **Crear sala** → **Cambiar reto** hasta que aparezca el reto de "Química 5to A". B: elegir la sala de la lista → **Estoy listo**. A: **Iniciar partida**. | Los dos entran al laberinto (A = Wizard, B = Player). | | |
| 6e | Jugar la **Sala 1** completa (poner a propósito un valor incorrecto una vez). Bajar las dos palancas a la vez. | Se abre la puerta de la Sala 1. El valor incorrecto muestra el aviso de error. | | |
| 7 | En las dos ventanas: Esc → **Salir de la sala**. Panel docente → Retos → el reto (recargar). | Aparecen 2 intentos nuevos (Ana y Beto), "No" en Completado, con el error en la columna **balanceo**. *El intento se guarda al salir de la sala o al terminar las 5 salas, no a mitad de partida.* | | |
| 8 | Volver a armar la sala con A y B y empezar otra partida. Abrir una **tercera** ventana del juego → pestaña **Docente** → `docente_demo` + contraseña → en la lista de salas, **Mirar** en la sala de Ana. | El docente ve la partida con cámara libre y no ocupa un lugar (la sala sigue con 2 jugadores). Esc lo devuelve a la lista. | | |
| 9 | Cerrar la ventana del servidor. Volver a abrir `QuimicaServidor.exe`. Panel docente. | Siguen la clase, los estudiantes y todos los intentos (incluidos los de la prueba 7). | | |
| 10 | **Desde otra PC o el celular** en la misma red Wi-Fi: abrir `http://<IP de la PC>:8000`. | Se ve el login del panel y se puede entrar como docente. Si no carga: `Servidor\abrir_firewall.bat` con clic derecho → *Ejecutar como administrador* y probar de nuevo. | | |
| 11 | (Solo si esa PC tiene Docker Desktop) Cerrar `QuimicaServidor.exe`. En `ServidorDedicado\`: copiar `.env.example` como `.env`, poner una contraseña en `ADMIN_PASSWORD`, doble clic en `instalar_servidor.bat`. Después `sembrar_demo_docker.bat`, y repetir 3–7. Luego `abrir_pgadmin.bat`. | Todo igual que con el `.exe`, pero con PostgreSQL. pgAdmin (`http://127.0.0.1:5050`) muestra las tablas `docentes`, `clases`, `retos`, `intentos`, etc. | | |

## Si algo falla
- Anotar el número de la fila, qué se vio y la hora.
- La ventana del servidor y la página **Logs** del panel (admin) muestran qué pasó a esa hora.
- Pasarle todo a Claude Code junto con este archivo.

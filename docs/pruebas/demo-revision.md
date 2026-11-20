# Guion de la demo — Revisión con el docente (20/11/2026)

> Flujo completo del **rol docente**: el admin crea un docente → el docente crea una clase y un reto → dos estudiantes se unen con el código y juegan → el docente ve los resultados y los logs. Al final, opcional: el docente mira una partida desde el juego como espectador.
> Se hace en **una sola PC** con el panel en el navegador y 2 juegos (build de Linux). Dura unos 10 minutos.
> La parte automática ya está probada: `scripts/probar_build.sh reto` (el juego real) y `servidor/tests` (pytest). Este guion es para **verlo con los ojos y los clics**.

## Datos de ejemplo

| Quién | Dónde entra | Usuario | Contraseña / dato |
|---|---|---|---|
| Admin | Panel web | `admin` | la de `ADMIN_PASSWORD` en el `.env` de la raíz del repo |
| Docente | Panel web | `profe_ana` | `quimica2026` (nombre visible: **Profe Ana**) |
| Estudiante A (anfitrión, 🧙 Wizard) | Juego 1 | `ana_lopez` | nombre visible **Ana** (los estudiantes no usan contraseña) |
| Estudiante B (🧑‍🔬 Player) | Juego 2 | `beto_ruiz` | nombre visible **Beto** |

Si alguno de esos usuarios ya existe de una demo anterior, usar otro (por ejemplo `profe_ana2`, `ana_lopez2`): el panel avisa "ya existe".

## Preparación (una sola vez, 3 minutos)
1. En una terminal, en la carpeta del repo: `scripts/servidor_iniciar.sh`. Espera hasta que diga **"Servidor en el puerto 7777"**.
2. Abrir **http://localhost:8000** en el navegador. Debe verse la pantalla de inicio de sesión del panel.
3. En otra terminal: `scripts/jugar_linux.sh 2`. Se abren **2 ventanas del juego**. Ponerlas una al lado de la otra.

## Pasos

### Parte 1 — El admin crea al docente
| # | Qué hacer | Qué se tiene que ver |
|---|---|---|
| 1 | En el panel, entrar con usuario `admin` y la contraseña del `.env` | Se abre **Estado**. En el menú de la izquierda está la página **🎓 Docentes** |
| 2 | Abrir **🎓 Docentes**. Completar: usuario `profe_ana`, nombre visible `Profe Ana`, contraseña `quimica2026`. Clic en **Crear docente** | Aparece la fila de `profe_ana` en la tabla, con estado **Activo** y 0 clases |
| 3 | Cerrar sesión del admin (abajo a la izquierda) | Vuelve la pantalla de inicio de sesión |

### Parte 2 — El docente crea una clase y un reto
| # | Qué hacer | Qué se tiene que ver |
|---|---|---|
| 4 | Entrar al panel con `profe_ana` / `quimica2026` | Se abre **🏫 Mis clases**. El menú del docente tiene solo: Mis clases, Retos, Partidas en vivo y Logs (no ve Usuarios, Auditoría ni Docentes) |
| 5 | Escribir el nombre `Química 3°A` y clic en **Crear clase** | Sale "Clase creada. Código para los estudiantes: **XXXXXXXX**" (8 letras y números). **Anotar el código** |
| 6 | Abrir **🎯 Retos**. Elegir la clase `Química 3°A`, dejar la semilla vacía, grupo `2`, tiempo límite `10` minutos. Clic en **Crear reto** | Aparece el reto en la tabla: nivel `laberinto_01`, una semilla (número), grupo 2, tiempo límite 10 min, estado **Abierto**, 0 jugaron |

### Parte 3 — Dos estudiantes se unen y juegan
| # | Qué hacer | Qué se tiene que ver |
|---|---|---|
| 7 | **Juego 1:** IP `127.0.0.1`, conectar. **Crear cuenta** con usuario `ana_lopez`, nombre `Ana`, cualquier color | Se abre el **Menú principal** |
| 8 | **Juego 1:** **Mi perfil** → en **Código** escribir el código del paso 5 → **Unirse a clase** | En **Mis clases** del perfil aparece `Química 3°A` |
| 9 | **Juego 2:** lo mismo con usuario `beto_ruiz`, nombre `Beto`, y el mismo código | En su perfil también aparece `Química 3°A` |
| 10 | **Panel (docente):** en **🏫 Mis clases**, clic en **Inscritos** de la clase | Aparecen `ana_lopez` y `beto_ruiz` |
| 11 | **Juego 1:** volver al menú → **Ver salas** → **Crear sala** | Se abre la sala; Ana es 🧙 Wizard (anfitriona). Abajo dice **"Sin reto: partida libre"** |
| 12 | **Juego 1:** clic en **Cambiar reto** | Cambia a **"Reto: Química 3°A · reto N · grupos de hasta 2"** |
| 13 | **Juego 2:** **Ver salas** → unirse a la sala de Ana → **Estoy listo** | Beto aparece como 🧑‍🔬 Player y listo en las dos ventanas |
| 14 | **Juego 1:** **Iniciar partida** | Las dos ventanas entran al laberinto. En el HUD se ve el **reloj del reto** contando hacia atrás desde 10:00 |
| 15 | **Panel (docente):** abrir **🧪 Partidas en vivo** | Aparece la sala con Ana y Beto, el tiempo y los errores, actualizándose sola cada pocos segundos |
| 16 | Jugar 1–2 minutos (mover a Beto, interactuar con algo de la primera sala). Después, salir de la partida con **Esc**: primero Beto (Juego 2), después Ana (Juego 1) | Los dos vuelven a la lista de salas |

### Parte 4 — El docente ve los resultados y los logs
| # | Qué hacer | Qué se tiene que ver |
|---|---|---|
| 17 | **Panel (docente):** **🎯 Retos** → **Resultados** del reto | Una fila por estudiante (**Ana y Beto**, el Wizard también cuenta): sala, tiempo, errores, **Completado ✘ No** (salieron a medias) y fecha. En la tabla de retos, "Jugaron" pasa a 2 |
| 18 | **🏫 Mis clases** → **Inscritos** → clic en `beto_ruiz` | La página del estudiante con sus intentos en todos los retos de la clase |
| 19 | Abrir **📜 Logs** | Solo líneas de **sus** estudiantes (`ana_lopez`, `beto_ruiz`), su conexión o su sala: entrada al juego, unirse a la clase, crear sala, inicio de la partida. Escribir `beto` en **Buscar texto…** filtra |
| 20 | (Opcional, seguridad) Cerrar sesión y entrar como `admin` → **🎓 Docentes** → **Desactivar** a `profe_ana`. Intentar entrar como `profe_ana` | No deja entrar. Con **Activar** vuelve a entrar |

### Parte 5 (opcional) — El docente mira una partida desde el juego
| # | Qué hacer | Qué se tiene que ver |
|---|---|---|
| 21 | Con Ana y Beto jugando de nuevo (pasos 11 a 14), abrir un **tercer juego**: `Build/Linux/QuimicaDemo.x86_64 &` | Se abre otra ventana del juego en el Login |
| 22 | **Juego 3:** pestaña **Docente** → usuario `profe_ana`, contraseña `quimica2026` → **Entrar como espectador** | Va directo a la lista de salas. La sala de Ana sale "En partida" y el botón dice **Mirar** |
| 23 | **Juego 3:** **Mirar** | Entra al laberinto con la cámara libre (arriba dice "Espectador · WASD y mouse…"). Ve moverse a Ana y Beto. Con Q/E sube y baja; atraviesa paredes |
| 24 | **Juegos 1 y 2:** seguir jugando | Nada cambia para ellos: el docente no aparece, no ocupa lugar en la sala y no puede tocar nada |
| 25 | **Juego 3:** **Esc** | Vuelve a la lista de salas; la partida de Ana y Beto sigue |

**Si se quiere mostrar un intento completado:** en el paso 16, en vez de salir, terminar el laberinto (abrir el portón final). En Resultados ese intento sale **✔ Sí** con el tiempo total.

## Si algo falla
- El juego dice "No se pudo conectar": falta el paso 1 de la preparación (`scripts/servidor_iniciar.sh`).
- **Cambiar reto** no aparece o solo dice "Sin reto": el anfitrión (Juego 1) no se unió a la clase (paso 8) o el reto está **Cerrado**.
- "El reto es para grupos de hasta 2 jugadores": hay 3 o más en la sala.
- Para ver qué pasó: `scripts/servidor_logs.sh`, o la página **Logs** del admin (ve todo).

## Resultado
| Fecha | Build (commit) | Quién | Resultado | Notas |
|---|---|---|---|---|
| | | | | |

# Informe de estado — Juego de Química VR

> Fecha: 27/10/2026 · Rama actual: `sprint-1` (sincronizada con `origin/sprint-1`) · Último commit: `aef8b05`

## 1. Resumen

| | Estado |
|---|---|
| **Sprint 0** — Demo multijugador (v0.1) | ✅ Cerrado. En `main`, con el tag `v0.1-demo` |
| **Sprint 1** — Roles Wizard/Player + misión (v0.2) | 🟡 Implementado y probado en Linux. **Falta la prueba en Windows 11** para hacer el merge a `main` |
| **Sprint 2** — Perfiles + progreso (v0.3) | ⚪ No iniciado. El brief (`SPRINT2.md`) existe pero no está en git |

## 2. Qué hace el sistema hoy (v0.2)

Es un juego cooperativo asimétrico en red local:

- Un servidor Python con asyncio sobre TCP (puerto **7777**) atiende a todos los jugadores. Es **autoritativo**: valida cada acción.
- El cliente es Unity 6.3 LTS (URP) y se compila para Windows y Linux.
- Cada jugador se conecta por IP. Uno crea una sala (con un código de 4 letras) y los demás se unen desde la lista o con el código. Cada uno marca "Listo" y el anfitrión inicia la partida.
- **Wizard (el anfitrión):** ve los símbolos y la receta, señala objetos con clic y puede reiniciar la misión.
- **Players:** agarran y sueltan esferas con E, pero solo ven "?".
- **Misión "Sintetizar agua":** hay que llevar 2 H + 1 O al reactor. Si entra un elemento equivocado, vuelve a la mesa y se cuenta un error.
- Los eventos se guardan en PostgreSQL 16 (conexiones, salas, partidas, `reaccion_fallida`, `mision_completada`). Si la BD se cae, el servidor sigue funcionando en memoria.
- Todo se levanta con Docker Compose. pgAdmin es opcional (perfil `admin`, `127.0.0.1:5050`).

## 3. Componentes

| Componente | Ubicación | Tamaño |
|---|---|---|
| Servidor | `servidor/server.py` | 484 líneas |
| Test sin Unity (2 jugadores simulados) | `servidor/probar_cliente.py` | — |
| Red del cliente (socket en un hilo aparte) | `QuimicaVR/Assets/Scripts/Red/ClienteRed.cs` | 231 líneas |
| Menú IMGUI (conexión, salas, Listo) | `QuimicaVR/Assets/Scripts/Red/MenuLobby.cs` | 247 líneas |
| Partida (escenario, roles, sincronización a 15 Hz) | `QuimicaVR/Assets/Scripts/Red/GestorPartida.cs` | 360 líneas |
| Generación de la escena | `QuimicaVR/Assets/Editor/ConfigurarDemo.cs` | 127 líneas |
| Builds Linux/Windows | `QuimicaVR/Assets/Editor/Construir.cs` | 55 líneas |
| Scripts de desarrollo | `scripts/*.sh` | 10 scripts |
| Entrega para Windows | `entrega/LEEME.txt` y `entrega/windows/*.bat` | 6 `.bat` |
| Documentación | `docs/protocolo.md`, `docs/decisiones.md`, `docs/backlog.md` y `docs/reportes/` | 8 reportes |

## 4. Historial

| Hito | Contenido |
|---|---|
| Sprint 0, fases 1-4 | Servidor y Docker, proyecto Unity, builds y paquete v0.1. Tag `v0.1-demo` |
| S1-1 | Roles y misión en el servidor (`5033e10`) |
| S1-2 | Cliente Unity con roles y escenario dictado por el servidor (`85cfcba`) |
| S1-3 | Corrección del JSON roto en `pos`/`soltar` por cultura numérica, receta legible y etiquetas (`e318bf7`). Aprobada por el cliente en editor y en el build de Linux |
| S1-4 | Build de Windows (Succeeded) y paquete v0.2 con LEEME de roles y controles (`c436a48`) |

En `main..sprint-1` hay 12 commits pendientes de merge.

## 5. Pendientes y bloqueos

1. **🧑 Prueba de la v0.2 en Windows 11 (bloqueante).** Docker Desktop → `instalar_servidor.bat` → abrir `QuimicaDemo.exe` dos veces → recorrer la misión completa. Hay que revisar que la flecha `→` de la receta se vea bien con la fuente de Windows.
2. **🤖 Después de aprobarla:** merge de `sprint-1` a `main`, tag `v0.2-demo`, push con tags y crear la rama `sprint-2` desde `main`.
3. **Sprint 2** (perfiles sin contraseña, edición de perfil y progreso por misiones): fases S2-1 a S2-4 sin empezar.

## 6. Hallazgos al revisar el directorio

- ✅ ~~Faltaba el zip de la v0.2 en `dist/`.~~ Regenerado el 27/10 con `scripts/empaquetar.sh v0.2` (38 MB). Sin `DoNotShip` y con los 6 `.bat` y el LEEME de la v0.2.
- ✅ ~~`CLAUDE.md` tenía cambios locales que desmarcaban casillas.~~ Restaurado con `git restore` (el PM confirmó que no fue intencional).
- `SPRINT2.md` no está versionado. Según su propio plan, debería entrar en la rama `sprint-2`, no en `sprint-1`.
- `Build/Windows/` contiene `QuimicaDemo_BurstDebugInformation_DoNotShip`. El reporte S1-4 confirma que el empaquetado lo excluye.

## 7. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Sin aprobación en Windows antes del corte | Se entregaría la v0.1 | Priorizar la prueba de Windows antes de empezar el Sprint 2 |
| `v0.1-demo` tiene el bug del JSON en `pos`, corregido en la v0.2 (`e318bf7`). **No es de cultura**: la v0.1 ya usaba `InvariantCulture` (`ClienteRed.cs:100`). En el Mono de Unity, `string.Format("...{3:F1}}}")` escribe `"ry":F1}`. El bug está desde `e756de0` (Fase 2, código de `_base/`), no nació en la S1-2 | Con la v0.1, los jugadores no se ven moverse **en cualquier sistema**, no solo en Windows en español | Entregar la v0.2, o aplicar un hotfix sobre la v0.1 si lo decide el PM |
| Docker Desktop roto en la PC Windows de prueba (`exec format error` en todos los contenedores) | **Riesgo del entorno, no del proyecto.** El servidor no arranca con `instalar_servidor.bat` en esa PC | Plan B2: correr el servidor directo con Python. Anotado en `docs/backlog.md` |
| El servidor envía el `elemento` a todos los clientes | Un cliente modificado podría hacer trampa | En el backlog (anti-trampas) |
| La distancia para agarrar solo la valida el cliente | Trampas | En el backlog |
| La receta está en constantes de `server.py` | Agregar misiones cuesta más | En el backlog (pasar las recetas a datos) |

## 8. Backlog registrado

Voz integrada · más misiones o recetas · anti-trampas (no enviar `elemento` a los players) · validar la distancia de agarre en el servidor · VR y física real · login y perfiles (Sprint 2) · roles de estudiante, docente y admin · servidor dedicado · UI definitiva · instalador con Inno Setup.

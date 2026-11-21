# SPRINT_UI.md — Interfaz del juego según el diseño de Claude Design

> Brief del PM para Claude Code. Siguen vigentes **todas** las reglas de `CLAUDE.md`.
> Referencia visual: carpeta `MDs/diseno_ui/` (5 pantallas exportadas del canvas "Pantallas principales — Juego de Química VR", en HTML + CSS a 1280×720).
> Rama: `ui-diseno`, creada desde la rama donde esté el Sprint 4 más avanzado. **No toca la jugabilidad del laberinto.**

## 0. Regla principal: el diseño se adapta al juego, no el juego al diseño
El diseño se hizo en octubre, antes de varias decisiones. Muestra funciones que **no existen** (contraseña, PvP, equipos, sincronización con la nube). **Este sprint no agrega funciones de juego**: se toma el **estilo visual** y la **estructura** de cada pantalla, y se rellenan con lo que el juego ya hace.
**Por qué:** si se implementaran todas las funciones que dibuja el diseño, esto se volvería un sprint de tres semanas.

## 1. Sistema visual (tokens del diseño)
| Token | Valor | Uso |
|---|---|---|
| Fondo | `#0e0a1f` | Fondo de pantalla e inputs |
| Tarjeta | `#1a1433`, borde `#3a2d6b`, radio 16 | Paneles |
| Tarjeta interna | `#241b45` | Subpaneles |
| Primario | `#7c3aed` (texto blanco) | Botón principal |
| Primario borde/acento | `#8b5cf6` · marca `#a78bfa` | Tarjeta destacada, logo "QUÍMICA VR" |
| Secundario | `#2a2050`, borde `#4a3a8a` | Botones secundarios, chips |
| Texto | `#f3efff` · secundario `#b8aedd` | |
| Chip OK | fondo `#123b36`, texto `#5eead4` | Listo, conectado |
| Chip aviso | fondo `#3a2d12`, texto `#fbbf24` | No listo, avisos |
| Chip host | fondo `#3b2a7a`, texto `#d8ccff` | Anfitrión / Wizard |
| Separador de filas | `#2e2457` | Listas |
| Tipografía | **Manrope** 400/600/800 | Títulos 40–60 px, cuerpo 18–20 px, etiquetas 15 px |
| Controles | Altura 52 px (44 px los chicos), radio 12 | Botones e inputs |

- Manrope tiene licencia **SIL OFL** (libre). Va en `Assets/Fonts/` y se registra en `docs/licencias.md`. **Por qué:** además reemplaza a la fuente actual, que no dibujaba "_" (bug B6 de la S2-3). Hay que verificar que tenga "_", tildes, "ñ" y "→". Para "₂" se puede usar como fallback **Noto Sans**, también con licencia OFL.

## 2. Tecnología: UI Toolkit
Se reemplaza el menú IMGUI (`OnGUI`) por **UI Toolkit**: un UXML por pantalla, un USS compartido con los tokens de §1, y `PanelSettings` con *Scale With Screen Size* y referencia de **1280×720**.
**Por qué UI Toolkit y no Canvas (uGUI):** el diseño está en HTML + CSS. UI Toolkit usa **USS (casi CSS)** y **flexbox**, así que la traducción es prácticamente 1:1: las mismas clases (`.btn`, `.card`, `.chip`, `.inp`, `.row`), los mismos colores y los mismos `gap`. Con uGUI habría que reconstruir cada pantalla a mano con anclajes.
- **La lógica se separa de la vista:** cada pantalla tiene un controlador C# que solo conecta botones con los métodos que ya existen en `ClienteRed`. La red no cambia.
- **Pensando en VR:** verifica si Unity 6.3 soporta **paneles de UI Toolkit en world space** y deja la conclusión en `docs/decisiones.md`. En VR los menús tienen que flotar en el mundo, no pegados a la pantalla. Si no lo soporta, se documenta cuál sería el plan para la fase de VR. No se implementa ahora.

## 3. Pantallas (diseño → juego real)

| Pantalla del diseño | Qué se toma | Qué cambia para que coincida con el juego |
|---|---|---|
| **Entrar · Login** (`Main.dc.html`) | Layout de dos columnas: lema a la izquierda, tarjeta a la derecha. Pestañas Entrar / Crear cuenta | **Sin contraseña** (el login es solo con usuario). El campo "Servidor" pasa a **IP + puerto** (la pantalla de Conexión actual se une con esta). *Crear cuenta* agrega **nombre visible** y el **selector de 8 colores**. Abajo a la izquierda, el estado real: "Servidor 192.168.x.x · conectado" o el error en un chip de aviso. Validación: usuario de 4 a 16 caracteres |
| **Menú principal** (`Menu.dc.html`) | Las 3 tarjetas, con Multijugador destacado. Fila de abajo: Perfil · Ajustes · Cerrar sesión | Historia y Laboratorio quedan **"Próxima fase", deshabilitadas** (coincide con los 3 pilares del proyecto). El chip superior muestra **nombre + color del perfil**. Sin el chip de "progreso sincronizado" |
| **Multijugador · Salas** (`Salas.dc.html`) | Lista de salas a la izquierda, "Crear sala" a la derecha, unirse con código | Código de **4** caracteres (no 5). Crear sala: **nombre + máximo de jugadores**. *Modo* queda fijo en Cooperativo (PvP desactivado y marcado "próximamente"). **Sin contraseña de sala.** La lista se actualiza sola cada 2 s, y además está el botón Actualizar |
| **Lobby de sala** (`Lobby.dc.html`) | Código grande arriba a la derecha, dos columnas de jugadores, aviso de estado, barra de acciones | **"Equipo A / Equipo B" pasa a "Lado Wizard / Lado Player"**, que coincide con el laberinto separado por paredes. El anfitrión aparece en Lado Wizard con el chip *Host*. Sin "Cambiar de equipo" ni "Expulsar" (al backlog 🟢). **Iniciar partida** se habilita solo con ≥ 2 jugadores y todos listos; si no, el chip de aviso dice qué falta. El avatar es un círculo con la inicial **en el color del perfil** |
| **Conflicto de progreso** (`Conflicto.dc.html`) | — | **No se implementa:** la sincronización con la nube estilo Steam Cloud todavía no existe. Queda en el backlog, y el diseño ya está listo para cuando se haga |

### Pantallas que no están en el diseño (se hacen con el mismo estilo)
- **Mi perfil:** tarjeta con usuario (no editable), nombre visible, selector de color, Guardar / Volver. Al lado, otra tarjeta **Progreso**: niveles completados, mejor tiempo, "Errores cometidos (todas las partidas)" e historial de los últimos 5.
- **Pausa** (ESC en partida): tarjeta centrada con *Continuar*, *Sensibilidad del mouse* (slider), *Salir de la sala*.
- **Avisos globales y motivos de expulsión o cierre de sala:** banner arriba con el estilo de chip de aviso.
- **HUD en partida:** mira, texto contextual ("E: girar dial"), sala actual, rol, mensaje central de la sala. Se aplican los mismos tokens (texto `#f3efff` sobre una tarjeta translúcida). El HUD no debe tapar la vista: ocupa como máximo ~25% de la pantalla.

## 4. Fases
- **UI-1:** USS con los tokens + fuente Manrope (verificar caracteres) + Login + Menú. Compila sin `error CS`.
- **UI-2:** Salas + Lobby + Mi perfil.
- **UI-3:** Pausa, avisos, HUD. Eliminar el código IMGUI viejo de `MenuLobby.cs` (que no quede menú duplicado).
- **UI-4:** `probar_build.sh` adaptado a los nuevos botones (todos los escenarios en verde) + **capturas de cada pantalla a 1280×720** en `docs/capturas/ui/`, para que el cliente las compare con el diseño. Build de Linux y reporte.

## 5. Criterio de terminado
- Las 5 pantallas del juego (Login, Menú, Salas, Lobby, Mi perfil) **se parecen al diseño**: el cliente lo aprueba comparando las capturas.
- `probar_build.sh` (todos los escenarios) y `pytest` en verde: el juego no se rompió.
- Ningún texto cortado ni caracteres faltantes ("_", tildes, ñ, →).
- Se ve bien a **1280×720 y a 1920×1080** (por el escalado).

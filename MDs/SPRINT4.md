# SPRINT4.md — Laberinto de las 5 puertas (primera persona)

> Brief del PM para Claude Code. Siguen vigentes **todas** las reglas de `CLAUDE.md`.
> **Entrega: lunes 16/11/2026.** Corte: **domingo 15/11 a las 20:00** → `v0.5-demo`. Si no se llega, se presenta la `v0.4-demo`.
> Rama: `sprint-4`, creada desde `main` con la v0.4 ya mergeada.

## 0. Calendario
| Día | Fase | Quién |
|---|---|---|
| Lun 09 | Fix del log de bytes basura (ver §6) · crear la rama · 🧑 descargar assets (§4) | 🤖 + 🧑 |
| Mar 10 | **S4-1** Servidor: nivel como datos, 5 puzzles, protocolo, tests | 🤖 |
| Mié 11 | **S4-2** Cliente: primera persona + generador de nivel con **cubos grises (greybox)** | 🤖 |
| Jue 12 | **S4-3** Prueba de jugabilidad en greybox | 🧑 → 🤖 correcciones |
| Vie 13–Sáb 14 | **S4-4** Arte: assets, iluminación y ambientación por sala | 🤖 + 🧑 revisión visual |
| Dom 15 | **S4-5** Prueba integral, estadísticas por concepto en el panel, build, tag | 🧑 + 🤖 |
| Lun 16 | 🎤 Presentación | |

**Regla de oro: primero se juega con cubos grises y recién después llegan los assets.**
**Por qué:** si un puzzle es aburrido o confuso, se descubre el jueves y se corrige en minutos. Si se descubre el domingo con el arte ya puesto, es tarde. Así trabajan los estudios de videojuegos: el *greybox* valida el diseño antes de invertir en arte.

## 1. Concepto (decisiones del cliente)

Cooperativo estilo *We Were Here Together*. Los dos jugadores, en **primera persona**, recorren **mitades separadas** de un laberinto por un muro central. Se ven por rejas y ventanas, pero nunca pueden cruzar al otro lado.

- **Roles:** se mantienen. El anfitrión es el **Wizard** (lado izquierdo) y el que se une es el **Player** (lado derecho). En una sala de más de 2 jugadores, los Players extra van al lado derecho.
- **Información repartida:** en cada sala, **cada lado tiene una parte de la receta**. Nadie puede resolver solo.
- **Los dos tienen algo que hacer:** cada lado tiene su propia tarea física (girar diales, cargar elementos, mover válvulas, pesar en la balanza). Nadie se queda solo leyendo.
- **Apertura conjunta:** cada puerta tiene **una palanca en cada lado**. Se abre solo si los dos lados dejaron su parte correcta **y** bajan su palanca con menos de **2 segundos** de diferencia. Si lo hace uno solo, la puerta no se abre.
- **Encadenamiento:** el producto de cada sala **sale por un montacargas y se usa en la siguiente**. Lo que fabricaste antes te sirve después.
- **Montacargas:** cada sala tiene una ventanilla en el muro central para **pasarse objetos** de un lado al otro.
- **Más estequiometría:** la dificultad sube de concepto en concepto, sala por sala (§2).

## 2. Las 5 salas
Los números **los sortea el servidor en cada partida** (dentro de rangos que den resultados enteros). **Por qué:** así no se pueden memorizar las respuestas. Además, cada error queda registrado con su **concepto** (§3.4).

| # | Sala (ambientación) | Reacción | Concepto | Lado Wizard tiene… | Lado Player tiene… | Produce → siguiente sala |
|---|---|---|---|---|---|---|
| 1 | **El Pozo** (mazmorra azul, antorchas) | `_H₂ + _O₂ → _H₂O` | **Balanceo** de coeficientes | Diales de los reactivos · tanques de H₂ | Dial del producto · tanques de O₂ · cuántas moléculas de H₂O pide la puerta | **Agua** (n mol) |
| 2 | **Puente de cadenas** (puentes sobre ácido verde) | `2Na + 2H₂O → 2NaOH + H₂` | Relación **mol a mol** | Cristales de Na (elige cuántos) | El agua de la sala 1 (llega por el montacargas) y la tabla de proporciones | **NaOH** y **H₂** |
| 3 | **Laboratorio de tanques** (tanques verdes, vapor) | `NaOH + HCl → NaCl + H₂O` | **Masa a masa** (gramos y masa molar) | **Tabla de masas molares** · balanza | El tanque de HCl indica sus **gramos** · válvula de NaOH | **NaCl** (llave de sal) |
| 4 | **Reactor de Haber** (sala de máquinas, rojo) | `N₂ + 3H₂ → 2NH₃` | **Reactivo limitante** | El H₂ que llegó de la sala 2 (cantidad limitada) | N₂ en abundancia · un dial con "¿cuántos mol de NH₃ salen?" | **NH₃** (combustible del portón) |
| 5 | **El Portón final** (cripta, calavera de cristal) | `4NH₃ + 3O₂ → 2N₂ + 6H₂O` | **Rendimiento porcentual** | Masa teórica de N₂ (tiene que calcularla) y entra el **rendimiento %** | Masa real de N₂ que muestra el horno | **Fin del nivel** |

Cada fila es una progresión: balanceo → mol → masa → limitante → rendimiento. Es el orden en que se enseña estequiometría en secundaria. El docente lo puede citar en la justificación pedagógica.

Si el diseño concreto de alguna tarea física no cierra con los números, Claude Code **propone un ajuste en el reporte** en lugar de inventarlo en silencio. El cliente decide.

> **Decisiones del PM sobre S4-1 (09/11):** (1) `n` (mol de agua base) se sortea en `{6, 12, 18, 24, 30, 36}` para que las 5 salas den enteros a la vez. (2) Masas molares reales (Cl = 35,5); la balanza de la Sala 3 muestra 1 decimal. (3) La Sala 5 pasa a la **combustión del amoníaco** (`4NH₃ + 3O₂ → 2N₂ + 6H₂O`): el NH₃ de la Sala 4 es su reactivo real, así el encadenamiento cierra químicamente (Opción B del reporte S4-1).

## 3. Diseño técnico

### 3.1 El nivel es un dato (el servidor sigue siendo la fuente de verdad)
`servidor/niveles/laberinto_01.json` contiene:
- Una grilla en **texto** por cada lado (ej. `#` pared, `.` piso, `D` puerta, `M` montacargas, `P` palanca, `C` consola, `S` aparición, `|` muro central con reja).
- Las salas con su puzzle (tipo, rangos para el sorteo y la posición de cada consola u objeto).

El servidor lo carga, sortea los números y lo envía en `inicio`. El cliente **construye el nivel a partir de ese dato** (`GeneradorNivel.cs`) con piezas modulares.
**Por qué:** se mantiene la regla del Sprint 1 (las posiciones viven en un solo lugar), Claude Code puede construir y testear el nivel sin ver la pantalla, y un nivel nuevo es otro JSON.

### 3.2 Servidor
- Valida todo: diales, cargas, montacargas, palancas (ventana de 2 s) y estado de las puertas. El cliente solo envía intenciones.
- Protocolo nuevo (documentar en `docs/protocolo.md`):
  `interactuar {obj, accion}` · `dial {consola, valor}` · `montacargas {obj}` · `palanca {puerta}` · respuesta `sala_estado {sala, puertas, objetos, mensaje}`.
- `pos` agrega `pitch` (la inclinación de la cabeza), para que se vea hacia dónde mira el otro jugador.
- La misión "Sintetizar agua" del Sprint 1 **se retira**: la Sala 1 la reemplaza. Hay que actualizar los tests.

### 3.3 Cliente en primera persona
- `CharacterController` + vista con el mouse (cursor bloqueado; **ESC** lo libera y abre la pausa), **WASD**, **E** para interactuar mediante un raycast desde el centro de la pantalla, con una mira (`+`) y un texto contextual ("E: girar dial").
- Sensibilidad del mouse ajustable en la pausa.
- **Preparado para VR:** separa *qué se quiere hacer* (`IInteractor`: apuntar y activar) de *cómo se ingresa* (`EntradaTeclado`). **Por qué:** en la fase de VR solo se agrega `EntradaXR` y el resto del código queda igual. Con esto ya se avanza hacia el aporte ingenieril del perfil.
- Al otro jugador se lo ve como una cápsula con el color de su perfil, el nombre encima y una "cabeza" que gira con su `pitch`.

### 3.4 Datos para la investigación
- Evento `error_estequiometria {sala, concepto, esperado, recibido, usuario}` y evento `sala_completada {sala, segundos, errores}`.
- Progreso del perfil: **nivel completado**, mejor tiempo y tiempo por sala.
- Panel → Estadísticas: **errores por concepto** (balanceo / mol / masa / limitante / rendimiento) y tiempo promedio por sala, calculados con pandas.
  **Por qué:** muestra en qué concepto se traban más los estudiantes. Es exactamente el análisis que promete el perfil de investigación.

## 4. Arte y ambientación
**Referencias del cliente:** mazmorra modular low-poly (estilo *Simple Dungeons*), puentes de cadenas sobre ácido verde y laboratorio de alquimia con tanques verdes. Esto define la paleta: **piedra oscura + luz de antorchas cálida + verde tóxico** como acento químico.

- 🧑 **Assets: usar packs CC0**, que son gratuitos y se pueden usar sin pedir permiso:
  - **KayKit – Dungeon Remastered** (Kay Lousberg, itch.io), que tiene un estilo muy parecido a la referencia.
  - Complementos: **Quaternius** (props) y **Poly Haven** (texturas).
  - Jona los descarga y los copia en `QuimicaVR/Assets/ThirdParty/<pack>/`. Claude Code crea `docs/licencias.md` con el pack, el autor, la licencia y el enlace.
  - *Simple Dungeons* (Synty) es **de pago**. Solo se usa si Jona lo compra, y en ese caso se documenta la licencia igual.
  **Por qué:** en un proyecto académico, usar assets con licencia dudosa es una observación fácil del evaluador. Con CC0 no hay discusión posible.
- Cada sala tiene su propia luz, como en las referencias: azul (1), verde ácido (2 y 3), rojo de máquinas (4) y cripta dorada (5).
- URP: niebla, *bloom* suave, luces puntuales en antorchas y tanques. **Sin** sombras en tiempo real en todas las luces.
  **Por qué:** en VR el juego tiene que correr a 72–90 FPS. Si el arte es pesado desde ahora, después habrá que rehacerlo.
- Elementos químicos como objetos reconocibles: tanques, cristales y frascos con el símbolo grabado, del lado que corresponde.

## 5. Prioridades (si falta tiempo se corta de abajo hacia arriba)
| Nivel | Qué |
|---|---|
| 🔴 | Primera persona · nivel desde JSON · las 5 salas jugables en greybox con apertura conjunta, montacargas y encadenamiento · validación en el servidor · `error_estequiometria` |
| 🟡 | Assets + iluminación por sala · estadísticas por concepto en el panel · pausa con sensibilidad |
| 🟢 | Sonido (puertas, cadenas, burbujeo) · animación de las puertas · pitch visible en el otro jugador |

## 6. Pendiente de antes (lunes 09)
- `server.py` ~800: atrapar `UnicodeDecodeError`/`ValueError` además de `JSONDecodeError`. Registrar `WARNING` "Datos no válidos desde <ip>" y cerrar esa conexión. Test con bytes binarios. Commit `fix:`.

## 7. Fases y criterios de terminado
- **S4-1:** `pytest` en verde, con un test por sala que la recorra entera (respuestas correctas y una incorrecta por concepto) y con la ventana de 2 s de las palancas. `probar_perfiles` sigue en verde. Reporte.
- **S4-2:** cero `error CS`, el nivel greybox se genera desde el JSON y `probar_build.sh` recorre las 5 salas con dos bots. Build de Linux. Reporte + **guion de prueba** en `docs/pruebas/s4-greybox.md`.
- **S4-3 (🧑):** jugar el nivel completo en pareja (dos ventanas) y anotar qué sala aburre, cuál confunde y cuál es demasiado fácil. 🤖 ajusta los números o las tareas.
- **S4-4:** assets e iluminación aplicados; 🧑 aprueba con capturas de cada sala. Rendimiento ≥ 60 FPS en la PC de Jona (mostrar FPS con F3).
- **S4-5:** prueba integral con el panel abierto (estadísticas por concepto), build de Linux y Windows, merge, tag `v0.5-demo` y reporte final.
  - **Migrar el panel a "errores por concepto" y borrar el modo agua por completo** (decisión S4-1): pasar `estadisticas.py`, `admin_api.py`, el frontend React (`Estadisticas.jsx`, `UsuarioDetalle.jsx`) y sus tests de *errores por elemento* a *errores por concepto* (balanceo/mol/masa/limitante/rendimiento), y eliminar la misión "Sintetizar agua" del servidor, el cliente y los tests.
    **Criterio de terminado:** `grep -rinE "sintetizar agua|MISION_AGUA|reaccion_fallida|errores_por_elemento|modo.*agua|\"agua\"" servidor QuimicaVR panel` devuelve **0 referencias**, y `pytest` sigue en verde.

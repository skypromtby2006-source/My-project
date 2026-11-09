# Guion de prueba S4 greybox — Laberinto de las 5 puertas (primera persona) (v0.5-s4-2)

> Lo ejecuta Jona en Arch, en pareja (dos ventanas del build de Linux), con el servidor arriba.
> **Es greybox:** todo son cubos grises; no hay arte ni luces (eso es S4-4). Se valida el
> **diseño**: que las 5 salas se puedan jugar de a dos, con apertura conjunta, montacargas y
> encadenamiento, y que el servidor rechace lo incorrecto. Cubre lo 🔴 de `MDs/SPRINT4.md §5`.
> La parte automatizable la cubre `scripts/probar_build.sh laberinto` (dos bots que recorren las
> 5 salas); esta prueba **no la reemplaza**: no ve el dibujo, los clics ni la sensación de jugar.

## Qué es cada cubo (greybox)
- **Gris alto:** pared · **Gris bajo:** piso · **Slab roja/verde:** puerta (roja = cerrada, verde = abierta).
- **Cian:** consola (dial / balanza / entrada / válvula / lectura) · **Amarillo:** palanca · **Magenta:** montacargas.
- Cada marcador tiene su **id** encima (p. ej. `dial_h2`, `D1_w`). El HUD arriba a la izquierda dice la sala, el concepto, la reacción y los números visibles de tu lado.

## Preparación
1. `scripts/servidor_iniciar.sh`.
2. `scripts/jugar_linux.sh 2` (build de Linux con el greybox del Sprint 4).
3. En cada ventana: conectar a `127.0.0.1`, entrar con un perfil (A y B).
4. A **crea** la sala (A = **Wizard**, lado izquierdo), B **se une** (B = **Player**, lado derecho) y marca *Listo*. A **inicia**.
   - Al iniciar, el cliente manda `iniciar modo:"laberinto"` (no hay opción de modo: es siempre el laberinto).

## Controles
- **WASD** moverse · **mouse** mirar · **E** interactuar con lo que apunta la mira (`+`) · **ESC** pausa (y ajuste de **sensibilidad**).
- Para una **consola de valor** (dial/balanza/entrada): apuntar + **E** abre un campo; escribir el número y **Enviar**. Para **palanca/montacargas/válvula**: apuntar + **E**.

## Pasos
| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1 | Al iniciar, mirar alrededor en primera persona y caminar | Cada uno aparece en **su** lado del muro central. Se ven las paredes, el piso y, al otro lado del muro, la cápsula del otro con su nombre y una "cabeza" que **gira cuando el otro mira** (pitch) |
| 1b | Antes de resolver la Sala 1, **caminar contra la puerta D1 (roja)** y contra el **muro central** | **No se puede pasar:** la puerta cerrada y el muro bloquean físicamente. Al otro lado se ve por el hueco, pero no se cruza |
| 2 | **Sala 1 (balanceo)** `2H₂+O₂→2H₂O`. El HUD dice cuántos mol de H₂O pide la puerta. A ajusta `dial_h2`, B ajusta `dial_o2` con los coeficientes correctos | Con los dos valores bien y las **dos palancas** (`D1_w` y `D1_p`) bajadas con < 2 s de diferencia, la puerta **D1 se abre** (se pone verde y baja: ahora **sí se puede cruzar**). Si la baja uno solo, o un valor está mal, **no abre** ni deja pasar, y el HUD avisa |
| 3 | Probar a propósito un valor **incorrecto** en una consola | El HUD muestra el mensaje de error del concepto y la puerta no abre. (En el panel queda un `error_estequiometria`, se ve en S4-5) |
| 4 | **Sala 2 (mol)** `2Na+2H₂O→2NaOH+H₂`. El HUD de B muestra el agua que llegó de la Sala 1. A pone los mol de `dial_na` | Abren D2 con la relación mol a mol correcta y las dos palancas. El agua de la sala anterior es la que se usa (encadenamiento) |
| 5 | **Sala 3 (masa)** `NaOH+HCl→NaCl+H₂O`. B usa la **válvula** (`valvula_naoh`, E) y A pone en la **balanza** los gramos de NaCl | La puerta solo abre si además de las dos palancas, la válvula fue abierta y la balanza tiene el valor correcto (gramos con 1 decimal; masa molar del Cl = 35,5) |
| 6 | **Sala 4 (limitante)** `N₂+3H₂→2NH₃`. El HUD de A muestra el H₂ limitado que llegó. B pone en `dial_nh3` cuántos mol de NH₃ salen | Abre con el NH₃ que da el **reactivo limitante** (H₂). Con otro número, no abre |
| 7 | **Sala 5 (rendimiento)** `4NH₃+3O₂→2N₂+6H₂O`. El HUD muestra la masa teórica de N₂ y la real del horno. A entra el **rendimiento %** en `consola_teorica` | Con el % correcto y las dos palancas, se abre el **portón final**: el HUD dice "¡Nivel completado!" |
| 8 | Abrir la **pausa** con ESC en plena partida | Se libera el cursor, aparece el menú y el **slider de sensibilidad** cambia la velocidad de la mirada. *Reanudar* vuelve al juego con el cursor bloqueado |
| 9 | Mientras uno juega, que el otro **mire hacia arriba y abajo** | En la ventana del compañero, la "cabeza" de la cápsula se inclina con el pitch |
| 10 | Al terminar el nivel, salir al lobby y volver a entrar a una sala nueva | Se puede arrancar otro laberinto desde cero (números nuevos sorteados por el servidor) |
| 11 | Anotar, por sala: **¿aburre? ¿confunde? ¿es demasiado fácil?** | Es la entrada de S4-3: 🤖 ajusta números o tareas según lo que Jona reporte |

**Esperado y no es un fallo (greybox):** todo son cubos grises sin textura ni luz (arte en S4-4). Las puertas **sí bloquean** (regla del juego, no arte): rojas = cerradas (no se pasa), verdes y bajas = abiertas. Los números de la sala se leen en el HUD, no todavía en la cara de cada consola.

## Resultado
| Fecha | Build (commit) | Quién | Resultado | Notas por sala (aburre/confunde/fácil) |
|---|---|---|---|---|
| | | Jona | | |

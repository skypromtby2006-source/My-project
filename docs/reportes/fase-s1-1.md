## Reporte Fase S1-1 — Servidor (roles Wizard/Player + misión)

Hecho:
- Rama `sprint-1` creada; `main` y `v0.1-demo` quedan intactos.
- `server.py`:
  - `Jugador.rol` es una propiedad que se deriva del anfitrión (`wizard`) o no (`player`). Así, cuando cambia el anfitrión, el rol cambia solo. `sala.info()` incluye `rol`.
  - `iniciar` exige al menos 2 jugadores, además de que todos estén listos.
  - Clase `Mision`: 6 esferas (H, H, O, Na, Cl, C) en posiciones fijas sobre la mesa, con los elementos **barajados** en cada misión para que el player no los memorice. Reactor en el suelo en (0, 0, 4), radio 1, del lado opuesto a donde aparecen los jugadores. Receta 2 H + 1 O.
  - Mensajes nuevos `agarrar`, `soltar`, `senalar` y `reiniciar`, que responden con `obj`, `senal`, `estado` e `inicio` (con `mision`). Se validan el rol, el portador, un solo objeto por jugador, que el objeto no esté en el reactor y que la misión no esté completada.
  - Un elemento equivocado en el reactor suma un error, vuelve a la mesa y muestra "Reacción inestable". Con 2 H + 1 O: `completada` y "¡Reacción completada! 2 H + 1 O → H₂O".
  - Desconexión: el objeto que llevaba cae al suelo en la última posición del jugador. Lo mismo pasa si el player que asciende a wizard llevaba algo, porque un wizard no puede soltar y el objeto quedaría bloqueado.
  - Eventos en BD: `agarrar`, `soltar`, `senal`, `reaccion_fallida` (`esperado`, `recibido`), `mision_completada` (`errores`, `duracion_s`) y `mision_reiniciada`.
- `probar_cliente.py`: recorre los 7 pasos del brief y agrega validaciones extra (Beto no puede señalar ni reiniciar, no puede llevar 2 objetos, el Na vuelve a su lugar en la mesa).
- `docs/protocolo.md`: mensajes nuevos, objeto *misión*, reglas de la misión y eventos. `docs/backlog.md`: lo que quedó fuera de alcance.

Probado (cómo y resultado):
- `servidor_iniciar.sh` (rebuild) y luego `probar_servidor.sh` → `TODO OK ✔` dos veces seguidas.
- En PostgreSQL aparecen `reaccion_fallida` `{"esperado": ["H","H","O"], "recibido": "Na"}`, `mision_completada` `{"errores": 1, "duracion_s": 0.1}` y `mision_reiniciada`.

Pendiente / riesgos:
- La regla 5 pide cambiar Python y C# en el mismo commit; el lado C# llega en S1-2. Mientras tanto, el cliente v0.1 sigue funcionando contra este servidor: ignora los campos nuevos. La única diferencia es que ahora hay que ser 2 para iniciar.
- Las coordenadas de la mesa y el reactor están copiadas de `GestorPartida.cs`. Si la escena cambia en S1-2, hay que mover las constantes de `server.py`.
- El servidor envía `elemento` a todos y el cliente lo oculta a los players (anti-trampas → backlog). El límite de 1.5 m para agarrar solo lo aplicará el cliente.
- `git status` muestra `CLAUDE.md` **borrado** del árbol de trabajo, sin intervención de Claude Code. No se incluyó en ningún commit.

Necesito de Jona:
- Confirmar si borró `CLAUDE.md` a propósito; si no, se restaura con `git checkout -- CLAUDE.md`.
- Nada más para esta fase; S1-2 (cliente Unity) puede arrancar. Para compilar en batch, el editor de Unity tiene que estar cerrado.
Commit: 5bf6c4a

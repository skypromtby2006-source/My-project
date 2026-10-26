## Reporte Fase S1-3 — Prueba de juego (correcciones)

Hecho (bugs que reportó Jona):
1. **Bloqueante: el movimiento remoto y soltar no funcionaban ("JSON inválido").**
   - **La causa real no era la cultura.** Los números ya salían con punto (`InvariantCulture`). El problema eran las llaves: en el Mono de Unity, `string.Format("...\"ry\":{3:F1}}}")` toma `}}` como parte del especificador y escribe el texto `F1` en vez del número. El JSON salía como `"ry":F1}` y lo mismo pasaba con `"z":F3}` en `soltar`.
   - Pista que llevó a la causa: en la BD de la partida WE8R hay `agarrar` y `senal`, que no llevan números, pero ningún `soltar`.
   - Arreglo: `pos` y `soltar` se arman concatenando, y cada número pasa por `Num()` (`ToString("0.###", InvariantCulture)`). En `ClienteRed` no quedan más `string.Format` con números.
2. Red de seguridad de la regla 8 (pedida por el PM): `ClienteRed.Awake` fija `CultureInfo.CurrentCulture` y `DefaultThreadCurrentCulture` a `InvariantCulture`.
3. `server.py`: ante un JSON inválido hace `log.warning` con el id, el nombre y los primeros 120 caracteres de la línea. Se ve con `servidor_logs.sh`.
4. Receta "H□O": `FORMULA` pasa a `2 H + 1 O → H2O`. Se eligió el texto plano y no `<size=70%>`, porque las etiquetas de IMGUI no aceptan tamaños en porcentaje.
5. Etiquetas encimadas en la vista del Wizard: en `server.py` la mesa pasa de 3 a 4 m y la separación entre esferas de 0.5 a 0.7 m (posiciones redondeadas a 3 decimales). En el cliente, las etiquetas de las esferas son más chicas (0.09 en vez de 0.15) y más altas (+0.4 m). El cliente sigue sin coordenadas propias.

Probado (cómo y resultado):
- Reproducción con el Mono de Unity (`MonoBleedingEdge`): la cadena vieja produce `{"t":"pos",...,"ry":F1}` → `json.loads` falla. La versión nueva, con la cultura del proceso en `es-BO` (control: `1.5f.ToString()` = `1,5`), produce `{"t":"pos","x":1.5,"y":1,"z":-2.25,"ry":90}` → JSON válido.
- `probar_servidor.sh` → `TODO OK ✔`.
- Una línea inválida enviada a mano aparece en el log: `[WARNING] JSON inválido de 0fe55f4f (Jugador): '{"t":"soltar","z":F3}\n'`.
- `Construir.Linux` → `Succeeded (95,3 MB, 0 errores)`.
- **No probado en pantalla:** la misión completa la vuelve a probar Jona.

Pendiente / riesgos:
- ⚠️ **`v0.1-demo` (el plan de respaldo) tiene el mismo bug en `pos`.** La línea está así desde `e756de0`. En la Fase 3 se comprobó crear sala, unirse, iniciar y el cambio de anfitrión, pero no que el movimiento remoto llegue al otro jugador. Si a las 19:00 se entrega la v0.1, **los jugadores no se verían moverse**. Decisión para el PM: hacer un hotfix de la v0.1 en `main` (una línea en `ClienteRed.cs` y los builds), o confiar en la v0.2.
- La flecha `→` se vio bien en Linux. En Windows la fuente es la misma, pero conviene revisarla en la S1-4.

Necesito de Jona:
- Repetir la prueba de la S1-3 con el build nuevo: `scripts/servidor_iniciar.sh`, editor → Play (Wizard) y `scripts/jugar_linux.sh 1` (Player). Recorrido: el player se ve moverse, Na → error, señalar, 2 H + 1 O → completada, reiniciar.
- Si vuelve a aparecer "JSON inválido", mirar `scripts/servidor_logs.sh`: ahora muestra la línea culpable.
Commit: e318bf7 (reporte: 8ffff11)

# Decisiones tomadas sin consulta — revisión del 20/11/2026

Trabajo autónomo (sin cliente ni PM). Regla: la opción más simple que mantenga los tests en verde. Cada decisión, con su porqué, para que el PM la revise.

## D1. La mejora visual sale del merge de `sprint-4`, con KayKit incluido
El plan decía "KayKit no está, la mejora es solo con luces, techo, Volume y etiquetas". Al revisar el repo, KayKit **sí está**: `sprint-4` (commit `1e075cd`, CC0, con licencia en `docs/licencias.md`) ya tenía la S4-4 terminada y probada: luz puntual por sala con el color `luz` del JSON, techo, Volume (tonemapping neutral + bloom suave), niebla, etiquetas ocultas salvo con F3 y capturas antes/después en `docs/capturas/s4-4/`.
**Por qué:** rehacer lo mismo "sin assets" costaba horas y daba un resultado peor. El merge (`b2eb566`) solo tuvo 4 conflictos triviales y dejó los **5 escenarios de `probar_build.sh` en verde** (laberinto a 527 FPS a 1920×1080). Si el PM prefiere la versión sin KayKit, se revierte con `git revert -m 1 b2eb566`.


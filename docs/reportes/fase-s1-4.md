## Reporte Fase S1-4 — Entrega v0.2 (parte de Claude Code)

Hecho:
- S1-3 cerrada: el cliente aprobó la ronda 2 (movimiento, soltar, error con Na, señalamiento, misión completada y reinicio en editor + build de Linux). Reporte y casillas actualizados.
- Build de Windows en batch: `Succeeded (97,7 MB, 0 errores)`.
- `scripts/empaquetar.sh v0.2` → `dist/QuimicaDemo_Windows_v0.2.zip` (37 MB).
- `entrega/LEEME.txt` (va dentro del zip):
  - Pasa a v0.2.
  - El PASO 3 dice quién será Wizard y quién Player, y que hacen falta al menos 2 jugadores.
  - El PASO 4 nuevo explica roles, controles por rol (WASD/Esc; clic y "Reiniciar misión" para el Wizard; E para agarrar y soltar para el Player), la misión 2 H + 1 O, qué pasa con un elemento equivocado y el cambio de Wizard si el anfitrión sale.
- `README.md`: v0.2, un párrafo sobre los roles y la misión, y el nombre del zip nuevo.
- **No hay merge a `main`**: queda a la espera de la prueba en Windows.

Probado (cómo y resultado):
- Zip descomprimido en una carpeta aparte:
  - LEEME y los 6 `.bat` tienen finales CRLF.
  - No hay `__pycache__` ni `*_DoNotShip`.
  - `docker compose config` es válido desde `Servidor/`.
  - `server.py` es idéntico al del repo.
  - `Assembly-CSharp.dll` es idéntica al build y contiene el código nuevo (`0.###` de `Num()`, "Reiniciar misión").
  - `MatBase`, `MatEsfera` y `MatTranslucido` están en `resources.assets` del build de Windows, así que no debería verse magenta.

Pendiente / riesgos:
- **Prueba en Windows 11 (🧑 Jona).** Es la única forma de validar Docker Desktop, el `.exe` y la fuente de Windows (la flecha `→` de la receta).
- Si en esa PC ya quedó instalada la v0.1, `instalar_servidor.bat` reconstruye la imagen (`up -d --build`), así que el servidor queda en v0.2 sin pasos extra.
- Sigue abierto el riesgo de la S1-3: `v0.1-demo` tiene el bug del JSON en `pos`. Si a las 19:00 se entrega la v0.1, los jugadores no se verán moverse. Lo decide el PM.

Necesito de Jona:
1. Copiar `dist/QuimicaDemo_Windows_v0.2.zip` al disco de Windows o a un USB y reiniciar en Windows 11.
2. Descomprimir, abrir Docker Desktop → `Servidor\instalar_servidor.bat` → abrir `Juego\QuimicaDemo.exe` dos veces.
3. Ventana A crea la sala (Wizard), B se une y marca Listo (Player), A inicia. Recorrer la misión: moverse, Na → error, señalar, 2 H + 1 O → completada, reiniciar. Revisar que la receta se lea bien.
4. Opcional: `Servidor\ver_eventos_bd.bat` para ver `reaccion_fallida` y `mision_completada`.
5. Avisarme el resultado: si es OK, hago el merge a `main`, el tag `v0.2-demo` y el reporte final.

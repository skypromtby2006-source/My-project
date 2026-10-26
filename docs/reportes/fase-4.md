## Reporte Fase 4 — Paquete de entrega Windows

Hecho:
- 4.1 `scripts/empaquetar.sh [versión]` genera `dist/QuimicaDemo_Windows_v0.1.zip` (37 MB):
  `QuimicaDemo/Juego/` (build de Windows sin la carpeta de símbolos `*_DoNotShip`), `QuimicaDemo/Servidor/` (compose + `servidor/` + los 5 `.bat`) y `QuimicaDemo/LEEME.txt` (fuente: `entrega/LEEME.txt`).
  Convierte `.bat` y LEEME a CRLF y **aborta si queda alguna línea sin CRLF**.
- 4.2 `README.md`: qué es, arquitectura en 5 puntos, tabla de scripts de Linux, builds en batch, pasos de Windows y estructura. Enlaza a `docs/protocolo.md` y a `docs/decisiones.md`.
- Extra: `docs/decisiones.md` conserva la sección "Cómo funciona por dentro" del LEEME anterior (el porqué de asyncio, hilo + cola en Unity, 15 envíos/s + Lerp, IMGUI, Docker, InvariantCulture y el arreglo de materiales). Sin esto se habría perdido al borrar `_base/`, y es lo que Jona necesita para defender el proyecto.
- 4.3 `_base/` borrada después de confirmar con `cmp` que todo quedó migrado sin diferencias (salvo los 4 scripts de Unity modificados a propósito en `8dd74b3`). Tag `v0.1-demo` subido a GitHub.
- La carpeta local `My project/` se conserva por decisión de Jona y quedó en `.gitignore`.

Probado (cómo y resultado):
- Zip descomprimido en una carpeta aparte: `file` confirma CRLF en los 5 `.bat` y en `LEEME.txt`; no hay `*_DoNotShip` ni `__pycache__`; `docker compose config` es válido desde `Servidor/` (build `./servidor`); `QuimicaDemo.exe` es idéntico byte a byte al build.
- `git ls-remote --tags origin` muestra `v0.1-demo`.

Pendiente / riesgos:
- **No se probó en Windows real** (Fase 5): Docker Desktop, `instalar_servidor.bat` y el `.exe` en Windows 11 solo se pueden validar allá.
- El `.exe` no está firmado: Windows SmartScreen mostrará "Windows protegió su PC". El LEEME explica cómo continuar.
- El zip no está en git (`dist/` se ignora): hay que copiarlo a mano al USB o al disco de Windows.

Necesito de Jona:
- Fase 5: copiar `dist/QuimicaDemo_Windows_v0.1.zip`, reiniciar en Windows 11 y seguir el `LEEME.txt` (Docker Desktop → `instalar_servidor.bat` → abrir el `.exe` dos veces → prueba 3.3).

Commit: eccdde8 (tag v0.1-demo)

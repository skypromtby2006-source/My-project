## Investigación — "el arte no se ve en la partida" (Sprint 4) · 19/11/2026

Pedido del PM: investigar y reportar, **sin corregir**. Además: capturas automáticas por sala en `probar_build.sh laberinto`.

### 1. Estado de la S4-4: no empezó
- No hay commits ni reportes después de la S4-2 (`docs/reportes/` termina en `fase-s4-2.md`). **Tampoco hay reporte de la S4-3** (la prueba de jugabilidad).
- **KayKit no está ni aplicado ni preparado:** no existe `QuimicaVR/Assets/ThirdParty/` en ninguna rama, ningún commit lo nombra y no hay archivos de KayKit en el disco (`find ~ -iname '*kaykit*'` vacío). Según la memoria del proyecto, la consigna era prepararlo *si llegaban* los assets, y no llegaron.
- `GeneradorNivel.cs` lo dice en su encabezado: *"El arte y la luz por sala llegan en S4-4"*. El nivel es **greybox**: cubos grises para paredes y pisos, cubos de colores para consolas (celeste), palancas (amarillo), montacargas (violeta) y puertas (rojo/verde), con etiquetas de depuración con el id (`dial_h2`, `D1_w`…).
- **Conclusión:** "el arte no se ve" porque **no hay arte**. No es un asset que se pierda en el build.

### 2. ¿Entra en el build?
No hay arte que pueda faltar, pero revisé lo que hay:
- **Tamaño:** 97,1 MB (`Build/Linux`, 98 MB en disco), lo mismo que en la S2-4 (98,5 MB). No se agregó ningún asset.
- **Shaders:** los 3 materiales de `Resources/Materiales/` usan **URP Lit**, que entra al build por estar referenciado desde `Resources`. La captura cuenta **267 renderers del nivel y 0 con shader faltante** (`Hidden/InternalErrorShader` o no soportado), y no hay magenta en ninguna imagen.
- **Referencias solo de editor:** ningún script fuera de `Assets/Editor/` usa `UnityEditor`.
- **`~/.config/unity3d/DefaultCompany/QuimicaDemo/Player.log`:** es del **26/10**. Desde entonces nadie abrió el build con ventana en esta PC (las pruebas corren con su propio log), así que no sirve como evidencia. No tiene errores de shaders ni de assets.
- Si el cliente lo vio en Windows, su log está en `%USERPROFILE%\AppData\LocalLow\DefaultCompany\QuimicaDemo\Player.log`.

### 3. Iluminación por sala: no está configurada
- El JSON del nivel trae un color de `luz` por sala (`#2E5FA8`, `#3FB24F`, `#2FA06A`, `#B23A2E`, `#C9A227`). El cliente lo recibe (`InfoSalaLayout.luz`, `InfoSalaEstado.luz`), pero **ningún script lo usa**.
- Escena `Demo.unity`: **una sola luz direccional** (intensidad 1, con sombras), **niebla apagada**, skybox por defecto, ambiente por cielo, **sin Volume en la escena**. El perfil de Volume por defecto de URP (`DefaultVolumeProfile`) está en valores neutros: post-exposición 0, tonemapping en *None*, bloom y viñeta en 0.
- **La niebla y la exposición no tapan nada.** Las 10 capturas dan luminancia media de 0,37 a 0,41 y contraste de 0,12 a 0,17. Todo se ve, y **igual en todas las salas**: no hay ambientación por sala. Las salas no tienen techo, así que se ve el cielo por arriba.

### 4. Capturas automáticas (nuevo en `probar_build.sh laberinto`)
- Paso nuevo `capturas` en `PruebaAutomatica`: para cada sala (1 a 5) y cada lado (Wizard y Player), lleva la **cámara del jugador local** (la misma `Camera`, con su FOV y su post-proceso) a la esquina del cuarto opuesta a la consola, a 1,6 m, mirando a la consola. Renderiza a una textura de 1280×720, guarda el PNG en `logs/capturas/laberinto/sala<N>_<lado>.png` y devuelve la cámara a su lugar **en el mismo frame**: el jugador no se mueve y el servidor no se entera.
- Además mide cada imagen y `probar_build.py` lo comprueba solo:
  - luminancia media entre 0,06 y 0,94 (ni negra ni quemada);
  - contraste ≥ 0,03 (no es un color plano);
  - magenta < 1 %;
  - ningún material con shader faltante;
  - una imagen por sala y por lado.
  Lo que no puede decidir es si el arte *se ve bien*: eso queda para una persona, mirando los PNG.
- **Sin ventana:** el escenario `laberinto` corre en `-batchmode` **sin** `-nographics`, así que crea GPU pero no abre ninguna ventana. En esta PC usa OpenGL Core en la RTX 5050.
  - Probado: el player de Linux **necesita un servidor gráfico**. Sin `DISPLAY` se cuelga con OpenGL y se cae (segfault) con Vulkan.
  - Por eso, sin sesión gráfica `probar_build.py` usa `xvfb-run`, y si no está instalado falla con el comando para instalarlo.
- Contraprueba: con `-nographics`, el paso falla con *"captura sin GPU"* en lugar de dar imágenes vacías.
- Los otros escenarios siguen con `-nographics`, como antes.
- Accesores de solo lectura agregados para la prueba (no cambian el juego): `GestorPartida.Generador` y `GeneradorNivel.CentroCelda`.

Probado: `probar_build.sh laberinto` → TODO OK, 24 ✔ (11 de capturas). `laberinto_player sesion reinicio panel` → TODO OK, 18 ✔. Miré yo mismo las capturas de la sala 1 (Wizard) y de la sala 3 (Player): coinciden con el diagnóstico (greybox, cielo abierto, etiquetas de depuración).

### Necesito de Jona
- **¿Llegaron los assets de KayKit?** Si los tiene descargados, que los deje en `QuimicaVR/Assets/ThirdParty/` (o que me pase la ruta).
- **El `Player.log` de la PC donde lo vio** (si fue en Windows, la ruta de arriba) y **qué zip o build estaba jugando**, para confirmar que no es otro problema además de la falta de arte.
- Opcional: `sudo pacman -S xorg-server-xvfb`, para que las capturas también corran sin sesión gráfica (por SSH o en CI).
- El detalle de las pruebas que el cliente reportó en el Sprint 4 (lo pasa el PM).

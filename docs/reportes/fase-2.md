## Reporte Fase 2 — Proyecto Unity

Hecho:
- 2.1 (Jona) Proyecto `QuimicaVR` (Universal 3D) creado en la raíz del repo.
- 2.2 Scripts copiados a `Assets/Scripts/Red/` y `Assets/Editor/`.
- 2.3 Compilación en batch: 0 `error CS` (Assembly-CSharp y Assembly-CSharp-Editor).
- 2.4 `ConfigurarDemo.Configurar` en batch: `Assets/Scenes/Demo.unity` creada y única escena en Build Settings; productName QuimicaDemo, ventana 1280×720, runInBackground, Active Input Handling = Both (el proyecto venía con "solo Input System nuevo": WASD habría lanzado error).
- 2.5 Commit del proyecto (77 archivos) sin Library/Temp/Logs/UserSettings; se agregó `*.slnx` (solución que genera Unity 6) al `.gitignore`.
- 2.6 (Jona) Prueba en editor + build Linux con 2 jugadores: OK. Encontró dos defectos, corregidos en `8dd74b3`:
  - **Todo magenta en el build:** los objetos se crean por código, ninguna escena referenciaba URP/Lit y Unity lo eliminaba. Ahora usan `Resources/Materiales/MatBase.mat` (creado por script en `ConfigurarDemo.AsegurarRecursos`, que también llama `Construir`).
  - **Mismo nombre "Jugador81" en ambas instancias:** editor y builds comparten PlayerPrefs. El nombre automático se genera en cada arranque y solo se guarda uno escrito por el usuario.
- Los cambios que el editor hizo al abrir el proyecto (componentes URP de luz/cámara) van aparte en `5b88f62`.

Probado (cómo y resultado):
- Builds Linux y Windows en batch: `Succeeded`, 0 errores (Linux 66,9 → 94,6 MB: ahora entra URP/Lit).
- `MatBase` y `Universal Render Pipeline/Lit` están dentro de `resources.assets` en ambos builds.
- 2 instancias del build Linux arrancan sin errores de shader en sus logs.
- Lo visual (sin magenta, nombres flotantes) se confirma en la 3.3.

Pendiente / riesgos:
- Intenté forzar `GUI/Text Shader` (fuente de los TextMesh) en *Always Included Shaders* y el build falló con `Failed to write file unity_builtin_extra`. Se descartó: la fuente integrada y su shader ya vienen en los recursos por defecto. Si en la 3.3 los nombres no se ven, se revisa ahí.
- La carpeta `My project/` (48 KB, solo caché de shaders) sigue sin borrar, a la espera de que Jona confirme.

Necesito de Jona:
- Prueba 3.3 (ver reporte en terminal).

Commit: 8dd74b3

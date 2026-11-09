## Reporte Fase S4-1 — Nivel como dato, los 5 puzzles y el sorteo de números

> Arranque del Sprint 4 (lunes 09/11). Esta fase es el servidor: el nivel vive en
> un JSON, el servidor sortea los números y valida. Primera persona, greybox y el
> protocolo nuevo completo vienen en S4-2. **Hay 3 decisiones de diseño abajo
> (sección "Que los números cierren") que necesito que el cliente resuelva antes
> de terminar S4-1.**

### Hecho
- **Git / versión:**
  - `v0.4` (Sprint 3, panel de administración) mergeada a `main` con merge-commit y **tag `v0.4-demo`**.
  - Rama **`sprint-4`** creada desde `main`.
  - **Fix del §6** (pendiente del lunes): `server.py` ahora atrapa `UnicodeDecodeError`/`ValueError` además de `JSONDecodeError`, registra `WARNING "Datos no válidos desde <ip> (¿navegador o escáner en el puerto del juego?)"` y **cierra** esa conexión. Es el primer commit de `sprint-4`.
- **El nivel es un dato:** `servidor/niveles/laberinto_01.json` con una grilla de texto por lado (greybox, se refina en S4-2) y los 5 puzzles (reacción, concepto, consolas, montacargas, puerta con palanca por lado).
- **Sorteo con enteros garantizados:** `servidor/nivel.py` sortea los números de cada partida dentro de rangos que **siempre** dan resultados enteros, modela el encadenamiento (lo que produce una sala = lo que recibe la siguiente) y trae el validador de la ventana de 2 s de las palancas.

### Probado (cómo y resultado)
- `pytest` del servidor: **35 pasan** (29 previos del panel + 6 nuevos de `test_nivel.py`).
- `test_nivel.py` incluye: carga del JSON, **3000 sorteos** verificando que las 5 salas den enteros, cierre del encadenamiento entre salas, rendimiento = real/teórica, y la ventana de 2 s (abre con < 2 s, no abre si baja uno solo).
- El fix del §6 sigue cubierto por `test_bytes_binarios_no_tumban_al_servidor`.

### Que los números cierren — 3 decisiones para el cliente (SPRINT4 §2 y §46)
El §34 pide "rangos que den resultados enteros". Al encadenar las 5 reacciones aparecen tres puntos que **no cierran solos**. Propongo, no invento:

**1. El número base `n` (mol de agua de la Sala 1) tiene que ser múltiplo de 6.**
`n` recorre todo el nivel. Para que las 5 salas den enteros a la vez hace falta que sea:
- **par** → O₂ de la Sala 1 (`n/2`) y H₂ de la Sala 2 (`n/2`) enteros, y gramos enteros en la Sala 3;
- **múltiplo de 3** → NH₃ de la Sala 4 (`n/3`, reactivo limitante) entero.
mcm(2, 3) = 6. Implementado como `n ∈ {6, 12, 18, 24}`. **Consecuencia:** no se puede sortear `n = 5` ni `n = 8`. Es una restricción matemática, no una elección, pero la informo porque acota la dificultad. *Si el cliente quiere más variedad, se puede ampliar a {6, 12, 18, 24, 30, 36} sin romper nada.* → **Decisión: ¿rango {6..24} o más amplio?**

**2. Sala 3 (masa a masa): las masas molares de secundaria tienen ,5.**
Con Cl = 35,5, HCl = 36,5 g/mol y NaCl = 58,5 g/mol. Los gramos solo son enteros si el mol que llega es par. Como `n` es múltiplo de 6 (par), **cierra**: p. ej. `n=6` → 219 g de HCl → 351 g de NaCl. Pero la balanza puede mostrar ,5 si el cliente quisiera sortear gramos sueltos. Propongo **mantener el encadenamiento (HCl = n mol) y que la balanza muestre 1 decimal**, aclarando en el puzzle que la masa molar del Cl es 35,5. No es un bug; es presentación. → **Decisión: ¿1 decimal en la balanza, OK?**

**3. Sala 5 (rendimiento): el encadenamiento químico se rompe (NH₃ → CH₄).**
La Sala 4 produce **NH₃** ("combustible del portón") y la Sala 5 es la combustión del **metano** (`CH₄ + 2O₂ → CO₂ + 2H₂O`). NH₃ no es CH₄: el "producto de una sala se usa en la siguiente" (§29) deja de ser cierto en la última sala. Hoy lo modelé como que el NH₃ llega al horno y "hace de" CH₄, pero eso es físicamente falso. Dos opciones:
- **Opción A (mínimo cambio, narrativa):** el NH₃ es el combustible que **enciende el horno**, y la reacción que se resuelve es la del metano con CH₄ propio de la cripta. El encadenamiento de la última sala pasa a ser narrativo ("el NH₃ prende el portón"), no químico.
- **Opción B (químicamente honesta, recomendada):** cambiar la Sala 5 a la **combustión del amoníaco**: `4NH₃ + 3O₂ → 2N₂ + 6H₂O`. Así el NH₃ de la Sala 4 **sí** es el reactivo de la Sala 5 y el rendimiento se calcula sobre el agua (o el NO) producido. Mantiene el encadenamiento real y es más defendible ante el docente. Cuesta cambiar una fila de la tabla §2 y la masa molar del cálculo.

Recomiendo **Opción B**. Dejé el puzzle marcado con `_ajuste_pendiente` en el JSON para no congelar la decisión.

### Pendiente / riesgos
- **S4-1 todavía no está "terminado" según §7:** falta wirear en `server.py` el protocolo nuevo (`interactuar`, `dial`, `montacargas`, `palanca`, `sala_estado` + `pitch` en `pos`), retirar la misión "Sintetizar agua" y su test, emitir `error_estequiometria` y `sala_completada`, y los **tests por sala** que recorran cada una entera (correcta + una incorrecta por concepto). La base de datos y los validadores ya están listos para engancharlo. **No lo hice todavía porque la decisión 3 cambia la Sala 5** y prefiero no implementar sobre un número que el cliente puede mover.
- Riesgo de alcance: S4-2 (primera persona + greybox) es grande; si la decisión 3 tarda, igual puedo avanzar salas 1–4.
- Las grillas del JSON son greybox de relleno; la geometría jugable se define en S4-2.

### Necesito de Jona
1. **Las 3 decisiones** de arriba (sobre todo la **3**: ¿Opción A narrativa u **Opción B** combustión de NH₃?).
2. Confirmar que empiece a **descargar los assets CC0** (§4: KayKit Dungeon Remastered, Quaternius, Poly Haven) a `QuimicaVR/Assets/ThirdParty/<pack>/` — es tarea 🧑 del lunes y no bloquea el servidor.
3. **¿Pusheo `main` + tag `v0.4-demo` + `sprint-4` a GitHub ahora?** Lo dejé commiteado en local a la espera de tu OK (es acción hacia afuera).

### Commit
- `sprint-4`: fix del §6, brief del Sprint 4, y este arranque S4-1 (nivel + sorteo + tests). Hashes en el push.

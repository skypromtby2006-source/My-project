using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

// Construye el nivel GREYBOX a partir del dato que manda el servidor en inicio.nivel
// (SPRINT4 §3.1/§3.2: "el cliente construye el nivel a partir de ese dato"). Cubos
// grises para las paredes, pisos, y marcadores de color para consolas, palancas y
// montacargas (con su Interactuable para el raycast). Las posiciones salen del JSON;
// aquí no hay ninguna coordenada inventada.
//
// S4-4: si están los prefabs de Resources/Arte (los arma Editor/ConfigurarArte.cs con
// KayKit), los cubos del greybox quedan INVISIBLES pero siguen ahí con su collider: la
// colisión, las puertas y el raycast de las consolas no cambian. El arte va encima,
// escalado a la celda de 2 m. Sin los prefabs, el nivel sale en greybox como antes.
public class GeneradorNivel
{
    const float CELDA = 2f;      // tamaño de cada celda de la grilla, en metros
    const float ALTO_PARED = 3f;

    public GameObject Raiz { get; private set; }
    int anchoGrilla;
    InfoNivel nivel;

    // Puertas por número de sala (1..5), para abrirlas a medida que se completan.
    readonly List<(int sala, GameObject go)> puertas = new List<(int, GameObject)>();
    readonly Dictionary<GameObject, Transform> artePuerta = new Dictionary<GameObject, Transform>();

    // Arte (S4-4)
    GameObject pPared, pPiso, pTecho, pRejilla, pPuerta, pReja, pConsola, pPalanca, pGemaMonta;
    bool hayArte;
    const float GROSOR_PANEL = .25f;   // el de los prefabs Pared y Puerta
    // Luz por sala: puntual, sin sombras (solo la luz principal de la escena las hace)
    const float RANGO_LUZ = 7f, INTENSIDAD_LUZ = 6f;
    public const string NombreEtiqueta = "EtiquetaDepuracion";

    static readonly Color GRIS = new Color(.45f, .47f, .52f);
    static readonly Color PISO = new Color(.28f, .3f, .36f);
    static readonly Color CONSOLA = new Color(.3f, .7f, .95f);
    static readonly Color PALANCA = new Color(.95f, .8f, .25f);
    static readonly Color MONTA = new Color(.85f, .4f, .85f);
    static readonly Color PUERTA_CERRADA = new Color(.55f, .25f, .25f);
    static readonly Color PUERTA_ABIERTA = new Color(.3f, .8f, .4f);

    float OrigenX(string lado) => lado == "wizard" ? 0f : (anchoGrilla + 3) * CELDA;

    Vector3 Mundo(string lado, int col, int row, float y) =>
        new Vector3(OrigenX(lado) + col * CELDA, y, -row * CELDA);

    // Para PruebaAutomatica (capturas por sala): la misma conversión celda -> mundo del nivel
    public Vector3 CentroCelda(string lado, int col, int row, float y) => Mundo(lado, col, row, y);

    public Vector3 AparicionMundo(string lado)
    {
        var l = lado == "wizard" ? nivel.lados.wizard : nivel.lados.player;
        if (l != null && l.aparicion != null && l.aparicion.Count >= 2)
            return Mundo(lado, l.aparicion[0], l.aparicion[1], 1f);
        return Mundo(lado, 2, 1, 1f);
    }

    public void Construir(InfoNivel n, Transform padre)
    {
        nivel = n;
        CargarArte();
        Raiz = new GameObject("Nivel");
        if (padre != null) Raiz.transform.SetParent(padre);
        anchoGrilla = (n.lados != null && n.lados.wizard != null && n.lados.wizard.grilla.Count > 0)
            ? n.lados.wizard.grilla[0].Length : 21;

        ConstruirLado("wizard", n.lados != null ? n.lados.wizard : null);
        ConstruirLado("player", n.lados != null ? n.lados.player : null);

        // Muro central con reja (visual): una pared larga entre los dos lados.
        float xMuro = (anchoGrilla + 1.5f) * CELDA;
        var muro = Cubo("MuroCentral", new Vector3(xMuro, ALTO_PARED / 2, -2 * CELDA),
                        new Vector3(CELDA, ALTO_PARED, 6 * CELDA), GRIS);
        muro.name = "MuroCentral";
        Ocultar(muro);
        // La reja: 6 tramos de 2 m a lo largo del muro (de z = 2 m a z = -10 m)
        if (hayArte)
            for (int k = 0; k < 6; k++)
                Poner(pReja, new Vector3(xMuro, 0, CELDA - CELDA / 2 - k * CELDA), 90);

        if (n.salas != null)
            foreach (var s in n.salas)
            {
                ConstruirInteractuables(s);
                if (hayArte) { LuzSala(s, "wizard"); LuzSala(s, "player"); }
            }

        // Tonemapping y bloom suave (el perfil lo arma ConfigurarArte; la niebla está en la escena)
        var perfil = hayArte ? Resources.Load<VolumeProfile>("Arte/VolumenLaberinto") : null;
        if (perfil != null)
        {
            var v = new GameObject("Volumen");
            v.transform.SetParent(Raiz.transform);
            var vol = v.AddComponent<Volume>();
            vol.isGlobal = true;
            vol.sharedProfile = perfil;
        }
    }

    void CargarArte()
    {
        GameObject A(string nombre) => Resources.Load<GameObject>("Arte/" + nombre);
        pPared = A("Pared"); pPiso = A("Piso"); pTecho = A("Techo"); pRejilla = A("Rejilla");
        pPuerta = A("Puerta"); pReja = A("Reja"); pConsola = A("Consola"); pPalanca = A("Palanca");
        pGemaMonta = A("GemaMontacargas");
        hayArte = pPared && pPiso && pTecho && pRejilla && pPuerta && pReja && pConsola && pPalanca && pGemaMonta;
        if (!hayArte) Debug.LogWarning("[Quimica] Faltan prefabs en Resources/Arte: el laberinto sale en greybox");
    }

    GameObject Poner(GameObject prefab, Vector3 pos, float rotY)
    {
        return Object.Instantiate(prefab, pos, Quaternion.Euler(0, rotY, 0), Raiz.transform);
    }

    // Con arte, el cubo del greybox sigue ahí por su collider, pero no se dibuja
    void Ocultar(GameObject go)
    {
        if (hayArte) go.GetComponent<MeshRenderer>().enabled = false;
    }

    // Las baldosas del techo tienen juntas: el sol se filtraba por ellas y dibujaba un
    // panal de luz en paredes y piso. Una losa que solo proyecta sombra (no se ve ni choca)
    // sobre todo el lado lo tapa: adentro manda la luz de cada sala.
    void TapaDeSombra(string lado, List<string> g)
    {
        int filas = g.Count, cols = g[0].Length;
        var tapa = GameObject.CreatePrimitive(PrimitiveType.Cube);
        tapa.name = "TapaDeSombra_" + lado;
        tapa.GetComponent<Collider>().enabled = false;
        tapa.transform.SetParent(Raiz.transform);
        tapa.transform.position = Mundo(lado, 0, 0, ALTO_PARED + .4f) + new Vector3((cols - 1) * CELDA / 2, 0, -(filas - 1) * CELDA / 2);
        tapa.transform.localScale = new Vector3((cols + 1) * CELDA, .2f, (filas + 1) * CELDA);
        var r = tapa.GetComponent<MeshRenderer>();
        Pintar(tapa, GRIS);
        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.ShadowsOnly;
    }

    static bool EsPared(List<string> g, int r, int c) =>
        r < 0 || r >= g.Count || c < 0 || c >= g[r].Length || g[r][c] == '#';

    // Un panel de pared en cada cara de la celda '#' que da a una celda libre. Los paneles
    // del prefab miran a ±z; los que dan a una celda vecina en x se giran 90°.
    void Paneles(string lado, List<string> g, int r, int c)
    {
        var centro = Mundo(lado, c, r, 0f);
        foreach (var (dc, dr) in new[] { (1, 0), (-1, 0), (0, 1), (0, -1) })
        {
            if (EsPared(g, r + dr, c + dc)) continue;
            var dir = new Vector3(dc, 0, -dr);   // fila +1 = z negativo (ver Mundo)
            Poner(pPared, centro + dir * (CELDA / 2 - GROSOR_PANEL / 2), dc != 0 ? 90 : 0);
        }
    }

    // La luz de la sala (color "luz" del JSON) en el centro del cuarto, cerca del techo.
    // El cuarto se ubica por su consola: está entre paredes cada 4 columnas.
    void LuzSala(InfoSalaLayout s, string lado)
    {
        var consolas = lado == "wizard" ? s.consolas?.wizard : s.consolas?.player;
        if (consolas == null || consolas.Count == 0 || consolas[0].pos.Count < 2) return;
        int c0 = (consolas[0].pos[0] - 1) / 4 * 4 + 1;
        var go = new GameObject($"luz_{lado}_sala{s.n}");
        go.transform.SetParent(Raiz.transform);
        go.transform.position = Mundo(lado, c0 + 1, 2, ALTO_PARED - .5f);
        var luz = go.AddComponent<Light>();
        luz.type = LightType.Point;
        luz.color = ColorUtility.TryParseHtmlString(s.luz ?? "", out var col) ? col : Color.white;
        luz.range = RANGO_LUZ;
        luz.intensity = INTENSIDAD_LUZ;
        luz.shadows = LightShadows.None;
    }

    void ConstruirLado(string lado, InfoLado l)
    {
        if (l == null || l.grilla == null) return;
        if (hayArte) TapaDeSombra(lado, l.grilla);
        for (int r = 0; r < l.grilla.Count; r++)
        {
            string fila = l.grilla[r];
            for (int c = 0; c < fila.Length; c++)
            {
                char ch = fila[c];
                if (ch == '#')
                {
                    Ocultar(Cubo($"pared_{lado}_{r}_{c}", Mundo(lado, c, r, ALTO_PARED / 2),
                                 new Vector3(CELDA, ALTO_PARED, CELDA), GRIS));
                    if (hayArte) Paneles(lado, l.grilla, r, c);
                }
                else
                {
                    Ocultar(Cubo($"piso_{lado}_{r}_{c}", Mundo(lado, c, r, 0f),
                                 new Vector3(CELDA, .1f, CELDA), PISO));
                    if (hayArte)
                    {
                        // 'M' = montacargas: rejilla en lugar de baldosa. Techo en toda celda libre:
                        // así cada sala es un cuarto y su luz no se mezcla con el cielo.
                        Poner(ch == 'M' ? pRejilla : pPiso, Mundo(lado, c, r, 0f), 0);
                        Poner(pTecho, Mundo(lado, c, r, ALTO_PARED), 0);
                    }
                    if (ch == 'D')
                    {
                        // Puerta: cubo SÓLIDO que llena el hueco de la pared (bloquea de
                        // verdad). El collider se desactiva cuando sala_estado la marca
                        // abierta (AbrirHasta). Es regla del juego, no arte.
                        // La sala se deduce de la columna (las puertas están en col 4,8,12,16).
                        var go = Cubo($"puerta_{lado}_{c}", Mundo(lado, c, r, ALTO_PARED / 2),
                                      new Vector3(CELDA, ALTO_PARED, CELDA), PUERTA_CERRADA);
                        puertas.Add((c / 4, go));
                        Ocultar(go);
                        // La reja se para de cara al paso: si las celdas libres están a los
                        // lados en x, el paso va en x y la reja se gira 90°.
                        if (hayArte)
                        {
                            bool pasoEnX = !EsPared(l.grilla, r, c - 1) || !EsPared(l.grilla, r, c + 1);
                            artePuerta[go] = Poner(pPuerta, Mundo(lado, c, r, 0f), pasoEnX ? 90 : 0).transform;
                        }
                    }
                }
            }
        }
    }

    void ConstruirInteractuables(InfoSalaLayout s)
    {
        if (s.consolas != null)
        {
            foreach (var c in s.consolas.wizard) Marcador(Interactuable.Clase.Consola, c.id, c.tipo, "wizard", c.pos, null);
            foreach (var c in s.consolas.player) Marcador(Interactuable.Clase.Consola, c.id, c.tipo, "player", c.pos, null);
        }
        if (s.montacargas != null && s.montacargas.pos != null && s.montacargas.pos.Count >= 2)
            Marcador(Interactuable.Clase.Montacargas, s.montacargas.id, "montacargas", "wizard", s.montacargas.pos, null);
        if (s.puerta != null)
        {
            Marcador(Interactuable.Clase.Palanca, s.puerta.id + "_w", "palanca", "wizard", s.puerta.palanca_wizard, s.puerta.id);
            Marcador(Interactuable.Clase.Palanca, s.puerta.id + "_p", "palanca", "player", s.puerta.palanca_player, s.puerta.id);
        }
    }

    void Marcador(Interactuable.Clase clase, string id, string subtipo, string lado, List<int> pos, string puertaId)
    {
        if (pos == null || pos.Count < 2) return;
        Color color = clase == Interactuable.Clase.Palanca ? PALANCA
                    : clase == Interactuable.Clase.Montacargas ? MONTA : CONSOLA;
        var go = Cubo(id, Mundo(lado, pos[0], pos[1], 1f), Vector3.one * .6f, color);
        var it = go.AddComponent<Interactuable>();
        it.clase = clase; it.id = id; it.subtipo = subtipo; it.lado = lado; it.puertaId = puertaId;
        // El cubo queda para el raycast de "E"; lo que se ve es la pieza del arte
        Ocultar(go);
        if (hayArte)
        {
            var prefab = clase == Interactuable.Clase.Palanca ? pPalanca
                       : clase == Interactuable.Clase.Montacargas ? pGemaMonta : pConsola;
            Poner(prefab, Mundo(lado, pos[0], pos[1], 0f), 0);
        }

        // Etiqueta con el id: solo para depurar, se ve con F3 (Depuracion)
        var etiqueta = new GameObject(NombreEtiqueta).AddComponent<TextMesh>();
        etiqueta.gameObject.SetActive(Depuracion.Visible);
        etiqueta.transform.SetParent(go.transform, false);
        etiqueta.transform.localPosition = new Vector3(0, 1f, 0);
        etiqueta.text = id;
        etiqueta.characterSize = .08f;
        etiqueta.fontSize = 40;
        etiqueta.anchor = TextAnchor.MiddleCenter;
        var fuente = GestorPartida.FuenteBase();
        if (fuente != null) { etiqueta.font = fuente; etiqueta.GetComponent<MeshRenderer>().material = fuente.material; }
    }

    // Abre las puertas de las salas ya completadas: desactiva su collider (deja pasar)
    // y la baja/pinta de verde. Las cerradas siguen bloqueando.
    public void AbrirHasta(int salaActual, bool nivelCompleto)
    {
        foreach (var (sala, go) in puertas)
        {
            if (go == null) continue;
            bool abierta = nivelCompleto || sala < salaActual;
            var col = go.GetComponent<Collider>();
            if (col != null) col.enabled = !abierta;    // abierta -> no bloquea
            float alto = abierta ? .4f : ALTO_PARED;    // abierta -> baja, como una reja levantada
            go.transform.localScale = new Vector3(CELDA, alto, CELDA);
            var p = go.transform.position; p.y = alto / 2f; go.transform.position = p;
            Pintar(go, abierta ? PUERTA_ABIERTA : PUERTA_CERRADA);
            // La reja del arte baja al piso igual que el cubo: queda asomando lo mismo (40 cm)
            if (artePuerta.TryGetValue(go, out var reja) && reja != null)
            {
                var pr = reja.position; pr.y = abierta ? alto - ALTO_PARED : 0f; reja.position = pr;
            }
        }
    }

    public void Destruir()
    {
        if (Raiz != null) Object.Destroy(Raiz);
        Raiz = null;
        puertas.Clear();
        artePuerta.Clear();
    }

    GameObject Cubo(string nombre, Vector3 pos, Vector3 escala, Color color)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = nombre;
        go.transform.SetParent(Raiz.transform);
        go.transform.position = pos;
        go.transform.localScale = escala;
        Pintar(go, color);
        return go;
    }

    // Mismos materiales de Resources que GestorPartida (si no, magenta en el build).
    static readonly Dictionary<string, Material> materiales = new Dictionary<string, Material>();
    static void Pintar(GameObject go, Color color)
    {
        if (!materiales.TryGetValue("MatBase", out var mat) || mat == null)
        {
            mat = Resources.Load<Material>("Materiales/MatBase");
            if (mat == null) { Debug.LogError("[Quimica] Falta Resources/Materiales/MatBase.mat"); return; }
            materiales["MatBase"] = mat;
        }
        go.GetComponent<Renderer>().sharedMaterial = new Material(mat) { color = color };
    }
}

using System.Collections.Generic;
using UnityEngine;

// Construye el nivel GREYBOX a partir del dato que manda el servidor en inicio.nivel
// (SPRINT4 §3.1/§3.2: "el cliente construye el nivel a partir de ese dato"). Cubos
// grises para las paredes, pisos, y marcadores de color para consolas, palancas y
// montacargas (con su Interactuable para el raycast). Las posiciones salen del JSON;
// aquí no hay ninguna coordenada inventada. El arte y la luz por sala llegan en S4-4.
public class GeneradorNivel
{
    const float CELDA = 2f;      // tamaño de cada celda de la grilla, en metros
    const float ALTO_PARED = 3f;

    public GameObject Raiz { get; private set; }
    int anchoGrilla;
    InfoNivel nivel;

    // Puertas por número de sala (1..5), para abrirlas a medida que se completan.
    readonly List<(int sala, GameObject go)> puertas = new List<(int, GameObject)>();

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
        Raiz = new GameObject("Nivel");
        if (padre != null) Raiz.transform.SetParent(padre);
        anchoGrilla = (n.lados != null && n.lados.wizard != null && n.lados.wizard.grilla.Count > 0)
            ? n.lados.wizard.grilla[0].Length : 21;

        ConstruirLado("wizard", n.lados != null ? n.lados.wizard : null);
        ConstruirLado("player", n.lados != null ? n.lados.player : null);

        // Muro central con reja (visual): una pared larga entre los dos lados.
        var muro = Cubo("MuroCentral", new Vector3((anchoGrilla + 1.5f) * CELDA, ALTO_PARED / 2, -2 * CELDA),
                        new Vector3(CELDA, ALTO_PARED, 6 * CELDA), GRIS);
        muro.name = "MuroCentral";

        if (n.salas != null)
            foreach (var s in n.salas) ConstruirInteractuables(s);
    }

    void ConstruirLado(string lado, InfoLado l)
    {
        if (l == null || l.grilla == null) return;
        for (int r = 0; r < l.grilla.Count; r++)
        {
            string fila = l.grilla[r];
            for (int c = 0; c < fila.Length; c++)
            {
                char ch = fila[c];
                if (ch == '#')
                    Cubo($"pared_{lado}_{r}_{c}", Mundo(lado, c, r, ALTO_PARED / 2),
                         new Vector3(CELDA, ALTO_PARED, CELDA), GRIS);
                else
                {
                    Cubo($"piso_{lado}_{r}_{c}", Mundo(lado, c, r, 0f),
                         new Vector3(CELDA, .1f, CELDA), PISO);
                    if (ch == 'D')
                    {
                        // Puerta: cubo SÓLIDO que llena el hueco de la pared (bloquea de
                        // verdad). El collider se desactiva cuando sala_estado la marca
                        // abierta (AbrirHasta). Es regla del juego, no arte.
                        // La sala se deduce de la columna (las puertas están en col 4,8,12,16).
                        var go = Cubo($"puerta_{lado}_{c}", Mundo(lado, c, r, ALTO_PARED / 2),
                                      new Vector3(CELDA, ALTO_PARED, CELDA), PUERTA_CERRADA);
                        puertas.Add((c / 4, go));
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

        var etiqueta = new GameObject("Etiqueta").AddComponent<TextMesh>();
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
        }
    }

    public void Destruir()
    {
        if (Raiz != null) Object.Destroy(Raiz);
        Raiz = null;
        puertas.Clear();
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

using System.Collections.Generic;
using UnityEngine;

// Escenario de la partida: suelo, jugadores y la misión (mesa, reactor y esferas).
// Todo se genera por código para no depender de prefabs.
// La mesa, el reactor y las esferas NO tienen posiciones propias aquí: se dibujan
// con lo que manda el servidor en inicio.mision, la única fuente de verdad.
public class GestorPartida : MonoBehaviour
{
    public float velocidad = 5f;
    public float enviosPorSegundo = 15f;
    public float alcanceAgarre = 1.5f;     // distancia horizontal máxima para agarrar con E
    public float duracionSenal = 2f;

    GameObject escena, jugadorLocal, raizMision;
    readonly Dictionary<string, Remoto> remotos = new Dictionary<string, Remoto>();
    readonly Dictionary<string, Esfera> esferas = new Dictionary<string, Esfera>();
    InfoMision mision;
    float proximoEnvio;
    Camera cam;

    class Remoto { public GameObject go; public Vector3 destino; public float rotY; }

    class Esfera
    {
        public InfoObjeto info;
        public GameObject go;        // contenedor: se mueve este
        public Transform malla;      // la esfera visible (escala del pulso)
        public Material material;
        public TextMesh etiqueta;
        public float senalHasta;
    }

    // El color va por posición en la mesa (o1..o6) y NO por elemento: como el servidor
    // baraja los elementos en cada misión, el color no delata qué es cada esfera.
    // Sirve para hablar ("la azul") sin que el player pueda saltarse al wizard.
    static readonly Color[] coloresEsfera =
    {
        new Color(.95f, .5f, .2f), new Color(.95f, .85f, .25f), new Color(.35f, .8f, .4f),
        new Color(.3f, .6f, .95f), new Color(.65f, .45f, .9f), new Color(.95f, .5f, .75f),
    };

    void Start()
    {
        cam = Camera.main;
        var red = ClienteRed.I;
        red.AlRecibir += m =>
        {
            switch (m.t)
            {
                case "inicio": Comenzar(m.sala, m.mision); break;
                case "pos": MoverRemoto(m); break;
                case "salio": Quitar(m.id); break;
                case "obj": if (m.objeto != null && esferas.TryGetValue(m.objeto.id, out var e)) e.info = m.objeto; break;
                case "senal": if (m.objId != null && esferas.TryGetValue(m.objId, out var s)) s.senalHasta = Time.time + duracionSenal; break;
            }
        };
        red.AlDesconectar += Terminar;
    }

    void Comenzar(InfoSala sala, InfoMision nueva)
    {
        // "inicio" llega también cuando el wizard reinicia: en ese caso solo se rehace la
        // misión y los jugadores siguen donde están.
        bool enCurso = escena != null && jugadorLocal != null;
        if (!enCurso)
        {
            Terminar();
            escena = new GameObject("Escena");

            var suelo = GameObject.CreatePrimitive(PrimitiveType.Plane);
            suelo.transform.SetParent(escena.transform);
            suelo.transform.localScale = new Vector3(3, 1, 3);
            Pintar(suelo, new Color(.25f, .28f, .35f));

            for (int i = 0; i < sala.jugadores.Count; i++)
            {
                var j = sala.jugadores[i];
                var inicio = new Vector3(-6 + i * 3f, 1, -5);
                // El color es el del perfil, así cada uno se reconoce igual en el lobby y en la partida
                if (!ColorUtility.TryParseHtmlString(j.color, out var color)) color = Color.white;
                var go = Crear(j.nombre, color, inicio);
                if (j.id == ClienteRed.I.MiId) jugadorLocal = go;
                else remotos[j.id] = new Remoto { go = go, destino = inicio };
            }
        }

        if (nueva == null) { Debug.LogWarning("[Quimica] 'inicio' sin misión: ¿servidor viejo?"); return; }
        ConstruirMision(nueva);
    }

    void ConstruirMision(InfoMision m)
    {
        if (raizMision != null) Destroy(raizMision);
        esferas.Clear();
        mision = m;
        raizMision = new GameObject("Mision");
        raizMision.transform.SetParent(escena.transform);

        var mesa = GameObject.CreatePrimitive(PrimitiveType.Cube);
        mesa.name = "Mesa";
        mesa.transform.SetParent(raizMision.transform);
        mesa.transform.position = new Vector3(m.mesa.x, m.mesa.y, m.mesa.z);
        mesa.transform.localScale = new Vector3(m.mesa.ancho, m.mesa.alto, m.mesa.largo);
        Pintar(mesa, new Color(.9f, .9f, .95f));

        // Reactor: disco plano translúcido. El cilindro de Unity mide 2 de alto y 1 de
        // diámetro, por eso la escala es (2r, grosor/2, 2r).
        var r = m.reactor;
        var reactor = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        reactor.name = "Reactor";
        reactor.transform.SetParent(raizMision.transform);
        reactor.transform.position = new Vector3(r.x, r.y + .02f, r.z);
        reactor.transform.localScale = new Vector3(2 * r.radio, .02f, 2 * r.radio);
        Destroy(reactor.GetComponent<Collider>());   // que el clic del wizard no choque con él
        Pintar(reactor, new Color(.2f, .9f, 1f, .4f), "MatTranslucido");
        var titulo = CrearEtiqueta(raizMision.transform, "REACTOR", new Color(.6f, .95f, 1f));
        titulo.transform.position = new Vector3(r.x, r.y + 1.2f, r.z);

        for (int i = 0; i < m.objetos.Count; i++)
        {
            var info = m.objetos[i];
            var go = new GameObject(info.id);
            go.transform.SetParent(raizMision.transform);
            go.transform.position = new Vector3(info.x, info.y, info.z);

            var malla = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            malla.transform.SetParent(go.transform, false);
            malla.transform.localScale = Vector3.one * 2 * m.radio_objeto;
            Pintar(malla, coloresEsfera[i % coloresEsfera.Length], "MatEsfera");

            // Más chica y más alta que la de los jugadores, para que no se encime con las vecinas
            var etiqueta = CrearEtiqueta(go.transform, "?", Color.white, .09f);
            etiqueta.transform.localPosition = new Vector3(0, m.radio_objeto + .4f, 0);

            esferas[info.id] = new Esfera
            {
                info = info, go = go, malla = malla.transform, etiqueta = etiqueta,
                material = malla.GetComponent<Renderer>().sharedMaterial,
            };
        }
    }

    GameObject Crear(string nombre, Color color, Vector3 pos)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        go.name = nombre;
        go.transform.SetParent(escena.transform);
        go.transform.position = pos;
        Pintar(go, color);

        // "nariz" para ver hacia dónde mira
        var nariz = GameObject.CreatePrimitive(PrimitiveType.Cube);
        nariz.transform.SetParent(go.transform, false);
        nariz.transform.localPosition = new Vector3(0, .4f, .5f);
        nariz.transform.localScale = Vector3.one * .25f;
        Pintar(nariz, Color.Lerp(color, Color.black, .5f));

        // Nombre flotante, más alto que el objeto que se lleva sobre la cabeza
        var etiqueta = CrearEtiqueta(go.transform, nombre, Color.white);
        etiqueta.transform.localPosition = new Vector3(0, 1.9f, 0);
        return go;
    }

    static TextMesh CrearEtiqueta(Transform padre, string texto, Color color, float tam = .15f)
    {
        var etiqueta = new GameObject("Etiqueta").AddComponent<TextMesh>();
        etiqueta.transform.SetParent(padre, false);
        etiqueta.text = texto;
        etiqueta.color = color;
        etiqueta.characterSize = tam;
        etiqueta.fontSize = 40;
        etiqueta.anchor = TextAnchor.MiddleCenter;
        var fuente = FuenteBase();
        if (fuente != null)
        {
            etiqueta.font = fuente;
            etiqueta.GetComponent<MeshRenderer>().material = fuente.material;
        }
        return etiqueta;
    }

    // Materiales URP/Lit guardados en Resources (los crea ConfigurarDemo.AsegurarRecursos).
    // Por qué: los objetos se crean en tiempo de ejecución, así que ninguna escena referencia
    // el shader y Unity lo elimina del build -> todo se ve magenta. Lo que está en Resources
    // entra siempre al build junto con su shader. MatEsfera trae la emisión activada y
    // MatTranslucido la transparencia: esas variantes del shader tampoco se pueden
    // activar en tiempo de ejecución si ningún material del build las usa.
    static readonly Dictionary<string, Material> materiales = new Dictionary<string, Material>();
    static void Pintar(GameObject go, Color color, string nombre = "MatBase")
    {
        if (!materiales.TryGetValue(nombre, out var mat) || mat == null)
        {
            mat = Resources.Load<Material>("Materiales/" + nombre);
            if (mat == null) { Debug.LogError($"[Quimica] Falta Resources/Materiales/{nombre}.mat"); return; }
            materiales[nombre] = mat;
        }
        // URP/Lit marca _BaseColor como [MainColor], por eso funciona .color
        go.GetComponent<Renderer>().sharedMaterial = new Material(mat) { color = color };
    }

    static Font fuenteCache;
    static Font FuenteBase()
    {
        if (fuenteCache != null) return fuenteCache;
        // Unity 2022.2+ usa LegacyRuntime.ttf; versiones anteriores, Arial.ttf
        try { fuenteCache = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); } catch { }
        if (fuenteCache == null) try { fuenteCache = Resources.GetBuiltinResource<Font>("Arial.ttf"); } catch { }
        return fuenteCache;
    }

    void MoverRemoto(Mensaje m)
    {
        if (!remotos.TryGetValue(m.id, out var r)) return;
        r.destino = new Vector3(m.x, m.y, m.z);
        r.rotY = m.ry;
    }

    void Quitar(string id)
    {
        if (!remotos.TryGetValue(id, out var r)) return;
        Destroy(r.go);
        remotos.Remove(id);
    }

    Transform CuerpoDe(string jugadorId)
    {
        if (jugadorId == ClienteRed.I.MiId) return jugadorLocal != null ? jugadorLocal.transform : null;
        return remotos.TryGetValue(jugadorId, out var r) ? r.go.transform : null;
    }

    void Update()
    {
        if (jugadorLocal == null) return;

        // Movimiento local (WASD / flechas)
        var dir = new Vector3(Input.GetAxisRaw("Horizontal"), 0, Input.GetAxisRaw("Vertical"));
        if (dir.sqrMagnitude > .01f)
        {
            dir.Normalize();
            jugadorLocal.transform.position += dir * velocidad * Time.deltaTime;
            jugadorLocal.transform.rotation = Quaternion.Slerp(jugadorLocal.transform.rotation, Quaternion.LookRotation(dir), 12 * Time.deltaTime);
        }

        // Enviar posición ~15 veces por segundo (no cada frame: ahorra red)
        if (Time.time >= proximoEnvio)
        {
            proximoEnvio = Time.time + 1f / enviosPorSegundo;
            ClienteRed.I.EnviarPosicion(jugadorLocal.transform.position, jugadorLocal.transform.eulerAngles.y);
        }

        // Interpolar remotos para que no "salten"
        foreach (var r in remotos.Values)
        {
            r.go.transform.position = Vector3.Lerp(r.go.transform.position, r.destino, 12 * Time.deltaTime);
            r.go.transform.rotation = Quaternion.Slerp(r.go.transform.rotation, Quaternion.Euler(0, r.rotY, 0), 12 * Time.deltaTime);
        }

        if (mision != null)
        {
            LeerAcciones();
            ActualizarEsferas();
        }

        // Cámara en tercera persona
        if (cam != null)
        {
            var objetivo = jugadorLocal.transform.position + new Vector3(0, 8, -9);
            cam.transform.position = Vector3.Lerp(cam.transform.position, objetivo, 5 * Time.deltaTime);
            cam.transform.LookAt(jugadorLocal.transform.position);
        }

        // Los textos miran a la cámara
        if (cam != null)
            foreach (var t in escena.GetComponentsInChildren<TextMesh>())
                t.transform.rotation = cam.transform.rotation;
    }

    // El cliente solo PIDE; el servidor decide y responde con "obj"/"senal" a todos.
    // Por eso aquí no se mueve ninguna esfera: así nadie ve algo que el servidor rechazó.
    void LeerAcciones()
    {
        var red = ClienteRed.I;
        if (red.SoyWizard)
        {
            if (Input.GetMouseButtonDown(0) && cam != null &&
                Physics.Raycast(cam.ScreenPointToRay(Input.mousePosition), out var hit, 200f))
            {
                foreach (var e in esferas.Values)
                    if (hit.transform == e.malla) { red.Senalar(e.info.id); break; }
            }
            return;
        }

        if (!Input.GetKeyDown(KeyCode.E)) return;

        foreach (var e in esferas.Values)
            if (e.info.portador == red.MiId) { red.Soltar(e.info.id, PuntoDeSoltar()); return; }

        // Agarrar la esfera libre más cercana dentro del alcance (distancia horizontal:
        // las de la mesa están más altas que el centro de la cápsula)
        Esfera mejor = null;
        float mejorDist = alcanceAgarre;
        var yo = jugadorLocal.transform.position;
        foreach (var e in esferas.Values)
        {
            if (!string.IsNullOrEmpty(e.info.portador)) continue;
            var p = e.go.transform.position;
            float d = Vector2.Distance(new Vector2(yo.x, yo.z), new Vector2(p.x, p.z));
            if (d <= mejorDist) { mejorDist = d; mejor = e; }
        }
        if (mejor != null) red.Agarrar(mejor.info.id);
    }

    // Un metro delante del jugador: sobre la tapa si cae encima de la mesa, si no en el suelo
    Vector3 PuntoDeSoltar()
    {
        var p = jugadorLocal.transform.position + jugadorLocal.transform.forward * 1f;
        var m = mision.mesa;
        bool sobreMesa = Mathf.Abs(p.x - m.x) <= m.ancho / 2 && Mathf.Abs(p.z - m.z) <= m.largo / 2;
        p.y = (sobreMesa ? m.y + m.alto / 2 : 0f) + mision.radio_objeto;
        return p;
    }

    void ActualizarEsferas()
    {
        bool soyWizard = ClienteRed.I.SoyWizard;
        foreach (var e in esferas.Values)
        {
            // Mientras alguien la lleva, se dibuja sobre su cabeza con la posición que ya
            // llega por "pos": no hace falta otro flujo de mensajes para el objeto.
            var cuerpo = string.IsNullOrEmpty(e.info.portador) ? null : CuerpoDe(e.info.portador);
            if (cuerpo != null)
                e.go.transform.position = cuerpo.position + Vector3.up * (1.2f + mision.radio_objeto);
            else
                e.go.transform.position = Vector3.Lerp(e.go.transform.position, new Vector3(e.info.x, e.info.y, e.info.z), 15 * Time.deltaTime);

            // El rol puede cambiar a mitad de partida (si el anfitrión se va), por eso se revisa cada frame
            e.etiqueta.text = soyWizard ? e.info.elemento : "?";

            // Señal del wizard: pulso de escala y brillo. Lo ven todos, también los players:
            // saben CUÁL les indican, pero no QUÉ es.
            float resto = e.senalHasta - Time.time;
            float k = resto > 0 ? Mathf.Abs(Mathf.Sin(resto * Mathf.PI * 3)) : 0;
            e.malla.localScale = Vector3.one * 2 * mision.radio_objeto * (1 + .4f * k);
            e.material.SetColor("_EmissionColor", new Color(1f, .9f, .3f) * 2.5f * k);
        }
    }

    public void Terminar()
    {
        if (escena != null) Destroy(escena);
        escena = null;
        raizMision = null;
        jugadorLocal = null;
        mision = null;
        remotos.Clear();
        esferas.Clear();
    }
}

using System.Collections.Generic;
using UnityEngine;

// Escenario plano de demostración: crea el suelo, tu jugador y los jugadores remotos.
// Todo se genera por código para no depender de prefabs.
public class GestorPartida : MonoBehaviour
{
    public float velocidad = 5f;
    public float enviosPorSegundo = 15f;

    GameObject escena, jugadorLocal;
    readonly Dictionary<string, Remoto> remotos = new Dictionary<string, Remoto>();
    float proximoEnvio;
    Camera cam;

    class Remoto { public GameObject go; public Vector3 destino; public float rotY; }

    static readonly Color[] colores = { Color.cyan, Color.yellow, Color.magenta, Color.green, new Color(1f, .5f, 0f), Color.red, Color.white, Color.blue };

    void Start()
    {
        cam = Camera.main;
        var red = ClienteRed.I;
        red.AlRecibir += m =>
        {
            switch (m.t)
            {
                case "inicio": Comenzar(m.sala); break;
                case "pos": MoverRemoto(m); break;
                case "salio": Quitar(m.id); break;
            }
        };
        red.AlDesconectar += Terminar;
    }

    void Comenzar(InfoSala sala)
    {
        Terminar();
        escena = new GameObject("Escena");

        var suelo = GameObject.CreatePrimitive(PrimitiveType.Plane);
        suelo.transform.SetParent(escena.transform);
        suelo.transform.localScale = new Vector3(3, 1, 3);
        suelo.GetComponent<Renderer>().material.color = new Color(.25f, .28f, .35f);

        // "Mesa de laboratorio" decorativa en el centro
        var mesa = GameObject.CreatePrimitive(PrimitiveType.Cube);
        mesa.transform.SetParent(escena.transform);
        mesa.transform.position = new Vector3(0, .5f, 0);
        mesa.transform.localScale = new Vector3(3, 1, 1.5f);
        mesa.GetComponent<Renderer>().material.color = new Color(.9f, .9f, .95f);

        for (int i = 0; i < sala.jugadores.Count; i++)
        {
            var j = sala.jugadores[i];
            var inicio = new Vector3(-6 + i * 3f, 1, -5);
            var go = Crear(j.nombre, colores[i % colores.Length], inicio);
            if (j.id == ClienteRed.I.MiId) jugadorLocal = go;
            else remotos[j.id] = new Remoto { go = go, destino = inicio };
        }
    }

    GameObject Crear(string nombre, Color color, Vector3 pos)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        go.name = nombre;
        go.transform.SetParent(escena.transform);
        go.transform.position = pos;
        go.GetComponent<Renderer>().material.color = color;

        // "nariz" para ver hacia dónde mira
        var nariz = GameObject.CreatePrimitive(PrimitiveType.Cube);
        nariz.transform.SetParent(go.transform, false);
        nariz.transform.localPosition = new Vector3(0, .4f, .5f);
        nariz.transform.localScale = Vector3.one * .25f;

        // nombre flotante
        var etiqueta = new GameObject("Nombre").AddComponent<TextMesh>();
        etiqueta.transform.SetParent(go.transform, false);
        etiqueta.transform.localPosition = new Vector3(0, 1.4f, 0);
        etiqueta.text = nombre;
        etiqueta.characterSize = .15f;
        etiqueta.fontSize = 40;
        etiqueta.anchor = TextAnchor.MiddleCenter;
        var fuente = FuenteBase();
        if (fuente != null)
        {
            etiqueta.font = fuente;
            etiqueta.GetComponent<MeshRenderer>().material = fuente.material;
        }
        return go;
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

        // Cámara en tercera persona
        if (cam != null)
        {
            var objetivo = jugadorLocal.transform.position + new Vector3(0, 8, -9);
            cam.transform.position = Vector3.Lerp(cam.transform.position, objetivo, 5 * Time.deltaTime);
            cam.transform.LookAt(jugadorLocal.transform.position);
        }

        // Los nombres miran a la cámara
        if (cam != null)
            foreach (var t in escena.GetComponentsInChildren<TextMesh>())
                t.transform.rotation = cam.transform.rotation;
    }

    public void Terminar()
    {
        if (escena != null) Destroy(escena);
        escena = null;
        jugadorLocal = null;
        remotos.Clear();
    }
}

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

// ---------- Modelos que llegan del servidor (JsonUtility ignora los campos que no vienen) ----------
[Serializable] public class InfoJugador { public string id; public string nombre; public string color; public bool listo; public string rol; }

// Perfil: llega en la raíz del mensaje "perfil" (ver docs/protocolo.md)
[Serializable] public class EntradaHistorial { public string fecha; public float duracion_s; public int errores; }

[Serializable] public class InfoProgreso
{
    public int completadas;
    public float mejor_tiempo_s;   // 0 = todavía sin misiones
    public int errores_totales;
    public List<EntradaHistorial> historial = new List<EntradaHistorial>();
}

[Serializable] public class InfoPerfil
{
    public string id;              // id de esta conexión, el mismo que usa la sala
    public string usuario, nombre, color;
    public InfoProgreso progreso;
}

[Serializable] public class InfoSala
{
    public string id; public string nombre; public string host;
    public int maximo; public int cantidad; public string estado;
    public List<InfoJugador> jugadores = new List<InfoJugador>();
}

// Misión: los nombres de campo son idénticos a los de server.py (Mision.info)
[Serializable] public class InfoObjeto
{
    public string id, elemento, portador;   // portador: id del jugador que lo lleva, "" = nadie
    public float x, y, z;
}

[Serializable] public class InfoReactor { public float x, y, z, radio; }
[Serializable] public class InfoMesa { public float x, y, z, ancho, alto, largo; }
[Serializable] public class ItemReceta { public string elemento; public int cantidad; }

[Serializable] public class EstadoMision
{
    public List<string> reactor = new List<string>();   // símbolos ya aceptados
    public int errores;
    public bool completada;
    public string mensaje;
}

[Serializable] public class InfoMision
{
    public List<InfoObjeto> objetos = new List<InfoObjeto>();
    public InfoReactor reactor;
    public InfoMesa mesa;
    public float radio_objeto;
    public List<ItemReceta> receta = new List<ItemReceta>();
    public string formula;
    public EstadoMision estado;
}

[Serializable] public class Mensaje
{
    public string t;            // tipo de mensaje
    public string id, nombre, msg;
    public InfoSala sala;
    public List<InfoSala> lista;
    public InfoMision mision;
    public float x, y, z, ry;

    // "obj" llega como objeto en el mensaje "obj" y como texto en "senal". JsonUtility
    // no admite un campo con dos tipos, así que esos mensajes se leen aparte (ver Update)
    // y el resultado se guarda aquí, fuera de la serialización.
    [NonSerialized] public InfoObjeto objeto;      // mensaje "obj"
    [NonSerialized] public string objId, por;      // mensaje "senal"
    [NonSerialized] public EstadoMision estado;    // mensaje "estado"
    [NonSerialized] public InfoPerfil perfil;      // mensaje "perfil"
}

[Serializable] class MsgObj { public InfoObjeto obj; }
[Serializable] class MsgSenal { public string obj; public string por; }

// ---------- Cliente TCP: un hilo lee del socket, Unity procesa en Update ----------
public class ClienteRed : MonoBehaviour
{
    public static ClienteRed I { get; private set; }

    // La misma paleta que server.py. Aquí solo sirve para dibujar el selector:
    // el servidor es el que rechaza un color que no esté en la lista.
    public static readonly string[] Paleta = { "#3FA9F5", "#F5D33F", "#E04FD8", "#4FE07A", "#F5913F", "#E04F4F", "#FFFFFF", "#6A5AE0" };

    public bool Conectado => cliente != null && cliente.Connected;
    public string MiId { get; private set; }
    public InfoPerfil MiPerfil { get; private set; }   // null = sin sesión
    public InfoSala SalaActual { get; private set; }
    public InfoMision MisionActual { get; private set; }
    public EstadoMision EstadoActual => MisionActual?.estado;

    // El rol no se guarda: se lee de la sala cada vez, así refleja el cambio de anfitrión
    public string MiRol => SalaActual?.jugadores.Find(j => j.id == MiId)?.rol ?? "player";
    public bool SoyWizard => MiRol == "wizard";

    public event Action<Mensaje> AlRecibir;   // cualquier mensaje
    public event Action<string> AlError;      // errores legibles
    public event Action AlDesconectar;

    TcpClient cliente;
    StreamWriter escritor;
    Thread hiloLectura;
    readonly ConcurrentQueue<string> entrada = new ConcurrentQueue<string>();
    readonly object candado = new object();
    volatile bool cayoConexion;

    void Awake()
    {
        if (I != null) { Destroy(gameObject); return; }
        I = this;
        DontDestroyOnLoad(gameObject);

        // Red de seguridad (regla 8): si algún número se formatea sin indicar cultura,
        // que salga con punto aunque Windows/Linux esté en español. Incluye los hilos
        // nuevos, como el de lectura del socket.
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
    }

    public bool Conectar(string ip, int puerto)
    {
        try
        {
            cliente = new TcpClient();
            var intento = cliente.BeginConnect(ip, puerto, null, null);
            if (!intento.AsyncWaitHandle.WaitOne(3000)) throw new Exception("tiempo de espera agotado");
            cliente.EndConnect(intento);
            cliente.NoDelay = true;

            var flujo = cliente.GetStream();
            escritor = new StreamWriter(flujo, new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" };
            var lector = new StreamReader(flujo, Encoding.UTF8);

            cayoConexion = false;
            hiloLectura = new Thread(() =>
            {
                try { string linea; while ((linea = lector.ReadLine()) != null) entrada.Enqueue(linea); }
                catch { /* socket cerrado */ }
                cayoConexion = true;
            }) { IsBackground = true };
            hiloLectura.Start();
            // Ya no se manda "hola": la identidad llega con login o registro
            return true;
        }
        catch (Exception e)
        {
            AlError?.Invoke($"No se pudo conectar a {ip}:{puerto} ({e.Message})");
            Cerrar();
            return false;
        }
    }

    // ---------- Perfil (el servidor responde siempre con "perfil" o "error") ----------
    public void Registrar(string usuario, string nombre, string color) =>
        Enviar("{\"t\":\"registro\",\"usuario\":" + Json(usuario) + ",\"nombre\":" + Json(nombre) + ",\"color\":" + Json(color) + "}");
    public void Login(string usuario) => Enviar("{\"t\":\"login\",\"usuario\":" + Json(usuario) + "}");
    public void EditarPerfil(string nombre, string color) =>
        Enviar("{\"t\":\"perfil_editar\",\"nombre\":" + Json(nombre) + ",\"color\":" + Json(color) + "}");
    public void VerPerfil() => Enviar("{\"t\":\"perfil_ver\"}");

    // ---------- Acciones de lobby ----------
    public void ListarSalas() => Enviar("{\"t\":\"listar\"}");
    public void CrearSala(string nombre, int maximo) => Enviar($"{{\"t\":\"crear_sala\",\"nombre_sala\":{Json(nombre)},\"maximo\":{maximo}}}");
    public void Unirse(string codigo) => Enviar($"{{\"t\":\"unirse\",\"sala_id\":{Json(codigo)}}}");
    public void SalirSala() => Enviar("{\"t\":\"salir\"}");
    public void MarcarListo(bool v) => Enviar($"{{\"t\":\"listo\",\"valor\":{(v ? "true" : "false")}}}");
    public void IniciarPartida() => Enviar("{\"t\":\"iniciar\"}");

    public void EnviarPosicion(Vector3 p, float rotY) =>
        Enviar("{\"t\":\"pos\",\"x\":" + Num(p.x) + ",\"y\":" + Num(p.y) + ",\"z\":" + Num(p.z) + ",\"ry\":" + Num(rotY) + "}");

    // ---------- Acciones de la misión (el servidor valida el rol) ----------
    public void Agarrar(string obj) => Enviar($"{{\"t\":\"agarrar\",\"obj\":{Json(obj)}}}");
    public void Senalar(string obj) => Enviar($"{{\"t\":\"senalar\",\"obj\":{Json(obj)}}}");
    public void Reiniciar() => Enviar("{\"t\":\"reiniciar\"}");

    public void Soltar(string obj, Vector3 p) =>
        Enviar("{\"t\":\"soltar\",\"obj\":" + Json(obj) + ",\"x\":" + Num(p.x) + ",\"y\":" + Num(p.y) + ",\"z\":" + Num(p.z) + "}");

    void Enviar(string json)
    {
        if (!Conectado) return;
        try { lock (candado) escritor.WriteLine(json); }
        catch { cayoConexion = true; }
    }

    void Update()
    {
        while (entrada.TryDequeue(out var linea))
        {
            Mensaje m;
            try { m = JsonUtility.FromJson<Mensaje>(linea); } catch { continue; }

            switch (m.t)
            {
                case "perfil":
                    // Los campos del perfil están en la raíz del mensaje y coinciden con InfoPerfil
                    m.perfil = JsonUtility.FromJson<InfoPerfil>(linea);
                    MiPerfil = m.perfil;
                    MiId = m.perfil.id;
                    break;
                case "sala": SalaActual = m.sala; break;
                case "inicio": SalaActual = m.sala; MisionActual = m.mision; break;
                case "fuera": SalaActual = null; MisionActual = null; break;
                case "obj":
                    m.objeto = JsonUtility.FromJson<MsgObj>(linea).obj;
                    if (MisionActual != null)
                    {
                        int i = MisionActual.objetos.FindIndex(o => o.id == m.objeto.id);
                        if (i >= 0) MisionActual.objetos[i] = m.objeto;
                    }
                    break;
                case "senal":
                    var s = JsonUtility.FromJson<MsgSenal>(linea);
                    m.objId = s.obj; m.por = s.por;
                    break;
                case "estado":
                    // Los campos de "estado" están en la raíz del mensaje y coinciden con EstadoMision
                    m.estado = JsonUtility.FromJson<EstadoMision>(linea);
                    if (MisionActual != null) MisionActual.estado = m.estado;
                    break;
                case "error": AlError?.Invoke(m.msg); break;
            }
            AlRecibir?.Invoke(m);
        }

        if (cayoConexion && cliente != null)
        {
            Cerrar();
            AlDesconectar?.Invoke();
        }
    }

    public void Cerrar()
    {
        try { cliente?.Close(); } catch { }
        cliente = null;
        SalaActual = null;
        MisionActual = null;
        MiId = null;
        MiPerfil = null;
    }

    void OnApplicationQuit() => Cerrar();

    // Todo número que viaja en el JSON pasa por aquí: siempre con punto decimal (regla 8).
    // Los mensajes se arman concatenando y NO con string.Format: en el Mono de Unity,
    // "{3:F1}}}" toma las llaves "}}" como parte del formato y escribe el texto "F1"
    // en vez del número, lo que rompía "pos" y "soltar" ("JSON inválido" en el servidor).
    static string Num(float v) => v.ToString("0.###", CultureInfo.InvariantCulture);

    static string Json(string s) =>
        "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
}

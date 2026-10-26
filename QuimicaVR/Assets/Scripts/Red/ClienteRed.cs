using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

// ---------- Modelos que llegan del servidor (JsonUtility ignora los campos que no vienen) ----------
[Serializable] public class InfoJugador { public string id; public string nombre; public bool listo; }

[Serializable] public class InfoSala
{
    public string id; public string nombre; public string host;
    public int maximo; public int cantidad; public string estado;
    public List<InfoJugador> jugadores = new List<InfoJugador>();
}

[Serializable] public class Mensaje
{
    public string t;            // tipo de mensaje
    public string id, nombre, msg;
    public InfoSala sala;
    public List<InfoSala> lista;
    public float x, y, z, ry;
}

// ---------- Cliente TCP: un hilo lee del socket, Unity procesa en Update ----------
public class ClienteRed : MonoBehaviour
{
    public static ClienteRed I { get; private set; }

    public bool Conectado => cliente != null && cliente.Connected;
    public string MiId { get; private set; }
    public InfoSala SalaActual { get; private set; }

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
    }

    public bool Conectar(string ip, int puerto, string nombre)
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

            Enviar($"{{\"t\":\"hola\",\"nombre\":{Json(nombre)}}}");
            return true;
        }
        catch (Exception e)
        {
            AlError?.Invoke($"No se pudo conectar a {ip}:{puerto} ({e.Message})");
            Cerrar();
            return false;
        }
    }

    // ---------- Acciones de lobby ----------
    public void ListarSalas() => Enviar("{\"t\":\"listar\"}");
    public void CrearSala(string nombre, int maximo) => Enviar($"{{\"t\":\"crear_sala\",\"nombre_sala\":{Json(nombre)},\"maximo\":{maximo}}}");
    public void Unirse(string codigo) => Enviar($"{{\"t\":\"unirse\",\"sala_id\":{Json(codigo)}}}");
    public void SalirSala() => Enviar("{\"t\":\"salir\"}");
    public void MarcarListo(bool v) => Enviar($"{{\"t\":\"listo\",\"valor\":{(v ? "true" : "false")}}}");
    public void IniciarPartida() => Enviar("{\"t\":\"iniciar\"}");

    public void EnviarPosicion(Vector3 p, float rotY)
    {
        var ci = System.Globalization.CultureInfo.InvariantCulture; // evita "1,5" en PCs en español
        Enviar(string.Format(ci, "{{\"t\":\"pos\",\"x\":{0:F3},\"y\":{1:F3},\"z\":{2:F3},\"ry\":{3:F1}}}", p.x, p.y, p.z, rotY));
    }

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
                case "bienvenido": MiId = m.id; break;
                case "sala":
                case "inicio": SalaActual = m.sala; break;
                case "fuera": SalaActual = null; break;
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
        MiId = null;
    }

    void OnApplicationQuit() => Cerrar();

    static string Json(string s) =>
        "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
}

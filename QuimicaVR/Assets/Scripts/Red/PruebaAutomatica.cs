using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;

// Modo de prueba del build real (lo usa servidor/probar_build.py). Solo se activa con
// el argumento -prueba "<pasos>", así que un jugador normal nunca lo ve.
// Por qué existe: los tests en Python hablan directo con el servidor y no pasan por
// MenuLobby ni GestorPartida, y ahí estaban los bugs de la prueba S2-3. Aquí el build
// ejecuta las mismas acciones que los botones (MenuLobby.Conectar, Entrar, SalirDeSala…)
// y escribe en el log lo que el jugador estaría viendo.
//
// Pasos separados por ";" y argumentos por "|". Ejemplo:
//   -prueba "conectar;login|ana;crear_sala;esperar_jugadores|2;esperar_listos;iniciar;reporte|inicio;fin"
// En el log salen líneas "[Prueba] REPORTE <etiqueta> {json}", "[Prueba] MARCA <texto>",
// "[Prueba] FALLO <motivo>" y "[Prueba] FIN". Las señales del orquestador llegan como
// archivos en la carpeta -senales.
public class PruebaAutomatica : MonoBehaviour
{
    public static bool Activa { get; private set; }

    const float EsperaMaxima = 20f;

    string pasos, ip = "127.0.0.1", puerto = "7777", senales = ".";
    MenuLobby menu;
    GestorPartida gestor;
    int perfilesRecibidos;
    bool fallo;

    ClienteRed Red => ClienteRed.I;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Arrancar()
    {
        var pasos = Argumento("-prueba");
        if (pasos == null) return;
        Activa = true;
        Application.targetFrameRate = 30;   // en batch no hay vsync: sin tope usa un núcleo entero
        new GameObject("PruebaAutomatica").AddComponent<PruebaAutomatica>().pasos = pasos;
    }

    IEnumerator Start()
    {
        menu = FindFirstObjectByType<MenuLobby>();
        gestor = FindFirstObjectByType<GestorPartida>();
        ip = Argumento("-ip") ?? ip;
        puerto = Argumento("-puerto") ?? puerto;
        senales = Argumento("-senales") ?? senales;
        Red.AlRecibir += m => { if (m.t == "perfil") perfilesRecibidos++; };
        yield return null;   // que MenuLobby y GestorPartida terminen su Start

        foreach (var paso in pasos.Split(';').Select(p => p.Trim()).Where(p => p != ""))
        {
            Log("PASO " + paso);
            yield return Ejecutar(paso.Split('|'));
            if (fallo) yield break;
        }
    }

    IEnumerator Ejecutar(string[] a)
    {
        string Arg(int i) => i < a.Length ? a[i] : "";
        switch (a[0])
        {
            case "conectar": menu.Conectar(ip, puerto); break;
            case "reconectar":
                // Al arrancar Docker, el proxy acepta la conexión antes de que el servidor
                // escuche y la corta enseguida: se reintenta como lo haría una persona.
                // Desde SPRINT_UI la conexión y el login son la misma pantalla: no hay un
                // cambio de pantalla que esperar, se espera a que la conexión quede arriba.
                float hasta = Time.time + EsperaMaxima;
                while (!menu.Conectar(ip, puerto) && Time.time < hasta)
                    yield return new WaitForSeconds(1.5f);
                yield return Esperar(() => Red.Conectado, "conexión al reconectar");
                break;
            case "esperar_conectado": yield return Esperar(() => Red.Conectado, "conexión con el servidor"); break;
            case "abrir_salas": menu.AbrirSalas(); break;   // botón "Ver salas" del Menú principal
            case "registro": menu.CrearPerfil(Arg(1), Arg(2), Arg(3)); break;
            case "login": menu.Entrar(Arg(1)); break;
            case "desconectar": menu.Desconectar(); break;
            case "crear_sala": menu.CrearSala(); break;
            case "unirse_codigo":
                // El código lo escribe el orquestador cuando su bot crea la sala
                var archivo = Path.Combine(senales, Arg(1));
                yield return Esperar(() => File.Exists(archivo), "señal " + Arg(1));
                if (menu.PantallaActual == "Sala")   // lo que haría una persona: salir antes de entrar a otra
                {
                    menu.SalirDeSala();
                    yield return Esperar(() => menu.PantallaActual == "Salas", "pantalla Salas");
                }
                menu.Unirse(File.ReadAllText(archivo).Trim());
                break;
            case "listo": menu.CambiarListo(); break;
            case "iniciar": menu.Iniciar(); break;
            case "salir": menu.SalirDeSala(); break;
            case "abrir_perfil":
                int antes = perfilesRecibidos;
                menu.AbrirEditarPerfil();
                yield return Esperar(() => perfilesRecibidos > antes, "respuesta a perfil_ver");
                break;
            case "guardar_perfil":
                int previos = perfilesRecibidos;
                menu.GuardarPerfil(Arg(1), Arg(2));
                yield return Esperar(() => perfilesRecibidos > previos, "respuesta a perfil_editar");
                break;
            case "volver": menu.Volver(); break;
            case "llevar": yield return Llevar(Arg(1)); break;

            // --- laberinto (S4): el build manda las mismas intenciones que con E ---
            case "dial": Red.Dial(Arg(1), float.Parse(Arg(2), System.Globalization.CultureInfo.InvariantCulture)); break;
            case "palanca": Red.Palanca(Arg(1)); break;
            case "interactuar": Red.Interactuar(Arg(1), Arg(2) == "" ? "abrir" : Arg(2)); break;
            case "montacargas": Red.Montacargas(Arg(1)); break;
            case "colocar": Colocar(Arg(1), Arg(2), Arg(3)); break;
            case "capturas": yield return Capturas(); break;
            case "empujar": yield return Empujar(Arg(1), Arg(2), Arg(3)); break;
            case "esperar_escena": yield return Esperar(() => gestor.HayEscena, "la escena del laberinto"); break;
            case "esperar_sala":
                yield return Esperar(() => Red.SalaEstadoActual != null && Red.SalaEstadoActual.sala == int.Parse(Arg(1)), "sala " + Arg(1));
                break;
            case "esperar_nivel":
                yield return Esperar(() => Red.SalaEstadoActual != null && Red.SalaEstadoActual.completada_nivel, "nivel completado");
                break;

            case "esperar": yield return new WaitForSeconds(float.Parse(Arg(1), System.Globalization.CultureInfo.InvariantCulture)); break;
            case "esperar_pantalla": yield return Esperar(() => menu.PantallaActual == Arg(1), "pantalla " + Arg(1)); break;
            case "esperar_aviso": yield return Esperar(() => (menu.Aviso ?? "").Contains(Arg(1)), "aviso '" + Arg(1) + "'"); break;
            case "esperar_aviso_global": yield return Esperar(() => menu.AvisoGlobal.Contains(Arg(1)), "aviso global '" + Arg(1) + "'"); break;
            case "esperar_jugadores":
                yield return Esperar(() => Red.SalaActual != null && Red.SalaActual.cantidad == int.Parse(Arg(1)), Arg(1) + " jugadores");
                break;
            case "esperar_listos":
                yield return Esperar(() => Red.SalaActual != null &&
                    Red.SalaActual.jugadores.All(j => j.id == Red.SalaActual.host || j.listo), "todos listos");
                break;
            case "esperar_senal":
                var senal = Path.Combine(senales, Arg(1));
                yield return Esperar(() => File.Exists(senal), "señal " + Arg(1), 60f);
                break;

            case "reporte": Log("REPORTE " + Arg(1) + " " + JsonUtility.ToJson(Estado())); break;
            case "marca": Log("MARCA " + Arg(1)); break;
            case "fin": Log("FIN"); Application.Quit(0); break;
            default: Fallar("paso desconocido: " + a[0]); break;
        }
    }

    // Agarra una esfera libre de ese elemento y la suelta en el centro del reactor.
    // Pide lo mismo que la tecla E, pero sin tener que caminar hasta la mesa.
    IEnumerator Llevar(string elemento)
    {
        var m = Red.MisionActual;
        if (m == null) { Fallar("no hay misión para llevar " + elemento); yield break; }
        var r = m.reactor;
        bool EnReactor(InfoObjeto o) => Vector2.Distance(new Vector2(o.x, o.z), new Vector2(r.x, r.z)) <= r.radio;
        var obj = m.objetos.FirstOrDefault(o => o.elemento == elemento && string.IsNullOrEmpty(o.portador) && !EnReactor(o));
        if (obj == null) { Fallar("no hay un " + elemento + " libre"); yield break; }
        string id = obj.id;
        InfoObjeto Actual() => Red.MisionActual.objetos.First(o => o.id == id);

        Red.Agarrar(id);
        yield return Esperar(() => Actual().portador == Red.MiId, "agarrar " + id);
        if (fallo) yield break;
        Red.Soltar(id, new Vector3(r.x, r.y + m.radio_objeto, r.z));
        yield return Esperar(() => string.IsNullOrEmpty(Actual().portador), "soltar " + id);
    }

    // Empuja al jugador en primera persona en una dirección del mundo durante unos
    // segundos (sin teclado). Si una puerta cerrada está en el camino, el
    // CharacterController choca con su collider y la posición no la cruza.
    void Colocar(string x, string y, string z)
    {
        var jl = gestor != null ? gestor.JugadorLocal : null;
        if (jl == null) { Fallar("no hay jugador local para colocar (¿no es laberinto?)"); return; }
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        jl.ColocarPrueba(new Vector3(float.Parse(x, ci), float.Parse(y, ci), float.Parse(z, ci)));
    }

    IEnumerator Empujar(string dx, string dz, string seg)
    {
        var jl = gestor != null ? gestor.JugadorLocal : null;
        if (jl == null) { Fallar("no hay jugador local para empujar (¿no es laberinto?)"); yield break; }
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        var dir = new Vector3(float.Parse(dx, ci), 0, float.Parse(dz, ci));
        jl.FijarEmpuje(dir);
        yield return new WaitForSeconds(float.Parse(seg, ci));
        jl.FijarEmpuje(Vector3.zero);
    }

    // ---------- Capturas del arte (pedido del PM tras la UI-2) ----------
    // Una imagen por sala y por lado, desde la cámara del jugador local (la misma Camera,
    // con su FOV y su post-proceso), para verificar el arte sin que nadie juegue. La cámara
    // se lleva a cada sala, se renderiza a una textura y vuelve a su lugar en el MISMO frame:
    // el jugador no se mueve, el servidor no se entera y la física no cambia.
    // Además de guardar el PNG, mide la imagen para que la prueba pueda fallar sola:
    // luminancia media (ni negra ni quemada), contraste (no es un color plano) y
    // proporción de magenta (el color que pone Unity cuando falta un shader).
    const int AnchoCaptura = 1280, AltoCaptura = 720;

    [Serializable] class InfoCaptura
    {
        public int sala; public string lado, nombre, archivo;
        public float luminancia, contraste, magenta;
    }
    [Serializable] class ListaCapturas
    {
        public string dispositivo;
        public int renderers, shaders_error;   // en todo el nivel: materiales con el shader de error de Unity
        public List<InfoCaptura> capturas = new List<InfoCaptura>();
    }

    IEnumerator Capturas()
    {
        if (SystemInfo.graphicsDeviceType == GraphicsDeviceType.Null)
        {
            Fallar("captura sin GPU: el build corrió con -nographics (probar_build.py lo lanza con gráficos para este escenario)");
            yield break;
        }
        var jl = gestor != null ? gestor.JugadorLocal : null;
        var gen = gestor != null ? gestor.Generador : null;
        var nivel = Red.NivelActual;
        if (jl == null || gen == null || nivel?.salas == null) { Fallar("no hay nivel del laberinto para capturar"); yield break; }
        var cam = jl.GetComponentInChildren<Camera>();
        string dir = Argumento("-capturas") ?? Path.Combine(senales, "capturas");
        Directory.CreateDirectory(dir);
        yield return new WaitForEndOfFrame();   // el nivel ya se dibujó una vez

        var lista = new ListaCapturas { dispositivo = SystemInfo.graphicsDeviceType + " · " + SystemInfo.graphicsDeviceName };
        foreach (var r in gen.Raiz.GetComponentsInChildren<Renderer>())
        {
            lista.renderers++;
            if (r.sharedMaterial == null || r.sharedMaterial.shader == null || !r.sharedMaterial.shader.isSupported
                || r.sharedMaterial.shader.name == "Hidden/InternalErrorShader") lista.shaders_error++;
        }

        var rt = new RenderTexture(AnchoCaptura, AltoCaptura, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 1 };
        var tex = new Texture2D(AnchoCaptura, AltoCaptura, TextureFormat.RGB24, false);
        foreach (var sala in nivel.salas)
            foreach (var lado in new[] { "wizard", "player" })
            {
                var consolas = lado == "wizard" ? sala.consolas?.wizard : sala.consolas?.player;
                if (consolas == null || consolas.Count == 0 || consolas[0].pos.Count < 2) continue;
                PuntoDeVista(gen, lado, consolas[0].pos, out var ojo, out var mira);
                Renderizar(cam, rt, tex, ojo, Quaternion.LookRotation(mira - ojo));
                var info = Medir(tex);
                info.sala = sala.n; info.lado = lado; info.nombre = sala.nombre;
                info.archivo = Path.GetFullPath(Path.Combine(dir, $"sala{sala.n}_{lado}.png"));
                File.WriteAllBytes(info.archivo, tex.EncodeToPNG());
                lista.capturas.Add(info);
            }
        rt.Release();
        Destroy(rt); Destroy(tex);
        Log("REPORTE capturas " + JsonUtility.ToJson(lista));
    }

    // Cada sala es un cuarto de 3×3 celdas entre paredes cada 4 columnas (la grilla del
    // JSON); la consola de cada lado está adentro. La cámara se para a la altura de los
    // ojos (1,6 m) en la esquina del fondo opuesta a la consola y mira hacia ella: así entran
    // las paredes, el piso, la consola, la palanca y el montacargas en una sola imagen.
    static void PuntoDeVista(GeneradorNivel gen, string lado, List<int> consola, out Vector3 ojo, out Vector3 mira)
    {
        int col = consola[0], fila = consola[1];
        int c0 = (col - 1) / 4 * 4 + 1;               // primera columna libre del cuarto
        int colOjo = col == c0 ? c0 + 2 : c0;
        int filaOjo = fila <= 1 ? 3 : 1;
        ojo = gen.CentroCelda(lado, colOjo, filaOjo, 1.6f);
        mira = gen.CentroCelda(lado, col, fila, 1.0f);
    }

    static void Renderizar(Camera cam, RenderTexture rt, Texture2D tex, Vector3 pos, Quaternion rot)
    {
        var t = cam.transform;
        Vector3 posAntes = t.position; Quaternion rotAntes = t.rotation;
        t.SetPositionAndRotation(pos, rot);
        // URP renderiza una cámara a una textura con un pedido estándar; Camera.Render
        // queda como respaldo por si el pipeline no lo acepta.
        var pedido = new RenderPipeline.StandardRequest { destination = rt };
        if (RenderPipeline.SupportsRenderRequest(cam, pedido)) RenderPipeline.SubmitRenderRequest(cam, pedido);
        else { var antes = cam.targetTexture; cam.targetTexture = rt; cam.Render(); cam.targetTexture = antes; }
        var activa = RenderTexture.active;
        RenderTexture.active = rt;
        tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
        tex.Apply();
        RenderTexture.active = activa;
        t.SetPositionAndRotation(posAntes, rotAntes);
    }

    static InfoCaptura Medir(Texture2D tex)
    {
        var px = tex.GetPixels32();
        double suma = 0, suma2 = 0; int magenta = 0;
        foreach (var c in px)
        {
            double l = (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255.0;
            suma += l; suma2 += l * l;
            if (c.r > 230 && c.g < 30 && c.b > 230) magenta++;
        }
        double media = suma / px.Length;
        return new InfoCaptura
        {
            luminancia = (float)media,
            contraste = (float)Math.Sqrt(Math.Max(0, suma2 / px.Length - media * media)),
            magenta = (float)magenta / px.Length,
        };
    }

    IEnumerator Esperar(Func<bool> condicion, string que, float maximo = EsperaMaxima)
    {
        float hasta = Time.time + maximo;
        while (!condicion())
        {
            if (Time.time > hasta) { Fallar("tiempo agotado esperando " + que); yield break; }
            yield return null;
        }
    }

    void Fallar(string motivo)
    {
        fallo = true;
        Log("REPORTE fallo " + JsonUtility.ToJson(Estado()));
        Log("FALLO " + motivo);
        Application.Quit(1);
    }

    [Serializable] class PosRemota { public string id; public float x, z; }

    [Serializable] class EstadoPrueba
    {
        public string pantalla, aviso, aviso_global, mi_id, usuario, nombre, sala, host, rol, estado_sala;
        public bool escena, local;
        public float local_x, local_z;
        public List<string> jugadores_sala = new List<string>();
        public List<PosRemota> remotos = new List<PosRemota>();
        public int completadas = -1, historial = -1;
        public bool mision_completada;
        public int sala_lab = -1;          // laberinto: sala actual (1..5)
        public bool nivel_completado;      // laberinto: el portón final abierto
    }

    EstadoPrueba Estado()
    {
        var e = new EstadoPrueba
        {
            pantalla = menu.PantallaActual, aviso = menu.Aviso, aviso_global = menu.AvisoGlobal, mi_id = Red.MiId,
            usuario = Red.MiPerfil?.usuario, nombre = Red.MiPerfil?.nombre,
            sala = Red.SalaActual?.id, host = Red.SalaActual?.host, estado_sala = Red.SalaActual?.estado,
            rol = Red.SalaActual != null ? Red.MiRol : null,
            escena = gestor.HayEscena, mision_completada = Red.EstadoActual?.completada ?? false,
            sala_lab = Red.SalaEstadoActual?.sala ?? -1,
            nivel_completado = Red.SalaEstadoActual?.completada_nivel ?? false,
        };
        if (gestor.PosicionLocal is Vector3 p) { e.local = true; e.local_x = p.x; e.local_z = p.z; }
        if (Red.SalaActual != null) e.jugadores_sala = Red.SalaActual.jugadores.Select(j => j.id).ToList();
        foreach (var id in gestor.IdsRemotos)
        {
            var d = gestor.DestinoRemoto(id);
            e.remotos.Add(new PosRemota { id = id, x = d.x, z = d.z });
        }
        var pr = Red.MiPerfil?.progreso;
        if (pr != null) { e.completadas = pr.completadas; e.historial = pr.historial.Count; }
        return e;
    }

    static void Log(string s) => Debug.Log("[Prueba] " + s);

    static string Argumento(string nombre)
    {
        var args = Environment.GetCommandLineArgs();
        int i = Array.IndexOf(args, nombre);
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : null;
    }
}

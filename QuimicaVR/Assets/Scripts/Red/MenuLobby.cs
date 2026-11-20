using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.UIElements;

// Estado del menú y acciones (SPRINT_UI §2): qué pantalla se ve y qué pasa al tocar un
// botón. Las pantallas de UI Toolkit (Scripts/UI/Pantalla*.cs) solo leen este estado y
// llaman a estas acciones; PruebaAutomatica llama a las MISMAS, así la prueba del build
// recorre el mismo código que un clic.
// Pantallas: Login -> Menú -> Salas -> Sala -> Partida. Desde el Menú, "Perfil" abre Mi perfil.
public class MenuLobby : MonoBehaviour
{
    enum Pantalla { Login, Menu, Salas, Sala, Perfil, Partida }
    Pantalla pantalla = Pantalla.Login;

    string ip = "127.0.0.1", puerto = "7777";
    string nombreSala = "", aviso = "", info = "";
    string errorConexion = "";   // el último fallo al conectar o la caída: va en el chip del Login
    int maximo = 4;
    bool listo;
    float proximoRefresco;
    Mensaje ultimaLista;

    // Perfil: pestaña 0 = entrar, 1 = crear cuenta. Los mismos campos sirven para editar.
    int pestana;
    string usuario = "", nombrePerfil = "", colorPerfil = ClienteRed.Paleta[0];
    bool guardando;   // para distinguir la respuesta a "Guardar" de la de "perfil_ver"

    // HUD: los mensajes del reactor y los errores se muestran unos segundos
    float tMensaje = -99, tAviso = -99;
    // Aviso global del panel web: banner arriba durante 6 s, en cualquier pantalla
    const float DuracionAvisoGlobal = 6f;
    string avisoGlobal = "";
    float tAvisoGlobal = -99;
    bool mensajeEsError;
    int erroresPrevios;

    ClienteRed Red => ClienteRed.I;

    // Las mismas reglas que server.py. Aquí solo evitan un viaje al servidor:
    // la regla de verdad la impone el servidor.
    static readonly Regex FormatoUsuario = new Regex(@"^[a-z0-9_]{4,16}$");

    // ---------- Vista (UI Toolkit) ----------
    readonly Dictionary<Pantalla, ControladorPantalla> vistas = new Dictionary<Pantalla, ControladorPantalla>();
    Label banner;
    Pantalla? pantallaDibujada;
    bool sucio = true;          // algo cambió: refrescar la pantalla visible en el próximo Update
    float proximoRepintado;

    void Start()
    {
        ip = PlayerPrefs.GetString("ip", "127.0.0.1");
        puerto = PlayerPrefs.GetString("puerto", "7777");
        // Se recuerda el último usuario para no reescribirlo en cada arranque
        usuario = PlayerPrefs.GetString("usuario", "");
        pestana = usuario == "" ? 1 : 0;

        Red.AlRecibir += m =>
        {
            sucio = true;
            if (m.t == "salas") ultimaLista = m;
            // "sala" llega cada vez que algo cambia (alguien entra, sale, marca listo o edita
            // su perfil). Solo lleva a la pantalla de la sala desde el lobby, al crear o
            // unirse: antes también sacaba de la partida a todos cuando salía un Player (B2).
            if (m.t == "sala" && pantalla == Pantalla.Salas) { pantalla = Pantalla.Sala; aviso = ""; }
            if (m.t == "salio" && pantalla == Pantalla.Partida)
            {
                // SalaActual todavía es la de antes: el "sala" sin ese jugador llega después
                var quien = Red.SalaActual?.jugadores.Find(j => j.id == m.id);
                aviso = $"{quien?.nombre ?? "Un jugador"} salió de la sala";
                tAviso = Time.time;
            }
            if (m.t == "fuera")
            {
                // Con msg, la sala se cerró ("El Wizard salió, la sala se cerró"); sin msg, salí yo
                pantalla = Pantalla.Salas; listo = false; Red.ListarSalas();
                aviso = m.msg ?? "";
                tAviso = Time.time;
            }
            if (m.t == "sala_cerrada")
            {
                // Lo cerró un administrador desde el panel: sigue conectado, vuelve al lobby
                pantalla = Pantalla.Salas; listo = false; Red.ListarSalas();
                aviso = m.motivo ?? "Un administrador cerró la sala";
                tAviso = Time.time;
            }
            if (m.t == "expulsado")
            {
                pantalla = Pantalla.Login; listo = false;
                aviso = "Fuiste expulsado por un administrador. Motivo: " + (m.motivo ?? "sin motivo");
                tAviso = Time.time;
            }
            if (m.t == "aviso") { avisoGlobal = m.msg ?? ""; tAvisoGlobal = Time.time; }
            if (m.t == "clase_unida") { aviso = ""; info = $"Te uniste a la clase {m.nombre} ({m.docente})"; }
            if (m.t == "inicio") { pantalla = Pantalla.Partida; tMensaje = -99; erroresPrevios = 0; }
            if (m.t == "perfil") AlRecibirPerfil(m.perfil);
            if (m.t == "estado")
            {
                tMensaje = Time.time;
                mensajeEsError = m.estado.errores > erroresPrevios;
                erroresPrevios = m.estado.errores;
            }
        };
        Red.AlError += e =>
        {
            // Sin conexión, el error es del intento de conectar: va al chip de estado del Login
            if (!Red.Conectado) errorConexion = e;
            aviso = e; info = ""; guardando = false; tAviso = Time.time; sucio = true;
        };
        Red.AlDesconectar += () =>
        {
            pantalla = Pantalla.Login;
            aviso = errorConexion = "Se perdió la conexión con el servidor";
            sucio = true;
        };

        CrearVista();
    }

    // Un UIDocument creado por código con el PanelSettings que genera ConfigurarUI
    // (escala con la pantalla, referencia 1280×720). Así la escena no cambia: el menú
    // sigue siendo solo este componente en el objeto "Red".
    void CrearVista()
    {
        var panel = Resources.Load<PanelSettings>("UI/PanelUI");
        if (panel == null)
        {
            Debug.LogError("[Quimica] Falta Resources/UI/PanelUI: ejecuta Quimica/4. Configurar UI");
            return;
        }
        var doc = gameObject.AddComponent<UIDocument>();
        doc.panelSettings = panel;

        var raiz = new VisualElement { name = "raiz", pickingMode = PickingMode.Ignore };
        raiz.AddToClassList("raiz");
        raiz.styleSheets.Add(Resources.Load<StyleSheet>("UI/Estilos"));
        doc.rootVisualElement.Add(raiz);

        vistas[Pantalla.Login] = new PantallaLogin(this, Cargar(raiz, "Login"));
        vistas[Pantalla.Menu] = new PantallaMenu(this, Cargar(raiz, "Menu"));
        vistas[Pantalla.Salas] = new PantallaSalas(this, Cargar(raiz, "Salas"));
        vistas[Pantalla.Sala] = new PantallaLobby(this, Cargar(raiz, "Lobby"));
        vistas[Pantalla.Perfil] = new PantallaPerfil(this, Cargar(raiz, "Perfil"));

        // El banner va al final para quedar encima de cualquier pantalla
        var franja = new VisualElement { pickingMode = PickingMode.Ignore };
        franja.AddToClassList("banner");
        banner = new Label { pickingMode = PickingMode.Ignore };
        franja.Add(banner);
        raiz.Add(franja);

        foreach (var v in vistas.Values) Ui.AplicarGaps(v.Raiz);
    }

    static VisualElement Cargar(VisualElement raiz, string uxml)
    {
        var arbol = Resources.Load<VisualTreeAsset>("UI/" + uxml);
        var cont = arbol.Instantiate();
        cont.AddToClassList("pantalla-cont");
        cont.pickingMode = PickingMode.Ignore;
        raiz.Add(cont);
        Ui.Mostrar(cont, false);
        return cont;
    }

    void AlRecibirPerfil(InfoPerfil p)
    {
        aviso = "";
        if (pantalla == Pantalla.Login)
        {
            if (!PruebaAutomatica.Activa) PlayerPrefs.SetString("usuario", p.usuario);
            pantalla = Pantalla.Menu;
        }
        else if (pantalla == Pantalla.Perfil && guardando)
        {
            guardando = false;
            info = "Perfil guardado";
        }
    }

    void Update()
    {
        if (pantalla == Pantalla.Partida && Input.GetKeyDown(KeyCode.Escape)) SalirDeSala();
        if (pantalla == Pantalla.Salas && Time.time > proximoRefresco)
        {
            proximoRefresco = Time.time + 2f;   // refresco automático de la lista
            Red.ListarSalas();
        }
        ActualizarVista();
    }

    void ActualizarVista()
    {
        if (vistas.Count == 0) return;
        if (pantallaDibujada != pantalla)
        {
            foreach (var par in vistas) Ui.Mostrar(par.Value.Raiz, par.Key == pantalla);
            if (vistas.TryGetValue(pantalla, out var nueva)) nueva.AlMostrar();
            pantallaDibujada = pantalla;
            sucio = true;
        }
        // Además de los cambios avisados, un repintado lento: la conexión puede caerse o
        // un aviso vencer sin que llegue ningún mensaje.
        if (sucio || Time.time > proximoRepintado)
        {
            sucio = false;
            proximoRepintado = Time.time + 0.5f;
            if (vistas.TryGetValue(pantalla, out var v)) v.Refrescar();
        }
        string global = AvisoGlobal;
        banner.text = global == "" ? "" : "AVISO: " + global;
        Ui.Mostrar(banner, global != "");
    }

    // ---------- HUD en IMGUI: pasa a UI Toolkit en la UI-3 ----------
    void OnGUI()
    {
        if (pantalla != Pantalla.Partida) return;
        var fuente = GestorPartida.FuenteBase();   // la misma de los textos 3D: tiene "_" y "₂"
        if (fuente != null) GUI.skin.font = fuente;
        GUI.skin.label.fontSize = 18;
        Hud();
    }

    void Hud()
    {
        var estado = Red.EstadoActual;
        if (estado != null && !string.IsNullOrEmpty(estado.mensaje) && (estado.completada || Time.time - tMensaje < 3f))
        {
            var centro = new GUIStyle(Rico()) { alignment = TextAnchor.MiddleCenter };
            GUI.Label(new Rect(0, Screen.height * .2f, Screen.width, 120), $"<b><size=28>{estado.mensaje}</size></b>", centro);
        }
        if (!string.IsNullOrEmpty(aviso) && Time.time - tAviso < 3f)
        {
            var abajo = new GUIStyle(Rico()) { alignment = TextAnchor.MiddleCenter };
            GUI.Label(new Rect(0, Screen.height - 60, Screen.width, 40), $"<color=#ffb060>{aviso}</color>", abajo);
        }
    }

    static GUIStyle Rico() => new GUIStyle(GUI.skin.label) { richText = true, wordWrap = true };

    // ---------- Estado que leen las pantallas ----------
    public string PantallaActual => pantalla.ToString();
    public string Aviso => aviso;
    public string Info => info;
    public string ErrorConexion => errorConexion;
    public string AvisoGlobal => Time.time - tAvisoGlobal < DuracionAvisoGlobal ? avisoGlobal : "";
    public string Ip => ip;
    public string Puerto => puerto;
    public string Usuario => usuario;
    public string NombrePerfil => nombrePerfil;
    public int Pestana => pestana;
    public string ColorPerfil { get => colorPerfil; set => colorPerfil = value; }
    public string NombreSala { get => nombreSala; set => nombreSala = value ?? ""; }
    public int Maximo { get => maximo; set => maximo = Mathf.Clamp(value, 2, 8); }   // mismo rango que el servidor
    public List<InfoSala> Salas => ultimaLista?.lista ?? new List<InfoSala>();

    // ---------- Acciones (las llaman los botones y también PruebaAutomatica) ----------
    public void CambiarPestana(int p)
    {
        if (p != pestana) aviso = "";
        pestana = p;
        sucio = true;
    }

    public void FijarServidor(string ip, string puerto)
    {
        this.ip = (ip ?? "").Trim();
        this.puerto = (puerto ?? "").Trim();
    }

    // Conecta sin salir del Login: el chip de abajo pasa a "conectado" o muestra el error
    public bool Conectar(string ip, string puerto)
    {
        FijarServidor(ip, puerto);
        if (!PruebaAutomatica.Activa) { PlayerPrefs.SetString("ip", this.ip); PlayerPrefs.SetString("puerto", this.puerto); }
        aviso = errorConexion = "";
        sucio = true;
        bool ok = Red.Conectar(this.ip, int.TryParse(this.puerto, out var p) ? p : 7777);
        // Si falla, ClienteRed ya avisó por AlError (que dejó el texto en aviso); puede
        // pasar con el socket todavía abierto (el servidor no respondió al ping), así que
        // se marca aquí y no se depende de Conectado.
        if (!ok) errorConexion = aviso;
        return ok;
    }

    // El Login unió la pantalla de conexión con la de perfil: si todavía no hay
    // conexión, Entrar / Crear cuenta conectan primero con la IP y el puerto escritos.
    bool AsegurarConexion() => Red.Conectado || Conectar(ip, puerto);

    public void Entrar(string usuario)
    {
        this.usuario = (usuario ?? "").ToLowerInvariant();
        if (UsuarioValido() && AsegurarConexion()) Red.Login(this.usuario.Trim());
        sucio = true;
    }

    public void CrearPerfil(string usuario, string nombre, string color)
    {
        this.usuario = (usuario ?? "").ToLowerInvariant();
        nombrePerfil = nombre ?? "";
        colorPerfil = color;
        if (UsuarioValido() && NombreValido() && AsegurarConexion())
            Red.Registrar(this.usuario.Trim(), nombrePerfil.Trim(), colorPerfil);
        sucio = true;
    }

    bool UsuarioValido()
    {
        if (FormatoUsuario.IsMatch(usuario.Trim())) return true;
        aviso = "Usuario inválido: de 4 a 16 caracteres, solo letras, números y _";
        return false;
    }

    bool NombreValido()
    {
        int n = nombrePerfil.Trim().Length;
        if (n >= 1 && n <= 20) return true;
        aviso = "El nombre visible debe tener de 1 a 20 caracteres";
        return false;
    }

    // "Cerrar sesión" en el menú y el botón de desconectar: vuelve al Login
    public void Desconectar()
    {
        Red.Cerrar();
        pantalla = Pantalla.Login;
        aviso = errorConexion = "";
        sucio = true;
    }

    public void AbrirSalas()
    {
        // Nombre sugerido como en el diseño ("Sala de Jugador 1"); se puede cambiar
        if (nombreSala == "" && Red.MiPerfil != null) nombreSala = "Sala de " + Red.MiPerfil.nombre;
        pantalla = Pantalla.Salas;
        aviso = "";
        proximoRefresco = 0;
        sucio = true;
    }

    public void VolverAlMenu()
    {
        pantalla = Pantalla.Menu;
        aviso = "";
        sucio = true;
    }

    public void AbrirEditarPerfil()
    {
        var p = Red.MiPerfil;
        if (p == null) return;
        nombrePerfil = p.nombre;
        colorPerfil = p.color;
        aviso = info = "";
        guardando = false;
        pantalla = Pantalla.Perfil;
        sucio = true;
        Red.VerPerfil();   // el progreso pudo cambiar desde el login
    }

    public void GuardarPerfil(string nombre, string color)
    {
        nombrePerfil = nombre ?? "";
        colorPerfil = color;
        sucio = true;
        if (!NombreValido()) return;
        info = "";
        guardando = true;
        Red.EditarPerfil(nombrePerfil.Trim(), colorPerfil);
    }

    public void Volver()
    {
        aviso = info = "";
        pantalla = Red.SalaActual != null ? Pantalla.Sala : Pantalla.Menu;
        proximoRefresco = 0;
        sucio = true;
    }

    public void CrearSala()
    {
        if (nombreSala.Trim() == "") nombreSala = "Sala de " + (Red.MiPerfil?.nombre ?? "laboratorio");
        Red.CrearSala(nombreSala.Trim(), maximo);
    }

    // Botón "Actualizar": pide la lista ya y reinicia el refresco automático de 2 s
    public void ActualizarSalas()
    {
        proximoRefresco = Time.time + 2f;
        Red.ListarSalas();
    }
    public void Unirse(string codigo) => Red.Unirse((codigo ?? "").Trim().ToUpperInvariant());
    public void Iniciar() => Red.IniciarPartida();

    // ---------- Rol docente (revisión 20/11) ----------
    public void UnirseClase(string codigo)
    {
        // Mismo formato que el servidor: 8 caracteres; espacios y minúsculas se toleran
        string c = (codigo ?? "").Replace(" ", "").Trim().ToUpperInvariant();
        sucio = true;
        if (c.Length != 8) { aviso = "El código de clase tiene 8 caracteres"; info = ""; tAviso = Time.time; return; }
        aviso = info = "";
        Red.UnirseClase(c);
    }

    // Botón del anfitrión en el Lobby: pasa al siguiente reto de la lista (y después a "sin reto")
    public void CambiarReto()
    {
        var s = Red.SalaActual;
        if (s == null) return;
        var ids = new List<int> { 0 };
        ids.AddRange(s.retos.ConvertAll(r => r.id));
        int i = ids.IndexOf(s.reto);
        Red.ElegirReto(ids[(i + 1) % ids.Count]);
    }

    public void ElegirReto(int id) => Red.ElegirReto(id);

    public void CambiarListo()
    {
        listo = !listo;
        Red.MarcarListo(listo);
        sucio = true;
    }

    // ESC en la partida o "Salir de la sala" en la sala
    public void SalirDeSala()
    {
        Red.SalirSala();
        if (pantalla != Pantalla.Partida) return;
        var gestor = FindFirstObjectByType<GestorPartida>();
        if (gestor != null) gestor.Terminar();
    }

    // El servidor manda la fecha en UTC (ISO 8601); se muestra en la hora de esta PC
    public static string Fecha(string iso) =>
        DateTime.TryParse(iso, CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal, out var f)
            ? f.ToLocalTime().ToString("dd/MM/yyyy HH:mm", CultureInfo.InvariantCulture)
            : iso;

    public static string Segundos(float s) => s.ToString("0.0", CultureInfo.InvariantCulture) + " s";
}

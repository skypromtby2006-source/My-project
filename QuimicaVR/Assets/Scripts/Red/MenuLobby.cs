using System;
using System.Globalization;
using System.Text.RegularExpressions;
using UnityEngine;

// Menú completo con IMGUI: no hace falta armar Canvas ni prefabs.
// Pantallas: Conexión -> Perfil (iniciar sesión / crear) -> Lista de salas -> Dentro de la sala -> Partida
// Desde la lista o desde la sala, "Mi perfil" abre EditarPerfil y "Volver" regresa.
public class MenuLobby : MonoBehaviour
{
    enum Pantalla { Conexion, Perfil, Salas, Sala, EditarPerfil, Partida }
    Pantalla pantalla = Pantalla.Conexion;

    string ip = "127.0.0.1", puerto = "7777";
    string nombreSala = "Laboratorio 1", codigo = "", aviso = "", info = "";
    int maximo = 4;
    bool listo;
    float proximoRefresco;
    Vector2 scroll;
    Mensaje ultimaLista;

    // Perfil: pestaña 0 = iniciar sesión, 1 = crear. Los mismos campos sirven para editar.
    int pestana;
    string usuario = "", nombrePerfil = "", colorPerfil = ClienteRed.Paleta[0];
    bool guardando;   // para distinguir la respuesta a "Guardar" de la de "perfil_ver"

    // HUD: los mensajes del reactor y los errores se muestran unos segundos
    float tMensaje = -99, tAviso = -99;
    bool mensajeEsError;
    int erroresPrevios;

    ClienteRed Red => ClienteRed.I;

    // Las mismas reglas que server.py. Aquí solo evitan un viaje al servidor:
    // la regla de verdad la impone el servidor.
    static readonly Regex FormatoUsuario = new Regex(@"^[a-z0-9_]{3,16}$");

    void Start()
    {
        ip = PlayerPrefs.GetString("ip", "127.0.0.1");
        // Se recuerda el último usuario para no reescribirlo en cada arranque
        usuario = PlayerPrefs.GetString("usuario", "");
        pestana = usuario == "" ? 1 : 0;

        Red.AlRecibir += m =>
        {
            if (m.t == "salas") ultimaLista = m;
            // Al editar el perfil dentro de una sala, el servidor reenvía "sala": no hay
            // que sacar al jugador de la pantalla de edición por eso.
            if (m.t == "sala" && pantalla != Pantalla.EditarPerfil) { pantalla = Pantalla.Sala; aviso = ""; }
            if (m.t == "fuera") { pantalla = Pantalla.Salas; listo = false; Red.ListarSalas(); }
            if (m.t == "inicio") { pantalla = Pantalla.Partida; tMensaje = -99; erroresPrevios = 0; }
            if (m.t == "perfil") AlRecibirPerfil(m.perfil);
            if (m.t == "estado")
            {
                tMensaje = Time.time;
                mensajeEsError = m.estado.errores > erroresPrevios;
                erroresPrevios = m.estado.errores;
            }
        };
        Red.AlError += e => { aviso = e; info = ""; guardando = false; tAviso = Time.time; };
        Red.AlDesconectar += () => { pantalla = Pantalla.Conexion; aviso = "Se perdió la conexión con el servidor"; };
    }

    void AlRecibirPerfil(InfoPerfil p)
    {
        aviso = "";
        if (pantalla == Pantalla.Perfil)
        {
            PlayerPrefs.SetString("usuario", p.usuario);
            pantalla = Pantalla.Salas;
            proximoRefresco = 0;
        }
        else if (pantalla == Pantalla.EditarPerfil && guardando)
        {
            guardando = false;
            info = "Perfil guardado";
        }
    }

    void Update()
    {
        if (pantalla == Pantalla.Partida && Input.GetKeyDown(KeyCode.Escape))
        {
            Red.SalirSala();
            var gestor = FindFirstObjectByType<GestorPartida>();
            if (gestor != null) gestor.Terminar();
        }
        if (pantalla == Pantalla.Salas && Time.time > proximoRefresco)
        {
            proximoRefresco = Time.time + 2f;   // refresco automático de la lista
            Red.ListarSalas();
        }
    }

    void OnGUI()
    {
        GUI.skin.label.fontSize = GUI.skin.button.fontSize = GUI.skin.textField.fontSize = 18;
        if (pantalla == Pantalla.Partida) { Hud(); return; }

        GUILayout.BeginArea(new Rect(Screen.width / 2f - 260, 40, 520, Screen.height - 80), GUI.skin.box);
        GUILayout.Label("<b><size=26>Juego de Química — Demo Multijugador</size></b>", Rico());

        // Los errores van arriba para que se vean sin bajar la vista
        if (!string.IsNullOrEmpty(aviso)) GUILayout.Label($"<color=#ff7070>{aviso}</color>", Rico());
        if (!string.IsNullOrEmpty(info)) GUILayout.Label($"<color=#7fff7f>{info}</color>", Rico());
        GUILayout.Space(10);

        switch (pantalla)
        {
            case Pantalla.Conexion: Conexion(); break;
            case Pantalla.Perfil: Perfil(); break;
            case Pantalla.Salas: Salas(); break;
            case Pantalla.Sala: Sala(); break;
            case Pantalla.EditarPerfil: EditarPerfil(); break;
        }
        GUILayout.EndArea();
    }

    void Conexion()
    {
        ip = Campo("IP del servidor", ip);
        puerto = Campo("Puerto", puerto);
        GUILayout.Space(10);
        if (GUILayout.Button("Conectar", GUILayout.Height(45)))
        {
            PlayerPrefs.SetString("ip", ip);
            aviso = "";
            if (Red.Conectar(ip.Trim(), int.TryParse(puerto, out var p) ? p : 7777)) pantalla = Pantalla.Perfil;
        }
        GUILayout.Label("<size=14>Local: 127.0.0.1 · En otra PC de la red: la IP que muestra instalar_servidor.bat</size>", Rico());
    }

    // ---------- Ventana 1: iniciar sesión / crear perfil ----------
    void Perfil()
    {
        int antes = pestana;
        pestana = GUILayout.Toolbar(pestana, new[] { "Iniciar sesión", "Crear perfil" }, GUILayout.Height(36));
        if (pestana != antes) aviso = "";
        GUILayout.Space(10);

        usuario = Campo("Usuario", usuario).ToLowerInvariant();
        if (pestana == 0)
        {
            GUILayout.Space(10);
            if (GUILayout.Button("Entrar", GUILayout.Height(45)) && UsuarioValido()) Red.Login(usuario.Trim());
        }
        else
        {
            GUILayout.Label("<size=14>De 3 a 16 caracteres: letras, números y _. No se puede cambiar después.</size>", Rico());
            nombrePerfil = Campo("Nombre visible", nombrePerfil);
            SelectorColor();
            GUILayout.Space(10);
            if (GUILayout.Button("Crear", GUILayout.Height(45)) && UsuarioValido() && NombreValido())
                Red.Registrar(usuario.Trim(), nombrePerfil.Trim(), colorPerfil);
        }

        GUILayout.Space(15);
        if (GUILayout.Button("Desconectar")) { Red.Cerrar(); pantalla = Pantalla.Conexion; aviso = ""; }
    }

    bool UsuarioValido()
    {
        if (FormatoUsuario.IsMatch(usuario.Trim())) return true;
        aviso = "Usuario inválido: de 3 a 16 caracteres, solo letras, números y _";
        return false;
    }

    bool NombreValido()
    {
        int n = nombrePerfil.Trim().Length;
        if (n >= 1 && n <= 20) return true;
        aviso = "El nombre visible debe tener de 1 a 20 caracteres";
        return false;
    }

    // 8 cuadrados del color de la paleta; el elegido lleva un borde blanco y negro
    // (las dos capas para que el borde también se vea alrededor del blanco).
    void SelectorColor()
    {
        GUILayout.BeginHorizontal();
        GUILayout.Label("Color", GUILayout.Width(170));
        foreach (var hex in ClienteRed.Paleta)
        {
            var r = GUILayoutUtility.GetRect(34, 34, GUILayout.Width(34), GUILayout.Height(34));
            ColorUtility.TryParseHtmlString(hex, out var c);
            if (hex == colorPerfil)
            {
                GUI.DrawTexture(r, Texture2D.whiteTexture);
                GUI.DrawTexture(Encoger(r, 3), Texture2D.whiteTexture, ScaleMode.StretchToFill, false, 0, Color.black, 0, 0);
                GUI.DrawTexture(Encoger(r, 6), Texture2D.whiteTexture, ScaleMode.StretchToFill, false, 0, c, 0, 0);
            }
            else GUI.DrawTexture(Encoger(r, 4), Texture2D.whiteTexture, ScaleMode.StretchToFill, false, 0, c, 0, 0);
            if (GUI.Button(r, GUIContent.none, GUIStyle.none)) colorPerfil = hex;
        }
        GUILayout.FlexibleSpace();
        GUILayout.EndHorizontal();
    }

    static Rect Encoger(Rect r, float d) => new Rect(r.x + d, r.y + d, r.width - 2 * d, r.height - 2 * d);

    // ---------- Ventana 2: editar perfil + progreso ----------
    void AbrirEditarPerfil()
    {
        var p = Red.MiPerfil;
        nombrePerfil = p.nombre;
        colorPerfil = p.color;
        aviso = info = "";
        guardando = false;
        pantalla = Pantalla.EditarPerfil;
        Red.VerPerfil();   // el progreso pudo cambiar desde el login
    }

    void EditarPerfil()
    {
        var p = Red.MiPerfil;
        if (p == null) return;
        GUILayout.Label("<b>Mi perfil</b>", Rico());
        GUILayout.BeginHorizontal();
        GUILayout.Label("Usuario", GUILayout.Width(170));
        GUILayout.Label($"<b>{p.usuario}</b>  <size=14><color=#aaaaaa>(no se puede cambiar)</color></size>", Rico());
        GUILayout.EndHorizontal();
        nombrePerfil = Campo("Nombre visible", nombrePerfil);
        SelectorColor();

        GUILayout.Space(8);
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Guardar", GUILayout.Height(40)) && NombreValido())
        {
            info = "";
            guardando = true;
            Red.EditarPerfil(nombrePerfil.Trim(), colorPerfil);
        }
        if (GUILayout.Button("Volver", GUILayout.Height(40)))
        {
            aviso = info = "";
            pantalla = Red.SalaActual != null ? Pantalla.Sala : Pantalla.Salas;
            proximoRefresco = 0;
        }
        GUILayout.EndHorizontal();

        GUILayout.Space(15);
        GUILayout.Label("<b>Progreso</b>", Rico());
        var pr = p.progreso;
        if (pr == null) return;
        GUILayout.Label($"Misiones completadas: <b>{pr.completadas}</b>", Rico());
        GUILayout.Label("Mejor tiempo en \"Sintetizar agua\": <b>" +
                        (pr.completadas > 0 ? Segundos(pr.mejor_tiempo_s) : "—") + "</b>", Rico());
        GUILayout.Label($"Errores totales como Player: <b>{pr.errores_totales}</b>", Rico());
        GUILayout.Space(5);
        GUILayout.Label("<b>Últimas misiones</b>", Rico());
        if (pr.historial.Count == 0) GUILayout.Label("<color=#aaaaaa>Todavía no completaste ninguna.</color>", Rico());
        foreach (var h in pr.historial)
            GUILayout.Label($"<size=16>{Fecha(h.fecha)} · {Segundos(h.duracion_s)} · {h.errores} errores</size>", Rico());
    }

    // El servidor manda la fecha en UTC (ISO 8601); se muestra en la hora de esta PC
    static string Fecha(string iso) =>
        DateTime.TryParse(iso, CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal, out var f)
            ? f.ToLocalTime().ToString("dd/MM/yyyy HH:mm", CultureInfo.InvariantCulture)
            : iso;

    static string Segundos(float s) => s.ToString("0.0", CultureInfo.InvariantCulture) + " s";

    static string ConColor(string texto, string hex) => $"<color={hex}>{texto}</color>";

    // ---------- Lobby ----------
    void Salas()
    {
        var p = Red.MiPerfil;
        GUILayout.BeginHorizontal();
        if (p != null) GUILayout.Label($"Hola, <b>{ConColor(p.nombre, p.color)}</b> <size=14>({p.usuario})</size>", Rico());
        if (GUILayout.Button("Mi perfil", GUILayout.Width(130))) AbrirEditarPerfil();
        GUILayout.EndHorizontal();
        GUILayout.Space(10);

        GUILayout.Label("<b>Crear sala</b>", Rico());
        nombreSala = Campo("Nombre", nombreSala);
        GUILayout.BeginHorizontal();
        GUILayout.Label($"Máx. jugadores: {maximo}", GUILayout.Width(200));
        maximo = Mathf.RoundToInt(GUILayout.HorizontalSlider(maximo, 2, 8));
        GUILayout.EndHorizontal();
        if (GUILayout.Button("Crear sala", GUILayout.Height(40))) Red.CrearSala(nombreSala, maximo);

        GUILayout.Space(15);
        GUILayout.Label("<b>Unirse por código</b>", Rico());
        GUILayout.BeginHorizontal();
        codigo = GUILayout.TextField(codigo.ToUpper(), 4, GUILayout.Width(120));
        if (GUILayout.Button("Unirse")) Red.Unirse(codigo);
        GUILayout.EndHorizontal();

        GUILayout.Space(15);
        GUILayout.Label("<b>Salas disponibles</b>", Rico());
        scroll = GUILayout.BeginScrollView(scroll, GUILayout.Height(220));
        if (ultimaLista?.lista == null || ultimaLista.lista.Count == 0)
            GUILayout.Label("No hay salas todavía. ¡Crea una!");
        else
            foreach (var s in ultimaLista.lista)
            {
                GUILayout.BeginHorizontal(GUI.skin.box);
                GUILayout.Label($"[{s.id}] {s.nombre}  ({s.cantidad}/{s.maximo}) {(s.estado == "jugando" ? "· en juego" : "")}");
                GUI.enabled = s.estado == "esperando" && s.cantidad < s.maximo;
                if (GUILayout.Button("Entrar", GUILayout.Width(90))) Red.Unirse(s.id);
                GUI.enabled = true;
                GUILayout.EndHorizontal();
            }
        GUILayout.EndScrollView();

        if (GUILayout.Button("Desconectar")) { Red.Cerrar(); pantalla = Pantalla.Conexion; }
    }

    void Sala()
    {
        var s = Red.SalaActual;
        if (s == null) return;
        bool soyHost = s.host == Red.MiId;

        GUILayout.BeginHorizontal();
        GUILayout.Label($"<b>{s.nombre}</b>   Código: <b><color=#7fd4ff>{s.id}</color></b>", Rico());
        if (GUILayout.Button("Mi perfil", GUILayout.Width(130))) AbrirEditarPerfil();
        GUILayout.EndHorizontal();
        GUILayout.Label($"Jugadores {s.cantidad}/{s.maximo}");
        // Texto y color en vez de emojis: la fuente por defecto de IMGUI no los dibuja
        foreach (var j in s.jugadores)
        {
            string etiqueta = j.rol == "wizard"
                ? "<color=#c58cff>Wizard (anfitrión)</color>"
                : "Player · " + (j.listo ? "<color=#7fff7f>listo</color>" : "<color=#aaaaaa>esperando</color>");
            GUILayout.Label($"• <b>{ConColor(j.nombre, j.color)}</b>{(j.id == Red.MiId ? " (tú)" : "")} — {etiqueta}", Rico());
        }
        GUILayout.Label(Red.SoyWizard
            ? "<size=14>Eres el <b>Wizard</b>: verás qué elemento es cada esfera y guiarás al equipo. No puedes agarrar ni sumas progreso.</size>"
            : "<size=14>Eres <b>Player</b>: llevarás las esferas al reactor, pero solo verás \"?\". Escucha al Wizard.</size>", Rico());

        GUILayout.Space(15);
        if (soyHost)
        {
            // Con el Wizard solo nadie puede agarrar: la misión sería imposible
            bool pocos = s.cantidad < 2;
            GUI.enabled = !pocos;
            if (GUILayout.Button("Iniciar partida", GUILayout.Height(45))) Red.IniciarPartida();
            GUI.enabled = true;
            if (pocos)
                GUILayout.Label("<color=#ffb060>Se necesitan al menos 2 jugadores: el Wizard no puede agarrar objetos.</color>", Rico());
            else if (s.jugadores.Exists(j => j.id != s.host && !j.listo))
                GUILayout.Label("<color=#aaaaaa>Esperando a que todos marquen \"Listo\".</color>", Rico());
        }
        else if (GUILayout.Button(listo ? "Ya no estoy listo" : "¡Listo!", GUILayout.Height(45)))
        {
            listo = !listo;
            Red.MarcarListo(listo);
        }
        if (GUILayout.Button("Salir de la sala")) Red.SalirSala();
    }

    void Hud()
    {
        var s = Red.SalaActual;
        var mision = Red.MisionActual;
        var estado = Red.EstadoActual;
        bool wizard = Red.SoyWizard;

        GUILayout.BeginArea(new Rect(10, 10, 420, 320), GUI.skin.box);
        GUILayout.Label($"Sala <b>{s?.id}</b> · {s?.cantidad} jugadores · Eres <b>{(wizard ? "<color=#c58cff>Wizard</color>" : "Player")}</b>", Rico());
        GUILayout.Label(wizard
            ? "<size=15>WASD: moverte · Clic en una esfera: señalarla · ESC: salir</size>"
            : "<size=15>WASD: moverte · E: agarrar / soltar cerca · ESC: salir</size>", Rico());
        if (estado != null)
        {
            string dentro = estado.reactor.Count == 0 ? "vacío" : string.Join(" + ", estado.reactor);
            GUILayout.Label($"Reactor: <b>{dentro}</b>", Rico());
            GUILayout.Label($"Errores: <b>{estado.errores}</b>", Rico());
        }
        if (wizard && mision != null)
        {
            GUILayout.Label($"Receta: <b><color=#7fd4ff>{mision.formula}</color></b>", Rico());
            if (GUILayout.Button("Reiniciar misión", GUILayout.Height(32))) Red.Reiniciar();
        }
        GUILayout.EndArea();

        // Mensaje central: la victoria queda fija; el resto se muestra 3 segundos
        if (estado != null && !string.IsNullOrEmpty(estado.mensaje) && (estado.completada || Time.time - tMensaje < 3f))
        {
            string color = estado.completada ? "#7fff7f" : (mensajeEsError ? "#ff7070" : "#ffffff");
            int tam = estado.completada ? 40 : 28;
            var centro = new GUIStyle(Rico()) { alignment = TextAnchor.MiddleCenter };
            GUI.Label(new Rect(0, Screen.height * .2f, Screen.width, 120), $"<b><size={tam}><color={color}>{estado.mensaje}</color></size></b>", centro);
        }

        // Rechazos del servidor (p. ej. "Otro jugador ya lleva ese objeto")
        if (!string.IsNullOrEmpty(aviso) && Time.time - tAviso < 3f)
        {
            var abajo = new GUIStyle(Rico()) { alignment = TextAnchor.MiddleCenter };
            GUI.Label(new Rect(0, Screen.height - 60, Screen.width, 40), $"<color=#ffb060>{aviso}</color>", abajo);
        }
    }

    string Campo(string etiqueta, string valor)
    {
        GUILayout.BeginHorizontal();
        GUILayout.Label(etiqueta, GUILayout.Width(170));
        valor = GUILayout.TextField(valor);
        GUILayout.EndHorizontal();
        return valor;
    }

    static GUIStyle Rico() => new GUIStyle(GUI.skin.label) { richText = true, wordWrap = true };
}

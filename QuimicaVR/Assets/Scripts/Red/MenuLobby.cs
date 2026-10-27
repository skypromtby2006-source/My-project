using System.Text.RegularExpressions;
using UnityEngine;

// Menú completo con IMGUI: no hace falta armar Canvas ni prefabs.
// Pantallas: Conexión -> Lista de salas -> Dentro de la sala -> Partida
public class MenuLobby : MonoBehaviour
{
    enum Pantalla { Conexion, Salas, Sala, Partida }
    Pantalla pantalla = Pantalla.Conexion;

    string ip = "127.0.0.1", puerto = "7777", nombre = "Jugador";
    string nombreSala = "Laboratorio 1", codigo = "", aviso = "";
    int maximo = 4;
    bool listo;
    float proximoRefresco;
    Vector2 scroll;
    Mensaje ultimaLista;

    // HUD: los mensajes del reactor y los errores se muestran unos segundos
    float tMensaje = -99, tAviso = -99;
    bool mensajeEsError;
    int erroresPrevios;

    ClienteRed Red => ClienteRed.I;

    // Nombre automático de este arranque. Solo se guarda en PlayerPrefs un nombre escrito
    // por el usuario: si se guardara el automático, todas las instancias de la misma PC
    // (editor y builds comparten PlayerPrefs) arrancarían con el mismo "JugadorNN".
    string nombreAuto;
    static bool EsAutomatico(string n) => Regex.IsMatch(n, @"^Jugador\d+$");

    void Start()
    {
        nombreAuto = "Jugador" + Random.Range(100, 1000);
        var guardado = PlayerPrefs.GetString("nombre", "");
        // Se descarta un automático guardado por versiones anteriores
        nombre = guardado == "" || EsAutomatico(guardado) ? nombreAuto : guardado;
        ip = PlayerPrefs.GetString("ip", "127.0.0.1");

        Red.AlRecibir += m =>
        {
            if (m.t == "salas") ultimaLista = m;
            if (m.t == "sala") { pantalla = Pantalla.Sala; aviso = ""; }
            if (m.t == "fuera") { pantalla = Pantalla.Salas; listo = false; Red.ListarSalas(); }
            if (m.t == "inicio") { pantalla = Pantalla.Partida; tMensaje = -99; erroresPrevios = 0; }
            if (m.t == "estado")
            {
                tMensaje = Time.time;
                mensajeEsError = m.estado.errores > erroresPrevios;
                erroresPrevios = m.estado.errores;
            }
        };
        Red.AlError += e => { aviso = e; tAviso = Time.time; };
        Red.AlDesconectar += () => { pantalla = Pantalla.Conexion; aviso = "Se perdió la conexión con el servidor"; };
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
        GUILayout.Space(10);

        switch (pantalla)
        {
            case Pantalla.Conexion: Conexion(); break;
            case Pantalla.Salas: Salas(); break;
            case Pantalla.Sala: Sala(); break;
        }

        if (!string.IsNullOrEmpty(aviso))
        {
            GUILayout.Space(10);
            GUILayout.Label($"<color=#ff7070>{aviso}</color>", Rico());
        }
        GUILayout.EndArea();
    }

    void Conexion()
    {
        nombre = Campo("Tu nombre", nombre);
        ip = Campo("IP del servidor", ip);
        puerto = Campo("Puerto", puerto);
        GUILayout.Space(10);
        if (GUILayout.Button("Conectar", GUILayout.Height(45)))
        {
            if (EsAutomatico(nombre.Trim())) PlayerPrefs.DeleteKey("nombre");
            else PlayerPrefs.SetString("nombre", nombre);
            PlayerPrefs.SetString("ip", ip);
            aviso = "";
            if (Red.Conectar(ip.Trim(), int.TryParse(puerto, out var p) ? p : 7777, nombre))
            {
                pantalla = Pantalla.Salas;
                proximoRefresco = 0;
            }
        }
        GUILayout.Label("<size=14>Local: 127.0.0.1 · En otra PC de la red: la IP que muestra instalar_servidor.bat</size>", Rico());
    }

    void Salas()
    {
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

        GUILayout.Label($"<b>{s.nombre}</b>   Código: <b><color=#7fd4ff>{s.id}</color></b>", Rico());
        GUILayout.Label($"Jugadores {s.cantidad}/{s.maximo}");
        // Texto y color en vez de emojis: la fuente por defecto de IMGUI no los dibuja
        foreach (var j in s.jugadores)
        {
            string etiqueta = j.rol == "wizard"
                ? "<color=#c58cff>Wizard (anfitrión)</color>"
                : "Player · " + (j.listo ? "<color=#7fff7f>listo</color>" : "<color=#aaaaaa>esperando</color>");
            GUILayout.Label($"• {j.nombre}{(j.id == Red.MiId ? " (tú)" : "")} — {etiqueta}", Rico());
        }
        GUILayout.Label(Red.SoyWizard
            ? "<size=14>Eres el <b>Wizard</b>: verás qué elemento es cada esfera y guiarás al equipo. No puedes agarrar.</size>"
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

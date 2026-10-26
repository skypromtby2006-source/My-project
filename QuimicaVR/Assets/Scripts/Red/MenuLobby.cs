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

    ClienteRed Red => ClienteRed.I;

    void Start()
    {
        nombre = PlayerPrefs.GetString("nombre", "Jugador" + Random.Range(10, 99));
        ip = PlayerPrefs.GetString("ip", "127.0.0.1");

        Red.AlRecibir += m =>
        {
            if (m.t == "salas") ultimaLista = m;
            if (m.t == "sala") { pantalla = Pantalla.Sala; aviso = ""; }
            if (m.t == "fuera") { pantalla = Pantalla.Salas; listo = false; Red.ListarSalas(); }
            if (m.t == "inicio") pantalla = Pantalla.Partida;
        };
        Red.AlError += e => aviso = e;
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
            PlayerPrefs.SetString("nombre", nombre);
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
        foreach (var j in s.jugadores)
        {
            string etiqueta = j.id == s.host ? "<color=#ffd24d>anfitrión</color>" : (j.listo ? "<color=#7fff7f>listo</color>" : "<color=#aaaaaa>esperando</color>");
            GUILayout.Label($"• {j.nombre}{(j.id == Red.MiId ? " (tú)" : "")} — {etiqueta}", Rico());
        }

        GUILayout.Space(15);
        if (soyHost)
        {
            if (GUILayout.Button("Iniciar partida", GUILayout.Height(45))) Red.IniciarPartida();
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
        GUI.Label(new Rect(10, 10, 600, 30), $"Sala {s?.id} · {s?.cantidad} jugadores · WASD para moverte · ESC salir", Rico());
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

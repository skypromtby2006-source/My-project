using System.Linq;
using UnityEngine.UIElements;

// Lobby.uxml: código grande, Lado Wizard (el anfitrión) y Lado Player, el chip que
// dice qué falta para empezar y la barra de acciones. El anfitrión ve "Iniciar
// partida"; los demás, "Estoy listo". Las reglas son las mismas que valida el
// servidor (server.py, "iniciar"): aquí solo se explican antes de que rebote.
public class PantallaLobby : ControladorPantalla
{
    readonly Label nombre, codigo, estado, aviso, reto;
    readonly VisualElement ladoWizard, ladoPlayer, filaReto;
    readonly Button listo, iniciar, cambiarReto;
    string firmaJugadores;

    public PantallaLobby(MenuLobby menu, VisualElement raiz) : base(menu, raiz)
    {
        nombre = Q<Label>("nombre");
        codigo = Q<Label>("codigo");
        estado = Q<Label>("estado");
        aviso = Q<Label>("aviso");
        ladoWizard = Q<VisualElement>("lado-wizard");
        ladoPlayer = Q<ScrollView>("lado-player");
        listo = Q<Button>("listo");
        iniciar = Q<Button>("iniciar");
        filaReto = Q<VisualElement>("fila-reto");
        reto = Q<Label>("reto");
        cambiarReto = Q<Button>("cambiar-reto");
        cambiarReto.clicked += menu.CambiarReto;

        Q<Button>("salir").clicked += menu.SalirDeSala;
        listo.clicked += menu.CambiarListo;
        iniciar.clicked += menu.Iniciar;
    }

    public override void AlMostrar() => firmaJugadores = null;

    public override void Refrescar()
    {
        var s = Red.SalaActual;
        if (s == null) return;
        nombre.text = s.nombre;
        codigo.text = s.id;

        string firma = string.Join("|", s.jugadores.Select(j => $"{j.id},{j.nombre},{j.color},{j.rol},{j.listo}")) + s.host;
        if (firma != firmaJugadores)
        {
            firmaJugadores = firma;
            ladoWizard.Clear();
            ladoPlayer.Clear();
            foreach (var j in s.jugadores)
                (j.rol == "wizard" ? ladoWizard : ladoPlayer).Add(Fila(j, s.host));
            Ui.AplicarGaps(ladoWizard);
            Ui.AplicarGaps(ladoPlayer);
        }

        bool soyHost = s.host == Red.MiId;
        int faltanListos = s.jugadores.Count(j => j.id != s.host && !j.listo);
        bool sePuede = s.cantidad >= 2 && faltanListos == 0;
        string texto;
        if (s.cantidad < 2) texto = "Falta al menos un jugador más para iniciar";
        else if (faltanListos > 0)
            texto = faltanListos == 1 ? "Falta 1 jugador por marcarse como listo" : $"Faltan {faltanListos} jugadores por marcarse como listos";
        else texto = soyHost ? "Todos listos: ya puedes iniciar la partida" : "Todos listos: el anfitrión puede iniciar";
        if (Red.SoyDocente) texto = "Estás mirando como docente: la partida empieza cuando el anfitrión la inicie";
        estado.text = texto;
        estado.EnableInClassList("warn", !sePuede);
        estado.EnableInClassList("ok", sePuede);

        // Reto del docente: solo aparece si el anfitrión está en una clase con retos abiertos.
        // Lo elige el anfitrión; los demás ven cuál quedó.
        var elegido = s.reto != 0 ? s.retos.Find(r => r.id == s.reto) : null;
        Ui.Mostrar(filaReto, s.retos.Count > 0 || s.reto != 0);
        reto.text = elegido == null ? "Sin reto: partida libre"
            : $"Reto: {elegido.nombre} · grupos de hasta {elegido.jugadores}"
              + (elegido.tiempo_limite_s > 0 ? $" · {elegido.tiempo_limite_s / 60} min" : "");
        Ui.Mostrar(cambiarReto, soyHost);   // el docente nunca es host: no lo ve

        // El aviso de error (p. ej. el rebote del servidor) no repite el chip de estado
        Ui.Chip(aviso, menu.Aviso);

        Ui.Mostrar(iniciar, soyHost);
        iniciar.SetEnabled(sePuede);
        Ui.Mostrar(listo, !soyHost && !Red.SoyDocente);
        bool yoListo = s.jugadores.Find(j => j.id == Red.MiId)?.listo ?? false;
        listo.text = yoListo ? "Ya no estoy listo" : "Estoy listo";
        Ui.AplicarGaps(Raiz);
    }

    VisualElement Fila(InfoJugador j, string host)
    {
        var fila = new VisualElement();
        fila.AddToClassList("fila-jugador");
        fila.AddToClassList("row");
        fila.AddToClassList("g14");
        fila.Add(Ui.Avatar(j.nombre, j.color));

        var nombre = new Label(j.id == Red.MiId ? j.nombre + " (tú)" : j.nombre);
        nombre.AddToClassList("nombre-jugador");
        fila.Add(nombre);

        // El anfitrión no marca "listo": es quien inicia. Por eso lleva solo el chip Host.
        var chip = new Label();
        chip.AddToClassList("chip");
        if (j.id == host) { chip.text = "Host"; chip.AddToClassList("host"); }
        else if (j.listo) { chip.text = "Listo"; chip.AddToClassList("ok"); }
        else { chip.text = "No listo"; chip.AddToClassList("warn"); }
        fila.Add(chip);
        return fila;
    }
}

using System.Linq;
using UnityEngine.UIElements;

// Salas.uxml: lista de salas a la izquierda (se refresca sola cada 2 s, más el botón
// Actualizar), unirse con código de 4 caracteres y "Crear sala" a la derecha.
public class PantallaSalas : ControladorPantalla
{
    readonly VisualElement chipPerfil;
    readonly ScrollView lista;
    readonly Label aviso, vacia, maximo;
    readonly TextField codigo, nombreSala;
    string firmaLista;   // la lista solo se rearma si cambió: si no, el botón bajo el mouse parpadea

    public PantallaSalas(MenuLobby menu, VisualElement raiz) : base(menu, raiz)
    {
        chipPerfil = Q<VisualElement>("chip-perfil");
        lista = Q<ScrollView>("lista");
        aviso = Q<Label>("aviso");
        vacia = Q<Label>("vacia");
        maximo = Q<Label>("maximo");
        codigo = Q<TextField>("codigo");
        nombreSala = Q<TextField>("nombre-sala");

        Q<Button>("volver").clicked += menu.VolverAlMenu;
        Q<Button>("actualizar").clicked += menu.ActualizarSalas;
        Q<Button>("unirse-codigo").clicked += UnirseConCodigo;
        Q<Button>("menos").clicked += () => { menu.Maximo--; Refrescar(); };
        Q<Button>("mas").clicked += () => { menu.Maximo++; Refrescar(); };
        Q<Button>("crear").clicked += Crear;
        Ui.EnterEjecuta(codigo, UnirseConCodigo);
        Ui.EnterEjecuta(nombreSala, Crear);
        // Los códigos son en mayúsculas: se ven igual que como los muestra el anfitrión
        codigo.RegisterValueChangedCallback(e =>
        {
            var may = e.newValue.ToUpperInvariant();
            if (may != e.newValue) codigo.SetValueWithoutNotify(may);
        });
        Ui.Placeholder(codigo, "Código de sala (4 caracteres)");
    }

    void UnirseConCodigo() => menu.Unirse(codigo.value);

    void Crear()
    {
        menu.NombreSala = nombreSala.value;
        menu.CrearSala();
    }

    public override void AlMostrar()
    {
        nombreSala.SetValueWithoutNotify(menu.NombreSala);
        codigo.SetValueWithoutNotify("");
        firmaLista = null;
    }

    public override void Refrescar()
    {
        Ui.LlenarChipPerfil(chipPerfil, Red.MiPerfil);
        Ui.Chip(aviso, menu.Aviso);
        maximo.text = menu.Maximo.ToString();

        var salas = menu.Salas;
        string firma = string.Join("|", salas.Select(s => $"{s.id},{s.nombre},{s.cantidad},{s.maximo},{s.estado}"));
        if (firma != firmaLista)
        {
            firmaLista = firma;
            lista.Clear();
            foreach (var s in salas) lista.Add(Fila(s));
            Ui.AplicarGaps(lista);
        }
        Ui.Mostrar(vacia, salas.Count == 0);
        Ui.AplicarGaps(Raiz);
    }

    VisualElement Fila(InfoSala s)
    {
        var fila = new VisualElement();
        fila.AddToClassList("fila");
        fila.AddToClassList("row");
        fila.AddToClassList("g14");

        var nombre = new Label(s.nombre);
        nombre.AddToClassList("nombre-fila");
        fila.Add(nombre);

        // El modo es siempre cooperativo: el chip se muestra igual que en el diseño
        var modo = new Label("Cooperativo");
        modo.AddToClassList("chip");
        fila.Add(modo);

        var cupo = new Label($"{s.cantidad}/{s.maximo}");
        cupo.AddToClassList("cupo");
        fila.Add(cupo);

        bool enPartida = s.estado != "esperando", llena = s.cantidad >= s.maximo;
        if (enPartida || llena)
        {
            var motivo = new Label(enPartida ? "En partida" : "Llena");
            motivo.AddToClassList("chip");
            motivo.AddToClassList("warn");
            fila.Add(motivo);
        }

        string id = s.id;
        var unirse = new Button(() => menu.Unirse(id)) { text = "Unirse" };
        unirse.AddToClassList("btn");
        unirse.AddToClassList("sm");
        unirse.SetEnabled(!enPartida && !llena);
        fila.Add(unirse);
        return fila;
    }
}

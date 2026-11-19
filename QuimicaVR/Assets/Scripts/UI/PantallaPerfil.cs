using System.Linq;
using UnityEngine.UIElements;

// Perfil.uxml: usuario (no editable), nombre visible y color, Guardar / Volver; al lado,
// el progreso que manda el servidor en el mensaje "perfil" (MenuLobby.AbrirEditarPerfil
// lo pide de nuevo al entrar, porque pudo cambiar desde el login).
public class PantallaPerfil : ControladorPantalla
{
    const int MaxHistorial = 5;
    readonly VisualElement chipPerfil, historial;
    readonly Label usuario, aviso, info, completadas, mejor, errores, sinHistorial;
    readonly TextField nombre;
    readonly System.Action repintarColor;

    public PantallaPerfil(MenuLobby menu, VisualElement raiz) : base(menu, raiz)
    {
        chipPerfil = Q<VisualElement>("chip-perfil");
        historial = Q<VisualElement>("historial");
        usuario = Q<Label>("usuario");
        aviso = Q<Label>("aviso");
        info = Q<Label>("info");
        completadas = Q<Label>("completadas");
        mejor = Q<Label>("mejor");
        errores = Q<Label>("errores");
        sinHistorial = Q<Label>("sin-historial");
        nombre = Q<TextField>("nombre");

        Q<Button>("guardar").clicked += Guardar;
        Q<Button>("volver").clicked += menu.Volver;
        Ui.EnterEjecuta(Q<VisualElement>("tarjeta"), Guardar);
        repintarColor = Ui.SelectorColor(Q<VisualElement>("colores"), () => menu.ColorPerfil, c => menu.ColorPerfil = c);
    }

    void Guardar() => menu.GuardarPerfil(nombre.value, menu.ColorPerfil);

    public override void AlMostrar()
    {
        nombre.SetValueWithoutNotify(menu.NombrePerfil);
        repintarColor();
    }

    public override void Refrescar()
    {
        var p = Red.MiPerfil;
        if (p == null) return;
        Ui.LlenarChipPerfil(chipPerfil, p);
        usuario.text = p.usuario;
        Ui.Chip(aviso, menu.Aviso);
        Ui.Chip(info, menu.Info);

        var pr = p.progreso ?? new InfoProgreso();
        completadas.text = pr.completadas.ToString();
        mejor.text = pr.completadas > 0 ? MenuLobby.Segundos(pr.mejor_tiempo_s) : "—";
        errores.text = pr.errores_totales.ToString();

        historial.Clear();
        foreach (var h in pr.historial.Take(MaxHistorial))
        {
            var fila = new VisualElement();
            fila.AddToClassList("fila-historial");
            var fecha = new Label(MenuLobby.Fecha(h.fecha));
            fecha.AddToClassList("fecha");
            fila.Add(fecha);
            var dur = new Label(MenuLobby.Segundos(h.duracion_s));
            dur.AddToClassList("col-dato");
            fila.Add(dur);
            var err = new Label(h.errores == 1 ? "1 error" : $"{h.errores} errores");
            err.AddToClassList("col-dato");
            fila.Add(err);
            historial.Add(fila);
        }
        Ui.Mostrar(sinHistorial, pr.historial.Count == 0);
        Ui.AplicarGaps(Raiz);
    }
}

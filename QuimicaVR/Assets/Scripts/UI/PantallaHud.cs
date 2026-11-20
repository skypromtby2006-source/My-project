using UnityEngine;
using UnityEngine.UIElements;

// Hud.uxml (UI-3): HUD de la partida, pausa y consola de valor con el diseño nuevo.
// Reemplaza el IMGUI de MenuLobby y PrimeraPersona. Solo lee estado (ClienteRed, el
// GestorPartida y el control de la cámara) y llama a las mismas acciones de siempre.
public class PantallaHud : ControladorPantalla
{
    readonly VisualElement panelSala, editor, pausa;
    readonly Label titulo, chipRol, chipConcepto, chipReto, reaccion, numeros, mensajeSala;
    readonly Label mira, pista, mensaje, aviso, ayuda, editorTitulo, sensValor;
    readonly TextField editorValor;
    readonly Slider sensibilidad;
    GestorPartida gestor;
    Interactuable editandoAntes;

    public PantallaHud(MenuLobby menu, VisualElement raiz) : base(menu, raiz)
    {
        panelSala = Q<VisualElement>("panel-sala");
        titulo = Q<Label>("sala-titulo");
        chipRol = Q<Label>("chip-rol");
        chipConcepto = Q<Label>("chip-concepto");
        chipReto = Q<Label>("chip-reto");
        reaccion = Q<Label>("reaccion");
        numeros = Q<Label>("numeros");
        mensajeSala = Q<Label>("mensaje-sala");
        mira = Q<Label>("mira");
        pista = Q<Label>("pista");
        mensaje = Q<Label>("mensaje");
        aviso = Q<Label>("aviso");
        ayuda = Q<Label>("ayuda");
        editor = Q<VisualElement>("editor");
        editorTitulo = Q<Label>("editor-titulo");
        editorValor = Q<TextField>("editor-valor");
        pausa = Q<VisualElement>("pausa");
        sensibilidad = Q<Slider>("sensibilidad");
        sensValor = Q<Label>("sensibilidad-valor");

        Q<Button>("editor-enviar").clicked += Enviar;
        Q<Button>("editor-cancelar").clicked += () => Jugador?.CancelarEdicion();
        Ui.EnterEjecuta(editorValor, Enviar);
        Ui.Placeholder(editorValor, "Valor (ej.: 2.5)");
        Q<Button>("continuar").clicked += () => Control?.Pausar(false);
        Q<Button>("salir-sala").clicked += menu.SalirDeSala;   // Terminar() libera el cursor
        sensibilidad.RegisterValueChangedCallback(e => { if (Control != null) Control.Sensibilidad = e.newValue; });
        Ui.AplicarGaps(Raiz);
    }

    GestorPartida Gestor => gestor != null ? gestor : (gestor = Object.FindFirstObjectByType<GestorPartida>());
    PrimeraPersona Jugador => Gestor != null ? Gestor.JugadorLocal : null;
    IControlPartida Control => Gestor != null ? Gestor.Control : null;

    void Enviar() => Jugador?.EnviarValor(editorValor.value);

    // Se llama en cada cuadro mientras se juega: el reloj del reto y la mira cambian solos
    public override void Refrescar()
    {
        var red = Red;
        var e = red.SalaEstadoActual;
        bool docente = red.SoyDocente;

        Ui.Mostrar(panelSala, e != null);
        if (e != null)
        {
            titulo.text = $"Sala {e.sala}/{red.NivelActual?.total_salas ?? 5} · {e.nombre}";
            chipRol.text = docente ? "Espectador" : red.SoyWizard ? "Wizard" : "Player";
            Ui.Chip(chipConcepto, string.IsNullOrEmpty(e.concepto) ? "" : "Concepto: " + e.concepto);
            var reto = red.RetoActual;
            string reloj = "";
            if (reto != null && reto.tiempo_limite_s > 0)
            {
                // Solo informativo: el que corta la partida es el servidor
                int resta = Mathf.Max(0, Mathf.CeilToInt(reto.tiempo_limite_s - (Time.time - red.InicioReto)));
                reloj = e.tiempo_agotado ? "Reto: tiempo agotado" : $"Reto: {resta / 60}:{resta % 60:00}";
            }
            Ui.Chip(chipReto, reloj);
            Ui.Chip(reaccion, e.reaccion);
            Ui.Chip(numeros, PrimeraPersona.Numeros(e));
            Ui.Chip(mensajeSala, e.mensaje);
        }

        var control = Control;
        bool enPausa = control != null && control.EnPausa;
        var jugador = Jugador;
        var editando = jugador != null ? jugador.Editando : null;

        Ui.Mostrar(mira, jugador != null && !enPausa && editando == null);
        Ui.Chip(pista, jugador != null && !enPausa ? jugador.Pista : "");
        Ui.Chip(mensaje, menu.MensajeCentral);
        Ui.Chip(aviso, menu.AvisoPartida);
        Ui.Chip(ayuda, docente && !enPausa ? "Espectador · WASD y mouse · Q/E bajar y subir · Shift rápido · Esc pausa" : "");

        // Consola de valor: al abrirse, el campo vacío y con el foco
        Ui.Mostrar(editor, editando != null && !enPausa);
        if (editando != editandoAntes)
        {
            editandoAntes = editando;
            if (editando != null)
            {
                editorTitulo.text = $"Ajustar {editando.id}";
                editorValor.SetValueWithoutNotify("");
                editorValor.schedule.Execute(() => editorValor.Focus());
            }
        }

        bool pausaVisible = pausa.style.display != DisplayStyle.None;
        if (enPausa && !pausaVisible) sensibilidad.SetValueWithoutNotify(control.Sensibilidad);
        Ui.Mostrar(pausa, enPausa);
        if (control != null) sensValor.text = control.Sensibilidad.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture);
        Ui.AplicarGaps(panelSala);
    }
}

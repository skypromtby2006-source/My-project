using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

// Utilidades de vista compartidas por las pantallas de UI Toolkit (SPRINT_UI §2).
// Solo arman o muestran elementos: no saben nada de la red ni del juego.
public static class Ui
{
    public static void Mostrar(VisualElement e, bool visible)
    {
        if (e != null) e.style.display = visible ? DisplayStyle.Flex : DisplayStyle.None;
    }

    static bool Oculto(VisualElement e) => e.style.display == DisplayStyle.None;

    // USS no tiene la propiedad "gap" del CSS del diseño. Las clases g6, g8, g14...
    // la imitan: se le pone margen a cada hijo visible menos al primero, a la izquierda
    // si el contenedor es .row y arriba si es columna. Se vuelve a llamar después de
    // mostrar u ocultar hijos, para que un hijo oculto no deje un hueco de más.
    static readonly int[] Separaciones = { 6, 8, 10, 12, 14, 16, 20, 24, 28, 36 };

    public static void AplicarGaps(VisualElement raiz)
    {
        raiz.Query<VisualElement>().ForEach(e =>
        {
            foreach (var g in Separaciones)
                if (e.ClassListContains("g" + g)) { Separar(e, g); break; }
        });
    }

    static void Separar(VisualElement contenedor, float g)
    {
        bool fila = contenedor.ClassListContains("row");
        bool primero = true;
        foreach (var hijo in contenedor.Children())
        {
            if (Oculto(hijo)) continue;
            float m = primero ? 0 : g;
            if (fila) hijo.style.marginLeft = m; else hijo.style.marginTop = m;
            primero = false;
        }
    }

    public static Color ColorDe(string hex) =>
        ColorUtility.TryParseHtmlString(hex ?? "", out var c) ? c : Color.white;

    // Texto oscuro sobre colores claros (amarillo, blanco) y blanco sobre los oscuros,
    // para que la inicial del avatar se lea con cualquiera de los 8 colores.
    public static Color TextoSobre(Color fondo) =>
        0.299f * fondo.r + 0.587f * fondo.g + 0.114f * fondo.b > 0.6f ? new Color32(0x0e, 0x0a, 0x1f, 0xff) : Color.white;

    // Círculo con la inicial del nombre en el color del perfil (Lobby, SPRINT_UI §3)
    public static VisualElement Avatar(string nombre, string hex)
    {
        var fondo = ColorDe(hex);
        var avatar = new VisualElement();
        avatar.AddToClassList("avatar");
        avatar.style.backgroundColor = fondo;
        var inicial = new Label(string.IsNullOrEmpty(nombre) ? "?" : nombre.Trim().Substring(0, 1).ToUpperInvariant());
        inicial.style.color = TextoSobre(fondo);
        avatar.Add(inicial);
        return avatar;
    }

    // Chip de arriba a la derecha: punto del color del perfil + nombre visible
    public static void LlenarChipPerfil(VisualElement chip, InfoPerfil p)
    {
        if (chip == null) return;
        chip.Clear();
        if (p == null) return;
        var punto = new VisualElement();
        punto.AddToClassList("punto");
        punto.style.backgroundColor = ColorDe(p.color);
        chip.Add(punto);
        chip.Add(new Label(p.nombre));
    }

    // Selector de los 8 colores de la paleta. Devuelve la función que repinta el borde
    // del elegido, para llamarla cuando el color cambia desde fuera (al abrir la pantalla).
    public static Action SelectorColor(VisualElement contenedor, Func<string> actual, Action<string> elegir)
    {
        contenedor.Clear();
        var muestras = new List<(VisualElement, string)>();
        void Repintar()
        {
            foreach (var (m, hex) in muestras) m.EnableInClassList("color-elegido", hex == actual());
        }
        foreach (var hex in ClienteRed.Paleta)
        {
            var m = new VisualElement { tooltip = hex };
            m.AddToClassList("color");
            m.style.backgroundColor = ColorDe(hex);
            string elegido = hex;
            m.RegisterCallback<ClickEvent>(_ => { elegir(elegido); Repintar(); });
            contenedor.Add(m);
            muestras.Add((m, hex));
        }
        Repintar();
        AplicarGaps(contenedor.parent ?? contenedor);
        return Repintar;
    }

    // Enter en cualquier campo de la tarjeta = el botón principal, como en un formulario web
    public static void EnterEjecuta(VisualElement zona, Action accion)
    {
        zona.RegisterCallback<KeyDownEvent>(e =>
        {
            if (e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter) accion();
        }, TrickleDown.TrickleDown);
    }

    // Muestra un chip solo si tiene texto
    public static void Chip(Label chip, string texto)
    {
        chip.text = texto ?? "";
        Mostrar(chip, !string.IsNullOrEmpty(texto));
    }
}

// Base de cada pantalla. El controlador solo conecta los botones de su UXML con las
// acciones de MenuLobby (que a su vez llaman a ClienteRed): la red no cambia, y la
// prueba del build (PruebaAutomatica) usa esas mismas acciones.
public abstract class ControladorPantalla
{
    protected readonly MenuLobby menu;
    public readonly VisualElement Raiz;
    protected ClienteRed Red => ClienteRed.I;

    protected ControladorPantalla(MenuLobby menu, VisualElement raiz)
    {
        this.menu = menu;
        Raiz = raiz;
    }

    // Al entrar a la pantalla: carga los campos con los valores actuales. Los campos de
    // texto NO se pisan en cada refresco: el cursor saltaría mientras se escribe.
    public virtual void AlMostrar() { }

    // Cada vez que llega un mensaje o cambia el estado del menú
    public virtual void Refrescar() { }

    protected T Q<T>(string nombre) where T : VisualElement
    {
        var e = Raiz.Q<T>(nombre);
        if (e == null) Debug.LogError($"[Quimica] Falta el elemento '{nombre}' en la pantalla {GetType().Name}");
        return e;
    }
}

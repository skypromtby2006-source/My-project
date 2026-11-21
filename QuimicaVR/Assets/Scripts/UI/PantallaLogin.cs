using UnityEngine.UIElements;

// Login.uxml: pestañas Entrar / Crear cuenta + IP y puerto del servidor.
// Abajo a la izquierda, el estado real de la conexión (SPRINT_UI §3).
public class PantallaLogin : ControladorPantalla
{
    readonly Button tabEntrar, tabCrear, tabDocente, accion;
    readonly TextField usuario, nombre, ip, puerto, contrasena;
    readonly VisualElement soloCrear, soloDocente, tarjeta;
    readonly Label estado, aviso, ayuda;
    readonly System.Action repintarColor;

    public PantallaLogin(MenuLobby menu, VisualElement raiz) : base(menu, raiz)
    {
        tabEntrar = Q<Button>("tab-entrar");
        tabCrear = Q<Button>("tab-crear");
        tabDocente = Q<Button>("tab-docente");
        contrasena = Q<TextField>("contrasena");
        soloDocente = Q<VisualElement>("solo-docente");
        accion = Q<Button>("accion");
        usuario = Q<TextField>("usuario");
        nombre = Q<TextField>("nombre");
        ip = Q<TextField>("ip");
        puerto = Q<TextField>("puerto");
        soloCrear = Q<VisualElement>("solo-crear");
        tarjeta = Q<VisualElement>("tarjeta");
        estado = Q<Label>("estado-servidor");
        aviso = Q<Label>("aviso");
        ayuda = Q<Label>("ayuda-usuario");

        tabEntrar.clicked += () => { menu.CambiarPestana(0); Refrescar(); };
        tabCrear.clicked += () => { menu.CambiarPestana(1); Refrescar(); };
        tabDocente.clicked += () => { menu.CambiarPestana(2); Refrescar(); };
        accion.clicked += Ejecutar;
        Ui.EnterEjecuta(tarjeta, Ejecutar);
        // El usuario se guarda en minúsculas (regla del servidor): se ve igual que se guardará
        usuario.RegisterValueChangedCallback(e =>
        {
            var min = e.newValue.ToLowerInvariant();
            if (min != e.newValue) usuario.SetValueWithoutNotify(min);
        });
        repintarColor = Ui.SelectorColor(Q<VisualElement>("colores"), () => menu.ColorPerfil, c => menu.ColorPerfil = c);
    }

    // Lo mismo que el botón Entrar / Crear cuenta: los campos pasan a MenuLobby y ahí
    // se valida y se conecta (si hace falta) antes de mandar login o registro.
    void Ejecutar()
    {
        menu.FijarServidor(ip.value, puerto.value);
        if (menu.Pestana == 0) menu.Entrar(usuario.value);
        else if (menu.Pestana == 2) menu.EntrarDocente(usuario.value, contrasena.value);
        else menu.CrearPerfil(usuario.value, nombre.value, menu.ColorPerfil);
        Refrescar();
    }

    public override void AlMostrar()
    {
        usuario.SetValueWithoutNotify(menu.Usuario);
        nombre.SetValueWithoutNotify(menu.NombrePerfil);
        ip.SetValueWithoutNotify(menu.Ip);
        puerto.SetValueWithoutNotify(menu.Puerto);
        repintarColor();
    }

    public override void Refrescar()
    {
        bool crear = menu.Pestana == 1, docente = menu.Pestana == 2;
        // La pestaña activa es el botón primario; las otras, secundario (igual que el diseño)
        tabEntrar.EnableInClassList("sec", menu.Pestana != 0);
        tabCrear.EnableInClassList("sec", !crear);
        tabDocente.EnableInClassList("sec", !docente);
        Ui.Mostrar(soloCrear, crear);
        Ui.Mostrar(soloDocente, docente);
        Ui.Mostrar(ayuda, crear);
        accion.text = crear ? "Crear cuenta" : docente ? "Entrar como espectador" : "Entrar";

        if (Red.Conectado)
        {
            estado.text = $"Servidor {menu.Ip}:{menu.Puerto} · conectado";
            estado.EnableInClassList("ok", true);
            estado.EnableInClassList("warn", false);
        }
        else
        {
            bool error = !string.IsNullOrEmpty(menu.ErrorConexion);
            estado.text = error ? menu.ErrorConexion : "Servidor sin conectar · se conecta al entrar";
            estado.EnableInClassList("ok", false);
            estado.EnableInClassList("warn", error);
        }

        // Los errores de conexión ya están en el chip de abajo: no se repiten en la tarjeta
        string texto = menu.Aviso == menu.ErrorConexion ? "" : menu.Aviso;
        Ui.Chip(aviso, texto);
        Ui.AplicarGaps(Raiz);
    }
}

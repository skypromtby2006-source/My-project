using UnityEngine.UIElements;

// Menu.uxml: las 3 tarjetas (solo Multijugador habilitada) y la fila Perfil · Ajustes ·
// Cerrar sesión. "Cerrar sesión" desconecta: el servidor libera el usuario al cortar
// la conexión, y no hay un mensaje de logout aparte en el protocolo.
public class PantallaMenu : ControladorPantalla
{
    readonly VisualElement chipPerfil;

    public PantallaMenu(MenuLobby menu, VisualElement raiz) : base(menu, raiz)
    {
        chipPerfil = Q<VisualElement>("chip-perfil");
        Q<Button>("ver-salas").clicked += menu.AbrirSalas;
        Q<Button>("perfil").clicked += menu.AbrirEditarPerfil;
        Q<Button>("cerrar-sesion").clicked += menu.Desconectar;
    }

    public override void Refrescar()
    {
        Ui.LlenarChipPerfil(chipPerfil, Red.MiPerfil);
        Ui.AplicarGaps(Raiz);
    }
}

using UnityEngine;

// "Cómo se ingresa": separa la entrada del controlador de primera persona para que
// en la fase de VR solo se agregue EntradaXR sin tocar el resto (SPRINT4 §3.3,
// "preparado para VR"). Es el aporte ingenieril del perfil: qué se quiere hacer
// (apuntar, moverse, activar) queda aparte de con qué se hace (teclado hoy, XR luego).
public interface IInteractor
{
    Vector2 Movimiento();  // x = lateral, y = adelante/atrás (WASD / stick izquierdo)
    Vector2 Mirada();      // delta para girar la vista (mouse / stick derecho)
    bool Activar();        // apretó "usar" este frame (E / gatillo)
    bool Pausa();          // apretó pausa este frame (ESC / botón de menú)
}

// Teclado + mouse. En VR se reemplaza por una EntradaXR que implemente IInteractor.
public class EntradaTeclado : IInteractor
{
    public float sensibilidad;

    public EntradaTeclado(float sensibilidad = 2f) { this.sensibilidad = sensibilidad; }

    public Vector2 Movimiento() => new Vector2(Input.GetAxisRaw("Horizontal"), Input.GetAxisRaw("Vertical"));

    public Vector2 Mirada()
    {
        // Sin "Mouse X/Y" configurados el proyecto igual los trae por defecto; si no,
        // devuelve 0 y la cámara no gira (no rompe).
        float mx = Input.GetAxis("Mouse X");
        float my = Input.GetAxis("Mouse Y");
        return new Vector2(mx, my) * sensibilidad;
    }

    public bool Activar() => Input.GetKeyDown(KeyCode.E);
    public bool Pausa() => Input.GetKeyDown(KeyCode.Escape);
}

// Marca un objeto del nivel con el que se puede interactuar. GeneradorNivel la pone en
// cada consola, palanca y montacargas; PrimeraPersona la lee con un raycast.
public class Interactuable : MonoBehaviour
{
    public enum Clase { Consola, Palanca, Montacargas }
    public Clase clase;
    public string id;        // id de la consola / montacargas
    public string subtipo;   // "dial", "balanza", "entrada", "valvula", "lectura"
    public string puertaId;  // para las palancas: a qué puerta pertenece
    public string lado;      // "wizard" / "player": de qué lado está

    public string Pista()
    {
        switch (clase)
        {
            case Clase.Consola:
                if (subtipo == "valvula") return $"E: abrir {id}";
                if (subtipo == "lectura") return $"E: leer {id}";
                return $"E: ajustar {id}";
            case Clase.Palanca: return "E: bajar la palanca";
            case Clase.Montacargas: return "E: enviar por el montacargas";
            default: return "E";
        }
    }
}

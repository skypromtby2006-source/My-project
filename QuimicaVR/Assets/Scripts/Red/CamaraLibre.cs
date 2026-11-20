using UnityEngine;
using UnityEngine.Rendering.Universal;

// Cámara del docente espectador (revisión 20/11): vuela libre por el laberinto, sin
// colisiones ni interacción y sin mandar posición (el servidor tampoco la reenviaría).
// WASD + mouse, Q/E para bajar y subir, Shift para ir rápido. Esc lo maneja MenuLobby
// (sale de la sala, como un jugador).
public class CamaraLibre : MonoBehaviour
{
    public float velocidad = 6f, sensibilidad = 2f;
    float pitch, yaw;

    public static CamaraLibre Crear(Vector3 pos, Transform padre)
    {
        var go = new GameObject("CamaraEspectador");
        go.transform.SetParent(padre, false);
        go.transform.position = pos;
        var cam = go.AddComponent<Camera>();
        go.AddComponent<AudioListener>();
        // Igual que PrimeraPersona: sin esto URP ignora el Volume del laberinto
        cam.GetUniversalAdditionalCameraData().renderPostProcessing = true;
        var c = go.AddComponent<CamaraLibre>();
        c.yaw = go.transform.eulerAngles.y;
        Cursor.lockState = CursorLockMode.Locked;
        Cursor.visible = false;
        return c;
    }

    void Update()
    {
        yaw += Input.GetAxis("Mouse X") * sensibilidad;
        pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * sensibilidad, -85f, 85f);
        transform.rotation = Quaternion.Euler(pitch, yaw, 0);

        var dir = new Vector3(Input.GetAxisRaw("Horizontal"), 0, Input.GetAxisRaw("Vertical"));
        if (Input.GetKey(KeyCode.E)) dir.y += 1;
        if (Input.GetKey(KeyCode.Q)) dir.y -= 1;
        float v = velocidad * (Input.GetKey(KeyCode.LeftShift) ? 3f : 1f);
        transform.position += transform.rotation * dir.normalized * v * Time.deltaTime;
    }

    // Se destruye con la escena al salir: el menú necesita el cursor de vuelta
    void OnDestroy()
    {
        Cursor.lockState = CursorLockMode.None;
        Cursor.visible = true;
    }
}

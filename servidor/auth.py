"""
Login del administrador del panel: credenciales del .env, token JWT y límite de intentos.
"""
import collections
import logging
import os
import pathlib
import secrets
import time

import jwt

log = logging.getLogger("servidor")

DURACION_TOKEN_S = 8 * 3600
INTENTOS_POR_MINUTO = 5
ALGORITMO = "HS256"


def cargar_env():
    """Lee el .env de la raíz del repo (o junto a server.py) sin pisar variables ya definidas.

    Por qué a mano y no con python-dotenv: es una dependencia más para el Plan B2 en
    Windows por 15 líneas. Con Docker no hace falta: compose pasa el .env con env_file.
    """
    aqui = pathlib.Path(__file__).resolve().parent
    for ruta in (aqui / ".env", aqui.parent / ".env"):
        if not ruta.is_file():
            continue
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
        log.info("Configuración del panel leída de %s", ruta)
        return


class Autenticador:
    def __init__(self, usuario: str, contrasena: str, secreto: str | None = None):
        self.usuario = usuario
        self.contrasena = contrasena
        if not secreto:
            # Sin JWT_SECRET se inventa uno: funciona, pero los tokens dejan de valer
            # al reiniciar el servidor (el admin tiene que volver a entrar).
            log.warning("Falta JWT_SECRET en el .env: las sesiones del panel se cierran al reiniciar el servidor")
            secreto = secrets.token_hex(32)
        self.secreto = secreto
        self.intentos: dict[str, collections.deque] = collections.defaultdict(collections.deque)

    @classmethod
    def desde_entorno(cls) -> "Autenticador | None":
        """None = panel deshabilitado. Nunca se usa una contraseña por defecto."""
        usuario = os.getenv("ADMIN_USER", "").strip()
        contrasena = os.getenv("ADMIN_PASSWORD", "")
        if not usuario or not contrasena:
            log.warning("Panel web DESHABILITADO: falta ADMIN_USER o ADMIN_PASSWORD en el .env (ver .env.example)")
            return None
        return cls(usuario, contrasena, os.getenv("JWT_SECRET", "").strip() or None)

    def permitir_intento(self, ip: str) -> bool:
        """Ventana deslizante de 60 s por IP. Cuenta todos los intentos, buenos o malos."""
        ahora = time.monotonic()
        cola = self.intentos[ip]
        while cola and ahora - cola[0] > 60:
            cola.popleft()
        if len(cola) >= INTENTOS_POR_MINUTO:
            return False
        cola.append(ahora)
        return True

    def verificar(self, usuario: str, contrasena: str) -> bool:
        # compare_digest tarda lo mismo coincidan o no los caracteres: con == se podría
        # adivinar la contraseña midiendo cuánto tarda la respuesta.
        # Se evalúan los dos siempre (& y no "and") por la misma razón.
        ok_usuario = secrets.compare_digest(usuario.encode(), self.usuario.encode())
        ok_contrasena = secrets.compare_digest(contrasena.encode(), self.contrasena.encode())
        return ok_usuario & ok_contrasena

    def emitir_token(self, usuario: str) -> str:
        ahora = int(time.time())
        return jwt.encode({"sub": usuario, "iat": ahora, "exp": ahora + DURACION_TOKEN_S},
                          self.secreto, algorithm=ALGORITMO)

    def validar_token(self, token: str) -> str | None:
        """Devuelve el usuario admin o None si el token es inválido o venció."""
        try:
            return jwt.decode(token, self.secreto, algorithms=[ALGORITMO])["sub"]
        except jwt.PyJWTError:
            return None

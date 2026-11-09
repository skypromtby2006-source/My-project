"""servidor_local.py (el arranque del .exe): carpeta sin permiso de escritura y admin.txt."""
import os

import pytest

import servidor_local


def test_carpeta_sin_escritura_muestra_mensaje_y_sale(tmp_path, monkeypatch, capsys):
    if getattr(os, "geteuid", lambda: 1)() == 0:   # geteuid no existe en Windows
        pytest.fail("este test no puede correr como root: root escribe aunque la carpeta sea de solo lectura")
    carpeta = tmp_path / "Archivos de programa"
    carpeta.mkdir()
    carpeta.chmod(0o555)   # solo lectura, como Program Files para un usuario normal
    try:
        assert servidor_local.carpeta_escribible(carpeta) is not None
        monkeypatch.setattr(servidor_local, "carpeta_base", lambda: carpeta)
        monkeypatch.setattr("builtins.input", lambda *_: "")
        with pytest.raises(SystemExit) as salida:
            servidor_local.main()
        assert salida.value.code == 2
        texto = capsys.readouterr().out
        assert "descomprime el zip en Documentos o en el Escritorio" in texto
        assert str(carpeta) in texto
        assert list(carpeta.iterdir()) == []   # no dejó admin.txt ni quimica.db a medias
    finally:
        carpeta.chmod(0o755)


def test_admin_txt_se_genera_una_vez_y_se_reusa(tmp_path, monkeypatch):
    for v in ("ADMIN_USER", "ADMIN_PASSWORD", "JWT_SECRET"):
        monkeypatch.delenv(v, raising=False)
    assert servidor_local.carpeta_escribible(tmp_path) is None
    ruta = servidor_local.preparar_admin(tmp_path)
    clave = os.environ["ADMIN_PASSWORD"]
    assert ruta == tmp_path / "admin.txt" and len(clave) == 12
    assert not set(clave) & set("0O1lI")          # legible para copiarla a mano
    for v in ("ADMIN_USER", "ADMIN_PASSWORD", "JWT_SECRET"):
        monkeypatch.delenv(v)
    servidor_local.preparar_admin(tmp_path)
    assert os.environ["ADMIN_PASSWORD"] == clave  # el segundo arranque reusa la misma

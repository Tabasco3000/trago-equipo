"""Cliente de la app de marketing: entra con el usuario y la contraseña de la persona (Basic), guardados en su llavero.
La app aplica permisos, avisos y reglas igual que en el navegador: aquí no se copia ninguna regla."""
import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlsplit

BASE = os.environ.get("TM_BASE", "https://marketing.tragotragotrago.com")
USUARIO = os.environ.get("TM_USUARIO", "sin-usuario")
SERVICIO = "trago-marketing-app"   # security add-generic-password -U -a <usuario> -s trago-marketing-app -w
GUARDAR = "sh '" + os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts/guardar-clave.sh")) + "'"
if not (BASE.startswith("https://") or urlsplit(BASE).hostname == "127.0.0.1"):
    raise SystemExit("TM_BASE tiene que ser https (la contraseña viaja en cada llamada).")


class Error(Exception):
    pass


class SinRedirect(urllib.request.HTTPRedirectHandler):
    # urllib reenvía la contraseña (Authorization) a donde apunte un redirect, también a otro sitio: no se sigue ninguno
    def redirect_request(self, *a, **k):
        return None


_abrir = urllib.request.build_opener(SinRedirect).open
_clave = None
_rechazada = False   # la app traba la entrada con 3 intentos malos (claves.js INTENTOS): tras un rechazo no se vuelve a intentar


def clave():
    global _clave
    if _clave is None:
        _clave = os.environ.get("TM_CLAVE") if urlsplit(BASE).hostname == "127.0.0.1" else None   # TM_CLAVE: solo pruebas locales
    if _clave is None:
        r = subprocess.run(["security", "find-generic-password", "-a", USUARIO, "-s", SERVICIO, "-w"], capture_output=True, text=True)
        if r.returncode:
            raise Error(f"Falta tu contraseña de la app en el llavero. Guárdala con una ventanita de la Mac (nunca por el chat) corriendo:\n{GUARDAR}")
        _clave = r.stdout.rstrip("\n")
    return _clave


def pedir(metodo: str, ruta: str, datos=None):
    """Llama a una ruta de la app (siempre empieza con «/»). Regresa el JSON, o el texto si la ruta contesta texto."""
    global _clave, _rechazada
    if _rechazada:
        raise Error(f"La app ya rechazó tu contraseña en esta sesión; no reintento para no trabarte la entrada (3 intentos = 15 min). "
                    f"Guarda la correcta con «{GUARDAR}» y abre una sesión nueva de Claude.")
    camino = ruta.split("?")[0]   # el Worker resuelve %2e%2e y \ como «..»: la ruta va escrita en claro o no va
    if not ruta.startswith("/") or ".." in camino or "%" in camino or "\\" in camino:
        raise Error(f"Ruta inválida: {ruta}")
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    req = urllib.request.Request(BASE + ruta, data=cuerpo, method=metodo)
    req.add_header("User-Agent", "trago-marketing-mcp/1.0")   # Cloudflare frena el de Python-urllib (error 1010)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{USUARIO}:{clave()}".encode()).decode())
    if cuerpo is not None:
        req.add_header("content-type", "application/json")
    try:
        with _abrir(req, timeout=120) as r:
            txt = r.read().decode()
            tipo = r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="replace")
        e.close()
        if e.code == 401:
            _clave, _rechazada = None, True
            raise Error(f"La app no aceptó tu usuario y contraseña. Guarda la correcta con «{GUARDAR}» y abre una sesión nueva de Claude.")
        if 300 <= e.code < 400:
            raise Error("La app me mandó a otra página (sin permiso para eso o ruta que no existe).")
        try:
            msg = json.loads(txt).get("error")
        except (ValueError, AttributeError):
            msg = None
        raise Error(msg or f"La app contestó {e.code}: {txt[:300]}")
    except urllib.error.URLError as e:
        raise Error(f"No pude llegar a la app: {e.reason}")
    if "json" not in tipo:
        if "html" in tipo:
            raise Error("La app contestó una página en vez de datos (¿ruta del Tablero sin permiso?).")
        return txt
    j = json.loads(txt)
    if isinstance(j, dict) and j.get("error"):
        raise Error(j["error"])
    return j


def subir_a_drive(url_subida: str, ruta: str, mime: str) -> dict:
    """Manda el archivo a la subida que la app le abrió en Drive (resumable; la URL ya trae su permiso). Regresa lo que contesta Drive."""
    u = urlsplit(url_subida)
    if not ((u.scheme == "https" and u.hostname == "www.googleapis.com") or (u.hostname == "127.0.0.1" == urlsplit(BASE).hostname)):
        raise Error("La subida no apunta a Google Drive.")
    with open(ruta, "rb") as f:   # el archivo va por partes desde el disco (un video no se carga entero en memoria)
        req = urllib.request.Request(url_subida, data=f, method="PUT")
        req.add_header("content-type", mime)
        req.add_header("content-length", str(os.path.getsize(ruta)))
        try:
            with _abrir(req, timeout=600) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise Error(f"Drive no recibió «{os.path.basename(ruta)}»: {e.code} {e.read().decode(errors='replace')[:200]}")
        except urllib.error.URLError as e:
            raise Error(f"No pude llegar a Drive: {e.reason}")

"""Pruebas sin red: una app de mentira en localhost anota cada llamada. Correr: python3 -m unittest discover -s tests (desde mcp/)."""
import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TM_CLAVE"] = "secreta"
LLAMADAS = []
ESTADO = {"yo": {"usuario": "luis"}, "hoy": "2026-10-23", "permisos": {"minuta": True},
          "modulos": [{"id": "m1", "nombre": "OCTUBRE 2026", "inicio": "2026-10-01", "fin": "2026-10-31"},
                      {"id": "m2", "nombre": "NOVIEMBRE 2026", "inicio": "2026-11-01", "fin": "2026-11-30",
                       "calendario": {"propuesta": {"pos": {"x2": ["2026-11-19"] * 100}}}}],
          "campanas": [{"id": "c1", "modulo": "m1"}, {"id": "c2", "modulo": "m2", "concepto": "Metro Ciudad TRAGO. " * 40}],
          "minis": [{"id": "n1", "campana": "c1"},
                    {"id": "n2", "campana": "c2", "caract": [["promo", "2x1", {"doc_id": "d1", "cita": "x" * 2000}], ["cover", "MX$100"]]},
                    {"id": "n3", "campana": "c2", "caract": [["otra", "y" * 290] for _ in range(12)]}],
          "contenidos": [{"id": "x2", "campana": "c2", "titulo": "Flyer GUDK", "origen_cita": None, "creado": "2026-10-23T00:00:00Z"}],
          "documentos": [], "minutas": [], "formularios": [],
          "master": [{"nombre": "TRAGOWEEN.", "fechas": ["2026-10-31"]}, {"nombre": "GUDK", "fechas": ["2026-11-20", "2026-11-21"]}],
          "catalogo": {}}


class App(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def responder(self, metodo):
        n = int(self.headers.get("content-length") or 0)
        crudo = self.rfile.read(n) if n else b""
        cuerpo = json.loads(crudo) if crudo and "json" in (self.headers.get("content-type") or "") else crudo or None
        LLAMADAS.append({"metodo": metodo, "ruta": self.path, "cuerpo": cuerpo, "auth": self.headers.get("Authorization"), "origin": self.headers.get("Origin")})
        tipo, extra = "application/json", {}
        if self.path == "/ap/api/planeacion/estado":
            st, r = 200, ESTADO
        elif self.path == "/ap/api/planeacion/evento" and cuerpo.get("nombre") == "REPETIDO":
            st, r = 400, {"error": "«REPETIDO» ya está en Planeación ese día."}
        elif self.path == "/ap/api/pieza/p1":
            st, r = 200, {"pieza": {"titulo": "Flyer GUDK", "estado": "con_luis", "tipo": "imagen", "autor": "america"}}
        elif self.path == "/ap/api/pieza/redirige":
            st, r, extra = 302, {}, {"Location": f"http://127.0.0.1:{PUERTO}/robado"}   # si lo siguiera, llegaría aquí con la contraseña
        elif self.path == "/ap/api/pieza/clave-mala":
            st, r = 401, {"error": "Tu sesión se cerró."}
        elif self.path == "/api/audiencia":
            st, r, tipo = 200, "<html>Tablero</html>", "text/html"
        elif self.path == "/ap/api/reprogramar":
            st, r = 200, {"resultados": [{"id": "p1", "ok": True}, {"id": "p2", "ok": False, "error": "Zernio no dejó"}]}
        elif self.path == "/drive-subida":
            st, r = 200, {"id": "drv1"}
        elif self.path in ("/ap/api/subir", "/ap/api/stock"):
            st, r = 200, {"url": f"http://127.0.0.1:{PUERTO}/drive-subida"}
        else:
            st, r = 200, {"ok": True}
        b = (r if isinstance(r, str) else json.dumps(r)).encode()
        self.send_response(st)
        self.send_header("content-type", tipo)
        self.send_header("content-length", str(len(b)))
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    do_GET = lambda self: self.responder("GET")
    do_POST = lambda self: self.responder("POST")
    do_PUT = lambda self: self.responder("PUT")


SERVIDOR = HTTPServer(("127.0.0.1", 0), App)
PUERTO = SERVIDOR.server_port
threading.Thread(target=SERVIDOR.serve_forever, daemon=True).start()
os.environ["TM_BASE"] = f"http://127.0.0.1:{PUERTO}"

from tm import api, mcp  # noqa: E402  (después de fijar TM_BASE)

DIR = os.path.realpath(tempfile.mkdtemp())   # carpeta permitida solo en las pruebas (no se escribe en las del usuario)
mcp.CARPETAS.append(DIR)


def llamar(herr, **args):
    r = mcp.responder({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": herr, "arguments": args}})["result"]
    return json.loads(r["content"][0]["text"]), r["isError"]


def archivo(nombre, datos):
    ruta = os.path.join(DIR, nombre)
    with open(ruta, "wb") as f:
        f.write(datos)
    return ruta


class Pruebas(unittest.TestCase):
    def setUp(self):
        LLAMADAS.clear()
        mcp._pendientes.clear()
        api._rechazada = False
        mcp._aviso_dado = True   # el aviso de versión se prueba aparte

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DIR, ignore_errors=True)
        shutil.rmtree(DIR + "X", ignore_errors=True)

    def test_libre_va_directo_con_su_usuario(self):
        r, err = llamar("evento_crear", nombre="CHINGU CLUB", inicio="2026-11-14")
        self.assertFalse(err)
        self.assertEqual(LLAMADAS[0]["ruta"], "/ap/api/planeacion/evento")
        self.assertEqual(LLAMADAS[0]["cuerpo"], {"nombre": "CHINGU CLUB", "inicio": "2026-11-14"})
        self.assertEqual(LLAMADAS[0]["auth"], "Basic " + base64.b64encode(b"luis:secreta").decode())
        self.assertIsNone(LLAMADAS[0]["origin"])   # sin Origin: la app solo frena peticiones de otra página web

    def test_error_de_la_app_llega_con_su_mensaje(self):
        r, err = llamar("evento_crear", nombre="REPETIDO", inicio="2026-11-14")
        self.assertTrue(err)
        self.assertIn("ya está en Planeación", r["error"])

    def test_falta_dato(self):
        r, err = llamar("evento_crear", nombre="X")
        self.assertTrue(err)
        self.assertEqual(LLAMADAS, [])

    def test_delicado_no_corre_hasta_confirmar_y_una_sola_vez(self):
        r, err = llamar("pieza_accion", id="p1", accion="aprobar")
        self.assertFalse(err)
        self.assertTrue(r["falta_ok"])
        self.assertRegex(r["codigo"], r"^\d{6}$")
        self.assertEqual(r["pieza"]["titulo"], "Flyer GUDK")                    # Luis ve el nombre, no solo el id
        self.assertEqual([c["metodo"] for c in LLAMADAS], ["GET"])               # solo leyó la pieza
        LLAMADAS.clear()
        r2, err = llamar("confirmar", codigo=r["codigo"])
        self.assertFalse(err)
        self.assertEqual(LLAMADAS[0]["cuerpo"], {"id": "p1", "accion": "aprobar"})
        _, err = llamar("confirmar", codigo=r["codigo"])
        self.assertTrue(err)
        self.assertEqual(len(LLAMADAS), 1)

    def test_codigo_falso_o_vencido_no_corre(self):
        r, _ = llamar("borrar", tabla="contenido", id="x1")
        _, err = llamar("confirmar", codigo="999999" if r["codigo"] != "999999" else "111111")
        self.assertTrue(err)
        mcp._pendientes[r["codigo"]] = mcp._pendientes[r["codigo"]][:2] + (0,)
        _, err = llamar("confirmar", codigo=r["codigo"])
        self.assertTrue(err)
        self.assertEqual(LLAMADAS, [])

    def test_lo_confirmado_es_lo_que_se_enseno(self):
        datos = {"minuta": "u1", "contenidos": [{"ref": "c1", "titulo": "Flyer"}]}
        r, _ = llamar("minuta_aprobar", **datos)
        r["datos"]["contenidos"][0]["titulo"] = "otra cosa"   # aunque se cambie la copia que regresó
        llamar("confirmar", codigo=r["codigo"])
        self.assertEqual(LLAMADAS[0]["cuerpo"], datos)

    def test_accion_fija_no_se_cambia_desde_fuera(self):
        r, _ = llamar("caption_guardar", id="p1", caption="hola", accion="aprobar")
        LLAMADAS.clear()
        llamar("confirmar", codigo=r["codigo"])
        self.assertEqual(LLAMADAS[0]["cuerpo"]["accion"], "caption")

    def test_delicadas_segun_sus_datos(self):
        casos = [("contenido_guardar", {"id": "x2", "titulo": "Flyer GUDK v2"}, False),
                 ("contenido_guardar", {"id": "x2", "fecha_pub": "2026-11-19"}, True),
                 ("contenido_guardar", {"unidad": "n2", "titulo": "Nuevo", "categorias": ["Flyer"], "fecha_pub": "2026-11-19"}, False),
                 ("calendario", {"modulo": "m2", "accion": "borrador"}, False),
                 ("calendario", {"modulo": "m2", "accion": "proponer"}, True),
                 ("caracteristica_editar", {"mini": "n2", "clave": "promo", "valor": "2x1"}, False),
                 ("caracteristica_editar", {"mini": "n2", "indice": 0, "quitar": True}, True),
                 ("caracteristica_editar", {"mini": "n2", "indice": 0, "valor": ""}, True),
                 ("mini_guardar", {"id": "n2", "fechas": ["2026-11-20"]}, False),
                 ("mini_guardar", {"id": "n2", "caract": [["promo", "2x1"]]}, True),
                 ("cambiar_tipo", {"de": "contenido", "id": "x2", "a": "caracteristica"}, True),
                 ("stock_subir", {"archivos": ["/x"], "negocio": "local"}, True),
                 ("correccion_agregar", {"id": "p9", "texto": "más grande"}, True)]
        for herr, args, delicada in casos:
            r, _ = llamar(herr, **args)
            self.assertEqual(bool(isinstance(r, dict) and r.get("falta_ok")), delicada, (herr, args))

    def test_todas_las_delicadas_avisan_en_su_descripcion(self):
        for n, (d, _, _, _, dl) in mcp.HERRAMIENTAS.items():
            if dl is not False:
                self.assertIn("OK", d, n)

    def test_tablero_anotar_no_sale_de_su_lista(self):
        for que in ("../bot/enviar-reporte", "reporte"):
            _, err = llamar("tablero_anotar", que=que, datos={})
            self.assertTrue(err, que)
        _, err = llamar("tablero_ver", que="../ap/api/eliminar")
        self.assertTrue(err)
        self.assertEqual(LLAMADAS, [])

    def test_ids_y_rutas_raras_no_salen(self):
        _, err = llamar("pieza_ver", id="../../google/conectar")
        self.assertTrue(err)
        _, err = llamar("minuta_ver", id="x/../../frameio/conectar")
        self.assertTrue(err)
        self.assertEqual(LLAMADAS, [])
        r, _ = llamar("app_llamar", metodo="GET", ruta="@evil.com/x")
        _, err = llamar("confirmar", codigo=r["codigo"])
        self.assertTrue(err)
        self.assertEqual(LLAMADAS, [])

    def test_no_sigue_redirects_con_la_contrasena(self):
        _, err = llamar("pieza_ver", id="redirige")
        self.assertTrue(err)
        self.assertEqual([c["ruta"] for c in LLAMADAS], ["/ap/api/pieza/redirige"])

    def test_tras_un_rechazo_de_contrasena_no_reintenta(self):
        _, err = llamar("pieza_ver", id="clave-mala")
        self.assertTrue(err)
        r, err = llamar("evento_crear", nombre="X", inicio="2026-11-14")
        self.assertTrue(err)
        self.assertIn("no reintento", r["error"])
        self.assertEqual(len(LLAMADAS), 1)

    def test_pagina_html_no_cuenta_como_exito(self):
        _, err = llamar("tablero_ver", que="audiencia")
        self.assertTrue(err)

    def test_reprogramar_a_medias_es_error(self):
        r, _ = llamar("reprogramar", cambios=[{"id": "p1", "fecha": "x"}, {"id": "p2", "fecha": "y"}])
        r, err = llamar("confirmar", codigo=r["codigo"])
        self.assertTrue(err)
        self.assertIn("Zernio no dejó", r["error"])

    def test_solo_sube_archivos_de_carpetas_permitidas(self):
        os.makedirs(os.path.join(DIR, ".oculto"), exist_ok=True)
        oculto = archivo(os.path.join(".oculto", "x.md"), b"secreto")
        os.makedirs(DIR + "X", exist_ok=True)   # mismo prefijo, otra carpeta
        vecino = os.path.join(DIR + "X", "a.md")
        open(vecino, "w").write("x")
        enlace = os.path.join(DIR, "enlace.md")
        if not os.path.exists(enlace):
            os.symlink("/etc/hosts", enlace)   # un enlace que apunta afuera
        for ruta in ["~/.ssh/id_ed25519", "/etc/hosts", os.path.join(DIR, "..", ".zshrc"), oculto, vecino, enlace]:
            r, _ = llamar("minuta_subir", campana="c2", archivos=[ruta])
            r, err = llamar("confirmar", codigo=r["codigo"])
            self.assertTrue(err, ruta)
            self.assertIn("Solo subo", r["error"], ruta)
        self.assertEqual(LLAMADAS, [])

    def test_minuta_subir_manda_el_archivo_en_base64(self):
        ruta = archivo("minuta.md", "# Minuta de noviembre\nGUDK 20-21".encode())
        r, _ = llamar("minuta_subir", campana="c2", archivos=[ruta])
        self.assertEqual(LLAMADAS, [])   # con archivos pide OK: los sube al Drive del equipo
        _, err = llamar("confirmar", codigo=r["codigo"])
        self.assertFalse(err)
        a = LLAMADAS[0]["cuerpo"]["archivos"][0]
        self.assertEqual(a["nombre"], "minuta.md")
        self.assertEqual(base64.b64decode(a["base64"]).decode(), "# Minuta de noviembre\nGUDK 20-21")

    def test_pieza_subir_sube_a_drive_y_crea_la_pieza(self):
        ruta = archivo("flyer.png", b"\x89PNG")
        r, _ = llamar("pieza_subir", archivos=[ruta], plan="x2")
        self.assertEqual(LLAMADAS, [])
        r2, err = llamar("confirmar", codigo=r["codigo"])
        self.assertFalse(err, r2)
        self.assertEqual([c["ruta"] for c in LLAMADAS], ["/ap/api/subir", "/drive-subida", "/ap/api/pieza"])
        self.assertEqual(LLAMADAS[1]["cuerpo"], b"\x89PNG")
        self.assertIsNone(LLAMADAS[1]["auth"])   # la contraseña de la app nunca va a Drive
        self.assertEqual(LLAMADAS[2]["cuerpo"]["archivos"], [{"id": "drv1", "nombre": "flyer.png", "mime": "image/png", "tam": 4}])
        self.assertIs(LLAMADAS[2]["cuerpo"]["analizador"], False)

    def test_pieza_subir_sin_contenido_no_sube_nada(self):
        ruta = archivo("flyer2.png", b"\x89PNG")
        r, _ = llamar("pieza_subir", archivos=[ruta])
        _, err = llamar("confirmar", codigo=r["codigo"])
        self.assertTrue(err)
        r, _ = llamar("pieza_subir", archivos=[ruta], noContenido=True)
        _, err = llamar("confirmar", codigo=r["codigo"])
        self.assertTrue(err)
        self.assertEqual(LLAMADAS, [])

    def test_planeacion_ver_un_mes_y_sin_vacios(self):
        r, err = llamar("planeacion_ver", mes="noviembre")
        self.assertFalse(err)
        self.assertEqual([m["id"] for m in r["modulos"]], ["m2"])
        self.assertEqual([c["id"] for c in r["campanas"]], ["c2"])
        self.assertEqual([x["id"] for x in r["minis"]], ["n2", "n3"])
        self.assertEqual(r["minis"][0]["caract"], [["promo", "2x1"], ["cover", "MX$100"]])   # sin la cita, pero completas
        self.assertEqual(len(r["minis"][1]["caract"]), 12)                                     # una mini grande no se queda sin características
        self.assertEqual(r["campanas"][0]["concepto"], "Metro Ciudad TRAGO. " * 40)              # un concepto largo no se recorta
        self.assertIn("propuesta", r["modulos"][0]["calendario"])
        self.assertEqual([e["nombre"] for e in r["eventos"]], ["GUDK"])
        self.assertEqual(r["contenidos"], [{"id": "x2", "campana": "c2", "titulo": "Flyer GUDK"}])
        r, err = llamar("planeacion_ver", mes="diciembre")
        self.assertTrue(err)
        self.assertIn("NOVIEMBRE 2026", r["error"])

    def test_cada_herramienta_esta_clasificada(self):
        # Toda herramienta nueva tiene que entrar a una de estas listas: así nadie agrega una que avise o borre sin candado
        libres = {"quien_soy", "planeacion_ver", "eventos_ver", "mes_guardar", "campana_guardar", "evento_crear", "contenido_clonar", "ordenar",
                  "restaurar", "documentos_agregar", "minuta_crear", "minuta_procesar", "minuta_ver", "vigilante_ver", "piezas_ver", "pieza_ver",
                  "ficha_ver", "pieza_titulo", "pieza_contenido", "mejor_hora", "tablero_ver", "tablero_anotar", "avisos_ver", "equipo_ver",
                  "mejoras_ver", "app_leer", "confirmar"}
        segun_datos = {"mini_guardar", "caracteristica_editar", "contenido_guardar", "minuta_subir", "calendario", "ficha_editar", "correccion_marcar"}
        for n, (_, _, _, _, dl) in mcp.HERRAMIENTAS.items():
            if n in libres:
                self.assertIs(dl, False, n)
            elif n in segun_datos:
                self.assertTrue(callable(dl), n)
            else:
                self.assertIs(dl, True, n)

    def test_resultado_que_no_se_hizo_lo_dice(self):
        r = mcp.revisado({"herramienta": "borrar", "resultado": {"confirmarPiezas": [{"titulo": "Flyer"}]}})
        self.assertIs(r["hecho"], False)
        r = mcp.revisado({"confirmar": [{"id": "x2"}]})
        self.assertIs(r["hecho"], False)
        r = mcp.revisado({"herramienta": "minuta_aprobar", "resultado": {"contenidos": [], "errores": [{"ref": "c1"}]}})
        self.assertEqual(r["hecho"], "a medias")
        self.assertNotIn("hecho", mcp.revisado({"ok": True}))

    def test_ficha_editar(self):
        _, err = llamar("ficha_editar", id="p1", cambios={"estado": "programada"})
        self.assertTrue(err)
        r, _ = llamar("ficha_editar", id="p1", cambios={"caption": "hola"})
        self.assertTrue(r["falta_ok"])
        r, err = llamar("ficha_editar", id="p1", cambios={"collabs": ["chinguclub.kr"]})
        self.assertFalse(err)
        self.assertEqual(LLAMADAS[-1]["cuerpo"], {"id": "p1", "cambios": {"collabs": ["chinguclub.kr"]}, "accion": "ficha"})

    def test_preguntar_con_puntos_y_ids_con_salto(self):
        _, err = llamar("tablero_ver", que="preguntar", q="qué pasó ayer...")
        self.assertFalse(err)
        _, err = llamar("pieza_ver", id="abc\n")
        self.assertTrue(err)

    def test_app_leer_solo_lee_rutas_de_datos(self):
        _, err = llamar("app_leer", ruta="/ap/api/planeta")
        self.assertFalse(err)
        self.assertEqual(LLAMADAS[-1]["metodo"], "GET")
        for ruta in ("/bot/gente", "/ap/google/conectar", "/ap/api/../google/conectar", "/ap/api/%2e%2e/%2e%2e/bot/gente",
                     "/api/%2E%2e/bot/preguntar?q=x", "/ap/api/.%2e/google/conectar", "/ap/api/..\\bot/gente", "/ap/api/./x", "/ap/api/telegram"):
            _, err = llamar("app_leer", ruta=ruta)
            self.assertTrue(err, ruta)
        self.assertEqual(len(LLAMADAS), 1)

    def test_rutas_codificadas_no_pasan_ni_por_herramientas_con_candado(self):
        r, _ = llamar("app_llamar", metodo="POST", ruta="/ap/api/%2e%2e/%2e%2e/bot/enviar-reporte")
        _, err = llamar("confirmar", codigo=r["codigo"])
        self.assertTrue(err)
        self.assertEqual(LLAMADAS, [])

    def test_correccion_marcar_sin_hecho_la_marca_hecha(self):
        llamar("correccion_marcar", cid=5)
        self.assertEqual(LLAMADAS[0]["cuerpo"], {"hecho": True, "cid": 5})
        llamar("correccion_marcar", cid=5, hecho=False)
        self.assertEqual(LLAMADAS[1]["cuerpo"], {"hecho": False, "cid": 5})

    def test_version_nueva_solo_de_pieza_propia_regresada(self):
        ruta = archivo("v2.png", b"\x89PNG")
        r, _ = llamar("pieza_subir", archivos=[ruta], pieza="p1")   # p1 es de América y está con Dupe
        r, err = llamar("confirmar", codigo=r["codigo"])
        self.assertTrue(err)
        self.assertIn("no está en tus manos", r["error"])
        self.assertEqual([c["ruta"] for c in LLAMADAS], ["/ap/api/pieza/p1"])   # no subió nada a Drive

    def test_revisado_corre_en_llamadas_libres_y_no_desenvuelve_lecturas(self):
        viejo = mcp.HERRAMIENTAS["contenido_guardar"]
        mcp.HERRAMIENTAS["contenido_guardar"] = viejo[:3] + (lambda a: {"confirmar": [{"id": "x2"}]}, False)
        try:
            r, _ = llamar("contenido_guardar", id="x2", titulo="otro")
            self.assertIs(r["hecho"], False)
        finally:
            mcp.HERRAMIENTAS["contenido_guardar"] = viejo
        self.assertNotIn("hecho", mcp.revisado({"resultado": {"errores": [1]}, "estado": "por_aprobar"}))   # p. ej. lo que regresa minuta_ver

    def test_subida_solo_a_drive_por_https(self):
        for url in ("http://www.googleapis.com/upload/x", "https://evil.com/upload"):
            with self.assertRaisesRegex(api.Error, "no apunta a Google Drive"):
                api.subir_a_drive(url, archivo("z.png", b"1"), "image/png")

    def test_aviso_de_version_nueva_una_sola_vez(self):
        viejo = mcp.actualizar.pendiente
        mcp.actualizar.pendiente = lambda: "- MCP: algo nuevo (2026-10-24)"
        mcp._aviso_dado = False
        try:
            primera = mcp.responder({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "eventos_ver", "arguments": {}}})["result"]
            segunda = mcp.responder({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "eventos_ver", "arguments": {}}})["result"]
        finally:
            mcp.actualizar.pendiente = viejo
        self.assertEqual(len(primera["content"]), 2)
        self.assertIn("HAY VERSIÓN NUEVA", primera["content"][1]["text"])
        self.assertIn("Nunca la instales sin su sí", primera["content"][1]["text"])
        self.assertEqual(len(segunda["content"]), 1)

    def test_actualizar_pide_ok(self):
        r, _ = llamar("actualizar")
        self.assertTrue(r["falta_ok"])

    def test_lista_de_herramientas(self):
        r = mcp.responder({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
        self.assertEqual(len(r), len(mcp.HERRAMIENTAS))
        self.assertIn("confirmar", [t["name"] for t in r])

    def test_mensaje_mal_formado_no_tumba(self):
        r = mcp.responder({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {}})
        self.assertEqual(r["id"], 7)
        self.assertTrue(r["result"]["isError"])


if __name__ == "__main__":
    unittest.main()

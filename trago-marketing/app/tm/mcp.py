"""MCP delgado (stdio, JSON-RPC) de la app de marketing de TRAGO.: cada herramienta llama a la misma ruta que usa el navegador.
Leer y armar corre directo. Lo delicado (avisa al equipo, sale a redes o a Zernio, borra, mete la minuta al calendario) no corre:
regresa qué va a pasar y un código, y solo la herramienta `confirmar` con ese código lo hace, después del «sí» de la persona."""
import base64
import json
import mimetypes
import os
import re
import secrets
import sys
import time
import traceback
from urllib.parse import quote

from . import actualizar, api

CANDADO = (" PIDE EL OK DE LA PERSONA: esta llamada no toca la app; regresa qué va a pasar y un código. Enséñaselo a la persona con sus nombres, "
           "espera su «sí» explícito en el chat y solo entonces llama `confirmar` con ese código.")
S, N, B, A, O = {"type": "string"}, {"type": "number"}, {"type": "boolean"}, {"type": "array"}, {"type": "object"}
VIGENCIA = 600   # segundos que vale un código
_pendientes = {}  # código → (herramienta, datos, vence): lo que corre al confirmar es exactamente lo que se enseñó
ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# Solo se suben archivos de estas carpetas (nada oculto: .ssh, .env…). Una minuta o un DM pueden traer instrucciones escondidas.
CASA = os.path.expanduser("~")
CARPETAS = [os.path.join(CASA, c) for c in ("Desktop", "Downloads", "Documents", "trago-marketing", "Library/CloudStorage")]
NEGOCIOS = ["global", "local", "peda", "ninxs", "feria", "catering", "traguito", "abarrotes"]   # biblioteca.js STOCK


def id_ok(x):
    if not ID.fullmatch(str(x or "")):
        raise api.Error(f"Id inválido: {x}")
    return str(x)


def plan(ruta):   # /ap/api/planeacion/<ruta> con los datos tal cual
    return lambda a: api.pedir("POST", "/ap/api/planeacion/" + ruta, a)


def ap(ruta):
    return lambda a: api.pedir("POST", "/ap/api/" + ruta, a)


def accion(nombre_accion):
    return lambda a: api.pedir("POST", "/ap/api/accion", {**a, "accion": nombre_accion or a.get("accion")})


def corto(x, tope=400, fuera=()):
    """Aligera una fila: sin vacíos ni fechas de sistema; un texto largo se recorta y lo que pesa mucho (fichas, análisis) se
    quita, pero se dice cuál en `_omitido` (para que nadie crea que no existe)."""
    out, omitido = {}, []
    for k, v in x.items():
        if v is None or v is False or v in ("", [], {}) or k in ("creado", "actualizado", "borrado", *fuera):
            continue
        if isinstance(v, str) and len(v) > tope:
            v = v[:tope] + "… (recortado)"
        elif not isinstance(v, str) and len(json.dumps(v, ensure_ascii=False)) > tope:
            omitido.append(k)
            continue
        out[k] = v
    return {**out, "_omitido": omitido} if omitido else out


FECHA = "hora de CDMX, exactamente AAAA-MM-DDTHH:MM (p. ej. 2026-11-14T19:00)"
CITAS = ("origen", "origen_fuentes", "origen_cita", "origen_doc", "origen_inicio", "origen_fin")


def sin_citas(x, detalle, fuera=()):   # las citas de la minuta (origen*) pesan la mitad de un mes; solo con `detalle`
    return corto(x, 20000, fuera) if detalle else corto(x, 1500, CITAS + fuera)


def planeacion_ver(a):
    e = api.pedir("GET", "/ap/api/planeacion/estado")
    mes = str(a.get("mes") or "").strip().lower()
    base = {"yo": e["yo"], "hoy": e["hoy"], "permisos": e["permisos"]}
    if not mes:
        return {**base, "meses_y_proyectos": [corto(m) for m in e["modulos"]],
                "nota": "Pasa `mes` (id o parte del nombre, p. ej. «noviembre») para ver todo lo de ese mes."}
    mods = [m for m in e["modulos"] if m["id"] == mes or mes in m["nombre"].lower()]
    if not mods:
        raise api.Error(f"No hay mes ni proyecto que se llame «{a['mes']}». Los que hay: " + ", ".join(m["nombre"] for m in e["modulos"]))
    mids = {m["id"] for m in mods}
    camps = [c for c in e["campanas"] if c["modulo"] in mids]
    cids = {c["id"] for c in camps}
    ini, fin = min(m["inicio"] for m in mods), max(m["fin"] for m in mods)
    det = bool(a.get("detalle"))
    de = lambda k: [sin_citas(x, det) for x in e[k] if x.get("campana") in cids]
    # las características se quedan siempre; sin `detalle`, sin su cita
    # las características van completas siempre (sin `detalle`, sin su cita): fuera del tope de `corto`
    minis = [{**sin_citas(m, det, ("caract",)), "caract": m.get("caract") if det else [c[:2] for c in m.get("caract") or []]}
             for m in e["minis"] if m.get("campana") in cids]
    return {**base, "modulos": [corto(m, 20000) for m in mods], "campanas": [corto(c, 20000) for c in camps], "minis": minis,
            "contenidos": de("contenidos"), "documentos": de("documentos"), "minutas": de("minutas"),
            "formularios": de("formularios"), "eventos": [x for x in e["master"] if x["fechas"][-1] >= ini and x["fechas"][0] <= fin],
            "catalogo": e["catalogo"]}


def vigilante_ver(a):
    v = api.pedir("GET", "/ap/api/planeacion/vigilante")
    pend = v.get("pendientes", [])
    otros = {o.get("id"): {"id": o.get("id"), "titulo": o.get("titulo")} for p in pend for o in (p.get("otros") or [])}   # la misma lista en cada una: va una vez
    return {**v, "pendientes": [{**corto(p, 1500, ("sugeridos", "otros")), "sugeridos": [corto(x, 300) for x in (p.get("sugeridos") or [])[:5]]}
                                for p in pend], "otros_contenidos": list(otros.values())}


def piezas_ver(a):
    r = api.pedir("GET", "/ap/api/piezas")
    est = {s.strip() for s in str(a.get("estado") or "").split(",") if s.strip()}
    q = str(a.get("buscar") or "").lower()
    ps = [corto(p) for p in r["piezas"] if (not est or p.get("estado") in est) and q in str(p.get("titulo", "")).lower()]
    return {"yo": r["yo"], "total": len(ps), "piezas": ps[: int(a.get("max") or 60)]}


def avisos_ver(a):
    n = int(a.get("max") or 30)
    v = api.pedir("GET", "/ap/api/vivo")
    return {"ahora": v.get("ahora"), "telegram": [corto(x, 1200) for x in v.get("tg", [])[:n]], "movimientos": [corto(x, 800) for x in v.get("movs", [])[:n]],
            "accesos": v.get("accesos", [])[:10]}


def leer(ruta, tope=None):
    real = os.path.realpath(os.path.expanduser(str(ruta)))
    if not any(real.startswith(c + os.sep) for c in CARPETAS) or any(p.startswith(".") and p != ".." for p in os.path.relpath(real, CASA).split(os.sep)):
        raise api.Error(f"Solo subo archivos de Escritorio, Descargas, Documentos, Google Drive o el repo de la app (nada oculto): {ruta}")
    if not os.path.isfile(real):
        raise api.Error(f"No encontré el archivo {ruta}")
    tam = os.path.getsize(real)
    if tope and tam > tope:
        raise api.Error(f"«{os.path.basename(real)}» pesa más de {tope // 2**20} MB.")
    return real, mimetypes.guess_type(real)[0] or "application/octet-stream", tam


def minuta_subir(a):
    archivos = []
    for r in a.get("archivos") or []:
        ruta, mime, _ = leer(r, 10 * 2**20)
        with open(ruta, "rb") as f:
            archivos.append({"nombre": os.path.basename(ruta), "tipo": mime, "base64": base64.b64encode(f.read()).decode()})
    return api.pedir("POST", "/ap/api/planeacion/minuta/subir", {"campana": a["campana"], "links": a.get("links") or [], "archivos": archivos})


def subir_archivo(ruta, abrir):
    ruta, mime, tam = leer(ruta)
    nombre = os.path.basename(ruta)
    url = abrir({"drive": True, "nombre": nombre, "mime": mime, "tam": tam})["url"]
    d = api.subir_a_drive(url, ruta, mime)
    return {"id": d["id"], "nombre": nombre, "mime": mime, "tam": tam}


def pieza_subir(a):
    # Lo que la app exige se revisa ANTES de subir a Drive: si falla después, el archivo queda huérfano en «En revisión»
    if a.get("noContenido") and not a.get("campana"):
        raise api.Error("Lo físico («No es contenido») va anclado a una campaña: falta `campana`.")
    if not a.get("noContenido") and not any(a.get(k) for k in ("pieza", "plan", "planNuevo", "planOmitir", "planDelegar")):
        raise api.Error("Falta qué contenido de la Planeación es: `plan`, `planNuevo`, `planOmitir` (Dupe/Fradell) o `planDelegar`.")
    if a.get("pieza"):
        p = api.pedir("GET", "/ap/api/pieza/" + id_ok(a["pieza"]))["pieza"]
        if p.get("autor") != api.USUARIO or p.get("estado") != "con_autor":
            raise api.Error(f"«{p.get('titulo')}» no está en tus manos (estado {p.get('estado')}, de {p.get('autor')}): no se le sube versión.")
    for r in a["archivos"]:
        leer(r)
    archivos = [subir_archivo(r, lambda b: api.pedir("POST", "/ap/api/subir", b)) for r in a["archivos"]]
    datos = {k: v for k, v in a.items() if k != "archivos"}
    return api.pedir("POST", "/ap/api/pieza", {"analizador": False, **datos, "archivos": archivos})


def stock_subir(a):
    if a["negocio"] not in NEGOCIOS:
        raise api.Error("negocio: " + ", ".join(NEGOCIOS))
    for r in a["archivos"]:
        leer(r)
    return [subir_archivo(r, lambda b: api.pedir("POST", "/ap/api/stock", {**b, "negocio": a["negocio"]})) for r in a["archivos"]]


def reprogramar(a):
    r = api.pedir("POST", "/ap/api/reprogramar", a)
    malas = [x for x in r.get("resultados", []) if not x.get("ok")]
    if malas:   # la app contesta 200 aunque alguna no se haya movido
        raise api.Error(f"Se movieron {len(r['resultados']) - len(malas)}; no se movieron: " + json.dumps(malas, ensure_ascii=False))
    return r


TABLERO = {"reporte": ("POST", "/api/reporte?dia={dia}"), "alertas": ("GET", "/bot/alertas"), "audiencia": ("GET", "/api/audiencia"),
           "cuentas": ("GET", "/api/cuentas-num?desde={desde}&hasta={hasta}"), "pauta": ("GET", "/api/pauta-num?desde={desde}&hasta={hasta}"),
           "gente": ("GET", "/bot/gente"), "preguntar": ("GET", "/bot/preguntar?q={q}"), "eventos": ("GET", "/api/eventos")}
ANOTAR = ["kpi", "asig", "asigp", "modelo"]


def tablero_ver(a):
    if a["que"] not in TABLERO:
        raise api.Error("que: " + ", ".join(TABLERO))
    metodo, ruta = TABLERO[a["que"]]
    return api.pedir(metodo, ruta.format(**{k: quote(str(a.get(k) or "")) for k in ("dia", "desde", "hasta", "q")}), {} if metodo == "POST" else None)


def tablero_anotar(a):
    if a["que"] not in ANOTAR:
        raise api.Error("que: " + ", ".join(ANOTAR))
    return api.pedir("POST", "/api/" + a["que"], a["datos"])


LEER = re.compile(r"^/(ap/api|api)/[A-Za-z0-9_/.-]+(\?[A-Za-z0-9_=&.:-]*)?$")
NO_LEER = ("/ap/api/telegram",)   # GET que escribe (genera el código para conectar Telegram)


def app_leer(a):
    ruta = str(a["ruta"])
    if not LEER.match(ruta) or ruta.split("?")[0] in NO_LEER or {".", ".."} & set(ruta.split("?")[0].split("/")):
        raise api.Error("Solo rutas de lectura /ap/api/… o /api/… escritas en claro (sin %, \\, . ni ..).")
    return api.pedir("GET", ruta)


def minuta_ver(a):
    m = api.pedir("GET", "/ap/api/planeacion/minuta/" + id_ok(a["id"]))
    if not a.get("detalle"):
        for d in m.get("documentos") or []:
            if len(d.get("texto") or "") > 3000:
                d["texto"] = d["texto"][:3000] + "… (recortado; `detalle`: true lo trae entero)"
    return m


FICHA = {"fecha", "ahora", "caption", "collabs", "etiquetados", "comenta", "tiktokTitulo", "tiktokMixto", "cancion", "redes", "tipoContenido", "etapaEmbudo"}


def ficha_editar(a):
    raras = set(a["cambios"]) - FICHA
    if raras:
        raise api.Error("La ficha no tiene: " + ", ".join(sorted(raras)))
    return accion("ficha")(a)


def app_llamar(a):
    m = str(a["metodo"]).upper()
    if m not in ("GET", "POST") or not re.match(r"^/(ap|api|bot)/", str(a["ruta"])):
        raise api.Error("metodo GET|POST y una ruta que empiece con /ap/, /api/ o /bot/.")
    return api.pedir(m, a["ruta"], (a.get("datos") or {}) if m == "POST" else None)


def quien_soy(a):
    r = {k: v for k, v in planeacion_ver({}).items() if k in ("yo", "permisos", "hoy")}
    try:
        r["conector"] = {"version": actualizar.version(), "version_nueva": actualizar.pendiente()}
    except Exception as e:
        r["conector"] = {"error": str(e)}
    return r


EVENTO = {"nombre": S, "inicio": S, "fin": S, "negocio": S, "artistas": S, "residentes": S}
CONT = {"id": S, "unidad": S, "titulo": S, "categorias": A, "responsables": A, "departamento": S, "formato": S, "fecha_pub": S,
        "fecha_entrega": S, "nota": S, "extra": B, "motivo": S, "referencia": O, "drive": S, "flyer": B, "confirmar": B}
SUBIR = {"archivos": A, "pieza": S, "titulo": S, "plan": S, "planNuevo": O, "planOmitir": B, "planDelegar": B, "noContenido": B, "campana": S, "mini": S,
         "directo": B, "nota": S}
# Algunas son delicadas solo con ciertos datos: borrar una característica, reemplazar la lista entera, mover fecha/flyer/mini.
contenido_delicado = lambda a: bool(a.get("id")) and any(k in a for k in ("fecha_pub", "flyer", "unidad"))
caract_delicado = lambda a: bool(a.get("quitar")) or (a.get("indice") not in (None, "") and not str(a.get("valor") or "").strip())

# nombre: (descripción, propiedades, requeridas, función, delicado: bool o función de los datos)
HERRAMIENTAS = {
    # ---- Planeación ----
    "quien_soy": ("Con qué usuario entra el conector, qué permisos de Planeación tiene, qué versión del conector corre y si hay una nueva.", {}, [],
                  quien_soy, False),
    "planeacion_ver": ("Planeación. Sin `mes`: la lista de meses y proyectos independientes. Con `mes` (id o parte del nombre): sus campañas, "
                       "mini campañas (con características), contenidos, documentos, minutas, formularios y los eventos de esas fechas. `detalle`: true "
                       "agrega de qué parte de la minuta salió cada cosa (pesa el doble) y lo recortado u omitido (`_omitido`). Nunca guardes un texto "
                       "que termine en «(recortado)»: pide `detalle` primero.", {"mes": S, "detalle": B}, [], planeacion_ver, False),
    "eventos_ver": ("Eventos que vienen (la lista de la app: Logística, los creados a mano y la hoja del Contestador).", {}, [],
                    lambda a: api.pedir("GET", "/ap/api/eventos"), False),
    "mes_guardar": ("＋ Mes o ＋ Proyecto independiente (sin `id`), o editar uno (con `id`: nombre, concepto, fechas). tipo: «mes» o «independiente». "
                    "Fechas AAAA-MM-DD; un mes sin `fin` acaba el último día. negocio: local (default), momento, mp4, archivo, peda, ninxs, feria, "
                    "catering, traguito, abarrotes. Un mes nuevo trae su «Campaña de eventos» y la mini «Comunicación del mes». No avisa a nadie.",
                    {"id": S, "tipo": S, "nombre": S, "inicio": S, "fin": S, "concepto": S, "tipo_campana": S, "negocio": S}, [], plan("modulo"), False),
    "campana_guardar": ("Crear una campaña dentro de un mes (`modulo` = id del mes) o editar una (`id`): nombre, concepto, tipo_nombre. No avisa.",
                        {"id": S, "modulo": S, "nombre": S, "concepto": S, "tipo_nombre": S}, [], plan("campana"), False),
    "mini_guardar": ("Crear una mini campaña (`campana`, `nombre`, `fechas` [AAAA-MM-DD], `caract` [[clave, valor]…]) o editar nombre y fechas (`id`). "
                     "Claves: dress code, concepto, happening, dinámica, cover, promo de cover gratis, promo, artistas, residentes, souvenir, decoración, otra. "
                     "Para cambiar características de una que ya existe usa caracteristica_editar (mandar `caract` con `id` reemplaza la lista entera y pide OK). No avisa.",
                     {"id": S, "campana": S, "nombre": S, "fechas": A, "caract": A}, [], plan("mini"), lambda a: bool(a.get("id")) and "caract" in a),
    "caracteristica_editar": ("Una característica de una mini campaña: agregar (sin `indice`) o editar (`indice` desde 0). Quitarla (`quitar`: true) pide OK.",
                              {"mini": S, "indice": N, "clave": S, "valor": S, "quitar": B}, ["mini"], plan("caract"), caract_delicado),
    "evento_crear": ("«＋ Evento»: crea el evento y su mini campaña en la Campaña de eventos del mes de ese negocio (el mes tiene que existir). "
                     "`inicio`/`fin` AAAA-MM-DD (fin solo si dura más de un día). No avisa.", EVENTO, ["nombre", "inicio"], plan("evento"), False),
    "contenido_guardar": ("Crear un contenido (`unidad` = id de la mini campaña o campaña, `titulo`, `categorias`) o editarlo (`id`). Categorías: Flyer, "
                          "Carrusel, Moving poster DJ, Moving poster hablado, Vlog, BTS, Storytelling, Concepto creativo, IA, Teaser, Trend, Aftermovie, "
                          "DJ set, Contenido PRO, Visuales. Responsables: América, Majo Martínez, Diego, Fradell, Dupe, María José. Crear o editar texto "
                          "es libre; editar `fecha_pub`, `flyer` o `unidad` de uno que ya existe pide OK (puede reprogramar Zernio, avisar a Fradell o "
                          "tocar al Contestador). Si la app contesta `confirmar` (ya está en Zernio), enséñaselo a la persona y repite con `confirmar`: true.",
                          CONT, [], plan("contenido"), contenido_delicado),
    "contenido_clonar": ("Copia idéntica de un contenido (nace «planeada», sin pieza).", {"id": S}, ["id"], plan("clonar"), False),
    "cambiar_tipo": ("Cambiar de tipo (`de` contenido|caracteristica, `a` caracteristica|contenido|mini) con su `id` (o `mini` + `indice` para una característica) "
                     "y lo que pida el nuevo (`titulo`, `categorias`, `clave`, `departamento`). Borra lo de antes y no se deshace con restaurar." + CANDADO,
                     {"de": S, "a": S, "id": S, "mini": S, "indice": N, "titulo": S, "categorias": A, "clave": S, "departamento": S}, ["de"], plan("convertir"), True),
    "ordenar": ("Acomodar el orden de mini campañas o contenidos: `tipo` mini|contenido, `ids` en el orden nuevo.", {"tipo": S, "ids": A}, ["tipo", "ids"],
                plan("orden"), False),
    "restaurar": ("Deshacer un borrado con lo que regresó `borrar` (`tabla`, `id`, `t`).", {"tabla": S, "id": S, "t": S}, ["tabla", "id", "t"],
                  plan("restaurar"), False),
    "documentos_agregar": ("Agregar documentos (links) a una campaña: `documentos` [{nombre, url}], `tipo` Minuta|Brainstorm|Diseño|Moodboard|Otro.",
                           {"campana": S, "tipo": S, "documentos": A}, ["campana", "documentos"], plan("documentos"), False),
    "minuta_crear": ("Crea en Drive el Doc de la minuta de una campaña (plantilla con los eventos del mes) y lo liga.", {"campana": S}, ["campana"],
                     plan("minuta/crear"), False),
    "minuta_subir": ("Sube una minuta a una campaña (la guarda en su carpeta de Drive) y la procesa con el modelo de la app (~3.5 min, cuenta 10 de "
                     "los 200 usos del día; queda «procesando» → «por_aprobar» y a ti te llega aviso por azul.os). `links`: links de Drive/Docs; "
                     "`archivos`: rutas de tu Mac (md, txt, pdf, docx…, máx 10 MB; con archivos pide OK porque los sube al Drive del equipo). "
                     "Nada pasa al calendario hasta aprobarla.", {"campana": S, "links": A, "archivos": A}, ["campana"], minuta_subir,
                     lambda a: bool(a.get("archivos"))),
    "minuta_procesar": ("Vuelve a procesar documentos ya ligados a una campaña (`documentos` = sus ids). Igual que minuta_subir: modelo y aviso a ti.",
                        {"campana": S, "documentos": A}, ["campana", "documentos"], plan("minuta/procesar"), False),
    "minuta_ver": ("Una minuta procesada: estado, documentos (su texto recortado a 3,000 caracteres; `detalle`: true lo trae entero) y lo que "
                   "sacó (mini_campanas, contenidos, cada uno con `ref`).", {"id": S, "detalle": B}, ["id"], minuta_ver, False),
    "minuta_aprobar": ("Pasa al calendario lo aprobado de una minuta: `minuta` (id), `mini_campanas` y `contenidos` con la MISMA forma y `ref` que "
                       "regresó minuta_ver (se pueden editar sus campos), `descartados` [{tipo, ref, titulo}], `terminar`: true para cerrarla. "
                       "Repetir un `ref` no duplica." + CANDADO,
                       {"minuta": S, "mini_campanas": A, "contenidos": A, "descartados": A, "terminar": B}, ["minuta"], plan("minuta/aprobar"), True),
    "minuta_borrar": ("Borra una minuta procesada (no sus documentos)." + CANDADO, {"id": S}, ["id"], plan("minuta/borrar"), True),
    "documento_desligar": ("Quita un documento de su campaña (el Doc se queda en Drive)." + CANDADO, {"id": S}, ["id"], plan("documento/desligar"), True),
    "borrar": ("Borra (suave, se puede deshacer con `restaurar`) un modulo|campana|mini|contenido|documento. Si tiene piezas, la app contesta "
               "`confirmarPiezas` (se eliminan y desprograman de Zernio): enséñaselas a la persona y repite con `confirmar`: true." + CANDADO,
               {"tabla": S, "id": S, "confirmar": B}, ["tabla", "id"], plan("borrar"), True),
    "contenidos_mover": ("Cambiar de día varios contenidos: `cambios` [{id, fecha}]. Puede reprogramar Zernio y avisar a Fradell. Si la app "
                         "contesta `confirmar`, repite con `confirmar` = lista de ids aceptados." + CANDADO,
                         {"cambios": A, "confirmar": A}, ["cambios"], plan("mover"), True),
    "calendario": ("Calendario del mes: `modulo`, `accion` borrador|borrador_quitar (libres) o proponer|propuesta_quitar|editar_propuesta|aprobar|quitar "
                   "(avisan a Fradell o al equipo; piden OK), `pos`.", {"modulo": S, "accion": S, "pos": O, "confirmar": B}, ["modulo", "accion"],
                   plan("calendario"), lambda a: a.get("accion") not in ("borrador", "borrador_quitar")),
    "formulario_mandar": ("Manda el formulario de fechas de entrega de una campaña a América (`departamento` diseno) o a Majo Martínez (video). Le llega aviso."
                          + CANDADO, {"campana": S, "departamento": S}, ["campana", "departamento"], plan("formulario/mandar"), True),
    "formulario_guardar": ("Llena un formulario de fechas: `id`, `filas` [{id del contenido, fecha_entrega, asignar (solo video: lista con majo, diego y/o dupe; reemplaza a esos tres)}], "
                           "`completar`: true para entregarlo. Avisa." + CANDADO, {"id": S, "filas": A, "completar": B}, ["id", "filas"],
                           plan("formulario/guardar"), True),
    "link_red": ("Pega (o quita con `quitar`) el link de la red de un contenido: lo marca publicado y lo palomea en su pieza. `red` instagram|tiktok|facebook."
                 + CANDADO, {"id": S, "red": S, "url": S, "quitar": B}, ["id", "red"], plan("link-red"), True),
    "flyer_elegir": ("Escoge el flyer del evento (`mini`, `contenido`; null = ninguno): su link le llega al Contestador, que lo manda a clientes." + CANDADO,
                     {"mini": S, "contenido": S, "fecha": S, "toggle": B}, ["mini"], plan("flyer"), True),
    "mandar_a_corregir": ("Regresa a corrección algo ya aprobado (`id` del contenido, o `pieza` si es «No es contenido»): lo desprograma y avisa."
                          + CANDADO, {"id": S, "pieza": S, "comentario": S}, [], plan("corregir"), True),
    "vigilante_ver": ("Lo que el vigilante de redes encontró publicado y falta ligar a Planeación (cada uno con su `key`).", {}, [],
                      vigilante_ver, False),
    "vigilante_resolver": ("Resuelve una publicación del vigilante (Fradell y Dupe): `key`, `accion` ignorar | ligar (`contenido` = id; el link lo marca "
                           "publicado) | nuevo (crea el contenido extra: `unidad`, `titulo`, `categoria`)." + CANDADO,
                           {"key": S, "accion": S, "contenido": S, "unidad": S, "titulo": S, "categoria": S}, ["key", "accion"], plan("vigilante"), True),
    # ---- Aprobación ----
    "piezas_ver": ("Piezas de Aprobación que puedes ver (como en la app). Filtros: `estado` (lista separada por comas: con_autor, analizando, con_fradell, "
                   "con_majo, con_luis, aprobada, programada, publicada…), `buscar` (en el título), `max` (60).",
                   {"estado": S, "buscar": S, "max": N}, [], piezas_ver, False),
    "pieza_ver": ("Una pieza con sus versiones, historial y correcciones.", {"id": S}, ["id"], lambda a: api.pedir("GET", "/ap/api/pieza/" + id_ok(a["id"])), False),
    "ficha_ver": ("La ficha de publicación de una pieza (caption, fecha, redes, collabs). Abrirla la aparta 4 minutos, igual que en la app.",
                  {"id": S}, ["id"], ap("ficha"), False),
    "ficha_editar": ("Edita la ficha (antes de programar): `cambios` con collabs, etiquetados, comenta, tiktokTitulo, tiktokMixto, cancion, redes, "
                     "tipoContenido, etapaEmbudo (lo que no esté en el catálogo de ficha_ver se ignora). `fecha` (" + FECHA + "; mueve también el "
                     "contenido en Planeación), `ahora` o `caption` piden OK.", {"id": S, "cambios": O}, ["id", "cambios"], ficha_editar,
                     lambda a: any(k in (a.get("cambios") or {}) for k in ("fecha", "ahora", "caption"))),
    "caption_guardar": ("Cambia el caption de una pieza (si ya está programada, también en Zernio) y le avisa a Fradell." + CANDADO,
                        {"id": S, "caption": S}, ["id", "caption"], accion("caption"), True),
    "pieza_accion": ("Mueve una pieza en Aprobación, como los botones de la app: `accion` aprobar, regresar (a corrección), mandar, a_luis, a_fradell, "
                     "apruebalo_tu, sin_fradell, directo, descartar, retirar o programar (la manda a Zernio). `comentario` opcional. Avisa a quien sigue."
                     + CANDADO, {"id": S, "accion": S, "comentario": S}, ["id", "accion"], accion(None), True),
    "pieza_titulo": ("Cambia el título de una pieza «No es contenido» (las de contenido toman el título de Planeación).", {"id": S, "titulo": S}, ["id", "titulo"], ap("titulo"), False),
    "pieza_contenido": ("Elige el contenido de Planeación de una pieza que lo tiene pendiente: `plan` (id), `planNuevo` {unidad, titulo, categorias} o `planOmitir`.",
                        {"id": S, "plan": S, "planNuevo": O, "planOmitir": B}, ["id"], ap("pieza-plan"), False),
    "correccion_marcar": ("Marca hecha una corrección de una pieza (`cid` = su id; `hecho`: false la regresa a pendiente). También la resuelve "
                          "o reabre en Frame.io. `borrar`: true la borra (también en Frame.io) y pide OK.", {"cid": N, "hecho": B, "borrar": B}, ["cid"],
                          lambda a: api.pedir("POST", "/ap/api/correccion/marcar", {"hecho": True, **a}),
                          lambda a: bool(a.get("borrar"))),
    "correccion_agregar": ("Agrega una corrección a una pieza en revisión (también queda como comentario en Frame.io): `texto`, y si es de video `ms` "
                           "(segundo ×1000) o `slide`." + CANDADO, {"id": S, "texto": S, "ms": N, "slide": N}, ["id", "texto"], ap("correccion"), True),
    "pieza_subir": ("Sube archivos de tu Mac (Escritorio, Descargas, Documentos, Google Drive) como pieza nueva (varios = carrusel; sin analizador, "
                    "se manda directo a revisión), o como versión nueva de una pieza que te regresaron (`pieza` = su id; ahí el analizador corre, "
                    "salvo «No es contenido»). "
                    "Contenido: `plan` (id), `planNuevo` {unidad, titulo, categorias}, `planOmitir` (Dupe/Fradell) o `planDelegar`. Lo físico: "
                    "`noContenido` true con `campana` (y `mini`). `directo` (María José, Fradell, Dupe). Le avisa a quien revisa." + CANDADO,
                    SUBIR, ["archivos"], pieza_subir, True),
    "pieza_eliminar": ("Elimina una pieza (y la desprograma de Zernio)." + CANDADO, {"id": S}, ["id"], ap("eliminar"), True),
    "stock_subir": ("Sube archivos de tu Mac a «Stock y recursos» del negocio en Drive, que ve todo el equipo. `negocio`: " + ", ".join(NEGOCIOS) + "." + CANDADO,
                    {"archivos": A, "negocio": S}, ["archivos", "negocio"], stock_subir, True),
    # ---- Distribución ----
    "mejor_hora": ("Mejores horas para publicar un día (AAAA-MM-DD), con lo que dice el Tablero.", {"fecha": S}, ["fecha"],
                   lambda a: api.pedir("GET", "/ap/api/mejor-hora?fecha=" + quote(a["fecha"])), False),
    "reprogramar": ("Mueve piezas programadas a otra fecha y hora: `cambios` [{id, fecha}] (hora de CDMX, exactamente AAAA-MM-DDTHH:MM (p. ej. 2026-11-14T19:00)). Se mueve en Zernio." + CANDADO,
                    {"cambios": A}, ["cambios"], reprogramar, True),
    "publicado_a_mano": ("Anota que una pieza programada ya se subió a mano en `red` instagram|tiktok." + CANDADO, {"id": S, "red": S},
                         ["id", "red"], ap("manual"), True),
    # ---- Tablero, avisos y equipo ----
    "tablero_ver": ("Tablero: `que` = reporte (de pauta; sin `dia` regenera y guarda el de ayer; usa el modelo), alertas, audiencia, cuentas o pauta "
                    "(`desde`/`hasta` AAAA-MM-DD), gente (cómo se la pasó la gente; 10 usos), preguntar (`q`, pregunta libre), eventos (todos).",
                    {"que": {"type": "string", "enum": list(TABLERO)}, "dia": S, "desde": S, "hasta": S, "q": S}, ["que"], tablero_ver, False),
    "tablero_anotar": ("Anotaciones del Tablero: `que` kpi {k, n} | asig {camp, ev} (campaña de pauta → evento) | asigp {pid, ev} (post → campaña) | "
                       "modelo {k, modelo}; `datos` con esos campos.", {"que": {"type": "string", "enum": ANOTAR}, "datos": O},
                       ["que", "datos"], tablero_anotar, False),
    "reporte_mandar": ("Manda ya el reporte de pauta por Telegram." + CANDADO, {}, [], lambda a: api.pedir("POST", "/bot/enviar-reporte", {}), True),
    "avisos_ver": ("Últimos avisos de azul.os (Telegram), movimientos y accesos (solo Dupe). `max` por lista (30).", {"max": N}, [], avisos_ver, False),
    "equipo_ver": ("Equipo con sus accesos y el panel de permisos (solo Dupe).", {}, [],
                   lambda a: {"equipo": api.pedir("GET", "/ap/api/equipo"), "permisos": api.pedir("GET", "/ap/api/permisos")}, False),
    "permisos_cambiar": ("Cambia permisos (solo Dupe): los datos van tal cual a la ruta de ⚙️ Permisos (`accion` alta|restablecer|cambiar…)." + CANDADO,
                         {"datos": O}, ["datos"], lambda a: api.pedir("POST", "/ap/api/permisos", a["datos"]), True),
    "clave_nueva": ("Contraseña nueva para alguien del equipo (solo Dupe). Sin `clave`, la app inventa una segura y la regresa." + CANDADO,
                    {"usuario": S, "clave": S}, ["usuario"], ap("equipo"), True),
    "mejoras_ver": ("Mejoras que propuso el equipo (solo Dupe).", {}, [], lambda a: api.pedir("GET", "/ap/api/mejoras"), False),
    "app_leer": ("Lee cualquier otra ruta GET de la app sin herramienta propia (p. ej. /ap/api/planeta, /ap/api/arrobas, "
                 "/ap/api/planeacion/formulario/<id>, /ap/api/planeacion/subida?tipo=imagen, /api/semana6).", {"ruta": S}, ["ruta"], app_leer, False),
    "app_llamar": ("Cualquier otra ruta de la app sin herramienta propia: `metodo` GET|POST, `ruta` (/ap/…, /api/… o /bot/…), `datos`." + CANDADO,
                   {"metodo": S, "ruta": S, "datos": O}, ["metodo", "ruta"], app_llamar, True),
    "actualizar": ("Instala la versión nueva del conector que ya está en GitHub, SOLO si la persona dijo que sí: avanza el repo, corre las pruebas y "
                   "si fallan regresa a la de antes. Después hay que abrir una sesión nueva de Claude." + CANDADO, {}, [],
                   lambda a: actualizar.instalar(), True),
    "confirmar": ("Hace la acción que una herramienta dejó pendiente, SOLO después de que la persona dijo «sí» en el chat a lo que se le enseñó. "
                  "`codigo` = el que regresó esa herramienta (vale 10 min y una vez).", {"codigo": S}, ["codigo"], None, False),
}
PIEZA = {"caption_guardar", "pieza_accion", "pieza_eliminar", "correccion_agregar", "publicado_a_mano"}


_aviso_dado = False


def aviso_de_version(nombre):
    """Como el de WhatsApp: en la primera herramienta de la sesión, si hay versión nueva, se dice una vez."""
    global _aviso_dado
    if _aviso_dado or nombre in ("actualizar", "confirmar", "quien_soy"):
        return None
    _aviso_dado = True
    try:
        nuevo = actualizar.pendiente()
    except Exception:   # el aviso nunca tumba una herramienta
        return None
    return nuevo and ("HAY VERSIÓN NUEVA del conector de la app de marketing:\n" + nuevo + "\nAntes de seguir, díselo a la persona y "
                      "pregúntale: ¿la instalo primero (herramienta `actualizar`, pide su OK; luego sesión nueva) o sigo sin ella? Nunca la instales sin su sí.")


def pendiente(nombre, args):
    """Primera llamada de algo delicado: no toca la app (solo lee el nombre de la pieza) y deja la acción guardada con un código."""
    desc = HERRAMIENTAS[nombre][0].split(" PIDE EL OK")[0]
    c = f"{secrets.randbelow(10**6):06d}"
    _pendientes[c] = (nombre, json.loads(json.dumps(args)), time.time() + VIGENCIA)
    r = {"ok": False, "falta_ok_de_luis": True, "herramienta": nombre, "que_hace": desc, "datos": args, "codigo": c,
         "siguiente": f"Enséñale esto a la persona y espera su «sí» explícito. Luego llama confirmar con codigo={c}."}
    if nombre in PIEZA:
        try:
            p = api.pedir("GET", "/ap/api/pieza/" + id_ok(args.get("id")))["pieza"]
            r["pieza"] = {k: p.get(k) for k in ("titulo", "estado", "tipo", "autor")}
        except Exception as e:   # leer el nombre es de cortesía: si falla, el aviso sale igual con el id
            r["pieza"] = {"error": str(e)}
    return r


def llamar(nombre, args):
    if nombre == "confirmar":
        ahora = time.time()
        for c, (_, _, vence) in list(_pendientes.items()):
            if vence < ahora:
                del _pendientes[c]
        p = _pendientes.pop(str(args.get("codigo", "")), None)
        if not p:
            raise api.Error("Ese código no vale (venció, ya se usó o es de otra sesión). Vuelve a llamar la herramienta y enséñaselo a la persona.")
        return revisado({"herramienta": p[0], "resultado": HERRAMIENTAS[p[0]][3](p[1])})
    desc, props, req, fn, delicado = HERRAMIENTAS[nombre]
    faltan = [k for k in req if args.get(k) in (None, "", [])]
    if faltan:
        raise api.Error("Falta: " + ", ".join(faltan))
    if delicado(args) if callable(delicado) else delicado:
        return pendiente(nombre, args)
    return revisado(fn(args))


def revisado(r):
    """La app contesta 200 aunque no haya hecho todo: pide confirmar (Zernio, piezas que se van) o trae errores. Se dice claro."""
    x = r["resultado"] if isinstance(r, dict) and "herramienta" in r else r   # solo desenvuelve lo que regresa `confirmar`
    if isinstance(x, dict):
        if x.get("confirmar") or x.get("confirmarPiezas"):
            return {**r, "hecho": False, "nota": "NO se hizo: la app pide confirmar esto. Enséñaselo a la persona y, si dice que sí, repite con `confirmar` (pedirá otro código)."}
        if x.get("errores"):
            return {**r, "hecho": "a medias", "nota": "Algunas cosas no entraron: revisa `errores`."}
    return r


def responder(msg: dict):
    metodo, mid = msg.get("method"), msg.get("id")
    if metodo == "initialize":
        res = {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
               "serverInfo": {"name": "trago-marketing", "version": "1.0"}}
    elif metodo == "tools/list":
        res = {"tools": [{"name": n, "description": d, "inputSchema": {"type": "object", "properties": p, "required": r}}
                         for n, (d, p, r, _, _) in HERRAMIENTAS.items()]}
    elif metodo == "tools/call":
        try:
            params = msg.get("params") or {}
            nombre, args = params.get("name"), dict(params.get("arguments") or {})
            if nombre not in HERRAMIENTAS:
                raise api.Error(f"No existe la herramienta {nombre}")
            out, error = llamar(nombre, args), False
        except api.Error as e:
            out, error = {"ok": False, "error": str(e)}, True
        except Exception as e:
            out, error = {"ok": False, "error": f"{type(e).__name__}: {e}"}, True
            traceback.print_exc(file=sys.stderr)
        res = {"content": [{"type": "text", "text": out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)}], "isError": error}
        aviso = aviso_de_version(nombre if isinstance(nombre, str) else "")
        if aviso:
            res["content"].append({"type": "text", "text": aviso})
    elif metodo == "ping":
        res = {}
    elif mid is None:
        return None   # notificación (p. ej. notifications/initialized): no se contesta
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"no conozco {metodo}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": res}


def main():
    actualizar.en_segundo_plano()
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8")
    for linea in sys.stdin:
        if not linea.strip():
            continue
        try:
            msg = json.loads(linea)
            r = responder(msg) if isinstance(msg, dict) else None
        except Exception as e:
            r = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"no entendí el mensaje: {e}"}}
        if r is not None:
            sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
            sys.stdout.flush()

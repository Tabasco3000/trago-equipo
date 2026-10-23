"""MCP sin herramientas: esta Mac ya tiene su propio conector de la app instalado aparte, y el del paquete no repite las suyas."""
import json
import sys

for linea in sys.stdin:
    try:
        m = json.loads(linea)
    except ValueError:
        continue
    if not isinstance(m, dict) or "id" not in m:
        continue
    if m.get("method") == "initialize":
        r = {"result": {"protocolVersion": (m.get("params") or {}).get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
                        "serverInfo": {"name": "trago-marketing-app", "version": "1"},
                        "instructions": "Esta Mac ya tiene su propio conector de la app de marketing («trago-marketing»): usa ese."}}
    elif m.get("method") == "tools/list":
        r = {"result": {"tools": []}}
    elif m.get("method") == "ping":
        r = {"result": {}}
    else:
        r = {"error": {"code": -32601, "message": "Este conector no tiene herramientas: usa «trago-marketing»."}}
    print(json.dumps({"jsonrpc": "2.0", "id": m["id"], **r}, ensure_ascii=False), flush=True)

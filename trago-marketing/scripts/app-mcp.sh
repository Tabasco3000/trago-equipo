#!/bin/sh
# Arranca el MCP de la app de marketing con el usuario que esta Mac tiene en su llavero (lo guarda scripts/guardar-clave.sh).
AQUI="$(dirname "$0")"
PY=$(sh "$AQUI/python.sh") || { echo "Falta Python en esta Mac: corre «xcode-select --install» (una vez) y abre una sesión nueva." >&2; exit 1; }
# Si esta Mac ya tiene su propio conector de la app (instalado aparte), el del paquete no repite sus herramientas.
if "$PY" -E -s -c 'import json,os,sys; c=json.load(open(os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~"), ".claude.json"))); sys.exit(0 if any("trago_marketing_mcp.py" in json.dumps(s) for s in c.get("mcpServers", {}).values()) else 1)' 2> /dev/null; then
  exec "$PY" -E -s "$AQUI/sin-herramientas.py"
fi
USUARIO=$(security find-generic-password -s trago-marketing-app 2> /dev/null | sed -n 's/^ *"acct"<blob>="\(.*\)"$/\1/p' | head -1)
# Sin usuario guardado el MCP arranca igual y cada herramienta dice que falta la contraseña (nunca cae en el de otra persona).
export TM_USUARIO="${USUARIO:-sin-usuario}"
# TM_BASE y TM_CLAVE son de las pruebas de la app: aquí la contraseña solo va a la app de verdad.
exec env -u TM_BASE -u TM_CLAVE "$PY" -E -s "$AQUI/../app/trago_marketing_mcp.py"

#!/bin/sh
# Arranca el MCP de la app de marketing con el usuario que esta Mac tiene en su llavero (lo guarda scripts/guardar-clave.sh).
AQUI="$(dirname "$0")"
PY=$(sh "$AQUI/python.sh") || { echo "Falta Python en esta Mac: corre «xcode-select --install» (una vez) y abre una sesión nueva." >&2; exit 1; }
USUARIO=$(security find-generic-password -s trago-marketing-app 2> /dev/null | sed -n 's/^ *"acct"<blob>="\(.*\)"$/\1/p' | head -1)
# Sin usuario guardado el MCP arranca igual y cada herramienta dice que falta la contraseña (nunca cae en el de otra persona).
export TM_USUARIO="${USUARIO:-sin-usuario}"
exec "$PY" "$AQUI/../app/trago_marketing_mcp.py"

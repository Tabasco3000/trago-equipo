#!/bin/sh
# Trae al paquete la copia del MCP de la app de marketing (repo de la obra de la app). Uso: ./traer-app.sh [carpeta del repo]
# Copia solo el código; apaga su actualizador (en el paquete lo actualiza el paquete, y su `git` podría caer en otro repo de
# arriba) y cambia «Luis» por «la persona» (el «sí» lo da quien lo usa). Después: pruebas, commit y ./publicar.sh.
set -eu
cd "$(dirname "$0")"
ORIGEN="${1:-$HOME/trago-marketing-mcp}"
DEST="$(pwd)/trago-marketing/app"
[ -f "$ORIGEN/tm/mcp.py" ] || { echo "no encuentro el MCP de la app en $ORIGEN" >&2; exit 1; }
[ -z "$(git -C "$ORIGEN" status --porcelain)" ] || { echo "el MCP de la app tiene cambios sin commit: primero que su obra los guarde" >&2; exit 1; }
rm -rf "$DEST"
mkdir -p "$DEST/tm"
cp "$ORIGEN/trago_marketing_mcp.py" "$DEST/"
for f in __init__ api mcp; do cp "$ORIGEN/tm/$f.py" "$DEST/tm/"; done
sed -i '' -e 's/Luis dijo/la persona dijo/g' -e 's/ a Luis/ a la persona/g' -e 's/de Luis/de la persona/g' -e 's/DE LUIS/DE LA PERSONA/g' -e 's/falta_ok_de_luis/falta_ok/g' "$DEST/tm/mcp.py"
# Sin usuario nunca cae en el de Luis, y la contraseña se guarda con la ventanita del paquete, no pegándola en una Terminal.
sed -i '' -e 's/"TM_USUARIO", "luis"/"TM_USUARIO", "sin-usuario"/' \
  -e 's|^GUARDAR = .*|GUARDAR = "sh '"'"'" + os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts/guardar-clave.sh")) + "'"'"'"|' \
  -e 's/Pégala en la Terminal con:/Guárdala con una ventanita de la Mac (nunca por el chat) corriendo:/' "$DEST/tm/api.py"
grep -q 'guardar-clave.sh' "$DEST/tm/api.py" && ! grep -q 'Terminal\|"luis"' "$DEST/tm/api.py" || { echo "cambió tm/api.py de la app: revisa los parches de traer-app.sh" >&2; exit 1; }
cat > "$DEST/tm/actualizar.py" <<'EOF'
"""En el paquete del equipo, este MCP lo actualiza el paquete (scripts/al-empezar.sh): aquí no se toca git."""
from pathlib import Path

ORIGEN = Path(__file__).resolve().parents[1] / "ORIGEN"


def en_segundo_plano(repo=None):
    pass


def version(repo=None):
    return "paquete trago-marketing · " + (ORIGEN.read_text().strip()[:60] if ORIGEN.exists() else "?")


def pendiente(repo=None):
    return None


def instalar(repo=None, pruebas=None):
    return {"estado": "al_dia", "version": version(), "nota": "Este conector lo actualiza solo el paquete trago-marketing."}
EOF
# Sus pruebas corren contra la copia parchada (test/app.test.mjs); no van en el paquete.
mkdir -p test/app-py && sed 's/falta_ok_de_luis/falta_ok/g' "$ORIGEN/tests/test_mcp.py" > test/app-py/test_mcp.py
git -C "$ORIGEN" log -1 --format='%h %cs %s' > "$DEST/ORIGEN"
echo "Copiado de $(cat "$DEST/ORIGEN")"

#!/bin/sh
# Publica una versión del paquete. Uso: ./publicar.sh 0.1.1
# Corre las pruebas y arma todo en una copia temporal hecha solo con lo que está en git (nada suelto ni ignorado llega
# al repo público): versión, zip, huella y catálogo van en un solo commit y push. La carpeta de trabajo no se toca hasta
# que el push salió; si algo falla, se borra la copia y ya. Cada Mac la baja sola (al abrir sesión, como mucho cada 6 horas).
set -eu
cd "$(dirname "$0")"
REPO=$(pwd)
V="${1:-}"
printf '%s' "$V" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || { echo "uso: ./publicar.sh <versión X.Y.Z, p. ej. 0.1.1>" >&2; exit 1; }
[ "$(git branch --show-current)" = main ] || { echo "publica desde la rama main" >&2; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "hay cambios sin commit: guárdalos primero" >&2; exit 1; }
ORIGEN=$(git remote get-url origin)
git ls-remote origin > /dev/null || { echo "no llego al repo de GitHub (origin)" >&2; exit 1; }
ZIP="dist/trago-marketing-$V.zip"
[ ! -e "$ZIP" ] || { echo "la versión $V ya se publicó" >&2; exit 1; }
CLAUDE_BIN="${CLAUDE_CODE_EXECPATH:-claude}"

node --test test/al-empezar.test.mjs test/limpieza.test.mjs # (publicar.test llama a este script)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git clone -q "$REPO" "$TMP/r"
cd "$TMP/r"
git remote set-url origin "$ORIGEN"
mkdir -p dist .claude-plugin # git no guarda carpetas vacías
sed -i '' -E "s/\"version\": \"[^\"]*\"/\"version\": \"$V\"/" trago-marketing/.claude-plugin/plugin.json
(cd trago-marketing && git ls-files | LC_ALL=C sort | zip -X -q "../$ZIP" -@)
SHA=$(shasum -a 256 "$ZIP" | cut -c1-64)
cat > .claude-plugin/marketplace.json <<EOF
{
  "name": "trago-equipo",
  "description": "Los paquetes del equipo de TRAGO.",
  "owner": { "name": "TRAGO." },
  "plugins": [
    {
      "name": "trago-marketing",
      "description": "El Cerebro TRAGO. para el equipo de marketing: la entrevista de entrada, y después los agentes del equipo.",
      "source": {
        "source": "archive",
        "url": "https://raw.githubusercontent.com/Tabasco3000/trago-equipo/main/$ZIP",
        "sha256": "$SHA"
      }
    }
  ]
}
EOF
node --test test/limpieza.test.mjs
"$CLAUDE_BIN" plugin validate .
"$CLAUDE_BIN" plugin validate trago-marketing
git add "$ZIP" .claude-plugin/marketplace.json trago-marketing/.claude-plugin/plugin.json
git commit -q -m "Versión $V"
git push -q origin HEAD:main
cd "$REPO"
git pull -q --ff-only origin main
echo "Publicada la $V ($SHA)."

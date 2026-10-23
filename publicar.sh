#!/bin/sh
# Publica una versión del paquete. Uso: ./publicar.sh 0.1.1
# Corre las pruebas, pone la versión, arma el zip, saca su huella y escribe el catálogo. Todo va en un solo commit y push,
# así el catálogo nunca apunta a un zip que no existe. Cada Mac la baja sola (al abrir sesión, como mucho cada 6 horas).
set -eu
cd "$(dirname "$0")"
V="${1:-}"
case "$V" in '' | *[!0-9.]* | .* | *.) echo "uso: ./publicar.sh <versión, p. ej. 0.1.1>" >&2; exit 1 ;; esac
[ "$(git branch --show-current)" = main ] || { echo "publica desde la rama main" >&2; exit 1; }
git ls-remote origin > /dev/null || { echo "no llego al repo de GitHub (origin)" >&2; exit 1; }
mkdir -p dist .claude-plugin # git no guarda carpetas vacías
ZIP="dist/trago-marketing-$V.zip"
[ ! -e "$ZIP" ] || { echo "la versión $V ya se publicó" >&2; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "hay cambios sin commit: guárdalos primero" >&2; exit 1; }
CLAUDE_BIN="${CLAUDE_CODE_EXECPATH:-claude}"

node --test test/al-empezar.test.mjs test/limpieza.test.mjs # (publicar.test llama a este script)
ANTES=$(git rev-parse HEAD)
# Si algo falla de aquí en adelante (también el push), todo vuelve a como estaba: el árbol estaba limpio al empezar.
trap 'git reset -q --hard "$ANTES"; git clean -fdq -- dist .claude-plugin' EXIT

sed -i '' -E "s/\"version\": \"[^\"]*\"/\"version\": \"$V\"/" trago-marketing/.claude-plugin/plugin.json
(cd trago-marketing && find . -type f ! -name .DS_Store | LC_ALL=C sort | zip -X -q "../$ZIP" -@)
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
git add -A
git commit -q -m "Versión $V"
git push -q origin HEAD:main
trap - EXIT
echo "Publicada la $V ($SHA)."

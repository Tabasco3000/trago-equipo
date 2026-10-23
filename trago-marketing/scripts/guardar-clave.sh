#!/bin/sh
# Guarda en el llavero de esta Mac el usuario y la contraseña de la app de marketing, con ventanitas de la Mac.
# La contraseña nunca pasa por el chat ni por lo que este script escribe: Claude solo ve «guardada» o el error.
pedir() {
  osascript -e "text returned of (display dialog \"$1\" default answer \"\" $2 with title \"TRAGO.\" buttons {\"Cancelar\", \"Guardar\"} default button \"Guardar\" cancel button \"Cancelar\")" 2> /dev/null
}
U=$(pedir "Tu usuario de la app de marketing (con el que entras a marketing.tragotragotrago.com):" "") || { echo "Cancelado: no se guardó nada."; exit 1; }
U=$(printf '%s' "$U" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
case "$U" in '' | *[!a-z0-9._-]*) echo "Ese usuario no es válido: no se guardó nada."; exit 1 ;; esac
P=$(pedir "La contraseña de la app de marketing (no la de tu Mac):" "with hidden answer") || { echo "Cancelado: no se guardó nada."; exit 1; }
[ -n "$P" ] || { echo "La contraseña vino vacía: no se guardó nada."; exit 1; }
# Una sola entrada: si antes se guardó otro usuario (mal escrito), el arranque podría seguir tomando ese.
for _ in 1 2 3 4 5; do security delete-generic-password -s trago-marketing-app > /dev/null 2>&1 || break; done
# shortcut: la contraseña va como argumento de «security» unas milésimas; cualquier programa de esta cuenta igual podría leerla del llavero.
if security add-generic-password -U -a "$U" -s trago-marketing-app -w "$P" > /dev/null 2>&1; then
  echo "Guardada para «$U». Abre una sesión nueva para usar la app."
else
  echo "No se pudo guardar en el llavero."
  exit 1
fi

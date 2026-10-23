#!/bin/sh
# Escribe el Python con el que corre la app de marketing, o sale con 1 si esta Mac no tiene. Nunca toca el «python3» de Apple
# si faltan sus herramientas: ese abre la ventana de instalar en cada sesión. (TRAGO_PY_*: solo para las pruebas.)
for p in ${TRAGO_PY_OTROS:-/opt/homebrew/bin/python3 /usr/local/bin/python3}; do [ -x "$p" ] && { echo "$p"; exit 0; }; done
APPLE="${TRAGO_PY_APPLE:-/usr/bin/python3}"
xcode-select -p > /dev/null 2>&1 && [ -x "$APPLE" ] && { echo "$APPLE"; exit 0; }
exit 1

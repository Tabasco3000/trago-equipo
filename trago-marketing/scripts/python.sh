#!/bin/sh
# Escribe el Python con el que corre la app de marketing, o sale con 1 si esta Mac no tiene uno que sirva. Nunca toca el «python3»
# de Apple si faltan sus herramientas: ese abre la ventana de instalar en cada sesión. (TRAGO_PY_*: solo para las pruebas.)
# Sirve si trae certificados: el de python.org sin «Install Certificates» no puede hablar con la app por https.
sirve() { [ -x "$1" ] && "$1" -E -s -c 'import ssl,sys; sys.exit(0 if ssl.create_default_context().cert_store_stats()["x509_ca"] else 1)' 2> /dev/null; }
for p in ${TRAGO_PY_OTROS:-/opt/homebrew/bin/python3 /usr/local/bin/python3}; do sirve "$p" && { echo "$p"; exit 0; }; done
APPLE="${TRAGO_PY_APPLE:-/usr/bin/python3}"
xcode-select -p > /dev/null 2>&1 && sirve "$APPLE" && { echo "$APPLE"; exit 0; }
exit 1

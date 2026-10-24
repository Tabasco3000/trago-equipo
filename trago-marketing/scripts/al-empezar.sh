#!/bin/sh
# Al abrir una sesión: el aviso corto para Claude y, como mucho cada 6 horas, la búsqueda de versión nueva en segundo plano.
# (La actualización automática de Claude Code viene apagada para paquetes que no son de Anthropic.) Nunca hace fallar la sesión.
DATOS="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/trago-marketing-trago-equipo}"
mkdir -p "$DATOS" 2>/dev/null
AHORA=$(date +%s)
# Una fecha guardada que no es número o está en el futuro (reloj mal puesto alguna vez) vale lo que diga el segundo argumento.
numero() { case "$1" in '' | *[!0-9]* | 0?*) echo "$2" ;; *) [ "$1" -le "$AHORA" ] && echo "$1" || echo "$2" ;; esac; }

if [ ! -f "$DATOS/visto" ]; then
  touch "$DATOS/visto" 2>/dev/null # «: >» es especial en sh: si no puede escribir, tumba el script
  echo "$AHORA" 2>/dev/null > "$DATOS/ok"
  echo "Es la primera sesión con el paquete del Cerebro TRAGO.: en tu primera respuesta, llama a la herramienta «contexto» del conector «Cerebro TRAGO.» y, si dice que falta la entrevista, preséntate en una línea y empiézala con el skill «trago-marketing:entrevista». Si no ves ese conector, ayuda a la persona a agregarlo (los pasos vienen en el skill «trago-marketing:entrevista»)."
else
  echo "Esta persona es del equipo de marketing de TRAGO. y tiene el Cerebro TRAGO. Cuando la plática sea de TRAGO., llama una vez a «contexto» del conector «Cerebro TRAGO.» antes de contestar: trae cómo trabaja el equipo y quién es esta persona. Si dice que falta la entrevista, ofrécela (skill «trago-marketing:entrevista»). Si no ves el conector «Cerebro TRAGO.», ayúdale a agregarlo con los pasos de ese skill."
fi

OK=$(numero "$(cat "$DATOS/ok" 2>/dev/null)" "$AHORA")
[ "$OK" = "$(cat "$DATOS/ok" 2>/dev/null)" ] || echo "$AHORA" 2>/dev/null > "$DATOS/ok" # roto o futuro: los 3 días cuentan desde hoy
REVISADO=$(numero "$(cat "$DATOS/revisado" 2>/dev/null)" 0)
# Solo si ya hubo intentos que fallaron durante 3 días: tras unas vacaciones sin abrir sesión, primero se revisa.
if [ $((REVISADO - OK)) -gt 259200 ]; then
  echo "El paquete del Cerebro TRAGO. no se ha podido actualizar en más de 3 días: díselo a la persona para que le avise a Luis."
fi

# La app de escritorio le pasa a cada sesión la ruta de su Claude Code; en Terminal está en el PATH.
CLAUDE_BIN="${CLAUDE_CODE_EXECPATH:-$(command -v claude 2>/dev/null)}"
find "$DATOS" -maxdepth 1 -name candado -mmin +10 -exec rmdir {} \; 2>/dev/null # una revisión que se murió a medias
if [ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] && [ $((AHORA - REVISADO)) -ge 21600 ] && mkdir "$DATOS/candado" 2>/dev/null; then
  echo "$AHORA" 2>/dev/null > "$DATOS/revisado"
  # shortcut: sin tope de tiempo (macOS no trae «timeout»); un «claude» colgado suelta el candado a los 10 min, y corre cada 6 h.
  # El catálogo es un archivo (no un repo), así que «plugin update» solo no lo vuelve a bajar: primero el catálogo.
  nohup sh -c '"$1" plugin marketplace update trago-equipo && "$1" plugin update trago-marketing@trago-equipo && date +%s > "$2/ok"; rmdir "$2/candado"' \
    sh "$CLAUDE_BIN" "$DATOS" > "$DATOS/actualizar.log" 2>&1 < /dev/null &
fi
exit 0

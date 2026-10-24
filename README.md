# TRAGO. · paquete del equipo

El paquete de Claude Code del equipo de marketing de TRAGO.: conecta a cada quien con el Cerebro TRAGO. y le hace la entrevista de entrada. Después trae los agentes del equipo, como versiones nuevas que llegan solas.

No lleva llaves, documentos ni datos. Lo del equipo lo entrega el Cerebro, y solo a quien Luis dio de alta. Instala solo desde el link que te mande Luis.

## Entrar (una vez)

1. **El conector.** En claude.ai (o en la app de Claude): Personalizar › Conectores › «+ Añadir» › «Añadir conector personalizado». Nombre `Cerebro TRAGO.`, URL `https://cerebro.tragotragotrago.com/mcp`, deja «Usar la identidad publicada de Claude», «Iniciar sesión ahora» y entra con **tu** Google. Sirve en la compu y en el celular. Igual con la app de marketing: nombre `TRAGO. Marketing`, URL `https://conector-marketing.tragotragotrago.com/mcp`.
2. **La línea.** Pégala en una sesión de la pestaña Code de la app de Claude (o en Terminal) y dale permiso cuando lo pida:

   ```
   "${CLAUDE_CODE_EXECPATH:-claude}" plugin install trago-marketing --marketplace https://raw.githubusercontent.com/Tabasco3000/trago-equipo/main/.claude-plugin/marketplace.json
   ```

3. **Abre una sesión nueva.** El Cerebro se presenta y te hace la entrevista (unos 5 minutos).

## Qué trae

- `trago-marketing/skills/entrevista`: las preguntas y cómo se hacen.
- `trago-marketing/scripts/al-empezar.sh`: al abrir cada sesión le recuerda a Claude que use el Cerebro y, como mucho cada 6 horas, busca versión nueva.

## Publicar una versión (Luis)

`./publicar.sh 0.3.0`: corre las pruebas, arma el zip con su huella y sube el catálogo en un solo commit.

Quien pueda subir a este repo corre código en las Macs del equipo: la cuenta de GitHub que publica lleva verificación en dos pasos.

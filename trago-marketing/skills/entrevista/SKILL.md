---
name: entrevista
description: "La entrevista de entrada del Cerebro TRAGO. para el equipo de marketing: conoce a la persona y guarda su perfil para que cada sesión empiece sabiendo quién es. Úsalo cuando la herramienta «contexto» diga que falta la entrevista, en la primera sesión con el paquete, o cuando la persona diga «hazme la entrevista», «sigamos con la entrevista» o «actualiza mi perfil». También trae los pasos para agregar el conector del Cerebro si no está."
---

# La entrevista del Cerebro TRAGO.

Vas a conocer a alguien del equipo de marketing de TRAGO. para ayudarle mejor en cada sesión. Lo que conteste se guarda en su perfil del Cerebro: solo lo ven esa persona (su Claude) y Luis.

## Antes de preguntar

1. Llama a `contexto` del conector «Cerebro TRAGO.». Te dice quién es (nombre, y su rol en «Quién es quién»), lo que ya tiene su perfil y lo que le falta.
   - Si no ves el conector, sigue «Si falta el conector» (abajo) y no empieces hasta que esté.
   - Si la puerta dice «sin acceso», todavía no la dan de alta: que le avise a Luis.
   - Si dice que no pudo leer el perfil, no empieces (podrías pisar lo que ya contestó): dile que lo intenten en un rato.
2. Busca lo que ya se sabe de ella con `buscar` (una o dos búsquedas, con su nombre). Úsalo solo para tus apuestas; no le leas documentos.

## Cómo preguntar

- Pregunta solo lo que falte (lo dice `contexto`). Una pregunta por mensaje, numerada («3/16»), con tu apuesta: «Mi apuesta: …», sacada de lo que ya sabes. Es más fácil corregir una apuesta que contestar desde cero.
- Habla como TRAGO.: de tú, corto y cálido. Sin sermones ni explicaciones largas.
- Si contesta corto, está bien. Si no quiere contestar algo, guarda «prefiere no decirlo».
- Cada 3 o 4 respuestas, guarda con `guardar_perfil`, cada respuesta en su campo (el nombre del campo va entre paréntesis abajo). Así no se pierde nada si la sesión se corta.
- Guarda sus palabras, resumidas si hace falta. Nunca guardes contraseñas, llaves ni datos de otras personas (teléfonos, cuánto le pagan a alguien); si los dice, no los guardes y díselo.
- Si se tiene que ir: guarda lo que lleve y dile que siguen cuando quiera («sigamos con la entrevista»).
- Los avisos y el reporte del día llegan solo aquí en Claude, al abrir sesión. No ofrezcas WhatsApp, correo ni otro canal: no existen. Si la persona lo pide, guárdalo como deseo («le gustaría por WhatsApp») y dile que por ahora llega en Claude.
- La 17 es solo para Fradell (la coordinadora).

## Las preguntas (en este orden)

1. (trato) ¿Cómo te digo y cómo te gusta que te hable?
2. (rol) ¿Qué haces en TRAGO., en tus palabras?
3. (semana) ¿Qué haces en una semana normal? Todo lo que te toca.
4. (negocios) ¿Qué negocios y páginas llevas?
5. (te_piden) ¿Quién te pide cosas y por dónde te llegan (WhatsApp, junta, la app)?
6. (pendientes) ¿Cómo sabes qué te toca y para cuándo? ¿Dónde lo apuntas?
7. (atraso) ¿Qué es un atraso para ti? ¿Cuándo quieres que te avise?
8. (reporte) ¿A qué hora quieres tu reporte del día? (Llega aquí en Claude.)
9. (se_atraso) ¿Qué se te atrasó u olvidó el último mes, y por qué?
10. (buscas) ¿Qué información buscas seguido y te cuesta encontrar? Dame tres ejemplos reales.
11. (aprobacion) ¿Qué pasas a aprobación, a quién, y cuánto esperas?
12. (atorado) Cuéntame una tarea de varios pasos que se atoró. ¿Qué pasó?
13. (a_mano) ¿Qué haces a mano que te gustaría que hiciera Claude?
14. (tablero) Si abrieras un tablero cada mañana, ¿qué quieres ver primero?
15. (donde) ¿Trabajas más desde la compu o desde el celular? ¿Para qué usas Claude hoy?
16. (privado) De lo que manejas, ¿qué no debería ver todo el equipo?
17. (seguimiento) Solo Fradell: ¿cómo le das seguimiento a tu equipo y qué quieres saber de cada quien sin preguntarle?

## Al terminar

Enséñale el resumen en 5 a 7 líneas, en sus palabras, y pregunta «¿Así?». Corrige lo que diga y guárdalo. Cierra con: «Listo 💙 Desde ahora, cuando hablemos de TRAGO., ya sé esto de ti. Si algo cambia, dime "actualiza mi perfil"».

Si pide cambiar algo después, pregunta qué y guarda solo ese campo.

## La app

El paquete también trae las herramientas de la app de marketing (servidor «app» de este paquete: `quien_soy`, `planeacion_ver`, `pieza_ver`…; si la persona ya tenía su propio conector «trago-marketing», el del paquete viene vacío y se usa el suyo). Entran con el usuario y la contraseña de la app de cada quien, con sus mismos permisos.

1. Al terminar la entrevista, llama `quien_soy` del servidor «app». Si contesta con su usuario, listo.
2. Si dice que falta la contraseña o que la app no la aceptó, corre el comando que trae ese mensaje (`sh '…/guardar-clave.sh'`, con 10 minutos de tiempo de espera: la persona tiene que escribir): abre dos ventanitas de la Mac, usuario y contraseña, y la guarda en su llavero. Tú solo ves «Guardada». Luego, sesión nueva.
3. **Nunca le pidas la contraseña en el chat.** Si la escribe ahí, no la uses ni la repitas, y dile que le avise a Luis para cambiarla.
4. Si el servidor «app» no aparece o dice que falta Python: que corra `xcode-select --install` (la ventana de Apple, una vez) y abra una sesión nueva.
5. Lo delicado (avisar al equipo, programar, borrar, aprobar) regresa un código: enséñale qué va a pasar y solo con su «sí» llamas `confirmar`. Si la app de Claude le pide permiso para `confirmar`, que nunca elija «permitir siempre».

## Si falta el conector

Se agrega una vez y sirve en la compu y en el celular. En claude.ai (o en la app de Claude):

1. Personalizar › Conectores › «+ Añadir» › «Añadir conector personalizado».
2. Nombre: `Cerebro TRAGO.` · URL: `https://cerebro.tragotragotrago.com/mcp` › Continuar.
3. En «Cliente OAuth» deja «Usar la identidad publicada de Claude (Recomendado)». Las otras dos opciones no funcionan con el Cerebro.
4. «Iniciar sesión ahora» › «Añadir» › entra con **tu** Google (el tuyo, nunca una cuenta compartida de TRAGO.).
5. Abre una sesión nueva.

Si alguien te manda un link para conectar el Cerebro, no lo abras: solo se conecta así, desde tus propios Ajustes.

// La app de marketing dentro del paquete: el arranque (Python y usuario del llavero), los avisos al abrir sesión, la ventanita que
// guarda la contraseña y el MCP de verdad por stdio. `security`, `osascript`, `xcode-select` y los Python son falsos que anotan.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync, spawn, spawnSync } from "node:child_process";

const PAQ = new URL("../trago-marketing/", import.meta.url).pathname;
const SCRIPTS = path.join(PAQ, "scripts");
const NADA = "/no/existe/python3";

// Una carpeta con programas falsos; cada uno anota en llamadas.log «nombre|args».
function montar(falsos) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "app-"));
  const bin = path.join(dir, "bin"), log = path.join(dir, "llamadas.log");
  fs.mkdirSync(bin);
  for (const [nombre, cuerpo] of Object.entries(falsos)) {
    fs.writeFileSync(path.join(bin, nombre), `#!/bin/sh\necho "${nombre}|$*" >> "${log}"\n${cuerpo}\n`, { mode: 0o755 });
  }
  const llamadas = () => (fs.existsSync(log) ? fs.readFileSync(log, "utf8").trim().split("\n").filter(Boolean) : []);
  const env = (extra = {}) => ({ PATH: `${bin}:/usr/bin:/bin`, HOME: dir, PYTHONDONTWRITEBYTECODE: "1", ...extra });
  return { dir, bin, llamadas, env };
}

// «security» que tiene (o no) la entrada de la app; nunca entrega una contraseña.
const SECURITY = (usuario) => (usuario
  ? `case "$1" in find-generic-password) case "$*" in *-w*) exit 44 ;; esac; echo 'keychain: "/x"'; echo '    "acct"<blob>="${usuario}"'; echo '    "svce"<blob>="trago-marketing-app"' ;; esac`
  : "exit 44");
// Python falso: pasa la revisión de certificados y anota con qué lo arrancan.
const PY_FALSO = (log, certificados = true) => `case "$*" in *cert_store_stats*) exit ${certificados ? 0 : 1} ;; *claude.json*) exit 1 ;; esac\necho "TM_USUARIO=$TM_USUARIO base=\${TM_BASE:-no} $*" >> "${log}"`;

test("arranque: usa el Python de Homebrew y el usuario del llavero", () => {
  const m = montar({ security: SECURITY("fulana") });
  const py = path.join(m.bin, "py-homebrew"), uso = path.join(m.dir, "uso.log");
  fs.writeFileSync(py, `#!/bin/sh\n${PY_FALSO(uso)}\n`, { mode: 0o755 });
  const r = spawnSync("sh", [path.join(SCRIPTS, "app-mcp.sh")], { encoding: "utf8", env: m.env({ TRAGO_PY_OTROS: `${NADA} ${py}`, TRAGO_PY_APPLE: NADA, TM_BASE: "https://otro.ejemplo" }) });
  assert.equal(r.status, 0, r.stderr);
  const linea = fs.readFileSync(uso, "utf8").trim();
  assert.match(linea, /^TM_USUARIO=fulana base=no -E -s \S*\/app\/trago_marketing_mcp\.py$/, "la contraseña nunca va a otra base");
  assert.ok(fs.existsSync(linea.split(" ").at(-1)), "el MCP existe donde lo busca");
});

test("arranque sin usuario guardado: «sin-usuario», nunca el de otra persona", () => {
  const m = montar({ security: SECURITY(null) });
  const py = path.join(m.bin, "py"), uso = path.join(m.dir, "uso.log");
  fs.writeFileSync(py, `#!/bin/sh\n${PY_FALSO(uso)}\n`, { mode: 0o755 });
  spawnSync("sh", [path.join(SCRIPTS, "app-mcp.sh")], { env: m.env({ TRAGO_PY_OTROS: py }) });
  assert.match(fs.readFileSync(uso, "utf8"), /^TM_USUARIO=sin-usuario /);
});

test("arranque sin Python ni herramientas de Apple: no toca el python3 de Apple y dice qué hacer", () => {
  const m = montar({ security: SECURITY("fulana"), "xcode-select": "exit 2" });
  const apple = path.join(m.bin, "py-apple"), uso = path.join(m.dir, "uso.log");
  fs.writeFileSync(apple, `#!/bin/sh\n${PY_FALSO(uso)}\n`, { mode: 0o755 });
  const r = spawnSync("sh", [path.join(SCRIPTS, "app-mcp.sh")], { encoding: "utf8", env: m.env({ TRAGO_PY_OTROS: NADA, TRAGO_PY_APPLE: apple }) });
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /xcode-select --install/);
  assert.ok(!fs.existsSync(uso), "el python3 de Apple no se corrió (abriría la ventana de instalar)");
  // con las herramientas de Apple instaladas, sí lo usa
  fs.writeFileSync(path.join(m.bin, "xcode-select"), "#!/bin/sh\necho /Library/Developer/CommandLineTools\n", { mode: 0o755 });
  assert.equal(spawnSync("sh", [path.join(SCRIPTS, "app-mcp.sh")], { env: m.env({ TRAGO_PY_OTROS: NADA, TRAGO_PY_APPLE: apple }) }).status, 0);
  assert.match(fs.readFileSync(uso, "utf8"), /^TM_USUARIO=fulana /);
});

test("al abrir sesión: avisa si falta Python o la contraseña, con la ruta de la ventanita; si todo está, no avisa", () => {
  const correr = (m, extra) => execFileSync("sh", [path.join(SCRIPTS, "al-empezar.sh")], { encoding: "utf8",
    env: m.env({ CLAUDE_PLUGIN_DATA: path.join(m.dir, "datos"), CLAUDE_CODE_EXECPATH: "", ...extra }) });
  const sinNada = montar({ security: SECURITY(null), "xcode-select": "exit 2" });
  const s = correr(sinNada, { TRAGO_PY_OTROS: NADA });
  assert.match(s, /falta Python.*xcode-select --install/);
  const clave = s.match(/corre «sh '([^']+)'»/);
  assert.ok(clave, s);
  assert.equal(clave[1], path.join(SCRIPTS, "guardar-clave.sh"));
  assert.match(s, /Nunca se la pidas en el chat/);
  assert.match(s, /contexto/, "el aviso de siempre sale igual");
  const todo = montar({ security: SECURITY("fulana") });
  fs.writeFileSync(path.join(todo.bin, "py"), `#!/bin/sh\n${PY_FALSO(path.join(todo.dir, "uso.log"))}\n`, { mode: 0o755 });
  const t = correr(todo, { TRAGO_PY_OTROS: path.join(todo.bin, "py") });
  assert.doesNotMatch(t, /Python|contraseña/);
});

test("un Python sin certificados (python.org sin «Install Certificates») se salta: no podría hablar con la app", () => {
  const m = montar({ security: SECURITY("fulana") });
  const sin = path.join(m.bin, "py-sin"), con = path.join(m.bin, "py-con"), uso = path.join(m.dir, "uso.log");
  fs.writeFileSync(sin, `#!/bin/sh\n${PY_FALSO(uso, false)}\n`, { mode: 0o755 });
  fs.writeFileSync(con, `#!/bin/sh\n${PY_FALSO(uso)}\n`, { mode: 0o755 });
  assert.equal(execFileSync("sh", [path.join(SCRIPTS, "python.sh")], { encoding: "utf8", env: m.env({ TRAGO_PY_OTROS: `${sin} ${con}`, TRAGO_PY_APPLE: NADA }) }).trim(), con);
  assert.notEqual(spawnSync("sh", [path.join(SCRIPTS, "python.sh")], { env: m.env({ TRAGO_PY_OTROS: sin, TRAGO_PY_APPLE: NADA }) }).status, 0);
});

// Ventanitas falsas: contestan en orden lo que trae RESPUESTAS (una por línea); «CANCELAR» = botón Cancelar.
function montarClave(respuestas, { guardarFalla = false, previas = 0 } = {}) {
  const m = montar({
    osascript: `n=$(cat "$CUENTA" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$CUENTA"; r=$(sed -n "\${n}p" "$RESPUESTAS"); [ "$r" = CANCELAR ] && exit 1; printf '%s\\n' "$r"`,
    security: `case "$1" in delete-generic-password) n=$(cat "$BORRAR" 2>/dev/null || echo ${previas}); [ "$n" -gt 0 ] || exit 44; echo $((n-1)) > "$BORRAR" ;; add-generic-password) exit ${guardarFalla ? 1 : 0} ;; esac`,
  });
  fs.writeFileSync(path.join(m.dir, "respuestas"), respuestas.join("\n") + "\n");
  const r = spawnSync("sh", [path.join(SCRIPTS, "guardar-clave.sh")], { encoding: "utf8",
    env: m.env({ CUENTA: path.join(m.dir, "cuenta"), RESPUESTAS: path.join(m.dir, "respuestas"), BORRAR: path.join(m.dir, "borrar") }) });
  return { ...m, r, salida: r.stdout + r.stderr };
}
const CLAVE = "S3creta-de-prueba!";

test("guardar-clave: usuario limpio, contraseña escondida, una sola entrada; la contraseña nunca sale en lo que escribe", () => {
  const m = montarClave(["  Fulana.Perez ", CLAVE], { previas: 2 });
  assert.equal(m.r.status, 0, m.salida);
  assert.match(m.salida, /Guardada para «fulana\.perez»/);
  assert.ok(!m.salida.includes(CLAVE));
  const ll = m.llamadas();
  assert.match(ll[1], /hidden answer/, "la contraseña se pide escondida");
  assert.doesNotMatch(ll[0], /hidden answer/);
  assert.equal(ll.filter((x) => x.startsWith("security|delete-generic-password -s trago-marketing-app")).length, 3, "borra las 2 de antes y para");
  assert.equal(ll.at(-1), `security|add-generic-password -U -a fulana.perez -s trago-marketing-app -w ${CLAVE}`);
});

test("guardar-clave: cancelar, usuario raro, contraseña vacía o llavero que falla no guardan nada ni enseñan la contraseña", () => {
  for (const [resp, que] of [[["CANCELAR"], /Cancelado/], [["fulana", "CANCELAR"], /Cancelado/], [["ful;ana", CLAVE], /no es válido/], [["fulana", ""], /vacía/]]) {
    const m = montarClave(resp);
    assert.notEqual(m.r.status, 0, resp.join(","));
    assert.match(m.salida, que);
    assert.ok(!m.llamadas().some((x) => /add-generic-password|delete-generic-password/.test(x)), `no tocó el llavero: ${resp}`);
  }
  const f = montarClave(["fulana", CLAVE], { guardarFalla: true });
  assert.notEqual(f.r.status, 0);
  assert.match(f.salida, /No se pudo guardar/);
  assert.ok(!f.salida.includes(CLAVE));
});

// El MCP de verdad, por stdio, con el python3 de Apple (3.9): lo que tiene una Mac del equipo sin Homebrew.
test("el MCP de la app arranca con el python3 de Apple y contesta tools/list; sin contraseña lo dice con la ventanita", { skip: !fs.existsSync("/usr/bin/python3") || spawnSync("xcode-select", ["-p"]).status !== 0 }, async () => {
  const m = montar({ security: SECURITY("fulana") });
  const p = spawn("sh", [path.join(SCRIPTS, "app-mcp.sh")], { env: m.env({ TRAGO_PY_OTROS: NADA, TM_BASE: "http://127.0.0.1:9" }) });
  let out = "", err = "";
  p.stdout.on("data", (d) => (out += d));
  p.stderr.on("data", (d) => (err += d));
  const mandar = (o) => p.stdin.write(JSON.stringify(o) + "\n");
  mandar({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "prueba", version: "0" } } });
  mandar({ jsonrpc: "2.0", method: "notifications/initialized" });
  mandar({ jsonrpc: "2.0", id: 2, method: "tools/list" });
  mandar({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "quien_soy", arguments: {} } });
  for (let i = 0; i < 100 && out.trim().split("\n").length < 3; i++) await new Promise((r) => setTimeout(r, 50));
  p.stdin.end();
  await new Promise((r) => p.on("close", r));
  const resp = Object.fromEntries(out.trim().split("\n").map((l) => JSON.parse(l)).map((j) => [j.id, j]));
  assert.ok(resp[2], `sin tools/list: ${err}`);
  assert.match(m.llamadas().join("\n"), /security\|find-generic-password -a fulana -s trago-marketing-app -w/, "pidió la contraseña de su usuario");
  const python = execFileSync("/usr/bin/python3", ["--version"], { encoding: "utf8" });
  assert.match(python, /^Python 3\.9/);
  const nombres = resp[2].result.tools.map((t) => t.name);
  for (const n of ["quien_soy", "planeacion_ver", "confirmar"]) assert.ok(nombres.includes(n), n);
  const texto = JSON.stringify(resp[3]);
  assert.match(texto, /Falta tu contraseña/);
  const ruta = texto.match(/sh '([^']+)'/);
  assert.equal(ruta?.[1], path.join(SCRIPTS, "guardar-clave.sh"), "manda a la ventanita del paquete");
  assert.doesNotMatch(texto, /Terminal/);
});

// Arranca el MCP del paquete por stdio y regresa los nombres de sus herramientas.
async function herramientas(m, extra = {}) {
  const p = spawn("sh", [path.join(SCRIPTS, "app-mcp.sh")], { env: m.env({ TRAGO_PY_OTROS: NADA, ...extra }) });
  let out = "";
  p.stdout.on("data", (d) => (out += d));
  p.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "prueba", version: "0" } } }) + "\n");
  p.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }) + "\n");
  for (let i = 0; i < 100 && out.trim().split("\n").length < 2; i++) await new Promise((r) => setTimeout(r, 50));
  p.stdin.end();
  await new Promise((r) => p.on("close", r));
  return JSON.parse(out.trim().split("\n")[1]).result.tools.map((x) => x.name);
}

test("si la Mac ya tiene su propio conector de la app, el del paquete arranca sin herramientas (no se repiten)", { skip: !fs.existsSync("/usr/bin/python3") || spawnSync("xcode-select", ["-p"]).status !== 0 }, async () => {
  const m = montar({ security: SECURITY("fulana") });
  const propio = { mcpServers: { "trago-marketing": { type: "stdio", command: "/opt/homebrew/bin/python3", args: ["/Users/x/trago-marketing-mcp/trago_marketing_mcp.py"] } } };
  assert.ok((await herramientas(m)).includes("quien_soy"), "sin conector propio, el del paquete trae todo");
  fs.writeFileSync(path.join(m.dir, ".claude.json"), JSON.stringify({ mcpServers: { otro: { command: "x" } } }));
  assert.ok((await herramientas(m)).includes("quien_soy"), "otro conector cualquiera no lo apaga");
  fs.writeFileSync(path.join(m.dir, ".claude.json"), JSON.stringify(propio));
  assert.deepEqual(await herramientas(m), []);
  const cfg = path.join(m.dir, "cfg");
  fs.mkdirSync(cfg);
  fs.renameSync(path.join(m.dir, ".claude.json"), path.join(cfg, ".claude.json"));
  assert.deepEqual(await herramientas(m, { CLAUDE_CONFIG_DIR: cfg }), [], "también con CLAUDE_CONFIG_DIR");
});

test("las pruebas del MCP de la app (redirects, 401, candado de confirmar, subidas) pasan contra la copia parchada del paquete", () => {
  const r = spawnSync("python3", ["-B", "-m", "unittest", "test_mcp"], { cwd: path.join(PAQ, "app"), encoding: "utf8",
    env: { PATH: "/opt/homebrew/bin:/usr/bin:/bin", HOME: os.tmpdir(), TM_USUARIO: "luis", PYTHONPATH: new URL("app-py", import.meta.url).pathname } });
  assert.equal(r.status, 0, r.stderr.slice(-1500));
  assert.match(r.stderr, /Ran (\d{2,}) tests/);
});

test("la copia de la app: no dice «Luis», no cae en su usuario, su actualizador no corre git, y todo lo que nombra existe", () => {
  const app = path.join(PAQ, "app");
  const archivos = (p) => (fs.statSync(p).isDirectory() ? fs.readdirSync(p).flatMap((x) => archivos(path.join(p, x))) : [p]);
  const todos = archivos(app);
  assert.ok(todos.some((f) => f.endsWith("tm/mcp.py")) && fs.existsSync(path.join(app, "ORIGEN")));
  for (const f of todos) assert.doesNotMatch(fs.readFileSync(f, "utf8"), /Luis|LUIS|de_luis/, path.relative(PAQ, f));
  const api = fs.readFileSync(path.join(app, "tm/api.py"), "utf8");
  assert.match(api, /"TM_USUARIO", "sin-usuario"/);
  assert.doesNotMatch(fs.readFileSync(path.join(app, "tm/actualizar.py"), "utf8"), /subprocess|os\.system|os\.popen|["']git["']/);
  const mcp = JSON.parse(fs.readFileSync(path.join(PAQ, ".mcp.json"), "utf8")).mcpServers.app;
  assert.deepEqual([mcp.command, ...mcp.args], ["sh", "${CLAUDE_PLUGIN_ROOT}/scripts/app-mcp.sh"]);
});

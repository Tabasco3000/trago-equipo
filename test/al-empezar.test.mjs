// El aviso al abrir sesión y el actualizador propio, con un Claude Code falso que anota lo que le piden.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

const SCRIPT = new URL("../trago-marketing/scripts/al-empezar.sh", import.meta.url).pathname;
const HORA = 3600;

function montar({ falla = false } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "al-empezar-"));
  const datos = path.join(dir, "datos"), log = path.join(dir, "llamadas.log");
  const falso = path.join(dir, "claude");
  fs.writeFileSync(falso, `#!/bin/sh\necho "$*" >> "${log}"\nexit ${falla ? 1 : 0}\n`, { mode: 0o755 });
  const correr = (env = {}) => {
    const t0 = Date.now();
    const salida = execFileSync("sh", [SCRIPT], { encoding: "utf8", env: { PATH: "/usr/bin:/bin", HOME: dir, CLAUDE_PLUGIN_DATA: datos, CLAUDE_CODE_EXECPATH: falso, ...env } });
    return { salida, ms: Date.now() - t0 };
  };
  const llamadas = () => (fs.existsSync(log) ? fs.readFileSync(log, "utf8").trim().split("\n").filter(Boolean) : []);
  const leer = (f) => (fs.existsSync(path.join(datos, f)) ? fs.readFileSync(path.join(datos, f), "utf8").trim() : null);
  const escribir = (f, v) => fs.writeFileSync(path.join(datos, f), String(v));
  const esperar = async (cond) => { for (let i = 0; i < 100 && !cond(); i++) await new Promise((r) => setTimeout(r, 20)); };
  const ahora = () => Math.floor(Date.now() / 1000);
  return { dir, datos, correr, llamadas, leer, escribir, esperar, ahora };
}

test("primera vez: aviso de primera sesión y revisa versión nueva en segundo plano, en orden; rápido", async () => {
  const m = montar();
  const { salida, ms } = m.correr();
  assert.match(salida, /primera sesión con el paquete del Cerebro TRAGO\./);
  assert.match(salida, /«contexto»/);
  assert.ok(ms < 1500, `tardó ${ms} ms`);
  await m.esperar(() => m.llamadas().length === 2 && !fs.existsSync(path.join(m.datos, "candado")));
  assert.deepEqual(m.llamadas(), ["plugin marketplace update trago-equipo", "plugin update trago-marketing@trago-equipo"]);
  assert.ok(m.leer("ok") && m.leer("revisado"));
});

test("la segunda sesión trae el aviso de siempre y no vuelve a revisar antes de 6 horas", async () => {
  const m = montar();
  m.correr();
  await m.esperar(() => m.llamadas().length === 2);
  const { salida } = m.correr();
  assert.match(salida, /Cuando la plática sea de TRAGO\., llama una vez a «contexto»/);
  assert.doesNotMatch(salida, /primera sesión/);
  await new Promise((r) => setTimeout(r, 200));
  assert.equal(m.llamadas().length, 2);
  m.escribir("revisado", m.ahora() - 7 * HORA);
  m.correr();
  await m.esperar(() => m.llamadas().length === 4);
  assert.equal(m.llamadas().length, 4);
});

test("candado: si otra sesión está revisando, no se encima; un candado viejo (10 min) se suelta", async () => {
  const m = montar();
  m.correr();
  await m.esperar(() => m.llamadas().length === 2 && !fs.existsSync(path.join(m.datos, "candado")));
  fs.mkdirSync(path.join(m.datos, "candado"));
  m.escribir("revisado", 0);
  m.correr();
  await new Promise((r) => setTimeout(r, 200));
  assert.equal(m.llamadas().length, 2, "con candado fresco no revisa");
  const viejo = new Date(Date.now() - 11 * 60_000);
  fs.utimesSync(path.join(m.datos, "candado"), viejo, viejo);
  m.correr();
  await m.esperar(() => m.llamadas().length === 4);
  assert.equal(m.llamadas().length, 4, "el candado viejo se soltó");
});

test("si no se pudo actualizar, no marca «ok»; a los 3 días sin poder, avisa que le digan a Luis", async () => {
  const m = montar({ falla: true });
  fs.mkdirSync(m.datos, { recursive: true });
  const viejo = m.ahora() - 4 * 24 * HORA;
  m.escribir("visto", ""); m.escribir("ok", viejo);
  assert.match(m.correr().salida, /no se ha podido actualizar en más de 3 días.*Luis/s);
  await m.esperar(() => m.llamadas().length >= 1 && !fs.existsSync(path.join(m.datos, "candado")));
  assert.deepEqual(m.llamadas(), ["plugin marketplace update trago-equipo"], "si falla el catálogo no sigue");
  assert.equal(m.leer("ok"), String(viejo), "una actualización que falló no cuenta como «ok»");
  m.escribir("ok", m.ahora() - 2 * 24 * HORA);
  assert.doesNotMatch(m.correr().salida, /no se ha podido actualizar/);
});

test("sin Claude Code a la mano o con archivos rotos: el aviso sale igual y la sesión no truena", async () => {
  const m = montar();
  const sin = m.correr({ CLAUDE_CODE_EXECPATH: "" });
  assert.match(sin.salida, /contexto/);
  fs.mkdirSync(m.datos, { recursive: true });
  m.escribir("revisado", "abc"); m.escribir("ok", "x y");
  const roto = m.correr({ CLAUDE_CODE_EXECPATH: "" });
  assert.match(roto.salida, /contexto/);
  assert.doesNotMatch(roto.salida, /no se ha podido/);
  assert.match(m.correr({ CLAUDE_PLUGIN_DATA: "", CLAUDE_CODE_EXECPATH: "" }).salida, /contexto/, "sin carpeta de datos usa la de respaldo");
});

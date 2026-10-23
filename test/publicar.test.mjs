// publicar.sh contra un GitHub de mentira (un repo «bare» local) y un Claude Code falso para la validación.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync, spawnSync } from "node:child_process";

const RAIZ = new URL("..", import.meta.url).pathname;
const git = (cwd, ...a) => execFileSync("git", a, { cwd, encoding: "utf8" }).trim();

function montar({ rechazar = false } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "publicar-"));
  const remoto = path.join(dir, "remoto.git"), copia = path.join(dir, "copia");
  git(dir, "init", "-q", "--bare", "-b", "main", remoto);
  if (rechazar) fs.writeFileSync(path.join(remoto, "hooks", "pre-receive"), "#!/bin/sh\nexit 1\n", { mode: 0o755 });
  // la copia de trabajo tal cual (sin .git ni zips), como un clon limpio: sin las carpetas vacías
  fs.cpSync(RAIZ, copia, { recursive: true, filter: (f) => !/\/\.git(\/|$)|\/dist\/|\.claude-plugin\/marketplace\.json$/.test(f) });
  for (const vacia of ["dist", ".claude-plugin"]) fs.rmSync(path.join(copia, vacia), { recursive: true, force: true });
  git(copia, "init", "-q", "-b", "main");
  git(copia, "config", "user.name", "prueba"); git(copia, "config", "user.email", "prueba@ejemplo.com");
  git(copia, "add", "-A"); git(copia, "commit", "-q", "-m", "base");
  git(copia, "remote", "add", "origin", remoto);
  fs.writeFileSync(path.join(dir, "claude"), "#!/bin/sh\nexit 0\n", { mode: 0o755 });
  const publicar = (v, extra = {}) => spawnSync("sh", ["publicar.sh", v], { cwd: copia, encoding: "utf8",
    env: { ...process.env, CLAUDE_CODE_EXECPATH: path.join(dir, "claude"), HEAVY_ADMISSION_BYPASS: "1", ...extra } });
  return { remoto, copia, publicar };
}

test("publica: zip con su huella, catálogo y versión en un solo commit en main del remoto", () => {
  const m = montar();
  const r = m.publicar("9.9.1");
  assert.equal(r.status, 0, r.stderr);
  const cat = JSON.parse(git(m.remoto, "show", "main:.claude-plugin/marketplace.json"));
  const fuente = cat.plugins[0].source;
  assert.equal(fuente.url, "https://raw.githubusercontent.com/Tabasco3000/trago-equipo/main/dist/trago-marketing-9.9.1.zip");
  const zip = execFileSync("git", ["show", "main:dist/trago-marketing-9.9.1.zip"], { cwd: m.remoto });
  assert.equal(fuente.sha256, (execFileSync("shasum", ["-a", "256"], { input: zip, encoding: "utf8" }).slice(0, 64)));
  assert.match(git(m.remoto, "show", "main:trago-marketing/.claude-plugin/plugin.json"), /"version": "9\.9\.1"/);
  assert.equal(git(m.remoto, "log", "-1", "--format=%s", "main"), "Versión 9.9.1");
  assert.equal(git(m.copia, "rev-parse", "HEAD"), git(m.remoto, "rev-parse", "main"), "la copia de trabajo queda al día");
});

test("solo publica lo que está en git: nada ignorado ni suelto llega al zip ni al repo", () => {
  const m = montar();
  fs.mkdirSync(path.join(m.copia, "trago-marketing", ".claude"), { recursive: true });
  fs.writeFileSync(path.join(m.copia, "trago-marketing", ".claude", "settings.local.json"), "{}");
  fs.writeFileSync(path.join(m.copia, ".git", "info", "exclude"), "trago-marketing/.claude/\n");
  assert.equal(m.publicar("9.9.4").status, 0);
  const zip = path.join(m.copia, "..", "bajado.zip");
  fs.writeFileSync(zip, execFileSync("git", ["show", "main:dist/trago-marketing-9.9.4.zip"], { cwd: m.remoto }));
  const lista = execFileSync("unzip", ["-l", zip], { encoding: "utf8" });
  assert.doesNotMatch(lista, /settings\.local/);
  assert.match(lista, /\.claude-plugin\/plugin\.json/);
  assert.doesNotMatch(git(m.remoto, "ls-tree", "-r", "--name-only", "main"), /settings\.local/);
});

test("si el push falla, todo queda como estaba y se puede reintentar", () => {
  const m = montar({ rechazar: true });
  const antes = git(m.copia, "rev-parse", "HEAD");
  const r = m.publicar("9.9.2");
  assert.notEqual(r.status, 0);
  assert.equal(git(m.copia, "rev-parse", "HEAD"), antes);
  assert.equal(git(m.copia, "status", "--porcelain"), "");
  assert.ok(!fs.existsSync(path.join(m.copia, "dist", "trago-marketing-9.9.2.zip")));
});

test("no publica desde otra rama ni con versiones raras", () => {
  const m = montar();
  git(m.copia, "checkout", "-q", "-b", "otra");
  assert.notEqual(m.publicar("9.9.3").status, 0);
  assert.equal(spawnSync("git", ["rev-parse", "--verify", "-q", "main"], { cwd: m.remoto }).status === 0 ? git(m.remoto, "log", "-1", "--format=%s", "main") : "", "");
  git(m.copia, "checkout", "-q", "main");
  for (const v of ["", "1.0;rm", "v1", ".1", "1.", "1..2", "00", "1.2.3.4", "1.2"]) assert.notEqual(m.publicar(v).status, 0, v);
});

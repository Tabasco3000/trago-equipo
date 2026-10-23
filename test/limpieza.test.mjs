// El paquete es público: nada de llaves, correos, IDs del Drive ni reglas del negocio. Esto truena antes de publicar.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const RAIZ = new URL("..", import.meta.url).pathname;
const REVISAR = [".claude-plugin", "trago-marketing", "README.md", "publicar.sh"];
const PROHIBIDO = [
  [/[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}/, "un correo"],
  [/\b(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Z])[A-Za-z0-9_-]{25,}\b|\b[0-9a-f]{32,}\b/, "algo con forma de llave o de ID del Drive"],
  [/sk-[A-Za-z0-9]|AKIA[0-9A-Z]|ghp_|xox[bp]-|BEGIN [A-Z ]*PRIVATE KEY/, "una llave"],
  [/drive\.google|docs\.google/i, "un link del Drive"],
  [/presupuest|n[oó]mina|sueldo|salari|contrat|factur|cotizaci|honorari|\bCAC\b|tragomexico|marketingtrago|TRAGO\. MASTER/i, "algo del negocio"],
];
// Lo único con forma de llave que puede ir: la huella sha256 del zip, en su campo del catálogo.
const PERMITIDO = /"sha256": "[0-9a-f]{64}"/g;

const archivos = (p) => (fs.statSync(p).isDirectory() ? fs.readdirSync(p).flatMap((x) => archivos(path.join(p, x))) : [p]);

test("el paquete público no lleva nada que no deba", () => {
  // en un clon limpio .claude-plugin/ todavía no existe (git no guarda carpetas vacías)
  const vistos = REVISAR.map((x) => path.join(RAIZ, x)).filter((x) => fs.existsSync(x)).flatMap(archivos);
  assert.ok(vistos.some((f) => f.endsWith("SKILL.md")), "revisó la entrevista");
  assert.ok(vistos.some((f) => f.endsWith("app/tm/mcp.py")), "revisó la copia de la app");
  for (const f of vistos) {
    const texto = fs.readFileSync(f, "utf8").replace(PERMITIDO, "");
    for (const [re, que] of PROHIBIDO) {
      const m = texto.match(re);
      assert.equal(m, null, `${path.relative(RAIZ, f)} trae ${que}: «${m?.[0]}»`);
    }
  }
});

test("la prueba de limpieza sí agarra (se rompe a propósito)", () => {
  // ejemplos inventados: este archivo también es público
  for (const malo of ["alguien@ejemplo.com", "1AbCdEfGhIjKlMnOpQrStUvWxYz0123", "ghp_abc", "presupuesto de pauta", "https://docs.google.com/x"]) {
    assert.ok(PROHIBIDO.some(([re]) => re.test(malo)), malo);
  }
});

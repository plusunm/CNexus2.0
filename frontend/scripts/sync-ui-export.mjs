/** Copy Next.js static export (out/) to repo ui/ for app_v2.py static serving. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, "..", "out");
const uiDir = path.join(__dirname, "..", "..", "ui");

if (!fs.existsSync(outDir)) {
  console.error(`Missing export dir: ${outDir} — run npm run build:personal first`);
  process.exit(1);
}

fs.rmSync(uiDir, { recursive: true, force: true });
fs.cpSync(outDir, uiDir, { recursive: true });
console.log(`Synced ${outDir} → ${uiDir}`);

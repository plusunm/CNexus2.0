/** Sync troubleshooting doc into static UI + Tauri installer resources. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..", "..");
const source = path.join(root, "docs", "cnexus-personal-troubleshooting.md");
const targets = [
  path.join(__dirname, "..", "public", "help", "cnexus-personal-troubleshooting.md"),
  path.join(__dirname, "..", "src-tauri", "resources", "help", "cnexus-personal-troubleshooting.md"),
];

if (!fs.existsSync(source)) {
  console.error(`Missing help source: ${source}`);
  process.exit(1);
}

const text = fs.readFileSync(source, "utf8");
for (const dest of targets) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, text, "utf8");
  console.log(`Synced help → ${dest}`);
}

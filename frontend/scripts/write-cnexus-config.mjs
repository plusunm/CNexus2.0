import fs from "node:fs";
import path from "node:path";

/** Release installer → enterprise only when explicitly requested. Dev → personal. */
const editionArg = process.argv[2];
const edition =
  editionArg === "personal"
    ? "personal"
    : editionArg === "enterprise" || editionArg === "release"
      ? "enterprise"
      : process.env.CNEXUS_EDITION === "enterprise"
        ? "enterprise"
        : "personal";

const gatewayPort = process.env.CNEXUS_GATEWAY_PORT ?? "7864";
const personalGateway = `http://127.0.0.1:${gatewayPort}`;
const apiBase = process.env.CNEXUS_API_BASE ?? personalGateway;
const wsBase =
  process.env.CNEXUS_WS_BASE ??
  (edition === "personal" ? "" : apiBase.replace(/^http/, "ws"));
const apiToken = process.env.CNEXUS_API_TOKEN ?? "";

const cfg = {
  edition,
  apiBase,
  wsBase,
};
if (apiToken) Object.assign(cfg, { apiToken });

const out = path.join(process.cwd(), "public", "cnexus-config.json");
fs.writeFileSync(out, `${JSON.stringify(cfg)}\n`, "utf8");
console.log(`Wrote ${out} (unified installer, edition=${edition})`);

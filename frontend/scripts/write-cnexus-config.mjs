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
// Empty apiBase → browser uses same origin (LAN / localhost both work).
const apiBase =
  process.env.CNEXUS_API_BASE ??
  (edition === "personal" ? "" : personalGateway);
const wsBase =
  process.env.CNEXUS_WS_BASE ??
  (edition === "personal" ? "" : apiBase.replace(/^http/, "ws"));
const apiToken = process.env.CNEXUS_API_TOKEN ?? "";

const cfg = {
  edition,
  apiBase,
  wsBase,
  bootstrapPeers: [
    {
      pubkey: "4db22395a0bd6abd5aad862d4c70436e47e2dac2712644ec57347d344ea1ea8c",
      host: "http://114.55.62.198:7864",
      label: "hub",
    },
    {
      pubkey: "da5886a7d0199609d431e0d23022503fd93eda68756f64d20ca454a9ade56abf",
      host: "",
      label: "founder",
    },
  ],
};
if (apiToken) Object.assign(cfg, { apiToken });

const out = path.join(process.cwd(), "public", "cnexus-config.json");
fs.writeFileSync(out, `${JSON.stringify(cfg)}\n`, "utf8");
console.log(`Wrote ${out} (unified installer, edition=${edition})`);

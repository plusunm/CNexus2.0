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
      pubkey: "4cbe1a21e9e202b128fa07395a6e06ab9ad7e2861bcdd7ce411e2f24c5b817ed",
      host: "http://114.55.62.198:7864",
      label: "hub",
    },
    {
      pubkey: "d7ff9669ed23349e92490ac03cc58980fb6440382637f944077bb0b4e5e68075",
      host: "",
      label: "founder",
    },
  ],
};
if (apiToken) Object.assign(cfg, { apiToken });

const out = path.join(process.cwd(), "public", "cnexus-config.json");
fs.writeFileSync(out, `${JSON.stringify(cfg)}\n`, "utf8");
console.log(`Wrote ${out} (unified installer, edition=${edition})`);

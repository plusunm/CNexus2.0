import type { NextConfig } from "next";

const isTauri = process.env.CNEXUS_TAURI === "1";
const isPersonalStatic =
  process.env.NEXT_PUBLIC_APP_MODE === "personal" ||
  process.env.CNEXUS_STATIC_EXPORT === "1" ||
  isTauri;

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: isPersonalStatic ? "export" : "standalone",
  trailingSlash: isPersonalStatic,
  images: { unoptimized: isPersonalStatic },
  env: {
    NEXT_PUBLIC_CNEXUS_RELEASE: process.env.CNEXUS_RELEASE ?? "",
    NEXT_PUBLIC_APP_MODE: process.env.NEXT_PUBLIC_APP_MODE ?? "personal",
    NEXT_PUBLIC_ENABLE_WS: process.env.NEXT_PUBLIC_ENABLE_WS ?? "false",
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE ?? "",
  },
};

export default nextConfig;

"""Mock systemCapability endpoint to trigger applyCapabilitySnapshot + markRuntimeReachabilityReady.
This is the probe fallback path that actually fires hydrateRuntimeData.
"""

import os

API = r"D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts"

with open(API, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    stripped = l.strip()
    if stripped.startswith("systemCapability") and "request" in stripped:
        v2_block = [
            '  systemCapability: async (): Promise<Record<string, unknown>> => {\n',
            "    try {\n",
            '      const resp = await fetch(getApiBase() + "/api/status");\n',
            "      if (resp.ok) {\n",
            "        const raw = await resp.json();\n",
            "        return {\n",
            '          reachable: true,\n',
            '          ready: true,\n',
            '          operational_ready: true,\n',
            '          boot_phase: "boot_4_ready",\n',
            '          progress: 100,\n',
            '          boot: {\n',
            '            phase: "boot_4_ready",\n',
            '            readiness: 1.0,\n',
            '            stage: "L0",\n',
            "          },\n",
            "        };\n",
            "      }\n",
            "    } catch {\n",
            "      /* fallback */\n",
            "    }\n",
            '    return request<Record<string, unknown>>("/v1/system/capability");\n',
            "  },\n",
        ]
        lines[i:i+1] = v2_block
        print(f"systemCapability mocked at line {i+1}")
        break

with open(API, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Done — systemCapability now returns mock boot_4_ready")

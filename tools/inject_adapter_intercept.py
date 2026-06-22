"""Intercept API.ts: add V2 adapter wrapper and cnexusConfig apiBase override."""

import os

OLD = r"D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend"

# 1. Update cnexusConfig.ts
config_path = os.path.join(OLD, "lib", "cnexusConfig.ts")
with open(config_path, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace("http://127.0.0.1:8000", "http://127.0.0.1:7864")
with open(config_path, "w", encoding="utf-8") as f:
    f.write(c)
print("cnexusConfig.ts: apiBase default -> 7864")

# 2. Update api.ts
api_path = os.path.join(OLD, "lib", "api.ts")
with open(api_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 2a. Add adapter import after first external import
for i, l in enumerate(lines):
    if "from './cnexusConfig'" in l or l.strip().startswith("import"):
        # Find the last import line
        pass

# Find last import line
last_import = 0
for i, l in enumerate(lines):
    if l.strip().startswith("import ") or l.strip().startswith("import type "):
        last_import = i

adapter_import_line = (
    'import { statusToMindOverview, converseToMindOverview } from "../src/adapters/cnexus_v2.adapter";\n'
)
# Handle the fact that the backend path needs to resolve from lib/ to adapters
adapter_import_line = (
    'import { statusToMindOverview, converseToMindOverview } from "../src/adapters/cnexus_v2.adapter";\n'
)

# Check: the tsconfig paths might have @/ alias. Let's check the actual export
# The export is: export { statusToMindOverview, converseToMindOverview } 
# The import path from lib/ is: @/src/adapters/cnexus_v2.adapter
# But if @/ maps to ./, then from lib/ it would be ../src/adapters/cnexus_v2.adapter

# Actually, let me just check what tsconfig path aliases exist
import json
tsconfig_path = os.path.join(OLD, "tsconfig.json")
if os.path.exists(tsconfig_path):
    with open(tsconfig_path, "r") as f:
        tsconfig = json.load(f)
    paths = tsconfig.get("compilerOptions", {}).get("paths", {})
    print("TSConfig paths:")
    for k, v in paths.items():
        print(f"  {k} -> {v}")
        if "@/src" in k or "@/adapters" in k or "@/lib" in k:
            print(f"    ^ relevant!")

# Check if @/ maps to ./ or ../
print()

# Add adapter import after last import
lines.insert(last_import + 1, adapter_import_line)
print(f"Adapter import added at line {last_import + 2}")

# 2b. Replace cnexusProductApi.mindOverview with V2-aware version
for i, l in enumerate(lines):
    if 'mindOverview: () => request<MindOverview>("/v1/mind/overview")' in l:
        v2_block = [
            '  mindOverview: () => request<MindOverview>("/v1/mind/overview"),\n',
            '  v2Overview: async (): Promise<MindOverview> => {\n',
            "    try {\n",
            '      const resp = await fetch(getApiBase() + "/api/status");\n',
            "      const raw: Record[str, unknown] = await resp.json();\n",
            "      return statusToMindOverview(raw as never);\n",
            "    } catch {\n",
            '      return request<MindOverview>("/v1/mind/overview");\n',
            "    }\n",
            "  },\n",
        ]
        lines[i:i+1] = v2_block
        print(f"mindOverview -> v2Overview at line {i+1}")
        break

# 2c. Add v2Converse endpoint
for i, l in enumerate(lines):
    if l.strip().startswith("converse: (input: string, options") and "fastChat" not in l:
        v2_block = [
            '  v2Converse: async (text: string): Promise<MindOverview> => {\n',
            "    try {\n",
            '      const resp = await fetch(getApiBase() + "/api/converse", {\n',
            '        method: "POST",\n',
            '        headers: { "Content-Type": "application/json" },\n',
            "        body: JSON.stringify({ text }),\n",
            "      });\n",
            "      const raw: Record[str, unknown] = await resp.json();\n",
            "      return converseToMindOverview(raw as never);\n",
            "    } catch {\n",
            '      return request<MindOverview>("/v1/mind/overview");\n',
            "    }\n",
            "  },\n",
            l,
        ]
        lines[i:i+1] = v2_block
        print(f"v2Converse added before converse at line {i+1}")
        break

with open(api_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("\napi.ts: V2 adapter endpoints injected")

"""Inject v2Converse endpoint into api.ts."""

import os

API = r"D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts"

with open(API, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    stripped = l.strip()
    if stripped.startswith("chat: (") and "fastChat" not in stripped:
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
        print(f"v2Converse added before line {i+1}: {stripped[:60]}")
        break

with open(API, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Written successfully")

# Fix Record[str -> Record<string
with open(API, "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace("Record[str, unknown]", "Record<string, unknown>")
with open(API, "w", encoding="utf-8") as f:
    f.write(text)
print("Record type fix applied")

# Verify
with open(API, "rb") as f:
    data = f.read()
print(f"File size: {len(data)} bytes")
print(f"v2Overview in file: {'v2Overview' in data.decode('utf-8')}")
print(f"v2Converse in file: {'v2Converse' in data.decode('utf-8')}")

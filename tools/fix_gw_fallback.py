"""Set gatewayHealth to force fallthrough to systemCapability for hydrate trigger."""
with open(r'D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace(
    'return {\n          gateway: "alive",\n          operational_ready: true,\n          full_ready: true,\n',
    'return {\n          gateway: "alive",\n          operational_ready: false,\n          full_ready: false,\n',
)
with open(r'D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts', 'w', encoding='utf-8') as f:
    f.write(c)
print("gatewayHealth operational_ready/full_ready -> false (forces cap fallback)")

with open(r'D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts','r',encoding='utf-8') as f:
    c = f.read()

import re

checks = {
    'adapter import': 'cnexus_v2.adapter' in c,
    'v2Overview': 'v2Overview' in c,
    'v2Converse': 'v2Converse' in c,
    'gw: alive + oper_ready=false': 'operational_ready: false' in c and 'gateway: "alive"' in c,
    'syscap: boot_4_ready': 'boot_4_ready' in c,
    'no Record[str, unk]': 'Record[str, unknown]' not in c,
    'Record<string, unk]': 'Record<string, unknown>' in c,
    'orig gwHealth removed': not re.search(r'gatewayHealth: \(\) =>', c),
    'orig syscap removed': 'systemCapability: () =>' not in c,
}
for k,v in checks.items():
    print(f'  {k}: {"OK" if v else "MISSING"}')
print(f'\nFile size: {len(c.encode())} bytes')

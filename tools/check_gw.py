with open(r'D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts','r',encoding='utf-8') as f:
    lines = f.readlines()
for i,l in enumerate(lines):
    if 'operational_ready' in l:
        s = l.strip()[:80]
        print(f'L{i+1}: |{s}|')
    if 'gateway' in l and 'alive' in l:
        s = l.strip()[:80]
        print(f'L{i+1}: |{s}|')

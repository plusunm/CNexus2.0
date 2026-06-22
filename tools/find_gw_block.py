with open(r'D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts','r',encoding='utf-8') as f:
    lines = f.readlines()
for i,l in enumerate(lines):
    if 'Mock enterprise gateway' in l:
        # Print surrounding 20 lines
        for j in range(i, min(i+20, len(lines))):
            print(f'{j+1}: |{lines[j].rstrip()[:100]}|')
        break

with open(r'D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts','r',encoding='utf-8') as f:
    c = f.read()
# Remove line with operational_ready: true from gatewayHealth block
c2 = c.replace(
    'operational_ready: true,',
    'operational_ready: false,',
)
c2 = c2.replace(
    'full_ready: true,',
    'full_ready: false,',
)
with open(r'D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts','w',encoding='utf-8') as f:
    f.write(c2)
print('Replaced operational_ready: true -> false and full_ready -> false')
print('Changes:', 'operational_ready: false' in c2, 'full_ready: false' in c2)

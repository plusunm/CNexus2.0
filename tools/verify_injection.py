c = open(r'D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend\lib\api.ts','r',encoding='utf-8').read()
checks = {
  'adapter import': 'cnexus_v2.adapter' in c,
  'v2Overview': 'v2Overview' in c,
  'v2Converse': 'v2Converse' in c,
  'gw alive': 'gateway' in c and 'alive' in c,
  'gw oper_ready=false': 'operational_ready: false' in c,
  'syscap boot_4_ready': 'boot_4_ready' in c,
  'no Record[str': 'Record[str, unknown]' not in c,
  'Record<string': 'Record<string, unknown>' in c,
}
for k,v in checks.items():
  st = 'OK' if v else 'MISSING'
  print(f'  {k}: {st}')

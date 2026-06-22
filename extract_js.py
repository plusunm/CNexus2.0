#!/usr/bin/env python3
"""Extract JS logic from current app_ui.py"""
with open("D:/类脑记忆/CNexus2.0/app_ui.py", "r", encoding="utf-8") as f:
    full = f.read()

shell_start_marker = "SHELL_HTML = r'''"
shell_start = full.find(shell_start_marker)
shell_content_start = shell_start + len(shell_start_marker)
shell_end_marker = "'''"
# Find end of SHELL_HTML - the closing ''' before FLOAT_HTML
idx_float_marker = full.find("FLOAT_HTML = r'''")
shell_content_end = full.rfind(shell_end_marker, shell_content_start, idx_float_marker)
if shell_content_end > 0:
    shell_content_end += 3  # include the '''

shell_content = full[shell_content_start:shell_content_end-3]

# Find JS
js_start = shell_content.find("<script>")
js_content_start = js_start + len("<script>")
js_end = shell_content.find("</script>", js_content_start)
js_content = shell_content[js_content_start:js_end]

# Verify functions
for fn in ['pollStatus', 'switchView', 'drawFlowGraph', 'gvBuildGraphViewModel',
           'gvFilterNodes', 'gvGroupColor', 'gvInitControls', 'gvSetSlider',
           'gvToggle', 'gvSetSearch', 'refreshAll', 'gvSliderRow']:
    if fn in js_content:
        print(f"  OK {fn}")
    else:
        print(f"  MISSING {fn}")

print(f"\nJS content length: {len(js_content)}")

# Also save JS to file for inspection
with open("D:/类脑记忆/CNexus2.0/current_js.txt", "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"JS saved to current_js.txt")

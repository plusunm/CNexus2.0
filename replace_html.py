#!/usr/bin/env python3
"""Replace SHELL_HTML and FLOAT_HTML in app_ui.py with content from HTML files."""

import sys

# Read the current app_ui.py
with open("D:/类脑记忆/CNexus2.0/app_ui.py", "r", encoding="utf-8") as f:
    full = f.read()

# Find the JS logic from old SHELL_HTML
shell_start_marker = "SHELL_HTML = r'''"
shell_start = full.find(shell_start_marker)
shell_content_start = shell_start + len(shell_start_marker)
idx_float_marker = full.find("FLOAT_HTML = r'''")
shell_content_end = full.rfind("'''", shell_content_start, idx_float_marker)
old_shell = full[shell_content_start:shell_content_end-3]

js_start = old_shell.find("<script>")
js_content_start = js_start + len("<script>")
js_end = old_shell.find("</script>", js_content_start)
js_logic = old_shell[js_content_start:js_end]

print(f"JS logic: {len(js_logic)} chars")

# Read new shell.html
with open("D:/类脑记忆/CNexus2.0/new_shell.html", "r", encoding="utf-8") as f:
    shell_template = f.read()

# Read new float.html
with open("D:/类脑记忆/CNexus2.0/new_float.html", "r", encoding="utf-8") as f:
    float_template = f.read()

# Replace placeholder
# Add extra window assignments for new HTML onclick bindings
js_extras = """
// Extra window assignments for new shell HTML
window.gvToggle=gvToggle;window.gvSetSlider=gvSetSlider;
window.gvSetSearch=gvSetSearch;window.refreshAll=refreshAll;"""

# Insert the extra assignments before the existing window assignments
js_mod = js_logic.replace(
    "window.pollStatus=pollStatus;window.switchView=switchView;",
    "window.pollStatus=pollStatus;window.switchView=switchView;" + js_extras
)

new_shell = shell_template.replace("/* JS_LOGIC */", js_mod)

# Build the new file
# Everything before SHELL_HTML stays
before_shell = full[:shell_start]
# Everything after SHELL_HTML closing and before FLOAT_HTML stays
after_shell_to_float = full[shell_content_end:idx_float_marker]
# Everything after FLOAT_HTML closing stays
idx_float_start = idx_float_marker + len("FLOAT_HTML = r'''")
float_content_end = full.find("'''", idx_float_start)
after_float = full[float_content_end+3:]

new_file = before_shell + "SHELL_HTML = r'''\n" + new_shell + "\n'''" + "\n\n\n# === FLOAT ===\nFLOAT_HTML = r'''\n" + float_template + "\n'''" + after_float

# Verify
before_len = len(before_shell)
after_shell_len = len(after_shell_to_float)
after_float_len = len(after_float)

# Check original structure
print(f"Before SHELL_HTML: {before_len} bytes")
print(f"SHELL to FLOAT gap: {after_shell_len} bytes")
print(f"After FLOAT_HTML: {after_float_len} bytes")
print(f"Old total: {len(full)} bytes")
print(f"New total: {len(new_file)} bytes")

# Verify SHELL_HTML and FLOAT_HTML are still valid Python strings
# Check that there are no r''' or ''' in the middle that would break
new_shell_start = new_file.find("SHELL_HTML = r'''")
new_shell_content_start = new_shell_start + len("SHELL_HTML = r'''")
# Find the closing '''
new_shell_end_marker = "\n'''"
new_shell_end = new_file.find(new_shell_end_marker, new_shell_content_start)
if new_shell_end < 0:
    print("ERROR: Could not find closing ''' for SHELL_HTML!")
    sys.exit(1)

new_float_start = new_file.find("FLOAT_HTML = r'''")
new_float_content_start = new_float_start + len("FLOAT_HTML = r'''")
new_float_end = new_file.find(new_shell_end_marker, new_float_content_start)
if new_float_end < 0:
    print("ERROR: Could not find closing ''' for FLOAT_HTML!")
    sys.exit(1)

print(f"New SHELL_HTML: {new_shell_end - new_shell_content_start} chars")
print(f"New FLOAT_HTML: {new_float_end - new_float_content_start} chars")

# Write the new file
output_path = "D:/类脑记忆/CNexus2.0/app_ui_new.py"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(new_file)

print(f"\nWritten to {output_path}")
print("Ready for syntax check!")

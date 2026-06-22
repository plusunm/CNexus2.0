#!/usr/bin/env python3
"""Build new SHELL_HTML and FLOAT_HTML from raw enterprise HTML + existing JS."""

import re

# Read original app_ui.py to extract JS logic
with open("D:/类脑记忆/CNexus2.0/app_ui.py", "r", encoding="utf-8") as f:
    full = f.read()

# Split at SHELL_HTML boundary
idx_shell_start = full.find("SHELL_HTML = r'''")
idx_shell_end = full.find("'''", idx_shell_start + 16)
idx_float_start = full.find("FLOAT_HTML = r'''")
idx_float_end = full.find("'''", idx_float_start + 16)

shell_before = full[:idx_shell_start]
shell_after = full[idx_shell_end+3:]
float_html_old = full[idx_float_start+16:idx_float_end]

print(f"Shell HTML length: {idx_shell_end - idx_shell_start}")
print(f"Float HTML length: {idx_float_end - idx_float_start}")
print(f"JS logic starts at about line 434 of file (in shell)")

# Extract the JS from old SHELL_HTML
old_shell = full[idx_shell_start+16:idx_shell_end]  # the r''' content

# Find the <script> block
script_start = old_shell.find("<script>")
script_text = old_shell[script_start + len("<script>"):]
script_end = script_text.find("</script>")
js_logic = script_text[:script_end]

print(f"JS logic length: {len(js_logic)}")
print("JS logic extracted OK")

import os
import re
import subprocess

# 1. Get modified files
result = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True)
modified_files = [f for f in result.stdout.split('\n') if f]

css_classes = set()
try:
    with open('static/css/design-system.css', 'r', encoding='utf-8') as f:
        css_content = f.read()
        # Find all class selectors
        classes_raw = re.findall(r'\.([a-zA-Z0-9_-]+)', css_content)
        # Only take those that actually seem to be selectors (followed by { or pseudo-classes or comma)
        css_classes = set(classes_raw)
        
        # Duplicates finding: very simple counting of blocks
        blocks = re.findall(r'\.([a-zA-Z0-9_-]+)[^{]*\{', css_content)
        css_duplicates = set([x for x in blocks if blocks.count(x) > 1])
except Exception as e:
    print("CSS Error:", e)
    css_duplicates = []

html_files = [f for f in modified_files if f.endswith('.html')]

# Bootstrap / standard classes we can ignore for now
ignore_classes = {'flex', 'hidden', 'text-white', 'bg-blue-500'}

missing_classes_per_file = {}
for hf in html_files:
    if os.path.exists(hf):
        with open(hf, 'r', encoding='utf-8') as f:
            content = f.read()
        classes = re.findall(r'class="([^"]+)"', content)
        all_classes_in_file = set()
        for c in classes:
            all_classes_in_file.update(c.split())
        
        # Check static tags
        static_tags = re.findall(r'\{%\s*static\s+[\'"]([^\'"]+)[\'"]\s*%\}', content)
        for st in static_tags:
            if not os.path.exists(st.lstrip('/')):
                 pass # Could check if static file exists, skipping for now
        
        missing = all_classes_in_file - css_classes - ignore_classes
        if missing:
            missing_classes_per_file[hf] = missing

all_funcs = []
try:
    with open('static/js/app-shell.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
    js_funcs = re.findall(r'function\s+([a-zA-Z0-9_-]+)', js_content)
    js_arrow_funcs = re.findall(r'(const|let|var)\s+([a-zA-Z0-9_-]+)\s*=\s*(async\s+)?\([^)]*\)\s*=>', js_content)
    all_funcs = [f for f in js_funcs] + [f[1] for f in js_arrow_funcs]
    js_duplicates = set([x for x in all_funcs if all_funcs.count(x) > 1])
except Exception as e:
    print("JS Error:", e)
    js_duplicates = []

missing_js_funcs = {}
for hf in html_files:
    if os.path.exists(hf):
        with open(hf, 'r', encoding='utf-8') as f:
            content = f.read()
        handlers = re.findall(r'on[a-z]+="([a-zA-Z0-9_-]+)\(', content)
        for h in handlers:
            if h not in all_funcs:
                if hf not in missing_js_funcs:
                    missing_js_funcs[hf] = set()
                missing_js_funcs[hf].add(h)

print("--- Backend changes ---")
print([f for f in modified_files if f.endswith('.py')])

print("\n--- CSS Duplicates ---")
print(list(css_duplicates)[:50])

print("\n--- JS Duplicates ---")
print(list(js_duplicates))

print("\n--- Missing CSS Classes (sample limit 10) ---")
c = 0
for f, classes in missing_classes_per_file.items():
    print(f, list(classes)[:10]) # print up to 10 missing classes per file
    c += 1

print("\n--- Missing JS Handlers in templates ---")
for f, funcs in missing_js_funcs.items():
    print(f, funcs)

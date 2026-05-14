import re

file_path = r"C:\Users\angit\OneDrive\Desktop\copy\Jan Aushathi\pharmacy_management\templates\pharmacy\order_tracking.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Simplified parser to track stack
stack = []
# Match any tag
tags = re.findall(r'{%\s*(if|else|elif|endif|for|endfor|block|endblock|with|endwith)\b.*?%}', content)

errors = []
for tag in tags:
    if tag == 'if':
        stack.append('if')
    elif tag == 'for':
        stack.append('for')
    elif tag == 'block':
        stack.append('block')
    elif tag == 'with':
        stack.append('with')
    elif tag == 'endif':
        if not stack or stack[-1] != 'if':
            errors.append(f"Unexpected endif, stack: {stack}")
        else:
            stack.pop()
    elif tag == 'endfor':
        if not stack or stack[-1] != 'for':
            errors.append(f"Unexpected endfor, stack: {stack}")
        else:
            stack.pop()
    elif tag == 'endblock':
        if not stack or stack[-1] != 'block':
            errors.append(f"Unexpected endblock, stack: {stack}")
        else:
            stack.pop()
    elif tag == 'endwith':
        if not stack or stack[-1] != 'with':
            errors.append(f"Unexpected endwith, stack: {stack}")
        else:
            stack.pop()

if stack:
    print(f"Unclosed tags in stack: {stack}")
if errors:
    print(f"Errors found: {errors}")
if not stack and not errors:
    print("All tags are perfectly balanced.")

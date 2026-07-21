with open("agent/policy.py", "r") as f:
    content = f.read()

content = content.replace('err_log.write(f"--- [SHALLOW SEARCH ERROR] ---\n")\n', 'err_log.write("--- [SHALLOW SEARCH ERROR] ---\\n")\n')
content = content.replace('err_log.write("\n")\n', 'err_log.write("\\n")\n')

with open("agent/policy.py", "w") as f:
    f.write(content)

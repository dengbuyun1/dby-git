import re

p = r"f:\\1_YX\\BSSS\\qhjjjjjjj\\ddd\\src\\views\\VPatientsMonitor.vue"
with open(p, encoding="utf-8") as f:
    s = f.read()
opens = []
unmatched = []
for m in re.finditer(r"<(/?)div(\b[^>]*)?>", s, re.IGNORECASE):
    kind = "close" if m.group(1) == "/" else "open"
    pos = m.start()
    line = s.count("\n", 0, pos) + 1
    if kind == "open":
        opens.append((line, pos))
    else:
        if opens:
            opens.pop()
        else:
            unmatched.append(("extra_close", line))
print("remaining opens:", len(opens))
for o in opens:
    print("unclosed <div> at line", o[0])
for u in unmatched:
    print("extra close at line", u[1])
print("\nQuick context around first unclosed/open (if any):")
if opens:
    ln = opens[0][0]
    with open(p, encoding="utf-8") as f:
        lines = f.readlines()
    start = max(0, ln - 5)
    end = min(len(lines), ln + 5)
    for i in range(start, end):
        print(f"{i+1}: {lines[i].rstrip()}")
elif unmatched:
    ln = unmatched[0][1]
    with open(p, encoding="utf-8") as f:
        lines = f.readlines()
    start = max(0, ln - 5)
    end = min(len(lines), ln + 5)
    for i in range(start, end):
        print(f"{i+1}: {lines[i].rstrip()}")
else:
    print("All matched (according to naive scanner)")

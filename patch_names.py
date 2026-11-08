# patch_names.py  -- run from the repo root
path = "backend/app/privacy/detectors/contextual.py"

with open(path, "r", encoding="utf-8") as f:
    data = f.read()

STOP = (
    "and|or|but|i|am|is|my|me|to|the|a|an|at|in|on|for|from|with|can|could|"
    "would|need|want|wants|wanted|wish|wishes|phone|email|mail|number|who|"
    "which|that|please|write|give|send|live|work|moved"
)

old = r"(?:\s+[A-Z][A-Za-z'-]{1,})"
new = r"(?:\s+(?!(?:" + STOP + r")\b)[A-Z][A-Za-z'-]*)"

count = data.count(old)
if count == 0:
    raise SystemExit("Pattern not found. File may already be patched.")

data = data.replace(old, new)

with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(data)

print(f"patched {count} patterns")
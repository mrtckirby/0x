"""Verify the documented test vector and category mapping."""
import base64
import json
import re
import sys
import textwrap
import types
import zlib
from pathlib import Path

root = Path(__file__).resolve().parent.parent
spec = (root / "EXPORT_FORMAT.md").read_text(encoding="utf-8")
payload = json.loads(re.search(r"```json\n(.*?)\n```", spec, re.S).group(1))
encoded = re.search(r"```text\n(0X1\.[^\n]+)\n```", spec).group(1)[4:]
decoded = zlib.decompress(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
assert json.loads(decoded.decode("utf-8")) == payload

source = (root / "index.html").read_text(encoding="utf-8")
code = re.search(r'<script type="py">(.*?)</script>', source, re.S).group(1)
code = code.split("# EVENT LISTENERS & INITIALIZATION")[0].rsplit("# ====", 1)[0]
pyscript = types.ModuleType("pyscript")
pyscript.document = pyscript.window = object()
pyodide = types.ModuleType("pyodide")
ffi = types.ModuleType("pyodide.ffi")
ffi.create_once_callable = ffi.create_proxy = lambda f: f
sys.modules.update({"pyscript": pyscript, "pyodide": pyodide, "pyodide.ffi": ffi})
ns = {}
exec(textwrap.dedent(code), ns)

mapping = {}
for line in spec.splitlines():
    if line.startswith("| `") and " | `" in line:
        category, ids = line.strip("| ").split(" | ")
        category = category.strip("`")
        if category in ns["MASTER_CATEGORIES"]:
            mapping.update({key: category for key in re.findall(r"`([^`]+)`", ids)})
assert mapping == {key: config["master"] for key, config in ns["QUESTION_CONFIG"].items()}
totals = [sum(count for key, count in payload["s"].items() if mapping[key] == category)
          for category in ns["MASTER_CATEGORIES"]]
assert totals == [9, 3, 0, 0, 0] and sum(totals) / len(totals) == 2.4
print("ok")

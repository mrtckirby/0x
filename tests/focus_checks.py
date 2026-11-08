"""Check focused question selection without a browser or PyScript download."""
import re
import sys
import textwrap
import types
from pathlib import Path

source = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
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

state = ns["state"]
config = ns["QUESTION_CONFIG"]
choices_seen = []


def record_pick(choices, weights):
    choices_seen.append(list(choices))
    return choices[0]


ns["weighted_pick"] = record_pick
for advanced in (False, True):
    state.advanced_mode = advanced
    for category in ns["MASTER_CATEGORIES"]:
        state.focus_category = category
        eligible = {key for key, value in config.items()
                    if value["master"] == category and (advanced or not value["advanced"])}
        choices_seen.clear()
        ns["choose_weighted_question_type"]()
        assert choices_seen[0] == [category]
        assert set(choices_seen[1]) == eligible

state.focus_category = None
choices_seen.clear()
ns["choose_weighted_question_type"]()
assert set(choices_seen[0]) == set(ns["MASTER_CATEGORIES"])
print("ok")

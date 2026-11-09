"""Check badge thresholds against the application's real question mapping."""
import re
import sys
import textwrap
import types
from pathlib import Path

source = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
code = re.search(r'<script type="py">(.*?)</script>', source, re.S).group(1)
code = code.split("# Wire up buttons and toggles")[0]
pyscript = types.ModuleType("pyscript")
pyscript.document = pyscript.window = object()
pyodide = types.ModuleType("pyodide")
ffi = types.ModuleType("pyodide.ffi")
ffi.create_once_callable = ffi.create_proxy = lambda f: f
sys.modules.update({"pyscript": pyscript, "pyodide": pyodide, "pyodide.ffi": ffi})
ns = {}
exec(textwrap.dedent(code), ns)
state = ns["state"]
progress = ns["badge_progress"]

state.daily_usage_ms = {"2026-01-01": 599_999}
state.all_time_scores = {"base_conversion": 2}
assert not progress()["ada"]["earned"]
state.daily_usage_ms["2026-01-01"] += 1
assert progress()["ada"]["earned"]
state.all_time_scores = {"base_conversion": 1}
assert not progress()["ada"]["earned"]

state.daily_usage_ms = {f"2026-01-{day:02d}": 300_000 for day in range(1, 31)}
state.daily_usage_ms["2026-02-01"] = 299_999
state.all_time_scores = {"base_conversion": 49}
assert progress()["hopper"]["earned"] and progress()["hamilton"]["earned"]
assert not progress()["knuth"]["earned"]
state.all_time_scores["base_conversion"] = 50
assert progress()["knuth"]["earned"]
state.daily_usage_ms["2026-01-30"] = 299_999
assert not progress()["knuth"]["earned"]

state.daily_usage_ms = {}
state.all_time_scores = {
    "base_conversion": 10, "binary_addition": 10, "unit_conversion": 10,
    "operators_div_mod": 10, "bitwise_operators": 9, "unrecognised": 1000,
}
assert not progress()["jones"]["earned"]
assert not progress()["dijkstra"]["earned"]
state.all_time_scores["bitwise_operators"] = 10
assert progress()["jones"]["earned"]
state.all_time_scores["binary_addition"] = 15
assert progress()["shannon"]["earned"]
state.all_time_scores["number_of_values"] = 15
assert progress()["johnson"]["earned"]
state.all_time_scores["operators_div_mod"] = 25
assert progress()["boole"]["earned"]
state.all_time_scores["unit_conversion"] = 25
assert progress()["dijkstra"]["earned"]
assert progress()["turing"]["earned"]
print("ok")

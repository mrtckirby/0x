"""Verify backup validation and persistence failure behavior without a browser."""
import json
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
state.firstname = "Ada"
state.lastname = "Lovelace"
state.all_time_scores = {"base_conversion": 5}
state.daily_scores = {"base_conversion": 1}
state.daily_usage_ms = {"2026-01-01": 1234}
state.usage_tracking_since = "2026-01-01"
data = json.loads(json.dumps(ns["state_data"]()))
assert ns["validate_backup"](data) == data

for patch in (
    {"firstname": ""}, {"advanced_mode": "yes"}, {"daily_scores": {"base_conversion": 6}},
    {"all_time_scores": {"base_conversion": True}}, {"daily_usage_ms": {"2026-02-30": 1}},
    {"usage_tracking_since": None}, {"focus_category": "bad"},
    {"focus_category": "operators", "focus_question_type": "binary_shift"},
    {"daily_usage_ms": []},
):
    bad = dict(data, **patch)
    try:
        ns["validate_backup"](bad)
        raise AssertionError(f"accepted invalid backup {patch!r}")
    except ValueError:
        pass
assert state.firstname == "Ada" and state.all_time_scores == {"base_conversion": 5}


class Classes:
    def remove(self, name):
        pass


elements = {key: types.SimpleNamespace(textContent="", classList=Classes())
            for key in ("storage-warning", "initial-backup-status")}
elements.update({
    "toggle-advanced-profile": types.SimpleNamespace(checked=False),
    "toggle-advanced-modal": types.SimpleNamespace(checked=False),
})
ns["document"] = types.SimpleNamespace(getElementById=lambda name: elements[name])


class Blocked:
    def getItem(self, key):
        raise RuntimeError("blocked")

    def setItem(self, key, value):
        raise RuntimeError("blocked")


ns["window"] = types.SimpleNamespace(localStorage=Blocked())
assert not ns["save_state"]()
assert "unavailable" in elements["storage-warning"].textContent
assert not ns["load_state"]()
assert state.firstname == "Ada"
print("ok")

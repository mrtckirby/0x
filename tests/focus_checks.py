"""Check focused question selection without a browser or PyScript download."""
import json
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


class Storage:
    def __init__(self, data):
        self.data = json.dumps(data)

    def getItem(self, key):
        return self.data

    def setItem(self, key, value):
        self.data = value


class Date:
    def new(self):
        return self

    def toDateString(self):
        return "today"


class Document:
    def __init__(self):
        self.elements = {
            "toggle-advanced-top": types.SimpleNamespace(checked=False),
            "toggle-advanced-modal": types.SimpleNamespace(checked=False),
        }

    def getElementById(self, key):
        return self.elements[key]


def load_saved(data):
    storage = Storage(data)
    ns["window"] = types.SimpleNamespace(localStorage=storage, Date=Date())
    ns["document"] = Document()
    assert ns["load_state"]()
    return storage


assert config["number_of_values"]["master"] == "base_conversion"
assert "number_of_values" not in ns["MASTER_CATEGORIES"]
state.focus_category = None
saved = {
    "firstname": "Ada", "lastname": "Lovelace", "advanced_mode": False,
    "focus_category": "number_of_values", "last_active_date": "today",
    "daily_scores": {"base_conversion": 2, "number_of_values": 4},
    "all_time_scores": {"base_conversion": 7, "number_of_values": 6},
}
storage = load_saved(saved)
assert state.focus_category == "base_conversion"
assert state.daily_scores == saved["daily_scores"]
assert state.all_time_scores == saved["all_time_scores"]
assert json.loads(storage.data)["focus_category"] == "base_conversion"
assert ns["load_state"]()
assert state.daily_scores == saved["daily_scores"]
assert state.all_time_scores == saved["all_time_scores"]

legacy = {
    "firstname": "Ada", "lastname": "Lovelace",
    "questions": [
        {"q_type": "a", "awarded": "today"},
        {"q_type": "d", "awarded": "today"},
        {"q_type": "d", "awarded": "yesterday"},
    ],
}
storage = load_saved(legacy)
assert state.daily_scores == {"base_conversion": 1, "number_of_values": 1}
assert state.all_time_scores == {"base_conversion": 1, "number_of_values": 2}
assert ns["load_state"]()
assert state.daily_scores == {"base_conversion": 1, "number_of_values": 1}
assert state.all_time_scores == {"base_conversion": 1, "number_of_values": 2}

saved["last_active_date"] = "yesterday"
load_saved(saved)
assert state.daily_scores == {}
assert state.all_time_scores == saved["all_time_scores"]
print("ok")

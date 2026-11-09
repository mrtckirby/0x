"""Check focused question selection without a browser or PyScript download."""
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

for q_type, item in config.items():
    state.advanced_mode = item["advanced"]
    state.focus_category = item["master"]
    state.focus_question_type = q_type
    choices_seen.clear()
    assert ns["choose_weighted_question_type"]() == q_type
    assert choices_seen == [[item["master"]], [q_type]]
    for _ in range(10):
        assert item["generator"]().question_type == q_type
state.focus_question_type = None


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


class Element:
    def __init__(self):
        self.children = []
        self.attributes = {}
        self.textContent = ""
        self.type = ""

    def replaceChildren(self):
        self.children.clear()

    def appendChild(self, child):
        self.children.append(child)

    def setAttribute(self, name, value):
        self.attributes[name] = value


class Document:
    def __init__(self):
        self.elements = {
            "toggle-advanced-profile": types.SimpleNamespace(checked=False),
            "toggle-advanced-modal": types.SimpleNamespace(checked=False),
            "focus-menu": Element(),
        }

    def getElementById(self, key):
        return self.elements[key]

    def createElement(self, name):
        return Element()


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

focused = dict(saved, focus_category="binary_arithmetic", focus_question_type="binary_shift")
storage = load_saved(focused)
assert state.focus_category == "binary_arithmetic"
assert state.focus_question_type == "binary_shift"
assert json.loads(storage.data)["focus_question_type"] == "binary_shift"
assert ns["load_state"]() and state.focus_question_type == "binary_shift"

advanced = dict(focused, focus_question_type="binary_subtraction", advanced_mode=True)
load_saved(advanced)
assert state.focus_question_type == "binary_subtraction"
advanced["advanced_mode"] = False
load_saved(advanced)
assert state.focus_category == "binary_arithmetic" and state.focus_question_type is None
load_saved(dict(focused, focus_question_type="not_a_type"))
assert state.focus_question_type is None
load_saved(dict(focused, focus_question_type="number_of_values"))
assert state.focus_question_type is None

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

events = []
ns["replace_questions"] = lambda: events.append("replace")
ns["refresh_dashboard"] = lambda: events.append("refresh")
ns["render_scorecard"] = lambda: events.append("render")
ns["save_state"] = lambda: events.append("save")
ns["close_menus"] = lambda: events.append("close")


class Button:
    def __init__(self, value):
        self.value = value

    def getAttribute(self, name):
        return self.value

    def closest(self, selector):
        return self


state.advanced_mode = False
state.focus_category = None
state.focus_question_type = None
ns["handle_scorecard_focus"](types.SimpleNamespace(target=Button("binary_shift")))
assert (state.focus_category, state.focus_question_type) == ("binary_arithmetic", "binary_shift")
assert events == ["close", "replace", "refresh", "save"]
events.clear()
ns["handle_scorecard_focus"](types.SimpleNamespace(target=Button("binary_shift")))
assert (state.focus_category, state.focus_question_type) == (None, None)
assert events == ["close", "replace", "refresh", "save"]
events.clear()
ns["handle_scorecard_focus"](types.SimpleNamespace(target=Button("binary_shift")))
ns["handle_focus"](types.SimpleNamespace(target=Button("base_conversion")))
assert (state.focus_category, state.focus_question_type) == ("base_conversion", None)
events.clear()
ns["toggle_menu"](types.SimpleNamespace(currentTarget=types.SimpleNamespace(id="focus-button")))
assert (state.focus_category, state.focus_question_type) == (None, None)
assert events == ["close", "replace", "refresh", "save"]
state.focus_category = "binary_arithmetic"
state.focus_question_type = "binary_subtraction"
state.advanced_mode = True
events.clear()
ns["set_advanced"](False)
assert (state.focus_category, state.focus_question_type) == ("binary_arithmetic", None)
assert events == ["replace", "refresh", "render"]
assert ns["document"].elements["toggle-advanced-profile"].checked is False
assert ns["document"].elements["toggle-advanced-modal"].checked is False
print("ok")

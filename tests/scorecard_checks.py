"""Exercise scorecard rendering without a browser or PyScript download."""
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


class Element:
    def __init__(self, tag):
        self.tag = tag
        self.children = []
        self.attributes = {}
        self.textContent = ""
        self.className = ""

    def appendChild(self, child):
        self.children.append(child)

    def replaceChildren(self):
        self.children.clear()

    def setAttribute(self, key, value):
        self.attributes[key] = value


class Document:
    def __init__(self):
        self.elements = {name: Element("div") for name in ("scorecard-title", "scorecard-scores")}

    def getElementById(self, name):
        return self.elements[name]

    def createElement(self, tag):
        return Element(tag)


class Date:
    def new(self):
        return self

    def toDateString(self):
        return "today"


doc = Document()
ns["document"] = doc
ns["window"] = types.SimpleNamespace(Date=Date())
state = ns["state"]
state.last_active_date = "today"
state.daily_scores = {"base_conversion": 2, "number_of_values": 4, "twos_comp_bin_to_den": 1, "binary_addition": 3}
state.all_time_scores = {"base_conversion": 7, "number_of_values": 6, "twos_comp_bin_to_den": 4, "binary_addition": 8}


def rows(category):
    ns["scorecard_category"] = category
    ns["render_scorecard"]()
    table = doc.elements["scorecard-scores"].children[-1]
    return table.children[1].children


for advanced_mode in (False, True):
    state.advanced_mode = advanced_mode
    for category in ns["MASTER_CATEGORIES"]:
        category_rows = rows(category)
        expected = {key for key, config in ns["QUESTION_CONFIG"].items()
                    if config["master"] == category and (advanced_mode or not config["advanced"])}
        actual = [row.attributes["data-question-type"] for row in category_rows]
        assert set(actual) == expected
        advanced_flags = [ns["QUESTION_CONFIG"][key]["advanced"] for key in actual]
        assert advanced_flags == sorted(advanced_flags)

    all_rows = rows("average")
    for index, row in enumerate(all_rows):
        if row.className != "category-heading":
            continue
        category = row.attributes["data-cat"]
        end = next((i for i in range(index + 1, len(all_rows))
                    if all_rows[i].className == "category-heading"), len(all_rows))
        actual = [r.attributes["data-question-type"] for r in all_rows[index + 1:end]]
        expected = {key for key, config in ns["QUESTION_CONFIG"].items()
                    if config["master"] == category and (advanced_mode or not config["advanced"])}
        assert set(actual) == expected
        advanced_flags = [ns["QUESTION_CONFIG"][key]["advanced"] for key in actual]
        assert advanced_flags == sorted(advanced_flags)

headings = [row for row in all_rows if row.className == "category-heading"]
assert len(headings) == len(ns["MASTER_CATEGORIES"])
assert [cell.textContent for cell in headings[0].children] == ["Base conversion", "7", "17"]
assert [cell.textContent for cell in headings[1].children] == ["Binary arithmetic", "3", "8"]
assert len([row for row in all_rows if "data-question-type" in row.attributes]) == len(ns["QUESTION_CONFIG"])
state.last_active_date = "yesterday"
assert [cell.textContent for cell in rows("average")[0].children] == ["Base conversion", "0", "17"]
state.advanced_mode = False
rows("average")
assert "include advanced scores" in doc.elements["scorecard-scores"].children[0].textContent
print("ok")

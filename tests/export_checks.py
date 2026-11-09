"""Exercise the actual PyScript exporter without a browser download."""
import asyncio
import base64
import json
import random
import re
import string
import sys
import textwrap
import types
import zlib
from datetime import date, datetime, timedelta, timezone
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


class DateValue:
    def __init__(self, value):
        self.value = datetime.fromtimestamp(value / 1000, timezone.utc)

    def getFullYear(self):
        return self.value.year

    def getMonth(self):
        return self.value.month - 1

    def getDate(self):
        return self.value.day

    def toDateString(self):
        return self.value.strftime("%Y-%m-%d")

    def toISOString(self):
        return self.value.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def setHours(self, hours, minutes, seconds, milliseconds):
        self.value = (self.value + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    def getTime(self):
        return int(self.value.timestamp() * 1000)


class Clock:
    time = int(datetime(2026, 11, 8, 20, tzinfo=timezone.utc).timestamp() * 1000)

    def now(self):
        return self.time

    def new(self, value=None):
        return DateValue(self.time if value is None else value)


class Classes:
    def __init__(self):
        self.hidden = True

    def add(self, name):
        if name == "hidden":
            self.hidden = True

    def remove(self, name):
        if name == "hidden":
            self.hidden = False


class Attributes:
    def __init__(self):
        self.values = {}

    def setAttribute(self, name, value):
        self.values[name] = value


class Clipboard:
    def __init__(self):
        self.value = None
        self.fail = False

    async def writeText(self, value):
        if self.fail:
            raise RuntimeError("permission denied")
        self.value = value


clock = Clock()
clipboard = Clipboard()
elements = {key: types.SimpleNamespace(classList=Classes(), value="", textContent="")
            for key in ("export-result", "export-status", "export-text-label", "export-text")}
elements.update({
    "focus-menu": types.SimpleNamespace(classList=Classes()),
    "profile-menu": types.SimpleNamespace(classList=Classes()),
    "focus-button": Attributes(),
    "profile-button": Attributes(),
})
success = []
elements["copy-success-modal"] = types.SimpleNamespace(showModal=lambda: success.append(True))
elements["settings-modal"] = types.SimpleNamespace(close=lambda: success.append("closed"))
ns["window"] = types.SimpleNamespace(
    Date=clock, navigator=types.SimpleNamespace(clipboard=clipboard),
    localStorage=types.SimpleNamespace(setItem=lambda key, value: None),
)
ns["document"] = types.SimpleNamespace(hidden=False, getElementById=lambda name: elements[name])
def close_menus():
    for name in ("focus", "profile"):
        elements[name + "-menu"].classList.add("hidden")
        elements[name + "-button"].setAttribute("aria-expanded", "false")

ns["close_menus"] = close_menus
state = ns["state"]
state.firstname = "Áda"
state.lastname = "Lovelace"
state.all_time_scores = {"base_conversion": 9, "future_type": 2}
state.daily_scores = {"base_conversion": 1}
state.last_active_date = "2026-11-08"
state.usage_tracking_since = "2026-01-01"
dates = [(date(2026, 1, 1) + timedelta(days=i * 2)).isoformat() for i in range(101)]
state.daily_usage_ms = {day: 30000 for day in dates}
state.daily_usage_ms[dates[-1]] = 29999
ns["usage_cursor"] = clock.time
ns["last_interaction"] = clock.time
clock.time += 45000

def decode(value):
    assert value.startswith("0X1.")
    encoded = value[4:]
    return json.loads(zlib.decompress(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))))


value = ns["build_export"](clock.time)
data = decode(value)
assert data["n"] == ["Áda", "Lovelace"]
assert data["s"] == state.all_time_scores and data["d"] == state.daily_scores
assert data["day"] == "2026-11-08" and data["at"] == "2026-11-08T20:00:45.000Z"
assert data["cut"] and len(data["t"]) == 100
assert set(data["t"]) == set(dates[2:] + ["2026-11-08"])
assert data["t"][dates[-1]] == 0 and data["t"][dates[-2]] == 1
assert data["t"]["2026-11-08"] == 1
assert len(state.daily_usage_ms) == 102

state.last_active_date = "yesterday"
assert decode(ns["build_export"](clock.time))["d"] == {}
asyncio.run(ns["export_scores"](None))
assert decode(clipboard.value)["n"] == ["Áda", "Lovelace"]
assert success == [True]
assert elements["export-text"].classList.hidden
assert elements["focus-menu"].classList.hidden and elements["profile-menu"].classList.hidden
assert elements["focus-button"].values["aria-expanded"] == "false"
assert elements["profile-button"].values["aria-expanded"] == "false"

clipboard.fail = True
asyncio.run(ns["export_scores"](None))
assert "Clipboard access failed" in elements["export-status"].textContent
assert decode(elements["export-text"].value)["s"] == state.all_time_scores
assert not elements["export-text"].classList.hidden

clipboard.fail = False
clipboard.value = None
randomizer = random.Random(7)
state.firstname = "".join(randomizer.choices(string.ascii_letters + string.digits, k=7000))
asyncio.run(ns["export_scores"](None))
assert clipboard.value is None
assert len(elements["export-text"].value) > 4000
assert "too long" in elements["export-status"].textContent
assert decode(elements["export-text"].value)["n"][0] == state.firstname
print("ok")

"""Exercise the browser usage tracker with a controllable local clock."""
import json
import re
import sys
import textwrap
import types
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

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

zone = ZoneInfo("Europe/London")


def millis(date):
    return int(date.timestamp() * 1000)


class DateValue:
    def __init__(self, value):
        self.date = datetime.fromtimestamp(value / 1000, zone)

    def getFullYear(self):
        return self.date.year

    def getMonth(self):
        return self.date.month - 1

    def getDate(self):
        return self.date.day

    def setHours(self, hours, minutes, seconds, milliseconds):
        assert (hours, minutes, seconds, milliseconds) == (24, 0, 0, 0)
        tomorrow = self.date.date() + timedelta(days=1)
        self.date = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=zone)

    def getTime(self):
        return millis(self.date)

    def toDateString(self):
        return "today"


class Clock:
    time = millis(datetime(2026, 3, 28, 23, 59, 50, tzinfo=zone))

    def now(self):
        return self.time

    def new(self, value=None):
        return DateValue(self.time if value is None else value)


class Storage:
    data = None

    def getItem(self, key):
        return self.data

    def setItem(self, key, value):
        self.data = value

    def removeItem(self, key):
        self.data = None


clock = Clock()
storage = Storage()
display = types.SimpleNamespace(textContent="")
document = types.SimpleNamespace(
    hidden=False,
    getElementById=lambda name: display if name == "time-today" else types.SimpleNamespace(checked=False),
)
ns["window"] = types.SimpleNamespace(Date=clock, localStorage=storage)
ns["document"] = document
state = ns["state"]
state.firstname = "Ada"
state.lastname = "Lovelace"
state.last_active_date = "today"

ns["usage_interaction"](None)
assert state.usage_tracking_since == "2026-03-28"
assert json.loads(storage.data)["usage_tracking_since"] == "2026-03-28"
clock.time += 20_000
ns["usage_tick"]()
assert state.daily_usage_ms == {"2026-03-28": 10_000, "2026-03-29": 10_000}
assert display.textContent == "10s"

# A long idle period contributes only the first minute, even after a delayed tick.
clock.time += 120_000
ns["usage_tick"]()
assert state.daily_usage_ms["2026-03-29"] == 50_000
ns["usage_interaction"](None)
clock.time += 5_000
ns["usage_tick"]()
assert state.daily_usage_ms["2026-03-29"] == 55_000

# Visibility loss flushes the current interval; hidden time and time before the
# next interaction on return are not included.
clock.time += 2_000
document.hidden = True
ns["usage_visibility"](None)
clock.time += 120_000
document.hidden = False
ns["usage_visibility"](None)
ns["usage_tick"]()
assert state.daily_usage_ms["2026-03-29"] == 57_000
ns["usage_interaction"](None)
clock.time += 3_000
ns["usage_pause"](None)
assert state.daily_usage_ms["2026-03-29"] == 60_000
assert display.textContent == "1m 0s"

# Interactions before the idle deadline extend the active interval without
# losing time between them, including when no periodic tick has fired.
ns["usage_interaction"](None)
clock.time += 50_000
ns["usage_interaction"](None)
clock.time += 50_000
ns["usage_tick"]()
assert state.daily_usage_ms["2026-03-29"] == 160_000

# A backwards clock adjustment must never subtract or invent elapsed time.
clock.time -= 200_000
ns["usage_tick"]()
assert state.daily_usage_ms["2026-03-29"] == 160_000
clock.time += 5_000
ns["usage_pause"](None)
assert state.daily_usage_ms["2026-03-29"] == 165_000

# Reload preserves usage, while older saved data starts with no tracking history.
state.daily_usage_ms = {}
assert ns["load_state"]()
assert state.daily_usage_ms == {"2026-03-28": 10_000, "2026-03-29": 165_000}
assert state.usage_tracking_since == "2026-03-28"
storage.data = json.dumps({"firstname": "Old", "lastname": "User", "last_active_date": "today"})
assert ns["load_state"]()
assert state.daily_usage_ms == {}
assert state.usage_tracking_since is None

# Reset must not allow subsequent idle checkpoints to recreate saved data.
class Classes:
    def add(self, name):
        pass

    def remove(self, name):
        pass


elements = {}
def element(name):
    if name not in elements:
        elements[name] = types.SimpleNamespace(classList=Classes(), checked=False, value="", textContent="")
    return elements[name]

document.getElementById = element
ns["clear_questions"] = lambda: None
ns["refresh_dashboard"] = lambda: None
ns["usage_interaction"](None)
clock.time += 4_000
ns["confirm_reset"](None)
ns["usage_tick"]()
ns["usage_pause"](None)
assert storage.data is None
assert state.daily_usage_ms == {} and state.usage_tracking_since is None
print("ok")

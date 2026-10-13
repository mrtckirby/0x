"""Logic checks for the Bit patterns (IPv4) questions.

Loads the Python in index.html (everything before the event listeners) with stubbed
browser modules, then exercises the generators and validators. Run by tests/bit_patterns.spec.js.
"""
import re
import sys
import textwrap
import types
from pathlib import Path

source = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
code = re.search(r'<script type="py">(.*?)</script>', source, re.S).group(1)
code = code.split("# EVENT LISTENERS & INITIALIZATION")[0]
code = code.rsplit("# ====", 1)[0]

pyscript = types.ModuleType("pyscript")
pyscript.document = pyscript.window = object()
pyodide = types.ModuleType("pyodide")
ffi = types.ModuleType("pyodide.ffi")
ffi.create_once_callable = ffi.create_proxy = lambda f: f
sys.modules.update({"pyscript": pyscript, "pyodide": pyodide, "pyodide.ffi": ffi})

ns = {}
exec(textwrap.dedent(code), ns)
CONFIG = ns["QUESTION_CONFIG"]
validate = ns["validate_answer"]
state = ns["state"]

IP_TYPES = {
    "ip_network_address", "ip_host_id", "ip_cidr_to_mask", "ip_mask_to_cidr",
    "ip_usable_hosts", "ip_min_subnet", "ip_broadcast_address", "ip_first_last_host",
}
IMAGE_TYPE = "image_representation"
LABELS = [
    "Network address (IP/CIDR)", "Host ID (IP/CIDR)", "CIDR → dotted-decimal mask",
    "Dotted-decimal mask → CIDR", "Usable hosts in subnet", "Minimum subnet for host requirement",
    "Broadcast address (IP/CIDR)", "First/last usable host",
    "Representing images (colour depth / file size)",
]


def to_int(dotted):
    a, b, c, d = (int(x) for x in dotted.split("."))
    return (a << 24) | (b << 16) | (c << 8) | d


def to_dotted(value):
    return ".".join(str((value >> s) & 255) for s in (24, 16, 8, 0))


def mask(prefix):
    return (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF


def check_config():
    assert "bit_patterns" in ns["MASTER_CATEGORIES"]
    ip = {k: v for k, v in CONFIG.items() if v["master"] == "bit_patterns"}
    assert set(ip) == IP_TYPES | {IMAGE_TYPE}
    assert sorted(v["label"] for v in ip.values()) == sorted(LABELS)
    assert all(v["advanced"] for v in ip.values())
    assert len({v["weight"] for v in ip.values()}) == 1

    for advanced in (False, True):
        state.advanced_mode = advanced
        seen = set()
        for _ in range(3000):
            seen.add(ns["choose_weighted_question_type"]())
        if advanced:
            assert IP_TYPES | {IMAGE_TYPE} <= seen, (IP_TYPES | {IMAGE_TYPE}) - seen
        else:
            assert not ((IP_TYPES | {IMAGE_TYPE}) & seen)
            assert not any(CONFIG[t]["master"] == "bit_patterns" for t in seen)
    state.advanced_mode = False


def check_generators():
    for q_type in sorted(IP_TYPES):
        for _ in range(500):
            q = CONFIG[q_type]["generator"]()
            assert q.question_type == q_type
            p = q.prompt
            # Never generate /31 or /32 questions.
            assert not re.search(r"/(31|32)\b", p), p
            check_question(q_type, q)


def addr_prefix(prompt):
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)/(\d+)", prompt)
    return to_int(m.group(1)), int(m.group(2))


def check_question(q_type, q):
    p = q.prompt
    if q_type in ("ip_network_address", "ip_host_id", "ip_broadcast_address"):
        ip, prefix = addr_prefix(p)
        first = ip >> 24
        assert 1 <= first <= 223 and first != 127, p
        host = ip & ~mask(prefix) & 0xFFFFFFFF
        assert 8 <= prefix <= 30 and host not in (0, ~mask(prefix) & 0xFFFFFFFF), p
        net = ip & mask(prefix)
        want = {
            "ip_network_address": net,
            "ip_host_id": host,
            "ip_broadcast_address": net | (~mask(prefix) & 0xFFFFFFFF),
        }[q_type]
        answer = to_dotted(want)
    elif q_type == "ip_cidr_to_mask":
        prefix = int(re.search(r"/(\d+)", p).group(1))
        assert 8 <= prefix <= 30
        answer = to_dotted(mask(prefix))
    elif q_type == "ip_mask_to_cidr":
        prefix = bin(to_int(re.search(r"mask (\d+\.\d+\.\d+\.\d+)", p).group(1))).count("1")
        assert 8 <= prefix <= 30
        assert validate(q.validator_type, q.expected, str(prefix))
        assert validate(q.validator_type, q.expected, "/" + str(prefix))
        assert validate(q.validator_type, q.expected, "  / " + str(prefix) + " ")
        assert not validate(q.validator_type, q.expected, str(prefix + 1))
        assert not validate(q.validator_type, q.expected, "//" + str(prefix))
        return
    elif q_type == "ip_usable_hosts":
        prefix = int(re.search(r"/(\d+) subnet", p).group(1))
        assert prefix <= 30
        assert validate(q.validator_type, q.expected, str(2 ** (32 - prefix) - 2))
        assert not validate(q.validator_type, q.expected, str(2 ** (32 - prefix)))
        return
    elif q_type == "ip_min_subnet":
        hosts = int(re.search(r"accommodate (\d+)", p).group(1))
        prefix = max(x for x in range(1, 31) if 2 ** (32 - x) - 2 >= hosts)
        assert hosts >= 2
        assert validate(q.validator_type, q.expected, "/" + str(prefix))
        assert validate(q.validator_type, q.expected, str(prefix))
        assert not validate(q.validator_type, q.expected, str(prefix + 1))
        return
    else:  # first/last host
        ip, prefix = addr_prefix(p)
        assert 8 <= prefix <= 30
        assert ip & mask(prefix) == ip, p
        broadcast = ip | (~mask(prefix) & 0xFFFFFFFF)
        answer = to_dotted(ip + 1 if " first " in p else broadcast - 1)
        assert " first " in p or " last " in p

    assert validate(q.validator_type, q.expected, answer), (p, answer)
    # Answer normalisation: whitespace and leading zeroes.
    padded = ".".join(o.zfill(3) for o in answer.split("."))
    assert validate(q.validator_type, q.expected, padded), padded
    assert validate(q.validator_type, q.expected, "  " + answer + "  ")
    assert validate(q.validator_type, q.expected, " . ".join(answer.split(".")))
    # Dotted-decimal only.
    assert not validate(q.validator_type, q.expected, str(to_int(answer)))
    assert not validate(q.validator_type, q.expected, bin(to_int(answer)))
    assert not validate(q.validator_type, q.expected, answer + ".0")
    assert not validate(q.validator_type, q.expected, "")


def check_images():
    import math
    master = set(ns["IMAGE_MASTER_PALETTE"])
    assert len(master) == 9
    pairs = ns["IMAGE_SIMILAR_PAIRS"]
    depths, variants = set(), set()
    # Soft similarity rule: at most this many flagged pairs for n colours (6 can avoid all).
    allowed = {7: 1, 8: 2, 9: 4}
    for n, bits in ((2, 1), (3, 2), (4, 2), (5, 3), (8, 3), (9, 4)):
        assert (n - 1).bit_length() == bits == math.ceil(math.log2(n))
    for _ in range(2000):
        q = CONFIG[IMAGE_TYPE]["generator"]()
        assert q.question_type == IMAGE_TYPE and q.validator_type == "integer"
        grid = q.grid
        h, w = len(grid), len(grid[0])
        assert 2 <= w <= 8 and 2 <= h <= 8 and all(len(r) == w for r in grid)
        flat = [c for r in grid for c in r]
        assert set(flat) <= master
        distinct = len(set(flat))
        assert 2 <= distinct <= min(9, w * h)
        if w * h == 4:
            assert distinct <= 4
        bits = math.ceil(math.log2(distinct))
        depths.add(bits)
        similar = sum(1 for pair in pairs if pair <= set(flat))
        assert similar == allowed.get(distinct, 0), (distinct, similar)
        p = q.prompt
        assert "minimum" in p and "image shown" in p
        if "file size" in p:
            assert "uncompressed" in p and "ignoring any metadata" in p
            size_bits = bits * w * h
            if p.endswith("Give your answer in bytes."):
                variants.add("bytes")
                assert size_bits % 8 == 0 and q.expected == size_bits // 8
                wrong = size_bits
            else:
                variants.add("bits")
                assert p.endswith("Give your answer in bits.") and q.expected == size_bits
                wrong = size_bits // 8 if size_bits % 8 == 0 else None
            if wrong is not None and wrong != q.expected:
                assert not validate(q.validator_type, q.expected, str(wrong))
        else:
            variants.add("depth")
            assert p.endswith("Give your answer in bits.") and q.expected == bits
        assert isinstance(q.expected, int)
        assert validate(q.validator_type, q.expected, " " + str(q.expected) + " ")
        assert not validate(q.validator_type, q.expected, "abc")
        assert not validate(q.validator_type, q.expected, str(q.expected + 1))
    assert depths == {1, 2, 3, 4}, depths
    assert variants == {"depth", "bits", "bytes"}, variants


def check_examples():
    assert validate("ip_address", (192, 168, 45, 0), "192.168.045.000 ")
    assert not validate("ip_address", (0, 0, 4, 52), "1076")
    assert not validate("ip_address", (0, 0, 4, 52), "0.0.4.5 2")
    assert not validate("ip_address", (0, 0, 4, 52), "0.0.4.-52")
    assert validate("cidr_prefix", 20, "/20") and validate("cidr_prefix", 20, "20")


for fn in (check_config, check_generators, check_images, check_examples):
    fn()
print("ok")

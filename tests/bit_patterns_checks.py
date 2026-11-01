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
BITWISE_TYPE = "bitwise_operators"
LABELS = [
    "Network address (IP/CIDR)", "Host ID (IP/CIDR)", "CIDR → dotted-decimal mask",
    "Dotted-decimal mask → CIDR", "Usable hosts in subnet", "Minimum subnet for host requirement",
    "Broadcast address (IP/CIDR)", "First/last usable host",
    "Representing images (colour depth / file size)",
    "4-bit bitwise operators",
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
    assert set(ip) == IP_TYPES | {IMAGE_TYPE, BITWISE_TYPE}
    assert sorted(v["label"] for v in ip.values()) == sorted(LABELS)
    assert all(ip[k]["advanced"] for k in IP_TYPES)
    assert not ip[IMAGE_TYPE]["advanced"]
    assert not ip[BITWISE_TYPE]["advanced"]
    assert len({v["weight"] for v in ip.values()}) == 1

    for advanced in (False, True):
        state.advanced_mode = advanced
        seen = set()
        for _ in range(3000):
            seen.add(ns["choose_weighted_question_type"]())
        if advanced:
            assert IP_TYPES | {IMAGE_TYPE, BITWISE_TYPE} <= seen, (IP_TYPES | {IMAGE_TYPE, BITWISE_TYPE}) - seen
        else:
            assert not (IP_TYPES & seen)
            assert {IMAGE_TYPE, BITWISE_TYPE} <= seen
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

def evaluate_expression(expression):
    def replace_comparison(match):
        left, op, right = int(match.group(1)), match.group(2), int(match.group(3))
        value = {
            "<": left < right,
            ">": left > right,
            "=": left == right,
            "≤": left <= right,
            "≥": left >= right,
        }[op]
        return "True" if value else "False"

    expression = re.sub(r"\((\d+) ([<>=≤≥]) (\d+)\)", replace_comparison, expression)
    tokens = re.findall(r"True|False|AND|OR|XOR|NOT|[()]", expression)
    assert "".join(tokens) == re.sub(r"\s+", "", expression)
    index = 0

    def parse_primary():
        nonlocal index
        if tokens[index] == "(":
            index += 1
            value = parse_or()
            assert tokens[index] == ")"
            index += 1
            return value
        value = tokens[index] == "True"
        assert tokens[index] in ("True", "False")
        index += 1
        return value

    def parse_unary():
        nonlocal index
        if tokens[index] == "NOT":
            index += 1
            return not parse_unary()
        return parse_primary()

    def parse_and():
        nonlocal index
        value = parse_unary()
        while index < len(tokens) and tokens[index] == "AND":
            index += 1
            right = parse_unary()
            value = value and right
        return value

    def parse_xor():
        nonlocal index
        value = parse_and()
        while index < len(tokens) and tokens[index] == "XOR":
            index += 1
            right = parse_and()
            value = value != right
        return value

    def parse_or():
        nonlocal index
        value = parse_xor()
        while index < len(tokens) and tokens[index] == "OR":
            index += 1
            right = parse_xor()
            value = value or right
        return value

    result = parse_or()
    assert index == len(tokens)
    return result


def check_logical_operators():
    logical_operators = set()
    for _ in range(1000):
        q = CONFIG["operators_boolean"]["generator"]()
        expression = q.prompt.split(": ", 1)[1].split("\n", 1)[0]
        comparisons = re.findall(r"\(\d+ [<>=≤≥] \d+\)", expression)
        assert 2 <= len(comparisons) <= 4, expression
        depth = maximum = 0
        for char in expression:
            if char == "(":
                depth += 1
                maximum = max(maximum, depth)
            elif char == ")":
                depth -= 1
                assert depth >= 0
        assert depth == 0 and maximum <= 2, expression
        logical_operators.update(re.findall(r"\b(?:AND|OR|XOR|NOT)\b", expression))
        assert evaluate_expression(expression) == q.expected, expression
        assert validate("boolean", q.expected, "True" if q.expected else "False")
        assert validate("boolean", q.expected, "true" if q.expected else "false")
        assert validate("boolean", q.expected, "1" if q.expected else "0")
    assert logical_operators == {"AND", "OR", "XOR", "NOT"}, logical_operators


def check_bitwise_questions():
    operations = set()
    for _ in range(1000):
        q = CONFIG[BITWISE_TYPE]["generator"]()
        match = re.fullmatch(
            r"Calculate (NOT )?([01]{4})(?: (AND|OR|XOR) ([01]{4}))?\. "
            r"Give your answer as a 4-bit binary number\.",
            q.prompt,
        )
        assert match and q.validator_type == "binary_4bit", q.prompt
        not_op, left_text, op, right_text = match.groups()
        left = int(left_text, 2)
        if not_op:
            expected = (~left) & 0b1111
            operations.add("NOT")
        else:
            right = int(right_text, 2)
            expected = {"AND": left & right, "OR": left | right, "XOR": left ^ right}[op]
            operations.add(op)
        expected_text = bin(expected)[2:].zfill(4)
        assert q.expected == expected_text, q.prompt
        assert validate(q.validator_type, q.expected, expected_text)
        assert not validate(q.validator_type, q.expected, expected_text[1:])
        assert not validate(q.validator_type, q.expected, expected_text + "0")
        assert not validate(q.validator_type, q.expected, "10a0")
    assert operations == {"AND", "OR", "XOR", "NOT"}, operations


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
        assert 2 <= h <= w <= 8 and w * h <= 16 and all(len(r) == w for r in grid)
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


for fn in (check_config, check_generators, check_images, check_examples, check_logical_operators, check_bitwise_questions):
    fn()
print("ok")

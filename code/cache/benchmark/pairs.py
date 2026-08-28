"""Labeled code/request pairs for measuring the semantic-cache threshold.

Each pair is (A, B, label):
  - "same"    : A and B mean the SAME thing -> the cache SHOULD reuse (want HIGH cosine)
  - "different": A and B mean DIFFERENT things -> the cache MUST NOT reuse (want LOW cosine)

The point of the benchmark is to find a threshold that keeps every "same" pair
above it and every "different" pair below it — or to show that none exists.
"""

SAME = [
    # reformatting / whitespace only
    ("def add(a,b):\n    return a+b",
     "def add(a, b):\n    return a + b"),
    # renamed local variable
    ("def total(items):\n    s = 0\n    for x in items:\n        s += x\n    return s",
     "def total(items):\n    acc = 0\n    for it in items:\n        acc += it\n    return acc"),
    # added / reworded comment (behaviour identical)
    ("def is_even(n):\n    return n % 2 == 0",
     "def is_even(n):\n    # True when n is divisible by 2\n    return n % 2 == 0"),
    # equivalent NL question about the same code
    ("What does the parse_config function do?",
     "Explain the parse_config function"),
    # docstring added
    ("def load(p):\n    return open(p).read()",
     "def load(p):\n    \"\"\"Read a file and return its text.\"\"\"\n    return open(p).read()"),
]

DIFFERENT = [
    # operator flip: strict vs non-strict
    ("def ok(a, b):\n    return a > b",
     "def ok(a, b):\n    return a >= b"),
    # arithmetic sign flip
    ("def step(x):\n    return x + 1",
     "def step(x):\n    return x - 1"),
    # boolean flip
    ("def flag():\n    return True",
     "def flag():\n    return False"),
    # equality vs inequality
    ("def same(a, b):\n    return a == b",
     "def same(a, b):\n    return a != b"),
    # off-by-one boundary
    ("def take(xs, n):\n    return xs[:n]",
     "def take(xs, n):\n    return xs[:n - 1]"),
    # different function called (and/or logic)
    ("def guard(a, b):\n    return a and b",
     "def guard(a, b):\n    return a or b"),
    # genuinely unrelated request that shares surface words
    ("Fix the bug in the validate function",
     "Add a new validate function from scratch"),
]

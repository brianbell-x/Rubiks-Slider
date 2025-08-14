import random
import hashlib
import functools
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import os
import re

# Use MMDDYYYYHHMM
def current_version_str():
    d = datetime.now()
    return f"{d.month:02d}{d.day:02d}{d.year:04d}{d.hour:02d}{d.minute:02d}"

def _env_version():
    v = os.getenv("BENCHMARK_VERSION")
    if v and re.fullmatch(r"\d{12}", v):
        return v
    return None

VERSION = _env_version() or current_version_str()

# Deterministic RNG aligned with ui/src/game.js (djb2_xor hash32 + mulberry32)
def _hash32(s: str) -> int:
    h = 5381
    for ch in s:
        h = ((h << 5) + h) ^ ord(ch)
        h &= 0xFFFFFFFF
    return h

def _imul(a: int, b: int) -> int:
    return ((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF)) & 0xFFFFFFFF

def _mulberry32(a: int):
    a &= 0xFFFFFFFF
    def rand():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = _imul(t ^ (t >> 15), t | 1)
        t ^= (t + _imul(t ^ (t >> 7), (t | 61)))
        t &= 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rand

class _RNG:
    def __init__(self, seed_str: str):
        self._seed = _hash32(seed_str)
        self._r = _mulberry32(self._seed)

    def rand(self) -> float:
        return self._r()

    def randint(self, lo: int, hi: int) -> int:
        if hi < lo:
            lo, hi = hi, lo
        return int(self.rand() * (hi - lo + 1)) + lo

    def choice(self, arr):
        if not arr:
            raise ValueError("choice() arg is an empty sequence")
        idx = int(self.rand() * len(arr))
        if idx == len(arr):  # clamp rare float edge
            idx = len(arr) - 1
        return arr[idx]

def _rng_from_seed_string(seed_str: str) -> _RNG:
    return _RNG(seed_str)

LOG_DIR = Path("benchmark/logs")
LOG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = "benchmark/benchmark_config.json"


def now_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_deterministic_shuffle_count(size: int) -> int:
    """
    Choose a deterministic 'random' shuffle length for a given grid size using VERSION as the seed.
    The range is [size, size*size*2] to scale reasonably with grid size.
    """
    rng = _rng_from_seed_string(f"ShuffleCount_v{VERSION}_{size}")
    min_moves = size
    max_moves = size * size * 2
    return rng.randint(min_moves, max_moves)


def generate_shuffle_sequence(size, moves=None):
    """
    Generate a pseudorandom shuffle sequence that is:
      • repeatable for this grid size
      • different for every size
      • still ‘random-looking’ to the model
    """
    rng = _rng_from_seed_string(f"Benchmark_v{VERSION}_{size}")
    moves = moves if moves is not None else get_deterministic_shuffle_count(size)
    seq = []
    for _ in range(moves):
        move_type = rng.choice(["row", "column"])
        idx = rng.randint(1, size)
        direction = rng.choice(["left", "right"]) if move_type == "row" else rng.choice(["up", "down"])
        seq.append({"type": move_type, "index": idx, "direction": direction})
    return seq


@functools.lru_cache(maxsize=None)
def get_shuffle_sequence(size: int) -> List[Dict]:
    return generate_shuffle_sequence(size)


def sanitize_model_name(model):
    """Sanitizes a model name string to be filesystem-safe."""
    model_str = str(model) if model is not None else "default"
    return model_str.replace("/", "_").replace(" ", "_").replace(":", "_")

import random
import hashlib
import functools
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Use MMDDYYYYHHMM
VERSION = 81220251052

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
    count_seed = (
        int(hashlib.sha256(f"ShuffleCount_v{VERSION}_{size}".encode()).hexdigest(), 16)
        & 0xFFFFFFFF
    )
    rng = random.Random(count_seed)
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
    seed = (
        int(hashlib.sha256(f"Benchmark_v{VERSION}_{size}".encode()).hexdigest(), 16)
        & 0xFFFFFFFF
    )
    rng = random.Random(seed)
    moves = moves if moves is not None else get_deterministic_shuffle_count(size)
    seq = []
    for _ in range(moves):
        move_type = rng.choice(["row", "column"])
        idx = rng.randint(1, size)
        direction = (
            rng.choice(["left", "right"])
            if move_type == "row"
            else rng.choice(["up", "down"])
        )
        seq.append({"type": move_type, "index": idx, "direction": direction})
    return seq


@functools.lru_cache(maxsize=None)
def get_shuffle_sequence(size: int) -> List[Dict]:
    return generate_shuffle_sequence(size)


def sanitize_model_name(model):
    """Sanitizes a model name string to be filesystem-safe."""
    model_str = str(model) if model is not None else "default"
    return model_str.replace("/", "_").replace(" ", "_").replace(":", "_")

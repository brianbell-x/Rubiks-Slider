# Rubiks Slider Benchmark

This project benchmarks how well language models can track and reason about the state of a complex, dynamic system. The test uses Rubiks Slider where each move shifts an entire row or column, causing nonlocal effects.

The benchmark is designed to measure a model's ability to handle problems with many interdependent parts, where the consequences of actions are not always immediately clear (aka nonlocal effects). Unlike tasks that can be solved by breaking them into independent subproblems, Rubiks Slider requires a holistic understanding of the entire state at all times.

I don't think there is a promptable or trainable solution to this problem, at least not in the sense of memorizing or brute forcing all possible states. As the Rubiks Slider size increases, the number of possible states grows exponentially, quickly exceeding any feasible memory or training capacity.

I believe that true success here lies in solving Rubiks Slider with the fewest moves and API calls. Efficiency minimizing the number of steps or interactions required to reach the solution is a key metric. There may be other definitions of success as well, and I'm interested in discovering and discussing them.

By observing model performance on this task, we hope to gain insight into their capacity for global reasoning and long horizon planning in environments with deeply entangled states.

## Repository Map

```
Rubiks-Slider-Lite/
├─ README.md             # Project documentation and setup instructions.
├─ requirements.txt      # Python dependencies for the project.
├─ benchmark/            # Benchmark execution and configuration.
│  ├─ __init__.py        # Makes the directory a Python package.
│  ├─ __main__.py        # Entry point for running as a module.
│  ├─ runner.py          # Main benchmark execution script.
│  ├─ benchmark_config.json # Configuration for benchmark runs.
│  ├─ providers.py       # API interaction layer for LLM providers.
│  ├─ sample_benchmark_config.jsonc # Sample configuration with detailed comments.
│  ├─ settings.py        # Global configuration and constants.
│  ├─ visualize.py       # Script to generate video visualizations of runs.
│  └─ .env.sample        # Template for environment variables.
└─ core/                 # Core Rubiks Slider logic and mechanics.
   ├─ __init__.py        # Makes the directory a Python package.
   └─ puzzle.py          # Core Rubiks Slider logic and state management.
```

## Running the Benchmark

1. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```
2. **Set API Keys**: Create a `.env` file in the `benchmark/` directory for your LLM provider API keys (e.g., `OPENAI_API_KEY=...`).

```
OPENAI_API_KEY = ""
GEMINI_API_KEY = ""
ANTHROPIC_API_KEY = ""
OPENROUTER_API_KEY = ""
```

3. **Configure**: Edit `benchmark/benchmark_config.json` to select the models to test.

4. **Execute**:
   ```sh
   python -m benchmark
   ```

## Human Play (Web)

A minimal, dependency-free web app is included at `docs/index.html`. It lets humans play the same Rubiks Slider as the models using click-and-drag only, with animated row/column shifts.

- Controls:
  - Drag horizontally on any tile to shift that row one step (wrap-around).
  - Drag vertically on any tile to shift that column one step (wrap-around).
  - Reset: restore the initial Rubiks Slider.
  - Share Rubiks Slider: copies a URL that reproduces the exact same Rubiks Slider.
  - New Random: casual play (not for strict benchmark parity).

- URL parameters:
  - `size`: grid size (default 6; min 2; max 12)
  - `p`: base64url-encoded JSON payload containing the shuffle used to create the Rubiks Slider, shaped like:
    ```json
    {"size":6,"seq":[{"type":"row","index":1,"direction":"left"}, ...]}
    ```
  If `p` is absent or invalid, the page falls back to a simple random shuffle.

### Progressive test mode

- Default behavior with no `p` parameter is a progressive test that starts at 3×3 and automatically advances to 4×4, 5×5, and 6×6 when each board is solved.
- You can also force progressive mode with `progressive=1` (e.g., `...?progressive=1`).
- When a `p` parameter is provided (benchmark-parity link), the page runs a single Rubiks Slider and does not auto-advance, preserving parity with the models.
- A version tag is shown in the header using the local date/time in the format `MMDDYYYYHHMM` (e.g., `v081220252332`).

### Hosting via GitHub Pages

1. Commit `docs/index.html` (already present).
2. In GitHub: Settings → Pages → Source: "Deploy from a branch"; Branch: `main`; Folder: `/docs`.
3. Save. Your site will be available at:
   ```
   https://<YOUR_GITHUB_USERNAME>.github.io/Rubiks-Slider-Lite/
   ```

### Generating a shareable Rubiks Slider link that matches the benchmark shuffle

Use the deterministic shuffle already used by the benchmark to ensure parity with model runs. The snippet below outputs a URL you can share with humans:

```python
# Generate a human-play URL with the same deterministic shuffle the benchmark uses.
import json, base64
from benchmark.settings import get_shuffle  # uses the deterministic seed/version

size = 6
moves = 10  # match your run settings; benchmark uses get_shuffle(size, moves)
seq = get_shuffle(size, moves)  # [{"type":"row"|"column","index":1-based,"direction":"left"|"right"|"up"|"down"}, ...]

payload = {"size": size, "seq": seq}
b64url = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")

base = "https://<YOUR_GITHUB_USERNAME>.github.io/Rubiks-Slider-Lite/"
print(f"{base}?size={size}&p={b64url}")
```

Replace `<YOUR_GITHUB_USERNAME>` with your GitHub username. The printed URL opens the web app with the exact same initial state the models received.

### Local testing

- Open `docs/index.html` directly in a browser, or serve the repo with any static server.
- You can also append `?size=6` (and optionally a `p` payload) to test parameters locally.

### Security note

Do not commit real API keys. Remove any secrets from version control and rotate keys if they were exposed (e.g., `benchmark/.env`). Use `benchmark/.env.sample` as the template checked into the repo.

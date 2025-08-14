Update the CLI so that it tracks and displays the number of API calls instead of the number of moves. When printing progress, show "> Attempting call N ..." (without the model name). In the result summary, include "api_calls=N" alongside moves, solved, and reason.

Attempting call 1
Attempting call 2
...

Here is what it looks like now:

```
...

--- Grid Size: 3×3 ---
  > Using shuffle of 14 moves for 3x3.

  --- Testing openai/gpt-5 ---
    * Attempt 1/3
    > Attempting move 1 (for openai/gpt-5)...
    > Result (Attempt 1): moves=17, solved=True, reason=Solved
    * Attempt 2/3
    > Attempting move 1 (for openai/gpt-5)...
    > Result (Attempt 2): moves=15, solved=True, reason=Solved
    * Attempt 3/3
    > Attempting move 1 (for openai/gpt-5)...
    > Result (Attempt 3): moves=17, solved=True, reason=Solved
    > Incremental results saved: benchmark\logs\20250814_003955\openai_gpt-5\openai_gpt-5_results.json

...
```
Heres what I want it to look like:

```
...

--- Grid Size: 3×3 ---
  > Using shuffle of 14 moves for 3x3.

  --- Testing openai/gpt-5 ---
    * Attempt 1/3
    > Attempting call 1 ...
    > Result (Attempt 1): api_calls=1, moves=17, solved=True, reason=Solved
    * Attempt 2/3
    > Attempting call 1 ...
    > Result (Attempt 2): api_calls=1, moves=15, solved=True, reason=Solved
    * Attempt 3/3
    > Attempting call 1 ...
    > Result (Attempt 3): api_calls=1, moves=17, solved=True, reason=Solved
    > Incremental results saved: benchmark\logs\20250814_003955\openai_gpt-5\openai_gpt-5_results.json

...
```

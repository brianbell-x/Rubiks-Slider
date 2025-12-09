# Rubiks Slider Benchmark

The benchmark is designed to measure a model's ability to handle problems with many interdependent parts, where the consequences of actions are not always immediately clear. Unlike tasks that can be solved by breaking them into independent subproblems, Rubiks Slider requires a holistic understanding of the entire state at all times.

I don't think there is a promptable or trainable solution to this problem, at least not in the sense of memorizing or brute forcing all possible states. As the Rubiks Slider size increases, the number of possible states grows exponentially, quickly exceeding any feasible memory or training capacity.

By observing model performance on this task, we hope to gain insight into their capacity for global reasoning and long horizon planning in environments with deeply entangled states.
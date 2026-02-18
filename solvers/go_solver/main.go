package main

import (
	"encoding/json"
	"io"
	"os"
)

func main() {
	data, err := io.ReadAll(os.Stdin)
	if err != nil {
		fail("failed to read stdin")
	}

	var req Request
	if err := json.Unmarshal(data, &req); err != nil {
		fail("invalid request JSON")
	}

	if req.SolveMethod == "" {
		req.SolveMethod = "mrv_backtracking"
	}

	st, err := buildState(req)
	if err != nil {
		fail(err.Error())
	}

	usePropagation := req.SolveMethod == "mrv_backtracking_with_propagation" ||
		req.SolveMethod == "mrv_backtracking_with_propagation_randomized"
	randomized := req.SolveMethod == "mrv_backtracking_randomized" ||
		req.SolveMethod == "mrv_backtracking_with_propagation_randomized" ||
		req.SolveMethod == "exhaustive_backtracking_randomized"
	exhaustive := req.SolveMethod == "exhaustive_backtracking" || req.SolveMethod == "exhaustive_backtracking_randomized"
	if !usePropagation && !randomized && !exhaustive && req.SolveMethod != "mrv_backtracking" {
		fail("unsupported solve_method")
	}

	if !search(st, usePropagation, randomized, exhaustive) {
		fail("No valid solution for the provided target and known grid")
	}

	solution := make([][]int, st.size)
	for r := 0; r < st.size; r++ {
		solution[r] = make([]int, st.size)
		copy(solution[r], st.grid[r])
	}

	response := Response{Solution: solution}
	encoded, err := json.Marshal(response)
	if err != nil {
		fail("failed to encode response")
	}
	_, _ = os.Stdout.WriteString(string(encoded) + "\n")
}

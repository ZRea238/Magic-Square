package main

import (
	"fmt"
	"math/rand"
	"time"
)

func buildRemainingAvailable(maxVal int, used map[int]bool, exclude int) []int {
	values := []int{}
	for v := 1; v <= maxVal; v++ {
		if used[v] || v == exclude {
			continue
		}
		values = append(values, v)
	}
	return values
}

func applyValue(st *State, value, r, c int) {
	st.grid[r][c] = value
	st.rowSums[r] += value
	st.colSums[c] += value
	st.rowUnknowns[r]--
	st.colUnknowns[c]--
	for _, d := range diagIndexes(r, c, st.size) {
		st.diagSums[d] += value
		st.diagUnknowns[d]--
	}
	st.used[value] = true
}

func revertValue(st *State, value, r, c int) {
	st.grid[r][c] = 0
	st.rowSums[r] -= value
	st.colSums[c] -= value
	st.rowUnknowns[r]++
	st.colUnknowns[c]++
	for _, d := range diagIndexes(r, c, st.size) {
		st.diagSums[d] -= value
		st.diagUnknowns[d]++
	}
	delete(st.used, value)
}

func buildState(req Request) (*State, error) {
	if req.Size < 2 {
		return nil, fmt.Errorf("size must be at least 2")
	}
	if req.Target <= req.Size {
		return nil, fmt.Errorf("target must be greater than size")
	}
	if req.GameMode == "" {
		req.GameMode = "unbounded"
	}
	maxVal := req.Target - 1
	if req.GameMode == "bounded_by_size_squared" {
		maxVal = min(maxVal, req.Size*req.Size)
	} else if req.GameMode != "unbounded" {
		return nil, fmt.Errorf("game_mode must be one of: unbounded, bounded_by_size_squared")
	}
	if maxVal < 1 {
		return nil, fmt.Errorf("no valid value range")
	}

	grid := make([][]int, req.Size)
	for i := 0; i < req.Size; i++ {
		grid[i] = make([]int, req.Size)
	}
	if req.KnownGrid != nil {
		if len(req.KnownGrid) != req.Size {
			return nil, fmt.Errorf("known_grid must match size")
		}
		for r := 0; r < req.Size; r++ {
			if len(req.KnownGrid[r]) != req.Size {
				return nil, fmt.Errorf("known_grid must match size")
			}
			for c := 0; c < req.Size; c++ {
				if req.KnownGrid[r][c] == nil {
					continue
				}
				value := *req.KnownGrid[r][c]
				if value < 1 || value > maxVal {
					return nil, fmt.Errorf("known value out of range")
				}
				grid[r][c] = value
			}
		}
	}

	st := &State{
		grid:        grid,
		target:      req.Target,
		size:        req.Size,
		maxVal:      maxVal,
		rowSums:     make([]int, req.Size),
		colSums:     make([]int, req.Size),
		rowUnknowns: make([]int, req.Size),
		colUnknowns: make([]int, req.Size),
		used:        map[int]bool{},
		rng:         rand.New(rand.NewSource(time.Now().UnixNano())),
	}

	for r := 0; r < req.Size; r++ {
		for c := 0; c < req.Size; c++ {
			value := st.grid[r][c]
			if value == 0 {
				st.rowUnknowns[r]++
				st.colUnknowns[c]++
				for _, d := range diagIndexes(r, c, st.size) {
					st.diagUnknowns[d]++
				}
				st.unknowns = append(st.unknowns, [2]int{r, c})
				continue
			}
			if st.used[value] {
				return nil, fmt.Errorf("known_grid cannot contain duplicate values")
			}
			st.used[value] = true
			st.rowSums[r] += value
			st.colSums[c] += value
			for _, d := range diagIndexes(r, c, st.size) {
				st.diagSums[d] += value
			}
		}
	}

	return st, nil
}

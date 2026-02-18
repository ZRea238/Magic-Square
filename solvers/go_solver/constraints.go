package main

func valueBounds(st *State, r, c int) (int, int) {
	rowLeft := st.target - st.rowSums[r]
	colLeft := st.target - st.colSums[c]
	exactValues := []int{}
	upperCandidates := []int{}

	if st.rowUnknowns[r] == 1 {
		exactValues = append(exactValues, rowLeft)
	} else {
		upperCandidates = append(upperCandidates, rowLeft-(st.rowUnknowns[r]-1))
	}

	if st.colUnknowns[c] == 1 {
		exactValues = append(exactValues, colLeft)
	} else {
		upperCandidates = append(upperCandidates, colLeft-(st.colUnknowns[c]-1))
	}

	for _, d := range diagIndexes(r, c, st.size) {
		diagLeft := st.target - st.diagSums[d]
		diagUnknown := st.diagUnknowns[d]
		if diagUnknown == 1 {
			exactValues = append(exactValues, diagLeft)
		} else {
			upperCandidates = append(upperCandidates, diagLeft-(diagUnknown-1))
		}
	}

	if len(exactValues) > 0 {
		reference := exactValues[0]
		if reference < 1 {
			return 1, 0
		}
		for _, v := range exactValues {
			if v != reference {
				return 1, 0
			}
		}
		for _, upper := range upperCandidates {
			if reference > upper {
				return 1, 0
			}
		}
		return reference, reference
	}

	if len(upperCandidates) == 0 {
		return 1, 0
	}

	upper := upperCandidates[0]
	for _, v := range upperCandidates {
		if v < upper {
			upper = v
		}
	}
	return 1, upper
}

func canPlace(st *State, value, r, c int) bool {
	if st.used[value] {
		return false
	}
	rowRemainingUnknown := st.rowUnknowns[r] - 1
	colRemainingUnknown := st.colUnknowns[c] - 1

	rowAfter := st.rowSums[r] + value
	colAfter := st.colSums[c] + value

	rowRemainingSum := st.target - rowAfter
	colRemainingSum := st.target - colAfter

	if rowRemainingUnknown == 0 && rowRemainingSum != 0 {
		return false
	}
	if colRemainingUnknown == 0 && colRemainingSum != 0 {
		return false
	}

	remaining := buildRemainingAvailable(st.maxVal, st.used, value)
	if rowRemainingUnknown > 0 {
		rowMin, rowMax := minMaxSum(remaining, rowRemainingUnknown)
		if rowRemainingSum < rowMin || rowRemainingSum > rowMax {
			return false
		}
	}
	if colRemainingUnknown > 0 {
		colMin, colMax := minMaxSum(remaining, colRemainingUnknown)
		if colRemainingSum < colMin || colRemainingSum > colMax {
			return false
		}
	}

	for _, d := range diagIndexes(r, c, st.size) {
		diagRemainingUnknown := st.diagUnknowns[d] - 1
		diagAfter := st.diagSums[d] + value
		diagRemainingSum := st.target - diagAfter
		if diagRemainingUnknown == 0 && diagRemainingSum != 0 {
			return false
		}
		if diagRemainingUnknown > 0 {
			dMin, dMax := minMaxSum(remaining, diagRemainingUnknown)
			if diagRemainingSum < dMin || diagRemainingSum > dMax {
				return false
			}
		}
	}

	return true
}

func validCandidates(st *State, r, c int, randomized bool) []int {
	low, high := valueBounds(st, r, c)
	if low > high {
		return []int{}
	}
	high = min(high, st.maxVal)
	candidates := []int{}
	for value := low; value <= high; value++ {
		if canPlace(st, value, r, c) {
			candidates = append(candidates, value)
		}
	}
	if randomized && len(candidates) > 1 {
		st.rng.Shuffle(len(candidates), func(i, j int) {
			candidates[i], candidates[j] = candidates[j], candidates[i]
		})
	}
	return candidates
}

func selectNext(st *State, randomized bool) (int, int, []int, bool) {
	bestR := -1
	bestC := -1
	bestCandidates := []int{}
	bestDomainSize := -1

	for _, pos := range st.unknowns {
		r := pos[0]
		c := pos[1]
		if st.grid[r][c] != 0 {
			continue
		}
		cands := validCandidates(st, r, c, randomized)
		if len(cands) == 0 {
			return r, c, cands, true
		}
		if bestDomainSize == -1 || len(cands) < bestDomainSize {
			bestDomainSize = len(cands)
			bestR = r
			bestC = c
			bestCandidates = cands
		}
	}

	if bestR == -1 {
		return 0, 0, nil, false
	}
	return bestR, bestC, bestCandidates, true
}

func selectNextExhaustive(st *State, randomized bool) (int, int, []int, bool) {
	for _, pos := range st.unknowns {
		r := pos[0]
		c := pos[1]
		if st.grid[r][c] != 0 {
			continue
		}
		candidates := validCandidates(st, r, c, randomized)
		return r, c, candidates, true
	}
	return 0, 0, nil, false
}

func finalConstraints(st *State) bool {
	for i := 0; i < st.size; i++ {
		if st.rowSums[i] != st.target || st.colSums[i] != st.target {
			return false
		}
	}
	return st.diagSums[0] == st.target && st.diagSums[1] == st.target
}

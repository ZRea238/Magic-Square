package main

func search(st *State, usePropagation bool, randomized bool, exhaustive bool) bool {
	forced := [][3]int{}
	for {
		var r, c int
		var candidates []int
		var hasChoice bool
		if exhaustive {
			r, c, candidates, hasChoice = selectNextExhaustive(st, randomized)
		} else {
			r, c, candidates, hasChoice = selectNext(st, randomized)
		}
		if !hasChoice {
			return finalConstraints(st)
		}
		if len(candidates) == 0 {
			for i := len(forced) - 1; i >= 0; i-- {
				revertValue(st, forced[i][2], forced[i][0], forced[i][1])
			}
			return false
		}
		if !usePropagation || len(candidates) != 1 {
			for _, value := range candidates {
				applyValue(st, value, r, c)
				if search(st, usePropagation, randomized, exhaustive) {
					return true
				}
				revertValue(st, value, r, c)
			}
			for i := len(forced) - 1; i >= 0; i-- {
				revertValue(st, forced[i][2], forced[i][0], forced[i][1])
			}
			return false
		}

		value := candidates[0]
		applyValue(st, value, r, c)
		forced = append(forced, [3]int{r, c, value})
	}
}
